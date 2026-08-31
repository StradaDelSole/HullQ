"""SLICE-0037 Oceanis 30.1 real-search pilot — local owner-test command.

Loads the retained, provenance-backed, non-fixture BENETEAU Oceanis 30.1
projection from
`research/benchmark/waves/sl0037-oceanis-30-1/oceanis_30_1_projection.v1.json`
(see that directory's `source_retrieval_log.json` for the bounded authoritative
source basis and `REPORT.md` for the full research narrative), builds a real
`hullq.search.configuration.DesignConfigurationSet` with `is_fixture=False`,
and runs the unchanged locked Q1-Q10 query shapes from
`fixtures/search/query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json`
through the existing `hullq.search.configuration_engine` kernel.

This script does not duplicate the evaluator: all truth is computed by
`hullq.search.configuration_engine.run_configuration_query`. It only loads the
retained real projection and formats the kernel's own output.

Run: uv run python scripts/search_oceanis_30_1.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hullq.domain.provenance import ResolutionState
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import (
    ConfigurationSearchOutcome,
    DesignQueryEvaluation,
    run_configuration_query,
)
from hullq.search.query_mixed import MixedAndQuery, mixed_query_from_json_dict
from hullq.search.values import (
    QualifiedCategoricalValue,
    QualifiedNumericValue,
    from_resolution_state,
    from_resolution_state_categorical,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_PATH = (
    ROOT
    / "research"
    / "benchmark"
    / "waves"
    / "sl0037-oceanis-30-1"
    / "oceanis_30_1_projection.v1.json"
)
QUERIES_FIXTURE = (
    ROOT / "fixtures" / "search" / "query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json"
)


def _numeric_field(field_data: dict[str, Any]) -> QualifiedNumericValue:
    state = ResolutionState(field_data["state"])
    return from_resolution_state(state, field_data.get("value"))


def _categorical_field(field_data: dict[str, Any]) -> QualifiedCategoricalValue:
    state = ResolutionState(field_data["state"])
    return from_resolution_state_categorical(state, field_data.get("value"))


def load_oceanis_30_1_configuration_set(
    path: Path = PROJECTION_PATH,
) -> DesignConfigurationSet:
    """Load the retained real Oceanis 30.1 projection. `is_fixture=False`.

    Only `numeric_fields`/`categorical_fields` entries actually present in the
    retained package are projected; every field the research deliberately
    left unresolved (see the package's `fields_deliberately_left_unresolved_*`
    sections) is simply absent here, which `ConfigurationProjection.get_*`
    already treats as MISSING -- never as a confirmed value or a confirmed
    non-match.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    configurations = []
    for config_data in payload["configurations"]:
        numeric_values = {
            field_name: _numeric_field(field_data)
            for field_name, field_data in config_data.get("numeric_fields", {}).items()
        }
        categorical_values = {
            field_name: _categorical_field(field_data)
            for field_name, field_data in config_data.get("categorical_fields", {}).items()
        }
        configurations.append(
            ResolvedConfiguration(
                identity=ConfigurationIdentity(
                    configuration_id=config_data["configuration_id"],
                    boat_design_id=payload["design_id"],
                    named_variant_id=config_data.get("named_variant_id"),
                    applied_option_ids=tuple(config_data.get("applied_option_ids", ())),
                ),
                projection=ConfigurationProjection(
                    numeric_values=numeric_values, categorical_values=categorical_values
                ),
            )
        )
    return DesignConfigurationSet(
        design_id=payload["design_id"],
        configurations=tuple(configurations),
        configuration_space_complete=payload["configuration_space_complete"],
        is_fixture=False,
    )


def load_locked_queries(path: Path = QUERIES_FIXTURE) -> list[tuple[str, str, str, MixedAndQuery]]:
    """Load the exact locked Q1-Q10 (query_id, role, description, MixedAndQuery) shapes."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        (
            entry["query_id"],
            entry["role"],
            entry["description"],
            mixed_query_from_json_dict(entry["query"]),
        )
        for entry in payload["queries"]
    ]


def _single_evaluation(outcome: ConfigurationSearchOutcome) -> DesignQueryEvaluation:
    all_evaluations = (
        outcome.confirmed_matches + outcome.confirmed_non_matches + outcome.insufficient_data
    )
    assert len(all_evaluations) == 1, "exactly one design (Oceanis 30.1) was queried"
    return all_evaluations[0]


def _print_result(
    query_id: str, role: str, description: str, evaluation: DesignQueryEvaluation
) -> None:
    reason = f" reason={evaluation.reason.value}" if evaluation.reason is not None else ""
    print(f"\n{query_id} [{role}] — {description}")
    print(f"  result_class={evaluation.result_class.value}{reason}")
    for config_eval in evaluation.configuration_evaluations:
        print(f"    configuration={config_eval.configuration_id} truth={config_eval.truth.value}")
        for criterion_eval in config_eval.criterion_evaluations:
            criterion_reason = (
                f" reason={criterion_eval.reason.value}"
                if criterion_eval.reason is not None
                else ""
            )
            print(
                f"        {criterion_eval.field}: {criterion_eval.truth.value}{criterion_reason} "
                f"({criterion_eval.explanation})"
            )
    if evaluation.matching_configuration_ids:
        print(f"  matching_configuration_ids={list(evaluation.matching_configuration_ids)}")


def main() -> dict[str, DesignQueryEvaluation]:
    print(
        "SLICE-0037 Oceanis 30.1 real-search pilot — REAL, provenance-backed "
        "BENETEAU Oceanis 30.1 projection (is_fixture=False), NOT synthetic fixture data.\n"
        "See research/benchmark/waves/sl0037-oceanis-30-1/REPORT.md for the full "
        "bounded authoritative-source research basis.\n"
    )
    config_set = load_oceanis_30_1_configuration_set()
    queries = load_locked_queries()
    results: dict[str, DesignQueryEvaluation] = {}
    for query_id, role, description, query in queries:
        outcome = run_configuration_query(query, [config_set])
        evaluation = _single_evaluation(outcome)
        results[query_id] = evaluation
        _print_result(query_id, role, description, evaluation)

    match_ids = sorted(
        qid for qid, ev in results.items() if ev.result_class.value == "CONFIRMED_MATCH"
    )
    non_match_ids = sorted(
        qid for qid, ev in results.items() if ev.result_class.value == "CONFIRMED_NON_MATCH"
    )
    insufficient_ids = sorted(
        qid for qid, ev in results.items() if ev.result_class.value == "INSUFFICIENT_DATA"
    )
    print("\nSummary:")
    print(f"  CONFIRMED_MATCH: {match_ids}")
    print(f"  CONFIRMED_NON_MATCH: {non_match_ids}")
    print(f"  INSUFFICIENT_DATA: {insufficient_ids}")
    return results


if __name__ == "__main__":
    main()
