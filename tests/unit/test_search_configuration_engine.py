"""Unit tests for hullq.search.configuration_engine — SLICE-0035.

Covers the slice's configuration-truth Required Behavior §C/§D and directly
exercises the adversarial review checklist (slice "Adversarial review
checklist" section) for configuration-level aggregation:

1. one FALSE + one UNKNOWN config -> must NOT become CONFIRMED_NON_MATCH
2. one TRUE + one FALSE/UNKNOWN config -> must be CONFIRMED_MATCH and keep
   the exact matching configuration identity (not "all configurations")
5. an option override never gets flattened into baseline (verified by using
   fully independent ConfigurationProjection instances per configuration)
8. editing a fixture's field values cannot silently redefine the supported
   query fields/enums (field names remain opaque strings throughout)

Also covers: standard vs shallow-draft draft-option fixture (acceptance
criterion), a genuinely configuration-ambiguous design remaining insufficient,
mixed categorical + numeric AND at configuration granularity, deterministic
design_id ordering, and the primary-result-surface boundary (only
CONFIRMED_MATCH counted as a match).

REVIEW amendment Finding 1: end-to-end proof (real
`from_resolution_state_categorical` adapter through to design-level
aggregation) that a reserved categorical sentinel ("unknown") can never
license `CONFIRMED_NON_MATCH`, and that "not_applicable" correctly flows to
FALSE and can license it.

REVIEW amendment Finding 3: a NamedVariantConstraint-governed configuration
composes correctly with normal design-level aggregation, including remaining
INSUFFICIENT_DATA (never a false CONFIRMED_NON_MATCH) when the configuration
space itself is not known to be complete.

REVIEW amendment second round, remaining blocker 1: an unresolved-
applicability option/variant declaration composes correctly with normal
design-level aggregation — a known FALSE configuration plus unresolved
applicability elsewhere is INSUFFICIENT_DATA, never CONFIRMED_NON_MATCH,
while a separately confirmed TRUE configuration still produces
CONFIRMED_MATCH regardless.
"""

from __future__ import annotations

from hullq.domain.provenance import ResolutionState
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    NamedVariantConstraint,
    OptionConstraint,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import (
    evaluate_configuration,
    evaluate_design_configuration_set,
    run_configuration_query,
)
from hullq.search.criteria import CategoricalLeafCriterion, NumericLeafCriterion
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import (
    NumericComparisonKind,
    ReasonCode,
    ResultClass,
    TruthState,
    ValueQualification,
)
from hullq.search.values import (
    QualifiedCategoricalValue,
    QualifiedNumericValue,
    from_resolution_state_categorical,
)


def _confirmed_numeric(value: float) -> QualifiedNumericValue:
    return QualifiedNumericValue(value=value, qualification=ValueQualification.CONFIRMED)


def _unqualified_numeric(
    qualification: ValueQualification = ValueQualification.MISSING,
) -> QualifiedNumericValue:
    return QualifiedNumericValue(value=None, qualification=qualification)


def _confirmed_categorical(value: str) -> QualifiedCategoricalValue:
    return QualifiedCategoricalValue(value=value, qualification=ValueQualification.CONFIRMED)


def _resolved_configuration(
    configuration_id: str,
    design_id: str,
    *,
    draft_max_m: float | None = None,
    draft_qualification: ValueQualification | None = None,
    sailplan: str | None = None,
    applied_option_ids: tuple[str, ...] = (),
) -> ResolvedConfiguration:
    numeric_values: dict[str, QualifiedNumericValue] = {}
    if draft_max_m is not None:
        numeric_values["draft_max_m"] = _confirmed_numeric(draft_max_m)
    elif draft_qualification is not None:
        numeric_values["draft_max_m"] = _unqualified_numeric(draft_qualification)
    categorical_values: dict[str, QualifiedCategoricalValue] = {}
    if sailplan is not None:
        categorical_values["rig.sailplan"] = _confirmed_categorical(sailplan)
    return ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id=configuration_id,
            boat_design_id=design_id,
            applied_option_ids=applied_option_ids,
        ),
        projection=ConfigurationProjection(
            numeric_values=numeric_values, categorical_values=categorical_values
        ),
    )


def _draft_query(threshold_max: float = 1.60) -> MixedAndQuery:
    return MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="draft_max_m",
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=threshold_max,
            ),
        )
    )


# ---------------------------------------------------------------------------
# evaluate_configuration
# ---------------------------------------------------------------------------


