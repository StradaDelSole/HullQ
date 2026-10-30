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
`Decimal`, never a binary float (slice item B). `draft_max` flows through the
design-level eligibility check as the same exact `Decimal` (amendment
review Finding 2) -- it is never coerced to `float`.

`compatible_boat_design_ids` now consults durable `FieldResolution` records
(`hullq.persistence.field_resolution`, SLICE-0051 FieldResolution blocker
amendment) rather than treating raw persisted BoatDesign JSON as
self-authorizing confirmed Search truth -- see
`hullq.search.draft_max_design_bridge`'s module docstring for the exact
qualification rule.

`CONFIRMED_MATCH` is the only primary result set. `CONFIRMED_NON_MATCH` is
counted (its deterministic classification must be provable — slice item H)
but never returned as a listing identity: nothing downstream needs one. A
listing whose PhysicalBoat lacks a durable BoatDesignRef, or whose
BoatDesignRef is not itself a design-level `CONFIRMED_MATCH`, is never a
candidate at all -- it never enters this classification and is not counted
in any surface (slice Required Behavior §3: "concrete shallow draft without
durable applicable design identity -> never confirmed through fuzzy
inference").

SLICE-0069 narrows the candidate set further, before any technical
`draft_max` classification: an ACTIVE listing that is not canonically
current-public eligible (`hullq.application.current_public_eligibility` --
D29, superseding the SLICE-0052 §7.2 freshness-only narrowing) is excluded
outright. That exclusion is current-public admission, never technical
`draft_max` truth, so it is not counted as `INSUFFICIENT_DATA`. A
`DUE_FOR_CONFIRMATION` listing may still be CONFIRMED_MATCH; every returned
match carries its freshness status and effective `last_confirmed_at` so the
web surface can disclose the due state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from hullq.application.current_public_eligibility import (
    resolve_current_public_eligibility,
    resolve_current_public_eligibility_for_many,
)
from hullq.application.native_inventory_query import (
    DEFAULT_CANDIDATE_SCAN_BUDGET,
    DEFAULT_REQUEST_DEADLINE_SECONDS,
    PublisherClaimCandidateEvaluation,
    SearchPageEvaluationState,
    build_mixed_requirement_query,
    check_request_deadline,
    classify_claim_only_page_candidate,
    evaluate_claim_only_candidates,
)
from hullq.application.native_listing_freshness import CurrentFreshness, resolve_current_freshness
from hullq.application.vessel_category_resolution import resolve_physical_boat_vessel_category
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.physical_boat_claims import AssertionKind
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.inventory_search import (
    ActiveDesignLinkedListing,
    ActiveNativeListingCandidate,
    active_native_listing_candidate_exists_after,
    list_active_design_linked_listings,
    list_active_native_listing_candidates_page,
)
from hullq.persistence.physical_boat_claims import (
    list_current_draft_observations_for_physical_boat,
    list_current_physical_boat_claim_observations_for_many,
)
from hullq.search.draft_max_design_bridge import compatible_boat_design_ids

__all__ = [
    "DraftMaxConfirmedMatch",
    "DraftMaxSearchOutcome",
    "DraftMaxSearchResultPage",
    "evaluate_draft_max_requirement",
    "evaluate_draft_max_requirement_page",
]


@dataclass(frozen=True, slots=True)
class DraftMaxConfirmedMatch:
    """One CONFIRMED_MATCH result: a concrete offered boat confirmed to satisfy `draft_max`."""

    native_listing_id: NativeListingId
    resolved_draft_m: Decimal
    publishing_organization_id: MarketplaceOrganizationId
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class DraftMaxSearchOutcome:
    """Separated result surfaces for one `draft_max` requirement evaluation.

    `confirmed_matches` is the only primary result set/count. `insufficient_data_count`
    is a separate discovery surface, never presented as a match.
    `confirmed_non_match_count` is counted for testability only (slice item H:
    "its deterministic classification must be tested") and carries no listing
    identity.

    SLICE-0092: `claim_only_matches`/`claim_only_non_matches`/
    `claim_only_insufficient_data` are the entirely separate, additive
    design-unresolved publisher-claim result surfaces for this same pure
    `draft_max` requirement (contract §F: "wire this optional additive path
    through (i) pure draft_max"). Never merged into `confirmed_matches` and
    never affect any of the three existing design-linked counts.
    """

    draft_max: Decimal
    confirmed_matches: tuple[DraftMaxConfirmedMatch, ...]
    confirmed_non_match_count: int
    insufficient_data_count: int
    claim_only_matches: tuple[PublisherClaimCandidateEvaluation, ...] = ()
    claim_only_non_matches: tuple[PublisherClaimCandidateEvaluation, ...] = ()
    claim_only_insufficient_data: tuple[PublisherClaimCandidateEvaluation, ...] = ()

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)

    @property
    def claim_only_match_count(self) -> int:
        return len(self.claim_only_matches)


