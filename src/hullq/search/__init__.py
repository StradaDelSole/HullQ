"""HullQ search kernel — first product vertical (SLICE-0033).

Implements the smallest trustworthy query engine that can evaluate
serializable numeric MUST criteria over canonical BoatDesign-style data and
return separately classified confirmed matches, confirmed non-matches and
insufficient-data records with criterion-level explanations, per the
accepted `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` (OQ-009 D1-D10).

Public surface:

- `hullq.search.types` — truth/result/reason/qualification vocabulary
- `hullq.search.values` — fail-closed `QualifiedNumericValue` + FieldResolution/
  MetricStatus adapters
- `hullq.search.criteria` — `NumericLeafCriterion` + leaf evaluation
- `hullq.search.projection` — persistence-neutral `SearchableDesignProjection`
- `hullq.search.query` — `AndQuery`, evaluation, JSON serialization
- `hullq.search.engine` — multi-projection execution and result classification

Does not implement: FastAPI/HTTP, Astro/frontend, public SEO/routing,
PostgreSQL persistence, PREFER ranking, OR/NOT, full ResolvedConfiguration
option search, market listings, alerts, or auth. Does not promote the
1,770-record normalized research-evidence corpus to canonical searchable
BoatDesigns.
"""

from __future__ import annotations

from hullq.search.criteria import CriterionEvaluation, NumericLeafCriterion, evaluate_numeric_leaf
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
from hullq.search.types import (
    NumericComparisonKind,
    ReasonCode,
    RequirementStrength,
    ResultClass,
    TruthState,
    ValueQualification,
)
from hullq.search.values import (
    QualifiedNumericValue,
    from_derived_metric_status,
    from_resolution_state,
)

__all__ = [
    "AndQuery",
    "CriterionEvaluation",
    "NumericComparisonKind",
    "NumericLeafCriterion",
    "QualifiedNumericValue",
    "QueryEvaluation",
    "ReasonCode",
    "RequirementStrength",
    "ResultClass",
    "SearchOutcome",
    "SearchableDesignProjection",
    "TruthState",
    "ValueQualification",
    "and_reduce",
    "evaluate_and_query",
    "evaluate_numeric_leaf",
    "from_derived_metric_status",
    "from_resolution_state",
    "query_from_json_dict",
    "query_to_json_dict",
    "result_class_for",
    "run_and_query",
]
