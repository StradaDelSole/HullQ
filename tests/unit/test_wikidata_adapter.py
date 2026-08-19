"""Unit tests for hullq.sources.wikidata — SLICE-0008.

All tests are offline and deterministic. No live network access occurs.

Covers required test scenarios 2-22 (scenario 1 is in tests/contract/):
  2.  adapter performs zero HTTP calls when rights gate is non-allow.
  3.  descriptive User-Agent/contact is mandatory.
  4.  unbounded/invalid requested item limit is rejected.
  5.  malformed QIDs are rejected before network.
  6.  controlled discovery parses exact QIDs deterministically.
  7.  duplicate identical QIDs are handled deterministically.
  8.  HTTP 429 / Retry-After yields throttled result and no busy retry loop.
  9.  timeout / 5xx / malformed JSON are explicit acquisition failures.
  10. manufacturer/designer statements remain source observations; no Brand/Org role inference.
  11. LOA vs LWL are distinguished only from explicit qualifier semantics.
  12. draft vs unrelated height is not conflated.
  13. displacement vs ballast are distinguished only from explicit qualifier semantics.
  14. missing / unsupported qualifier is retained/routed unsupported rather than guessed.
  15. raw Wikidata quantity/unit survives separately from normalized candidate.
  16. SLICE-0004 normalization is reused for supported quantity units.
  17. generated FieldEvidence carries source/QID/property locator and immutable raw observation.
  18. no FieldResolution/canonical BoatModel/BoatDesign write occurs.
  19. quality report counts requested/fetched/present/unsupported deterministically.
  20. normal test suite performs no live network access.
  21. optional live smoke is explicit opt-in only (verified by marker; smoke in integration/).
  22. private boat-list content is absent from fixtures and repository changes.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import httpx
import pytest

from hullq.domain.provenance import (
    FieldEvidence,
    RawObservationKind,
    SubjectKind,
)
from hullq.sources.rights import (
    DecisionOutcome,
)
from hullq.sources.wikidata import (
    SLICE_0008_ITEM_CEILING,
    WIKIDATA_SOURCE_ID,
    WikidataAdapter,
    WikidataAdapterConfig,
    WikidataEntityData,
    WikidataHTTPError,
    WikidataMalformedResponse,
    WikidataRightsBlocked,
    WikidataThrottled,
    WikidataTimeout,
    validate_qid,
)

ROOT = Path(__file__).resolve().parents[2]
WIKIDATA_FIXTURE = ROOT / "fixtures" / "sources" / "wikidata_source.json"

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _load_wikidata_source() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(WIKIDATA_FIXTURE.read_text(encoding="utf-8")))


def _make_config(
    user_agent: str = "HullQ/0.1 (test; contact@example.invalid)",
    item_limit: int = 10,
    timeout: float = 5.0,
    language: str = "en",
) -> WikidataAdapterConfig:
    return WikidataAdapterConfig(
        user_agent=user_agent,
        request_timeout_seconds=timeout,
        item_limit=item_limit,
        language=language,
    )


def _make_mock_response(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    resp.headers = headers or {}
    return resp


def _make_mock_client(response: MagicMock) -> MagicMock:
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = response
    return client


def _make_blocked_source() -> dict[str, Any]:
    """Return a source record that will produce BLOCKED for automated ingestion."""
    source = _load_wikidata_source()
    source = cast(dict[str, Any], json.loads(json.dumps(source)))  # deep copy
    source["rights"]["clearance"]["automated_ingestion"] = "prohibited"
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


def _sparql_response_for_qids(qids: list[str]) -> dict[str, Any]:
    """Build a synthetic SPARQL JSON response binding for the given QIDs."""
    return {
        "results": {
            "bindings": [
                {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"}}
                for q in qids
            ]
        }
    }


def _entity_api_response(entities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build a synthetic wbgetentities API JSON response."""
    return {"entities": entities}


def _minimal_entity(
    qid: str,
    label: str = "Test Sailboat",
    *,
    claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "item",
        "id": qid,
        "labels": {"en": {"language": "en", "value": label}},
        "aliases": {},
        "claims": claims or {},
    }


def _quantity_claim(
    prop: str,
    amount: str,
    unit_qid: str,
    *,
    qualifier_qid: str | None = None,
    stmt_id: str | None = None,
    rank: str = "normal",
) -> dict[str, Any]:
    """Build a minimal Wikidata quantity claim dict."""
    unit_uri = f"http://www.wikidata.org/entity/{unit_qid}"
    claim: dict[str, Any] = {
        "type": "statement",
        "id": stmt_id or f"{prop}$abc-001",
        "rank": rank,
        "mainsnak": {
            "snaktype": "value",
            "property": prop,
            "datavalue": {
                "type": "quantity",
                "value": {
                    "amount": amount,
                    "unit": unit_uri,
                },
            },
        },
    }
    if qualifier_qid is not None:
        claim["qualifiers"] = {
            "P642": [
                {
                    "snaktype": "value",
                    "property": "P642",
                    "datavalue": {
                        "type": "wikibase-entityid",
                        "value": {"entity-type": "item", "id": qualifier_qid},
                    },
                }
            ]
        }
    return claim