def _classify_candidate(
    conn: Any,
    candidate: ActiveDesignLinkedListing | ActiveNativeListingCandidate,
    draft_max: Decimal,
    *,
    freshness_status: FreshnessStatus,
    last_confirmed_at: datetime | None,
) -> DraftMaxConfirmedMatch | str:
    """Classify one admitted candidate. Returns a confirmed match or a literal
    `"CONFIRMED_NON_MATCH"` / `"INSUFFICIENT_DATA"` marker.

    Never backfills from BoatDesign/configuration truth (slice item F): the
    only candidate concrete value is the publishing Organization's own
    current `physical_boat.draft` claim.

    Amendment review Finding 5: the publisher's own current claim and the
    same-PhysicalBoat contradiction guard's cross-Organization observation
    set are resolved from a *single* call to
    `list_current_draft_observations_for_physical_boat` -- one SQL
    statement, therefore one consistent PostgreSQL MVCC snapshot for both --
    rather than two separate queries. Reading the publisher's claim and the
    "every current observation" set via two separate statements would let a
    concurrent claim revision, committed between them, combine a stale
    publisher value with a newer (or older) cross-Organization observation
    set, potentially producing a CONFIRMED_MATCH that was never actually
    true of any single consistent database state.
    """
    observations = list_current_draft_observations_for_physical_boat(
        conn, candidate.physical_boat_id
    )
    publisher_observation = next(
        (
            obs
            for obs in observations
            if obs.claiming_organization_id == candidate.publishing_organization_id
        ),
        None,
    )
    draft_claim = publisher_observation.draft if publisher_observation is not None else None

    if draft_claim is None or draft_claim.assertion_kind is AssertionKind.UNKNOWN:
        return "INSUFFICIENT_DATA"

    assert draft_claim.assertion_kind is AssertionKind.VALUE_ASSERTION
    assert draft_claim.value is not None

    # Same-PhysicalBoat contradiction guard (Option B, slice item G): every
    # claiming Organization's current admissible (VALUE_ASSERTION) draft
    # observation for this exact PhysicalBoatId, including the publisher's
    # own, drawn from the identical single-query result read above.
    # Semantically equivalent current values (exact Decimal equality) never
    # conflict; UNKNOWN/omitted observations never manufacture one; more
    # than one distinct current value blocks confirmation.
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
            freshness_status=freshness_status,
            last_confirmed_at=last_confirmed_at,
        )
    return "CONFIRMED_NON_MATCH"


