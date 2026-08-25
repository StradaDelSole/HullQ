"""English Wikipedia MediaWiki Action API rights-gated adapter — SLICE-0023.

Implements bounded, rights-gated live acquisition for the SLICE-0023 Wikimedia
category identity-lead discovery pilot:

- ``list=categorymembers`` (``cmnamespace=0``, main-namespace pages only, with
  continuation) over one caller-supplied fixed category title, failing closed
  the instant the running member count exceeds that category's hard cap;
- ``prop=pageprops`` (``ppprop=wikibase_item``) batched lookup of the linked
  Wikidata QID for a bounded list of page IDs.

Does not parse article prose/infobox/table/image/reference content; never
recurses into subcategories; never queries any endpoint other than
``https://en.wikipedia.org/w/api.php``. The SLICE-0021 Wikidata CC0 quality
sample reuses the already-accepted ``hullq.sources.wikidata.WikidataAdapter``
directly rather than being re-implemented here.

Core rule (mirrors ``hullq.sources.wikidata``): both the ``research_lead`` and
``automated_ingestion`` rights gates must return ALLOWED before every HTTP
request, and the fixed per-run request ceiling is enforced before dispatch —
the adapter never grants itself permission from a URL, license name, or
payload content, and never sends a request that would exceed the configured
ceiling.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from hullq.sources.rights import (
    DecisionOutcome,
    ExtractionBudget,
    SourceUsageMetrics,
    SourceUse,
    SourceUseDecision,
    check_source_use,
)

__all__ = [
    "WIKIPEDIA_ACTION_API_ENDPOINT",
    "WIKIPEDIA_SOURCE_ID",
    "CategoryCapExceededError",
    "CategoryMember",
    "RequestCeilingExceededError",
    "WikimediaAcquisitionError",
    "WikimediaAdapter",
    "WikimediaAdapterConfig",
    "WikimediaHTTPError",
    "WikimediaMalformedResponse",
    "WikimediaRightsBlocked",
    "WikimediaThrottled",
    "WikimediaTimeout",
]

WIKIPEDIA_SOURCE_ID = "SRC_WIKIPEDIA_API_2026"
WIKIPEDIA_ACTION_API_ENDPOINT = "https://en.wikipedia.org/w/api.php"

# Documented cmlimit maximum for unauthenticated/non-bot clients.
_CATEGORYMEMBERS_LIMIT = 500

# Batch size for prop=pageprops requests, matching the Wikidata adapter's
# documented wbgetentities batch convention.
_PAGEPROPS_BATCH_SIZE = 50


@dataclass(frozen=True)
class WikimediaAdapterConfig:
    """Immutable configuration for a single bounded SLICE-0023 acquisition run.

    ``user_agent`` must identify HullQ and provide a contact identifier per
    Wikimedia User-Agent policy. ``wikipedia_request_ceiling`` bounds the
    total number of Wikipedia/MediaWiki HTTP requests this adapter instance
    may dispatch across its lifetime.
    """

    user_agent: str
    request_timeout_seconds: float = 30.0
    wikipedia_request_ceiling: int = 75

    def __post_init__(self) -> None:
        ua = self.user_agent.strip()
        if not ua:
            raise ValueError(
                "WikimediaAdapterConfig.user_agent must be a non-empty descriptive string"
            )
        has_hullq = "hullq" in ua.lower()
        has_contact = bool(re.search(r"\S+@\S+\.\S+", ua) or re.search(r"https?://\S+", ua))
        if not has_hullq or not has_contact:
            raise ValueError(
                "WikimediaAdapterConfig.user_agent must identify HullQ and include "
                "a contact identifier (email address or URL), per Wikimedia "
                "User-Agent policy. Example: "
                "'HullQ/0.1 (contact@example.com; https://github.com/example/hullq)'"
            )
        if self.request_timeout_seconds <= 0:
            raise ValueError(
                "WikimediaAdapterConfig.request_timeout_seconds must be a positive number"
            )
        if self.wikipedia_request_ceiling <= 0:
            raise ValueError(
                "WikimediaAdapterConfig.wikipedia_request_ceiling must be a positive integer"
            )


class WikimediaAcquisitionError(Exception):
    """Base class for Wikimedia adapter acquisition errors."""


class WikimediaRightsBlocked(WikimediaAcquisitionError):
    """A rights gate (research_lead or automated_ingestion) returned a
    non-ALLOWED outcome. No HTTP request is sent when this is raised.
    """

    def __init__(self, decision: SourceUseDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Wikimedia {decision.use} gate: {decision.outcome} — "
            f"{sorted(str(r) for r in decision.reasons)}"
        )


class RequestCeilingExceededError(WikimediaAcquisitionError):
    """Raised before dispatch when the next request would exceed the
    configured Wikipedia request ceiling. No HTTP request is sent.
    """

    def __init__(self, would_be_count: int, ceiling: int) -> None:
        self.would_be_count = would_be_count
        self.ceiling = ceiling
        super().__init__(
            f"Dispatching this request would raise the Wikipedia request count to "
            f"{would_be_count}, exceeding the configured ceiling of {ceiling}"
        )


class CategoryCapExceededError(WikimediaAcquisitionError):
    """Raised the instant a category's running main-namespace member count
    exceeds its fixed hard cap, before continuation proceeds any further.
    """

    def __init__(self, category_title: str, observed_count: int, hard_cap: int) -> None:
        self.category_title = category_title
        self.observed_count = observed_count
        self.hard_cap = hard_cap
        super().__init__(
            f"category {category_title!r} exceeded its hard cap of {hard_cap} "
            f"(observed {observed_count} main-namespace pages so far); refusing to continue "
            "continuation-based paging"
        )


class WikimediaThrottled(WikimediaAcquisitionError):
    """HTTP 429 received; no retry loop is attempted."""

    def __init__(self, retry_after: str | None = None) -> None:
        self.retry_after = retry_after
        msg = "Wikimedia API rate-limited (HTTP 429)"
        if retry_after:
            msg += f"; Retry-After: {retry_after}"
        super().__init__(msg)


class WikimediaHTTPError(WikimediaAcquisitionError):
    """Non-throttle HTTP error from the Wikimedia API."""

    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} from {url}")


class WikimediaTimeout(WikimediaAcquisitionError):
    """Request timed out before a response was received."""


class WikimediaMalformedResponse(WikimediaAcquisitionError):
    """Response JSON could not be parsed or lacks the expected structure."""


@dataclass(frozen=True)
class CategoryMember:
    """One acquired main-namespace ``list=categorymembers`` result row."""

    pageid: int
    title: str
    ns: int


class WikimediaAdapter:
    """Rights-gated English Wikipedia MediaWiki Action API adapter for SLICE-0023.

    Requires a reviewed Source record with ``source_id == WIKIPEDIA_SOURCE_ID``
    that satisfies both the ``research_lead`` and ``automated_ingestion``
    rights gates, a valid ``WikimediaAdapterConfig``, and an injected
    ``httpx.Client`` (allows deterministic offline testing without live
    network access).
    """

    def __init__(
        self,
        source: dict[str, Any],
        config: WikimediaAdapterConfig,
        http_client: httpx.Client,
    ) -> None:
        if source.get("source_id") != WIKIPEDIA_SOURCE_ID:
            raise ValueError(
                f"Source record must have source_id={WIKIPEDIA_SOURCE_ID!r}; "
                f"got {source.get('source_id')!r}"
            )
        self._source = source
        self._config = config
        self._client = http_client
        self._usage = SourceUsageMetrics(
            source_id=WIKIPEDIA_SOURCE_ID, retrieval_count=0, extracted_record_count=0
        )

    @property
    def usage_metrics(self) -> SourceUsageMetrics:
        """Current cumulative usage metrics attributed to WIKIPEDIA_SOURCE_ID."""
        return self._usage

    def _check_research_lead_rights(self) -> SourceUseDecision:
        decision = check_source_use(self._source, SourceUse.RESEARCH_LEAD)
        if decision.outcome != DecisionOutcome.ALLOWED:
            raise WikimediaRightsBlocked(decision)
        return decision

    def _check_automated_ingestion_rights(self) -> SourceUseDecision:
        """REQ-RESEARCH-008 cumulative-extraction telemetry check: the
        AUTOMATED_INGESTION gate requires metrics+budget because this source
        is not bulk-cleared. Uses the configured request ceiling as the
        extraction budget so a projected dispatch that would exceed it fails
        closed here in addition to the ``_get``-level ceiling check.

        ``ExtractionBudget.within_limits`` treats a metrics value at-or-above
        ``retrieval_limit`` as exceeded, so the limit is set to
        ``wikipedia_request_ceiling + 1`` here to allow exactly
        ``wikipedia_request_ceiling`` requests (matching the explicit
        ``_get``-level ``RequestCeilingExceededError`` boundary) rather than
        one fewer.
        """
        budget = ExtractionBudget(
            retrieval_limit=self._config.wikipedia_request_ceiling + 1, extracted_record_limit=None
        )
        decision = check_source_use(
            self._source,
            SourceUse.AUTOMATED_INGESTION,
            metrics=self._usage,
            budget=budget,
            projected_retrieval_delta=1,
        )
        if decision.outcome != DecisionOutcome.ALLOWED:
            raise WikimediaRightsBlocked(decision)
        return decision

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._config.user_agent}

    def _get(self, params: dict[str, str]) -> dict[str, Any]:
        """Execute a single GET, enforcing the request ceiling and both
        rights gates before dispatch, and handling throttle/timeout/HTTP
        errors. Increments the retrieval counter after each successful
        dispatch (regardless of HTTP status code) so usage is attributable.
        """
        would_be_count = self._usage.retrieval_count + 1
        if would_be_count > self._config.wikipedia_request_ceiling:
            raise RequestCeilingExceededError(
                would_be_count, self._config.wikipedia_request_ceiling
            )
        self._check_research_lead_rights()
        self._check_automated_ingestion_rights()

        try:
            response = self._client.get(
                WIKIPEDIA_ACTION_API_ENDPOINT,
                params=params,
                headers=self._headers(),
                timeout=self._config.request_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise WikimediaTimeout(f"Request timed out: {exc}") from exc

        self._usage = self._usage.add(retrieval_delta=1)

        if response.status_code == 429:
            retry_after = (
                response.headers.get("Retry-After") if hasattr(response, "headers") else None
            )
            raise WikimediaThrottled(retry_after)
        if response.status_code >= 400:
            raise WikimediaHTTPError(response.status_code, WIKIPEDIA_ACTION_API_ENDPOINT)

        try:
            data: dict[str, Any] = response.json()
        except Exception as exc:
            raise WikimediaMalformedResponse(f"Response is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise WikimediaMalformedResponse(
                f"Expected JSON object at root; got {type(data).__name__}"
            )
        return data

    def fetch_category_members(
        self, category_title: str, *, hard_cap: int
    ) -> tuple[list[CategoryMember], int, int]:
        """Fetch the complete, deduplicated, main-namespace membership of
        ``Category:{category_title}`` via ``list=categorymembers``
        (``cmnamespace=0``), following continuation until exhaustion.

        Returns ``(members, request_count, continuation_count)`` in API
        result order. Fails closed with ``CategoryCapExceededError`` the
        instant the running member count exceeds *hard_cap*, before
        requesting any further continuation page — a category whose true
        membership exceeds its cap is never silently truncated into an
        apparently-complete result.
        """
        members: list[CategoryMember] = []
        seen: set[int] = set()
        cmcontinue: str | None = None
        request_count = 0
        continuation_count = 0

        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": f"Category:{category_title}",
                "cmnamespace": "0",
                "cmlimit": str(_CATEGORYMEMBERS_LIMIT),
                "format": "json",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue

            data = self._get(params)
            request_count += 1

            batch = data.get("query", {}).get("categorymembers")
            if not isinstance(batch, list):
                raise WikimediaMalformedResponse(
                    "categorymembers response missing query.categorymembers list"
                )
            for item in batch:
                if not isinstance(item, dict):
                    raise WikimediaMalformedResponse("categorymembers item is not an object")
                pageid = item.get("pageid")
                title = item.get("title")
                ns = item.get("ns")
                if (
                    not isinstance(pageid, int)
                    or not isinstance(title, str)
                    or not isinstance(ns, int)
                ):
                    raise WikimediaMalformedResponse(
                        "categorymembers item missing valid pageid/title/ns"
                    )
                if ns != 0:
                    # Defense-in-depth: cmnamespace=0 already filters server-side.
                    continue
                if pageid in seen:
                    continue
                seen.add(pageid)
                members.append(CategoryMember(pageid=pageid, title=title, ns=ns))

            if len(members) > hard_cap:
                raise CategoryCapExceededError(category_title, len(members), hard_cap)

            cont = data.get("continue")
            cmcontinue = cont.get("cmcontinue") if isinstance(cont, dict) else None
            if not cmcontinue:
                break
            continuation_count += 1

        return members, request_count, continuation_count

    def fetch_pageprops_wikibase_items(self, pageids: Sequence[int]) -> dict[int, str]:
        """Batched ``prop=pageprops``/``ppprop=wikibase_item`` lookup.

        Returns a ``page_id -> QID`` mapping covering only page IDs that have
        a linked ``wikibase_item`` page property; a page ID absent from the
        returned mapping has no linked Wikidata item. Deduplicates
        *pageids* preserving first-seen order before batching.
        """
        deduped: list[int] = list(dict.fromkeys(pageids))
        result: dict[int, str] = {}

        for i in range(0, len(deduped), _PAGEPROPS_BATCH_SIZE):
            batch = deduped[i : i + _PAGEPROPS_BATCH_SIZE]
            params = {
                "action": "query",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "pageids": "|".join(str(pid) for pid in batch),
                "format": "json",
            }
            data = self._get(params)
            pages = data.get("query", {}).get("pages")
            if not isinstance(pages, dict):
                raise WikimediaMalformedResponse("pageprops response missing query.pages object")
            for page in pages.values():
                if not isinstance(page, dict):
                    continue
                pid = page.get("pageid")
                if not isinstance(pid, int):
                    continue
                props = page.get("pageprops")
                if isinstance(props, dict):
                    qid = props.get("wikibase_item")
                    if isinstance(qid, str) and qid:
                        result[pid] = qid

        return result