def test_evaluate_configuration_true() -> None:
    configuration = _resolved_configuration("cfg-1", "design-1", draft_max_m=1.5)
    evaluation = evaluate_configuration(_draft_query(), configuration)
    assert evaluation.truth is TruthState.TRUE
    assert evaluation.configuration_id == "cfg-1"


def test_evaluate_configuration_false() -> None:
    configuration = _resolved_configuration("cfg-1", "design-1", draft_max_m=1.9)
    evaluation = evaluate_configuration(_draft_query(), configuration)
    assert evaluation.truth is TruthState.FALSE


def test_evaluate_configuration_unknown_on_missing_field() -> None:
    configuration = _resolved_configuration("cfg-1", "design-1")
    evaluation = evaluate_configuration(_draft_query(), configuration)
    assert evaluation.truth is TruthState.UNKNOWN


# ---------------------------------------------------------------------------
# Adversarial Q1: FALSE + UNKNOWN configs must not become CONFIRMED_NON_MATCH
# ---------------------------------------------------------------------------


def test_false_and_unknown_configs_is_insufficient_not_non_match() -> None:
    false_cfg = _resolved_configuration("cfg-false", "design-1", draft_max_m=1.9)
    unknown_cfg = _resolved_configuration("cfg-unknown", "design-1")  # no draft data at all
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(false_cfg, unknown_cfg),
        configuration_space_complete=True,
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA
    assert evaluation.result_class is not ResultClass.CONFIRMED_NON_MATCH
    assert evaluation.matching_configuration_ids == ()


def test_false_and_unknown_configs_insufficient_even_when_space_complete() -> None:
    # Even a *complete* configuration space cannot license NON_MATCH while
    # one member's own truth is UNKNOWN — completeness of the space and
    # resolution of each member are independent requirements.
    false_cfg = _resolved_configuration("cfg-false", "design-1", draft_max_m=1.9)
    unknown_cfg = _resolved_configuration(
        "cfg-unknown", "design-1", draft_qualification=ValueQualification.UNRESOLVED_CONFLICT
    )
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(false_cfg, unknown_cfg),
        configuration_space_complete=True,
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# Adversarial Q2: TRUE + FALSE/UNKNOWN must be CONFIRMED_MATCH with exact identity
# ---------------------------------------------------------------------------


def test_true_and_false_config_is_confirmed_match_with_exact_identity() -> None:
    true_cfg = _resolved_configuration("cfg-shallow", "design-1", draft_max_m=1.5)
    false_cfg = _resolved_configuration("cfg-baseline", "design-1", draft_max_m=1.9)
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(true_cfg, false_cfg),
        configuration_space_complete=True,
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    # Exact identity only — the non-matching baseline must not appear.
    assert evaluation.matching_configuration_ids == ("cfg-shallow",)


def test_true_and_unknown_config_is_confirmed_match_with_exact_identity() -> None:
    true_cfg = _resolved_configuration("cfg-shallow", "design-1", draft_max_m=1.5)
    unknown_cfg = _resolved_configuration("cfg-unknown", "design-1")
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(true_cfg, unknown_cfg),
        configuration_space_complete=False,
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == ("cfg-shallow",)


