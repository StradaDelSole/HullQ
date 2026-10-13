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
       (hullq.search.boat_design_field_bridge.run_boat_design_configuration_query)
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

## Evidence preservation (contract §6/§7, amendment Finding 1)

Unlike SLICE-0051's `DraftMaxSearchOutcome` (which counts non-match/
insufficient-data listings but does not identify them), this module's
`NativeInventorySearchOutcome` retains full typed evidence for all three
result classes:

- `NativeInventorySearchOutcome.query` is the exact `MixedAndQuery` that was
  evaluated, so every candidate's requested criterion value/comparison
  (`NumericLeafCriterion`/`CategoricalLeafCriterion`, already typed) is
  recoverable without re-running Search truth;
- `NativeInventoryCandidateEvaluation.design_evaluation` is the *complete,
  unmodified* `hullq.search.configuration_engine.DesignQueryEvaluation` for
  the candidate's BoatDesign -- never collapsed to a bare confirmed/not-
  confirmed boolean. It carries `matching_configuration_ids` (the exact
  resolved BoatDesign/NamedVariant configuration identity/identities that
  admitted the design, per Required Behavior §D) and the full per-
  configuration `configuration_evaluations` (each itself a per-criterion
  `CriterionEvaluation`), including for a design that is `INSUFFICIENT_DATA`
  (e.g. an unsupported keel taxonomy mapping) or a `CONFIRMED_NON_MATCH` --
  such a design's listings are classified accordingly and *this* evidence is
  attached, rather than the listing silently disappearing from every result
  surface;