def evaluate_draft_max_requirement(
    conn: Any, draft_max: Decimal, *, as_of: datetime
) -> DraftMaxSearchOutcome:
    """Evaluate the complete bounded `draft_max` vertical against real persisted state.

    *draft_max* must already be an exact positive finite `Decimal` (see
    `hullq.search.draft_max_request.parse_draft_max_decimal`) -- this function
    performs no additional parsing/canonicalization.

    SLICE-0052 contract §7.2: every ACTIVE design-linked candidate is
    freshness-resolved at the explicit *as_of* boundary before any technical
    classification. STALE/UNKNOWN candidates are excluded outright -- never
    counted as `insufficient_data_count`, since their exclusion is inventory
    freshness, not missing `draft_max` truth.
    """
    if not isinstance(draft_max, Decimal) or not draft_max.is_finite() or draft_max <= 0:
        raise ValueError(f"draft_max must be a positive finite Decimal; got {draft_max!r}")

    # SLICE-0092 contract §F: the new design-unresolved claim-only Sail path
    # is evaluated unconditionally for this same pure draft_max requirement,
    # independent of whether any design-linked candidate exists at all --
    # reusing the identical claim-only evaluator the mixed nine-criterion
    # funnel uses (`evaluate_native_inventory_requirements`), never a second
    # independently maintained claim-only funnel. `build_mixed_requirement_query`
    # with only `draft_max` active produces the identical single-leaf query/
    # definition the shared MUST/AND kernel expects.
    claim_only_query, claim_only_definitions = build_mixed_requirement_query(
        draft_max=draft_max, keel_configuration=None
    )
    claim_only_matches, claim_only_non_matches, claim_only_insufficient_data = (
        evaluate_claim_only_candidates(
            conn, query=claim_only_query, active_definitions=claim_only_definitions, as_of=as_of
        )
    )

    all_candidates = list_active_design_linked_listings(conn)
    if not all_candidates:
        return DraftMaxSearchOutcome(
            draft_max=draft_max,
            confirmed_matches=(),
            confirmed_non_match_count=0,
            insufficient_data_count=0,
            claim_only_matches=claim_only_matches,
            claim_only_non_matches=claim_only_non_matches,
            claim_only_insufficient_data=claim_only_insufficient_data,
        )

    current_candidates = []
    for candidate in all_candidates:
        eligibility = resolve_current_public_eligibility(
            conn, candidate.native_listing_id, as_of=as_of
        )
        if eligibility is None or eligibility.status is not CurrentPublicEligibilityStatus.ELIGIBLE:
            continue
        freshness = resolve_current_freshness(conn, candidate.native_listing_id, as_of=as_of)
        current_candidates.append((candidate, freshness))

    if not current_candidates:
        return DraftMaxSearchOutcome(
            draft_max=draft_max,
            confirmed_matches=(),
            confirmed_non_match_count=0,
            insufficient_data_count=0,
            claim_only_matches=claim_only_matches,
            claim_only_non_matches=claim_only_non_matches,
            claim_only_insufficient_data=claim_only_insufficient_data,
        )

    distinct_design_ids = sorted({c.boat_design_ref.value for c, _ in current_candidates})
    boat_designs = []
    for design_id in distinct_design_ids:
        raw_design = fetch_boat_design(conn, design_id)
        if raw_design is not None:
            boat_designs.append(raw_design)

    # Amendment review Finding 2: pass the exact Decimal requirement through
    # unchanged -- never coerce to float before design/configuration
    # eligibility, which could silently change an accepted exact buyer
    # threshold or overflow/underflow for an otherwise-valid accepted
    # arbitrary-precision Decimal spelling.
    compatible_ids = compatible_boat_design_ids(conn, draft_max, boat_designs)

    confirmed_matches: list[DraftMaxConfirmedMatch] = []
    confirmed_non_match_count = 0
    insufficient_data_count = 0

    for candidate, freshness in current_candidates:
        if candidate.boat_design_ref.value not in compatible_ids:
            continue
        # SLICE-0091 amendment Finding A: this pure draft_max funnel is a
        # second Sail entrypoint distinct from
        # hullq.application.native_inventory_query -- the fail-closed
        # category pre-filter must be applied here too, or an explicit
        # POWER/MOTORSAILER/CONFLICT vessel could still surface as a
        # confirmed Sail match through this unmodified SLICE-0051 path.
        # UNKNOWN (including every legacy null-category row) is untouched,
        # preserving accepted SLICE-0051 behavior exactly.
        category_resolution = resolve_physical_boat_vessel_category(
            conn,
            physical_boat_id=candidate.physical_boat_id,
            boat_design_ref=candidate.boat_design_ref,
        )
        if category_resolution.is_explicitly_non_sail_or_conflicted:
            confirmed_non_match_count += 1
            continue
        result = _classify_candidate(
            conn,
            candidate,
            draft_max,
            freshness_status=freshness.status,
            last_confirmed_at=freshness.last_confirmed_at,
        )
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
        claim_only_matches=claim_only_matches,
        claim_only_non_matches=claim_only_non_matches,
        claim_only_insufficient_data=claim_only_insufficient_data,
    )


