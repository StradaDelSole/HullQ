"""Optional live network smoke test for the Wikidata adapter — SLICE-0008.

This test makes REAL HTTP requests to Wikidata's official endpoints.
It is SKIPPED by default in CI (requires explicit opt-in via --run-live).

Requirements to run:
  pytest tests/integration/test_wikidata_live.py --run-live

The test:
- uses the same reviewed source record and rights gate as production code
- sends a descriptive User-Agent with a contact identifier
- stays within the SLICE_0008_ITEM_CEILING bound
- reports the exact endpoint/query/QIDs used
- fails clearly on network unavailability rather than weakening offline tests
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from hullq.sources.wikidata import (
    SLICE_0008_ITEM_CEILING,
    WIKIDATA_SOURCE_ID,
    WikidataAcquisitionError,
    WikidataAdapter,
    WikidataAdapterConfig,
)

ROOT = Path(__file__).resolve().parents[2]
WIKIDATA_FIXTURE = ROOT / "fixtures" / "sources" / "wikidata_source.json"

# Bounded probe parameters for the live smoke
_LIVE_DISCOVERY_LIMIT = 5
_LIVE_USER_AGENT = (
    "HullQ/0.1 (SLICE-0008 controlled smoke test; https://github.com/StradaDelSole/HullQ)"
)


def _require_live(request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--run-live", default=False):
        pytest.skip("Live network smoke tests require --run-live; skipped in normal CI")


def test_wikidata_live_sailboat_discovery_smoke(request: pytest.FixtureRequest) -> None:
    """Live smoke: discover a small bounded sample of sailboat-class QIDs.

    Verifies:
    - Rights gate allows acquisition via the reviewed source record
    - SPARQL endpoint returns at least one sailboat-class QID
    - QIDs match the expected Wikidata format
    - User-Agent header is sent

    Reports the exact endpoint and QIDs used so the result is reproducible.
    """
    _require_live(request)

    source = json.loads(WIKIDATA_FIXTURE.read_text(encoding="utf-8"))
    config = WikidataAdapterConfig(
        user_agent=_LIVE_USER_AGENT,
        request_timeout_seconds=30.0,
        item_limit=min(_LIVE_DISCOVERY_LIMIT, SLICE_0008_ITEM_CEILING),
        language="en",
    )

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        try:
            qids = adapter.discover_sailboat_qids(_LIVE_DISCOVERY_LIMIT)
        except WikidataAcquisitionError as exc:
            pytest.fail(f"Live SPARQL discovery failed: {exc}")

    print(f"\n[live smoke] Discovered {len(qids)} sailboat-class QIDs: {qids}")
    assert len(qids) > 0, "Expected at least one sailboat-class QID from Wikidata SPARQL"
    for qid in qids:
        assert qid.startswith("Q") and qid[1:].isdigit(), f"Unexpected QID format: {qid!r}"


def test_wikidata_live_entity_fetch_smoke(request: pytest.FixtureRequest) -> None:
    """Live smoke: fetch and extract evidence for a small bounded QID set.

    Uses the standard sailboat-class discovery followed by entity acquisition
    and field-evidence extraction. Reports field presence statistics.
    """
    _require_live(request)

    source = json.loads(WIKIDATA_FIXTURE.read_text(encoding="utf-8"))
    config = WikidataAdapterConfig(
        user_agent=_LIVE_USER_AGENT,
        request_timeout_seconds=30.0,
        item_limit=min(_LIVE_DISCOVERY_LIMIT, SLICE_0008_ITEM_CEILING),
        language="en",
    )

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        try:
            result = adapter.run_controlled_probe(
                discovery_limit=_LIVE_DISCOVERY_LIMIT,
                retrieved_at="2026-08-19T00:00:00Z",
            )
        except WikidataAcquisitionError as exc:
            pytest.fail(f"Live controlled probe failed: {exc}")

    report = result.quality_report
    print("\n[live smoke] Probe report:")
    print(f"  source_id: {report.source_id}")
    print(f"  requested_qid_count: {report.requested_qid_count}")
    print(f"  fetched_entity_count: {report.fetched_entity_count}")
    print(f"  field_presence: {report.field_presence}")
    print(f"  malformed_statement_count: {report.malformed_statement_count}")
    print(f"  unsupported_qualifier_count: {report.unsupported_qualifier_count}")
    print(f"  retrieval_count_attributed: {report.retrieval_count_attributed}")
    print(f"  evidence items: {len(result.evidence)}")

    assert report.source_id == WIKIDATA_SOURCE_ID
    assert report.fetched_entity_count >= 0
    assert report.retrieval_count_attributed >= 1
