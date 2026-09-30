"""Post-promotion NativeListing offer / Organization PhysicalBoat claim
editing -- SLICE-0072.

Implements `specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md` §4-§7: an
ordinary offer/claim edit is composed directly from the already-accepted
transaction-scoped write primitives
(`hullq.persistence.native_listing_offer.write_native_listing_offer_revision_row`,
`hullq.persistence.physical_boat_claims.write_physical_boat_claim_revision_row`)
-- never a second, independently maintained offer/claim persistence path
(contract §1: "No second listing truth store is introduced.").

For a candidate resulting head that lands on an ACTIVE NativeListing, this
module additionally re-evaluates a narrowed form of the canonical D29
CurrentPublicEligibility rule set
(`hullq.domain.current_public_eligibility.evaluate_current_public_eligibility`)
-- never the D22 PublicationReadiness evaluator
(`hullq.persistence.publication_readiness.resolve_publication_readiness`):
D22 unconditionally blocks with `LIFECYCLE_NOT_DRAFT` for any non-DRAFT
listing (it is the `DRAFT -> ACTIVE` promotion gate, not an ACTIVE-state
invariant), so reusing it here would reject every ordinary edit of an
already-ACTIVE listing. D29 is evaluated here with `freshness_status`/
`cover_state`/`has_public_usable_image` fixed to their most-permissive
values -- contract §6/§8's "price change does not alter ... freshness" and
§11's "media truth remains untouched" mean neither dimension is a
*candidate resulting head* of an offer/claim edit (contract §7), and an
edit must never be rejected for a pre-existing, unrelated staleness/media
condition it did not cause. Only offer/claim presence, MarketEpisode/
PhysicalBoat chain resolution and Organization eligibility -- the
dimensions an offer/claim edit's own candidate heads can actually affect --
remain live checks.

This re-evaluation runs inside the *same* top-level transaction as the
just-applied revision write. A violation raises a private rollback
sentinel that unwinds the surrounding `with conn.transaction():` block --
discarding the just-inserted revision row and head update together,
atomically, before this module's caller ever sees them (contract §7: "must
fail atomically ... must not leave an ACTIVE listing with a knowingly
invalid current required state"). An `ALREADY_EXISTS` retry (identical
content, zero state change) skips this re-check: nothing about the
NativeListing's candidate current heads changed, so a previously-valid
ACTIVE state cannot have been made invalid by this call.

Every genuine authorization/tenancy/idempotency/conflict decision is made by
the row-writer primitives themselves, exactly once, unchanged -- this module
adds no second authorization check and no second content-fingerprint/
current-head comparison of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.domain.current_public_eligibility import (
    CurrentPublicCoverState,
    CurrentPublicEligibilityFacts,
    CurrentPublicEligibilityStatus,
    CurrentPublicSuppressionReason,
    evaluate_current_public_eligibility,
)
from hullq.domain.market_identity import MarketEpisodeId, NativeListingId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import (
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
)
from hullq.domain.physical_boat_claims import PhysicalBoatClaimRevisionId, PhysicalBoatClaimSnapshot
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.broker_identity import fetch_marketplace_organization
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing_offer import (
    NativeListingOfferWriteResult,
    NativeListingOfferWriteStatus,
    fetch_current_native_listing_offer,
    write_native_listing_offer_revision_row,
)
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimWriteResult,
    PhysicalBoatClaimWriteStatus,
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision_row,
)

__all__ = [
    "ClaimEditResult",
    "ClaimEditStatus",
    "InventoryEditTransactionOwnershipError",
    "OfferEditResult",
    "OfferEditStatus",
    "edit_native_listing_offer",
    "edit_physical_boat_claim",
]


class InventoryEditTransactionOwnershipError(RuntimeError):
    """An edit call cannot safely own a top-level transaction on *conn*.

    Mirrors every other write module's identical guard (e.g.
    `hullq.persistence.native_listing_offer.NativeListingOfferTransactionOwnershipError`):
    a REVISED/ALREADY_EXISTS result must always mean the new current head is
    already durably committed, independent of later caller action. That
    guarantee only holds when *conn* is IDLE. Call
    ``conn.commit()``/``conn.rollback()`` first, or pass a freshly opened
    connection.
    """


_SELECT_LIFECYCLE_AND_EPISODE = (
    "SELECT lifecycle_state, market_episode_id FROM native_listings WHERE native_listing_id = %s"
)


class _ActiveInvariantRollback(Exception):
    """Private sentinel: unwinds the surrounding `with conn.transaction():`
    block so the just-applied revision write and head advance are discarded
    together, atomically, before ever reaching this module's caller."""

    def __init__(self, blockers: frozenset[CurrentPublicSuppressionReason]) -> None:
        self.blockers = blockers