def test_multiple_true_configs_all_returned_deterministically() -> None:
    cfg_a = _resolved_configuration("cfg-b", "design-1", draft_max_m=1.4)
    cfg_b = _resolved_configuration("cfg-a", "design-1", draft_max_m=1.5)
    config_set = DesignConfigurationSet(
        design_id="design-1", configurations=(cfg_a, cfg_b), configuration_space_complete=True
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == ("cfg-a", "cfg-b")


# ---------------------------------------------------------------------------
# Acceptance criterion: standard vs shallow-draft option fixture
# ---------------------------------------------------------------------------


def test_shallow_draft_option_matches_while_standard_baseline_does_not() -> None:
    baseline = _resolved_configuration("design-42-baseline", "design-42", draft_max_m=1.90)
    shallow_option = _resolved_configuration(
        "design-42-shallow-draft",
        "design-42",
        draft_max_m=1.55,
        applied_option_ids=("OPT-SHALLOW-DRAFT",),
    )
    config_set = DesignConfigurationSet(
        design_id="design-42",
        configurations=(baseline, shallow_option),
        configuration_space_complete=True,
    )
    evaluation = evaluate_design_configuration_set(_draft_query(1.60), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == ("design-42-shallow-draft",)
    # No false universal claim: the baseline configuration itself must be FALSE.
    baseline_eval = next(
        ce
        for ce in evaluation.configuration_evaluations
        if ce.configuration_id == "design-42-baseline"
    )
    assert baseline_eval.truth is TruthState.FALSE


# ---------------------------------------------------------------------------
# CONFIRMED_NON_MATCH — universal, requires complete + all-FALSE
# ---------------------------------------------------------------------------


def test_all_false_and_complete_space_is_confirmed_non_match() -> None:
    cfg = _resolved_configuration("cfg-1", "design-1", draft_max_m=1.9)
    config_set = DesignConfigurationSet(
        design_id="design-1", configurations=(cfg,), configuration_space_complete=True
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_NON_MATCH
    assert evaluation.matching_configuration_ids == ()
    assert evaluation.reason is None


def test_not_configuration_sensitive_single_baseline_non_match() -> None:
    # A design with no named variants/options relevant to the query is just
    # the trivial single-configuration, complete case.
    cfg = _resolved_configuration("design-simple-baseline", "design-simple", draft_max_m=2.10)
    config_set = DesignConfigurationSet(
        design_id="design-simple", configurations=(cfg,), configuration_space_complete=True
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_NON_MATCH


# ---------------------------------------------------------------------------
# Genuinely configuration-ambiguous design remains insufficient
# ---------------------------------------------------------------------------


def test_ambiguous_configuration_space_is_insufficient_with_reason() -> None:
    known_false = _resolved_configuration("design-9-baseline", "design-9", draft_max_m=1.90)
    config_set = DesignConfigurationSet(
        design_id="design-9",
        configurations=(known_false,),
        configuration_space_complete=False,  # a possible shallow-draft option is undocumented
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA
    assert evaluation.reason is ReasonCode.CONFIGURATION_AMBIGUOUS


def test_complete_space_all_false_never_carries_configuration_ambiguous_reason() -> None:
    cfg = _resolved_configuration("cfg-1", "design-1", draft_max_m=1.9)
    config_set = DesignConfigurationSet(
        design_id="design-1", configurations=(cfg,), configuration_space_complete=True
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.reason is None


# ---------------------------------------------------------------------------
# Mixed categorical + numeric AND at configuration granularity
# ---------------------------------------------------------------------------


def test_mixed_categorical_and_numeric_and_query() -> None:
    query = MixedAndQuery(
        criteria=(
            CategoricalLeafCriterion(field="rig.sailplan", equals="cutter"),
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.80
            ),
        )
    )
    matching_cfg = _resolved_configuration(
        "cfg-match", "design-1", draft_max_m=1.70, sailplan="cutter"
    )
    wrong_rig_cfg = _resolved_configuration(
        "cfg-wrong-rig", "design-1", draft_max_m=1.70, sailplan="sloop"
    )
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(matching_cfg, wrong_rig_cfg),
        configuration_space_complete=True,
    )
    evaluation = evaluate_design_configuration_set(query, config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == ("cfg-match",)


# ---------------------------------------------------------------------------
# Option override is never flattened into baseline (adversarial Q5)
# ---------------------------------------------------------------------------


def test_option_configuration_does_not_leak_into_baseline_projection() -> None:
    baseline = _resolved_configuration("cfg-baseline", "design-1", sailplan="sloop")
    cutter_option = _resolved_configuration(
        "cfg-cutter-option", "design-1", sailplan="cutter", applied_option_ids=("OPT-CUTTER",)
    )
    # Independent ConfigurationProjection instances: mutating one cannot
    # affect the other's stored values (dataclass-level isolation).
    assert baseline.projection is not cutter_option.projection
    assert baseline.projection.get_categorical("rig.sailplan").value == "sloop"
    assert cutter_option.projection.get_categorical("rig.sailplan").value == "cutter"


# ---------------------------------------------------------------------------
# run_configuration_query — multi-design engine, primary result boundary
# ---------------------------------------------------------------------------


def test_run_configuration_query_separates_three_surfaces_and_orders_by_design_id() -> None:
    match_set = DesignConfigurationSet(
        design_id="z-match",
        configurations=(_resolved_configuration("z-cfg", "z-match", draft_max_m=1.5),),
        configuration_space_complete=True,
    )
    non_match_set = DesignConfigurationSet(
        design_id="a-non-match",
        configurations=(_resolved_configuration("a-cfg", "a-non-match", draft_max_m=1.9),),
        configuration_space_complete=True,
    )
    insufficient_set = DesignConfigurationSet(
        design_id="m-insufficient",
        configurations=(_resolved_configuration("m-cfg", "m-insufficient"),),
        configuration_space_complete=True,
    )
    outcome = run_configuration_query(_draft_query(), [match_set, non_match_set, insufficient_set])
    assert outcome.confirmed_match_count == 1
    assert outcome.confirmed_non_match_count == 1
    assert outcome.insufficient_data_count == 1
    assert outcome.confirmed_matches[0].design_id == "z-match"
    assert outcome.confirmed_non_matches[0].design_id == "a-non-match"
    assert outcome.insufficient_data[0].design_id == "m-insufficient"


def test_run_configuration_query_ordering_is_stable_regardless_of_input_order() -> None:
    sets = [
        DesignConfigurationSet(
            design_id=design_id,
            configurations=(
                _resolved_configuration(f"{design_id}-cfg", design_id, draft_max_m=1.5),
            ),
            configuration_space_complete=True,
        )
        for design_id in ("z-design", "a-design", "m-design")
    ]
    forward = run_configuration_query(_draft_query(), sets)
    reversed_result = run_configuration_query(_draft_query(), list(reversed(sets)))
    forward_ids = [e.design_id for e in forward.confirmed_matches]
    reversed_ids = [e.design_id for e in reversed_result.confirmed_matches]
    assert forward_ids == reversed_ids == sorted(forward_ids)


# ---------------------------------------------------------------------------
# REVIEW amendment Finding 1 — reserved sentinels through the full pipeline,
# adapter -> leaf -> configuration -> design aggregation
# ---------------------------------------------------------------------------


def _masthead_query() -> MixedAndQuery:
    return MixedAndQuery(
        criteria=(CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead"),)
    )


def test_unknown_sentinel_field_cannot_license_confirmed_non_match() -> None:
    # The only criterion resolves to the reserved "unknown" sentinel through
    # the real adapter; even with a complete, single-configuration space this
    # must remain INSUFFICIENT_DATA, never CONFIRMED_NON_MATCH.
    configuration = ResolvedConfiguration(
        identity=ConfigurationIdentity(configuration_id="cfg-1", boat_design_id="design-1"),
        projection=ConfigurationProjection(
            categorical_values={
                "rig.masthead_fractional": from_resolution_state_categorical(
                    ResolutionState.RESOLVED, "unknown"
                )
            }
        ),
    )
    config_set = DesignConfigurationSet(
        design_id="design-1", configurations=(configuration,), configuration_space_complete=True
    )
    evaluation = evaluate_design_configuration_set(_masthead_query(), config_set)
    assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA
    assert evaluation.result_class is not ResultClass.CONFIRMED_NON_MATCH


def test_not_applicable_sentinel_field_flows_to_confirmed_non_match() -> None:
    # "not_applicable" through the real adapter correctly produces FALSE
    # (confirmed exclusion) at the leaf, and therefore a genuine
    # CONFIRMED_NON_MATCH when it is the only configuration in a complete space.
    configuration = ResolvedConfiguration(
        identity=ConfigurationIdentity(configuration_id="cfg-1", boat_design_id="design-1"),
        projection=ConfigurationProjection(
            categorical_values={
                "rig.masthead_fractional": from_resolution_state_categorical(
                    ResolutionState.RESOLVED, "not_applicable"
                )
            }
        ),
    )
    config_set = DesignConfigurationSet(
        design_id="design-1", configurations=(configuration,), configuration_space_complete=True
    )
    evaluation = evaluate_design_configuration_set(_masthead_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_NON_MATCH
    assert evaluation.configuration_evaluations[0].truth is TruthState.FALSE
    assert evaluation.configuration_evaluations[0].criterion_evaluations[0].reason is (
        ReasonCode.NOT_APPLICABLE
    )


# ---------------------------------------------------------------------------
# REVIEW amendment Finding 3 — NamedVariantConstraint composes with aggregation
# ---------------------------------------------------------------------------


def test_variant_constrained_configuration_evaluates_normally() -> None:
    variant_cfg = _resolved_configuration("cfg-center-cockpit", "design-1", draft_max_m=1.5)
    variant_cfg = ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id="cfg-center-cockpit",
            boat_design_id="design-1",
            named_variant_id="VARIANT-CENTER-COCKPIT",
            applied_option_ids=("OPT-WHEEL-STEERING",),
        ),
        projection=variant_cfg.projection,
    )
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(variant_cfg,),
        configuration_space_complete=True,
        variant_constraints={
            "VARIANT-CENTER-COCKPIT": NamedVariantConstraint(
                variant_id="VARIANT-CENTER-COCKPIT",
                requires_option_ids=frozenset({"OPT-WHEEL-STEERING"}),
            )
        },
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == ("cfg-center-cockpit",)


def test_variant_constrained_configuration_with_incomplete_space_is_insufficient() -> None:
    # Even though the known variant-bearing configuration is itself FALSE,
    # an incomplete configuration space still forces INSUFFICIENT_DATA.
    variant_cfg = _resolved_configuration("cfg-baseline", "design-1", draft_max_m=1.9)
    variant_cfg = ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id="cfg-baseline",
            boat_design_id="design-1",
            named_variant_id="VARIANT-CENTER-COCKPIT",
            applied_option_ids=("OPT-WHEEL-STEERING",),
        ),
        projection=variant_cfg.projection,
    )
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(variant_cfg,),
        configuration_space_complete=False,
        variant_constraints={
            "VARIANT-CENTER-COCKPIT": NamedVariantConstraint(
                variant_id="VARIANT-CENTER-COCKPIT",
                requires_option_ids=frozenset({"OPT-WHEEL-STEERING"}),
            )
        },
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA
    assert evaluation.reason is ReasonCode.CONFIGURATION_AMBIGUOUS


# ---------------------------------------------------------------------------
# REVIEW amendment (second round) — remaining blocker 1: unresolved
# applicability composes correctly with design-level aggregation
# ---------------------------------------------------------------------------


def test_unresolved_applicability_plus_known_false_config_is_insufficient_not_non_match() -> None:
    # The disputed option is declared with unresolved applicability but is
    # not referenced by any configuration (referencing it would be rejected
    # at construction); its mere declaration forces
    # configuration_space_complete=False, so the known FALSE baseline cannot
    # license a universal CONFIRMED_NON_MATCH.
    false_cfg = _resolved_configuration("cfg-baseline", "design-1", draft_max_m=1.9)
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(false_cfg,),
        configuration_space_complete=False,
        option_constraints={
            "OPT-UNRESEARCHED": OptionConstraint(
                option_id="OPT-UNRESEARCHED",
                applicability=ValueQualification.APPLICABILITY_UNKNOWN,
            )
        },
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA
    assert evaluation.result_class is not ResultClass.CONFIRMED_NON_MATCH
    assert evaluation.reason is ReasonCode.CONFIGURATION_AMBIGUOUS


def test_unresolved_applicability_plus_separate_confirmed_true_config_still_matches() -> None:
    # A separately confirmed TRUE configuration still produces
    # CONFIRMED_MATCH, preserving existential-match semantics regardless of
    # unresolved applicability elsewhere in the same design.
    true_cfg = _resolved_configuration("cfg-shallow", "design-1", draft_max_m=1.5)
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(true_cfg,),
        configuration_space_complete=False,
        variant_constraints={
            "VARIANT-UNRESEARCHED": NamedVariantConstraint(
                variant_id="VARIANT-UNRESEARCHED",
                applicability=ValueQualification.APPLICABILITY_UNKNOWN,
            )
        },
    )
    evaluation = evaluate_design_configuration_set(_draft_query(), config_set)
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == ("cfg-shallow",)


def test_constructing_disputed_option_configuration_is_rejected_before_evaluation() -> None:
    # A configuration cannot even be assembled with a disputed option, so it
    # can never reach evaluate_design_configuration_set to begin with.
    disputed_cfg = ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id="cfg-disputed",
            boat_design_id="design-1",
            applied_option_ids=("OPT-UNRESEARCHED",),
        ),
        projection=ConfigurationProjection(),
    )
    try:
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(disputed_cfg,),
            configuration_space_complete=False,
            option_constraints={
                "OPT-UNRESEARCHED": OptionConstraint(
                    option_id="OPT-UNRESEARCHED",
                    applicability=ValueQualification.APPLICABILITY_UNKNOWN,
                )
            },
        )
    except ValueError as exc:
        assert "not CONFIRMED" in str(exc)
    else:
        raise AssertionError("expected ValueError for disputed applicability-unknown option")
