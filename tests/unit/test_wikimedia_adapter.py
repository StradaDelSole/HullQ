"""Unit tests for hullq.sources.wikimedia — SLICE-0023.

All tests are offline and deterministic. No live network access occurs.

Covers:
  1. zero HTTP calls when the rights gate is non-allow;
  2. descriptive User-Agent/contact is mandatory;
  3. request-ceiling enforcement fails closed before dispatch;
  4. list=categorymembers acquisition parses/dedupes/paginates correctly;
  5. a category exceeding its hard cap fails closed mid-continuation;
  6. non-main-namespace members are filtered defensively;
  7. prop=pageprops wikibase_item mapping parses correctly and omits unmapped pages;
  8. HTTP 429 / timeout / malformed JSON are explicit acquisition failures;
  9. usage metrics accumulate deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import httpx
import pytest

from hullq.sources.rights import DecisionOutcome
from hullq.sources.wikimedia import (
    WIKIPEDIA_SOURCE_ID,
    CategoryCapExceededError,
    RequestCeilingExceededError,
    WikimediaAdapter,
    WikimediaAdapterConfig,
    WikimediaHTTPError,
    WikimediaMalformedResponse,
    WikimediaRightsBlocked,
    WikimediaThrottled,
    WikimediaTimeout,
)

ROOT = Path(__file__).resolve().parents[2]
WIKIPEDIA_FIXTURE = ROOT / "fixtures" / "sources" / "wikipedia_source.json"


def _load_wikipedia_source() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(WIKIPEDIA_FIXTURE.read_text(encoding="utf-8")))


def _make_config(
    user_agent: str = "HullQ/0.1 (test; contact@example.invalid)",
    timeout: float = 5.0,
    wikipedia_request_ceiling: int = 75,
) -> WikimediaAdapterConfig:
    return WikimediaAdapterConfig(
        user_agent=user_agent,
        request_timeout_seconds=timeout,
        wikipedia_request_ceiling=wikipedia_request_ceiling,
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


def _make_mock_client(*responses: MagicMock) -> MagicMock:
    client = MagicMock(spec=httpx.Client)
    if len(responses) == 1:
        client.get.return_value = responses[0]
    else:
        client.get.side_effect = list(responses)
    return client


def _make_blocked_source() -> dict[str, Any]:
    source = _load_wikipedia_source()
    source = cast(dict[str, Any], json.loads(json.dumps(source)))
    source["rights"]["clearance"]["research_lead"] = "prohibited"
    return source


def _categorymembers_response(
    items: list[tuple[int, str]], *, cmcontinue: str | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "query": {
            "categorymembers": [{"pageid": pid, "ns": 0, "title": title} for pid, title in items]
        }
    }
    if cmcontinue:
        body["continue"] = {"cmcontinue": cmcontinue, "continue": "-||"}
    return body


def _pageprops_response(pages: dict[int, str | None]) -> dict[str, Any]:
    return {
        "query": {
            "pages": {
                str(pid): (
                    {"pageid": pid, "pageprops": {"wikibase_item": qid}} if qid else {"pageid": pid}
                )
                for pid, qid in pages.items()
            }
        }
    }


def _make_adapter(
    source: dict[str, Any] | None = None,
    config: WikimediaAdapterConfig | None = None,
    mock_client: MagicMock | None = None,
) -> WikimediaAdapter:
    return WikimediaAdapter(
        source=source or _load_wikipedia_source(),
        config=config or _make_config(),
        http_client=mock_client or MagicMock(spec=httpx.Client),
    )


# ---------------------------------------------------------------------------
# Source ID validation
# ---------------------------------------------------------------------------


def test_adapter_rejects_mismatched_source_id() -> None:
    with pytest.raises(ValueError, match="source_id"):
        WikimediaAdapter(
            source={"source_id": "WRONG"},
            config=_make_config(),
            http_client=MagicMock(spec=httpx.Client),
        )


# ---------------------------------------------------------------------------
# Rights gate — zero HTTP calls when non-allow
# ---------------------------------------------------------------------------


def test_rights_blocked_source_raises_before_http_calls() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    adapter = WikimediaAdapter(
        source=_make_blocked_source(), config=_make_config(), http_client=mock_client
    )
    with pytest.raises(WikimediaRightsBlocked):
        adapter.fetch_category_members("Keelboats", hard_cap=2000)
    mock_client.get.assert_not_called()


def test_rights_blocked_decision_is_accessible_on_exception() -> None:
    adapter = _make_adapter(source=_make_blocked_source())
    with pytest.raises(WikimediaRightsBlocked) as exc_info:
        adapter.fetch_category_members("Keelboats", hard_cap=2000)
    assert exc_info.value.decision.outcome != DecisionOutcome.ALLOWED


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def test_config_requires_hullq_identifier() -> None:
    with pytest.raises(ValueError, match="identify HullQ"):
        WikimediaAdapterConfig(user_agent="GenericBot/1.0 (contact@example.com)")


def test_config_requires_contact_identifier() -> None:
    with pytest.raises(ValueError, match="contact identifier"):
        WikimediaAdapterConfig(user_agent="HullQ/0.1")


def test_config_rejects_non_positive_ceiling() -> None:
    with pytest.raises(ValueError, match="wikipedia_request_ceiling"):
        WikimediaAdapterConfig(
            user_agent="HullQ/0.1 (contact@example.com)", wikipedia_request_ceiling=0
        )


def test_config_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        WikimediaAdapterConfig(
            user_agent="HullQ/0.1 (contact@example.com)", request_timeout_seconds=0
        )


# ---------------------------------------------------------------------------
# Request-ceiling enforcement
# ---------------------------------------------------------------------------


def test_request_ceiling_exceeded_before_dispatch() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    config = _make_config(wikipedia_request_ceiling=1)
    adapter = WikimediaAdapter(
        source=_load_wikipedia_source(), config=config, http_client=mock_client
    )
    mock_client.get.return_value = _make_mock_response(json_body=_pageprops_response({1: "Q1"}))
    # First request consumes the ceiling of 1.
    adapter.fetch_pageprops_wikibase_items([1])
    with pytest.raises(RequestCeilingExceededError):
        adapter.fetch_pageprops_wikibase_items([2])


# ---------------------------------------------------------------------------
# list=categorymembers acquisition
# ---------------------------------------------------------------------------


def test_fetch_category_members_single_page() -> None:
    mock_client = _make_mock_client(
        _make_mock_response(json_body=_categorymembers_response([(1, "Alpha 30"), (2, "Beta 40")]))
    )
    adapter = _make_adapter(mock_client=mock_client)
    members, request_count, continuation_count = adapter.fetch_category_members(
        "Keelboats", hard_cap=2000
    )
    assert [m.pageid for m in members] == [1, 2]
    assert [m.title for m in members] == ["Alpha 30", "Beta 40"]
    assert request_count == 1
    assert continuation_count == 0
    params = mock_client.get.call_args.kwargs["params"]
    assert params["cmtitle"] == "Category:Keelboats"
    assert params["cmnamespace"] == "0"


def test_fetch_category_members_follows_continuation() -> None:
    mock_client = _make_mock_client(
        _make_mock_response(json_body=_categorymembers_response([(1, "Alpha")], cmcontinue="next")),
        _make_mock_response(json_body=_categorymembers_response([(2, "Beta")])),
    )
    adapter = _make_adapter(mock_client=mock_client)
    members, request_count, continuation_count = adapter.fetch_category_members(
        "Keelboats", hard_cap=2000
    )
    assert [m.pageid for m in members] == [1, 2]
    assert request_count == 2
    assert continuation_count == 1
    second_call_params = mock_client.get.call_args_list[1].kwargs["params"]
    assert second_call_params["cmcontinue"] == "next"


def test_fetch_category_members_deduplicates_repeated_pageid() -> None:
    mock_client = _make_mock_client(
        _make_mock_response(json_body=_categorymembers_response([(1, "Alpha"), (1, "Alpha")]))
    )
    adapter = _make_adapter(mock_client=mock_client)
    members, _, _ = adapter.fetch_category_members("Keelboats", hard_cap=2000)
    assert len(members) == 1


def test_fetch_category_members_filters_non_main_namespace_defensively() -> None:
    body = {
        "query": {
            "categorymembers": [
                {"pageid": 1, "ns": 0, "title": "Alpha"},
                {"pageid": 2, "ns": 14, "title": "Category:Something"},
            ]
        }
    }
    mock_client = _make_mock_client(_make_mock_response(json_body=body))
    adapter = _make_adapter(mock_client=mock_client)
    members, _, _ = adapter.fetch_category_members("Keelboats", hard_cap=2000)
    assert [m.pageid for m in members] == [1]


def test_fetch_category_members_fails_closed_over_hard_cap() -> None:
    items = [(i, f"Page {i}") for i in range(1, 6)]
    mock_client = _make_mock_client(_make_mock_response(json_body=_categorymembers_response(items)))
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(CategoryCapExceededError):
        adapter.fetch_category_members("Keelboats", hard_cap=3)


def test_fetch_category_members_raises_on_malformed_response() -> None:
    mock_client = _make_mock_client(_make_mock_response(json_body={"query": {}}))
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(WikimediaMalformedResponse):
        adapter.fetch_category_members("Keelboats", hard_cap=2000)


# ---------------------------------------------------------------------------
# prop=pageprops QID mapping
# ---------------------------------------------------------------------------


def test_fetch_pageprops_wikibase_items_maps_present_and_omits_absent() -> None:
    mock_client = _make_mock_client(
        _make_mock_response(json_body=_pageprops_response({1: "Q1", 2: None}))
    )
    adapter = _make_adapter(mock_client=mock_client)
    mapping = adapter.fetch_pageprops_wikibase_items([1, 2])
    assert mapping == {1: "Q1"}


def test_fetch_pageprops_wikibase_items_batches_over_fifty() -> None:
    pageids = list(range(1, 121))
    responses = [
        _make_mock_response(
            json_body=_pageprops_response({pid: f"Q{pid}" for pid in pageids[i : i + 50]})
        )
        for i in range(0, len(pageids), 50)
    ]
    mock_client = _make_mock_client(*responses)
    adapter = _make_adapter(mock_client=mock_client)
    mapping = adapter.fetch_pageprops_wikibase_items(pageids)
    assert len(mapping) == 120
    assert mock_client.get.call_count == 3


def test_fetch_pageprops_wikibase_items_raises_on_malformed_response() -> None:
    mock_client = _make_mock_client(_make_mock_response(json_body={"query": {}}))
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(WikimediaMalformedResponse):
        adapter.fetch_pageprops_wikibase_items([1])


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------


def test_throttled_response_raises() -> None:
    mock_client = _make_mock_client(
        _make_mock_response(status_code=429, headers={"Retry-After": "5"})
    )
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(WikimediaThrottled) as exc_info:
        adapter.fetch_category_members("Keelboats", hard_cap=2000)
    assert exc_info.value.retry_after == "5"


def test_http_error_raises() -> None:
    mock_client = _make_mock_client(_make_mock_response(status_code=500))
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(WikimediaHTTPError) as exc_info:
        adapter.fetch_category_members("Keelboats", hard_cap=2000)
    assert exc_info.value.status_code == 500


def test_timeout_raises() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.TimeoutException("boom")
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(WikimediaTimeout):
        adapter.fetch_category_members("Keelboats", hard_cap=2000)


def test_non_json_response_raises_malformed() -> None:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.side_effect = ValueError("not json")
    resp.headers = {}
    mock_client = _make_mock_client(resp)
    adapter = _make_adapter(mock_client=mock_client)
    with pytest.raises(WikimediaMalformedResponse):
        adapter.fetch_category_members("Keelboats", hard_cap=2000)


# ---------------------------------------------------------------------------
# Usage metrics
# ---------------------------------------------------------------------------


def test_usage_metrics_accumulate_across_calls() -> None:
    mock_client = _make_mock_client(
        _make_mock_response(json_body=_categorymembers_response([(1, "Alpha")])),
        _make_mock_response(json_body=_pageprops_response({1: "Q1"})),
    )
    adapter = _make_adapter(mock_client=mock_client)
    adapter.fetch_category_members("Keelboats", hard_cap=2000)
    adapter.fetch_pageprops_wikibase_items([1])
    assert adapter.usage_metrics.source_id == WIKIPEDIA_SOURCE_ID
    assert adapter.usage_metrics.retrieval_count == 2
