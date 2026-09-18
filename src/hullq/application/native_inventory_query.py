"""Requirements -> Native Inventory Search vertical, generalized to criterion #2 — SLICE-0055.

`hullq.application.inventory_search.evaluate_draft_max_requirement` (SLICE-0051)
remains unchanged and is still used, unmodified, for a pure `draft_max`
request (Required Behavior/contract §8: "A request containing only draft_max
MUST retain accepted SLICE-0051 behavior"). This module is the new bounded
funnel for a request that involves `keel_configuration`, alone or combined
with `draft_max`:

    exact-Decimal draft_max and/or canonical keel_configuration requirement
    -> deterministic BoatDesign/configuration eligibility, merged across
       every active criterion on the same configuration identity
       (hullq.search.boat_design_field_bridge.compatible_boat_design_ids_for_query)
    -> durable design identity admission to ACTIVE, current native inventory
       (hullq.persistence.inventory_search, hullq.application.native_listing_freshness --
        both reused unchanged)
    -> publishing Organization's current concrete PhysicalBoat claim(s) for
       every active field, read from one consistent snapshot
       (hullq.persistence.physical_boat_claims.list_current_physical_boat_claim_observations)
    -> listing-level CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA,
       evaluated by reusing the same MUST-AND kernel primitives
       (hullq.search.configuration_engine.evaluate_configuration) that
       already classify design-level eligibility -- never a bespoke
       hand-rolled combination of per-field if/else branches.

Design/configuration eligibility only establishes possible eligibility
(Required Behavior §C); a concrete listing is confirmed only after the
PUBLISHER's own current PhysicalBoat claim(s) independently confirm every
active criterion -- never backfilled from BoatDesign/configuration truth.

Unlike SLICE-0051's `DraftMaxSearchOutcome` (which counts non-match/
insufficient-data listings but does not identify them), this module's
`NativeInventorySearchOutcome` retains full typed criterion-level evidence
for all three result classes (Required Behavior §G / contract §7): a later
explainability projection may consume it without re-running Search truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from hullq.application.native_listing_freshness import (
    is_current_market_eligible,
    resolve_current_freshness,
)
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.physical_boat_claims import AssertionKind, KeelConfigurationClaim
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.inventory_search import (
    ActiveDesignLinkedListing,
    list_active_design_linked_listings,
)
from hullq.persistence.physical_boat_claims import list_current_physical_boat_claim_observations
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    compatible_boat_design_ids_for_query,
)
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import evaluate_configuration
from hullq.search.criteria import (
    CategoricalLeafCriterion,
    CriterionEvaluation,
    NumericLeafCriterion,
)
from hullq.search.draft_max_design_bridge import (
    DRAFT_MAX_FIELD_PROJECTION_SPEC,
    DRAFT_MAX_PROJECTION_FIELD,
)
from hullq.search.keel_design_bridge import (
    KEEL_CONFIGURATION_FIELD_PROJECTION_SPEC,
    KEEL_CONFIGURATION_PROJECTION_FIELD,
    SEARCH_KEEL_CONFIGURATION_VALUES,
)
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import NumericComparisonKind, ResultClass, TruthState, ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue

__all__ = [
    "NativeInventoryCandidateEvaluation",
    "NativeInventorySearchOutcome",
    "evaluate_native_inventory_requirements",
]


@dataclass(frozen=True, slots=True)
class NativeInventoryCandidateEvaluation:
    """One concrete candidate's classification plus full per-criterion evidence."""

    native_listing_id: NativeListingId
    result_class: ResultClass
    criterion_evaluations: tuple[CriterionEvaluation, ...]
    publishing_organization_id: MarketplaceOrganizationId
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class NativeInventorySearchOutcome:
    """Separated result surfaces for one mixed requirement evaluation.

    `confirmed_matches` is the only primary result set. Unlike SLICE-0051's
    `DraftMaxSearchOutcome`, `confirmed_non_matches`/`insufficient_data` are
    full listings carrying typed criterion-level evidence, not bare counts
    (Required Behavior §G).
    """

    draft_max: Decimal | None
    keel_configuration: str | None
    confirmed_matches: tuple[NativeInventoryCandidateEvaluation, ...]
    confirmed_non_matches: tuple[NativeInventoryCandidateEvaluation, ...]
    insufficient_data: tuple[NativeInventoryCandidateEvaluation, ...]

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)

    @property
    def confirmed_non_match_count(self) -> int:
        return len(self.confirmed_non_matches)

    @property
    def insufficient_data_count(self) -> int:
        return len(self.insufficient_data)


def _confirmed_keel_claim_value(claim: KeelConfigurationClaim) -> str:
    """Extract the Search-vocabulary string from a `VALUE_ASSERTION` keel claim.

    Callers must only pass a claim already known (by their own
    `assertion_kind is AssertionKind.VALUE_ASSERTION` check) to carry a
    value -- `KeelConfigurationClaim.__post_init__` guarantees `value` is
    non-`None` exactly for that assertion kind, but that domain invariant is
    not itself visible to the type checker at the call site.
    """
    assert claim.assertion_kind is AssertionKind.VALUE_ASSERTION
    assert claim.value is not None
    return claim.value.value


