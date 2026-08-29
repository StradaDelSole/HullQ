"""SLICE-0033 local search-kernel demonstration.

Loads the explicit fixture query and fixture BoatDesign-style projections
under `fixtures/search/`, runs the query through the `hullq.search` kernel,
and prints the three separated outcome classes with criterion-level
explanations.

FIXTURE DATA ONLY: every design below is explicit test/fixture data. This
script does not read, promote or otherwise represent the 1,770-record
normalized research-evidence corpus as canonical searchable BoatDesigns
(slice Required Behavior §E).

Run: uv run python scripts/search_demo.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hullq.domain.derived_metrics import MetricStatus
from hullq.domain.provenance import ResolutionState
from hullq.search import (
    QualifiedNumericValue,
    QueryEvaluation,
    SearchableDesignProjection,
    SearchOutcome,
    from_derived_metric_status,
    from_resolution_state,
    query_from_json_dict,
    run_and_query,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "fixtures" / "search"
PROJECTIONS_FIXTURE = FIXTURES_DIR / "boatdesign_projections.fixture.v0.1.json"
QUERY_FIXTURE = FIXTURES_DIR / "query.loa_draft_beam.fixture.v0.1.json"


def _field_to_qualified_value(field_data: dict[str, Any]) -> QualifiedNumericValue:
    """Build a QualifiedNumericValue from one fixture field entry.

    Mirrors the boundary a future ingestion layer would cross: a raw
    FieldResolution.state or derived-metric MetricStatus, translated through
    the accepted `hullq.search.values` adapters — never a raw trusted number.
    """
    source = field_data["source"]
    value = field_data.get("value")
    if source == "field_resolution":
        state = ResolutionState(field_data["state"])
        return from_resolution_state(state, value)
    if source == "derived_metric":
        status = MetricStatus(field_data["status"])
        return from_derived_metric_status(status, value)
    raise ValueError(f"Unknown fixture field source: {source!r}")


def load_fixture_projections(path: Path = PROJECTIONS_FIXTURE) -> list[SearchableDesignProjection]:
    """Load fixture BoatDesign-style projections. Every result has is_fixture=True."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    projections = []
    for design in payload["designs"]:
        values = {
            field_name: _field_to_qualified_value(field_data)
            for field_name, field_data in design["fields"].items()
        }
        projections.append(
            SearchableDesignProjection(
                design_id=design["design_id"],
                values=values,
                is_fixture=True,
            )
        )
    return projections


def _print_evaluation(evaluation: QueryEvaluation) -> None:
    print(f"  - {evaluation.design_id} [{evaluation.result_class.value}]")
    for criterion_eval in evaluation.criterion_evaluations:
        print(f"      {criterion_eval.explanation}")


def print_outcome(outcome: SearchOutcome) -> None:
    print(f"CONFIRMED_MATCH ({outcome.confirmed_match_count}):")
    for evaluation in outcome.confirmed_matches:
        _print_evaluation(evaluation)

    print(f"\nCONFIRMED_NON_MATCH ({outcome.confirmed_non_match_count}):")
    for evaluation in outcome.confirmed_non_matches:
        _print_evaluation(evaluation)

    print(f"\nINSUFFICIENT_DATA ({outcome.insufficient_data_count}):")
    for evaluation in outcome.insufficient_data:
        _print_evaluation(evaluation)


def main() -> SearchOutcome:
    print("SLICE-0033 search kernel demo — FIXTURE DATA ONLY, not canonical BoatDesigns.\n")
    query = query_from_json_dict(json.loads(QUERY_FIXTURE.read_text(encoding="utf-8")))
    projections = load_fixture_projections()
    outcome = run_and_query(query, projections)
    print_outcome(outcome)
    return outcome


if __name__ == "__main__":
    main()