- `NativeInventoryCandidateEvaluation.design_configuration_evidence` closes
  the second amendment's Finding 1 gap: `design_evaluation` alone carries
  each evaluated configuration's `CriterionEvaluation` (typed truth/reason)
  but not the BoatDesign/NamedVariant canonical value that was actually
  qualified and compared to produce it -- `evaluate_configuration` reads
  that value from `ResolvedConfiguration.projection` but does not return it,
  and the `DesignConfigurationSet`/`ResolvedConfiguration` objects
  themselves go out of scope once `run_configuration_query` returns. This
  module retains them (via `hullq.search.boat_design_field_bridge.
  run_boat_design_configuration_query`'s `configurations_by_id`) and pairs
  each of `design_evaluation.configuration_evaluations`' own per-criterion
  `CriterionEvaluation` with the exact requested criterion and the safely
  resolved/observed canonical value used, one `ConfigurationEvidence` per
  evaluated BoatDesign/NamedVariant configuration -- present for every
  design result class (match, non-match, insufficient alike), never only
  for the configurations that matched;
- `NativeInventoryCandidateEvaluation.concrete_criterion_evidence` is the
  concrete PhysicalBoat-level evidence, kept separate from the design-level
  evidence above (contract §7 point 6). Each `SearchCriterionEvidence` pairs
  the exact requested `NumericLeafCriterion`/`CategoricalLeafCriterion`, the
  unmodified `CriterionEvaluation` (typed truth + reason code), and the
  safely observed/resolved concrete canonical value when one exists (never
  encoded only inside `CriterionEvaluation.explanation` text) -- mirroring
  the typed `resolved_draft_m` field SLICE-0051's own
  `DraftMaxConfirmedMatch` already carried, generalized to both criteria and
  to the non-match/insufficient classes SLICE-0051 only counted.

No second Search truth engine is introduced and the established
`hullq.search.configuration_engine` kernel types
(`ConfigurationEvaluation`/`DesignQueryEvaluation`/`ConfigurationSearchOutcome`)
are never modified. `SearchCriterionEvidence`/`ConfigurationEvidence` are
bounded typed wrappers reused for both the design-side and concrete-side
evidence, adding only the one piece of information the kernel types do not
carry (the resolved/observed value) -- never re-derived from
`CriterionEvaluation.explanation` text.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from hullq.application.current_public_eligibility import resolve_current_public_eligibility
from hullq.application.native_listing_freshness import resolve_current_freshness
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId, PhysicalBoatId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    KeelConfigurationClaim,
    RudderConfigurationClaim,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.inventory_search import list_active_design_linked_listings
from hullq.persistence.physical_boat_claims import list_current_physical_boat_claim_observations
from hullq.search.boat_design_field_bridge import (
    BoatDesignConfigurationQueryResult,
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    run_boat_design_configuration_query,
)
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import (
    ConfigurationEvaluation,
    ConfigurationSearchOutcome,
    DesignQueryEvaluation,
    evaluate_configuration,
    run_configuration_query,
)
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
from hullq.search.loa_design_bridge import LOA_FIELD_PROJECTION_SPEC, LOA_PROJECTION_FIELD
from hullq.search.query_mixed import MixedAndQuery, MixedLeafCriterion
from hullq.search.rudder_design_bridge import (
    RUDDER_CONFIGURATION_PROJECTION_FIELD,
    SEARCH_RUDDER_CONFIGURATION_VALUES,
    build_boat_design_rudder_configuration_set,
)
from hullq.search.types import NumericComparisonKind, ResultClass, TruthState, ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue

__all__ = [
    "ConfigurationEvidence",
    "NativeInventoryCandidateEvaluation",
    "NativeInventorySearchOutcome",
    "SearchCriterionEvidence",
    "build_configuration_evidence",
    "build_mixed_requirement_query",
    "classify_concrete_candidate",
    "evaluate_native_inventory_requirements",
    "run_mixed_boat_design_configuration_query",
]


@dataclass(frozen=True, slots=True)
class SearchCriterionEvidence:
    """Typed per-criterion concrete evidence (contract §6/§7, Finding 1).

    Pairs the exact requested leaf criterion (already typed with its own
    field/comparison/thresholds or `equals` value) with the unmodified
    `CriterionEvaluation` result (typed truth + reason code) and, when one
    exists, the safely observed/resolved concrete canonical value -- e.g. the
    publisher's own current `draft` (`Decimal`) or `keel_configuration`
    (`str`) claim. `observed_value` is `None` whenever `evaluation.truth` is
    not derived from a `CONFIRMED` qualified value (missing/UNKNOWN/
    unresolved-conflict evidence never fabricates an observed value).
    """

    criterion: MixedLeafCriterion
    evaluation: CriterionEvaluation
    observed_value: Decimal | str | None


@dataclass(frozen=True, slots=True)
class ConfigurationEvidence:
    """One resolved BoatDesign/NamedVariant configuration's typed evidence
    (contract §7, second amendment Finding 1).

    `configuration_id`/`boat_design_id`/`named_variant_id` are the exact
    resolved configuration identity `hullq.search.configuration.
    ConfigurationIdentity` already carries (`named_variant_id` is `None`
    for the baseline configuration). `truth` is this configuration's own
    aggregate `hullq.search.configuration_engine.ConfigurationEvaluation.truth`.
    `criterion_evidence` pairs each requested criterion with its
    per-criterion `CriterionEvaluation` and the safely resolved/observed
    BoatDesign/NamedVariant canonical value actually used for that
    evaluation (from the exact `ResolvedConfiguration.projection` that was
    evaluated) -- never fabricated, and never re-derived from
    `CriterionEvaluation.explanation` text.
    """

    configuration_id: str
    boat_design_id: str
    named_variant_id: str | None
    truth: TruthState
    criterion_evidence: tuple[SearchCriterionEvidence, ...]


@dataclass(frozen=True, slots=True)
class NativeInventoryCandidateEvaluation:
    """One concrete candidate's classification plus full typed evidence.

    `design_evaluation` is the complete, unmodified design-level
    `DesignQueryEvaluation` for this candidate's BoatDesign -- present even
    when `result_class` is `CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA` at the
    design level, in which case `concrete_criterion_evidence` is empty
    because the concrete PhysicalBoat claim was never consulted (design/
    configuration eligibility never admitted the design to the concrete
    funnel at all -- Required Behavior §C). When the design *is* a design-
    level `CONFIRMED_MATCH`, `concrete_criterion_evidence` carries the
    concrete classification's own per-criterion evidence, and `result_class`
    reflects that concrete classification, not the design-level one.

    `design_configuration_evidence` is always populated, one
    `ConfigurationEvidence` per entry in
    `design_evaluation.configuration_evaluations` (baseline and every
    evaluated NamedVariant alike, regardless of which one(s) matched) --
    the typed BoatDesign/NamedVariant observed-value evidence
    `design_evaluation` alone cannot recover (second amendment Finding 1).
    """

    native_listing_id: NativeListingId
    result_class: ResultClass
    design_evaluation: DesignQueryEvaluation
    design_configuration_evidence: tuple[ConfigurationEvidence, ...]
    concrete_criterion_evidence: tuple[SearchCriterionEvidence, ...]
    publishing_organization_id: MarketplaceOrganizationId
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class NativeInventorySearchOutcome:
    """Separated result surfaces for one mixed requirement evaluation.

    `confirmed_matches` is the only primary result set. Unlike SLICE-0051's
    `DraftMaxSearchOutcome`, `confirmed_non_matches`/`insufficient_data` are
    full listings carrying typed design- and concrete-level evidence, not
    bare counts (Required Behavior §G). `query` is the exact evaluated
    `MixedAndQuery`, carrying every active criterion's own requested
    value/comparison.
    """

    draft_max: Decimal | None
    keel_configuration: str | None
    loa_min: Decimal | None
    loa_max: Decimal | None
    rudder_configuration: str | None
    query: MixedAndQuery
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


def _confirmed_rudder_claim_value(claim: RudderConfigurationClaim) -> str:
    """Extract the Search-vocabulary string from a `VALUE_ASSERTION` rudder claim.

    Mirrors `_confirmed_keel_claim_value` exactly -- see that function's
    docstring.
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


def _observed_projection_value(
    resolved_configuration: ResolvedConfiguration, criterion: MixedLeafCriterion
) -> Decimal | str | None:
    """The safely resolved/observed BoatDesign/NamedVariant canonical value
    *criterion* was actually compared against in *resolved_configuration*,
    or `None` when that field's qualification is not `CONFIRMED` -- read
    directly from `ResolvedConfiguration.projection` (never fabricated, and
    independent of `CriterionEvaluation.explanation` text).
    """
    if isinstance(criterion, NumericLeafCriterion):
        qualified_numeric = resolved_configuration.projection.get_numeric(criterion.field)
        if qualified_numeric.qualification is not ValueQualification.CONFIRMED:
            return None
        # Every SLICE-0055 numeric FieldProjectionSpec decodes via
        # decode_decimal_for_qualification, which QualifiedNumericValue
        # preserves as an exact Decimal, never coerced to float -- see that
        # class's docstring.
        assert isinstance(qualified_numeric.value, Decimal)
        return qualified_numeric.value
    qualified_categorical = resolved_configuration.projection.get_categorical(criterion.field)
    if qualified_categorical.qualification is not ValueQualification.CONFIRMED:
        return None
    assert qualified_categorical.value is not None
    return qualified_categorical.value


def build_configuration_evidence(
    query: MixedAndQuery,
    configuration_evaluation: ConfigurationEvaluation,
    resolved_configuration: ResolvedConfiguration,
) -> ConfigurationEvidence:
    """Build one `ConfigurationEvidence` for *resolved_configuration* (second
    amendment Finding 1): pairs each of `query.criteria`, in order, with its
    `configuration_evaluation.criterion_evaluations` counterpart (the same
    order `hullq.search.configuration_engine.evaluate_configuration` used to
    produce them) and the safely resolved/observed canonical value read from
    `resolved_configuration.projection` -- the exact `ResolvedConfiguration`
    `build_boat_design_configuration_set` built and `run_configuration_query`
    evaluated, never re-derived from `CriterionEvaluation.explanation`.
    """
    criterion_evidence = tuple(
        SearchCriterionEvidence(
            criterion=criterion,
            evaluation=criterion_evaluation,
            observed_value=_observed_projection_value(resolved_configuration, criterion),
        )
        for criterion, criterion_evaluation in zip(
            query.criteria, configuration_evaluation.criterion_evaluations, strict=True
        )
    )
    identity = resolved_configuration.identity
    return ConfigurationEvidence(
        configuration_id=identity.configuration_id,
        boat_design_id=identity.boat_design_id,
        named_variant_id=identity.named_variant_id,
        truth=configuration_evaluation.truth,
        criterion_evidence=criterion_evidence,
    )


def classify_concrete_candidate(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    publishing_organization_id: MarketplaceOrganizationId,
    physical_boat_id: PhysicalBoatId,
    boat_design_id: str,
    query: MixedAndQuery,
    draft_active: bool,
    keel_active: bool,
    loa_active: bool = False,
    rudder_active: bool = False,
) -> tuple[ResultClass, tuple[SearchCriterionEvidence, ...]]:
    """Classify one design-eligible, currently-fresh candidate's concrete
    PhysicalBoat claims.

    Reads every active field's current cross-Organization observation set
    from one call to `list_current_physical_boat_claim_observations` (one
    SQL statement, therefore one consistent PostgreSQL MVCC snapshot for
    both draft and keel -- mirrors the SLICE-0051 Finding 5 rationale), then
    reuses the exact same `evaluate_configuration` MUST-AND kernel already
    used for design-level eligibility to combine the active criteria's
    concrete truth: any confirmed FALSE prevents a confirmed joint match;
    unresolved evidence never becomes TRUE (Required Behavior §B).

    Returns typed `SearchCriterionEvidence` (requested criterion + typed
    evaluation + safely observed concrete value), not bare
    `CriterionEvaluation`, so the observed value is preserved through the
    application boundary rather than existing only inside
    `CriterionEvaluation.explanation` text (Finding 1).

    Takes the resolved identity fields directly (rather than an
    `ActiveDesignLinkedListing`) so both the public bulk native-inventory
    funnel (`evaluate_native_inventory_requirements`, below) and SLICE-0084's
    authorized single-target hypothetical DRAFT preview
    (`hullq.application.broker_search_fit`) call the identical concrete
    classification kernel -- never a second, independently maintained
    concrete-claim truth path.
    """
    observations = list_current_physical_boat_claim_observations(conn, physical_boat_id)
    publisher_observation = next(
        (obs for obs in observations if obs.claiming_organization_id == publishing_organization_id),
        None,
    )

    numeric_values: dict[str, QualifiedNumericValue] = {}
    categorical_values: dict[str, QualifiedCategoricalValue] = {}
    observed_by_field: dict[str, Decimal | str | None] = {}

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
        is_confirmed = qualification is ValueQualification.CONFIRMED
        numeric_values[DRAFT_MAX_PROJECTION_FIELD] = QualifiedNumericValue(
            value=value if is_confirmed else None, qualification=qualification
        )
        observed_by_field[DRAFT_MAX_PROJECTION_FIELD] = value if is_confirmed else None

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
        is_confirmed = qualification is ValueQualification.CONFIRMED
        categorical_values[KEEL_CONFIGURATION_PROJECTION_FIELD] = QualifiedCategoricalValue(
            value=value if is_confirmed else None, qualification=qualification
        )
        observed_by_field[KEEL_CONFIGURATION_PROJECTION_FIELD] = value if is_confirmed else None

    if loa_active:
        loa_claim = publisher_observation.loa_length if publisher_observation is not None else None
        cross_organization_loa_values = {
            obs.loa_length.value
            for obs in observations
            if obs.loa_length is not None
            and obs.loa_length.assertion_kind is AssertionKind.VALUE_ASSERTION
        }
        qualification, value = _qualify_claim_field(
            publisher_assertion_kind=(loa_claim.assertion_kind if loa_claim is not None else None),
            publisher_value=loa_claim.value if loa_claim is not None else None,
            cross_organization_values=cross_organization_loa_values,
        )
        is_confirmed = qualification is ValueQualification.CONFIRMED
        numeric_values[LOA_PROJECTION_FIELD] = QualifiedNumericValue(
            value=value if is_confirmed else None, qualification=qualification
        )
        observed_by_field[LOA_PROJECTION_FIELD] = value if is_confirmed else None

    if rudder_active:
        rudder_claim = (
            publisher_observation.rudder_configuration
            if publisher_observation is not None
            else None
        )
        cross_organization_rudder_values = {
            _confirmed_rudder_claim_value(obs.rudder_configuration)
            for obs in observations
            if obs.rudder_configuration is not None
            and obs.rudder_configuration.assertion_kind is AssertionKind.VALUE_ASSERTION
        }
        publisher_rudder_value = (
            _confirmed_rudder_claim_value(rudder_claim)
            if rudder_claim is not None
            and rudder_claim.assertion_kind is AssertionKind.VALUE_ASSERTION
            else None
        )
        qualification, value = _qualify_claim_field(
            publisher_assertion_kind=(
                rudder_claim.assertion_kind if rudder_claim is not None else None
            ),
            publisher_value=publisher_rudder_value,
            cross_organization_values=cross_organization_rudder_values,
        )
        is_confirmed = qualification is ValueQualification.CONFIRMED
        categorical_values[RUDDER_CONFIGURATION_PROJECTION_FIELD] = QualifiedCategoricalValue(
            value=value if is_confirmed else None, qualification=qualification
        )
        observed_by_field[RUDDER_CONFIGURATION_PROJECTION_FIELD] = value if is_confirmed else None

    projection = ConfigurationProjection(
        numeric_values=numeric_values, categorical_values=categorical_values
    )
    pseudo_configuration = ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id=native_listing_id.value,
            boat_design_id=boat_design_id,
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

    # `evaluate_configuration` evaluates `query.criteria` in that exact order
    # (hullq.search.configuration_engine.evaluate_configuration), so pairing
    # by position is safe and avoids re-deriving field identity by string
    # matching.
    evidence = tuple(
        SearchCriterionEvidence(
            criterion=criterion,
            evaluation=criterion_evaluation,
            observed_value=observed_by_field.get(criterion.field),
        )
        for criterion, criterion_evaluation in zip(
            query.criteria, evaluation.criterion_evaluations, strict=True
        )
    )
    return result_class, evidence


def build_mixed_requirement_query(
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    loa_min: Decimal | None = None,
    loa_max: Decimal | None = None,
    rudder_configuration: str | None = None,
) -> tuple[MixedAndQuery, tuple[FieldProjectionSpec, ...], bool]:
    """Validate and build the bounded multi-criterion `MixedAndQuery` + its
    matching `FieldProjectionSpec`s + whether `rudder_configuration` is active.

    Shared by the public bulk native-inventory funnel
    (`evaluate_native_inventory_requirements`, below) and SLICE-0084's
    authorized single-target hypothetical DRAFT preview
    (`hullq.application.broker_search_fit`), so the MUST/AND query this
    bounded vertical evaluates is constructed in exactly one place -- never
    a second, independently maintained query-construction path for any of
    the accepted criteria.

    At least one criterion must be supplied. Every value must already be
    parsed/validated for public syntax by its own accepted parser
    (`hullq.search.draft_max_request.parse_draft_max_decimal`,
    `hullq.search.keel_design_bridge.SEARCH_KEEL_CONFIGURATION_VALUES`,
    `hullq.search.loa_request.parse_loa_decimal`,
    `hullq.search.rudder_design_bridge.SEARCH_RUDDER_CONFIGURATION_VALUES`)
    -- none is re-parsed/re-validated here.

    `rudder_configuration` is returned as its own boolean (SLICE-0085) rather
    than folded into *specs*: unlike every other criterion, its design-side
    projection is a generation-aware derived value
    (`hullq.search.rudder_design_bridge.build_boat_design_rudder_configuration_set`),
    not a single `FieldProjectionSpec` the generic shared bridge can project
    -- see `_run_mixed_boat_design_configuration_query`, below.
    """
    if (
        draft_max is None
        and keel_configuration is None
        and loa_min is None
        and loa_max is None
        and rudder_configuration is None
    ):
        raise ValueError("at least one criterion must be supplied")
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
    for label, bound in (("loa_min", loa_min), ("loa_max", loa_max)):
        if bound is not None and (
            not isinstance(bound, Decimal) or not bound.is_finite() or bound <= 0
        ):
            raise ValueError(f"{label} must be a positive finite Decimal; got {bound!r}")
    if loa_min is not None and loa_max is not None and loa_min > loa_max:
        raise ValueError(f"loa_min ({loa_min}) must be <= loa_max ({loa_max})")
    if (
        rudder_configuration is not None
        and rudder_configuration not in SEARCH_RUDDER_CONFIGURATION_VALUES
    ):
        raise ValueError(
            f"rudder_configuration must be one of {sorted(SEARCH_RUDDER_CONFIGURATION_VALUES)}; "
            f"got {rudder_configuration!r}"
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
    if loa_min is not None or loa_max is not None:
        # SLICE-0085 normative LOA semantics: both bounds project against the
        # SAME deduplicated loa_m FieldProjectionSpec, as two independent
        # numeric leaves -- never a single RANGE leaf (which would merge
        # their evidence into one explanation) and never a duplicated spec.
        if loa_min is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=LOA_PROJECTION_FIELD,
                    comparison=NumericComparisonKind.MINIMUM,
                    threshold_min=loa_min,
                )
            )
        if loa_max is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=LOA_PROJECTION_FIELD,
                    comparison=NumericComparisonKind.MAXIMUM,
                    threshold_max=loa_max,
                )
            )
        specs.append(LOA_FIELD_PROJECTION_SPEC)
    rudder_active = rudder_configuration is not None
    if rudder_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=RUDDER_CONFIGURATION_PROJECTION_FIELD, equals=rudder_configuration
            )
        )
    return MixedAndQuery(criteria=tuple(criteria)), tuple(specs), rudder_active


def _merge_design_configuration_set_with_rudder(
    base_set: DesignConfigurationSet | None, rudder_set: DesignConfigurationSet
) -> DesignConfigurationSet:
    """Merge *rudder_set* (the generation-aware derived `rudder_configuration`
    projection for one design, `hullq.search.rudder_design_bridge.
    build_boat_design_rudder_configuration_set`) into *base_set* (the
    ordinary `FieldProjectionSpec`-driven projection for the same design's
    other active criteria), by `configuration_id`.

    Both builders enumerate the identical baseline + eligible-NamedVariant
    configuration set for the same `boat_design` (same exclusion of a
    variant with unresolved `requires_option_ids`,
    `hullq.search.boat_design_field_bridge.build_boat_design_configuration_set`'s
    own documented rule) -- their `configuration_id`s are therefore always
    identical sets, so a direct per-id lookup (never positional zipping) is
    safe. *base_set* is `None` when `rudder_configuration` is the only
    active criterion (no other `FieldProjectionSpec` was ever projected for
    this design), in which case *rudder_set* alone is returned unchanged.
    """
    if base_set is None:
        return rudder_set
    rudder_by_id = {
        configuration.identity.configuration_id: configuration
        for configuration in rudder_set.configurations
    }
    merged_configurations = tuple(
        ResolvedConfiguration(
            identity=configuration.identity,
            projection=ConfigurationProjection(
                numeric_values=dict(configuration.projection.numeric_values),
                categorical_values={
                    **configuration.projection.categorical_values,
                    **rudder_by_id[
                        configuration.identity.configuration_id
                    ].projection.categorical_values,
                },
            ),
        )
        for configuration in base_set.configurations
    )
    return DesignConfigurationSet(
        design_id=base_set.design_id,
        configurations=merged_configurations,
        configuration_space_complete=base_set.configuration_space_complete,
        option_constraints=base_set.option_constraints,
        variant_constraints=base_set.variant_constraints,
        is_fixture=base_set.is_fixture,
    )


def run_mixed_boat_design_configuration_query(
    conn: Any,
    query: MixedAndQuery,
    boat_designs: Iterable[Mapping[str, Any]],
    specs: Sequence[FieldProjectionSpec],
    *,
    rudder_active: bool,
) -> BoatDesignConfigurationQueryResult:
    """Evaluate *query* against every design's configuration set, merging the
    generation-aware derived `rudder_configuration` projection into the
    ordinary `FieldProjectionSpec`-driven one when *rudder_active* (SLICE-0085).

    When *rudder_active* is `False` this is a byte-for-byte delegation to the
    unmodified `hullq.search.boat_design_field_bridge.
    run_boat_design_configuration_query` -- every pre-0085 caller (a pure
    `draft_max`/`keel_configuration`/`loa` request, in any combination) sees
    zero behavior change. `rudder_configuration` cannot be expressed as a
    single `FieldProjectionSpec` (its design-side truth depends on which of
    two schema generations a design actually carries -- see
    `hullq.search.rudder_design_bridge`'s docstring), so this is the one
    bounded merge point `build_mixed_requirement_query`'s own `rudder_active`
    return value is for -- never a second, independently maintained
    FieldResolution/configuration-evaluation kernel.
    """
    if not rudder_active:
        return run_boat_design_configuration_query(conn, query, boat_designs, specs)

    boat_designs = tuple(boat_designs)
    if not boat_designs:
        return BoatDesignConfigurationQueryResult(
            outcome=ConfigurationSearchOutcome(
                confirmed_matches=(), confirmed_non_matches=(), insufficient_data=()
            ),
            configurations_by_id={},
        )
    merged_sets = tuple(
        _merge_design_configuration_set_with_rudder(
            build_boat_design_configuration_set(conn, boat_design, specs) if specs else None,
            build_boat_design_rudder_configuration_set(conn, boat_design),
        )
        for boat_design in boat_designs
    )
    configurations_by_id = {
        configuration.identity.configuration_id: configuration
        for configuration_set in merged_sets
        for configuration in configuration_set.configurations
    }
    outcome = run_configuration_query(query, merged_sets)
    return BoatDesignConfigurationQueryResult(
        outcome=outcome, configurations_by_id=configurations_by_id
    )


def evaluate_native_inventory_requirements(
    conn: Any,
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    loa_min: Decimal | None = None,
    loa_max: Decimal | None = None,
    rudder_configuration: str | None = None,
    as_of: datetime,
) -> NativeInventorySearchOutcome:
    """Evaluate the bounded mixed vertical against real persisted state.

    At least one criterion must be supplied. Every value must already be
    parsed/validated for public syntax by its own accepted parser -- see
    `build_mixed_requirement_query`'s docstring for the exact list. None is
    re-parsed/re-validated for public syntax here.

    SLICE-0069 (supersedes the SLICE-0052 §7.2 freshness-only narrowing):
    every ACTIVE design-linked candidate is resolved against the canonical
    D29 CurrentPublicEligibility authority
    (`hullq.application.current_public_eligibility`) at the explicit *as_of*
    boundary before any technical classification. Current-public-ineligible
    candidates are excluded outright -- never counted as insufficient data.

    Finding 1 (amendment): a candidate whose BoatDesign is *not* a design-
    level `CONFIRMED_MATCH` is no longer silently dropped from every result
    surface. Its `DesignQueryEvaluation` (`CONFIRMED_NON_MATCH` or
    `INSUFFICIENT_DATA`, e.g. an unsupported keel taxonomy mapping) is
    attached and the listing is classified accordingly -- fail-closed,
    outside the primary confirmed-match set, but never erased from the
    application evidence. A candidate whose BoatDesign could not even be
    durably fetched (`hullq.persistence.identity_readback.fetch_boat_design`
    returns `None` -- a dangling `BoatDesignRef`, a distinct data-integrity
    condition from an evaluated-but-insufficient design) is excluded exactly
    as SLICE-0051's own funnel excludes it: there is no `DesignQueryEvaluation`
    to attach because the design was never evaluated at all.

    Finding 1 (second amendment): every candidate's
    `NativeInventoryCandidateEvaluation.design_configuration_evidence` is
    populated from `hullq.search.boat_design_field_bridge.
    run_boat_design_configuration_query`'s `configurations_by_id`, so the
    safely resolved/observed BoatDesign/NamedVariant canonical value behind
    each design-side criterion evaluation remains typed and recoverable,
    not only the aggregate truth/reason `DesignQueryEvaluation` itself
    carries.
    """
    query, specs, rudder_active = build_mixed_requirement_query(
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
    )

    def _empty() -> NativeInventorySearchOutcome:
        return NativeInventorySearchOutcome(
            draft_max=draft_max,
            keel_configuration=keel_configuration,
            loa_min=loa_min,
            loa_max=loa_max,
            rudder_configuration=rudder_configuration,
            query=query,
            confirmed_matches=(),
            confirmed_non_matches=(),
            insufficient_data=(),
        )

    all_candidates = list_active_design_linked_listings(conn)
    if not all_candidates:
        return _empty()

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
        return _empty()

    distinct_design_ids = sorted({c.boat_design_ref.value for c, _ in current_candidates})
    boat_designs = []
    for design_id in distinct_design_ids:
        raw_design = fetch_boat_design(conn, design_id)
        if raw_design is not None:
            boat_designs.append(raw_design)

    design_result = run_mixed_boat_design_configuration_query(
        conn, query, boat_designs, tuple(specs), rudder_active=rudder_active
    )
    design_evaluation_by_id: dict[str, DesignQueryEvaluation] = {
        evaluation.design_id: evaluation
        for evaluation in (
            design_result.outcome.confirmed_matches
            + design_result.outcome.confirmed_non_matches
            + design_result.outcome.insufficient_data
        )
    }

    confirmed_matches: list[NativeInventoryCandidateEvaluation] = []
    confirmed_non_matches: list[NativeInventoryCandidateEvaluation] = []
    insufficient_data: list[NativeInventoryCandidateEvaluation] = []

    for candidate, freshness in current_candidates:
        design_evaluation = design_evaluation_by_id.get(candidate.boat_design_ref.value)
        if design_evaluation is None:
            # Dangling BoatDesignRef (no durable canonical design to
            # evaluate at all) -- never a candidate, exactly like SLICE-0051.
            continue

        design_configuration_evidence = tuple(
            build_configuration_evidence(
                query,
                configuration_evaluation,
                design_result.configurations_by_id[configuration_evaluation.configuration_id],
            )
            for configuration_evaluation in design_evaluation.configuration_evaluations
        )

        if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
            result_class, concrete_evidence = classify_concrete_candidate(
                conn,
                native_listing_id=candidate.native_listing_id,
                publishing_organization_id=candidate.publishing_organization_id,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_id=candidate.boat_design_ref.value,
                query=query,
                draft_active=draft_max is not None,
                keel_active=keel_configuration is not None,
                loa_active=loa_min is not None or loa_max is not None,
                rudder_active=rudder_active,
            )
        else:
            # Design/configuration eligibility never admitted this design to
            # the concrete funnel (Required Behavior §C) -- the listing is
            # classified directly from the design-level result, fail-closed,
            # without ever consulting the concrete PhysicalBoat claim.
            # Finding 1: this evidence is retained, not discarded.
            result_class = design_evaluation.result_class
            concrete_evidence = ()

        evaluation = NativeInventoryCandidateEvaluation(
            native_listing_id=candidate.native_listing_id,
            result_class=result_class,
            design_evaluation=design_evaluation,
            design_configuration_evidence=design_configuration_evidence,
            concrete_criterion_evidence=concrete_evidence,
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
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
        query=query,
        confirmed_matches=tuple(confirmed_matches),
        confirmed_non_matches=tuple(confirmed_non_matches),
        insufficient_data=tuple(insufficient_data),
    )
