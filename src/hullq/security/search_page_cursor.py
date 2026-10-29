"""Signed, tamper-safe bounded Search page continuation cursor — SLICE-0096.

Implements `specs/NATIVE_TECHNICAL_SEARCH_BOUNDED_PAGING_CONTRACT.v0.1.md`
§2's cursor invariant: "bounded-length, opaque to clients, request-bound
(category, active canonical technical requirement, relevant page-size/order
state and serialization version), integrity protected or equivalently
unforgeable, and expiration/invalid-version safe". Deliberately mirrors the
accepted `hullq.security.discovery_surface_signing` shape (SLICE-0071) and
its HMAC-SHA-256/base64url discipline, but is a structurally distinct token
`typ` -- a Search page cursor is navigation state (contract §2: "a
`page_after` opaque continuation token is navigation state, not a technical
Search criterion"), never a lead-discovery-surface provenance claim, and the
two token kinds must never be interchangeable even if the same signing
secret happens to be reused.

The cursor's `last_native_listing_id` is a bounded *transient navigation
hint*, never durable eligibility evidence (contract §3's "Durable source of
truth" invariant) -- verification only proves the cursor was minted by this
server for the exact same domain/query identity/page size and has not
expired; it never re-validates that the named listing itself is still
ACTIVE/eligible (the bounded page evaluator re-reads current truth for every
request regardless of cursor validity).

Verification is fail-closed: a tampered signature, wrong secret, malformed
structure, unsupported version, domain/query-identity/page-size mismatch or
expired token all collapse to `None` -- the caller treats `None` identically
to "no cursor was supplied; reject as an invalid continuation", never a
guess and never an exception that could turn a real validation failure into
an unhandled 500.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

__all__ = [
    "DEFAULT_SEARCH_PAGE_CURSOR_TTL_SECONDS",
    "SearchPageCursorDomain",
    "mint_search_page_cursor",
    "verify_search_page_cursor",
]

_TOKEN_VERSION = 1
_TOKEN_PURPOSE = "hullq_search_page_cursor_v1"

#: Generous enough for a buyer to page through a long result set in one
#: sitting, bounded enough that a stale/shared link cannot indefinitely
#: continue a traversal against since-changed inventory. Exact value is
#: implementation-local (mirrors `discovery_surface_signing`'s identical
#: rationale) -- cursors are transient navigation hints, never durable
#: state, so an expired cursor simply forces a fresh first page, never data
#: loss.
DEFAULT_SEARCH_PAGE_CURSOR_TTL_SECONDS = 3600

_B64URL_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class SearchPageCursorDomain(StrEnum):
    """The two disjoint public bounded-Search surfaces a cursor may belong
    to -- a Sail cursor can never be replayed against the Power route or
    vice versa (contract §2: "Query change, locale/category cross-use ...
    must fail visibly")."""

    SAIL = "SAIL"
    POWER = "POWER"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    if not text or not _B64URL_SEGMENT_RE.fullmatch(text):
        raise ValueError("cursor segment is not strict, canonical, unpadded base64url")
    padded = text + ("=" * ((-len(text)) % 4))
    decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    if _b64url_encode(decoded) != text:
        raise ValueError("cursor segment is not the canonical base64url encoding of its bytes")
    return decoded


def _sign(payload: bytes, secret: bytes) -> bytes:
    return hmac.new(secret, payload, hashlib.sha256).digest()


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)


