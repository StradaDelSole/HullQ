"""Unit tests for hullq.search.engine — SLICE-0033.

Covers:
- run_and_query separates all three result surfaces
- primary result set/count contains only CONFIRMED_MATCH (§C)
- confirmed non-matches are retained but never counted as matches
- stable identity (design_id) ordering regardless of input iteration order
"""

from __future__ import annotations

from hullq.search.criteria import NumericLeafCriterion
from hullq.search.engine import run_and_query
from hullq.search.projection import SearchableDesignProjection
from hullq.search.query import AndQuery
from hullq.search.types import NumericComparisonKind, ValueQualification
from hullq.search.values import QualifiedNumericValue


def _confirmed(value: float) -> QualifiedNumericValue:
    return QualifiedNumericValue(value=value, qualification=ValueQualification.CONFIRMED)


def _query() -> AndQuery:
    return AndQuery(
        criteria=(
            NumericLeafCriterion(
                field="loa_m", comparison=NumericComparisonKind.MINIMUM, threshold_min=10.0
            ),
        )
    )


def _projections() -> list[SearchableDesignProjection]:
    return [
        SearchableDesignProjection(design_id="z-match", values={"loa_m": _confirmed(11.0)}),
        SearchableDesignProjection(design_id="a-non-match", values={"loa_m": _confirmed(9.0)}),
        SearchableDesignProjection(design_id="m-insufficient", values={}),
    ]


def test_run_and_query_separates_three_surfaces() -> None:
    outcome = run_and_query(_query(), _projections())
    assert outcome.confirmed_match_count == 1
    assert outcome.confirmed_non_match_count == 1
    assert outcome.insufficient_data_count == 1
    assert outcome.confirmed_matches[0].design_id == "z-match"
    assert outcome.confirmed_non_matches[0].design_id == "a-non-match"
    assert outcome.insufficient_data[0].design_id == "m-insufficient"


def test_primary_result_excludes_non_matches_and_insufficient_data() -> None:
    outcome = run_and_query(_query(), _projections())
    match_ids = {e.design_id for e in outcome.confirmed_matches}
    assert match_ids == {"z-match"}


def test_ordering_is_stable_by_design_id_regardless_of_input_order() -> None:
    forward = run_and_query(_query(), _projections())
    reversed_input = run_and_query(_query(), list(reversed(_projections())))
    forward_ids = [
        e.design_id
        for e in (
            *forward.confirmed_matches,
            *forward.confirmed_non_matches,
            *forward.insufficient_data,
        )
    ]
    reversed_ids = [
        e.design_id
        for e in (
            *reversed_input.confirmed_matches,
            *reversed_input.confirmed_non_matches,
            *reversed_input.insufficient_data,
        )
    ]
    assert forward_ids == reversed_ids
    assert [e.design_id for e in forward.confirmed_matches] == sorted(
        e.design_id for e in forward.confirmed_matches
    )
