"""Requirements -> Native Inventory Search vertical — SLICE-0051.

The one production application service for this slice's bounded funnel:

    exact-Decimal draft_max requirement
    -> deterministic BoatDesign/configuration eligibility
       (hullq.search.draft_max_design_bridge, unchanged Search kernel)
    -> durable design identity admission to ACTIVE native inventory
       (hullq.persistence.inventory_search)
    -> publishing Organization's current physical_boat.draft claim
       (hullq.persistence.physical_boat_claims.fetch_current_physical_boat_claim)
    -> same-PhysicalBoat current-observation contradiction guard
       (hullq.persistence.physical_boat_claims.list_current_draft_observations_for_physical_boat)
    -> listing-level CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA

Every stage above is a separate, independently testable step (slice Required
Behavior §2: "Make these boundaries explicit in code/tests rather than
collapsing semantics into one opaque SQL predicate"). The concrete
PhysicalBoat comparison in `_classify_candidate` is exact `Decimal`-to-
`Decimal`, never a binary float (slice item B) -- unlike the design-level
eligibility check, which is the accepted legacy float-based Search kernel
path (slice item B explicitly permits this split).

`CONFIRMED_MATCH` is the only primary result set. `CONFIRMED_NON_MATCH` is
counted (its deterministic classification must be provable — slice item H)
but never returned as a listing identity: nothing downstream needs one. A
listing whose PhysicalBoat lacks a durable BoatDesignRef, or whose
BoatDesignRef is not itself a design-level `CONFIRMED_MATCH`, is never a
candidate at all -- it never enters this classification and is not counted
in any surface (slice Required Behavior §3: "concrete shallow draft without
durable applicable design identity -> never confirmed through fuzzy
inference").
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.physical_boat_claims import AssertionKind
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.inventory_search import (
    ActiveDesignLinkedListing,
    list_active_design_linked_listings,
)
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    list_current_draft_observations_for_physical_boat,
)
from hullq.search.draft_max_design_bridge import compatible_boat_design_ids

__all__ = ["DraftMaxConfirmedMatch", "DraftMaxSearchOutcome", "evaluate_draft_max_requirement"]


@dataclass(frozen=True, slots=True)
class DraftMaxConfirmedMatch:
    """One CONFIRMED_MATCH result: a concrete offered boat confirmed to satisfy `draft_max`."""

    native_listing_id: NativeListingId
    resolved_draft_m: Decimal
    publishing_organization_id: MarketplaceOrganizationId


@dataclass(frozen=True, slots=True)
class DraftMaxSearchOutcome:
    """Separated result surfaces for one `draft_max` requirement evaluation.

    `confirmed_matches` is the only primary result set/count. `insufficient_data_count`
    is a separate discovery surface, never presented as a match.
    `confirmed_non_match_count` is counted for testability only (slice item H:
    "its deterministic classification must be tested") and carries no listing
    identity.
    """

    draft_max: Decimal
    confirmed_matches: tuple[DraftMaxConfirmedMatch, ...]
    confirmed_non_match_count: int
    insufficient_data_count: int

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)


def _classify_candidate(
    conn: Any, candidate: ActiveDesignLinkedListing, draft_max: Decimal
) -> DraftMaxConfirmedMatch | str:
    """Classify one admitted candidate. Returns a confirmed match or a literal
    `"CONFIRMED_NON_MATCH"` / `"INSUFFICIENT_DATA"` marker.

    Never backfills from BoatDesign/configuration truth (slice item F): the
    only candidate concrete value is the publishing Organization's own
    current `physical_boat.draft` claim.
    """
    claim_record = fetch_current_physical_boat_claim(
        conn, candidate.physical_boat_id, candidate.publishing_organization_id
    )
    draft_claim = claim_record.claims.draft if claim_record is not None else None

    if draft_claim is None or draft_claim.assertion_kind is AssertionKind.UNKNOWN:
        return "INSUFFICIENT_DATA"

    assert draft_claim.assertion_kind is AssertionKind.VALUE_ASSERTION
    assert draft_claim.value is not None

    # Same-PhysicalBoat contradiction guard (Option B, slice item G): every
    # claiming Organization's current admissible (VALUE_ASSERTION) draft
    # observation for this exact PhysicalBoatId, including the publisher's
    # own. Semantically equivalent current values (exact Decimal equality)
    # never conflict; UNKNOWN/omitted observations never manufacture one;
    # more than one distinct current value blocks confirmation.
    observations = list_current_draft_observations_for_physical_boat(
        conn, candidate.physical_boat_id
    )
    distinct_values = {
        obs.draft.value
        for obs in observations
        if obs.draft is not None and obs.draft.assertion_kind is AssertionKind.VALUE_ASSERTION
    }
    if len(distinct_values) > 1:
        return "INSUFFICIENT_DATA"

    resolved_draft_m = draft_claim.value
    if resolved_draft_m <= draft_max:
        return DraftMaxConfirmedMatch(
            native_listing_id=candidate.native_listing_id,
            resolved_draft_m=resolved_draft_m,
            publishing_organization_id=candidate.publishing_organization_id,
        )
    return "CONFIRMED_NON_MATCH"


def evaluate_draft_max_requirement(conn: Any, draft_max: Decimal) -> DraftMaxSearchOutcome:
    """Evaluate the complete bounded `draft_max` vertical against real persisted state.

    *draft_max* must already be an exact positive finite `Decimal` (see
    `hullq.search.draft_max_request.parse_draft_max_decimal`) -- this function
    performs no additional parsing/canonicalization.
    """
    if not isinstance(draft_max, Decimal) or not draft_max.is_finite() or draft_max <= 0:
        raise ValueError(f"draft_max must be a positive finite Decimal; got {draft_max!r}")

    candidates = list_active_design_linked_listings(conn)
    if not candidates:
        return DraftMaxSearchOutcome(
            draft_max=draft_max,
            confirmed_matches=(),
            confirmed_non_match_count=0,
            insufficient_data_count=0,
        )

    distinct_design_ids = sorted({c.boat_design_ref.value for c in candidates})
    boat_designs = []
    for design_id in distinct_design_ids:
        raw_design = fetch_boat_design(conn, design_id)
        if raw_design is not None:
            boat_designs.append(raw_design)

    compatible_ids = compatible_boat_design_ids(float(draft_max), boat_designs)

    confirmed_matches: list[DraftMaxConfirmedMatch] = []
    confirmed_non_match_count = 0
    insufficient_data_count = 0

    for candidate in candidates:
        if candidate.boat_design_ref.value not in compatible_ids:
            continue
        result = _classify_candidate(conn, candidate, draft_max)
        if isinstance(result, DraftMaxConfirmedMatch):
            confirmed_matches.append(result)
        elif result == "CONFIRMED_NON_MATCH":
            confirmed_non_match_count += 1
        else:
            insufficient_data_count += 1

    confirmed_matches.sort(key=lambda m: m.native_listing_id.value)

    return DraftMaxSearchOutcome(
        draft_max=draft_max,
        confirmed_matches=tuple(confirmed_matches),
        confirmed_non_match_count=confirmed_non_match_count,
        insufficient_data_count=insufficient_data_count,
    )
