"""End-to-end runner-level tests for scripts/bootstrap/wikidata_tier0_runner.py.

All tests are offline and deterministic: ``run_live_bootstrap`` is exercised
through a fake ``httpx.Client`` (no real network access); ``recompute_manifest_offline``
performs no network access at all by construction.

Covers the SLICE-0017 independent-review requirement that a live rerun must
never silently remint an already-retained QID -> HullQ-ID mapping, proven at
the runner level (not only via a pure ``classify_candidates`` unit test).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from bootstrap.wikidata_tier0_runner import (  # noqa: E402
    recompute_manifest_offline,
    run_live_bootstrap,
)

from hullq.bootstrap.wikidata_tier0 import BootstrapDecision, CrosswalkConflictError  # noqa: E402

_USER_AGENT = "HullQ/0.1 (test; https://github.com/StradaDelSole/HullQ)"


def _sparql_response(qids: list[str]) -> dict[str, Any]:
    return {
        "results": {
            "bindings": [
                {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"}}
                for q in qids
            ]
        }
    }


def _entities_response(entries: dict[str, str]) -> dict[str, Any]:
    return {
        "entities": {
            qid: {
                "type": "item",
                "id": qid,
                "labels": {"en": {"language": "en", "value": label}},
                "aliases": {},
                "claims": {},
            }
            for qid, label in entries.items()
        }
    }


class _FakeResponse:
    def __init__(self, json_body: dict[str, Any]) -> None:
        self._json_body = json_body
        self.status_code = 200
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._json_body


class _FakeHttpxClient:
    """Minimal offline stand-in for ``httpx.Client`` used as a context manager."""

    def __init__(self, discovery_qids: list[str], entities: dict[str, str]) -> None:
        self._discovery_qids = discovery_qids
        self._entities = entities

    def __enter__(self) -> _FakeHttpxClient:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get(
        self, url: str, params: Any = None, headers: Any = None, timeout: Any = None
    ) -> _FakeResponse:
        if "query.wikidata.org" in url:
            return _FakeResponse(_sparql_response(self._discovery_qids))
        return _FakeResponse(_entities_response(self._entities))


def _patch_httpx_client(
    monkeypatch: pytest.MonkeyPatch, discovery_qids: list[str], entities: dict[str, str]
) -> None:
    import httpx

    monkeypatch.setattr(httpx, "Client", lambda: _FakeHttpxClient(discovery_qids, entities))


def test_live_rerun_reuses_retained_id_for_already_mapped_qid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "REPORT.md"

    _patch_httpx_client(monkeypatch, ["Q1", "Q2"], {"Q1": "Alpha Yacht", "Q2": "Beta Yacht"})
    first = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    first_ids = {c["qid"]: c["hullq_id"] for c in first["candidates"]}
    assert first_ids["Q1"] is not None
    assert first_ids["Q2"] is not None

    # Second live run returns the exact same discovery/entity set (as if
    # rerunning against an unchanged Wikidata state). Q1/Q2 must reuse their
    # exact retained IDs, never mint new ones.
    _patch_httpx_client(monkeypatch, ["Q1", "Q2"], {"Q1": "Alpha Yacht", "Q2": "Beta Yacht"})
    second = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    second_ids = {c["qid"]: c["hullq_id"] for c in second["candidates"]}
    assert second_ids == first_ids


def test_live_rerun_mints_only_for_genuinely_new_qids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "REPORT.md"

    _patch_httpx_client(monkeypatch, ["Q1"], {"Q1": "Alpha Yacht"})
    first = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=1,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    q1_id = first["candidates"][0]["hullq_id"]

    _patch_httpx_client(monkeypatch, ["Q1", "Q2"], {"Q1": "Alpha Yacht", "Q2": "New Yacht"})
    second = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    by_qid = {c["qid"]: c["hullq_id"] for c in second["candidates"]}
    assert by_qid["Q1"] == q1_id  # unchanged, reused
    assert by_qid["Q2"] is not None
    assert by_qid["Q2"] != q1_id


def test_retained_qid_survives_a_discovery_window_that_omits_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Three-run regression: a retained QID must keep its byte-identical
    HullQ ID even after a later discovery window's first-N result happens
    not to include it, and must not be reminted when it reappears — while
    ``candidates`` always describes only the CURRENT discovery window and
    ``retained_crosswalk`` is the separate historical registry.

    Run 1: discovery returns Q1 -> mints an ID for Q1.
    Run 2: discovery returns only Q2 (Q1 absent from this window's first-N)
           -> candidates contains ONLY Q2; Q1's mapping survives in
           retained_crosswalk, not as a stale candidate decision.
    Run 3: discovery returns Q1 and Q2 again -> Q1 reappears in candidates
           and reuses its exact original ID from run 1, not a new one.

    Covers independent-review requirements (a) candidates-only-current-window,
    (b) reuse-on-reappearance, (c) candidates_processed excludes
    historical-only mappings, (e) no stale AUTO_ADMIT candidate decision for
    an absent QID.
    """
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "REPORT.md"

    _patch_httpx_client(monkeypatch, ["Q1"], {"Q1": "Alpha Yacht"})
    run1 = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=1,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    q1_original_id = next(c["hullq_id"] for c in run1["candidates"] if c["qid"] == "Q1")
    assert q1_original_id is not None
    assert [c["qid"] for c in run1["candidates"]] == ["Q1"]
    assert [row["qid"] for row in run1["retained_crosswalk"]] == ["Q1"]

    _patch_httpx_client(monkeypatch, ["Q2"], {"Q2": "Beta Yacht"})
    run2 = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=1,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    run2_candidate_qids = {c["qid"] for c in run2["candidates"]}
    # (a) candidates contains ONLY the current window's QIDs.
    assert run2_candidate_qids == {"Q2"}
    # (e) no stale AUTO_ADMIT candidate decision leaks in for the absent QID.
    assert "Q1" not in run2_candidate_qids
    # (c) candidates_processed describes only the current window.
    assert run2["discovery"]["candidates_processed"] == 1
    assert len(run2["candidates"]) == 1
    # Q1's historical mapping survives independently in retained_crosswalk.
    run2_crosswalk = {row["qid"]: row["hullq_id"] for row in run2["retained_crosswalk"]}
    assert run2_crosswalk["Q1"] == q1_original_id
    assert run2_crosswalk["Q2"] is not None
    assert len(run2["retained_crosswalk"]) == 2

    _patch_httpx_client(monkeypatch, ["Q1", "Q2"], {"Q1": "Alpha Yacht", "Q2": "Beta Yacht"})
    run3 = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    run3_by_qid = {c["qid"]: c["hullq_id"] for c in run3["candidates"]}
    # (b) Q1 reappears in candidates and reuses its exact original ID.
    assert run3_by_qid == {"Q1": q1_original_id, "Q2": run2_crosswalk["Q2"]}
    assert run3["discovery"]["candidates_processed"] == 2


