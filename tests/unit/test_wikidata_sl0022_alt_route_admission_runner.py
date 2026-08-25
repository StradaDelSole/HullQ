"""End-to-end runner-level tests for
scripts/bootstrap/wikidata_sl0022_alt_route_admission_runner.py.

All tests are offline and deterministic by construction: SLICE-0022 performs
zero network access in any mode. ``run_classify``/``run_verify`` are
exercised against the real committed immutable retained inputs (SLICE-0017/
0018/0021), writing their own manifest/report/artifact-digests output to
``tmp_path`` so the real committed
``research/bootstrap/wikidata/sl0022-alt-route-admission/`` package is never
touched by tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from bootstrap.wikidata_sl0022_alt_route_admission_runner import (  # noqa: E402
    run_classify,
    run_verify,
)

from hullq.bootstrap.wikidata_sl0022_alt_route_admission import (  # noqa: E402
    EXPECTED_R1_COUNT,
    EXPECTED_R3_COUNT,
    EXPECTED_TOTAL_CANDIDATES,
    load_and_fingerprint_immutable_inputs,
)

# The accepted retained SLICE-0021 source-fact acquisition timestamp
# (sampled_candidates.json's own top-level generated_at) — SLICE-0022 must
# use this verbatim as every candidate's retrieved_at / manifest acquired_at.
_RETAINED_SOURCE_FACT_TIMESTAMP = load_and_fingerprint_immutable_inputs().sl0021_generated_at


def _run_classify(tmp_path: Path) -> tuple[dict, Path, Path, Path]:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "REPORT.md"
    artifact_digests_path = tmp_path / "ARTIFACT-DIGESTS.json"
    manifest = run_classify(
        manifest_path=manifest_path,
        report_path=report_path,
        artifact_digests_path=artifact_digests_path,
    )
    return manifest, manifest_path, report_path, artifact_digests_path


def test_run_classify_writes_valid_manifest_report_and_artifact_digests(tmp_path: Path) -> None:
    manifest, manifest_path, report_path, artifact_digests_path = _run_classify(tmp_path)

    assert manifest_path.exists()
    assert report_path.exists()
    assert artifact_digests_path.exists()
    assert manifest["candidate_universe"] == {
        "total": EXPECTED_TOTAL_CANDIDATES,
        "r1_count": EXPECTED_R1_COUNT,
        "r2_count": 0,
        "r3_count": EXPECTED_R3_COUNT,
    }
    # R1 admission governance amendment: measured result under the accepted
    # retained SLICE-0021 facts is 0 AUTO_ADMIT / 31 REVIEW_REQUIRED (27 R1 +
    # 4 R3) / 26 NOT_ADMITTED (missing label).
    assert manifest["counts"]["auto_admit"] == 0
    assert manifest["counts"]["auto_admit_r1"] == 0
    assert manifest["counts"]["auto_admit_r3"] == 0
    assert manifest["counts"]["review_required"] == 31
    assert manifest["counts"]["not_admitted"] == 26
    assert manifest["counts"]["candidates_processed"] == EXPECTED_TOTAL_CANDIDATES
    assert manifest["counts"]["combined_canonical_boat_model_count_expected"] == 1770
    assert manifest["counts"]["retained_crosswalk_count"] == 1772

    # acquired_at is the retained SLICE-0021 source-fact timestamp, NOT this
    # run's own wall-clock computation time (generated_at).
    assert manifest["acquired_at"] == _RETAINED_SOURCE_FACT_TIMESTAMP
    assert manifest["acquired_at"] != manifest["generated_at"]
    assert manifest["classification_recomputed_at"] is None

    for row in manifest["candidates"]:
        assert row["retrieved_at"] == _RETAINED_SOURCE_FACT_TIMESTAMP
        assert row["hullq_id"] is None
        assert row["decision"] != "auto_admit"

    q232393 = next(row for row in manifest["candidates"] if row["qid"] == "Q232393")
    assert q232393["decision"] == "review_required"
    assert q232393["reason_codes"] == ["r1_alternative_route_requires_review"]

    report_text = report_path.read_text(encoding="utf-8")
    assert "SLICE-0022" in report_text
    assert "ZERO LIVE NETWORK ACQUISITION" in report_text

    digests_doc = json.loads(artifact_digests_path.read_text(encoding="utf-8"))
    assert digests_doc["excludes_self"] == "ARTIFACT-DIGESTS.json"
    assert set(digests_doc["digests"]) == {"manifest.json", "manifest_schema.json", "REPORT.md"}


def test_run_classify_is_idempotent_across_reruns(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "REPORT.md"
    artifact_digests_path = tmp_path / "ARTIFACT-DIGESTS.json"

    first = run_classify(
        manifest_path=manifest_path,
        report_path=report_path,
        artifact_digests_path=artifact_digests_path,
    )
    second = run_classify(
        manifest_path=manifest_path,
        report_path=report_path,
        artifact_digests_path=artifact_digests_path,
    )

    first_by_qid = {row["qid"]: row for row in first["candidates"]}
    second_by_qid = {row["qid"]: row for row in second["candidates"]}
    assert set(first_by_qid) == set(second_by_qid)
    for qid, first_row in first_by_qid.items():
        second_row = second_by_qid[qid]
        # A rerun must never mint a new mapping, and must never mutate the
        # retained source-fact timestamp.
        assert second_row["hullq_id"] == first_row["hullq_id"]
        assert (
            second_row["retrieved_at"]
            == first_row["retrieved_at"]
            == _RETAINED_SOURCE_FACT_TIMESTAMP
        )

    assert second["acquired_at"] == first["acquired_at"] == _RETAINED_SOURCE_FACT_TIMESTAMP
    assert second["classification_recomputed_at"] is not None
    assert first["classification_recomputed_at"] is None


def test_run_verify_passes_on_freshly_classified_manifest(tmp_path: Path) -> None:
    _, manifest_path, report_path, artifact_digests_path = _run_classify(tmp_path)

    run_verify(
        manifest_path=manifest_path,
        report_path=report_path,
        artifact_digests_path=artifact_digests_path,
    )  # must not raise


def test_run_verify_fails_closed_on_tampered_decision(tmp_path: Path) -> None:
    _, manifest_path, report_path, artifact_digests_path = _run_classify(tmp_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = next(r for r in manifest["candidates"] if r["route_membership"] == ["R3"])
    row["decision"] = "auto_admit"
    row["reason_codes"] = ["ok"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SystemExit):
        run_verify(
            manifest_path=manifest_path,
            report_path=report_path,
            artifact_digests_path=artifact_digests_path,
        )


def test_run_verify_fails_closed_on_tampered_retained_report(tmp_path: Path) -> None:
    """A REPORT.md edited after --classify no longer matches its own
    retained ARTIFACT-DIGESTS.json digest."""
    _, manifest_path, report_path, artifact_digests_path = _run_classify(tmp_path)

    report_path.write_text("tampered", encoding="utf-8")

    with pytest.raises(SystemExit):
        run_verify(
            manifest_path=manifest_path,
            report_path=report_path,
            artifact_digests_path=artifact_digests_path,
        )


def test_run_verify_fails_closed_when_artifact_digests_missing(tmp_path: Path) -> None:
    _, manifest_path, report_path, artifact_digests_path = _run_classify(tmp_path)
    artifact_digests_path.unlink()

    with pytest.raises(SystemExit):
        run_verify(
            manifest_path=manifest_path,
            report_path=report_path,
            artifact_digests_path=artifact_digests_path,
        )


def test_run_verify_passes_against_real_committed_manifest() -> None:
    """The actual retained SLICE-0022 manifest/report/artifact-digests/
    replay-evidence committed to the repository must themselves pass offline
    verification — the same check normal CI runs. ``replay_result_path``/
    ``replay_report_path`` default to the real committed
    REPLAY-RESULT.json/REPLAY-REPORT.md, so this also exercises the checked-in
    replay-evidence verification path end to end.
    """
    from bootstrap.wikidata_sl0022_alt_route_admission_runner import (
        ARTIFACT_DIGESTS_PATH,
        MANIFEST_PATH,
        REPORT_PATH,
    )

    run_verify(
        manifest_path=MANIFEST_PATH,
        report_path=REPORT_PATH,
        artifact_digests_path=ARTIFACT_DIGESTS_PATH,
    )  # must not raise


# ---------------------------------------------------------------------------
# Checked-in PostgreSQL replay-evidence verification (--verify and the
# --replay pre-mutation gate)
# ---------------------------------------------------------------------------


def _run_classify_with_real_replay_evidence(
    tmp_path: Path,
) -> tuple[dict, Path, Path, Path, Path, Path]:
    """Freshly --classify into *tmp_path*, then copy the real checked-in
    REPLAY-RESULT.json/REPLAY-REPORT.md alongside it.

    Safe because classification is fully deterministic from the immutable
    retained inputs (no IDs are ever minted under the R1 governance
    amendment), so a fresh manifest in *tmp_path* has byte-identical
    candidate/decision/count content to the real committed manifest.json —
    only ``generated_at`` differs (wall-clock write time), which the replay
    verifier never inspects. The real replay evidence is therefore valid
    against this fresh manifest too.
    """
    from bootstrap.wikidata_sl0022_alt_route_admission_runner import (
        REPLAY_REPORT_PATH,
        REPLAY_RESULT_PATH,
    )

    manifest, manifest_path, report_path, artifact_digests_path = _run_classify(tmp_path)
    replay_result_path = tmp_path / "REPLAY-RESULT.json"
    replay_report_path = tmp_path / "REPLAY-REPORT.md"
    replay_result_path.write_bytes(REPLAY_RESULT_PATH.read_bytes())
    replay_report_path.write_bytes(REPLAY_REPORT_PATH.read_bytes())
    return (
        manifest,
        manifest_path,
        report_path,
        artifact_digests_path,
        replay_result_path,
        replay_report_path,
    )


def test_run_verify_passes_with_copied_real_replay_evidence(tmp_path: Path) -> None:
    (
        _,
        manifest_path,
        report_path,
        artifact_digests_path,
        replay_result_path,
        replay_report_path,
    ) = _run_classify_with_real_replay_evidence(tmp_path)

    run_verify(
        manifest_path=manifest_path,
        report_path=report_path,
        artifact_digests_path=artifact_digests_path,
        replay_result_path=replay_result_path,
        replay_report_path=replay_report_path,
    )  # must not raise


def test_run_verify_fails_closed_on_tampered_replay_result_auto_admit(tmp_path: Path) -> None:
    (
        _,
        manifest_path,
        report_path,
        artifact_digests_path,
        replay_result_path,
        replay_report_path,
    ) = _run_classify_with_real_replay_evidence(tmp_path)

    replay_result = json.loads(replay_result_path.read_text(encoding="utf-8"))
    replay_result["sl0022_auto_admit"] = 1
    replay_result_path.write_text(json.dumps(replay_result), encoding="utf-8")

    with pytest.raises(SystemExit):
        run_verify(
            manifest_path=manifest_path,
            report_path=report_path,
            artifact_digests_path=artifact_digests_path,
            replay_result_path=replay_result_path,
            replay_report_path=replay_report_path,
        )


def test_run_verify_fails_closed_when_replay_report_changed_independently_of_result(
    tmp_path: Path,
) -> None:
    (
        _,
        manifest_path,
        report_path,
        artifact_digests_path,
        replay_result_path,
        replay_report_path,
    ) = _run_classify_with_real_replay_evidence(tmp_path)

    replay_report_path.write_text("this report text was hand-edited", encoding="utf-8")

    with pytest.raises(SystemExit):
        run_verify(
            manifest_path=manifest_path,
            report_path=report_path,
            artifact_digests_path=artifact_digests_path,
            replay_result_path=replay_result_path,
            replay_report_path=replay_report_path,
        )


def test_run_verify_fails_closed_when_replay_result_changed_while_report_stale(
    tmp_path: Path,
) -> None:
    (
        _,
        manifest_path,
        report_path,
        artifact_digests_path,
        replay_result_path,
        replay_report_path,
    ) = _run_classify_with_real_replay_evidence(tmp_path)

    replay_result = json.loads(replay_result_path.read_text(encoding="utf-8"))
    replay_result["first_pass"]["readback"]["stray_row_counts"]["canonical_brands"] = 1
    replay_result_path.write_text(json.dumps(replay_result), encoding="utf-8")
    # replay_report_path is intentionally left untouched (now stale relative
    # to the just-tampered REPLAY-RESULT.json).

    with pytest.raises(SystemExit):
        run_verify(
            manifest_path=manifest_path,
            report_path=report_path,
            artifact_digests_path=artifact_digests_path,
            replay_result_path=replay_result_path,
            replay_report_path=replay_report_path,
        )


def test_run_verify_passes_when_no_replay_evidence_has_ever_been_produced(tmp_path: Path) -> None:
    """A freshly-classified manifest with no REPLAY-RESULT.json yet (no
    --replay has ever run) is NOT itself a --verify failure — replay evidence
    is validated only if present."""
    _, manifest_path, report_path, artifact_digests_path = _run_classify(tmp_path)

    run_verify(
        manifest_path=manifest_path,
        report_path=report_path,
        artifact_digests_path=artifact_digests_path,
        replay_result_path=tmp_path / "REPLAY-RESULT.json",
        replay_report_path=tmp_path / "REPLAY-REPORT.md",
    )  # must not raise


def test_replay_gate_aborts_before_db_mutation_for_tampered_checked_in_replay_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The --replay pre-mutation safety gate must reject tampered checked-in
    replay evidence and abort BEFORE any PostgreSQL connection is attempted —
    proven here by making a connection attempt itself fail the test."""
    import psycopg
    from bootstrap.wikidata_sl0022_alt_route_admission_runner import (
        ARTIFACT_DIGESTS_PATH,
        MANIFEST_PATH,
        REPLAY_REPORT_PATH,
        REPLAY_RESULT_PATH,
        REPORT_PATH,
        replay_manifest,
    )

    def _must_not_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "psycopg.connect must not be called when the pre-mutation replay-safety gate "
            "rejects tampered checked-in replay evidence"
        )

    monkeypatch.setattr(psycopg, "connect", _must_not_connect)

    tampered_result = json.loads(REPLAY_RESULT_PATH.read_text(encoding="utf-8"))
    tampered_result["all_zero_tolerance_conditions_clear"] = False
    tampered_result_path = tmp_path / "REPLAY-RESULT.json"
    tampered_result_path.write_text(json.dumps(tampered_result), encoding="utf-8")
    copied_report_path = tmp_path / "REPLAY-REPORT.md"
    copied_report_path.write_bytes(REPLAY_REPORT_PATH.read_bytes())

    with pytest.raises(SystemExit):
        replay_manifest(
            "postgresql://this-host-must-never-be-contacted.invalid/db",
            manifest_path=MANIFEST_PATH,
            retained_report_path=REPORT_PATH,
            artifact_digests_path=ARTIFACT_DIGESTS_PATH,
            result_path=tampered_result_path,
            report_path=copied_report_path,
        )
