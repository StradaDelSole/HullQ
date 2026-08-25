"""Runner-level tests for
scripts/bootstrap/wikimedia_sl0024_independent_verification_runner.py.

All tests are offline and deterministic: only ``--verify`` is exercised here
(``--assemble`` is exercised once as a regression check that it reproduces
the real committed retained package byte-for-byte). ``run_verify`` is
exercised first against the real committed retained SLICE-0024 package (a
regression check that the checked-in
``research/bootstrap/wikimedia/sl0024-independent-verification/`` documents
remain self-consistent), then against tampered copies (written to
``tmp_path``, via monkeypatched module path constants so the real committed
package is never touched by tests) to prove the offline verifier fails
closed.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts" / "bootstrap" / "wikimedia_sl0024_independent_verification_runner.py"


def _load_runner_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "hullq_sl0024_wikimedia_runner_test_import", RUNNER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runner() -> Any:
    return _load_runner_module()


def _copy_retained_package(runner: Any, tmp_path: Path) -> None:
    """Copy the real committed retained package into tmp_path and repoint the
    runner module's path constants there, so tamper tests never touch the
    real committed files.
    """
    for src in runner.SL0024_DIR.iterdir():
        if src.is_file():
            (tmp_path / src.name).write_bytes(src.read_bytes())

    runner.SL0024_DIR = tmp_path
    runner.VERIFICATION_SAMPLE_PATH = tmp_path / "verification_sample.json"
    runner.VERIFICATION_SAMPLE_SCHEMA_PATH = tmp_path / "verification_sample_schema.json"
    runner.VERIFICATION_RESULTS_PATH = tmp_path / "verification_results.json"
    runner.VERIFICATION_RESULTS_SCHEMA_PATH = tmp_path / "verification_results_schema.json"
    runner.REPORT_PATH = tmp_path / "REPORT.md"
    runner.ARTIFACT_DIGESTS_PATH = tmp_path / "ARTIFACT-DIGESTS.json"
    runner.ARTIFACT_DIGESTS_SCHEMA_PATH = tmp_path / "ARTIFACT-DIGESTS.schema.json"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _first_result(results_doc: dict[str, Any], qid: str) -> dict[str, Any]:
    return next(row for row in results_doc["results"] if row["qid"] == qid)


# ---------------------------------------------------------------------------
# Regression: the real committed retained package verifies clean
# ---------------------------------------------------------------------------


def test_run_verify_passes_against_real_committed_retained_package(runner: Any) -> None:
    runner.run_verify()  # must not raise


def test_run_assemble_reproduces_real_committed_retained_package(
    runner: Any, tmp_path: Path
) -> None:
    """--assemble is fully deterministic: re-running it must reproduce the
    exact bytes of every already-committed retained file."""
    real_dir = runner.SL0024_DIR
    originals = {p.name: p.read_bytes() for p in real_dir.iterdir() if p.is_file()}

    runner.run_assemble()

    for name, original_bytes in originals.items():
        regenerated = (real_dir / name).read_bytes()
        assert regenerated == original_bytes, f"{name} is not byte-stable across --assemble reruns"


# ---------------------------------------------------------------------------
# Tamper tests: --verify must fail closed on any manipulated retained field
# ---------------------------------------------------------------------------


def test_run_verify_fails_closed_on_tampered_pinned_boundary(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    sample_path = tmp_path / "verification_sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    sample["pinned_inputs"]["unique_incremental_qid_lead_count"] = 999
    _write_json(sample_path, sample)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_sample_selection(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    sample_path = tmp_path / "verification_sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    sample["selected_qids"][0] = "Q1"
    _write_json(sample_path, sample)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_prior_tag(runner: Any, tmp_path: Path) -> None:
    """Moving a candidate to a different prior-tag stratum must be caught,
    even though the QID set stays superficially unchanged."""
    _copy_retained_package(runner, tmp_path)
    sample_path = tmp_path / "verification_sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    plausible = sample["selected_by_stratum_sha256_order"]["plausible_model_or_class_lead"]
    ambiguous = sample["selected_by_stratum_sha256_order"]["ambiguous"]
    plausible[0], ambiguous[0] = ambiguous[0], plausible[0]
    _write_json(sample_path, sample)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_duplicated_qid(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    dup_row = copy.deepcopy(results_doc["results"][0])
    results_doc["results"][1] = dup_row
    _write_json(results_path, results_doc)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError, StopIteration)):
        runner.run_verify()


def test_run_verify_fails_closed_on_invalid_source_class(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    row = results_doc["results"][0]
    if row["evidence_citations"]:
        row["evidence_citations"][0]["source_class"] = "not_a_real_class"
    _write_json(results_path, results_doc)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_evidence_strength_outcome_mismatch(
    runner: Any, tmp_path: Path
) -> None:
    """An ``unresolved`` row retained with ``evidence_strength=strong_source``
    must be rejected (evidence_strength=insufficient is mandatory for
    unresolved/conflict)."""
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    row = next(r for r in results_doc["results"] if r["subject_outcome"] == "unresolved")
    row["evidence_strength"] = "strong_source"
    _write_json(results_path, results_doc)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_evidence_strength_drift_from_citations(
    runner: Any, tmp_path: Path
) -> None:
    """Retained ``evidence_strength`` must match what the retained
    ``evidence_citations`` actually support, not merely be self-consistent
    with ``subject_outcome``."""
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    row = next(r for r in results_doc["results"] if r["subject_outcome"] == "unresolved")
    row["evidence_strength"] = "two_independent_specialist_sources"
    _write_json(results_path, results_doc)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_fake_two_specialist_independence(
    runner: Any, tmp_path: Path
) -> None:
    """A candidate whose two specialist citations are NOT declared mutually
    independent must not be upgraded to ``two_independent_specialist_sources``
    by simply relabeling the outcome/evidence fields without real
    independence support."""
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    row = _first_result(results_doc, "Q113987990")  # Newport 28-2: unresolved/insufficient
    row["subject_outcome"] = "in_scope_identity"
    row["evidence_strength"] = "two_independent_specialist_sources"
    # Mark two non-independent specialist-class citations as "supporting"
    # without adding a genuine mutual independent_of relationship.
    for c in row["evidence_citations"]:
        c["accessible"] = True
        c["supports_identity"] = c["source_class"] == "high_quality_specialist_documentation"
    _write_json(results_path, results_doc)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_action_ceiling_manipulation(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    row = results_doc["results"][0]
    row["search_query_count"] = 5
    row["combined_action_count"] = row["combined_action_count"] + 3
    _write_json(results_path, results_doc)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_global_ceiling_manipulation(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    for row in results_doc["results"]:
        row["source_page_evaluation_count"] = 4
        row["combined_action_count"] = row["search_query_count"] + 4
        row["evidence_citations"] = row["evidence_citations"][:0]
    _write_json(results_path, results_doc)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_aggregate_metric_drift(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    results_doc["metrics"]["subject_outcome_counts"]["in_scope_identity"] += 1
    _write_json(results_path, results_doc)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_recommendation_drift(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    results_doc["recommendation"] = "LOW_INDEPENDENT_VERIFICATION_YIELD"
    _write_json(results_path, results_doc)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_artifact_digest_tamper(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    report_path = tmp_path / "REPORT.md"
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_missing_result_row(runner: Any, tmp_path: Path) -> None:
    """Removing one candidate's result row (so results no longer exactly
    cover the 30-QID sample) must be rejected."""
    _copy_retained_package(runner, tmp_path)
    results_path = tmp_path / "verification_results.json"
    results_doc = json.loads(results_path.read_text(encoding="utf-8"))
    results_doc["results"].pop()
    _write_json(results_path, results_doc)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()