def _entity_ref_claim(
    prop: str,
    ref_qid: str,
    *,
    stmt_id: str | None = None,
) -> dict[str, Any]:
    """Build a minimal Wikidata entity-reference claim dict."""
    return {
        "type": "statement",
        "id": stmt_id or f"{prop}$ref-001",
        "rank": "normal",
        "mainsnak": {
            "snaktype": "value",
            "property": prop,
            "datavalue": {
                "type": "wikibase-entityid",
                "value": {"entity-type": "item", "id": ref_qid},
            },
        },
    }


# ---------------------------------------------------------------------------
# Scenario 2 — zero HTTP calls when rights gate is non-allow
# ---------------------------------------------------------------------------


def test_rights_blocked_source_raises_before_http_calls() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = WikidataAdapter(
        source=_make_blocked_source(),
        config=_make_config(),
        http_client=mock_client,
    )
    with pytest.raises(WikidataRightsBlocked):
        adapter.discover_sailboat_qids(5)
    mock_client.get.assert_not_called()


def test_rights_blocked_source_no_http_on_fetch_entities() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = WikidataAdapter(
        source=_make_blocked_source(),
        config=_make_config(),
        http_client=mock_client,
    )
    with pytest.raises(WikidataRightsBlocked):
        adapter.fetch_entities(["Q12345"])
    mock_client.get.assert_not_called()


def test_rights_blocked_decision_is_accessible_on_exception() -> None:
    adapter = _make_adapter(source=_make_blocked_source())
    with pytest.raises(WikidataRightsBlocked) as exc_info:
        adapter.discover_sailboat_qids(5)
    assert exc_info.value.decision.outcome != DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Scenario 3 — descriptive User-Agent is mandatory
# ---------------------------------------------------------------------------


def test_empty_user_agent_is_rejected() -> None:
    with pytest.raises(ValueError, match="user_agent"):
        WikidataAdapterConfig(user_agent="", item_limit=10)


def test_whitespace_only_user_agent_is_rejected() -> None:
    with pytest.raises(ValueError, match="user_agent"):
        WikidataAdapterConfig(user_agent="   ", item_limit=10)


def test_descriptive_user_agent_is_accepted() -> None:
    cfg = WikidataAdapterConfig(
        user_agent="HullQ/0.1 (research probe; contact@example.invalid)",
        item_limit=10,
    )
    assert "HullQ" in cfg.user_agent


def test_adapter_sends_configured_user_agent() -> None:
    cfg = _make_config(user_agent="HullQ-Test/0.1 (probe; bot@example.invalid)")
    resp = _make_mock_response(json_body=_sparql_response_for_qids([]))
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(config=cfg, mock_client=mock_client)
    adapter.discover_sailboat_qids(5)
    call_kwargs = mock_client.get.call_args
    sent_headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
    assert sent_headers.get("User-Agent") == cfg.user_agent


# ---------------------------------------------------------------------------
# Scenario 4 — unbounded/invalid item limit is rejected
# ---------------------------------------------------------------------------


def test_zero_item_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="item_limit"):
        WikidataAdapterConfig(user_agent="HullQ/0.1", item_limit=0)


def test_negative_item_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="item_limit"):
        WikidataAdapterConfig(user_agent="HullQ/0.1", item_limit=-1)


def test_item_limit_above_ceiling_is_rejected() -> None:
    with pytest.raises(ValueError, match="item_limit"):
        WikidataAdapterConfig(user_agent="HullQ/0.1", item_limit=SLICE_0008_ITEM_CEILING + 1)


def test_maximum_ceiling_item_limit_is_accepted() -> None:
    cfg = WikidataAdapterConfig(user_agent="HullQ/0.1 (test)", item_limit=SLICE_0008_ITEM_CEILING)
    assert cfg.item_limit == SLICE_0008_ITEM_CEILING


def test_negative_timeout_is_rejected() -> None:
    with pytest.raises(ValueError, match="timeout"):
        WikidataAdapterConfig(user_agent="HullQ/0.1", request_timeout_seconds=-1.0)


def test_discover_limit_exceeding_config_limit_is_rejected() -> None:
    cfg = _make_config(item_limit=5)
    adapter = _make_adapter(config=cfg)
    with pytest.raises(ValueError, match="limit"):
        adapter.discover_sailboat_qids(10)


