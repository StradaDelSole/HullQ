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
from hullq.application.vessel_category_resolution import resolve_physical_boat_vessel_category
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId, PhysicalBoatId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.physical_boat_claims import AssertionKind
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.domain.vessel_category import VesselCategoryExclusionEvidence
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.inventory_search import list_active_design_linked_listings
from hullq.persistence.physical_boat_claims import list_current_physical_boat_claim_observations
from hullq.search.boat_design_field_bridge import BoatDesignConfigurationQueryResult
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
from hullq.search.criteria_registry import (
    BEAM_DEFINITION,
    COCKPIT_POSITION_DEFINITION,
    DECK_SALOON_DEFINITION,
    DRAFT_MAX_DEFINITION,
    HULL_CONFIGURATION_DEFINITION,
    HULL_MATERIAL_DEFINITION,
    KEEL_CONFIGURATION_DEFINITION,
    LOA_DEFINITION,
    RUDDER_CONFIGURATION_DEFINITION,
    CriterionDefinition,
    CriterionKind,
)
from hullq.search.query_mixed import MixedAndQuery, MixedLeafCriterion
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

    `vessel_category_exclusion` is populated only when the SLICE-0091 §C
    category pre-filter itself produced this `CONFIRMED_NON_MATCH` (the
    design level was a `CONFIRMED_MATCH` but the resolved vessel category is
    explicitly `POWER`/`MOTORSAILER`/`CONFLICT`) -- `None` in every other
    case, including an ordinary nine-criterion technical non-match/
    insufficient-data result and a design/configuration-level exclusion.
    Amendment review Finding I: without this, such a candidate was
    mechanically indistinguishable from an ordinary technical mismatch, with
    zero retained evidence explaining why. Deliberately the bounded,
    cross-Organization-identity-free `VesselCategoryExclusionEvidence`, never
    the full `VesselCategoryResolutionResult` (see that type's docstring).
    """

    native_listing_id: NativeListingId
    result_class: ResultClass
    design_evaluation: DesignQueryEvaluation
    design_configuration_evidence: tuple[ConfigurationEvidence, ...]
    concrete_criterion_evidence: tuple[SearchCriterionEvidence, ...]
    vessel_category_exclusion: VesselCategoryExclusionEvidence | None
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
    hull_configuration: str | None
    cockpit_position: str | None
    deck_saloon: str | None
    beam_min: Decimal | None
    beam_max: Decimal | None
    hull_material: str | None
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
    active_definitions: Sequence[CriterionDefinition],
) -> tuple[ResultClass, tuple[SearchCriterionEvidence, ...]]:
    """Classify one design-eligible, currently-fresh candidate's concrete
    PhysicalBoat claims.

    Reads every active field's current cross-Organization observation set
    from one call to `list_current_physical_boat_claim_observations` (one
    SQL statement, therefore one consistent PostgreSQL MVCC snapshot across
    every active criterion -- mirrors the SLICE-0051 Finding 5 rationale),
    then reuses the exact same `evaluate_configuration` MUST-AND kernel
    already used for design-level eligibility to combine the active
    criteria's concrete truth: any confirmed FALSE prevents a confirmed
    joint match; unresolved evidence never becomes TRUE (Required
    Behavior §B).

    Review amendment (Finding C): *active_definitions* replaces four
    previously hand-duplicated per-criterion boolean flags/blocks. Every
    `hullq.search.criteria_registry.CriterionDefinition.read_claim` has the
    identical `(observation) -> (assertion_kind, value) | None` shape, so
    the same-PhysicalBoat cross-Organization qualification
    (`_qualify_claim_field`) now runs in one shared loop over whichever
    definitions are active, rather than one copy-pasted block per
    criterion -- this is the registry's "concrete publisher accessor"
    being genuinely consumed, not merely declared.

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

    for definition in active_definitions:
        publisher_entry = (
            definition.read_claim(publisher_observation)
            if publisher_observation is not None
            else None
        )
        cross_organization_values = {
            entry[1]
            for obs in observations
            if (entry := definition.read_claim(obs)) is not None
            and entry[0] is AssertionKind.VALUE_ASSERTION
        }
        qualification, value = _qualify_claim_field(
            publisher_assertion_kind=publisher_entry[0] if publisher_entry is not None else None,
            publisher_value=publisher_entry[1] if publisher_entry is not None else None,
            cross_organization_values=cross_organization_values,
        )
        is_confirmed = qualification is ValueQualification.CONFIRMED
        resolved_value = value if is_confirmed else None
        if definition.kind is CriterionKind.CATEGORICAL:
            categorical_values[definition.projection_field] = QualifiedCategoricalValue(
                value=resolved_value, qualification=qualification
            )
        else:
            numeric_values[definition.projection_field] = QualifiedNumericValue(
                value=resolved_value, qualification=qualification
            )
        observed_by_field[definition.projection_field] = resolved_value

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
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
    beam_min: Decimal | None = None,
    beam_max: Decimal | None = None,
    hull_material: str | None = None,
) -> tuple[MixedAndQuery, tuple[CriterionDefinition, ...]]:
    """Validate and build the bounded multi-criterion `MixedAndQuery` + the
    exact `hullq.search.criteria_registry.CriterionDefinition`s active in it.

    Shared by the public bulk native-inventory funnel
    (`evaluate_native_inventory_requirements`, below) and SLICE-0084's
    authorized single-target hypothetical DRAFT preview
    (`hullq.application.broker_search_fit`), so the MUST/AND query this
    bounded vertical evaluates is constructed in exactly one place -- never
    a second, independently maintained query-construction path for any of
    the accepted criteria.

    At least one criterion must be supplied. Every value must already be
    parsed/validated for public syntax by its own accepted parser (each
    `CriterionDefinition`'s own `parse_value`/`allowed_values`) -- none is
    re-parsed/re-validated here, only re-checked as a defensive invariant.

    Review amendment (Finding C): the returned `active_definitions` replaces
    the previous `(specs, rudder_active)` pair -- `run_mixed_boat_design_
    configuration_query` and `classify_concrete_candidate` both consume the
    SAME tuple directly, so "which criteria are active" is computed exactly
    once per request, not re-derived at each call site.
    """
    if (
        draft_max is None
        and keel_configuration is None
        and loa_min is None
        and loa_max is None
        and rudder_configuration is None
        and hull_configuration is None
        and cockpit_position is None
        and deck_saloon is None
        and beam_min is None
        and beam_max is None
        and hull_material is None
    ):
        raise ValueError("at least one criterion must be supplied")
    if draft_max is not None and (
        not isinstance(draft_max, Decimal) or not draft_max.is_finite() or draft_max <= 0
    ):
        raise ValueError(f"draft_max must be a positive finite Decimal; got {draft_max!r}")
    assert KEEL_CONFIGURATION_DEFINITION.allowed_values is not None
    if (
        keel_configuration is not None
        and keel_configuration not in KEEL_CONFIGURATION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"keel_configuration must be one of "
            f"{sorted(KEEL_CONFIGURATION_DEFINITION.allowed_values)}; got {keel_configuration!r}"
        )
    for label, bound in (("loa_min", loa_min), ("loa_max", loa_max)):
        if bound is not None and (
            not isinstance(bound, Decimal) or not bound.is_finite() or bound <= 0
        ):
            raise ValueError(f"{label} must be a positive finite Decimal; got {bound!r}")
    if loa_min is not None and loa_max is not None and loa_min > loa_max:
        raise ValueError(f"loa_min ({loa_min}) must be <= loa_max ({loa_max})")
    assert RUDDER_CONFIGURATION_DEFINITION.allowed_values is not None
    if (
        rudder_configuration is not None
        and rudder_configuration not in RUDDER_CONFIGURATION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"rudder_configuration must be one of "
            f"{sorted(RUDDER_CONFIGURATION_DEFINITION.allowed_values)}; got {rudder_configuration!r}"
        )
    assert HULL_CONFIGURATION_DEFINITION.allowed_values is not None
    if (
        hull_configuration is not None
        and hull_configuration not in HULL_CONFIGURATION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"hull_configuration must be one of "
            f"{sorted(HULL_CONFIGURATION_DEFINITION.allowed_values)}; got {hull_configuration!r}"
        )
    assert COCKPIT_POSITION_DEFINITION.allowed_values is not None
    if (
        cockpit_position is not None
        and cockpit_position not in COCKPIT_POSITION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"cockpit_position must be one of "
            f"{sorted(COCKPIT_POSITION_DEFINITION.allowed_values)}; got {cockpit_position!r}"
        )
    assert DECK_SALOON_DEFINITION.allowed_values is not None
    if deck_saloon is not None and deck_saloon not in DECK_SALOON_DEFINITION.allowed_values:
        raise ValueError(
            f"deck_saloon must be one of "
            f"{sorted(DECK_SALOON_DEFINITION.allowed_values)}; got {deck_saloon!r}"
        )
    for label, bound in (("beam_min", beam_min), ("beam_max", beam_max)):
        if bound is not None and (
            not isinstance(bound, Decimal) or not bound.is_finite() or bound <= 0
        ):
            raise ValueError(f"{label} must be a positive finite Decimal; got {bound!r}")
    if beam_min is not None and beam_max is not None and beam_min > beam_max:
        raise ValueError(f"beam_min ({beam_min}) must be <= beam_max ({beam_max})")
    assert HULL_MATERIAL_DEFINITION.allowed_values is not None
    if hull_material is not None and hull_material not in HULL_MATERIAL_DEFINITION.allowed_values:
        raise ValueError(
            f"hull_material must be one of "
            f"{sorted(HULL_MATERIAL_DEFINITION.allowed_values)}; got {hull_material!r}"
        )

    criteria: list[NumericLeafCriterion | CategoricalLeafCriterion] = []
    active_definitions: list[CriterionDefinition] = []
    if draft_max is not None:
        criteria.append(
            NumericLeafCriterion(
                field=DRAFT_MAX_DEFINITION.projection_field,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=draft_max,
            )
        )
        active_definitions.append(DRAFT_MAX_DEFINITION)
    if keel_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=KEEL_CONFIGURATION_DEFINITION.projection_field, equals=keel_configuration
            )
        )
        active_definitions.append(KEEL_CONFIGURATION_DEFINITION)
    if loa_min is not None or loa_max is not None:
        # SLICE-0085 normative LOA semantics: both bounds project against the
        # SAME deduplicated loa_m field, as two independent numeric leaves --
        # never a single RANGE leaf (which would merge their evidence into
        # one explanation) and never a duplicated design-side build.
        if loa_min is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=LOA_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MINIMUM,
                    threshold_min=loa_min,
                )
            )
        if loa_max is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=LOA_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MAXIMUM,
                    threshold_max=loa_max,
                )
            )
        active_definitions.append(LOA_DEFINITION)
    if rudder_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=RUDDER_CONFIGURATION_DEFINITION.projection_field, equals=rudder_configuration
            )
        )
        active_definitions.append(RUDDER_CONFIGURATION_DEFINITION)
    if hull_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=HULL_CONFIGURATION_DEFINITION.projection_field, equals=hull_configuration
            )
        )
        active_definitions.append(HULL_CONFIGURATION_DEFINITION)
    if cockpit_position is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=COCKPIT_POSITION_DEFINITION.projection_field, equals=cockpit_position
            )
        )
        active_definitions.append(COCKPIT_POSITION_DEFINITION)
    if deck_saloon is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=DECK_SALOON_DEFINITION.projection_field, equals=deck_saloon
            )
        )
        active_definitions.append(DECK_SALOON_DEFINITION)
    if beam_min is not None or beam_max is not None:
        # SLICE-0087 normative beam semantics: both bounds project against
        # the SAME deduplicated beam_m field, as two independent numeric
        # leaves -- mirrors LOA's identical rule.
        if beam_min is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=BEAM_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MINIMUM,
                    threshold_min=beam_min,
                )
            )
        if beam_max is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=BEAM_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MAXIMUM,
                    threshold_max=beam_max,
                )
            )
        active_definitions.append(BEAM_DEFINITION)
    if hull_material is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=HULL_MATERIAL_DEFINITION.projection_field, equals=hull_material
            )
        )
        active_definitions.append(HULL_MATERIAL_DEFINITION)
    return MixedAndQuery(criteria=tuple(criteria)), tuple(active_definitions)