def _require_idle(conn: Any) -> None:
    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise InventoryEditTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); an inventory edit requires an IDLE connection so "
            "it can safely own and commit its own top-level transaction. Call "
            "conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )


def _fetch_lifecycle_and_episode(
    cur: Any, native_listing_id: NativeListingId
) -> tuple[NativeListingLifecycleState, str | None]:
    cur.execute(_SELECT_LIFECYCLE_AND_EPISODE, [native_listing_id.value])
    row = cur.fetchone()
    assert row is not None, "native_listings row vanished after a successful revision write"
    lifecycle_state_text, market_episode_id_value = row
    return NativeListingLifecycleState(lifecycle_state_text), market_episode_id_value


def _resolve_active_candidate_head_invariant(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    publishing_organization_id: MarketplaceOrganizationId,
    market_episode_id_value: str | None,
) -> tuple[CurrentPublicEligibilityStatus, frozenset[CurrentPublicSuppressionReason]]:
    """Contract §7's narrowed ACTIVE hard-invariant re-check -- see this
    module's docstring for why D29, not D22, and why freshness/cover/image
    are fixed to their most-permissive value rather than genuinely resolved.

    Reads only through the already-accepted fetch functions this same
    NativeListing's `native_listings` row lock (held by the caller's
    surrounding transaction) already serializes every concurrent offer/
    claim/gallery writer against -- mirrors
    `hullq.persistence.publication_readiness.resolve_publication_readiness`'s
    identical concurrency argument.
    """
    organization = fetch_marketplace_organization(conn, publishing_organization_id)

    market_episode_exists = False
    physical_boat_exists = False
    physical_boat_claim = None
    if market_episode_id_value is not None:
        market_episode_record = fetch_market_episode(conn, MarketEpisodeId(market_episode_id_value))
        if market_episode_record is not None:
            market_episode_exists = True
            physical_boat_id = market_episode_record.market_episode.physical_boat_id
            physical_boat_exists = fetch_physical_boat(conn, physical_boat_id) is not None
            if physical_boat_exists:
                claim_record = fetch_current_physical_boat_claim(
                    conn, physical_boat_id, publishing_organization_id
                )
                physical_boat_claim = claim_record.claims if claim_record is not None else None

    offer_record = fetch_current_native_listing_offer(conn, native_listing_id)
    offer = offer_record.offer if offer_record is not None else None

    facts = CurrentPublicEligibilityFacts(
        native_listing_id_value=native_listing_id.value,
        lifecycle_state=NativeListingLifecycleState.ACTIVE,
        freshness_status=FreshnessStatus.CONFIRMED,
        organization_exists=organization is not None,
        organization_publishing_eligibility=(
            organization.publishing_eligibility if organization is not None else None
        ),
        market_episode_id_present=market_episode_id_value is not None,
        market_episode_exists=market_episode_exists,
        physical_boat_exists=physical_boat_exists,
        offer=offer,
        physical_boat_claim=physical_boat_claim,
        has_public_usable_image=True,
        cover_state=CurrentPublicCoverState.VALID,
    )
    result = evaluate_current_public_eligibility(facts)
    return result.status, result.suppression_reasons


# ---------------------------------------------------------------------------
# NativeListing offer edit
# ---------------------------------------------------------------------------


class OfferEditStatus(StrEnum):
    """Mechanically distinct offer-edit outcomes. Never a bare boolean."""

    REVISED = "revised"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    DENIED = "denied"
    CROSS_ORGANIZATION_DENIED = "cross_organization_denied"
    NATIVE_LISTING_NOT_FOUND = "native_listing_not_found"
    ACTIVE_INVARIANT_VIOLATION = "active_invariant_violation"


