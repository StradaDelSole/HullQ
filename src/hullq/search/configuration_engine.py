"""Configuration-aware BoatDesign evaluator — SLICE-0035.

Implements slice Required Behavior §C (configuration truth) and §D (matching
configuration identity): a BoatDesign is discoverable when at least one
explicit resolved configuration satisfies the complete MUST query
(existential), while confirmed exclusion requires every materially
applicable, sufficiently resolved configuration to evaluate FALSE
(universal). See `hullq.search.configuration.DesignConfigurationSet` for the
persistence-neutral input contract this module consumes — it is never built
here from raw BoatDesign/FieldResolution data (slice Required Behavior §E).

Does not implement: automatic configuration expansion, PREFER, OR/NOT, or
ranking.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from hullq.search.configuration import (
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.criteria import (
    CriterionEvaluation,
    NumericLeafCriterion,
    evaluate_categorical_leaf,
    evaluate_numeric_leaf,
)
from hullq.search.query import and_reduce
from hullq.search.query_mixed import MixedAndQuery, MixedLeafCriterion
from hullq.search.types import ReasonCode, ResultClass, TruthState

__all__ = [
    "ConfigurationEvaluation",
    "ConfigurationSearchOutcome",
    "DesignQueryEvaluation",
    "evaluate_configuration",
    "evaluate_design_configuration_set",
    "run_configuration_query",
]


def _evaluate_leaf(
    criterion: MixedLeafCriterion, projection: ConfigurationProjection
) -> CriterionEvaluation:
    if isinstance(criterion, NumericLeafCriterion):
        return evaluate_numeric_leaf(criterion, projection.get_numeric(criterion.field))
    return evaluate_categorical_leaf(criterion, projection.get_categorical(criterion.field))


@dataclass(frozen=True, slots=True)
class ConfigurationEvaluation:
    """One resolved configuration's aggregate truth plus per-criterion explanation."""

    configuration_id: str
    truth: TruthState
    criterion_evaluations: tuple[CriterionEvaluation, ...]


def evaluate_configuration(
    query: MixedAndQuery, configuration: ResolvedConfiguration
) -> ConfigurationEvaluation:
    """Evaluate every leaf of *query* against one resolved configuration.

    Criterion ordering may affect explanation order but never affects
    aggregate truth (`and_reduce` is order-independent) — slice Required
    Behavior §B.
    """
    evaluations = tuple(
        _evaluate_leaf(criterion, configuration.projection) for criterion in query.criteria
    )
    aggregate = and_reduce(tuple(e.truth for e in evaluations))
    return ConfigurationEvaluation(
        configuration_id=configuration.identity.configuration_id,
        truth=aggregate,
        criterion_evaluations=evaluations,
    )


@dataclass(frozen=True, slots=True)
class DesignQueryEvaluation:
    """One BoatDesign's configuration-aware result — slice Required Behavior §C/§D.

    `matching_configuration_ids` is the deterministic, complete set of every
    resolved configuration that is a confirmed TRUE match, sorted by
    `configuration_id`; it is non-empty if and only if `result_class` is
    `CONFIRMED_MATCH`. A FALSE configuration never erases a TRUE one, and an
    UNKNOWN configuration is never dropped merely to manufacture a
    design-level `CONFIRMED_NON_MATCH` — see `evaluate_design_configuration_set`.
    """

    design_id: str
    result_class: ResultClass
    matching_configuration_ids: tuple[str, ...]
    configuration_evaluations: tuple[ConfigurationEvaluation, ...]
    reason: ReasonCode | None


