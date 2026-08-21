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
