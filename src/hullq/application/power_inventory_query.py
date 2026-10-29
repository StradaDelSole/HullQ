"""Power-domain Requirements -> Native Inventory Search vertical — SLICE-0093,
extended SLICE-0094.

The two accepted Power hard technical criteria, `power_drive_configuration`
(`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`) and
`power_engine_count` (`specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md`).
This module is the Power-domain counterpart of
`hullq.application.native_inventory_query`, reusing its genuinely
category-neutral shared kernel directly rather than re-implementing it
(Trigger Gates "Second-criterion bridge comparison" / "Third-copy
abstraction guard": COMMON STRUCTURE GENERALIZED / REUSED):

    `classify_concrete_candidate` / `classify_claim_only_candidate` --
        already generic over any `Sequence[CriterionDefinition]` and any
        `MixedAndQuery`, never Sail-specific in their own signatures;
    `SearchCriterionEvidence` / `ConfigurationEvidence` / `build_configuration_evidence` --
        the same typed evidence wrappers, unmodified;
    `PublisherClaimSourceBasis` / `PublisherClaimSourceEvidence` --
        the same `PUBLISHER_CLAIM` source-basis discriminator and internal
        provenance shape;
    `hullq.application.native_inventory_query
    .run_mixed_boat_design_configuration_query` (SLICE-0094; itself a thin
    per-`CriterionDefinition.design_set_builder` + merge wrapper over
    `hullq.search.boat_design_field_bridge.run_boat_design_configuration_query`) --
        the identical shared BoatDesign/NamedVariant evaluation bridge, fed
        each active criterion's own `FieldProjectionSpec`
        (`hullq.search.power_drive_design_bridge`,
        `hullq.search.power_engine_count_design_bridge`);
    `hullq.persistence.inventory_search.list_active_design_linked_listings` /
    `list_active_design_unresolved_listings`,
    `hullq.application.current_public_eligibility
    .resolve_current_public_eligibility_for_many`,
    `hullq.persistence.physical_boat_claims
    .list_current_physical_boat_claim_observations_for_many` --
        the identical batched D29/claim-observation read primitives SLICE-0092
        established, unmodified;
    `hullq.domain.vessel_category.resolve_vessel_category` --
        the identical pure category-resolution combination step.

What is genuinely new here (never borrowed from the Sail path): the
publisher-owned-**POWER** admission precondition (the mirror image of the
Sail path's publisher-owned-SAIL precondition -- a different positive
category, so a distinct, narrow predicate), and `PowerCategoryExclusionEvidence`
(the Sail path's own `VesselCategoryExclusionEvidence` is hard-validated to
POWER/MOTORSAILER/CONFLICT only -- the exact *opposite* explicit-exclusion
set a Power admission needs, SAIL/MOTORSAILER/CONFLICT, so it cannot be
reused as-is without weakening its own invariant).

SLICE-0094 adds `power_engine_count` as a genuine second Power criterion,
combinable with `power_drive_configuration` as MUST-AND on the same
publisher current claim revision/resolved configuration
(`build_power_query`, `evaluate_power_requirement`). The unmodified
SLICE-0093 `evaluate_power_drive_requirement`/`build_power_drive_query`/
`_ACTIVE_POWER_DEFINITIONS` remain byte-for-byte unchanged and are the exact
code path a pure `power_drive`-only request still uses -- never a second,
independently-timed equivalent for that case.

Existing Sail funnels (`evaluate_native_inventory_requirements`,
`evaluate_draft_max_requirement`, `evaluate_claim_only_candidates`) are never
called, imported-and-mutated or altered by this module. No `power_drive`/
`power_engine_count` query key is ever accepted by the Sail parser, and no
Sail key is ever accepted here (`hullq.application.power_search_read` owns
that boundary).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from hullq.application.current_public_eligibility import (
    resolve_current_public_eligibility_for_many,
)
from hullq.application.native_inventory_query import (
    DEFAULT_CANDIDATE_SCAN_BUDGET,
    ConfigurationEvidence,
    PublisherClaimSourceBasis,
    PublisherClaimSourceEvidence,
    SearchCriterionEvidence,
    SearchPageEvaluationState,
    build_configuration_evidence,
    classify_claim_only_candidate,
    classify_concrete_candidate,
    run_mixed_boat_design_configuration_query,
)
from hullq.application.native_listing_freshness import CurrentFreshness
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.physical_boat_claims import AssertionKind, PowerDriveConfiguration, VesselCategory
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.domain.vessel_category import (
    ConcreteVesselCategoryEvidence,
    VesselCategoryResolution,
    VesselCategoryResolutionReason,
    VesselCategoryResolutionResult,
    resolve_vessel_category,
)
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.inventory_search import (
    ActiveDesignLinkedListing,
    ActiveDesignUnresolvedListing,
    ActiveNativeListingCandidate,
    active_native_listing_candidate_exists_after,
    list_active_design_linked_listings,
    list_active_design_unresolved_listings,
    list_active_native_listing_candidates_page,
)
from hullq.persistence.physical_boat_claims import (
    CurrentPhysicalBoatClaimObservation,
    list_current_physical_boat_claim_observations_for_many,
)
from hullq.persistence.power_category_drive_snapshot import fetch_power_category_drive_snapshot
from hullq.search.configuration import ResolvedConfiguration
from hullq.search.configuration_engine import DesignQueryEvaluation
from hullq.search.criteria import (
    CategoricalLeafCriterion,
    CriterionEvaluation,
    NumericLeafCriterion,
)
from hullq.search.criteria_registry import CriterionDefinition
from hullq.search.power_criteria_registry import (
    POWER_DRIVE_CONFIGURATION_DEFINITION,
    POWER_ENGINE_COUNT_DEFINITION,
    SEARCH_POWER_DRIVE_VALUES,
)
from hullq.search.query import and_reduce, result_class_for
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import NumericComparisonKind, ReasonCode, ResultClass, TruthState

__all__ = [
    "PowerCategoryExclusionEvidence",
    "PowerClaimOnlyMatch",
    "PowerDesignLinkedMatch",
    "PowerSearchOutcome",
    "PowerSearchResultPage",
    "build_power_drive_query",
    "build_power_query",
    "downgrade_mixed_non_match_to_insufficient_data",
    "evaluate_power_drive_requirement",
    "evaluate_power_requirement",
    "evaluate_power_requirement_page",
    "resolve_power_category_admission",
    "resolve_power_claim_only_category_from_observations",
]

#: Exactly one active Power `CriterionDefinition` -- Power domain ordinal 1.
#: SLICE-0094: this fixed one-definition tuple remains the exact default for
#: `evaluate_power_claim_only_candidates`/`evaluate_power_design_linked_candidates`
#: below, so the unmodified `evaluate_power_drive_requirement` entrypoint
#: (SLICE-0093, byte-for-byte unchanged) keeps calling them with the
#: identical active-definition set and therefore produces identical results
#: (contract acceptance criterion: "old 0093 drive-only Search returns
#: identical results"). A request involving `power_engine_count` passes its
#: own wider `active_definitions` tuple explicitly (see `build_power_query`/
#: `evaluate_power_requirement`).
_ACTIVE_POWER_DEFINITIONS: Final[tuple[CriterionDefinition, ...]] = (
    POWER_DRIVE_CONFIGURATION_DEFINITION,
)

#: The explicit non-POWER resolutions a Power admission can be excluded by --
#: the mirror image of the Sail path's own POWER/MOTORSAILER/CONFLICT set.
_EXPLICITLY_NON_POWER: Final = frozenset(
    {
        VesselCategoryResolution.SAIL,
        VesselCategoryResolution.MOTORSAILER,
        VesselCategoryResolution.CONFLICT,
    }
)


def build_power_drive_query(power_drive: str) -> MixedAndQuery:
    """Build the one-leaf `MixedAndQuery` for *power_drive*.

    *power_drive* must already be one of `SEARCH_POWER_DRIVE_VALUES` (public
    syntax validation is `hullq.application.power_search_read`'s job, not
    re-done here -- mirrors `hullq.application.native_inventory_query
    .build_mixed_requirement_query`'s identical division of labor).
    """
    if power_drive not in SEARCH_POWER_DRIVE_VALUES:
        raise ValueError(
            f"power_drive must be one of {sorted(SEARCH_POWER_DRIVE_VALUES)}; got {power_drive!r}"
        )
    return MixedAndQuery(
        criteria=(
            CategoricalLeafCriterion(
                field=POWER_DRIVE_CONFIGURATION_DEFINITION.projection_field, equals=power_drive
            ),
        )
    )


def build_power_query(
    *, power_drive: str | None, power_engine_count: Decimal | None
) -> tuple[MixedAndQuery, tuple[CriterionDefinition, ...]]:
    """Validate and build the bounded two-criterion Power `MixedAndQuery` +
    the exact active `CriterionDefinition`s it uses -- SLICE-0094.

    Mirrors `hullq.application.native_inventory_query
    .build_mixed_requirement_query`'s identical division of labor: at least
    one of *power_drive*/*power_engine_count* must be supplied, each value
    is already parsed/validated for public syntax by its own accepted
    parser (`hullq.application.power_search_read`), and this function only
    re-checks membership/shape as a defensive invariant, never re-parses.
    `power_engine_count` builds one exact numeric `RANGE` leaf with
    `threshold_min == threshold_max` -- the contract's own words: "The count
    filter uses an exact numeric RANGE with threshold_min=threshold_max, so
    the common kernel is reused ... without another count scorer".

    Returned `active_definitions` is exactly the ordered tuple of
    definitions this query's leaves need -- a request for `power_drive`
    alone builds the identical one-element tuple
    `evaluate_power_drive_requirement`'s own `_ACTIVE_POWER_DEFINITIONS`
    constant already uses, so a caller combining both entrypoints never
    observes two different "active definitions for drive-only" values.
    """
    if power_drive is None and power_engine_count is None:
        raise ValueError("at least one of power_drive/power_engine_count must be supplied")
    if power_drive is not None and power_drive not in SEARCH_POWER_DRIVE_VALUES:
        raise ValueError(
            f"power_drive must be one of {sorted(SEARCH_POWER_DRIVE_VALUES)}; got {power_drive!r}"
        )
    if power_engine_count is not None and (
        not isinstance(power_engine_count, Decimal)
        or not power_engine_count.is_finite()
        or power_engine_count != power_engine_count.to_integral_value()
        or not (1 <= power_engine_count <= 8)
    ):
        raise ValueError(
            f"power_engine_count must be an exact integer Decimal 1-8; got {power_engine_count!r}"
        )

    criteria: list[CategoricalLeafCriterion | NumericLeafCriterion] = []
    active_definitions: list[CriterionDefinition] = []
    if power_drive is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=POWER_DRIVE_CONFIGURATION_DEFINITION.projection_field, equals=power_drive
            )
        )
        active_definitions.append(POWER_DRIVE_CONFIGURATION_DEFINITION)
    if power_engine_count is not None:
        criteria.append(
            NumericLeafCriterion(
                field=POWER_ENGINE_COUNT_DEFINITION.projection_field,
                comparison=NumericComparisonKind.RANGE,
                threshold_min=power_engine_count,
                threshold_max=power_engine_count,
            )
        )
        active_definitions.append(POWER_ENGINE_COUNT_DEFINITION)
    return MixedAndQuery(criteria=tuple(criteria)), tuple(active_definitions)


@dataclass(frozen=True, slots=True)
class PowerCategoryExclusionEvidence:
    """Bounded, cross-Organization-identity-free record of why a candidate
    was excluded from the Power technical Search funnel by the category
    pre-filter -- mirrors `hullq.domain.vessel_category
    .VesselCategoryExclusionEvidence`'s identical rationale (amendment review
    Finding I for the Sail path), but validated against the *opposite*
    explicit-exclusion set (`SAIL`/`MOTORSAILER`/`CONFLICT`) a Power
    admission is excluded by -- the Sail type's own validator rejects `SAIL`
    outright, so it cannot be reused here without weakening its invariant.
    """

    resolution: VesselCategoryResolution
    reason: VesselCategoryResolutionReason

    def __post_init__(self) -> None:
        if self.resolution not in _EXPLICITLY_NON_POWER:
            raise ValueError(
                "PowerCategoryExclusionEvidence.resolution must be an explicit non-Power/"
                f"conflicted resolution (SAIL/MOTORSAILER/CONFLICT), got {self.resolution.value!r}"
            )


@dataclass(frozen=True, slots=True)
class PowerDesignLinkedMatch:
    """One design-linked candidate's Power classification plus full typed
    evidence -- mirrors `hullq.application.native_inventory_query
    .NativeInventoryCandidateEvaluation`'s identical evidence-preservation
    rationale, bounded to the single Power criterion.

    `category_exclusion` is populated only when the category pre-filter
    itself produced this `CONFIRMED_NON_MATCH` (the design level was a
    `CONFIRMED_MATCH` but the resolved vessel category is explicitly
    `SAIL`/`MOTORSAILER`/`CONFLICT`) -- `None` in every other case, including
    an ordinary technical non-match/insufficient-data result and a
    design/configuration-level exclusion.
    """

    native_listing_id: NativeListingId
    result_class: ResultClass
    design_evaluation: DesignQueryEvaluation
    design_configuration_evidence: tuple[ConfigurationEvidence, ...]
    concrete_criterion_evidence: tuple[SearchCriterionEvidence, ...]
    category_exclusion: PowerCategoryExclusionEvidence | None
    publishing_organization_id: MarketplaceOrganizationId
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class PowerClaimOnlyMatch:
    """One design-unresolved candidate's Power publisher-claim-only
    classification -- mirrors `hullq.application.native_inventory_query
    .PublisherClaimCandidateEvaluation`'s identical shape/rationale, bounded
    to the single Power criterion and gated on a publisher-owned explicit
    `POWER` category claim (never a different Organization's category, never
    `UNKNOWN` treated as `POWER`).
    """

    native_listing_id: NativeListingId
    result_class: ResultClass
    criterion_evidence: tuple[SearchCriterionEvidence, ...]
    category_exclusion: PowerCategoryExclusionEvidence | None
    publishing_organization_id: MarketplaceOrganizationId
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None
    source_basis: PublisherClaimSourceBasis
    source_evidence: PublisherClaimSourceEvidence | None


@dataclass(frozen=True, slots=True)
class PowerSearchOutcome:
    """Separated result surfaces for one Power requirement evaluation --
    mirrors `hullq.application.native_inventory_query.NativeInventorySearchOutcome`'s
    separation of design-linked vs. claim-only result surfaces, entirely
    independent of (and structurally distinct from) the Sail outcome type.

    SLICE-0094: `power_drive`/`power_engine_count` are each independently
    optional (never both `None` -- `build_power_query` already enforces at
    least one is supplied), reflecting that a request may supply either
    criterion alone or both combined as MUST-AND.
    """

    power_drive: str | None
    power_engine_count: Decimal | None
    query: MixedAndQuery
    design_linked_matches: tuple[PowerDesignLinkedMatch, ...]
    design_linked_non_matches: tuple[PowerDesignLinkedMatch, ...]
    design_linked_insufficient_data: tuple[PowerDesignLinkedMatch, ...]
    claim_only_matches: tuple[PowerClaimOnlyMatch, ...]
    claim_only_non_matches: tuple[PowerClaimOnlyMatch, ...]
    claim_only_insufficient_data: tuple[PowerClaimOnlyMatch, ...]

    @property
    def design_linked_match_count(self) -> int:
        return len(self.design_linked_matches)

    @property
    def claim_only_match_count(self) -> int:
        return len(self.claim_only_matches)


@dataclass(frozen=True, slots=True)
class PowerSearchResultPage:
    """One bounded page of the Power requirement vertical -- SLICE-0096,
    mirrors `hullq.application.native_inventory_query
    .NativeInventorySearchResultPage`'s identical page-local/invariant
    discipline (same `__post_init__` PARTIAL-must-carry-cursor /
    COMPLETE-must-not rule), bounded to the Power domain's two match
    surfaces instead of the Sail ones. `design_linked_insufficient_data_count`/
    `claim_only_insufficient_data_count` are kept separate, mirroring the
    pre-0096 public API exactly: the existing `/api/search/{locale}/power`
    route only ever serialized the design-linked plane's insufficient count
    (`design_linked_insufficient_data_count`); the claim-only plane's own
    insufficient data was never exposed as a count at all.
    """

    query: MixedAndQuery
    evaluation_state: SearchPageEvaluationState
    next_after_native_listing_id: str | None
    design_linked_matches: tuple[PowerDesignLinkedMatch, ...]
    claim_only_matches: tuple[PowerClaimOnlyMatch, ...]
    design_linked_insufficient_data_count: int
    claim_only_insufficient_data_count: int

    def __post_init__(self) -> None:
        is_partial = self.evaluation_state is SearchPageEvaluationState.PARTIAL
        if is_partial and self.next_after_native_listing_id is None:
            raise ValueError("A PARTIAL page must carry next_after_native_listing_id")
        if not is_partial and self.next_after_native_listing_id is not None:
            raise ValueError("A COMPLETE page must not carry next_after_native_listing_id")

    @property
    def design_linked_match_count(self) -> int:
        return len(self.design_linked_matches)

    @property
    def claim_only_match_count(self) -> int:
        return len(self.claim_only_matches)


# ---------------------------------------------------------------------------
# Claim-only (design-unresolved) Power path
# ---------------------------------------------------------------------------


def resolve_power_claim_only_category_from_observations(
    observations: Sequence[CurrentPhysicalBoatClaimObservation],
) -> VesselCategoryResolutionResult:
    """Resolve the current `VesselCategory` directly from an already-fetched
    *observations* set -- identical reasoning to `hullq.application
    .native_inventory_query._resolve_claim_only_category_from_observations`:
    one coherent snapshot, no second independent SQL read. `design_evidence`
    is always `None` (a design-unresolved PhysicalBoat never has one).
    Reuses the exact same pure `resolve_vessel_category` combination step --
    no second category-resolution rule.
    """
    concrete_evidence = tuple(
        ConcreteVesselCategoryEvidence(
            claiming_organization_id=obs.claiming_organization_id,
            revision_id=obs.revision_id,
            recorded_by_account_id=obs.recorded_by_account_id,
            recorded_at=obs.recorded_at,
            claim=obs.vessel_category,
        )
        for obs in observations
    )
    return resolve_vessel_category(design_evidence=None, concrete_evidence=concrete_evidence)


def resolve_power_category_admission(
    category_resolution: VesselCategoryResolutionResult,
    publishing_organization_id: MarketplaceOrganizationId,
) -> tuple[bool, PowerCategoryExclusionEvidence | None]:
    """Contract §A / READY "Must-never-change invariant": a candidate is
    admitted to the Power path iff the overall resolution is `POWER`
    **and** the publishing Organization itself (never merely another
    current claimant, and never merely the design plane alone) carries an
    explicit current `VALUE_ASSERTION(POWER)` claim -- "Another
    Organization's category assertion cannot lend the publisher its Sail
    eligibility", generalized to POWER. "No drive without a publisher's
    own positive POWER and current specific drive in one revision
    qualifies" (the READY contract's exact words) applies to **both**
    Power candidate planes identically -- claim-only (where this
    admission precondition originated) and design-linked (review
    amendment, §2: a design-only or other-Organization-only POWER
    resolution must never silently admit the publisher's own concrete
    drive claim to `classify_concrete_candidate`).

    Returns `(admitted, exclusion_evidence)`. `exclusion_evidence` is
    populated only when the resolution is explicitly SAIL/MOTORSAILER/
    CONFLICT. A missing/UNKNOWN category, a POWER resolution contributed
    only by the design plane (`DESIGN_ONLY`) with no publisher claim at
    all, or a POWER resolution contributed only by a different
    Organization, is `(False, None)`: the caller classifies that as
    `INSUFFICIENT_DATA`, never `CONFIRMED_NON_MATCH` and never a
    `CONFIRMED_MATCH`.
    """
    exclusion = (
        PowerCategoryExclusionEvidence(
            resolution=category_resolution.resolution, reason=category_resolution.reason
        )
        if category_resolution.resolution in _EXPLICITLY_NON_POWER
        else None
    )
    if category_resolution.resolution is not VesselCategoryResolution.POWER:
        return False, exclusion
    publisher_entry = next(
        (
            entry
            for entry in category_resolution.concrete_evidence
            if entry.claiming_organization_id == publishing_organization_id
        ),
        None,
    )
    publisher_owns_power = (
        publisher_entry is not None
        and publisher_entry.claim is not None
        and publisher_entry.claim.assertion_kind is AssertionKind.VALUE_ASSERTION
        and publisher_entry.claim.value is VesselCategory.POWER
    )
    return publisher_owns_power, exclusion


def downgrade_mixed_non_match_to_insufficient_data(
    result_class: ResultClass,
    criterion_evidence: tuple[SearchCriterionEvidence, ...],
) -> tuple[ResultClass, tuple[SearchCriterionEvidence, ...]]:
    """Review amendment Finding H: a current `VALUE_ASSERTION(MIXED)` drive
    claim never proves the absence of any single accepted drive type (the
    normative contract's own words are "even if the vessel uses one of the
    types") -- so it must never surface as a confirmed exclusion.

    Applied strictly AFTER `classify_claim_only_candidate`/
    `classify_concrete_candidate` has already run the ordinary, unmodified
    fail-closed qualification (`hullq.application.native_inventory_query
    ._qualify_claim_field`) -- including its same-PhysicalBoat
    cross-Organization contradiction guard -- against the TRUE, unmasked
    claim values (`hullq.search.power_criteria_registry
    ._read_power_drive_configuration_claim` is a plain passthrough; see
    that function's docstring for why an earlier revision's claim-read-level
    masking silently hid genuine cross-Organization `MIXED` contradictions,
    Finding H).

    Because this runs after qualification, `observed_value == "MIXED"` on a
    `CONFIRMED_NON_MATCH` outcome can only mean the publisher's own current
    claim, uncontested by any other current claiming Organization, IS
    `MIXED` -- a cross-Organization contradiction (publisher SHAFT vs.
    another Organization MIXED, or vice versa) already yields `MISSING` ->
    `INSUFFICIENT_DATA` with `observed_value is None` from the ordinary
    qualification step, never reaching this function with `"MIXED"` at all.
    `OTHER` and every other single-token value are untouched: this function
    only ever rewrites the one `"MIXED"` case.

    SLICE-0094 generalization: with a second active criterion
    (`power_engine_count`), `criterion_evidence` may now carry two entries.
    Only the drive leaf (matched by `criterion.field`, never by position) is
    ever eligible for rewriting -- a genuinely non-matching `power_engine_count`
    leaf must still confirm exclusion regardless of an uninformative MIXED
    drive leaf alongside it. After rewriting the drive leaf's truth to
    UNKNOWN, the aggregate result is recomputed via the identical
    `and_reduce`/`result_class_for` MUST-AND reduction every other combined
    query already uses -- never a bespoke two-criterion special case: if
    another leaf is still a genuine confirmed FALSE, the aggregate correctly
    remains `CONFIRMED_NON_MATCH` (MIXED never rescues an independently
    confirmed non-match); if no leaf is FALSE, the aggregate becomes
    `INSUFFICIENT_DATA`. A single drive-only request (SLICE-0093's own
    unmodified call site) behaves identically to before: exactly one
    evidence entry, `and_reduce((UNKNOWN,)) == UNKNOWN`,
    `result_class_for(UNKNOWN) == INSUFFICIENT_DATA`.
    """
    if result_class is not ResultClass.CONFIRMED_NON_MATCH:
        return result_class, criterion_evidence
    drive_field = POWER_DRIVE_CONFIGURATION_DEFINITION.projection_field
    rewritten = False
    updated_evidence: list[SearchCriterionEvidence] = []
    for evidence in criterion_evidence:
        if (
            evidence.criterion.field == drive_field
            and evidence.evaluation.truth is TruthState.FALSE
            and evidence.observed_value == PowerDriveConfiguration.MIXED.value
        ):
            rewritten = True
            updated_evidence.append(
                SearchCriterionEvidence(
                    criterion=evidence.criterion,
                    evaluation=CriterionEvaluation(
                        field=evidence.evaluation.field,
                        truth=TruthState.UNKNOWN,
                        reason=ReasonCode.VALUE_MISSING,
                        explanation=(
                            f"{evidence.evaluation.field}: current claim is MIXED, which never "
                            f"proves the absence of any single accepted drive type (even if the "
                            f"vessel uses one of the types) -- insufficient data, not a confirmed "
                            f"exclusion"
                        ),
                    ),
                    observed_value=None,
                )
            )
        else:
            updated_evidence.append(evidence)
    if not rewritten:
        return result_class, criterion_evidence
    aggregate = and_reduce(tuple(e.evaluation.truth for e in updated_evidence))
    return result_class_for(aggregate), tuple(updated_evidence)


def evaluate_power_claim_only_candidates(
    conn: Any,
    *,
    query: MixedAndQuery,
    as_of: datetime,
    active_definitions: Sequence[CriterionDefinition] = _ACTIVE_POWER_DEFINITIONS,
) -> tuple[
    tuple[PowerClaimOnlyMatch, ...],
    tuple[PowerClaimOnlyMatch, ...],
    tuple[PowerClaimOnlyMatch, ...],
]:
    """Evaluate every ACTIVE, design-UNRESOLVED candidate's publisher-claim
    evidence against *query* -- the Power-domain mirror of
    `hullq.application.native_inventory_query.evaluate_claim_only_candidates`,
    reusing its identical batched D29/observation-read strategy (amendment
    review PR #387 Finding D) and its generic `classify_claim_only_candidate`
    directly, rather than a new Power scorer.

    SLICE-0094: *active_definitions* defaults to the unmodified SLICE-0093
    one-element `_ACTIVE_POWER_DEFINITIONS` tuple, so the unmodified
    `evaluate_power_drive_requirement` call site (which never passes this
    parameter) is byte-for-byte unaffected. A request involving
    `power_engine_count` passes the wider tuple `build_power_query` returns.
    """
    all_candidates = list_active_design_unresolved_listings(conn)
    if not all_candidates:
        return (), (), ()

    bulk_eligibility = resolve_current_public_eligibility_for_many(
        conn, [candidate.native_listing_id for candidate in all_candidates], as_of=as_of
    )
    eligible_candidates: list[tuple[ActiveDesignUnresolvedListing, CurrentFreshness]] = []
    for candidate in all_candidates:
        bulk_result = bulk_eligibility.get(candidate.native_listing_id.value)
        if (
            bulk_result is None
            or bulk_result.eligibility.status is not CurrentPublicEligibilityStatus.ELIGIBLE
        ):
            continue
        eligible_candidates.append((candidate, bulk_result.freshness))
    if not eligible_candidates:
        return (), (), ()

    observations_by_boat = list_current_physical_boat_claim_observations_for_many(
        conn, [candidate.physical_boat_id for candidate, _ in eligible_candidates]
    )

    matches: list[PowerClaimOnlyMatch] = []
    non_matches: list[PowerClaimOnlyMatch] = []
    insufficient_data: list[PowerClaimOnlyMatch] = []

    for candidate, freshness in eligible_candidates:
        observations = observations_by_boat[candidate.physical_boat_id]
        category_resolution = resolve_power_claim_only_category_from_observations(observations)
        admitted, exclusion = resolve_power_category_admission(
            category_resolution, candidate.publishing_organization_id
        )

        publisher_observation = next(
            (
                obs
                for obs in observations
                if obs.claiming_organization_id == candidate.publishing_organization_id
            ),
            None,
        )
        source_evidence = (
            PublisherClaimSourceEvidence(
                revision_id=publisher_observation.revision_id,
                recorded_by_account_id=publisher_observation.recorded_by_account_id,
                recorded_at=publisher_observation.recorded_at,
                category_claim=publisher_observation.vessel_category,
            )
            if publisher_observation is not None
            else None
        )

        criterion_evidence: tuple[SearchCriterionEvidence, ...]
        if exclusion is not None:
            result_class = ResultClass.CONFIRMED_NON_MATCH
            criterion_evidence = ()
        elif not admitted:
            result_class = ResultClass.INSUFFICIENT_DATA
            criterion_evidence = ()
        else:
            result_class, criterion_evidence = classify_claim_only_candidate(
                observations,
                publishing_organization_id=candidate.publishing_organization_id,
                query=query,
                active_definitions=active_definitions,
            )
            result_class, criterion_evidence = downgrade_mixed_non_match_to_insufficient_data(
                result_class, criterion_evidence
            )

        evaluation = PowerClaimOnlyMatch(
            native_listing_id=candidate.native_listing_id,
            result_class=result_class,
            criterion_evidence=criterion_evidence,
            category_exclusion=exclusion,
            publishing_organization_id=candidate.publishing_organization_id,
            freshness_status=freshness.status,
            last_confirmed_at=freshness.last_confirmed_at,
            source_basis=PublisherClaimSourceBasis.PUBLISHER_CLAIM,
            source_evidence=source_evidence,
        )
        if result_class is ResultClass.CONFIRMED_MATCH:
            matches.append(evaluation)
        elif result_class is ResultClass.CONFIRMED_NON_MATCH:
            non_matches.append(evaluation)
        else:
            insufficient_data.append(evaluation)

    matches.sort(key=lambda m: m.native_listing_id.value)
    non_matches.sort(key=lambda m: m.native_listing_id.value)
    insufficient_data.sort(key=lambda m: m.native_listing_id.value)
    return tuple(matches), tuple(non_matches), tuple(insufficient_data)


# ---------------------------------------------------------------------------
# Design-linked Power path
# ---------------------------------------------------------------------------


def evaluate_power_design_linked_candidates(
    conn: Any,
    *,
    query: MixedAndQuery,
    as_of: datetime,
    active_definitions: Sequence[CriterionDefinition] = _ACTIVE_POWER_DEFINITIONS,
) -> tuple[
    tuple[PowerDesignLinkedMatch, ...],
    tuple[PowerDesignLinkedMatch, ...],
    tuple[PowerDesignLinkedMatch, ...],
]:
    """Evaluate every ACTIVE design-linked candidate's Power classification.

    Design-side source-qualification is bounded to v0.6's `shaft`/`outboard`
    mapping (`hullq.search.power_drive_design_bridge`) -- `STERNDRIVE`/
    `POD`/`WATERJET` are always `INSUFFICIENT_DATA` at the design level, as
    the normative contract requires ("No v0.7 BoatDesign schema/migration is
    granted by this criterion"). A confirmed design-level match still
    requires the current PhysicalBoat's own concrete claim to independently
    confirm the same field (`classify_concrete_candidate`, reused unchanged)
    -- design truth never silently becomes concrete truth.

    SLICE-0094: *active_definitions* defaults to the unmodified SLICE-0093
    one-element `_ACTIVE_POWER_DEFINITIONS` tuple (same rationale as
    `evaluate_power_claim_only_candidates`). The design-side configuration
    set is now built via the shared
    `hullq.application.native_inventory_query
    .run_mixed_boat_design_configuration_query` -- the identical generalized
    per-definition `design_set_builder` + merge kernel the Sail funnel
    already established -- rather than a Power-specific call to
    `run_boat_design_configuration_query` with a single hardcoded
    `FieldProjectionSpec`. For the unmodified one-definition default this
    produces byte-identical results (a single-element merge is a no-op,
    `hullq.application.native_inventory_query._merge_configuration_sets`'s
    own docstring), so this is pure reuse, not a behavior change for the
    drive-only path.
    """
    all_candidates = list_active_design_linked_listings(conn)
    if not all_candidates:
        return (), (), ()

    bulk_eligibility = resolve_current_public_eligibility_for_many(
        conn, [candidate.native_listing_id for candidate in all_candidates], as_of=as_of
    )
    current_candidates: list[tuple[ActiveDesignLinkedListing, CurrentFreshness]] = []
    for candidate in all_candidates:
        bulk_result = bulk_eligibility.get(candidate.native_listing_id.value)
        if (
            bulk_result is None
            or bulk_result.eligibility.status is not CurrentPublicEligibilityStatus.ELIGIBLE
        ):
            continue
        current_candidates.append((candidate, bulk_result.freshness))
    if not current_candidates:
        return (), (), ()

    distinct_design_ids = sorted({c.boat_design_ref.value for c, _ in current_candidates})
    boat_designs = []
    for design_id in distinct_design_ids:
        raw_design = fetch_boat_design(conn, design_id)
        if raw_design is not None:
            boat_designs.append(raw_design)

    design_result = run_mixed_boat_design_configuration_query(
        conn, query, boat_designs, active_definitions
    )
    design_evaluation_by_id: dict[str, DesignQueryEvaluation] = {
        evaluation.design_id: evaluation
        for evaluation in (
            design_result.outcome.confirmed_matches
            + design_result.outcome.confirmed_non_matches
            + design_result.outcome.insufficient_data
        )
    }

    matches: list[PowerDesignLinkedMatch] = []
    non_matches: list[PowerDesignLinkedMatch] = []
    insufficient_data: list[PowerDesignLinkedMatch] = []

    for candidate, freshness in current_candidates:
        design_evaluation = design_evaluation_by_id.get(candidate.boat_design_ref.value)
        if design_evaluation is None:
            # Dangling BoatDesignRef -- never a candidate, mirrors the Sail
            # funnel's identical exclusion.
            continue

        design_configuration_evidence = tuple(
            build_configuration_evidence(
                query,
                configuration_evaluation,
                design_result.configurations_by_id[configuration_evaluation.configuration_id],
            )
            for configuration_evaluation in design_evaluation.configuration_evaluations
        )

        concrete_evidence: tuple[SearchCriterionEvidence, ...]
        if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
            # Review amendment Finding G: category admission and drive
            # classification MUST be read from the same PostgreSQL
            # statement/snapshot -- a two-statement sequence here (resolve
            # category, then separately re-read claims to classify drive)
            # reopens exactly the MVCC tear window SLICE-0091 amendment
            # Finding F closed for category-alone. One combined snapshot
            # read, then the pure `resolve_vessel_category` combination
            # function plus `classify_concrete_candidate` fed that same
            # snapshot's observations -- never a second claims read.
            snapshot = fetch_power_category_drive_snapshot(
                conn,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_id=candidate.boat_design_ref.value,
            )
            category_resolution = resolve_vessel_category(
                design_evidence=snapshot.design_evidence,
                concrete_evidence=snapshot.concrete_evidence,
            )
            # Review amendment §2: admission reuses the exact same
            # publisher-owned-POWER precondition the claim-only plane
            # already enforces (`resolve_power_category_admission`) --
            # the READY contract's "No drive without a publisher's own
            # positive POWER ... in one revision qualifies" invariant
            # applies identically to both planes. `category_resolution.
            # resolution is POWER` alone is NOT sufficient here: a
            # `DESIGN_ONLY` resolution (canonical BoatDesign asserts POWER,
            # publisher has no current category claim at all) or a POWER
            # resolution contributed only by a different Organization must
            # never admit the publisher's own concrete drive claim to
            # `classify_concrete_candidate` -- that would let a bare
            # design-level category assertion stand in for the publisher's
            # own missing positive POWER claim.
            admitted, category_exclusion = resolve_power_category_admission(
                category_resolution, candidate.publishing_organization_id
            )
            if admitted:
                result_class, concrete_evidence = classify_concrete_candidate(
                    conn,
                    native_listing_id=candidate.native_listing_id,
                    publishing_organization_id=candidate.publishing_organization_id,
                    physical_boat_id=candidate.physical_boat_id,
                    boat_design_id=candidate.boat_design_ref.value,
                    query=query,
                    active_definitions=active_definitions,
                    observations=snapshot.observations,
                )
                result_class, concrete_evidence = downgrade_mixed_non_match_to_insufficient_data(
                    result_class, concrete_evidence
                )
            elif category_exclusion is not None:
                result_class = ResultClass.CONFIRMED_NON_MATCH
                concrete_evidence = ()
            else:
                # Missing/UNKNOWN category, DESIGN_ONLY with no publisher
                # claim, or POWER contributed only by a different
                # Organization -- insufficient, never a false exclusion
                # and never a false match via the design plane alone.
                result_class = ResultClass.INSUFFICIENT_DATA
                concrete_evidence = ()
        else:
            result_class = design_evaluation.result_class
            concrete_evidence = ()
            category_exclusion = None

        evaluation = PowerDesignLinkedMatch(
            native_listing_id=candidate.native_listing_id,
            result_class=result_class,
            design_evaluation=design_evaluation,
            design_configuration_evidence=design_configuration_evidence,
            concrete_criterion_evidence=concrete_evidence,
            category_exclusion=category_exclusion,
            publishing_organization_id=candidate.publishing_organization_id,
            freshness_status=freshness.status,
            last_confirmed_at=freshness.last_confirmed_at,
        )
        if result_class is ResultClass.CONFIRMED_MATCH:
            matches.append(evaluation)
        elif result_class is ResultClass.CONFIRMED_NON_MATCH:
            non_matches.append(evaluation)
        else:
            insufficient_data.append(evaluation)

    matches.sort(key=lambda m: m.native_listing_id.value)
    non_matches.sort(key=lambda m: m.native_listing_id.value)
    insufficient_data.sort(key=lambda m: m.native_listing_id.value)
    return tuple(matches), tuple(non_matches), tuple(insufficient_data)


# ---------------------------------------------------------------------------
# Combined entrypoint
# ---------------------------------------------------------------------------


def evaluate_power_drive_requirement(
    conn: Any, *, power_drive: str, as_of: datetime
) -> PowerSearchOutcome:
    """Evaluate one already-canonical Power `power_drive` requirement
    against real persisted state -- the Power-domain entrypoint
    `hullq.application.power_search_read` dispatches to, exactly mirroring
    `hullq.application.search_read.evaluate_requirement_search_outcome`'s
    division of labor for the Sail path."""
    query = build_power_drive_query(power_drive)
    claim_only_matches, claim_only_non_matches, claim_only_insufficient_data = (
        evaluate_power_claim_only_candidates(conn, query=query, as_of=as_of)
    )
    design_linked_matches, design_linked_non_matches, design_linked_insufficient_data = (
        evaluate_power_design_linked_candidates(conn, query=query, as_of=as_of)
    )
    return PowerSearchOutcome(
        power_drive=power_drive,
        power_engine_count=None,
        query=query,
        design_linked_matches=design_linked_matches,
        design_linked_non_matches=design_linked_non_matches,
        design_linked_insufficient_data=design_linked_insufficient_data,
        claim_only_matches=claim_only_matches,
        claim_only_non_matches=claim_only_non_matches,
        claim_only_insufficient_data=claim_only_insufficient_data,
    )


def evaluate_power_requirement(
    conn: Any, *, power_drive: str | None, power_engine_count: Decimal | None, as_of: datetime
) -> PowerSearchOutcome:
    """Evaluate one already-canonical Power requirement -- `power_drive`
    and/or `power_engine_count` -- SLICE-0094 entrypoint
    `hullq.application.power_search_read` dispatches to.

    A pure `power_drive`-only requirement (`power_engine_count is None`)
    keeps calling the byte-for-byte unmodified SLICE-0093
    `evaluate_power_drive_requirement` -- the contract's own acceptance
    criterion ("old 0093 drive-only Search returns identical results") is
    satisfied by literal reuse of that exact code path, never a second
    independently-timed equivalent. A request involving `power_engine_count`
    (alone or combined with `power_drive`) builds the combined MUST-AND
    query via `build_power_query` and reuses the identical
    `evaluate_power_claim_only_candidates`/
    `evaluate_power_design_linked_candidates` kernels, parameterized over
    the exact active definitions this request needs -- never a union of
    separately evaluated per-criterion candidate sets.
    """
    if power_engine_count is None:
        assert power_drive is not None  # build_power_query already enforced this upstream
        return evaluate_power_drive_requirement(conn, power_drive=power_drive, as_of=as_of)

    query, active_definitions = build_power_query(
        power_drive=power_drive, power_engine_count=power_engine_count
    )
    claim_only_matches, claim_only_non_matches, claim_only_insufficient_data = (
        evaluate_power_claim_only_candidates(
            conn, query=query, as_of=as_of, active_definitions=active_definitions
        )
    )
    design_linked_matches, design_linked_non_matches, design_linked_insufficient_data = (
        evaluate_power_design_linked_candidates(
            conn, query=query, as_of=as_of, active_definitions=active_definitions
        )
    )
    return PowerSearchOutcome(
        power_drive=power_drive,
        power_engine_count=power_engine_count,
        query=query,
        design_linked_matches=design_linked_matches,
        design_linked_non_matches=design_linked_non_matches,
        design_linked_insufficient_data=design_linked_insufficient_data,
        claim_only_matches=claim_only_matches,
        claim_only_non_matches=claim_only_non_matches,
        claim_only_insufficient_data=claim_only_insufficient_data,
    )


def _classify_power_design_linked_page_candidate(
    conn: Any,
    candidate: ActiveNativeListingCandidate,
    freshness: CurrentFreshness,
    *,
    query: MixedAndQuery,
    active_definitions: Sequence[CriterionDefinition],
    design_evaluation_by_id: Mapping[str, DesignQueryEvaluation],
    configurations_by_id: Mapping[str, ResolvedConfiguration],
) -> PowerDesignLinkedMatch | None:
    """One design-linked candidate's Power classification for the bounded
    page path -- byte-identical decision logic to
    `evaluate_power_design_linked_candidates`'s own per-candidate loop body
    (review amendment Finding G's one-combined-snapshot-statement rule
    included), factored out so the bounded page evaluator can call it from
    a single global-order walk. `None` for a dangling `BoatDesignRef`.
    """
    assert candidate.boat_design_ref is not None
    design_evaluation = design_evaluation_by_id.get(candidate.boat_design_ref.value)
    if design_evaluation is None:
        return None

    design_configuration_evidence = tuple(
        build_configuration_evidence(
            query,
            configuration_evaluation,
            configurations_by_id[configuration_evaluation.configuration_id],
        )
        for configuration_evaluation in design_evaluation.configuration_evaluations
    )

    concrete_evidence: tuple[SearchCriterionEvidence, ...]
    category_exclusion: PowerCategoryExclusionEvidence | None
    if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
        snapshot = fetch_power_category_drive_snapshot(
            conn,
            physical_boat_id=candidate.physical_boat_id,
            boat_design_id=candidate.boat_design_ref.value,
        )
        category_resolution = resolve_vessel_category(
            design_evidence=snapshot.design_evidence, concrete_evidence=snapshot.concrete_evidence
        )
        admitted, category_exclusion = resolve_power_category_admission(
            category_resolution, candidate.publishing_organization_id
        )
        if admitted:
            result_class, concrete_evidence = classify_concrete_candidate(
                conn,
                native_listing_id=candidate.native_listing_id,
                publishing_organization_id=candidate.publishing_organization_id,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_id=candidate.boat_design_ref.value,
                query=query,
                active_definitions=active_definitions,
                observations=snapshot.observations,
            )
            result_class, concrete_evidence = downgrade_mixed_non_match_to_insufficient_data(
                result_class, concrete_evidence
            )
        elif category_exclusion is not None:
            result_class = ResultClass.CONFIRMED_NON_MATCH
            concrete_evidence = ()
        else:
            result_class = ResultClass.INSUFFICIENT_DATA
            concrete_evidence = ()
    else:
        result_class = design_evaluation.result_class
        concrete_evidence = ()
        category_exclusion = None

    return PowerDesignLinkedMatch(
        native_listing_id=candidate.native_listing_id,
        result_class=result_class,
        design_evaluation=design_evaluation,
        design_configuration_evidence=design_configuration_evidence,
        concrete_criterion_evidence=concrete_evidence,
        category_exclusion=category_exclusion,
        publishing_organization_id=candidate.publishing_organization_id,
        freshness_status=freshness.status,
        last_confirmed_at=freshness.last_confirmed_at,
    )


def _classify_power_claim_only_page_candidate(
    candidate: ActiveNativeListingCandidate,
    freshness: CurrentFreshness,
    *,
    query: MixedAndQuery,
    active_definitions: Sequence[CriterionDefinition],
    observations: Sequence[CurrentPhysicalBoatClaimObservation],
) -> PowerClaimOnlyMatch:
    """One design-unresolved candidate's Power classification for the
    bounded page path -- byte-identical decision logic to
    `evaluate_power_claim_only_candidates`'s own per-candidate loop body.
    """
    assert candidate.boat_design_ref is None
    category_resolution = resolve_power_claim_only_category_from_observations(observations)
    admitted, exclusion = resolve_power_category_admission(
        category_resolution, candidate.publishing_organization_id
    )

    publisher_observation = next(
        (
            obs
            for obs in observations
            if obs.claiming_organization_id == candidate.publishing_organization_id
        ),
        None,
    )
    source_evidence = (
        PublisherClaimSourceEvidence(
            revision_id=publisher_observation.revision_id,
            recorded_by_account_id=publisher_observation.recorded_by_account_id,
            recorded_at=publisher_observation.recorded_at,
            category_claim=publisher_observation.vessel_category,
        )
        if publisher_observation is not None
        else None
    )

    criterion_evidence: tuple[SearchCriterionEvidence, ...]
    if exclusion is not None:
        result_class = ResultClass.CONFIRMED_NON_MATCH
        criterion_evidence = ()
    elif not admitted:
        result_class = ResultClass.INSUFFICIENT_DATA
        criterion_evidence = ()
    else:
        result_class, criterion_evidence = classify_claim_only_candidate(
            observations,
            publishing_organization_id=candidate.publishing_organization_id,
            query=query,
            active_definitions=active_definitions,
        )
        result_class, criterion_evidence = downgrade_mixed_non_match_to_insufficient_data(
            result_class, criterion_evidence
        )

    return PowerClaimOnlyMatch(
        native_listing_id=candidate.native_listing_id,
        result_class=result_class,
        criterion_evidence=criterion_evidence,
        category_exclusion=exclusion,
        publishing_organization_id=candidate.publishing_organization_id,
        freshness_status=freshness.status,
        last_confirmed_at=freshness.last_confirmed_at,
        source_basis=PublisherClaimSourceBasis.PUBLISHER_CLAIM,
        source_evidence=source_evidence,
    )


def evaluate_power_requirement_page(
    conn: Any,
    *,
    power_drive: str | None,
    power_engine_count: Decimal | None,
    as_of: datetime,
    after_native_listing_id: str | None,
    page_size: int,
    candidate_scan_budget: int = DEFAULT_CANDIDATE_SCAN_BUDGET,
) -> PowerSearchResultPage:
    """Evaluate one bounded page of the Power requirement vertical --
    SLICE-0096's new public entrypoint, the Power-domain mirror of
    `hullq.application.native_inventory_query
    .evaluate_native_inventory_requirements_page`. See that function's
    docstring for the shared bounded-scan/early-stop/exact-fill-lookahead
    rationale -- identical here, just dispatching to the Power-domain
    per-candidate classifiers above instead of the Sail ones.
    """
    if not isinstance(page_size, int) or isinstance(page_size, bool) or not (1 <= page_size <= 50):
        raise ValueError(f"page_size must be an int in [1, 50]; got {page_size!r}")
    # Mirrors hullq.application.native_inventory_query
    # .evaluate_native_inventory_requirements_page's identical rationale:
    # candidate_scan_budget is an internal safety cap independent of
    # page_size, never required to be >= it.
    if (
        not isinstance(candidate_scan_budget, int)
        or isinstance(candidate_scan_budget, bool)
        or (candidate_scan_budget < 1)
    ):
        raise ValueError(
            f"candidate_scan_budget must be a positive int; got {candidate_scan_budget!r}"
        )

    query, active_definitions = build_power_query(
        power_drive=power_drive, power_engine_count=power_engine_count
    )

    batch = list_active_native_listing_candidates_page(
        conn, after_native_listing_id=after_native_listing_id, limit=candidate_scan_budget
    )
    if not batch:
        return PowerSearchResultPage(
            query=query,
            evaluation_state=SearchPageEvaluationState.COMPLETE,
            next_after_native_listing_id=None,
            design_linked_matches=(),
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

    design_evaluation_by_id: dict[str, DesignQueryEvaluation] = {}
    configurations_by_id: Mapping[str, ResolvedConfiguration] = {}
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
            raw_design = fetch_boat_design(conn, design_id)
            if raw_design is not None:
                boat_designs.append(raw_design)
        design_result = run_mixed_boat_design_configuration_query(
            conn, query, boat_designs, active_definitions
        )
        design_evaluation_by_id = {
            evaluation.design_id: evaluation
            for evaluation in (
                design_result.outcome.confirmed_matches
                + design_result.outcome.confirmed_non_matches
                + design_result.outcome.insufficient_data
            )
        }
        configurations_by_id = design_result.configurations_by_id

    claim_only_observations_by_boat: dict[Any, list[CurrentPhysicalBoatClaimObservation]] = {}
    if claim_only_eligible:
        claim_only_observations_by_boat = list_current_physical_boat_claim_observations_for_many(
            conn, [candidate.physical_boat_id for candidate in claim_only_eligible]
        )

    design_linked_matches: list[PowerDesignLinkedMatch] = []
    claim_only_matches: list[PowerClaimOnlyMatch] = []
    design_linked_insufficient_data_count = 0
    claim_only_insufficient_data_count = 0
    last_examined_id: str | None = None
    exhausted_batch = True

    for index, candidate in enumerate(batch):
        last_examined_id = candidate.native_listing_id.value
        freshness = eligible_by_id.get(candidate.native_listing_id.value)
        if freshness is None:
            continue

        if candidate.boat_design_ref is not None:
            design_match = _classify_power_design_linked_page_candidate(
                conn,
                candidate,
                freshness,
                query=query,
                active_definitions=active_definitions,
                design_evaluation_by_id=design_evaluation_by_id,
                configurations_by_id=configurations_by_id,
            )
            if design_match is None:
                continue
            if design_match.result_class is ResultClass.CONFIRMED_MATCH:
                design_linked_matches.append(design_match)
            elif design_match.result_class is ResultClass.INSUFFICIENT_DATA:
                design_linked_insufficient_data_count += 1
        else:
            observations = claim_only_observations_by_boat.get(candidate.physical_boat_id, [])
            claim_match = _classify_power_claim_only_page_candidate(
                candidate,
                freshness,
                query=query,
                active_definitions=active_definitions,
                observations=observations,
            )
            if claim_match.result_class is ResultClass.CONFIRMED_MATCH:
                claim_only_matches.append(claim_match)
            elif claim_match.result_class is ResultClass.INSUFFICIENT_DATA:
                claim_only_insufficient_data_count += 1

        if len(design_linked_matches) + len(claim_only_matches) >= page_size:
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

    return PowerSearchResultPage(
        query=query,
        evaluation_state=evaluation_state,
        next_after_native_listing_id=next_after_native_listing_id,
        design_linked_matches=tuple(design_linked_matches),
        claim_only_matches=tuple(claim_only_matches),
        design_linked_insufficient_data_count=design_linked_insufficient_data_count,
        claim_only_insufficient_data_count=claim_only_insufficient_data_count,
    )
