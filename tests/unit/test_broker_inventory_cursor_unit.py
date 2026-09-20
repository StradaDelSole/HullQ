"""Pure unit tests for the SLICE-0060 inventory opaque-cursor codec.

No PostgreSQL/FastAPI dependency: exercises only
`hullq.application.broker_inventory_read`'s cursor encode/decode round-trip
and its fail-closed malformed-input handling (contract §9: "invalid/
malformed cursors fail as a bounded client error").
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hullq.application.broker_inventory_read import (
    InvalidInventoryCursorError,
    _decode_cursor,
    _encode_cursor,
)
from hullq.domain.market_identity import NativeListingId
from hullq.persistence.native_listing_inventory import InventorySortKey


def test_encode_decode_round_trip_preserves_sort_key() -> None:
    key = InventorySortKey(
        created_at=datetime(2026, 3, 1, 12, 30, 0, tzinfo=UTC),
        native_listing_id=NativeListingId("NL-CURSOR-1"),
    )
    cursor = _encode_cursor(key)
    decoded = _decode_cursor(cursor)
    assert decoded == key


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not-valid-base64!!!",
        "e30=",  # base64 of "{}" -- valid JSON object, but missing required fields
    ],
)
def test_malformed_cursor_fails_closed(raw: str) -> None:
    with pytest.raises(InvalidInventoryCursorError):
        _decode_cursor(raw)


def test_cursor_with_naive_datetime_fails_closed() -> None:
    import base64
    import json

    payload = json.dumps({"created_at": "2026-03-01T12:30:00", "native_listing_id": "NL-X"})
    cursor = base64.urlsafe_b64encode(payload.encode("utf-8")).rstrip(b"=").decode("ascii")
    with pytest.raises(InvalidInventoryCursorError):
        _decode_cursor(cursor)


def test_cursor_with_wrong_type_fields_fails_closed() -> None:
    import base64
    import json

    payload = json.dumps({"created_at": 123, "native_listing_id": "NL-X"})
    cursor = base64.urlsafe_b64encode(payload.encode("utf-8")).rstrip(b"=").decode("ascii")
    with pytest.raises(InvalidInventoryCursorError):
        _decode_cursor(cursor)
