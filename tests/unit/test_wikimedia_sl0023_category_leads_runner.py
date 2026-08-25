"""Runner-level tests for
scripts/bootstrap/wikimedia_sl0023_category_leads_runner.py.

All tests are offline and deterministic: only ``--verify`` is exercised here
(``--live``/``--assemble`` require network access or a manually-authored
quality-tags file and are exercised by the one-shot retained live run, not by
normal CI). ``run_verify`` is exercised first against the real committed
retained SLICE-0023 package (a regression check that the checked-in
``research/bootstrap/wikimedia/sl0023-category-leads/`` documents remain
self-consistent), then against tampered copies (written to ``tmp_path``, via
monkeypatched module path constants so the real committed package is never
touched by tests) to prove the offline verifier fails closed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts" / "bootstrap" / "wikimedia_sl0023_category_leads_runner.py"


def _load_runner_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "hullq_sl0023_wikimedia_runner_test_import", RUNNER_PATH
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
    for src in runner.SL0023_DIR.iterdir():
        if src.is_file():
            (tmp_path / src.name).write_bytes(src.read_bytes())

    runner.SL0023_DIR = tmp_path
    runner.SOURCE_ASSESSMENT_PATH = tmp_path / "source_assessment.json"
    runner.SOURCE_ASSESSMENT_SCHEMA_PATH = tmp_path / "source_assessment_schema.json"
    runner.DISCOVERY_MANIFEST_PATH = tmp_path / "discovery_manifest.json"
    runner.DISCOVERY_MANIFEST_SCHEMA_PATH = tmp_path / "discovery_manifest_schema.json"
    runner.QUALITY_SAMPLE_PATH = tmp_path / "quality_sample.json"
    runner.QUALITY_SAMPLE_SCHEMA_PATH = tmp_path / "quality_sample_schema.json"
    runner.REPORT_PATH = tmp_path / "REPORT.md"
    runner.ARTIFACT_DIGESTS_PATH = tmp_path / "ARTIFACT-DIGESTS.json"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Regression: the real committed retained package verifies clean
# ---------------------------------------------------------------------------


def test_run_verify_passes_against_real_committed_retained_package(runner: Any) -> None:
    runner.run_verify()  # must not raise


# ---------------------------------------------------------------------------
# Tamper tests: --verify must fail closed on any manipulated retained field
# ---------------------------------------------------------------------------


def test_run_verify_fails_closed_on_tampered_overlap_count(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["overlap_sets"]["incremental_qid_lead"]["count"] = 999999
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_category_member_count(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["categories"]["Keelboats"]["member_count"] = 1
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_immutable_boundary(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["immutable_boundaries"]["retained_historical_crosswalk_count"] = 1
    _write_json(manifest_path, manifest)

    # The 1,772 accepted constant is also schema-enforced (const), so a
    # tampered value fails closed via schema rejection before reaching the
    # mismatch-collection logic.
    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_quality_recommendation(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    quality_path = tmp_path / "quality_sample.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["recommendation"] = "LOW_INCREMENTAL_YIELD"
    _write_json(quality_path, quality)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_quality_tag_counts(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    quality_path = tmp_path / "quality_sample.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["quality_tag_counts"]["plausible_model_or_class_lead"] += 1
    _write_json(quality_path, quality)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_sample_selection(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sample_selection"]["selected_qids"] = ["Q1"]
    manifest["sample_selection"]["selected_count"] = 1
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_unique_pages_title(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_pageid = next(iter(manifest["unique_pages"]))
    manifest["unique_pages"][first_pageid]["title"] = "Tampered Title Not In Category Members"
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_invalid_quality_tag(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    quality_path = tmp_path / "quality_sample.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["quality_review"][0]["quality_tag"] = "not_a_real_tag"
    _write_json(quality_path, quality)

    # The quality-tag vocabulary is also schema-enforced (enum), so an
    # invalid tag fails closed via schema rejection.
    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_artifact_digests_tamper(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    report_path = tmp_path / "REPORT.md"
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit):
        runner.run_verify()


# ---------------------------------------------------------------------------
# Independent-review amendment tamper tests (2026-08-25 AMEND round)
# ---------------------------------------------------------------------------


def test_run_verify_fails_closed_on_tampered_qid_mapping(runner: Any, tmp_path: Path) -> None:
    """A tampered page->QID mapping must be caught by overlap-set recompute,
    not merely by title/category consistency.
    """
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_pageid = next(
        pid for pid, info in manifest["unique_pages"].items() if info.get("qid") is not None
    )
    manifest["unique_pages"][first_pageid]["qid"] = "Q999999999999"
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_wikidata_context_missing_row(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    quality_path = tmp_path / "quality_sample.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["wikidata_context"].pop()
    _write_json(quality_path, quality)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_wikidata_context_duplicate_row(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    quality_path = tmp_path / "quality_sample.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["wikidata_context"].append(quality["wikidata_context"][0])
    _write_json(quality_path, quality)

    with pytest.raises((SystemExit, jsonschema.exceptions.ValidationError)):
        runner.run_verify()


def test_run_verify_fails_closed_on_request_breakdown_tamper(runner: Any, tmp_path: Path) -> None:
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["request_ceilings"]["wikipedia_request_count"] += 1
    manifest["request_ceilings"]["total_request_count"] += 1
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_pageprops_request_count_tamper(
    runner: Any, tmp_path: Path
) -> None:
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["request_breakdown"]["pageprops_request_count"] += 1
    manifest["request_breakdown"]["reconciled_wikipedia_request_count"] += 1
    manifest["request_ceilings"]["wikipedia_request_count"] += 1
    manifest["request_ceilings"]["total_request_count"] += 1
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_coherent_rights_access_and_recommendation_tamper(
    runner: Any, tmp_path: Path
) -> None:
    """A sophisticated tamper that edits ``rights_access_ok`` AND
    ``recommendation`` together (so they remain internally coherent with each
    other) AND regenerates ``ARTIFACT-DIGESTS.json`` to match must still fail,
    because rights-access truth is independently re-derived from the live
    reviewed Source records and the retained ``discovery_manifest.rights_gate``
    — never trusted from the document's own stored flag.
    """
    _copy_retained_package(runner, tmp_path)
    quality_path = tmp_path / "quality_sample.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["rights_access_ok"] = False
    quality["recommendation"] = "RIGHTS_OR_ACCESS_BLOCKED"
    _write_json(quality_path, quality)

    # Simulate an attacker who also correctly regenerates the digest file
    # after tampering — artifact-digest matching alone must not be sufficient.
    runner._write_artifact_digests(runner.ARTIFACT_DIGESTS_PATH)

    with pytest.raises(SystemExit):
        runner.run_verify()


def test_run_verify_fails_closed_on_tampered_rights_gate_disagreeing_with_sources(
    runner: Any, tmp_path: Path
) -> None:
    """A retained ``rights_gate`` that disagrees with the actual reviewed
    Source records must itself be treated as untrustworthy.
    """
    _copy_retained_package(runner, tmp_path)
    manifest_path = tmp_path / "discovery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["rights_gate"]["wikipedia_automated_ingestion_clearance"] = "prohibited"
    _write_json(manifest_path, manifest)

    with pytest.raises(SystemExit):
        runner.run_verify()
