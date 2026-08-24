"""Unit tests for the SLICE-0021 alternative-discovery extensions on
``WikidataAdapter`` (``run_alt_discovery_item_query``,
``run_alt_discovery_item_desc_query``, ``fetch_sampled_entity_details``).

All tests are offline and deterministic: no live network access occurs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import httpx
import pytest

from hullq.bootstrap.wikidata_sl0021_alt_discovery import R1, R3
from hullq.sources.wikidata import (
    WIKIDATA_BOOTSTRAP_SAFETY_CEILING,
    SampledEntityDetail,
    WikidataAdapter,
    WikidataAdapterConfig,
    WikidataRightsBlocked,
)

ROOT = Path(__file__).resolve().parents[2]
WIKIDATA_FIXTURE = ROOT / "fixtures" / "sources" / "wikidata_source.json"


def _load_wikidata_source() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(WIKIDATA_FIXTURE.read_text(encoding="utf-8")))


def _make_config() -> WikidataAdapterConfig:
    return WikidataAdapterConfig(
        user_agent="HullQ/0.1 (test; contact@example.invalid)", request_timeout_seconds=5.0
    )


def _make_mock_response(json_body: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_body
    resp.headers = {}
    return resp


def _make_adapter(
    source: dict[str, Any] | None = None, mock_client: MagicMock | None = None
) -> WikidataAdapter:
    return WikidataAdapter(
        source=source or _load_wikidata_source(),
        config=_make_config(),
        http_client=mock_client or MagicMock(spec=httpx.Client),
    )


def _bulk_blocked_source() -> dict[str, Any]:
    source = _load_wikidata_source()
    source["rights"]["clearance"]["bulk_bootstrap"] = "prohibited"
    return source


def _automated_blocked_source() -> dict[str, Any]:
    source = _load_wikidata_source()
    source["rights"]["clearance"]["automated_ingestion"] = "prohibited"
    return source


def _item_bindings(qids: list[str]) -> dict[str, Any]:
    return {
        "results": {
            "bindings": [
                {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"}}
                for q in qids
            ]
        }
    }


def _item_desc_bindings(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "results": {
            "bindings": [
                {
                    "item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"},
                    "desc": {"type": "literal", "value": d},
                }
                for q, d in pairs
            ]
        }
    }


# ---------------------------------------------------------------------------
# run_alt_discovery_item_query — rights gating + parsing
# ---------------------------------------------------------------------------


def test_run_alt_discovery_item_query_blocked_by_bulk_bootstrap_before_http() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(source=_bulk_blocked_source(), mock_client=mock_client)
    with pytest.raises(WikidataRightsBlocked):
        adapter.run_alt_discovery_item_query(R1.query_text)
    mock_client.get.assert_not_called()


def test_run_alt_discovery_item_query_blocked_by_automated_ingestion_before_http() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(source=_automated_blocked_source(), mock_client=mock_client)
    with pytest.raises(WikidataRightsBlocked):
        adapter.run_alt_discovery_item_query(R1.query_text)
    mock_client.get.assert_not_called()


def test_run_alt_discovery_item_query_dispatches_exact_query_text_and_parses_qids() -> None:
    captured: dict[str, Any] = {}

    def _fake_get(url: str, params: Any = None, headers: Any = None, timeout: Any = None) -> Any:
        captured["url"] = url
        captured["query"] = params["query"]
        return _make_mock_response(_item_bindings(["Q10", "Q20"]))

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = _fake_get
    adapter = _make_adapter(mock_client=mock_client)
    result = adapter.run_alt_discovery_item_query(R1.query_text)

    assert result == ["Q10", "Q20"]
    assert captured["query"] == R1.query_text
    assert captured["url"] == "https://query.wikidata.org/sparql"


def test_run_alt_discovery_item_query_deduplicates_preserving_order() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_item_bindings(["Q10", "Q20", "Q10"]))
    adapter = _make_adapter(mock_client=mock_client)
    assert adapter.run_alt_discovery_item_query(R1.query_text) == ["Q10", "Q20"]


def test_run_alt_discovery_item_query_increments_retrieval_count() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_item_bindings([]))
    adapter = _make_adapter(mock_client=mock_client)
    adapter.run_alt_discovery_item_query(R1.query_text)
    assert adapter.usage_metrics.retrieval_count == 1


# ---------------------------------------------------------------------------
# run_alt_discovery_item_desc_query (R3) — rights gating + parsing
# ---------------------------------------------------------------------------


def test_run_alt_discovery_item_desc_query_blocked_before_http() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(source=_bulk_blocked_source(), mock_client=mock_client)
    with pytest.raises(WikidataRightsBlocked):
        adapter.run_alt_discovery_item_desc_query(R3.query_text)
    mock_client.get.assert_not_called()


def test_run_alt_discovery_item_desc_query_parses_pairs() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(
        _item_desc_bindings([("Q5", "a sailboat class"), ("Q3", "another sailboat class")])
    )
    adapter = _make_adapter(mock_client=mock_client)
    result = adapter.run_alt_discovery_item_desc_query(R3.query_text)
    assert result == [("Q5", "a sailboat class"), ("Q3", "another sailboat class")]


def test_run_alt_discovery_item_desc_query_dedupes_first_seen_description() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(
        _item_desc_bindings([("Q5", "first description"), ("Q5", "second description")])
    )
    adapter = _make_adapter(mock_client=mock_client)
    result = adapter.run_alt_discovery_item_desc_query(R3.query_text)
    assert result == [("Q5", "first description")]


# ---------------------------------------------------------------------------
# fetch_sampled_entity_details — bounded, identity-relevant fields only
# ---------------------------------------------------------------------------


def _entities_response(entities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"entities": entities}


def _entity_ref_claim(prop_target_qid: str) -> dict[str, Any]:
    return {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {"type": "wikibase-entityid", "value": {"id": prop_target_qid}},
        }
    }


def test_fetch_sampled_entity_details_rejects_invalid_qid_before_network() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(ValueError, match="Invalid QID"):
        adapter.fetch_sampled_entity_details(["Q1", "not-a-qid"])
    mock_client.get.assert_not_called()


def test_fetch_sampled_entity_details_rejects_more_than_safety_ceiling() -> None:
    adapter = _make_adapter()
    qids = [f"Q{i}" for i in range(1, WIKIDATA_BOOTSTRAP_SAFETY_CEILING + 2)]
    with pytest.raises(ValueError, match="exceeds allowed limit"):
        adapter.fetch_sampled_entity_details(qids)


def test_fetch_sampled_entity_details_blocked_before_http_when_rights_not_allowed() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(source=_bulk_blocked_source(), mock_client=mock_client)
    with pytest.raises(WikidataRightsBlocked):
        adapter.fetch_sampled_entity_details(["Q1"])
    mock_client.get.assert_not_called()


def test_fetch_sampled_entity_details_parses_identity_relevant_fields_only() -> None:
    entity_raw = {
        "type": "item",
        "id": "Q42",
        "labels": {"en": {"language": "en", "value": "Test Class"}},
        "aliases": {"en": [{"language": "en", "value": "Test Class Alias"}]},
        "descriptions": {"en": {"language": "en", "value": "a sailboat class"}},
        "claims": {
            "P31": [_entity_ref_claim("Q106179098")],
            "P279": [_entity_ref_claim("Q9999")],
            "P176": [_entity_ref_claim("Q1")],
            "P287": [_entity_ref_claim("Q2")],
            # A broad technical field (length) must NOT surface on
            # SampledEntityDetail at all — only identity-relevant fields do.
            "P2043": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"type": "quantity", "value": {"amount": "+10", "unit": "1"}},
                    }
                }
            ],
        },
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_entities_response({"Q42": entity_raw}))
    adapter = _make_adapter(mock_client=mock_client)

    result = adapter.fetch_sampled_entity_details(["Q42"])

    assert len(result) == 1
    detail = result[0]
    assert isinstance(detail, SampledEntityDetail)
    assert detail.qid == "Q42"
    assert detail.label == "Test Class"
    assert detail.aliases == ["Test Class Alias"]
    assert detail.description_en == "a sailboat class"
    assert detail.p31_qids == ["Q106179098"]
    assert detail.p279_qids == ["Q9999"]
    assert detail.p176_qids == ["Q1"]
    assert detail.p287_qids == ["Q2"]
    assert not hasattr(detail, "loa_m")


def test_fetch_sampled_entity_details_missing_optional_fields_are_empty_or_none() -> None:
    entity_raw = {
        "type": "item",
        "id": "Q7",
        "labels": {},
        "aliases": {},
        "descriptions": {},
        "claims": {},
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_entities_response({"Q7": entity_raw}))
    adapter = _make_adapter(mock_client=mock_client)

    detail = adapter.fetch_sampled_entity_details(["Q7"])[0]
    assert detail.label is None
    assert detail.aliases == []
    assert detail.description_en is None
    assert detail.p31_qids == []
    assert detail.p176_qids == []


def test_fetch_sampled_entity_details_skips_non_item_and_missing_entities() -> None:
    entities_raw = {
        "Q1": {
            "type": "item",
            "id": "Q1",
            "labels": {},
            "aliases": {},
            "descriptions": {},
            "claims": {},
        },
        "Q2": {"type": "property", "id": "Q2"},
        # Q3 deliberately absent from the response.
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_entities_response(entities_raw))
    adapter = _make_adapter(mock_client=mock_client)

    result = adapter.fetch_sampled_entity_details(["Q1", "Q2", "Q3"])
    assert [d.qid for d in result] == ["Q1"]


def test_fetch_sampled_entity_details_batches_by_50_and_checks_rights_per_batch() -> None:
    call_count = {"n": 0}

    def _fake_get(url: str, params: Any = None, headers: Any = None, timeout: Any = None) -> Any:
        call_count["n"] += 1
        ids = params["ids"].split("|")
        entities = {
            qid: {
                "type": "item",
                "id": qid,
                "labels": {},
                "aliases": {},
                "descriptions": {},
                "claims": {},
            }
            for qid in ids
        }
        return _make_mock_response(_entities_response(entities))

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = _fake_get
    adapter = _make_adapter(mock_client=mock_client)

    qids = [f"Q{i}" for i in range(1, 122)]  # 121 QIDs -> 3 batches of 50/50/21
    result = adapter.fetch_sampled_entity_details(qids)

    assert call_count["n"] == 3
    assert len(result) == 121


def test_fetch_sampled_entity_details_ignores_novalue_and_malformed_claims() -> None:
    entity_raw = {
        "type": "item",
        "id": "Q9",
        "labels": {},
        "aliases": {},
        "descriptions": {},
        "claims": {
            "P31": [
                {"mainsnak": {"snaktype": "novalue"}},
                "not-a-dict",
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"type": "string", "value": "nope"},
                    }
                },
                _entity_ref_claim("Q106179098"),
            ]
        },
    }
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = _make_mock_response(_entities_response({"Q9": entity_raw}))
    adapter = _make_adapter(mock_client=mock_client)

    detail = adapter.fetch_sampled_entity_details(["Q9"])[0]
    assert detail.p31_qids == ["Q106179098"]
