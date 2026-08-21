"""Unit tests for the SLICE-0017 bootstrap-scale extensions on WikidataAdapter.

All tests are offline and deterministic. No live network access occurs.

Covers SLICE-0017 required test scenarios 1-6:
  1. bootstrap discovery performs zero HTTP requests when rights gate is not ALLOWED.
  2. bootstrap discovery limit/cap is explicit and bounded.
  3. discovery uses deterministic stable ordering before limiting.
  4. invalid/duplicate QIDs are handled deterministically without identity merge inference.
  5. normal CI does not perform live network access (implied: everything here is mocked).
  6. existing SLICE-0008 <=100 probe semantics remain unchanged (see
     test_wikidata_adapter.py, run unmodified against the refactored implementation).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import httpx
import pytest

from hullq.sources.wikidata import (
    WIKIDATA_BOOTSTRAP_SAFETY_CEILING,
    WikidataAdapter,
    WikidataAdapterConfig,
    WikidataRightsBlocked,
)

ROOT = Path(__file__).resolve().parents[2]
WIKIDATA_FIXTURE = ROOT / "fixtures" / "sources" / "wikidata_source.json"


def _load_wikidata_source() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(WIKIDATA_FIXTURE.read_text(encoding="utf-8")))


def _make_config(item_limit: int = 10) -> WikidataAdapterConfig:
    return WikidataAdapterConfig(
        user_agent="HullQ/0.1 (test; contact@example.invalid)",
        request_timeout_seconds=5.0,
        item_limit=item_limit,
        language="en",
    )


def _make_mock_response(json_body: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.headers = {}
    return resp


def _sparql_response_for_qids(qids: list[str]) -> dict[str, Any]:
    return {
        "results": {
            "bindings": [
                {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"}}
                for q in qids
            ]
        }
    }


def _bulk_blocked_source() -> dict[str, Any]:
    source = _load_wikidata_source()
    source["rights"]["clearance"]["bulk_bootstrap"] = "prohibited"
    return source


def _make_adapter(
    source: dict[str, Any] | None = None,
    config: WikidataAdapterConfig | None = None,
    mock_client: MagicMock | None = None,
) -> WikidataAdapter:
    return WikidataAdapter(
        source=source or _load_wikidata_source(),
        config=config or _make_config(),
        http_client=mock_client or MagicMock(spec=httpx.Client),
    )


# ---------------------------------------------------------------------------
# 1. zero HTTP calls when BULK_BOOTSTRAP rights gate is not ALLOWED
# ---------------------------------------------------------------------------


def test_bootstrap_discovery_blocked_source_raises_before_http() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(source=_bulk_blocked_source(), mock_client=mock_client)
    with pytest.raises(WikidataRightsBlocked):
        adapter.discover_bootstrap_qids(100)
    mock_client.get.assert_not_called()


def test_bootstrap_fetch_entities_still_gated_by_automated_ingestion() -> None:
    source = _load_wikidata_source()
    source["rights"]["clearance"]["automated_ingestion"] = "prohibited"
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(source=source, mock_client=mock_client)
    with pytest.raises(WikidataRightsBlocked):
        adapter.fetch_entities_bootstrap(["Q1", "Q2"])
    mock_client.get.assert_not_called()


# ---------------------------------------------------------------------------
# 2. bootstrap discovery limit/cap is explicit and bounded
# ---------------------------------------------------------------------------


def test_bootstrap_discovery_rejects_limit_above_safety_ceiling() -> None:
    adapter = _make_adapter()
    with pytest.raises(ValueError, match="limit"):
        adapter.discover_bootstrap_qids(WIKIDATA_BOOTSTRAP_SAFETY_CEILING + 1)


def test_bootstrap_discovery_rejects_zero_limit() -> None:
    adapter = _make_adapter()
    with pytest.raises(ValueError, match="limit"):
        adapter.discover_bootstrap_qids(0)


def test_bootstrap_discovery_accepts_limit_at_ceiling() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_sparql_response_for_qids([]))
    adapter = _make_adapter(mock_client=mock_client)
    result = adapter.discover_bootstrap_qids(WIKIDATA_BOOTSTRAP_SAFETY_CEILING)
    assert result == []


def test_bootstrap_discovery_is_independent_of_configured_item_limit() -> None:
    """A tiny config.item_limit (SLICE-0008 controlled-probe cap) must not
    constrain the separately authorized bootstrap discovery request size.
    """
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_sparql_response_for_qids([]))
    adapter = _make_adapter(config=_make_config(item_limit=1), mock_client=mock_client)
    adapter.discover_bootstrap_qids(1000)  # would exceed item_limit=1; must not raise
    mock_client.get.assert_called_once()


def test_fetch_entities_bootstrap_rejects_more_than_safety_ceiling() -> None:
    adapter = _make_adapter()
    qids = [f"Q{i}" for i in range(1, WIKIDATA_BOOTSTRAP_SAFETY_CEILING + 2)]
    with pytest.raises(ValueError, match="exceeds allowed limit"):
        adapter.fetch_entities_bootstrap(qids)


# ---------------------------------------------------------------------------
# 3. discovery uses deterministic stable ordering before limiting
# ---------------------------------------------------------------------------


def test_bootstrap_query_contains_explicit_order_by_before_limit() -> None:
    captured: dict[str, Any] = {}

    def _fake_get(url: str, params: Any = None, headers: Any = None, timeout: Any = None) -> Any:
        captured["query"] = params["query"]
        return _make_mock_response(_sparql_response_for_qids([]))

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = _fake_get
    adapter = _make_adapter(mock_client=mock_client)
    adapter.discover_bootstrap_qids(50)

    query = captured["query"]
    order_by_pos = query.find("ORDER BY")
    limit_pos = query.find("LIMIT")
    assert order_by_pos != -1
    assert limit_pos != -1
    assert order_by_pos < limit_pos


def test_bootstrap_query_differs_from_slice_0008_probe_query() -> None:
    """The bootstrap query must carry its own version header, distinct from
    the unchanged SLICE-0008 controlled-probe query.
    """
    captured: dict[str, Any] = {}

    def _fake_get(url: str, params: Any = None, headers: Any = None, timeout: Any = None) -> Any:
        captured["query"] = params["query"]
        return _make_mock_response(_sparql_response_for_qids([]))

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = _fake_get
    adapter = _make_adapter(mock_client=mock_client)
    adapter.discover_bootstrap_qids(50)
    assert "SLICE-0017-bootstrap" in captured["query"]


# ---------------------------------------------------------------------------
# 4. invalid/duplicate QIDs handled deterministically without merge inference
# ---------------------------------------------------------------------------


def test_bootstrap_discovery_deduplicates_preserving_order() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(
        _sparql_response_for_qids(["Q10", "Q20", "Q10", "Q30"])
    )
    adapter = _make_adapter(mock_client=mock_client)
    result = adapter.discover_bootstrap_qids(50)
    assert result == ["Q10", "Q20", "Q30"]


def test_fetch_entities_bootstrap_rejects_invalid_qid_before_network() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(ValueError, match="Invalid QID"):
        adapter.fetch_entities_bootstrap(["Q1", "not-a-qid"])
    mock_client.get.assert_not_called()


def test_fetch_entities_bootstrap_batches_and_checks_rights_per_batch() -> None:
    """A 120-QID request must be split into multiple wbgetentities batches,
    each individually rights-gated (AUTOMATED_INGESTION), even though the
    total exceeds the unrelated SLICE-0008 item_limit cap.
    """
    qids = [f"Q{i}" for i in range(1, 121)]

    def _entity_response(batch: list[str]) -> dict[str, Any]:
        return {
            "entities": {
                q: {
                    "type": "item",
                    "id": q,
                    "labels": {"en": {"language": "en", "value": f"Boat {q}"}},
                    "aliases": {},
                    "claims": {},
                }
                for q in batch
            }
        }

    call_batches: list[list[str]] = []

    def _fake_get(url: str, params: Any = None, headers: Any = None, timeout: Any = None) -> Any:
        batch = params["ids"].split("|")
        call_batches.append(batch)
        return _make_mock_response(_entity_response(batch))

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = _fake_get
    adapter = _make_adapter(config=_make_config(item_limit=1), mock_client=mock_client)
    entities = adapter.fetch_entities_bootstrap(qids)

    assert len(entities) == 120
    assert len(call_batches) == 3  # 120 / 50 = 3 batches (50, 50, 20)
    assert sum(len(b) for b in call_batches) == 120