def _merge_configuration_sets(
    design_id: str, configuration_sets: Sequence[DesignConfigurationSet]
) -> DesignConfigurationSet:
    """Merge every active criterion's own `DesignConfigurationSet` for one
    design into a single combined set, by `configuration_id`.

    Review amendment (Finding C): generalizes the previous rudder-only
    special-case merge to every active `CriterionDefinition.design_set_
    builder` uniformly -- draft_max/keel_configuration/loa (ordinary
    `FieldProjectionSpec`-backed) and rudder_configuration (generation-aware
    derived) are merged by the exact same code path, never a second
    "ordinary vs. special" branch. Every builder enumerates the identical
    baseline + eligible-NamedVariant configuration set for the same
    `boat_design` (same exclusion of a variant with unresolved
    `requires_option_ids`), so their `configuration_id`s are always
    identical sets across all of *configuration_sets* -- a direct per-id
    lookup (never positional zipping) is safe. A single-element input is
    returned unchanged (no-op merge).
    """
    if len(configuration_sets) == 1:
        return configuration_sets[0]
    by_id_per_set = [
        {c.identity.configuration_id: c for c in s.configurations} for s in configuration_sets
    ]
    base_by_id = by_id_per_set[0]
    base_set = configuration_sets[0]
    merged_configurations = []
    for configuration_id, base_config in base_by_id.items():
        numeric_values: dict[str, Any] = dict(base_config.projection.numeric_values)
        categorical_values: dict[str, Any] = dict(base_config.projection.categorical_values)
        for other_by_id in by_id_per_set[1:]:
            other_config = other_by_id[configuration_id]
            numeric_values.update(other_config.projection.numeric_values)
            categorical_values.update(other_config.projection.categorical_values)
        merged_configurations.append(
            ResolvedConfiguration(
                identity=base_config.identity,
                projection=ConfigurationProjection(
                    numeric_values=numeric_values, categorical_values=categorical_values
                ),
            )
        )
    return DesignConfigurationSet(
        design_id=design_id,
        configurations=tuple(merged_configurations),
        configuration_space_complete=base_set.configuration_space_complete,
        option_constraints=base_set.option_constraints,
        variant_constraints=base_set.variant_constraints,
        is_fixture=base_set.is_fixture,
    )


