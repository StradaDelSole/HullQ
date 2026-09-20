"""Authenticated Organization inventory overview — SLICE-0060.

Implements `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md`: given
the current session and one explicit Organization, reuse the exact accepted
SLICE-0053 Organization workspace authorization/MFA boundary
(`hullq.application.broker_workspace_read.get_organization_workspace_result`)
and, only once it resolves AUTHORIZED, project that Organization's own
current NativeListing inventory -- exact lifecycle, current offer, current
freshness and public-link availability -- as one bounded, deterministically
ordered, keyset-paginated read model.

This module is read-only: it creates or mutates no lifecycle/offer/
freshness/membership/inventory row. Every fact is resolved by calling the
already-accepted production read functions for that fact
(`hullq.persistence.native_listing_offer.fetch_current_native_listing_offer`,
`hullq.application.native_listing_freshness.resolve_current_freshness`,
`hullq.application.public_listing_read.get_public_listing_read_model`) --
never a second reimplementation of any of those decisions.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.application.native_listing_freshness import resolve_current_freshness
from hullq.application.public_listing_read import get_public_listing_read_model
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_offer import AskingPriceMode
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.native_listing_inventory import (
    InventoryListingRow,
    InventorySortKey,
    fetch_organization_inventory_page,
)
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.security.session_token import SessionClaims

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "InvalidInventoryCursorError",
    "InventoryItemView",
    "InventoryOfferView",
    "InventoryPageView",
    "InventoryReadOutcome",
    "InventoryReadResult",
    "get_organization_inventory_page",
]

#: Contract §9 v0.1 bounds.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class InvalidInventoryCursorError(ValueError):
    """*cursor* is not a validly encoded inventory continuation cursor.

    Raised only for a malformed/tampered cursor -- never for a merely stale
    one. A stale-but-well-formed cursor (pointing past the current last row)
    simply yields zero further rows, not this error.
    """


class InventoryReadOutcome(StrEnum):
    """Mechanically distinct outcomes for one inventory-page request."""

    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    INVALID_PAGE_SIZE = "INVALID_PAGE_SIZE"
    INVALID_CURSOR = "INVALID_CURSOR"
    OK = "OK"


@dataclass(frozen=True)
class InventoryOfferView:
    """Contract §6: exact current offer head, or an explicit absent state."""

    kind: str  # "AMOUNT" | "POA" | "NO_CURRENT_OFFER"
    amount: str | None
    currency: str | None

    def to_public_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "amount": self.amount, "currency": self.currency}


@dataclass(frozen=True)
class InventoryItemView:
    """One inventory row's factual, presentation-ready projection."""

    native_listing_id: str
    lifecycle_state: str
    broker_listing_reference: str | None
    created_at: str
    offer: InventoryOfferView
    freshness_status: str
    last_confirmed_at: str | None
    is_publicly_listed: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "native_listing_id": self.native_listing_id,
            "lifecycle_state": self.lifecycle_state,
            "broker_listing_reference": self.broker_listing_reference,
            "created_at": self.created_at,
            "offer": self.offer.to_public_dict(),
            "freshness_status": self.freshness_status,
            "last_confirmed_at": self.last_confirmed_at,
            "is_publicly_listed": self.is_publicly_listed,
        }


@dataclass(frozen=True)
class InventoryPageView:
    """Contract §9: `next_cursor` is present only when another page exists."""

    items: tuple[InventoryItemView, ...]
    next_cursor: str | None

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"items": [item.to_public_dict() for item in self.items]}
        if self.next_cursor is not None:
            result["next_cursor"] = self.next_cursor
        return result


