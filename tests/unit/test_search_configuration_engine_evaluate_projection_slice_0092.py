"""Unit tests for `hullq.search.configuration_engine.evaluate_projection` — SLICE-0092.

`evaluate_projection` is the pure leaf-evaluation + `and_reduce` body
factored out of `evaluate_configuration` (contract §C exact implementation
boundary: "safely factor the existing leaf-evaluation + and_reduce loop into
a pure shared projection-evaluation helper consumed by the unchanged
design-linked wrapper and the new publisher-claim path"). These tests prove:

1. `evaluate_projection` combines TRUE/FALSE/UNKNOWN leaves with the exact
   same MUST/AND semantics `evaluate_configuration` already has (any
   confirmed FALSE -> FALSE; otherwise any UNKNOWN -> UNKNOWN; otherwise
   TRUE) -- it is not a second, independently maintained aggregation rule.
2. `evaluate_configuration` and `evaluate_projection`, given the identical
   `MixedAndQuery` and `ConfigurationProjection`, produce the identical
   aggregate truth and per-criterion evaluations -- proving the factoring
   changed no design-linked behavior (byte-for-byte non-regression).
3. `evaluate_projection` never requires a `ConfigurationIdentity`/
   `boat_design_id` at all -- it operates on a bare `ConfigurationProjection`,
   exactly the contract's "never wrapped in a fake ConfigurationIdentity or
   given an invented design ID" requirement for the claim-only path.
"""

from __future__ import annotations

from decimal import Decimal

from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import evaluate_configuration, evaluate_projection
from hullq.search.criteria import CategoricalLeafCriterion, NumericLeafCriterion
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import NumericComparisonKind, TruthState, ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue


def _confirmed_numeric(value: Decimal) -> QualifiedNumericValue:
    return QualifiedNumericValue(value=value, qualification=ValueQualification.CONFIRMED)


def _missing_numeric() -> QualifiedNumericValue:
    return QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING)


def _confirmed_categorical(value: str) -> QualifiedCategoricalValue:
    return QualifiedCategoricalValue(value=value, qualification=ValueQualification.CONFIRMED)


def test_evaluate_projection_true_when_every_leaf_confirmed_and_satisfied() -> None:
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.6
            ),
            CategoricalLeafCriterion(field="keel_configuration", equals="FIN"),
        )
    )
    projection = ConfigurationProjection(
        numeric_values={"draft_max_m": _confirmed_numeric(Decimal("1.4"))},
        categorical_values={"keel_configuration": _confirmed_categorical("FIN")},
    )
    truth, evaluations = evaluate_projection(query, projection)
    assert truth is TruthState.TRUE
    assert len(evaluations) == 2
    assert all(e.truth is TruthState.TRUE for e in evaluations)


def test_evaluate_projection_false_wins_over_unknown() -> None:
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.0
            ),
            CategoricalLeafCriterion(field="keel_configuration", equals="FIN"),
        )
    )
    projection = ConfigurationProjection(
        numeric_values={"draft_max_m": _confirmed_numeric(Decimal("1.4"))},  # FALSE (1.4 > 1.0)
        categorical_values={},  # keel_configuration missing -> UNKNOWN
    )
    truth, _ = evaluate_projection(query, projection)
    assert truth is TruthState.FALSE


def test_evaluate_projection_unknown_when_no_false_but_one_unresolved() -> None:
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.6
            ),
            CategoricalLeafCriterion(field="keel_configuration", equals="FIN"),
        )
    )
    projection = ConfigurationProjection(
        numeric_values={"draft_max_m": _confirmed_numeric(Decimal("1.4"))},  # TRUE
        categorical_values={},  # keel_configuration missing -> UNKNOWN
    )
    truth, _ = evaluate_projection(query, projection)
    assert truth is TruthState.UNKNOWN


def test_evaluate_projection_never_requires_configuration_identity() -> None:
    """Contract §C: the claim-only path must be able to evaluate a bare
    `ConfigurationProjection` with no `ConfigurationIdentity`/`boat_design_id`
    at all -- `evaluate_projection`'s signature itself proves this (it takes
    only `query`/`projection`, never an identity)."""
    query = MixedAndQuery(
        criteria=(CategoricalLeafCriterion(field="keel_configuration", equals="FIN"),)
    )
    projection = ConfigurationProjection(
        categorical_values={"keel_configuration": _confirmed_categorical("FIN")}
    )
    truth, evaluations = evaluate_projection(query, projection)
    assert truth is TruthState.TRUE
    assert len(evaluations) == 1


def test_evaluate_projection_matches_evaluate_configuration_identical_inputs() -> None:
    """Non-regression: factoring `evaluate_projection` out of
    `evaluate_configuration` must not change the design-linked wrapper's own
    aggregate truth or per-criterion evaluations for the identical inputs."""
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.6
            ),
            CategoricalLeafCriterion(field="keel_configuration", equals="FIN"),
        )
    )
    projection = ConfigurationProjection(
        numeric_values={"draft_max_m": _confirmed_numeric(Decimal("1.4"))},
        categorical_values={"keel_configuration": _confirmed_categorical("FIN")},
    )
    configuration = ResolvedConfiguration(
        identity=ConfigurationIdentity(configuration_id="CFG-1", boat_design_id="BD-1"),
        projection=projection,
    )

    wrapped = evaluate_configuration(query, configuration)
    bare_truth, bare_evaluations = evaluate_projection(query, projection)

    assert wrapped.truth is bare_truth
    assert wrapped.criterion_evaluations == bare_evaluations
    assert wrapped.configuration_id == "CFG-1"


def test_evaluate_projection_missing_value_never_becomes_true() -> None:
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.6
            ),
        )
    )
    projection = ConfigurationProjection(numeric_values={"draft_max_m": _missing_numeric()})
    truth, evaluations = evaluate_projection(query, projection)
    assert truth is TruthState.UNKNOWN
    assert evaluations[0].truth is TruthState.UNKNOWN
