"""End-to-end runner-level tests for
scripts/bootstrap/wikidata_tier0_sl0018_runner.py.

All tests are offline and deterministic: ``run_live_bootstrap`` is exercised
through a fake ``httpx.Client`` (no real network access) or, for the
above-2,500 rejection test, is proven to reject before ``httpx.Client`` is
ever touched; ``recompute_manifest_offline`` performs no network access at
all by construction.

Covers the SLICE-0018 independent-review correction round:

- Blocker 1: a retained SLICE-0018 QID->HullQ-ID mapping must survive a
  later discovery window that omits it, and must be reused byte-for-byte if
  the QID reappears — proven at the runner level (not only via a pure
  ``classify_delta_candidates``/``build_sl0018_manifest`` unit test).
- Blocker 2: incomplete entity acquisition must fail closed and must not
  overwrite the previously retained manifest.
- Blocker 3: ``requested_limit`` above 2,500 must be rejected before any
  network request.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from bootstrap.wikidata_tier0_sl0018_runner import (  # noqa: E402
    recompute_manifest_offline,
    run_live_bootstrap,
)

from hullq.bootstrap.wikidata_tier0 import (  # noqa: E402
    BootstrapDecision,
)
from hullq.bootstrap.wikidata_tier0 import (  # noqa: E402
    build_manifest as build_baseline_manifest_0017,
)
from hullq.bootstrap.wikidata_tier0 import (  # noqa: E402
    classify_candidates as classify_baseline_candidates_0017,
)
from hullq.bootstrap.wikidata_tier0_sl0018 import DeltaCompletenessError  # noqa: E402
from hullq.sources.wikidata import WikidataEntityData  # noqa: E402

_USER_AGENT = "HullQ/0.1 (test; https://github.com/StradaDelSole/HullQ)"


def _entity(qid: str, label: str | None) -> WikidataEntityData:
    return WikidataEntityData(qid=qid, label=label, aliases=[], raw_claims={})


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


def _small_baseline_manifest_path(tmp_path: Path) -> Path:
    """A small synthetic accepted-baseline-shaped manifest: B1 auto-admits."""
    entities = [_entity("Q1", "Baseline Auto Admit Yacht")]
    candidates = classify_baseline_candidates_0017(entities, retrieved_at="2026-08-21T00:00:00Z")
    manifest = build_baseline_manifest_0017(
        candidates,
        generated_at="2026-08-21T00:00:00Z",
        requested_limit=1,
        unique_qids_returned=1,
        retrieval_count=1,
        extracted_record_count=1,
        target_reached=False,
    )
    path = tmp_path / "baseline_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# BLOCKER 1 — historical crosswalk survives omission/reappearance (runner level)
# ---------------------------------------------------------------------------


def test_retained_sl0018_id_survives_a_discovery_window_that_omits_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Three-run runner-level regression mirroring the accepted SLICE-0017
    ``test_retained_qid_survives_a_discovery_window_that_omits_it``:

    Run 1: discovery returns baseline Q1 + delta Q2 -> mints an ID for Q2.
    Run 2: discovery returns only baseline Q1 (Q2 absent from this window)
           -> candidates contains NO delta rows; Q2's mapping survives in
           retained_crosswalk, not as a stale candidate decision.
    Run 3: discovery returns Q1 and Q2 again -> Q2 reappears in candidates
           and reuses its exact original ID from run 1, never reminted.
    """
    baseline_path = _small_baseline_manifest_path(tmp_path)
    manifest_path = tmp_path / "sl0018_manifest.json"
    report_path = tmp_path / "REPORT.md"

    _patch_httpx_client(
        monkeypatch, ["Q1", "Q2"], {"Q1": "Baseline Auto Admit Yacht", "Q2": "Delta Yacht"}
    )
    first = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2,
        baseline_manifest_path=baseline_path,
        manifest_path=manifest_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    assert {c["qid"] for c in first["candidates"]} == {"Q2"}
    q2_id = next(c["hullq_id"] for c in first["candidates"] if c["qid"] == "Q2")
    assert q2_id is not None
    crosswalk_after_1 = {row["qid"]: row["hullq_id"] for row in first["retained_crosswalk"]}
    assert crosswalk_after_1["Q2"] == q2_id

    # Run 2: Q2 absent from this window's discovery.
    _patch_httpx_client(monkeypatch, ["Q1"], {"Q1": "Baseline Auto Admit Yacht"})
    second = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=1,
        baseline_manifest_path=baseline_path,
        manifest_path=manifest_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    assert second["candidates"] == []  # no delta this run
    crosswalk_after_2 = {row["qid"]: row["hullq_id"] for row in second["retained_crosswalk"]}
    assert crosswalk_after_2["Q2"] == q2_id  # survived, never dropped

    # Run 3: Q2 reappears.
    _patch_httpx_client(
        monkeypatch, ["Q1", "Q2"], {"Q1": "Baseline Auto Admit Yacht", "Q2": "Delta Yacht"}
    )
    third = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2,
        baseline_manifest_path=baseline_path,
        manifest_path=manifest_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    assert {c["qid"] for c in third["candidates"]} == {"Q2"}
    assert third["candidates"][0]["hullq_id"] == q2_id  # reused, never reminted
    assert third["candidates"][0]["decision"] == str(BootstrapDecision.AUTO_ADMIT)