@dataclass(frozen=True)
class InventoryReadResult:
    """Deterministic result of one inventory-page request.

    Only `OK` carries a page; every other outcome carries none, so a caller
    can never accidentally render a page body for a denied/invalid request.
    """

    outcome: InventoryReadOutcome
    page: InventoryPageView | None = None

    def __post_init__(self) -> None:
        if self.outcome is InventoryReadOutcome.OK:
            if self.page is None:
                raise ValueError("An OK inventory read result must carry a page")
        elif self.page is not None:
            raise ValueError("Only an OK inventory read result may carry a page")


# ---------------------------------------------------------------------------
# Opaque cursor encode/decode
# ---------------------------------------------------------------------------


#: Every cursor this module mints is built purely from `_cursor_b64url_encode`,
#: which never emits '=' padding or any character outside the base64url
#: alphabet -- so a genuine cursor always matches this exactly.
_CURSOR_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _cursor_b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _cursor_b64url_decode(text: str) -> bytes:
    """Strictly decode one unpadded base64url cursor segment.

    Mirrors `hullq.security.preview_token._b64url_decode` /
    `hullq.security.session_token._b64url_decode`. Two distinct non-
    canonical-input problems must both be rejected, not just one:

    1. `base64.b64decode`/`urlsafe_b64decode` with the default
       `validate=False` silently *discards* any character outside the
       base64 alphabet before decoding rather than rejecting it -- so
       without this, a server-issued cursor with illegal characters
       appended (e.g. `"<valid_cursor>!!"`) can decode to the identical
       bytes as the original cursor and be wrongly accepted. Contract §9
       requires invalid/malformed cursors to fail as a bounded client
       error, never be silently normalized away. Rejecting non-alphabet
       characters via `_CURSOR_SEGMENT_RE` first, then decoding with
       `validate=True` too, closes that.
    2. Even with only alphabet-valid characters, a base64 group whose byte
       count isn't a multiple of 3 has a final character encoding some
       "don't-care" trailing bits that carry no information, so several
       distinct alphabet-valid strings could decode to the identical
       bytes. Re-encoding the decoded bytes and requiring an exact match
       against *text* rejects any such non-canonical alias -- only the one
       canonical encoding of a given byte string is ever accepted.
    """
    if not text or not _CURSOR_SEGMENT_RE.fullmatch(text):
        raise InvalidInventoryCursorError("cursor is not strict, canonical, unpadded base64url")
    padded = text + ("=" * ((-len(text)) % 4))
    try:
        decoded = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidInventoryCursorError("malformed cursor encoding") from exc
    if _cursor_b64url_encode(decoded) != text:
        raise InvalidInventoryCursorError(
            "cursor is not the canonical base64url encoding of its bytes"
        )
    return decoded


