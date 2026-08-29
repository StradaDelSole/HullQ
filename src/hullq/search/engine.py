"""Search execution over multiple projections — SLICE-0033.

Implements the slice's Required Behavior §C (primary result boundary) and
§D (determinism / stable ordering). Confirmed non-matches are retained for
explainability/debugging but never appear in the primary match count/list.

Does not implement: ranking by preference/quality/popularity/completeness —
SEARCH_QUERY_SEMANTICS.v0.1.md §9 forbids inventing an opaque score, and this
slice deliberately uses stable design-identity ordering only.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from hullq.search.projection import SearchableDesignProjection
from hullq.search.query import AndQuery, QueryEvaluation, evaluate_and_query
from hullq.search.types import ResultClass

__all__ = ["SearchOutcome", "run_and_query"]


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    """Separated result surfaces for one query run — slice Required Behavior §C.

    `confirmed_matches` is the only primary result set/count.
    `confirmed_non_matches` and `insufficient_data` are separate discovery
    surfaces retained for explainability and MUST NOT be presented as matches.
    """

    confirmed_matches: tuple[QueryEvaluation, ...]
    confirmed_non_matches: tuple[QueryEvaluation, ...]
    insufficient_data: tuple[QueryEvaluation, ...]

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)

    @property
    def confirmed_non_match_count(self) -> int:
        return len(self.confirmed_non_matches)

    @property
    def insufficient_data_count(self) -> int:
        return len(self.insufficient_data)


def run_and_query(
    query: AndQuery, projections: Iterable[SearchableDesignProjection]
) -> SearchOutcome:
    """Evaluate *query* against every projection and classify into three surfaces.

    Projections are ordered by `design_id` before evaluation — a simple
    stable identity order, per slice Required Behavior §D, so identical
    serialized query input and identical projection data always produce the
    same ordered output regardless of the caller's iteration order.
    """
    ordered = sorted(projections, key=lambda p: p.design_id)
    evaluations = tuple(evaluate_and_query(query, projection) for projection in ordered)
    matches = tuple(e for e in evaluations if e.result_class is ResultClass.CONFIRMED_MATCH)
    non_matches = tuple(e for e in evaluations if e.result_class is ResultClass.CONFIRMED_NON_MATCH)
    insufficient = tuple(e for e in evaluations if e.result_class is ResultClass.INSUFFICIENT_DATA)
    return SearchOutcome(
        confirmed_matches=matches,
        confirmed_non_matches=non_matches,
        insufficient_data=insufficient,
    )