_OFFER_STATUSES_REQUIRING_CURRENT_REVISION = frozenset(
    {OfferEditStatus.REVISED, OfferEditStatus.ALREADY_EXISTS}
)
_OFFER_STATUSES_FORBIDDING_CURRENT_REVISION = frozenset(
    {
        OfferEditStatus.DENIED,
        OfferEditStatus.CROSS_ORGANIZATION_DENIED,
        OfferEditStatus.NATIVE_LISTING_NOT_FOUND,
        OfferEditStatus.ACTIVE_INVARIANT_VIOLATION,
    }
)


@dataclass(frozen=True)
class OfferEditResult:
    """Deterministic result of one offer-edit attempt.

    `DENIED` always carries the real SLICE-0041 denial reason.
    `ACTIVE_INVARIANT_VIOLATION` always carries the narrowed deterministic
    `CurrentPublicSuppressionReason` set the in-transaction D29 re-evaluation
    produced -- the candidate revision was already rolled back by the time
    the caller observes this, so `current_revision_id` is never populated
    here (the prior current head is unaffected; re-read authoritative state
    to observe it, contract §5).
    """

    status: OfferEditStatus
    denial_reason: PublishingEligibilityReason | None = None
    current_revision_id: NativeListingOfferRevisionId | None = None
    blockers: frozenset[CurrentPublicSuppressionReason] | None = None

    def __post_init__(self) -> None:
        if self.status is OfferEditStatus.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED offer edit result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED offer edit result may carry a denial reason")

        if self.status in _OFFER_STATUSES_REQUIRING_CURRENT_REVISION:
            if self.current_revision_id is None:
                raise ValueError(
                    f"A {self.status.value.upper()} offer edit result must carry current_revision_id"
                )
        elif (
            self.status in _OFFER_STATUSES_FORBIDDING_CURRENT_REVISION
            and self.current_revision_id is not None
        ):
            raise ValueError(
                f"A {self.status.value.upper()} offer edit result must not carry current_revision_id"
            )

        if self.status is OfferEditStatus.ACTIVE_INVARIANT_VIOLATION:
            if not self.blockers:
                raise ValueError(
                    "An ACTIVE_INVARIANT_VIOLATION offer edit result must carry at least one blocker"
                )
        elif self.blockers is not None:
            raise ValueError(
                "Only an ACTIVE_INVARIANT_VIOLATION offer edit result may carry blockers"
            )


def _map_offer_write_result(result: NativeListingOfferWriteResult) -> OfferEditResult:
    if result.status is NativeListingOfferWriteStatus.CROSS_ORGANIZATION_DENIED:
        return OfferEditResult(status=OfferEditStatus.CROSS_ORGANIZATION_DENIED)
    if result.status is NativeListingOfferWriteStatus.NATIVE_LISTING_NOT_FOUND:
        return OfferEditResult(status=OfferEditStatus.NATIVE_LISTING_NOT_FOUND)
    if result.status is NativeListingOfferWriteStatus.CONFLICT:
        return OfferEditResult(
            status=OfferEditStatus.CONFLICT, current_revision_id=result.current_revision_id
        )
    if result.status is NativeListingOfferWriteStatus.ALREADY_EXISTS:
        assert result.current_revision_id is not None
        return OfferEditResult(
            status=OfferEditStatus.ALREADY_EXISTS, current_revision_id=result.current_revision_id
        )
    assert result.status in (
        NativeListingOfferWriteStatus.CREATED,
        NativeListingOfferWriteStatus.REVISED,
    )
    assert result.current_revision_id is not None
    return OfferEditResult(
        status=OfferEditStatus.REVISED, current_revision_id=result.current_revision_id
    )


