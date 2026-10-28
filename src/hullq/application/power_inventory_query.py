"""Power-domain Requirements -> Native Inventory Search vertical — SLICE-0093.

The first Power hard technical criterion, `power_drive_configuration`
(`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`). This module is
the Power-domain counterpart of `hullq.application.native_inventory_query`,
reusing its genuinely category-neutral shared kernel directly rather than
re-implementing it (Trigger Gates "Second-criterion bridge comparison" /
"Third-copy abstraction guard": COMMON STRUCTURE GENERALIZED / REUSED):

    `classify_concrete_candidate` / `classify_claim_only_candidate` --
        already generic over any `Sequence[CriterionDefinition]` and any
        `MixedAndQuery`, never Sail-specific in their own signatures;
    `SearchCriterionEvidence` / `ConfigurationEvidence` / `build_configuration_evidence` --
        the same typed evidence wrappers, unmodified;
    `PublisherClaimSourceBasis` / `PublisherClaimSourceEvidence` --
        the same `PUBLISHER_CLAIM` source-basis discriminator and internal
        provenance shape;
    `hullq.search.boat_design_field_bridge.run_boat_design_configuration_query` --
        the identical shared BoatDesign/NamedVariant evaluation bridge, fed
        this criterion's own `FieldProjectionSpec`
        (`hullq.search.power_drive_design_bridge`);
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

Existing Sail funnels (`evaluate_native_inventory_requirements`,
`evaluate_draft_max_requirement`, `evaluate_claim_only_candidates`) are never
called, imported-and-mutated or altered by this module. No `power_drive`
query key is ever accepted by the Sail parser, and no Sail key is ever
accepted here (`hullq.application.power_search_read` owns that boundary).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from hullq.application.current_public_eligibility import (
    resolve_current_public_eligibility_for_many,
)
from hullq.application.native_inventory_query import (
    ConfigurationEvidence,
    PublisherClaimSourceBasis,
    PublisherClaimSourceEvidence,
    SearchCriterionEvidence,
    build_configuration_evidence,
    classify_claim_only_candidate,
    classify_concrete_candidate,
)
from hullq.application.native_listing_freshness import CurrentFreshness
from hullq.application.vessel_category_resolution import resolve_physical_boat_vessel_category
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.physical_boat_claims import AssertionKind, VesselCategory
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
    list_active_design_linked_listings,
    list_active_design_unresolved_listings,
)
from hullq.persistence.physical_boat_claims import (
    CurrentPhysicalBoatClaimObservation,
    list_current_physical_boat_claim_observations_for_many,
)
from hullq.search.boat_design_field_bridge import run_boat_design_configuration_query
from hullq.search.configuration_engine import DesignQueryEvaluation
from hullq.search.criteria import CategoricalLeafCriterion
from hullq.search.criteria_registry import CriterionDefinition
from hullq.search.power_criteria_registry import (
    POWER_DRIVE_CONFIGURATION_DEFINITION,
    SEARCH_POWER_DRIVE_VALUES,
)
from hullq.search.power_drive_design_bridge import (
    POWER_DRIVE_CONFIGURATION_FIELD_PROJECTION_SPEC,
)
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import ResultClass

__all__ = [
    "PowerCategoryExclusionEvidence",
    "PowerClaimOnlyMatch",
    "PowerDesignLinkedMatch",
    "PowerSearchOutcome",
    "build_power_drive_query",
    "evaluate_power_drive_requirement",
]

#: Exactly one active Power `CriterionDefinition` -- Power domain ordinal 1.
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
    """Separated result surfaces for one Power `power_drive` evaluation --
    mirrors `hullq.application.native_inventory_query.NativeInventorySearchOutcome`'s
    separation of design-linked vs. claim-only result surfaces, entirely
    independent of (and structurally distinct from) the Sail outcome type.
    """

    power_drive: str
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


# ---------------------------------------------------------------------------
# Claim-only (design-unresolved) Power path
# ---------------------------------------------------------------------------


def _resolve_power_claim_only_category_from_observations(
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


def _resolve_power_claim_only_admission(
    category_resolution: VesselCategoryResolutionResult,
    publishing_organization_id: MarketplaceOrganizationId,
) -> tuple[bool, PowerCategoryExclusionEvidence | None]:
    """Contract §A: a claim-only candidate is admitted to the Power path iff
    the overall resolution is `POWER` **and** the publishing Organization
    itself (never merely another current claimant) carries an explicit
    current `VALUE_ASSERTION(POWER)` claim -- "Another Organization's
    category assertion cannot lend the publisher its Sail eligibility",
    generalized to POWER.

    Returns `(admitted, exclusion_evidence)`. `exclusion_evidence` is
    populated only when the resolution is explicitly SAIL/MOTORSAILER/
    CONFLICT. A missing/UNKNOWN category, or a POWER resolution contributed
    only by a different Organization, is `(False, None)`: the caller
    classifies that as `INSUFFICIENT_DATA`, never `CONFIRMED_NON_MATCH`.
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


def evaluate_power_claim_only_candidates(
    conn: Any,
    *,
    query: MixedAndQuery,
    as_of: datetime,
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
        category_resolution = _resolve_power_claim_only_category_from_observations(observations)
        admitted, exclusion = _resolve_power_claim_only_admission(
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
                active_definitions=_ACTIVE_POWER_DEFINITIONS,
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

    design_result = run_boat_design_configuration_query(
        conn, query, boat_designs, (POWER_DRIVE_CONFIGURATION_FIELD_PROJECTION_SPEC,)
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
            category_resolution = resolve_physical_boat_vessel_category(
                conn,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_ref=candidate.boat_design_ref,
            )
            if category_resolution.resolution is VesselCategoryResolution.POWER:
                result_class, concrete_evidence = classify_concrete_candidate(
                    conn,
                    native_listing_id=candidate.native_listing_id,
                    publishing_organization_id=candidate.publishing_organization_id,
                    physical_boat_id=candidate.physical_boat_id,
                    boat_design_id=candidate.boat_design_ref.value,
                    query=query,
                    active_definitions=_ACTIVE_POWER_DEFINITIONS,
                )
                category_exclusion = None
            elif category_resolution.resolution in _EXPLICITLY_NON_POWER:
                result_class = ResultClass.CONFIRMED_NON_MATCH
                concrete_evidence = ()
                category_exclusion = PowerCategoryExclusionEvidence(
                    resolution=category_resolution.resolution, reason=category_resolution.reason
                )
            else:
                # UNKNOWN: not yet established as the publisher's own POWER
                # claim -- insufficient, never a false exclusion or a
                # silent Sail-legacy passthrough (there is no legacy Power
                # inventory to preserve compatibility for).
                result_class = ResultClass.INSUFFICIENT_DATA
                concrete_evidence = ()
                category_exclusion = None
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
        query=query,
        design_linked_matches=design_linked_matches,
        design_linked_non_matches=design_linked_non_matches,
        design_linked_insufficient_data=design_linked_insufficient_data,
        claim_only_matches=claim_only_matches,
        claim_only_non_matches=claim_only_non_matches,
        claim_only_insufficient_data=claim_only_insufficient_data,
    )