def _encode_cursor(key: InventorySortKey) -> str:
    payload = {
        "created_at": key.created_at.isoformat(),
        "native_listing_id": key.native_listing_id.value,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _cursor_b64url_encode(raw)


def _decode_cursor(cursor: str) -> InventorySortKey:
    if not isinstance(cursor, str) or not cursor:
        raise InvalidInventoryCursorError("cursor must be a non-empty string")

    raw = _cursor_b64url_decode(cursor)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidInventoryCursorError("malformed cursor payload") from exc
    if not isinstance(payload, dict):
        raise InvalidInventoryCursorError("malformed cursor payload")

    created_at_raw = payload.get("created_at")
    native_listing_id_raw = payload.get("native_listing_id")
    if not isinstance(created_at_raw, str) or not created_at_raw:
        raise InvalidInventoryCursorError("malformed cursor: created_at")
    if not isinstance(native_listing_id_raw, str) or not native_listing_id_raw:
        raise InvalidInventoryCursorError("malformed cursor: native_listing_id")

    try:
        created_at = datetime.fromisoformat(created_at_raw)
    except ValueError as exc:
        raise InvalidInventoryCursorError("malformed cursor: created_at") from exc
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise InvalidInventoryCursorError("malformed cursor: created_at must be timezone-aware")

    return InventorySortKey(
        created_at=created_at, native_listing_id=NativeListingId(native_listing_id_raw)
    )


# ---------------------------------------------------------------------------
# Per-item fact resolution -- reuses existing accepted read functions only
# ---------------------------------------------------------------------------


def _resolve_offer_view(conn: Any, native_listing_id: NativeListingId) -> InventoryOfferView:
    record = fetch_current_native_listing_offer(conn, native_listing_id)
    if record is None:
        return InventoryOfferView(kind="NO_CURRENT_OFFER", amount=None, currency=None)
    offer = record.offer
    if offer.asking_price_mode is AskingPriceMode.POA:
        return InventoryOfferView(kind="POA", amount=None, currency=None)
    assert offer.asking_price_amount is not None
    assert offer.currency is not None
    return InventoryOfferView(
        kind="AMOUNT", amount=str(offer.asking_price_amount), currency=offer.currency
    )


def _build_item_view(conn: Any, row: InventoryListingRow, *, as_of: datetime) -> InventoryItemView:
    offer_view = _resolve_offer_view(conn, row.native_listing_id)
    freshness = resolve_current_freshness(conn, row.native_listing_id, as_of=as_of)
    is_publicly_listed = (
        get_public_listing_read_model(conn, row.native_listing_id, as_of=as_of) is not None
    )
    return InventoryItemView(
        native_listing_id=row.native_listing_id.value,
        lifecycle_state=row.lifecycle_state.value,
        broker_listing_reference=row.broker_listing_reference,
        created_at=row.created_at.isoformat(),
        offer=offer_view,
        freshness_status=freshness.status.value,
        last_confirmed_at=(
            freshness.last_confirmed_at.isoformat()
            if freshness.last_confirmed_at is not None
            else None
        ),
        is_publicly_listed=is_publicly_listed,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def get_organization_inventory_page(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    *,
    page_size: int | None,
    cursor: str | None,
    as_of: datetime,
) -> InventoryReadResult:
    """Evaluate current Organization workspace authorization, then project
    one bounded, deterministically ordered inventory page.

    Authorization is evaluated first and exactly once per call, reusing
    `get_organization_workspace_result` -- the identical accepted SLICE-0053
    boundary the Organization workspace landing itself uses -- so this read
    can never diverge from that decision. Only once it resolves AUTHORIZED
    are *page_size*/*cursor* validated and the inventory query issued.
    """
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return InventoryReadResult(outcome=InventoryReadOutcome.NOT_FOUND_OR_DENIED)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return InventoryReadResult(outcome=InventoryReadOutcome.MFA_REQUIRED)

    if page_size is not None and not (1 <= page_size <= MAX_PAGE_SIZE):
        return InventoryReadResult(outcome=InventoryReadOutcome.INVALID_PAGE_SIZE)
    resolved_page_size = page_size if page_size is not None else DEFAULT_PAGE_SIZE

    after: InventorySortKey | None = None
    if cursor is not None:
        try:
            after = _decode_cursor(cursor)
        except InvalidInventoryCursorError:
            return InventoryReadResult(outcome=InventoryReadOutcome.INVALID_CURSOR)

    # Fetch one extra row to determine whether another page exists without a
    # separate total-count query (contract §9: "no total-count query is
    # required by v0.1").
    rows = fetch_organization_inventory_page(
        conn, organization_id, limit=resolved_page_size + 1, after=after
    )
    has_more = len(rows) > resolved_page_size
    page_rows = rows[:resolved_page_size]

    items = tuple(_build_item_view(conn, row, as_of=as_of) for row in page_rows)
    next_cursor = (
        _encode_cursor(
            InventorySortKey(
                created_at=page_rows[-1].created_at,
                native_listing_id=page_rows[-1].native_listing_id,
            )
        )
        if has_more and page_rows
        else None
    )
    return InventoryReadResult(
        outcome=InventoryReadOutcome.OK,
        page=InventoryPageView(items=items, next_cursor=next_cursor),
    )