def edit_native_listing_offer(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
    revision_id: NativeListingOfferRevisionId,
    expected_current_revision_id: NativeListingOfferRevisionId | None,
    offer: NativeListingOfferSnapshot,
) -> OfferEditResult:
    """Apply one ordinary NativeListing offer revision, atomically rejecting
    an ACTIVE candidate result that would violate a hard D29 requirement.

    Raises InventoryEditTransactionOwnershipError, before any read/write is
    attempted, if *conn* already has an open transaction.
    """
    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return OfferEditResult(status=OfferEditStatus.DENIED, denial_reason=decision.reason)

    _require_idle(conn)

    try:
        with conn.transaction(), conn.cursor() as cur:
            write_result = write_native_listing_offer_revision_row(
                cur,
                account_id=account_id,
                candidate_organization=candidate_organization,
                native_listing_id=native_listing_id,
                revision_id=revision_id,
                expected_current_revision_id=expected_current_revision_id,
                offer=offer,
            )
            if write_result.status not in (
                NativeListingOfferWriteStatus.CREATED,
                NativeListingOfferWriteStatus.REVISED,
            ):
                return _map_offer_write_result(write_result)

            lifecycle_state, market_episode_id_value = _fetch_lifecycle_and_episode(
                cur, native_listing_id
            )
            if lifecycle_state is NativeListingLifecycleState.ACTIVE:
                status, blockers = _resolve_active_candidate_head_invariant(
                    conn,
                    native_listing_id=native_listing_id,
                    publishing_organization_id=candidate_organization.id,
                    market_episode_id_value=market_episode_id_value,
                )
                if status is not CurrentPublicEligibilityStatus.ELIGIBLE:
                    raise _ActiveInvariantRollback(blockers)

            return _map_offer_write_result(write_result)
    except _ActiveInvariantRollback as rollback:
        return OfferEditResult(
            status=OfferEditStatus.ACTIVE_INVARIANT_VIOLATION, blockers=rollback.blockers
        )


# ---------------------------------------------------------------------------
# Organization PhysicalBoat claim edit
# ---------------------------------------------------------------------------


class ClaimEditStatus(StrEnum):
    """Mechanically distinct claim-edit outcomes. Never a bare boolean."""

    REVISED = "revised"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    DENIED = "denied"
    CROSS_ORGANIZATION_DENIED = "cross_organization_denied"
    NATIVE_LISTING_NOT_FOUND = "native_listing_not_found"
    CHAIN_INCOMPLETE = "chain_incomplete"
    ACTIVE_INVARIANT_VIOLATION = "active_invariant_violation"


_CLAIM_STATUSES_REQUIRING_CURRENT_REVISION = frozenset(
    {ClaimEditStatus.REVISED, ClaimEditStatus.ALREADY_EXISTS}
)
_CLAIM_STATUSES_FORBIDDING_CURRENT_REVISION = frozenset(
    {
        ClaimEditStatus.DENIED,
        ClaimEditStatus.CROSS_ORGANIZATION_DENIED,
        ClaimEditStatus.NATIVE_LISTING_NOT_FOUND,
        ClaimEditStatus.CHAIN_INCOMPLETE,
        ClaimEditStatus.ACTIVE_INVARIANT_VIOLATION,
    }
)


@dataclass(frozen=True)
class ClaimEditResult:
    """Deterministic result of one PhysicalBoat claim-edit attempt.

    Mirrors `OfferEditResult` field-for-field; see that class's docstring.
    """

    status: ClaimEditStatus
    denial_reason: PublishingEligibilityReason | None = None
    current_revision_id: PhysicalBoatClaimRevisionId | None = None
    blockers: frozenset[CurrentPublicSuppressionReason] | None = None

    def __post_init__(self) -> None:
        if self.status is ClaimEditStatus.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED claim edit result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED claim edit result may carry a denial reason")

        if self.status in _CLAIM_STATUSES_REQUIRING_CURRENT_REVISION:
            if self.current_revision_id is None:
                raise ValueError(
                    f"A {self.status.value.upper()} claim edit result must carry current_revision_id"
                )
        elif (
            self.status in _CLAIM_STATUSES_FORBIDDING_CURRENT_REVISION
            and self.current_revision_id is not None
        ):
            raise ValueError(
                f"A {self.status.value.upper()} claim edit result must not carry current_revision_id"
            )

        if self.status is ClaimEditStatus.ACTIVE_INVARIANT_VIOLATION:
            if not self.blockers:
                raise ValueError(
                    "An ACTIVE_INVARIANT_VIOLATION claim edit result must carry at least one blocker"
                )
        elif self.blockers is not None:
            raise ValueError(
                "Only an ACTIVE_INVARIANT_VIOLATION claim edit result may carry blockers"
            )


