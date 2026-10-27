"""Canonical CurrentPublicEligibility resolution — SLICE-0069.

The one production application entry point resolving
`hullq.domain.current_public_eligibility.evaluate_current_public_eligibility`
against real persisted state for one exact NativeListing, at an explicit
*as_of* freshness boundary.

Reused identically by the public exact-listing read model
(`hullq.application.public_listing_read`) and both accepted Direct Search
paths (`hullq.application.inventory_search`,
`hullq.application.native_inventory_query`) so "ACTIVE != current-public" and
D29 admission can never silently diverge between those surfaces (contract
§16: "must reuse one current-public eligibility function/service"). Also
reused by the Broker Workspace inventory read
(`hullq.application.broker_inventory_read`) to render structured ACTIVE-but-
suppressed reasons (contract §17) without a second, independently
maintained definition of current-public truth.

This module never mutates lifecycle/freshness/offer/claim/media state --
resolving eligibility here is always a pure read, and a SUPPRESSED result
never implies any lifecycle rewrite (contract §12).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.application.native_listing_freshness import (
    CurrentFreshness,
    resolve_current_freshness,
)
from hullq.domain.current_public_eligibility import (
    CurrentPublicCoverState,
    CurrentPublicEligibilityFacts,
    CurrentPublicEligibilityResult,
    CurrentPublicEligibilityStatus,
    CurrentPublicSuppressionReason,
    evaluate_current_public_eligibility,
)
from hullq.domain.market_identity import (
    MarketEpisodeId,
    NativeListingId,
    PhysicalBoatId,
)
from hullq.domain.native_listing_freshness import (
    MANUAL_NATIVE_V1,
    FreshnessStatus,
    evaluate_freshness_status,
)
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.publication_readiness import CoverState
from hullq.domain.publishing_eligibility import (
    MarketplaceOrganizationId,
    OrganizationPublishingEligibility,
)
from hullq.persistence.broker_identity import fetch_marketplace_organization
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.persistence.physical_boat_claims import fetch_current_physical_boat_claim
from hullq.persistence.publication_readiness import resolve_cover_state_and_image_presence

__all__ = [
    "BulkCurrentPublicEligibility",
    "resolve_current_public_eligibility",
    "resolve_current_public_eligibility_for_many",
]

_COVER_STATE_MAP: dict[CoverState, CurrentPublicCoverState] = {
    CoverState.VALID: CurrentPublicCoverState.VALID,
    CoverState.MISSING: CurrentPublicCoverState.MISSING,
    CoverState.INVALID: CurrentPublicCoverState.INVALID,
}


def resolve_current_public_eligibility(
    conn: Any, native_listing_id: NativeListingId, *, as_of: datetime
) -> CurrentPublicEligibilityResult | None:
    """Resolve canonical CurrentPublicEligibility for *native_listing_id*, or
    `None` when the NativeListing itself does not exist.

    `None` is a distinct "no such listing" outcome -- every caller deciding
    public/current-market readability already has a real NativeListingId
    candidate before reaching this function (contract §13: a genuinely
    missing listing is a caller-level non-enumerating concern, decided
    exactly like the existing `fetch_lifecycle_state`-first pattern in
    `hullq.application.public_listing_read.get_public_listing_read_model`).
    """
    listing_record = fetch_native_listing(conn, native_listing_id)
    if listing_record is None:
        return None

    lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
    assert lifecycle_state is not None

    freshness = resolve_current_freshness(conn, native_listing_id, as_of=as_of)

    organization = fetch_marketplace_organization(conn, listing_record.publishing_organization_id)

    market_episode_id_value: str | None = (
        listing_record.listing.market_episode_id.value
        if listing_record.listing.market_episode_id is not None
        else None
    )
    market_episode_exists = False
    physical_boat_exists = False
    physical_boat_id: PhysicalBoatId | None = None
    if market_episode_id_value is not None:
        market_episode_record = fetch_market_episode(conn, MarketEpisodeId(market_episode_id_value))
        if market_episode_record is not None:
            market_episode_exists = True
            physical_boat_id = market_episode_record.market_episode.physical_boat_id
            physical_boat_exists = fetch_physical_boat(conn, physical_boat_id) is not None

    offer_record = fetch_current_native_listing_offer(conn, native_listing_id)
    offer = offer_record.offer if offer_record is not None else None

    physical_boat_claim = None
    if physical_boat_exists:
        assert physical_boat_id is not None
        claim_record = fetch_current_physical_boat_claim(
            conn, physical_boat_id, listing_record.publishing_organization_id
        )
        physical_boat_claim = claim_record.claims if claim_record is not None else None

    has_public_usable_image, cover_state = resolve_cover_state_and_image_presence(
        conn, native_listing_id
    )

    facts = CurrentPublicEligibilityFacts(
        native_listing_id_value=native_listing_id.value,
        lifecycle_state=lifecycle_state,
        freshness_status=freshness.status,
        organization_exists=organization is not None,
        organization_publishing_eligibility=(
            organization.publishing_eligibility if organization is not None else None
        ),
        market_episode_id_present=market_episode_id_value is not None,
        market_episode_exists=market_episode_exists,
        physical_boat_exists=physical_boat_exists,
        offer=offer,
        physical_boat_claim=physical_boat_claim,
        has_public_usable_image=has_public_usable_image,
        cover_state=_COVER_STATE_MAP[cover_state],
    )
    return evaluate_current_public_eligibility(facts)


#: Mirrors `hullq.domain.current_public_eligibility`'s own private
#: `_CURRENT_FRESHNESS_STATUSES` (and `hullq.application.
#: native_listing_freshness._CURRENT_MARKET_ELIGIBLE_STATUSES`, the
#: identical already-duplicated pair) -- used only to decide, for the
#: *cheap* batched facts below, whether freshness status ALONE already
#: forces suppression. Never a second freshness *policy*: the actual
#: status value is still produced by the single unmodified
#: `evaluate_freshness_status`/`MANUAL_NATIVE_V1` pure policy.
_CHEAP_CURRENT_FRESHNESS_STATUSES = frozenset(
    {FreshnessStatus.CONFIRMED, FreshnessStatus.DUE_FOR_CONFIRMATION}
)


@dataclass(frozen=True, slots=True)
class BulkCurrentPublicEligibility:
    """One batched-path result -- amendment review (PR #387) Finding D.

    `eligibility` is produced either directly (a candidate already
    suppressed by a *cheap* batched fact needs no further reads: its
    `suppression_reasons` are a truthful, possibly-partial subset of the
    full reason set `resolve_current_public_eligibility` would compute, but
    `status` is exactly as authoritative, since any one reason already
    forces `SUPPRESSED`) or by calling the identical, unmodified
    `hullq.domain.current_public_eligibility.evaluate_current_public_eligibility`
    pure evaluator against a fully real, completely-read fact set (for a
    candidate that passed every cheap check -- the only candidates for
    which the expensive offer/claim/cover reads are ever issued). Either
    way this is never a second, independently maintained eligibility rule.

    `freshness` is the identical `CurrentFreshness` already computed as
    part of the same batched read, so callers never issue a second,
    separate `resolve_current_freshness` call for the same NativeListingId.
    """

    eligibility: CurrentPublicEligibilityResult
    freshness: CurrentFreshness


def resolve_current_public_eligibility_for_many(
    conn: Any, native_listing_ids: Sequence[NativeListingId], *, as_of: datetime
) -> dict[str, BulkCurrentPublicEligibility]:
    """Batched sibling of `resolve_current_public_eligibility` -- amendment
    review (PR #387) Finding D: "a safe bounded/batched... current-public
    eligibility + freshness on the new path".

    Reads the *cheap* facts (`native_listings` lifecycle/organization/
    episode link, `marketplace_organizations` publishing eligibility,
    `market_episodes`/`physical_boats` existence, and freshness evidence)
    for the **entire** *native_listing_ids* population in a small constant
    number of batched `= ANY(%s)` statements, instead of one statement per
    fact per candidate. Any one of these cheap facts failing already forces
    `SUPPRESSED` (`evaluate_current_public_eligibility`'s own rule: status
    is `SUPPRESSED` iff *any* reason fired) -- such a candidate's result is
    returned immediately, with ZERO further reads, since nothing downstream
    in this slice's claim-only funnel inspects anything beyond `status`.

    Only candidates that pass *every* cheap check ("survivors") ever reach
    the expensive, unchanged per-candidate reads this module's single-id
    function already uses (`fetch_current_native_listing_offer`,
    `fetch_current_physical_boat_claim`, `resolve_cover_state_and_image_presence`)
    -- for those, the full real fact set is built and the identical pure
    `evaluate_current_public_eligibility` evaluator decides the final,
    100%-authoritative result, byte-for-byte the same computation
    `resolve_current_public_eligibility` would have performed for that
    exact listing. This function never weakens D29, never truncates the
    candidate population (every id in *native_listing_ids* gets an entry),
    and never duplicates the pure evaluator's own suppression rule -- it
    only changes *how many SQL statements* gather the inputs, and *in what
    order* obviously-suppressed candidates are recognized, so the
    expensive reads scale with the surviving-candidate count rather than
    the full population.

    Returns one entry per *distinct* input id's `.value`. An input id this
    repository's own `native_listings` table has no row for at all (should
    not occur for a caller-enumerated id, defensive only) fails closed as
    `SUPPRESSED` with `LIFECYCLE_NOT_ACTIVE` rather than raising or assuming
    eligible.
    """
    distinct_values = sorted({nid.value for nid in native_listing_ids})
    if not distinct_values:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            "SELECT native_listing_id, publishing_organization_id, market_episode_id, "
            "lifecycle_state FROM native_listings WHERE native_listing_id = ANY(%s)",
            [distinct_values],
        )
        listing_rows = cur.fetchall()
    listing_facts: dict[str, tuple[str, str | None, str]] = {
        row[0]: (row[1], row[2], row[3]) for row in listing_rows
    }

    org_ids = sorted({org_id for org_id, _episode_id, _lifecycle in listing_facts.values()})
    episode_ids = sorted(
        {
            episode_id
            for _org, episode_id, _lifecycle in listing_facts.values()
            if episode_id is not None
        }
    )

    org_eligibility: dict[str, OrganizationPublishingEligibility] = {}
    if org_ids:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT organization_id, publishing_eligibility FROM marketplace_organizations "
                "WHERE organization_id = ANY(%s)",
                [org_ids],
            )
            org_eligibility = {
                row[0]: OrganizationPublishingEligibility(row[1]) for row in cur.fetchall()
            }

    episode_to_boat: dict[str, str] = {}
    if episode_ids:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT market_episode_id, physical_boat_id FROM market_episodes "
                "WHERE market_episode_id = ANY(%s)",
                [episode_ids],
            )
            episode_to_boat = dict(cur.fetchall())

    existing_boat_ids: set[str] = set()
    boat_ids = sorted(set(episode_to_boat.values()))
    if boat_ids:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT physical_boat_id FROM physical_boats WHERE physical_boat_id = ANY(%s)",
                [boat_ids],
            )
            existing_boat_ids = {row[0] for row in cur.fetchall()}

    # Freshness evidence, batched -- mirrors `hullq.persistence.
    # native_listing_freshness.fetch_effective_confirmed_at`'s own two
    # queries exactly, just `= ANY(%s)` instead of `= %s`.
    publication_at: dict[str, datetime] = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT native_listing_id, occurred_at FROM native_listing_publication_transitions "
            "WHERE native_listing_id = ANY(%s) AND from_state = 'DRAFT' AND to_state = 'ACTIVE'",
            [distinct_values],
        )
        publication_at = dict(cur.fetchall())
    reconfirmed_at: dict[str, datetime] = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT native_listing_id, MAX(occurred_at) FROM native_listing_freshness_confirmations "
            "WHERE native_listing_id = ANY(%s) GROUP BY native_listing_id",
            [distinct_values],
        )
        reconfirmed_at = {row[0]: row[1] for row in cur.fetchall() if row[1] is not None}

    def _effective_confirmed_at(native_listing_id_value: str) -> datetime | None:
        candidates = [
            value
            for value in (
                publication_at.get(native_listing_id_value),
                reconfirmed_at.get(native_listing_id_value),
            )
            if value is not None
        ]
        return max(candidates) if candidates else None

    results: dict[str, BulkCurrentPublicEligibility] = {}
    survivors: list[str] = []

    for native_listing_id_value in distinct_values:
        confirmed_at = _effective_confirmed_at(native_listing_id_value)
        freshness_status = evaluate_freshness_status(
            confirmed_at=confirmed_at, as_of=as_of, policy=MANUAL_NATIVE_V1
        )
        freshness = CurrentFreshness(status=freshness_status, last_confirmed_at=confirmed_at)

        if native_listing_id_value not in listing_facts:
            results[native_listing_id_value] = BulkCurrentPublicEligibility(
                eligibility=CurrentPublicEligibilityResult(
                    native_listing_id_value=native_listing_id_value,
                    status=CurrentPublicEligibilityStatus.SUPPRESSED,
                    suppression_reasons=frozenset(
                        {CurrentPublicSuppressionReason.LIFECYCLE_NOT_ACTIVE}
                    ),
                ),
                freshness=freshness,
            )
            continue

        org_id, episode_id, lifecycle_raw = listing_facts[native_listing_id_value]
        cheap_reasons: set[CurrentPublicSuppressionReason] = set()

        if NativeListingLifecycleState(lifecycle_raw) is not NativeListingLifecycleState.ACTIVE:
            cheap_reasons.add(CurrentPublicSuppressionReason.LIFECYCLE_NOT_ACTIVE)
        if freshness_status not in _CHEAP_CURRENT_FRESHNESS_STATUSES:
            cheap_reasons.add(CurrentPublicSuppressionReason.FRESHNESS_NOT_CURRENT)
        if org_eligibility.get(org_id) is not OrganizationPublishingEligibility.ELIGIBLE:
            cheap_reasons.add(CurrentPublicSuppressionReason.ORGANIZATION_NOT_ELIGIBLE)
        if episode_id is None or episode_id not in episode_to_boat:
            cheap_reasons.add(CurrentPublicSuppressionReason.MARKET_EPISODE_UNRESOLVED)
        elif episode_to_boat[episode_id] not in existing_boat_ids:
            cheap_reasons.add(CurrentPublicSuppressionReason.PHYSICAL_BOAT_MISSING)

        if cheap_reasons:
            results[native_listing_id_value] = BulkCurrentPublicEligibility(
                eligibility=CurrentPublicEligibilityResult(
                    native_listing_id_value=native_listing_id_value,
                    status=CurrentPublicEligibilityStatus.SUPPRESSED,
                    suppression_reasons=frozenset(cheap_reasons),
                ),
                freshness=freshness,
            )
        else:
            survivors.append(native_listing_id_value)
            results[native_listing_id_value] = BulkCurrentPublicEligibility(
                eligibility=CurrentPublicEligibilityResult(
                    native_listing_id_value=native_listing_id_value,
                    status=CurrentPublicEligibilityStatus.ELIGIBLE,
                    suppression_reasons=frozenset(),
                ),
                freshness=freshness,
            )

    # Survivors only: the expensive, unchanged per-candidate reads, and the
    # identical pure evaluator used by the single-id function above --
    # byte-for-byte the same final decision a per-listing call would reach.
    for native_listing_id_value in survivors:
        org_id, episode_id, lifecycle_raw = listing_facts[native_listing_id_value]
        assert episode_id is not None
        physical_boat_id_value = episode_to_boat[episode_id]
        native_listing_id = NativeListingId(native_listing_id_value)

        offer_record = fetch_current_native_listing_offer(conn, native_listing_id)
        offer = offer_record.offer if offer_record is not None else None

        claim_record = fetch_current_physical_boat_claim(
            conn,
            PhysicalBoatId(physical_boat_id_value),
            MarketplaceOrganizationId(org_id),
        )
        physical_boat_claim = claim_record.claims if claim_record is not None else None

        has_public_usable_image, cover_state = resolve_cover_state_and_image_presence(
            conn, native_listing_id
        )

        facts = CurrentPublicEligibilityFacts(
            native_listing_id_value=native_listing_id_value,
            lifecycle_state=NativeListingLifecycleState(lifecycle_raw),
            freshness_status=results[native_listing_id_value].freshness.status,
            organization_exists=org_id in org_eligibility,
            organization_publishing_eligibility=org_eligibility.get(org_id),
            market_episode_id_present=True,
            market_episode_exists=True,
            physical_boat_exists=True,
            offer=offer,
            physical_boat_claim=physical_boat_claim,
            has_public_usable_image=has_public_usable_image,
            cover_state=_COVER_STATE_MAP[cover_state],
        )
        results[native_listing_id_value] = BulkCurrentPublicEligibility(
            eligibility=evaluate_current_public_eligibility(facts),
            freshness=results[native_listing_id_value].freshness,
        )

    return results