def test_recompute_offline_accepts_a_live_produced_manifest_with_historical_mappings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """(d) A manifest produced by --live that carries historical mappings in
    retained_crosswalk (for QIDs absent from the current candidates window)
    must still be --recompute-able offline: candidates always share one
    uniform retrieved_at because they only ever hold the current window.
    """
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "REPORT.md"

    _patch_httpx_client(monkeypatch, ["Q1"], {"Q1": "Alpha Yacht"})
    run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=1,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    _patch_httpx_client(monkeypatch, ["Q2"], {"Q2": "Beta Yacht"})
    live_manifest = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=1,
        manifest_path=manifest_path,
        report_path=report_path,
    )
    # Sanity: this manifest does carry a historical-only mapping (Q1) not
    # present in candidates — exactly the scenario that must not break recompute.
    assert {c["qid"] for c in live_manifest["candidates"]} == {"Q2"}
    assert {row["qid"] for row in live_manifest["retained_crosswalk"]} == {"Q1", "Q2"}

    recomputed = recompute_manifest_offline(manifest_path=manifest_path, report_path=report_path)
    assert {c["qid"] for c in recomputed["candidates"]} == {"Q2"}
    assert {row["qid"] for row in recomputed["retained_crosswalk"]} == {"Q1", "Q2"}