@dataclass(frozen=True, slots=True)
class DraftMaxSearchResultPage:
    """One bounded page of the PURE `draft_max`-only vertical -- SLICE-0096.

    Deliberately a SEPARATE bounded evaluator/type from
    `hullq.application.native_inventory_query.NativeInventorySearchResultPage`,
    not a special case of it. A real-PG18 regression proof during this
    slice's own implementation showed the two pure-draft/mixed design-linked
    exclusion rules are NOT byte-identical: this module's own
    `compatible_boat_design_ids` treats a BoatDesign with no durably admitted
    `draft_max` FieldResolution as EXCLUDED (never a candidate at all --
    Required Behavior §3's "concrete shallow draft without durable
    applicable design identity -> never confirmed through fuzzy inference"),
    while `hullq.search.boat_design_field_bridge
    .run_boat_design_configuration_query` (the kernel the mixed/mixed-
    criteria bounded page reuses) instead classifies the SAME situation as a
    design-level `INSUFFICIENT_DATA`. Reusing the generalized kernel for the
    pure-draft page would have silently turned a pre-0096 "never counted at
    all" candidate into a counted `insufficient_data_count` -- a real wire-
    visible regression this slice's own equivalence testing caught. Keeping
    this a distinct evaluator preserves the exact pre-0096
    `evaluate_draft_max_requirement` semantics (byte-for-byte reused via
    `_classify_candidate`/`compatible_boat_design_ids`) for every bounded
    page too.

    Mirrors `NativeInventorySearchResultPage`'s identical page-local counts/
    `__post_init__` PARTIAL-must-carry-cursor invariant otherwise.
    """

    draft_max: Decimal
    evaluation_state: SearchPageEvaluationState
    next_after_native_listing_id: str | None
    confirmed_matches: tuple[DraftMaxConfirmedMatch, ...]
    claim_only_matches: tuple[PublisherClaimCandidateEvaluation, ...]
    design_linked_insufficient_data_count: int
    claim_only_insufficient_data_count: int

    def __post_init__(self) -> None:
        is_partial = self.evaluation_state is SearchPageEvaluationState.PARTIAL
        if is_partial and self.next_after_native_listing_id is None:
            raise ValueError("A PARTIAL page must carry next_after_native_listing_id")
        if not is_partial and self.next_after_native_listing_id is not None:
            raise ValueError("A COMPLETE page must not carry next_after_native_listing_id")

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)

    @property
    def claim_only_match_count(self) -> int:
        return len(self.claim_only_matches)