def evaluate_design_configuration_set(
    query: MixedAndQuery, config_set: DesignConfigurationSet
) -> DesignQueryEvaluation:
    """Aggregate per-configuration truth into one design-level result.

    - `CONFIRMED_MATCH` — at least one resolved configuration is TRUE
      (existential; slice Required Behavior §C). Every TRUE configuration id
      is returned, not an arbitrary favorite (slice Required Behavior §D).
    - `CONFIRMED_NON_MATCH` — no configuration is TRUE, every listed
      configuration is a confirmed FALSE (never UNKNOWN), and the caller
      declared `configuration_space_complete=True` (universal; slice
      Required Behavior §C).
    - `INSUFFICIENT_DATA` — otherwise: no confirmed match exists, and either
      some listed configuration is UNKNOWN or the configuration space is not
      known to be complete. `reason` is `CONFIGURATION_AMBIGUOUS` exactly
      when the incompleteness of the configuration space itself is what
      prevents a confirmed non-match (`configuration_space_complete` is
      `False`); it is `None` when every listed configuration's own
      per-criterion reason codes already explain the UNKNOWN.
    """
    ordered = tuple(sorted(config_set.configurations, key=lambda c: c.identity.configuration_id))
    configuration_evaluations = tuple(evaluate_configuration(query, c) for c in ordered)

    matching_ids = tuple(
        ce.configuration_id for ce in configuration_evaluations if ce.truth is TruthState.TRUE
    )
    if matching_ids:
        return DesignQueryEvaluation(
            design_id=config_set.design_id,
            result_class=ResultClass.CONFIRMED_MATCH,
            matching_configuration_ids=matching_ids,
            configuration_evaluations=configuration_evaluations,
            reason=None,
        )

    all_false = all(ce.truth is TruthState.FALSE for ce in configuration_evaluations)
    if all_false and config_set.configuration_space_complete:
        return DesignQueryEvaluation(
            design_id=config_set.design_id,
            result_class=ResultClass.CONFIRMED_NON_MATCH,
            matching_configuration_ids=(),
            configuration_evaluations=configuration_evaluations,
            reason=None,
        )

    reason = None if config_set.configuration_space_complete else ReasonCode.CONFIGURATION_AMBIGUOUS
    return DesignQueryEvaluation(
        design_id=config_set.design_id,
        result_class=ResultClass.INSUFFICIENT_DATA,
        matching_configuration_ids=(),
        configuration_evaluations=configuration_evaluations,
        reason=reason,
    )


@dataclass(frozen=True, slots=True)
class ConfigurationSearchOutcome:
    """Separated result surfaces for one configuration-aware query run — mirrors
    `hullq.search.engine.SearchOutcome`'s primary-result boundary (slice
    Required Behavior §C): `confirmed_matches` is the only primary result
    set/count.
    """

    confirmed_matches: tuple[DesignQueryEvaluation, ...]
    confirmed_non_matches: tuple[DesignQueryEvaluation, ...]
    insufficient_data: tuple[DesignQueryEvaluation, ...]

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)

    @property
    def confirmed_non_match_count(self) -> int:
        return len(self.confirmed_non_matches)

    @property
    def insufficient_data_count(self) -> int:
        return len(self.insufficient_data)


def run_configuration_query(
    query: MixedAndQuery, design_configuration_sets: Iterable[DesignConfigurationSet]
) -> ConfigurationSearchOutcome:
    """Evaluate *query* against every design's configuration set; classify into three surfaces.

    Ordered by `design_id` before evaluation — the same deterministic
    stable-identity ordering as `hullq.search.engine.run_and_query`.
    """
    ordered = sorted(design_configuration_sets, key=lambda s: s.design_id)
    evaluations = tuple(evaluate_design_configuration_set(query, s) for s in ordered)
    matches = tuple(e for e in evaluations if e.result_class is ResultClass.CONFIRMED_MATCH)
    non_matches = tuple(e for e in evaluations if e.result_class is ResultClass.CONFIRMED_NON_MATCH)
    insufficient = tuple(e for e in evaluations if e.result_class is ResultClass.INSUFFICIENT_DATA)
    return ConfigurationSearchOutcome(
        confirmed_matches=matches,
        confirmed_non_matches=non_matches,
        insufficient_data=insufficient,
    )