def _map_claim_write_result(result: PhysicalBoatClaimWriteResult) -> ClaimEditResult:
    if result.status is PhysicalBoatClaimWriteStatus.CROSS_ORGANIZATION_DENIED:
        return ClaimEditResult(status=ClaimEditStatus.CROSS_ORGANIZATION_DENIED)
    if result.status is PhysicalBoatClaimWriteStatus.NATIVE_LISTING_NOT_FOUND:
        return ClaimEditResult(status=ClaimEditStatus.NATIVE_LISTING_NOT_FOUND)
    if result.status is PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE:
        return ClaimEditResult(status=ClaimEditStatus.CHAIN_INCOMPLETE)
    if result.status is PhysicalBoatClaimWriteStatus.CONFLICT:
        return ClaimEditResult(
            status=ClaimEditStatus.CONFLICT, current_revision_id=result.current_revision_id
        )
    if result.status is PhysicalBoatClaimWriteStatus.ALREADY_EXISTS:
        assert result.current_revision_id is not None
        return ClaimEditResult(
            status=ClaimEditStatus.ALREADY_EXISTS, current_revision_id=result.current_revision_id
        )
    assert result.status in (
        PhysicalBoatClaimWriteStatus.CREATED,
        PhysicalBoatClaimWriteStatus.REVISED,
    )
    assert result.current_revision_id is not None
    return ClaimEditResult(
        status=ClaimEditStatus.REVISED, current_revision_id=result.current_revision_id
    )


def edit_physical_boat_claim(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
    revision_id: PhysicalBoatClaimRevisionId,
    expected_current_revision_id: PhysicalBoatClaimRevisionId | None,
    claims: PhysicalBoatClaimSnapshot,
) -> ClaimEditResult:
    """Apply one ordinary Organization PhysicalBoat claim revision, atomically
    rejecting an ACTIVE candidate result that would violate a hard D29
    requirement.

    A valid technical claim change may legitimately change deterministic
    Search match/non-match/insufficient-data outcomes (contract §7) --
    that is never itself a blocker here and is not evaluated by this
    narrowed re-check; Search continues reading the newly current claim head
    through its own existing paths on its own next read.

    Raises InventoryEditTransactionOwnershipError, before any read/write is
    attempted, if *conn* already has an open transaction.
    """
    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return ClaimEditResult(status=ClaimEditStatus.DENIED, denial_reason=decision.reason)

    _require_idle(conn)

    try:
        with conn.transaction(), conn.cursor() as cur:
            write_result = write_physical_boat_claim_revision_row(
                cur,
                account_id=account_id,
                candidate_organization=candidate_organization,
                native_listing_id=native_listing_id,
                revision_id=revision_id,
                expected_current_revision_id=expected_current_revision_id,
                claims=claims,
            )
            if write_result.status not in (
                PhysicalBoatClaimWriteStatus.CREATED,
                PhysicalBoatClaimWriteStatus.REVISED,
            ):
                return _map_claim_write_result(write_result)

            lifecycle_state, market_episode_id_value = _fetch_lifecycle_and_episode(
                cur, native_listing_id
            )
            if lifecycle_state is NativeListingLifecycleState.ACTIVE:
                status, blockers = _resolve_active_candidate_head_invariant(
                    conn,
                    native_listing_id=native_listing_id,
                    publishing_organization_id=candidate_organization.id,
                    market_episode_id_value=market_episode_id_value,
                )
                if status is not CurrentPublicEligibilityStatus.ELIGIBLE:
                    raise _ActiveInvariantRollback(blockers)

            return _map_claim_write_result(write_result)
    except _ActiveInvariantRollback as rollback:
        return ClaimEditResult(
            status=ClaimEditStatus.ACTIVE_INVARIANT_VIOLATION, blockers=rollback.blockers
        )