def _qualify_claim_field(
    *,
    publisher_assertion_kind: AssertionKind | None,
    publisher_value: Any,
    cross_organization_values: set[Any],
) -> tuple[ValueQualification, Any]:
    """Fail-closed concrete-claim qualification shared by draft/keel (contract §3).

    Missing/omitted or explicit `UNKNOWN` publisher claim -> `MISSING`
    (never guessed). More than one distinct current value across every
    claiming Organization for this PhysicalBoatId (the same-PhysicalBoat
    contradiction guard, SLICE-0051 §G / contract §3) -> `MISSING`. Otherwise
    the publisher's own current value is `CONFIRMED` -- never backfilled
    from BoatDesign/configuration truth.
    """
    if publisher_assertion_kind is None or publisher_assertion_kind is AssertionKind.UNKNOWN:
        return (ValueQualification.MISSING, None)
    if len(cross_organization_values) > 1:
        return (ValueQualification.MISSING, None)
    return (ValueQualification.CONFIRMED, publisher_value)


def _classify_candidate(
    conn: Any,
    candidate: ActiveDesignLinkedListing,
    query: MixedAndQuery,
    *,
    draft_active: bool,
    keel_active: bool,
) -> tuple[ResultClass, tuple[CriterionEvaluation, ...]]:
    """Classify one design-eligible, currently-fresh candidate.

    Reads every active field's current cross-Organization observation set
    from one call to `list_current_physical_boat_claim_observations` (one
    SQL statement, therefore one consistent PostgreSQL MVCC snapshot for
    both draft and keel -- mirrors the SLICE-0051 Finding 5 rationale), then
    reuses the exact same `evaluate_configuration` MUST-AND kernel already
    used for design-level eligibility to combine the active criteria's
    concrete truth: any confirmed FALSE prevents a confirmed joint match;
    unresolved evidence never becomes TRUE (Required Behavior §B).
    """
    observations = list_current_physical_boat_claim_observations(conn, candidate.physical_boat_id)
    publisher_observation = next(
        (
            obs
            for obs in observations
            if obs.claiming_organization_id == candidate.publishing_organization_id
        ),
        None,
    )

    numeric_values: dict[str, QualifiedNumericValue] = {}
    categorical_values: dict[str, QualifiedCategoricalValue] = {}

    if draft_active:
        draft_claim = publisher_observation.draft if publisher_observation is not None else None
        cross_organization_draft_values = {
            obs.draft.value
            for obs in observations
            if obs.draft is not None and obs.draft.assertion_kind is AssertionKind.VALUE_ASSERTION
        }
        qualification, value = _qualify_claim_field(
            publisher_assertion_kind=(
                draft_claim.assertion_kind if draft_claim is not None else None
            ),
            publisher_value=draft_claim.value if draft_claim is not None else None,
            cross_organization_values=cross_organization_draft_values,
        )
        numeric_values[DRAFT_MAX_PROJECTION_FIELD] = QualifiedNumericValue(
            value=value if qualification is ValueQualification.CONFIRMED else None,
            qualification=qualification,
        )

    if keel_active:
        keel_claim = (
            publisher_observation.keel_configuration if publisher_observation is not None else None
        )
        cross_organization_keel_values = {
            _confirmed_keel_claim_value(obs.keel_configuration)
            for obs in observations
            if obs.keel_configuration is not None
            and obs.keel_configuration.assertion_kind is AssertionKind.VALUE_ASSERTION
        }
        publisher_keel_value = (
            _confirmed_keel_claim_value(keel_claim)
            if keel_claim is not None and keel_claim.assertion_kind is AssertionKind.VALUE_ASSERTION
            else None
        )
        qualification, value = _qualify_claim_field(
            publisher_assertion_kind=(
                keel_claim.assertion_kind if keel_claim is not None else None
            ),
            publisher_value=publisher_keel_value,
            cross_organization_values=cross_organization_keel_values,
        )
        categorical_values[KEEL_CONFIGURATION_PROJECTION_FIELD] = QualifiedCategoricalValue(
            value=value if qualification is ValueQualification.CONFIRMED else None,
            qualification=qualification,
        )

    projection = ConfigurationProjection(
        numeric_values=numeric_values, categorical_values=categorical_values
    )
    pseudo_configuration = ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id=candidate.native_listing_id.value,
            boat_design_id=candidate.boat_design_ref.value,
        ),
        projection=projection,
    )
    evaluation = evaluate_configuration(query, pseudo_configuration)
    if evaluation.truth is TruthState.TRUE:
        result_class = ResultClass.CONFIRMED_MATCH
    elif evaluation.truth is TruthState.FALSE:
        result_class = ResultClass.CONFIRMED_NON_MATCH
    else:
        result_class = ResultClass.INSUFFICIENT_DATA
    return result_class, evaluation.criterion_evaluations