def test_recompute_offline_performs_no_network_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """recompute_manifest_offline must not touch the network at all — patch
    httpx.Client to raise if it is ever constructed, proving the offline path
    never imports/uses it.
    """
    import httpx

    def _boom() -> None:
        raise AssertionError("recompute_manifest_offline must not open any network client")

    monkeypatch.setattr(httpx, "Client", _boom)

    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "manifest_version": "0017-v1",
        "source_id": "SRC_WIKIDATA_API_2026",
        "generated_at": "2026-08-21T00:00:00Z",
        "requested_limit": 1,
        "safety_ceiling": 1500,
        "discovery": {
            "unique_qids_returned": 1,
            "candidates_processed": 1,
            "target_reached": False,
        },
        "usage_metrics": {"retrieval_count": 1, "extracted_record_count": 1},
        "candidates": [
            {
                "qid": "Q1",
                "retrieved_at": "2026-08-21T00:00:00Z",
                "preferred_label": "Solo Yacht",
                "aliases": [],
                "hullq_id": "BM_WDT0_RETAINED",
                "decision": "auto_admit",
                "reason_codes": ["ok"],
                "observation_id": "OBS-WD-TIER0-Q1",
                "bundle_id": "BUNDLE-WD-TIER0-Q1",
                "bundle_version": "1",
                "evidence_link_id": "LINK-WD-TIER0-Q1",
            }
        ],
        "counts": {
            "candidates_processed": 1,
            "auto_admit": 1,
            "review_required": 0,
            "not_admitted": 0,
            "reason_breakdown": {"ok": 1},
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = recompute_manifest_offline(
        manifest_path=manifest_path, report_path=tmp_path / "REPORT.md"
    )
    assert result["candidates"][0]["hullq_id"] == "BM_WDT0_RETAINED"
    assert result["candidates"][0]["decision"] == "auto_admit"


def test_recompute_offline_demotes_newly_detected_collision_and_preserves_ids(
    tmp_path: Path,
) -> None:
    """A pair that was previously (incorrectly) both auto_admit under weaker
    collision logic must be demoted to review_required on recompute, while
    each keeps its exact historical HullQ ID as a reserved (non-admitted)
    record — never silently reminted, never force-merged.
    """
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "manifest_version": "0017-v1",
        "source_id": "SRC_WIKIDATA_API_2026",
        "generated_at": "2026-08-21T00:00:00Z",
        "requested_limit": 2,
        "safety_ceiling": 1500,
        "discovery": {
            "unique_qids_returned": 2,
            "candidates_processed": 2,
            "target_reached": False,
        },
        "usage_metrics": {"retrieval_count": 1, "extracted_record_count": 2},
        "candidates": [
            {
                "qid": "Q1",
                "retrieved_at": "2026-08-21T00:00:00Z",
                "preferred_label": "Example Boats Ltd.",
                "aliases": [],
                "hullq_id": "BM_WDT0_OLD_Q1",
                "decision": "auto_admit",
                "reason_codes": ["ok"],
                "observation_id": "OBS-WD-TIER0-Q1",
                "bundle_id": "BUNDLE-WD-TIER0-Q1",
                "bundle_version": "1",
                "evidence_link_id": "LINK-WD-TIER0-Q1",
            },
            {
                "qid": "Q2",
                "retrieved_at": "2026-08-21T00:00:00Z",
                "preferred_label": "Example Boats",
                "aliases": [],
                "hullq_id": "BM_WDT0_OLD_Q2",
                "decision": "auto_admit",
                "reason_codes": ["ok"],
                "observation_id": "OBS-WD-TIER0-Q2",
                "bundle_id": "BUNDLE-WD-TIER0-Q2",
                "bundle_version": "1",
                "evidence_link_id": "LINK-WD-TIER0-Q2",
            },
        ],
        "counts": {
            "candidates_processed": 2,
            "auto_admit": 2,
            "review_required": 0,
            "not_admitted": 0,
            "reason_breakdown": {"ok": 2},
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = recompute_manifest_offline(
        manifest_path=manifest_path, report_path=tmp_path / "REPORT.md"
    )
    by_qid = {c["qid"]: c for c in result["candidates"]}
    assert by_qid["Q1"]["decision"] == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q2"]["decision"] == BootstrapDecision.REVIEW_REQUIRED
    assert by_qid["Q1"]["hullq_id"] == "BM_WDT0_OLD_Q1"
    assert by_qid["Q2"]["hullq_id"] == "BM_WDT0_OLD_Q2"

    # Re-reading the written manifest from disk confirms it was persisted.
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk["counts"]["review_required"] == 2
    assert on_disk["counts"]["auto_admit"] == 0


def test_recompute_offline_fails_closed_on_conflicting_retained_crosswalk(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "manifest_version": "0017-v1",
        "source_id": "SRC_WIKIDATA_API_2026",
        "generated_at": "2026-08-21T00:00:00Z",
        "requested_limit": 2,
        "safety_ceiling": 1500,
        "discovery": {
            "unique_qids_returned": 2,
            "candidates_processed": 2,
            "target_reached": False,
        },
        "usage_metrics": {"retrieval_count": 1, "extracted_record_count": 2},
        "candidates": [
            {
                "qid": "Q1",
                "retrieved_at": "2026-08-21T00:00:00Z",
                "preferred_label": "Solo Yacht One",
                "aliases": [],
                "hullq_id": "BM_WDT0_SHARED",
                "decision": "auto_admit",
                "reason_codes": ["ok"],
                "observation_id": "OBS-WD-TIER0-Q1",
                "bundle_id": "BUNDLE-WD-TIER0-Q1",
                "bundle_version": "1",
                "evidence_link_id": "LINK-WD-TIER0-Q1",
            },
            {
                "qid": "Q2",
                "retrieved_at": "2026-08-21T00:00:00Z",
                "preferred_label": "Solo Yacht Two",
                "aliases": [],
                "hullq_id": "BM_WDT0_SHARED",
                "decision": "auto_admit",
                "reason_codes": ["ok"],
                "observation_id": "OBS-WD-TIER0-Q2",
                "bundle_id": "BUNDLE-WD-TIER0-Q2",
                "bundle_version": "1",
                "evidence_link_id": "LINK-WD-TIER0-Q2",
            },
        ],
        "counts": {
            "candidates_processed": 2,
            "auto_admit": 2,
            "review_required": 0,
            "not_admitted": 0,
            "reason_breakdown": {"ok": 2},
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = manifest_path.read_text(encoding="utf-8")

    with pytest.raises(CrosswalkConflictError):
        recompute_manifest_offline(manifest_path=manifest_path, report_path=tmp_path / "REPORT.md")

    # The manifest on disk must not have been overwritten by a failed recompute.
    assert manifest_path.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# _isolated_schema — offline control-flow proof (no real database)
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    def execute(self, sql: str, *args: object) -> None:
        self._log.append(sql)

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _FakeConn:
    def __init__(self) -> None:
        self.log: list[str] = []
        self.commits = 0

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.log)

    def commit(self) -> None:
        self.commits += 1


def test_isolated_schema_drops_creates_and_sets_search_path_in_order() -> None:
    from bootstrap.wikidata_tier0_runner import _isolated_schema

    conn = _FakeConn()
    with _isolated_schema(conn, "hullq_wdt0_test_schema"):
        conn.log.append("<<inside>>")

    assert conn.log == [
        'DROP SCHEMA IF EXISTS "hullq_wdt0_test_schema" CASCADE',
        'CREATE SCHEMA "hullq_wdt0_test_schema"',
        'SET search_path TO "hullq_wdt0_test_schema"',
        "<<inside>>",
        'DROP SCHEMA IF EXISTS "hullq_wdt0_test_schema" CASCADE',
    ]
    assert conn.commits == 2  # once after setup, once after teardown


def test_isolated_schema_drops_even_if_body_raises() -> None:
    from bootstrap.wikidata_tier0_runner import _isolated_schema

    conn = _FakeConn()
    with pytest.raises(RuntimeError), _isolated_schema(conn, "hullq_wdt0_test_schema"):
        raise RuntimeError("boom")

    assert conn.log[-1] == 'DROP SCHEMA IF EXISTS "hullq_wdt0_test_schema" CASCADE'