def evaluate_draft_max_requirement_page(
    conn: Any,
    draft_max: Decimal,
    *,
    as_of: datetime,
    after_native_listing_id: str | None,
    page_size: int,
    candidate_scan_budget: int = DEFAULT_CANDIDATE_SCAN_BUDGET,
    request_deadline_seconds: float = DEFAULT_REQUEST_DEADLINE_SECONDS,
) -> DraftMaxSearchResultPage:
    """Evaluate one bounded page of the PURE `draft_max`-only vertical --
    SLICE-0096's new public entrypoint for the legacy SLICE-0051 shape. See
    `DraftMaxSearchResultPage`'s docstring for why this is a separate
    evaluator rather than a call to
    `hullq.application.native_inventory_query
    .evaluate_native_inventory_requirements_page`, and that function's own
    docstring for the shared bounded-scan/early-stop/exact-fill-lookahead
    rationale -- identical here for the OUTER paging mechanics; only the
    design-linked per-candidate classification differs.
    """
    if not isinstance(page_size, int) or isinstance(page_size, bool) or not (1 <= page_size <= 50):
        raise ValueError(f"page_size must be an int in [1, 50]; got {page_size!r}")
    if (
        not isinstance(candidate_scan_budget, int)
        or isinstance(candidate_scan_budget, bool)
        or candidate_scan_budget < 1
    ):
        raise ValueError(
            f"candidate_scan_budget must be a positive int; got {candidate_scan_budget!r}"
        )
    if (
        not isinstance(request_deadline_seconds, (int, float))
        or isinstance(request_deadline_seconds, bool)
        or request_deadline_seconds <= 0
    ):
        raise ValueError(
            f"request_deadline_seconds must be a positive number; got {request_deadline_seconds!r}"
        )

    # Finding E2 (round 2): see `hullq.application.native_inventory_query
    # .evaluate_native_inventory_requirements_page`'s identical rationale.
    deadline = time.monotonic() + request_deadline_seconds

    claim_only_query, claim_only_definitions = build_mixed_requirement_query(
        draft_max=draft_max, keel_configuration=None
    )

    batch = list_active_native_listing_candidates_page(
        conn, after_native_listing_id=after_native_listing_id, limit=candidate_scan_budget
    )
    if not batch:
        return DraftMaxSearchResultPage(
            draft_max=draft_max,
            evaluation_state=SearchPageEvaluationState.COMPLETE,
            next_after_native_listing_id=None,
            confirmed_matches=(),
            claim_only_matches=(),
            design_linked_insufficient_data_count=0,
            claim_only_insufficient_data_count=0,
        )

    bulk_eligibility = resolve_current_public_eligibility_for_many(
        conn, [candidate.native_listing_id for candidate in batch], as_of=as_of
    )
    eligible_by_id: dict[str, CurrentFreshness] = {}
    for candidate in batch:
        bulk_result = bulk_eligibility.get(candidate.native_listing_id.value)
        if (
            bulk_result is not None
            and bulk_result.eligibility.status is CurrentPublicEligibilityStatus.ELIGIBLE
        ):
            eligible_by_id[candidate.native_listing_id.value] = bulk_result.freshness

    design_linked_eligible = [
        candidate
        for candidate in batch
        if candidate.boat_design_ref is not None
        and candidate.native_listing_id.value in eligible_by_id
    ]
    claim_only_eligible = [
        candidate
        for candidate in batch
        if candidate.boat_design_ref is None and candidate.native_listing_id.value in eligible_by_id
    ]

    compatible_ids: frozenset[str] = frozenset()
    if design_linked_eligible:
        distinct_design_ids = sorted(
            {
                candidate.boat_design_ref.value
                for candidate in design_linked_eligible
                if candidate.boat_design_ref is not None
            }
        )
        boat_designs = []
        for design_id in distinct_design_ids:
            check_request_deadline(deadline)
            raw_design = fetch_boat_design(conn, design_id)
            if raw_design is not None:
                boat_designs.append(raw_design)
        compatible_ids = frozenset(compatible_boat_design_ids(conn, draft_max, boat_designs))

    claim_only_observations_by_boat: dict[Any, list[Any]] = {}
    if claim_only_eligible:
        claim_only_observations_by_boat = list_current_physical_boat_claim_observations_for_many(
            conn, [candidate.physical_boat_id for candidate in claim_only_eligible]
        )

    confirmed_matches: list[DraftMaxConfirmedMatch] = []
    claim_only_matches: list[PublisherClaimCandidateEvaluation] = []
    design_linked_insufficient_data_count = 0
    claim_only_insufficient_data_count = 0
    last_examined_id: str | None = None
    exhausted_batch = True

    for index, candidate in enumerate(batch):
        check_request_deadline(deadline)
        last_examined_id = candidate.native_listing_id.value
        freshness = eligible_by_id.get(candidate.native_listing_id.value)
        if freshness is None:
            continue

        if candidate.boat_design_ref is not None:
            # Exact pre-0096 exclusion rule (never INSUFFICIENT_DATA): see
            # DraftMaxSearchResultPage's own docstring.
            if candidate.boat_design_ref.value not in compatible_ids:
                continue
            category_resolution = resolve_physical_boat_vessel_category(
                conn,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_ref=candidate.boat_design_ref,
            )
            if category_resolution.is_explicitly_non_sail_or_conflicted:
                continue
            result = _classify_candidate(
                conn,
                candidate,
                draft_max,
                freshness_status=freshness.status,
                last_confirmed_at=freshness.last_confirmed_at,
            )
            if isinstance(result, DraftMaxConfirmedMatch):
                confirmed_matches.append(result)
            elif result != "CONFIRMED_NON_MATCH":
                design_linked_insufficient_data_count += 1
        else:
            observations = claim_only_observations_by_boat.get(candidate.physical_boat_id, [])
            claim_evaluation = classify_claim_only_page_candidate(
                candidate,
                freshness,
                query=claim_only_query,
                active_definitions=claim_only_definitions,
                observations=observations,
            )
            if claim_evaluation.result_class.value == "CONFIRMED_MATCH":
                claim_only_matches.append(claim_evaluation)
            elif claim_evaluation.result_class.value == "INSUFFICIENT_DATA":
                claim_only_insufficient_data_count += 1

        if len(confirmed_matches) + len(claim_only_matches) >= page_size:
            exhausted_batch = index == len(batch) - 1
            break

    assert last_examined_id is not None
    if exhausted_batch and len(batch) < candidate_scan_budget:
        evaluation_state = SearchPageEvaluationState.COMPLETE
        next_after_native_listing_id = None
    elif exhausted_batch:
        if active_native_listing_candidate_exists_after(conn, last_examined_id):
            evaluation_state = SearchPageEvaluationState.PARTIAL
            next_after_native_listing_id = last_examined_id
        else:
            evaluation_state = SearchPageEvaluationState.COMPLETE
            next_after_native_listing_id = None
    else:
        evaluation_state = SearchPageEvaluationState.PARTIAL
        next_after_native_listing_id = last_examined_id

    return DraftMaxSearchResultPage(
        draft_max=draft_max,
        evaluation_state=evaluation_state,
        next_after_native_listing_id=next_after_native_listing_id,
        confirmed_matches=tuple(confirmed_matches),
        claim_only_matches=tuple(claim_only_matches),
        design_linked_insufficient_data_count=design_linked_insufficient_data_count,
        claim_only_insufficient_data_count=claim_only_insufficient_data_count,
    )