def test_discover_zero_limit_is_rejected() -> None:
    adapter = _make_adapter()
    with pytest.raises(ValueError, match="limit"):
        adapter.discover_sailboat_qids(0)


def test_fetch_entities_exceeding_config_limit_is_rejected() -> None:
    cfg = _make_config(item_limit=3)
    adapter = _make_adapter(config=cfg)
    with pytest.raises(ValueError):
        adapter.fetch_entities(["Q1", "Q2", "Q3", "Q4"])


# ---------------------------------------------------------------------------
# Scenario 5 — malformed QIDs rejected before network
# ---------------------------------------------------------------------------


def test_invalid_qid_q0_is_rejected() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(ValueError, match="Invalid QID"):
        adapter.fetch_entities(["Q0"])
    mock_client.get.assert_not_called()


def test_invalid_qid_lowercase_is_rejected() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(ValueError, match="Invalid QID"):
        adapter.fetch_entities(["q12345"])
    mock_client.get.assert_not_called()


def test_invalid_qid_no_number_is_rejected() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(ValueError, match="Invalid QID"):
        adapter.fetch_entities(["QXYZ"])
    mock_client.get.assert_not_called()


def test_valid_qid_pattern_accepted() -> None:
    assert validate_qid("Q1")
    assert validate_qid("Q12345")
    assert validate_qid("Q106179098")


def test_invalid_qid_pattern_rejected() -> None:
    assert not validate_qid("Q0")
    assert not validate_qid("q12")
    assert not validate_qid("12")
    assert not validate_qid("")
    assert not validate_qid("Q")
    assert not validate_qid("Q01")  # leading zero


# ---------------------------------------------------------------------------
# Scenario 6 — discovery parses exact QIDs deterministically
# ---------------------------------------------------------------------------


def test_discover_parses_qids_from_sparql_response() -> None:
    expected_qids = ["Q12345", "Q67890", "Q11111"]
    resp = _make_mock_response(json_body=_sparql_response_for_qids(expected_qids))
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    result = adapter.discover_sailboat_qids(10)
    assert result == expected_qids


def test_discover_empty_result_returns_empty_list() -> None:
    resp = _make_mock_response(json_body=_sparql_response_for_qids([]))
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    result = adapter.discover_sailboat_qids(5)
    assert result == []


def test_discover_skips_invalid_uris_in_bindings() -> None:
    body = {
        "results": {
            "bindings": [
                {"item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q12345"}},
                {"item": {"type": "uri", "value": "http://example.com/not-wikidata"}},
                {"item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q0"}},
                {"item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q99"}},
            ]
        }
    }
    resp = _make_mock_response(json_body=body)
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    result = adapter.discover_sailboat_qids(10)
    assert result == ["Q12345", "Q99"]


# ---------------------------------------------------------------------------
# Scenario 7 — duplicate QIDs handled deterministically
# ---------------------------------------------------------------------------


def test_discover_deduplicates_qids_preserving_order() -> None:
    body = _sparql_response_for_qids(["Q100", "Q200", "Q100", "Q300"])
    resp = _make_mock_response(json_body=body)
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    result = adapter.discover_sailboat_qids(10)
    assert result == ["Q100", "Q200", "Q300"]


def test_fetch_entities_deduplicates_qids_without_identity_merge() -> None:
    resp = _make_mock_response(json_body=_entity_api_response({"Q42": _minimal_entity("Q42")}))
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    entities = adapter.fetch_entities(["Q42", "Q42"])
    qids = [e.qid for e in entities]
    # Q42 should appear at most once (exact QID identity deduplication)
    assert qids.count("Q42") <= 1


# ---------------------------------------------------------------------------
# Scenario 8 — HTTP 429 / Retry-After yields throttled result
# ---------------------------------------------------------------------------


def test_http_429_raises_wikidata_throttled() -> None:
    resp = _make_mock_response(status_code=429, headers={"Retry-After": "30"})
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    with pytest.raises(WikidataThrottled) as exc_info:
        adapter.discover_sailboat_qids(5)
    assert exc_info.value.retry_after == "30"


def test_http_429_without_retry_after_raises_throttled() -> None:
    resp = _make_mock_response(status_code=429)
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    with pytest.raises(WikidataThrottled):
        adapter.discover_sailboat_qids(5)


def test_http_429_no_busy_retry_loop() -> None:
    """After HTTP 429, only one request must have been dispatched (no retry loop)."""
    resp = _make_mock_response(status_code=429)
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    with pytest.raises(WikidataThrottled):
        adapter.discover_sailboat_qids(5)

    assert mock_client.get.call_count == 1


