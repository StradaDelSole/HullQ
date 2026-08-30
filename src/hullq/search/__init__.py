"""HullQ search kernel — first product vertical (SLICE-0033) + categorical/
configuration-aware extension (SLICE-0035).

SLICE-0033 implemented the smallest trustworthy query engine that can
evaluate serializable numeric MUST criteria over canonical BoatDesign-style
data and return separately classified confirmed matches, confirmed
non-matches and insufficient-data records with criterion-level explanations,
per the accepted `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` (OQ-009 D1-D10).
SLICE-0035 adds categorical MUST leaves, a versioned mixed numeric/categorical
query contract (v0.2, reading v0.1 unchanged) and configuration-aware
BoatDesign evaluation per `specs/SEARCH_BENCHMARK.v0.1.md`.

Public surface:

- `hullq.search.types` — truth/result/reason/qualification vocabulary
- `hullq.search.values` — fail-closed `QualifiedNumericValue`/
  `QualifiedCategoricalValue` + FieldResolution/MetricStatus adapters
- `hullq.search.criteria` — `NumericLeafCriterion`/`CategoricalLeafCriterion`
  + leaf evaluation
- `hullq.search.projection` — persistence-neutral `SearchableDesignProjection`
  (numeric-only, SLICE-0033)
- `hullq.search.query` — `AndQuery`, evaluation, v0.1 JSON serialization
- `hullq.search.query_mixed` — `MixedAndQuery`, v0.1/v0.2 JSON serialization
- `hullq.search.engine` — multi-projection execution and result classification
  (numeric-only, SLICE-0033)
- `hullq.search.configuration` — persistence-neutral `DesignConfigurationSet`/
  `ResolvedConfiguration` resolved-configuration input contract
- `hullq.search.configuration_engine` — configuration-aware multi-design
  execution and result classification

Does not implement: FastAPI/HTTP, Astro/frontend, public SEO/routing,
PostgreSQL persistence, PREFER ranking, OR/NOT, automatic option-combination
expansion, market listings, alerts, or auth. Does not promote the
1,770-record normalized research-evidence corpus to canonical searchable
BoatDesigns.
"""

from __future__ import annotations

from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    NamedVariantConstraint,
    OptionConstraint,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import (
    ConfigurationEvaluation,
    ConfigurationSearchOutcome,
    DesignQueryEvaluation,
    evaluate_configuration,
    evaluate_design_configuration_set,
    run_configuration_query,
)
from hullq.search.criteria import (
    CategoricalLeafCriterion,
    CriterionEvaluation,
    NumericLeafCriterion,
    evaluate_categorical_leaf,
    evaluate_numeric_leaf,
)
from hullq.search.engine import SearchOutcome, run_and_query
from hullq.search.projection import SearchableDesignProjection
from hullq.search.query import (
    AndQuery,
    QueryEvaluation,
    and_reduce,
    evaluate_and_query,
    query_from_json_dict,
    query_to_json_dict,
    result_class_for,
)
from hullq.search.query_mixed import (
    MixedAndQuery,
    MixedLeafCriterion,
    mixed_query_from_json_dict,
    mixed_query_to_json_dict,
)
from hullq.search.types import (
    LeafCriterionKind,
    NumericComparisonKind,
    ReasonCode,
    RequirementStrength,
    ResultClass,
    TruthState,
    ValueQualification,
)
from hullq.search.values import (
    RESERVED_CATEGORICAL_SENTINELS,
    QualifiedCategoricalValue,
    QualifiedNumericValue,
    from_derived_metric_status,
    from_resolution_state,
    from_resolution_state_categorical,
)

__all__ = [
    "RESERVED_CATEGORICAL_SENTINELS",
    "AndQuery",
    "CategoricalLeafCriterion",
    "ConfigurationEvaluation",
    "ConfigurationIdentity",
    "ConfigurationProjection",
    "ConfigurationSearchOutcome",
    "CriterionEvaluation",
    "DesignConfigurationSet",
    "DesignQueryEvaluation",
    "LeafCriterionKind",
    "MixedAndQuery",
    "MixedLeafCriterion",
    "NamedVariantConstraint",
    "NumericComparisonKind",
    "NumericLeafCriterion",
    "OptionConstraint",
    "QualifiedCategoricalValue",
    "QualifiedNumericValue",
    "QueryEvaluation",
    "ReasonCode",
    "RequirementStrength",
    "ResolvedConfiguration",
    "ResultClass",
    "SearchOutcome",
    "SearchableDesignProjection",
    "TruthState",
    "ValueQualification",
    "and_reduce",
    "evaluate_and_query",
    "evaluate_categorical_leaf",
    "evaluate_configuration",
    "evaluate_design_configuration_set",
    "evaluate_numeric_leaf",
    "from_derived_metric_status",
    "from_resolution_state",
    "from_resolution_state_categorical",
    "mixed_query_from_json_dict",
    "mixed_query_to_json_dict",
    "query_from_json_dict",
    "query_to_json_dict",
    "result_class_for",
    "run_and_query",
    "run_configuration_query",
]