# ---------------------------------------------------------------------------
# BLOCKER 2 — incomplete entity acquisition fails closed at the runner level
# ---------------------------------------------------------------------------


class _IncompleteFakeHttpxClient(_FakeHttpxClient):
    """Discovery reports Q3+Q4 as the delta, but the entity API only returns
    Q3 — simulating a Wikidata response silently omitting a requested QID.
    """

    def get(
        self, url: str, params: Any = None, headers: Any = None, timeout: Any = None
    ) -> _FakeResponse:
        if "query.wikidata.org" in url:
            return _FakeResponse(_sparql_response(self._discovery_qids))
        # Only ever return Q3's entity, regardless of what was requested.
        return _FakeResponse(_entities_response({"Q3": "Found Yacht"}))


def test_run_live_bootstrap_fails_closed_on_incomplete_entity_acquisition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_path = _small_baseline_manifest_path(tmp_path)
    manifest_path = tmp_path / "sl0018_manifest.json"
    report_path = tmp_path / "REPORT.md"

    import httpx

    monkeypatch.setattr(httpx, "Client", lambda: _IncompleteFakeHttpxClient(["Q1", "Q3", "Q4"], {}))

    with pytest.raises(DeltaCompletenessError, match=r"missing=\['Q4'\]"):
        run_live_bootstrap(
            user_agent=_USER_AGENT,
            requested_limit=3,
            baseline_manifest_path=baseline_path,
            manifest_path=manifest_path,
            report_path=report_path,
            verify_baseline_integrity=False,
        )
    # Must not have written a partial/incorrect manifest.
    assert not manifest_path.exists()


# ---------------------------------------------------------------------------
# BLOCKER 3 — requested_limit above 2,500 rejected before any network use
# ---------------------------------------------------------------------------


def test_run_live_bootstrap_rejects_limit_above_2500_before_any_network_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import hullq.sources.wikidata as wikidata_module

    def _explode(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("WikidataAdapter must never be constructed for a rejected limit")

    monkeypatch.setattr(wikidata_module, "WikidataAdapter", _explode)

    with pytest.raises(SystemExit, match="2500"):
        run_live_bootstrap(
            user_agent=_USER_AGENT,
            requested_limit=2501,
            manifest_path=tmp_path / "manifest.json",
            report_path=tmp_path / "REPORT.md",
        )
    assert not (tmp_path / "manifest.json").exists()


def test_run_live_bootstrap_accepts_limit_at_exactly_2500_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_path = _small_baseline_manifest_path(tmp_path)
    manifest_path = tmp_path / "sl0018_manifest.json"
    report_path = tmp_path / "REPORT.md"

    _patch_httpx_client(monkeypatch, ["Q1"], {"Q1": "Baseline Auto Admit Yacht"})
    manifest = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2500,
        baseline_manifest_path=baseline_path,
        manifest_path=manifest_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    assert manifest["requested_limit"] == 2500


# ---------------------------------------------------------------------------
# Offline recompute remains network-free and preserves historical crosswalk
# ---------------------------------------------------------------------------


def test_recompute_preserves_historical_crosswalk_entries_absent_from_delta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_path = _small_baseline_manifest_path(tmp_path)
    manifest_path = tmp_path / "sl0018_manifest.json"
    report_path = tmp_path / "REPORT.md"

    _patch_httpx_client(
        monkeypatch, ["Q1", "Q2"], {"Q1": "Baseline Auto Admit Yacht", "Q2": "Delta Yacht"}
    )
    first = run_live_bootstrap(
        user_agent=_USER_AGENT,
        requested_limit=2,
        baseline_manifest_path=baseline_path,
        manifest_path=manifest_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    q2_id = first["candidates"][0]["hullq_id"]

    recomputed = recompute_manifest_offline(
        baseline_manifest_path=baseline_path,
        manifest_path=manifest_path,
        report_path=report_path,
        verify_baseline_integrity=False,
    )
    assert recomputed["candidates"][0]["hullq_id"] == q2_id
    crosswalk = {row["qid"]: row["hullq_id"] for row in recomputed["retained_crosswalk"]}
    assert crosswalk["Q2"] == q2_id