def run_mixed_boat_design_configuration_query(
    conn: Any,
    query: MixedAndQuery,
    boat_designs: Iterable[Mapping[str, Any]],
    active_definitions: Sequence[CriterionDefinition],
) -> BoatDesignConfigurationQueryResult:
    """Evaluate *query* against every design's configuration set, merging
    every active criterion's own `design_set_builder` output (SLICE-0085,
    review amendment Finding C).

    Review amendment (Finding C): replaces the previous "ordinary
    `FieldProjectionSpec`-list fast path, with a rudder-only special merge"
    split -- every active definition's `design_set_builder` is called and
    merged uniformly via `_merge_configuration_sets`, regardless of whether
    its own projection is `FieldProjectionSpec`-backed or a generation-aware
    derived value. No second, independently maintained FieldResolution/
    configuration-evaluation kernel is introduced; `run_configuration_query`
    (the unmodified shared kernel) still does the actual truth evaluation.
    """
    boat_designs = tuple(boat_designs)
    if not boat_designs:
        return BoatDesignConfigurationQueryResult(
            outcome=ConfigurationSearchOutcome(
                confirmed_matches=(), confirmed_non_matches=(), insufficient_data=()
            ),
            configurations_by_id={},
        )
    merged_sets = tuple(
        _merge_configuration_sets(
            boat_design["id"],
            [definition.design_set_builder(conn, boat_design) for definition in active_definitions],
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
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
    beam_min: Decimal | None = None,
    beam_max: Decimal | None = None,
    hull_material: str | None = None,
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
    populated from `run_mixed_boat_design_configuration_query`'s
    `configurations_by_id`, so the safely resolved/observed BoatDesign/
    NamedVariant canonical value behind each design-side criterion
    evaluation remains typed and recoverable, not only the aggregate
    truth/reason `DesignQueryEvaluation` itself carries.
    """
    query, active_definitions = build_mixed_requirement_query(
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
        hull_configuration=hull_configuration,
        cockpit_position=cockpit_position,
        deck_saloon=deck_saloon,
        beam_min=beam_min,
        beam_max=beam_max,
        hull_material=hull_material,
    )

    def _empty() -> NativeInventorySearchOutcome:
        return NativeInventorySearchOutcome(
            draft_max=draft_max,
            keel_configuration=keel_configuration,
            loa_min=loa_min,
            loa_max=loa_max,
            rudder_configuration=rudder_configuration,
            hull_configuration=hull_configuration,
            cockpit_position=cockpit_position,
            deck_saloon=deck_saloon,
            beam_min=beam_min,
            beam_max=beam_max,
            hull_material=hull_material,
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
            # SLICE-0091 §A/§C: category is an admission/type foundation,
            # not a tenth technical Sail criterion -- this fail-closed
            # pre-filter runs *before* the concrete nine-criterion
            # classification, never alongside it as a CriterionDefinition.
            # An explicit POWER/MOTORSAILER/CONFLICT resolution excludes the
            # candidate from a confirmed Sail match outright; UNKNOWN
            # (including every legacy null-category row) is deliberately
            # untouched, preserving exact pre-0091 Sail-only behavior.
            category_resolution = resolve_physical_boat_vessel_category(
                conn,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_ref=candidate.boat_design_ref,
            )
            if category_resolution.is_explicitly_non_sail_or_conflicted:
                result_class = ResultClass.CONFIRMED_NON_MATCH
                concrete_evidence = ()
                # Amendment Finding I: retain *why* -- bounded, enum-only,
                # never the full result (which can name a different
                # claiming Organization under CROSS_ORGANIZATION_DISAGREEMENT).
                vessel_category_exclusion = VesselCategoryExclusionEvidence(
                    resolution=category_resolution.resolution,
                    reason=category_resolution.reason,
                )
            else:
                result_class, concrete_evidence = classify_concrete_candidate(
                    conn,
                    native_listing_id=candidate.native_listing_id,
                    publishing_organization_id=candidate.publishing_organization_id,
                    physical_boat_id=candidate.physical_boat_id,
                    boat_design_id=candidate.boat_design_ref.value,
                    query=query,
                    active_definitions=active_definitions,
                )
                vessel_category_exclusion = None
        else:
            # Design/configuration eligibility never admitted this design to
            # the concrete funnel (Required Behavior §C) -- the listing is
            # classified directly from the design-level result, fail-closed,
            # without ever consulting the concrete PhysicalBoat claim.
            # Finding 1: this evidence is retained, not discarded.
            result_class = design_evaluation.result_class
            concrete_evidence = ()
            vessel_category_exclusion = None

        evaluation = NativeInventoryCandidateEvaluation(
            native_listing_id=candidate.native_listing_id,
            result_class=result_class,
            design_evaluation=design_evaluation,
            design_configuration_evidence=design_configuration_evidence,
            concrete_criterion_evidence=concrete_evidence,
            vessel_category_exclusion=vessel_category_exclusion,
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
        hull_configuration=hull_configuration,
        cockpit_position=cockpit_position,
        deck_saloon=deck_saloon,
        beam_min=beam_min,
        beam_max=beam_max,
        hull_material=hull_material,
        query=query,
        confirmed_matches=tuple(confirmed_matches),
        confirmed_non_matches=tuple(confirmed_non_matches),
        insufficient_data=tuple(insufficient_data),
    )
