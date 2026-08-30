"""SLICE-0035 local categorical + configuration-aware search demonstration.

Loads the explicit fixture design-configuration corpus under
`fixtures/search/design_configuration_sets.fixture.v0.1.json` and the ten
query-shape fixtures mirroring `specs/SEARCH_BENCHMARK.v0.1.md` Q1-Q10 under
`fixtures/search/query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json`, runs
every query through the `hullq.search.configuration_engine` kernel, and
prints the three separated outcome classes with per-configuration truth and
matching-configuration identity.

FIXTURE DATA ONLY: every design below is explicit synthetic test/fixture
data. This script does not read, promote or otherwise represent the
1,770-record normalized research-evidence corpus, nor the locked
SEARCH_BENCHMARK.v0.1.md 12-BoatDesign corpus, as canonical searchable
BoatDesigns (slice Required Behavior §E; slice stop condition on real
benchmark data admission).

Run: uv run python scripts/search_demo_configuration_aware.py
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
FIXTURES_DIR = ROOT / "fixtures" / "search"
DESIGNS_FIXTURE = FIXTURES_DIR / "design_configuration_sets.fixture.v0.1.json"
QUERIES_FIXTURE = FIXTURES_DIR / "query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json"


def _numeric_field(field_data: dict[str, Any]) -> QualifiedNumericValue:
    state = ResolutionState(field_data["state"])
    return from_resolution_state(state, field_data.get("value"))


def _categorical_field(field_data: dict[str, Any]) -> QualifiedCategoricalValue:
    state = ResolutionState(field_data["state"])
    return from_resolution_state_categorical(state, field_data.get("value"))


def load_fixture_design_configuration_sets(
    path: Path = DESIGNS_FIXTURE,
) -> list[DesignConfigurationSet]:
    """Load fixture DesignConfigurationSets. Every result has is_fixture=True."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    design_sets = []
    for design in payload["designs"]:
        configurations = []
        for config_data in design["configurations"]:
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
                        boat_design_id=design["design_id"],
                        named_variant_id=config_data.get("named_variant_id"),
                        applied_option_ids=tuple(config_data.get("applied_option_ids", ())),
                    ),
                    projection=ConfigurationProjection(
                        numeric_values=numeric_values, categorical_values=categorical_values
                    ),
                )
            )
        design_sets.append(
            DesignConfigurationSet(
                design_id=design["design_id"],
                configurations=tuple(configurations),
                configuration_space_complete=design["configuration_space_complete"],
                is_fixture=True,
            )
        )
    return design_sets


def load_fixture_queries(path: Path = QUERIES_FIXTURE) -> list[tuple[str, str, str, MixedAndQuery]]:
    """Load (query_id, role, description, MixedAndQuery) tuples in fixture order."""
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


def _print_evaluation(evaluation: DesignQueryEvaluation) -> None:
    reason = f" reason={evaluation.reason.value}" if evaluation.reason is not None else ""
    print(f"  - {evaluation.design_id} [{evaluation.result_class.value}]{reason}")
    for config_eval in evaluation.configuration_evaluations:
        print(f"      configuration={config_eval.configuration_id} truth={config_eval.truth.value}")
    if evaluation.matching_configuration_ids:
        print(f"      matching_configuration_ids={list(evaluation.matching_configuration_ids)}")


def print_outcome(
    query_id: str, role: str, description: str, outcome: ConfigurationSearchOutcome
) -> None:
    print(f"\n{query_id} [{role}] — {description}")
    print(
        f"  distribution: CONFIRMED_MATCH={outcome.confirmed_match_count} "
        f"CONFIRMED_NON_MATCH={outcome.confirmed_non_match_count} "
        f"INSUFFICIENT_DATA={outcome.insufficient_data_count}"
    )
    print(f"  CONFIRMED_MATCH ({outcome.confirmed_match_count}):")
    for evaluation in outcome.confirmed_matches:
        _print_evaluation(evaluation)
    print(f"  CONFIRMED_NON_MATCH ({outcome.confirmed_non_match_count}):")
    for evaluation in outcome.confirmed_non_matches:
        _print_evaluation(evaluation)
    print(f"  INSUFFICIENT_DATA ({outcome.insufficient_data_count}):")
    for evaluation in outcome.insufficient_data:
        _print_evaluation(evaluation)


def main() -> dict[str, ConfigurationSearchOutcome]:
    print(
        "SLICE-0035 categorical + configuration-aware search demo — FIXTURE DATA ONLY, "
        "not canonical BoatDesigns, not the real SEARCH_BENCHMARK.v0.1.md corpus.\n"
    )
    design_sets = load_fixture_design_configuration_sets()
    queries = load_fixture_queries()
    outcomes: dict[str, ConfigurationSearchOutcome] = {}
    for query_id, role, description, query in queries:
        outcome = run_configuration_query(query, design_sets)
        outcomes[query_id] = outcome
        print_outcome(query_id, role, description, outcome)
    return outcomes


if __name__ == "__main__":
    main()