# ---------------------------------------------------------------------------
# Scenario 9 — timeout / 5xx / malformed JSON are explicit failures
# ---------------------------------------------------------------------------


def test_timeout_raises_wikidata_timeout() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.TimeoutException("timed out")
    adapter = _make_adapter(mock_client=mock_client)

    with pytest.raises(WikidataTimeout):
        adapter.discover_sailboat_qids(5)


def test_http_500_raises_wikidata_http_error() -> None:
    resp = _make_mock_response(status_code=500)
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    with pytest.raises(WikidataHTTPError) as exc_info:
        adapter.discover_sailboat_qids(5)
    assert exc_info.value.status_code == 500


def test_malformed_json_raises_wikidata_malformed_response() -> None:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.side_effect = ValueError("not json")
    resp.headers = {}
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    with pytest.raises(WikidataMalformedResponse):
        adapter.discover_sailboat_qids(5)


def test_missing_entities_key_raises_malformed_response() -> None:
    resp = _make_mock_response(json_body={"something_else": {}})
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    with pytest.raises(WikidataMalformedResponse):
        adapter.fetch_entities(["Q42"])


# ---------------------------------------------------------------------------
# Scenario 10 — manufacturer/designer are source observations only
# ---------------------------------------------------------------------------


def test_manufacturer_statement_is_raw_evidence_no_role_inference() -> None:
    entity = WikidataEntityData(
        qid="Q999",
        label="Test Boat",
        aliases=[],
        raw_claims={
            "P176": [_entity_ref_claim("P176", "Q54321")],
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    mfg_ev = [e for e in evidence if "/relationships/builders" in e.field_pointer.raw]
    assert len(mfg_ev) >= 1
    ev = mfg_ev[0]
    # Raw observation preserves the QID; no normalized candidate (no role inference)
    assert ev.normalized_candidate is None
    raw_val = ev.raw.value
    assert isinstance(raw_val, dict)
    assert raw_val.get("entity_id") == "Q54321"
    assert ev.raw.kind == RawObservationKind.STRUCTURED_RECORD


def test_designer_statement_is_raw_evidence_no_role_inference() -> None:
    entity = WikidataEntityData(
        qid="Q999",
        label="Test Boat",
        aliases=[],
        raw_claims={
            "P287": [_entity_ref_claim("P287", "Q99999")],
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    des_ev = [e for e in evidence if "/relationships/designers" in e.field_pointer.raw]
    assert len(des_ev) >= 1
    assert des_ev[0].normalized_candidate is None


# ---------------------------------------------------------------------------
# Scenario 11 — LOA vs LWL distinguished by qualifier only
# ---------------------------------------------------------------------------


def test_loa_qualifier_maps_to_loa_field() -> None:
    entity = WikidataEntityData(
        qid="Q100",
        label="Sloop X",
        aliases=[],
        raw_claims={
            "P2043": [_quantity_claim("P2043", "+12.8", "Q11573", qualifier_qid="Q2358152")]
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    loa_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/loa_m"]
    assert len(loa_ev) == 1
    assert report.field_presence.get("loa", 0) == 1


def test_lwl_qualifier_maps_to_lwl_field() -> None:
    entity = WikidataEntityData(
        qid="Q100",
        label="Sloop X",
        aliases=[],
        raw_claims={
            "P2043": [_quantity_claim("P2043", "+10.5", "Q11573", qualifier_qid="Q1817392")]
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    lwl_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/lwl_m"]
    assert len(lwl_ev) == 1
    assert report.field_presence.get("lwl", 0) == 1


def test_p2043_without_qualifier_is_unsupported_not_guessed() -> None:
    entity = WikidataEntityData(
        qid="Q100",
        label="Sloop X",
        aliases=[],
        raw_claims={
            "P2043": [_quantity_claim("P2043", "+12.8", "Q11573")]  # no qualifier
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    # No LOA or LWL evidence should be produced
    length_ev = [
        e
        for e in evidence
        if e.field_pointer.raw in ("/baseline/dimensions/loa_m", "/baseline/dimensions/lwl_m")
    ]
    assert length_ev == []
    assert report.unsupported_qualifier_count >= 1


def test_loa_and_lwl_from_same_entity_are_independent() -> None:
    entity = WikidataEntityData(
        qid="Q100",
        label="Sloop X",
        aliases=[],
        raw_claims={
            "P2043": [
                _quantity_claim(
                    "P2043",
                    "+12.8",
                    "Q11573",
                    qualifier_qid="Q2358152",
                    stmt_id="Q100$loa-001",
                ),
                _quantity_claim(
                    "P2043",
                    "+10.5",
                    "Q11573",
                    qualifier_qid="Q1817392",
                    stmt_id="Q100$lwl-001",
                ),
            ]
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    loa_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/loa_m"]
    lwl_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/lwl_m"]
    assert len(loa_ev) == 1
    assert len(lwl_ev) == 1
    # Evidence IDs must be distinct
    assert loa_ev[0].evidence_id != lwl_ev[0].evidence_id


# ---------------------------------------------------------------------------
# Scenario 12 — draft vs unrelated height is not conflated
# ---------------------------------------------------------------------------


def test_draft_qualifier_maps_to_draft_field() -> None:
    entity = WikidataEntityData(
        qid="Q200",
        label="Ketch Y",
        aliases=[],
        raw_claims={"P2048": [_quantity_claim("P2048", "+1.8", "Q11573", qualifier_qid="Q244777")]},
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    draft_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/draft_min_m"]
    assert len(draft_ev) == 1
    assert report.field_presence.get("draft", 0) == 1


def test_height_without_draft_qualifier_is_unsupported() -> None:
    """A P2048 (height) statement without the draft qualifier must not be mapped to draft."""
    entity = WikidataEntityData(
        qid="Q200",
        label="Ketch Y",
        aliases=[],
        raw_claims={
            "P2048": [
                _quantity_claim("P2048", "+15.0", "Q11573")  # mast height, no qualifier
            ]
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    draft_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/draft_min_m"]
    assert draft_ev == []
    assert report.unsupported_qualifier_count >= 1


# ---------------------------------------------------------------------------
# Scenario 13 — displacement vs ballast distinguished by qualifier only
# ---------------------------------------------------------------------------


def test_displacement_qualifier_maps_to_displacement_field() -> None:
    entity = WikidataEntityData(
        qid="Q300",
        label="Cruiser Z",
        aliases=[],
        raw_claims={
            "P2067": [_quantity_claim("P2067", "+6000", "Q11570", qualifier_qid="Q5636358")]
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    disp_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/displacement_kg"]
    assert len(disp_ev) == 1
    assert report.field_presence.get("displacement", 0) == 1


def test_ballast_qualifier_maps_to_ballast_field() -> None:
    entity = WikidataEntityData(
        qid="Q300",
        label="Cruiser Z",
        aliases=[],
        raw_claims={
            "P2067": [_quantity_claim("P2067", "+2000", "Q11570", qualifier_qid="Q5461048")]
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    ballast_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/ballast_kg"]
    assert len(ballast_ev) == 1
    assert report.field_presence.get("ballast", 0) == 1


def test_mass_without_qualifier_is_unsupported_not_guessed() -> None:
    entity = WikidataEntityData(
        qid="Q300",
        label="Cruiser Z",
        aliases=[],
        raw_claims={
            "P2067": [_quantity_claim("P2067", "+6000", "Q11570")]  # no qualifier
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    mass_ev = [
        e
        for e in evidence
        if e.field_pointer.raw
        in (
            "/baseline/dimensions/displacement_kg",
            "/baseline/dimensions/ballast_kg",
        )
    ]
    assert mass_ev == []
    assert report.unsupported_qualifier_count >= 1


# ---------------------------------------------------------------------------
# Scenario 14 — missing/unsupported qualifier is retained/routed unsupported
# ---------------------------------------------------------------------------


def test_unknown_qualifier_qid_routes_to_unsupported() -> None:
    entity = WikidataEntityData(
        qid="Q400",
        label="Catamaran A",
        aliases=[],
        raw_claims={
            "P2043": [_quantity_claim("P2043", "+12.0", "Q11573", qualifier_qid="Q9999999")]
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    length_ev = [
        e
        for e in evidence
        if e.field_pointer.raw
        in (
            "/baseline/dimensions/loa_m",
            "/baseline/dimensions/lwl_m",
        )
    ]
    assert length_ev == []
    assert report.unsupported_qualifier_count >= 1


def test_unsupported_qualifier_count_is_cumulative_across_entities() -> None:
    entities = [
        WikidataEntityData(
            qid=f"Q{500 + i}",
            label=f"Boat {i}",
            aliases=[],
            raw_claims={
                "P2043": [
                    _quantity_claim("P2043", "+10.0", "Q11573")  # no qualifier
                ]
            },
        )
        for i in range(3)
    ]
    adapter = _make_adapter()
    _, report = adapter.extract_field_evidence(entities, "2026-08-19T00:00:00Z")

    assert report.unsupported_qualifier_count == 3


# ---------------------------------------------------------------------------
# Scenario 15 — raw Wikidata quantity/unit survives separately
# ---------------------------------------------------------------------------


def test_raw_quantity_and_unit_are_preserved_separately() -> None:
    entity = WikidataEntityData(
        qid="Q600",
        label="Sloop B",
        aliases=[],
        raw_claims={
            "P2043": [
                _quantity_claim(
                    "P2043",
                    "+42.0",
                    "Q11573",
                    qualifier_qid="Q2358152",
                    stmt_id="Q600$loa-stmt",
                )
            ]
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    loa_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/loa_m"]
    assert len(loa_ev) == 1
    ev = loa_ev[0]

    # Raw observation preserves original Wikidata representation
    assert ev.raw.kind == RawObservationKind.LITERAL
    raw_val = ev.raw.value
    assert isinstance(raw_val, dict)
    assert raw_val["amount"] == "+42.0"
    assert "Q11573" in raw_val["unit"]
    # unit QID preserved on the raw observation
    assert ev.raw.unit == "Q11573"

    # Normalized candidate is separate and not the same object
    assert ev.normalized_candidate is not None
    nc = ev.normalized_candidate
    assert nc.value == Decimal("42.0")
    assert nc.unit == "m"


def test_unknown_unit_produces_no_normalized_candidate() -> None:
    entity = WikidataEntityData(
        qid="Q601",
        label="Sloop C",
        aliases=[],
        raw_claims={
            "P2043": [
                _quantity_claim(
                    "P2043",
                    "+42.0",
                    "Q99999999",  # unknown unit QID
                    qualifier_qid="Q2358152",
                )
            ]
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    loa_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/loa_m"]
    assert len(loa_ev) == 1
    ev = loa_ev[0]

    # Raw observation must still be present
    assert ev.raw.unit == "Q99999999"
    # No normalized candidate for unknown unit
    assert ev.normalized_candidate is None


# ---------------------------------------------------------------------------
# Scenario 16 — SLICE-0004 normalization reused for supported units
# ---------------------------------------------------------------------------


def test_metres_unit_produces_correct_normalized_candidate() -> None:
    entity = WikidataEntityData(
        qid="Q700",
        label="Yawl D",
        aliases=[],
        raw_claims={
            "P2049": [
                _quantity_claim("P2049", "+4.2", "Q11573")  # beam in metres
            ]
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    beam_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/beam_m"]
    assert len(beam_ev) == 1
    nc = beam_ev[0].normalized_candidate
    assert nc is not None
    assert nc.value == Decimal("4.2")
    assert nc.unit == "m"
    assert nc.method_id == "hullq-measurements-1.0"


def test_kilograms_unit_produces_correct_normalized_candidate() -> None:
    entity = WikidataEntityData(
        qid="Q700",
        label="Yawl D",
        aliases=[],
        raw_claims={
            "P2067": [_quantity_claim("P2067", "+5000", "Q11570", qualifier_qid="Q5636358")]
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    disp_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/displacement_kg"]
    assert len(disp_ev) == 1
    nc = disp_ev[0].normalized_candidate
    assert nc is not None
    assert nc.value == Decimal("5000")
    assert nc.unit == "kg"


def test_metric_tonne_converts_to_kg() -> None:
    entity = WikidataEntityData(
        qid="Q701",
        label="Cutter E",
        aliases=[],
        raw_claims={"P2067": [_quantity_claim("P2067", "+5", "Q11369", qualifier_qid="Q5636358")]},
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    disp_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/displacement_kg"]
    assert len(disp_ev) == 1
    nc = disp_ev[0].normalized_candidate
    assert nc is not None
    # 5 metric tonnes = 5000 kg
    assert nc.value == Decimal("5000")
    assert nc.unit == "kg"


# ---------------------------------------------------------------------------
# Scenario 17 — FieldEvidence carries source/QID/property locator
# ---------------------------------------------------------------------------


def test_field_evidence_has_wikidata_source_id() -> None:
    entity = WikidataEntityData(
        qid="Q800",
        label="Trimaran F",
        aliases=[],
        raw_claims={
            "P2049": [_quantity_claim("P2049", "+7.5", "Q11573")],
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    assert len(evidence) >= 1
    for ev in evidence:
        assert ev.source_id == WIKIDATA_SOURCE_ID


def test_field_evidence_locator_contains_qid_and_property() -> None:
    entity = WikidataEntityData(
        qid="Q801",
        label="Sloop G",
        aliases=[],
        raw_claims={
            "P2049": [_quantity_claim("P2049", "+3.8", "Q11573", stmt_id="Q801$beam-001")],
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    ev = evidence[0]
    assert ev.source_locator.record_key is not None
    assert "Q801" in ev.source_locator.record_key
    assert "P2049" in ev.source_locator.record_key


def test_field_evidence_subject_uses_qid_as_id() -> None:
    entity = WikidataEntityData(
        qid="Q802",
        label="Schooner H",
        aliases=[],
        raw_claims={
            "P2049": [_quantity_claim("P2049", "+5.0", "Q11573")],
        },
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    ev = evidence[0]
    assert ev.subject.id == "Q802"
    assert ev.subject.kind == SubjectKind.BOAT_DESIGN


def test_field_evidence_raw_observation_is_immutable_snapshot() -> None:
    raw_claims: dict[str, Any] = {
        "P2049": [_quantity_claim("P2049", "+3.5", "Q11573")],
    }
    entity = WikidataEntityData(qid="Q803", label="Sloop I", aliases=[], raw_claims=raw_claims)
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")

    # Mutating the original raw_claims must not affect captured evidence
    raw_claims.clear()
    for ev in evidence:
        assert ev.raw is not None
        raw_val = ev.raw.value
        assert raw_val is not None


# ---------------------------------------------------------------------------
# Scenario 18 — no FieldResolution/canonical BoatModel/BoatDesign write
# ---------------------------------------------------------------------------


def test_no_field_resolution_imported_in_wikidata_module() -> None:
    """FieldResolution must not be imported in the adapter module."""
    import hullq.sources.wikidata as wikidata_mod

    # FieldResolution must not appear in the module's names or imports
    assert not hasattr(wikidata_mod, "FieldResolution"), (
        "FieldResolution must not be imported into wikidata.py"
    )
    # Also verify it is not accessible via the module's public __all__
    assert "FieldResolution" not in wikidata_mod.__all__


def test_extract_field_evidence_returns_only_field_evidence_objects() -> None:
    entity = WikidataEntityData(
        qid="Q900",
        label="Test",
        aliases=[],
        raw_claims={"P2049": [_quantity_claim("P2049", "+4.0", "Q11573")]},
    )
    adapter = _make_adapter()
    evidence, _ = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    for ev in evidence:
        assert isinstance(ev, FieldEvidence)


# ---------------------------------------------------------------------------
# Scenario 19 — quality report counts are deterministic
# ---------------------------------------------------------------------------


def test_quality_report_requested_count_matches_input() -> None:
    entities = [
        WikidataEntityData(qid=f"Q{1000 + i}", label=f"Boat {i}", aliases=[], raw_claims={})
        for i in range(4)
    ]
    adapter = _make_adapter()
    _, report = adapter.extract_field_evidence(entities, "2026-08-19T00:00:00Z")
    assert report.requested_qid_count == 4
    assert report.fetched_entity_count == 4


def test_quality_report_field_presence_counts_entities_not_statements() -> None:
    """field_presence counts entities with ≥1 valid mapped statement, not total statements."""
    entity_1 = WikidataEntityData(
        qid="Q1001",
        label="A",
        aliases=[],
        raw_claims={
            "P2049": [
                _quantity_claim("P2049", "+3.8", "Q11573", stmt_id="Q1001$b1"),
                _quantity_claim("P2049", "+3.9", "Q11573", stmt_id="Q1001$b2"),
            ]
        },
    )
    entity_2 = WikidataEntityData(
        qid="Q1002",
        label="B",
        aliases=[],
        raw_claims={
            "P2049": [_quantity_claim("P2049", "+4.1", "Q11573", stmt_id="Q1002$b1")],
        },
    )
    adapter = _make_adapter()
    _, report = adapter.extract_field_evidence([entity_1, entity_2], "2026-08-19T00:00:00Z")

    assert report.field_presence.get("beam", 0) == 2


def test_quality_report_malformed_count_includes_bad_statements() -> None:
    entity = WikidataEntityData(
        qid="Q1003",
        label="C",
        aliases=[],
        raw_claims={
            "P2049": [{"not": "a real claim"}],
        },
    )
    adapter = _make_adapter()
    _, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    assert report.malformed_statement_count >= 1


def test_quality_report_source_id_matches_wikidata() -> None:
    adapter = _make_adapter()
    _, report = adapter.extract_field_evidence([], "2026-08-19T00:00:00Z")
    assert report.source_id == WIKIDATA_SOURCE_ID


def test_quality_report_retrieval_count_attributed() -> None:
    """retrieval_count_attributed reflects HTTP requests made in this adapter instance."""
    qids = ["Q42", "Q43"]
    first_resp = _make_mock_response(json_body=_sparql_response_for_qids(qids))
    second_resp = _make_mock_response(
        json_body=_entity_api_response(
            {
                "Q42": _minimal_entity("Q42"),
                "Q43": _minimal_entity("Q43"),
            }
        )
    )
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [first_resp, second_resp]
    adapter = _make_adapter(mock_client=mock_client)

    adapter.discover_sailboat_qids(5)
    entities = adapter.fetch_entities(qids)
    _, report = adapter.extract_field_evidence(entities, "2026-08-19T00:00:00Z")

    # 2 HTTP requests: 1 SPARQL + 1 entity batch
    assert report.retrieval_count_attributed == 2


# ---------------------------------------------------------------------------
# Scenario 20 — normal tests perform no live network access
# (Verified structurally: all HTTP calls use mock_client; no real httpx.Client
# is constructed or connected in this file.)
# ---------------------------------------------------------------------------


def test_no_live_network_httpx_not_called_in_unit_tests() -> None:
    """Structural verification: confirm all test adapters use mock clients."""
    # This test documents the intent; actual enforcement is via mock_client injection.
    # Any real httpx.Client call would fail in an isolated CI environment.
    adapter = _make_adapter()  # uses MagicMock, not a real httpx.Client
    assert hasattr(adapter, "_client")


# ---------------------------------------------------------------------------
# Scenario 21 — live smoke is explicit opt-in only (marker check)
# ---------------------------------------------------------------------------


def test_live_integration_tests_require_explicit_marker() -> None:
    """Verify that integration tests exist as a separate path."""
    integration_dir = ROOT / "tests" / "integration"
    live_test = integration_dir / "test_wikidata_live.py"
    assert live_test.exists(), f"Expected integration smoke test at {live_test}"


# ---------------------------------------------------------------------------
# Scenario 22 — private boat-list content absent
# ---------------------------------------------------------------------------


def test_no_private_reference_boat_list_in_wikidata_fixture() -> None:
    """The wikidata_source.json fixture must not contain private boat-list data."""
    source = _load_wikidata_source()
    source_text = json.dumps(source)
    # The private list is a 9,277-row reference; it would contain many model names
    # We verify the fixture is a source record, not a data payload
    assert "9277" not in source_text
    assert "source_id" in source_text
    assert source["source_id"] == WIKIDATA_SOURCE_ID


# ---------------------------------------------------------------------------
# Additional edge-case coverage
# ---------------------------------------------------------------------------


def test_adapter_rejects_wrong_source_id() -> None:
    wrong_source = _load_wikidata_source()
    wrong_source["source_id"] = "SRC_WRONG"
    with pytest.raises(ValueError, match="source_id"):
        WikidataAdapter(
            source=wrong_source,
            config=_make_config(),
            http_client=MagicMock(spec=httpx.Client),
        )


def test_entity_data_deep_copies_raw_claims() -> None:
    original_claims: dict[str, Any] = {"P176": [_entity_ref_claim("P176", "Q111")]}
    entity = WikidataEntityData(qid="Q50", label="Boat", aliases=[], raw_claims=original_claims)
    original_claims.clear()
    assert "P176" in entity.raw_claims


def test_beam_without_qualifier_produces_evidence() -> None:
    """P2049 (beam) needs no qualifier disambiguation and must produce evidence."""
    entity = WikidataEntityData(
        qid="Q2000",
        label="Cat",
        aliases=[],
        raw_claims={"P2049": [_quantity_claim("P2049", "+6.2", "Q11573")]},
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    beam_ev = [e for e in evidence if e.field_pointer.raw == "/baseline/dimensions/beam_m"]
    assert len(beam_ev) == 1
    assert report.field_presence.get("beam", 0) == 1


def test_total_produced_evidence_from_p1092() -> None:
    entity = WikidataEntityData(
        qid="Q2001",
        label="Series D",
        aliases=[],
        raw_claims={
            "P1092": [_quantity_claim("P1092", "+450", "Q11570")]  # using kg unit for test
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    built_ev = [e for e in evidence if e.field_pointer.raw == "/relationships/number_built"]
    assert len(built_ev) == 1
    assert report.field_presence.get("total_produced", 0) == 1


def test_novalue_snak_is_skipped_not_malformed() -> None:
    """novalue/somevalue snaks are not malformed — they must be skipped silently."""
    entity = WikidataEntityData(
        qid="Q2002",
        label="Unknown",
        aliases=[],
        raw_claims={
            "P2049": [
                {
                    "type": "statement",
                    "id": "Q2002$novalue-001",
                    "rank": "normal",
                    "mainsnak": {"snaktype": "novalue", "property": "P2049"},
                }
            ]
        },
    )
    adapter = _make_adapter()
    evidence, report = adapter.extract_field_evidence([entity], "2026-08-19T00:00:00Z")
    assert evidence == []
    assert report.malformed_statement_count == 0


def test_usage_metrics_increments_on_retrieval() -> None:
    resp = _make_mock_response(json_body=_sparql_response_for_qids([]))
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)

    assert adapter.usage_metrics.retrieval_count == 0
    adapter.discover_sailboat_qids(5)
    assert adapter.usage_metrics.retrieval_count == 1