def evaluate_native_inventory_requirements(
    conn: Any,
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    as_of: datetime,
) -> NativeInventorySearchOutcome:
    """Evaluate the bounded mixed vertical against real persisted state.

    At least one of *draft_max*/*keel_configuration* must be supplied.
    *draft_max* must already be an exact positive finite `Decimal`
    (`hullq.search.draft_max_request.parse_draft_max_decimal`).
    *keel_configuration* must already be one of
    `hullq.search.keel_design_bridge.SEARCH_KEEL_CONFIGURATION_VALUES`.
    Neither is re-parsed/re-validated for public syntax here.

    SLICE-0052 contract §7.2 (reused unchanged): every ACTIVE design-linked
    candidate is freshness-resolved at the explicit *as_of* boundary before
    any technical classification. STALE/UNKNOWN candidates are excluded
    outright -- never counted as insufficient data.
    """
    if draft_max is None and keel_configuration is None:
        raise ValueError("at least one of draft_max/keel_configuration must be supplied")
    if draft_max is not None and (
        not isinstance(draft_max, Decimal) or not draft_max.is_finite() or draft_max <= 0
    ):
        raise ValueError(f"draft_max must be a positive finite Decimal; got {draft_max!r}")
    if (
        keel_configuration is not None
        and keel_configuration not in SEARCH_KEEL_CONFIGURATION_VALUES
    ):
        raise ValueError(
            f"keel_configuration must be one of {sorted(SEARCH_KEEL_CONFIGURATION_VALUES)}; "
            f"got {keel_configuration!r}"
        )

    criteria: list[NumericLeafCriterion | CategoricalLeafCriterion] = []
    specs: list[FieldProjectionSpec] = []
    if draft_max is not None:
        criteria.append(
            NumericLeafCriterion(
                field=DRAFT_MAX_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=draft_max,
            )
        )
        specs.append(DRAFT_MAX_FIELD_PROJECTION_SPEC)
    if keel_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=KEEL_CONFIGURATION_PROJECTION_FIELD, equals=keel_configuration
            )
        )
        specs.append(KEEL_CONFIGURATION_FIELD_PROJECTION_SPEC)
    query = MixedAndQuery(criteria=tuple(criteria))

    def _empty() -> NativeInventorySearchOutcome:
        return NativeInventorySearchOutcome(
            draft_max=draft_max,
            keel_configuration=keel_configuration,
            confirmed_matches=(),
            confirmed_non_matches=(),
            insufficient_data=(),
        )

    all_candidates = list_active_design_linked_listings(conn)
    if not all_candidates:
        return _empty()

    current_candidates = []
    for candidate in all_candidates:
        freshness = resolve_current_freshness(conn, candidate.native_listing_id, as_of=as_of)
        if is_current_market_eligible(freshness.status):
            current_candidates.append((candidate, freshness))
    if not current_candidates:
        return _empty()

    distinct_design_ids = sorted({c.boat_design_ref.value for c, _ in current_candidates})
    boat_designs = []
    for design_id in distinct_design_ids:
        raw_design = fetch_boat_design(conn, design_id)
        if raw_design is not None:
            boat_designs.append(raw_design)

    compatible_ids = compatible_boat_design_ids_for_query(conn, query, boat_designs, tuple(specs))

    confirmed_matches: list[NativeInventoryCandidateEvaluation] = []
    confirmed_non_matches: list[NativeInventoryCandidateEvaluation] = []
    insufficient_data: list[NativeInventoryCandidateEvaluation] = []

    for candidate, freshness in current_candidates:
        if candidate.boat_design_ref.value not in compatible_ids:
            continue
        result_class, criterion_evaluations = _classify_candidate(
            conn,
            candidate,
            query,
            draft_active=draft_max is not None,
            keel_active=keel_configuration is not None,
        )
        evaluation = NativeInventoryCandidateEvaluation(
            native_listing_id=candidate.native_listing_id,
            result_class=result_class,
            criterion_evaluations=criterion_evaluations,
            publishing_organization_id=candidate.publishing_organization_id,
            freshness_status=freshness.status,
            last_confirmed_at=freshness.last_confirmed_at,
        )
        if result_class is ResultClass.CONFIRMED_MATCH:
            confirmed_matches.append(evaluation)
        elif result_class is ResultClass.CONFIRMED_NON_MATCH:
            confirmed_non_matches.append(evaluation)
        else:
            insufficient_data.append(evaluation)

    confirmed_matches.sort(key=lambda m: m.native_listing_id.value)
    confirmed_non_matches.sort(key=lambda m: m.native_listing_id.value)
    insufficient_data.sort(key=lambda m: m.native_listing_id.value)

    return NativeInventorySearchOutcome(
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        confirmed_matches=tuple(confirmed_matches),
        confirmed_non_matches=tuple(confirmed_non_matches),
        insufficient_data=tuple(insufficient_data),
    )