def mint_search_page_cursor(
    *,
    domain: SearchPageCursorDomain,
    query_identity: str,
    page_size: int,
    last_native_listing_id: str,
    secret: bytes,
    ttl_seconds: int = DEFAULT_SEARCH_PAGE_CURSOR_TTL_SECONDS,
    now: datetime | None = None,
) -> str:
    """Mint a finite, stateless, signed continuation cursor.

    *query_identity* is the exact canonical sparse technical-query string
    (e.g. the criterion-only canonical path/query FastAPI already builds for
    this request, never including `page_after`/`page_size` themselves) the
    cursor is bound to -- a request whose active technical requirement
    differs at all mints/verifies against a different value here, so reusing
    a cursor across a changed query fails closed at verification rather
    than silently continuing the wrong traversal. Pure and stateless --
    performs no database read/write.
    """
    if not isinstance(domain, SearchPageCursorDomain):
        raise TypeError(f"domain must be a SearchPageCursorDomain, got {type(domain).__name__}")
    if not isinstance(query_identity, str):
        raise ValueError("query_identity must be a str")
    if not isinstance(page_size, int) or isinstance(page_size, bool) or page_size <= 0:
        raise ValueError(f"page_size must be a positive int; got {page_size!r}")
    if not isinstance(last_native_listing_id, str) or not last_native_listing_id:
        raise ValueError("last_native_listing_id must be a non-empty str")
    if len(secret) < 32:
        raise ValueError("secret must be at least 32 bytes")
    if ttl_seconds <= 0:
        raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}")

    minted_at = _now(now)
    expires_at = datetime.fromtimestamp(int(minted_at.timestamp()) + ttl_seconds, tz=UTC)
    claims = {
        "v": _TOKEN_VERSION,
        "typ": _TOKEN_PURPOSE,
        "dom": domain.value,
        "q": query_identity,
        "ps": page_size,
        "last": last_native_listing_id,
        "iat": int(minted_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = _sign(payload, secret)
    return f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"


@dataclass(frozen=True, slots=True)
class _DecodedSearchPageCursor:
    domain: SearchPageCursorDomain
    query_identity: str
    page_size: int
    last_native_listing_id: str


def verify_search_page_cursor(
    cursor: object,
    *,
    domain: SearchPageCursorDomain,
    query_identity: str,
    page_size: int,
    secret: bytes,
    now: datetime | None = None,
) -> str | None:
    """Verify *cursor*'s signature/expiry/binding against the exact current
    request's *domain*/*query_identity*/*page_size*, returning the bound
    `last_native_listing_id` or `None` for any invalid input.

    Never raises: a non-`str`, empty, malformed, tampered, wrong-secret,
    unsupported-version, wrong-domain, wrong-query-identity, wrong-page-size
    or expired cursor all resolve to `None` identically -- the caller must
    treat `None` as an invalid continuation (fail closed), never a guess.
    """
    if not isinstance(cursor, str) or not cursor:
        return None
    parts = cursor.split(".")
    if len(parts) != 2:
        return None
    payload_part, signature_part = parts

    try:
        payload = _b64url_decode(payload_part)
        signature = _b64url_decode(signature_part)
    except binascii.Error, ValueError:
        return None

    expected_signature = _sign(payload, secret)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        claims = json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError, json.JSONDecodeError:
        return None
    if not isinstance(claims, dict):
        return None

    if claims.get("v") != _TOKEN_VERSION or claims.get("typ") != _TOKEN_PURPOSE:
        return None
    domain_value = claims.get("dom")
    query_identity_value = claims.get("q")
    page_size_value = claims.get("ps")
    last_value = claims.get("last")
    expires_at_epoch = claims.get("exp")
    if not isinstance(domain_value, str) or not isinstance(query_identity_value, str):
        return None
    if not isinstance(last_value, str) or not last_value:
        return None
    if not isinstance(page_size_value, int) or isinstance(page_size_value, bool):
        return None
    if not isinstance(expires_at_epoch, int) or isinstance(expires_at_epoch, bool):
        return None
    try:
        decoded_domain = SearchPageCursorDomain(domain_value)
    except ValueError:
        return None
    if decoded_domain is not domain:
        return None
    if query_identity_value != query_identity:
        return None
    if page_size_value != page_size:
        return None
    expires_at = datetime.fromtimestamp(expires_at_epoch, tz=UTC)
    if expires_at <= _now(now):
        return None
    decoded = _DecodedSearchPageCursor(
        domain=decoded_domain,
        query_identity=query_identity_value,
        page_size=page_size_value,
        last_native_listing_id=last_value,
    )
    return decoded.last_native_listing_id
