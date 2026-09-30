"""Signed, tamper-safe Lead discovery-surface token — SLICE-0071 amendment.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§8B's "bounded, tamper-safe or server-validatable first-party mechanism":
a finite, HMAC-SHA-256-signed, URL-safe token binding one bounded
`DiscoverySurface` value to the exact `NativeListingId` it was minted for.
Deliberately mirrors the accepted `hullq.security.session_token` (SLICE-0053)
shape and canonical-base64url discipline.

HullQ's own server-rendered surfaces (technical search results, the
shortlist, compare) mint this token when they render a link to a listing's
detail page; the listing detail page itself mints a fresh token for
`DIRECT_LISTING`/`UNKNOWN` when no valid incoming token is present. Either
way, the *browser* only ever forwards an opaque signed token it cannot
construct or alter -- it is never asked to supply (and its value is never
trusted for) a plain discovery-surface string. Verification is fail-closed:
a tampered signature, wrong secret, malformed structure, unsupported
version, listing-id mismatch or expired token all collapse to `None`
(resolved by the caller as `DiscoverySurface.UNKNOWN`), never an exception
that could interrupt Lead creation (contract §8B invariant: "must not ...
[risk] the Lead creation path").
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

from hullq.domain.lead_provenance import DiscoverySurface

__all__ = [
    "DEFAULT_DISCOVERY_TOKEN_TTL_SECONDS",
    "mint_discovery_surface_token",
    "verify_discovery_surface_token",
]

_TOKEN_VERSION = 1
_TOKEN_PURPOSE = "hullq_discovery_surface_v1"

#: Generous enough for a buyer to browse from a search/shortlist/compare
#: page through to submitting the contact form on the listing page, bounded
#: enough that a stale/reused link cannot indefinitely assert stale
#: provenance. Exact value is implementation-local (contract §8B).
DEFAULT_DISCOVERY_TOKEN_TTL_SECONDS = 3600

_B64URL_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    if not text or not _B64URL_SEGMENT_RE.fullmatch(text):
        raise ValueError("token segment is not strict, canonical, unpadded base64url")
    padded = text + ("=" * ((-len(text)) % 4))
    decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    if _b64url_encode(decoded) != text:
        raise ValueError("token segment is not the canonical base64url encoding of its bytes")
    return decoded


def _sign(payload: bytes, secret: bytes) -> bytes:
    return hmac.new(secret, payload, hashlib.sha256).digest()


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)


@dataclass(frozen=True)
class _DecodedToken:
    surface: DiscoverySurface
    native_listing_id: str
    expires_at: datetime


def mint_discovery_surface_token(
    surface: DiscoverySurface,
    native_listing_id: str,
    *,
    secret: bytes,
    ttl_seconds: int = DEFAULT_DISCOVERY_TOKEN_TTL_SECONDS,
    now: datetime | None = None,
) -> str:
    """Mint a finite, stateless, signed discovery-surface token bound to
    *native_listing_id*.

    Pure and stateless -- performs no database read/write, exactly like
    `hullq.security.session_token.mint_session_token`.
    """
    if not isinstance(surface, DiscoverySurface):
        raise TypeError(f"surface must be a DiscoverySurface, got {type(surface).__name__}")
    if not isinstance(native_listing_id, str) or not native_listing_id:
        raise ValueError("native_listing_id must be a non-empty str")
    if len(secret) < 32:
        raise ValueError("secret must be at least 32 bytes")
    if ttl_seconds <= 0:
        raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}")

    minted_at = _now(now)
    expires_at = datetime.fromtimestamp(int(minted_at.timestamp()) + ttl_seconds, tz=UTC)
    claims = {
        "v": _TOKEN_VERSION,
        "typ": _TOKEN_PURPOSE,
        "surface": surface.value,
        "nlid": native_listing_id,
        "iat": int(minted_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = _sign(payload, secret)
    return f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"


def verify_discovery_surface_token(
    token: object,
    native_listing_id: str,
    *,
    secret: bytes,
    now: datetime | None = None,
) -> DiscoverySurface | None:
    """Verify *token*'s signature/expiry/listing-binding and return the
    bound `DiscoverySurface`, or `None` for any invalid input.

    Never raises: a non-`str`, empty, malformed, tampered, wrong-secret,
    unsupported-version, listing-mismatched or expired token all resolve to
    `None` identically -- the caller treats `None` as
    `DiscoverySurface.UNKNOWN`, never a guess and never an error that could
    interrupt Lead creation.
    """
    if not isinstance(token, str) or not token:
        return None
    parts = token.split(".")
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
    surface_value = claims.get("surface")
    nlid_value = claims.get("nlid")
    expires_at_epoch = claims.get("exp")
    if not isinstance(surface_value, str) or not isinstance(nlid_value, str):
        return None
    if not isinstance(expires_at_epoch, int) or isinstance(expires_at_epoch, bool):
        return None
    if nlid_value != native_listing_id:
        return None
    try:
        surface = DiscoverySurface(surface_value)
    except ValueError:
        return None
    expires_at = datetime.fromtimestamp(expires_at_epoch, tz=UTC)
    if expires_at <= _now(now):
        return None
    return surface
