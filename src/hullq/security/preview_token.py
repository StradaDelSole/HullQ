"""Finite signed preview-capability bearer tokens — SLICE-0048.

A preview token is a stateless, URL-safe bearer capability binding token
format/version, an exact `NativeListingId` and an expiry timestamp, signed
with HMAC-SHA-256 under a caller-supplied key
(`hullq.security.preview_signing`). It authorizes nothing beyond "read this
one NativeListing's preview until this timestamp": no token table, no
revocation UI, no session system and no production authentication semantics
are introduced here.

`PREVIEWABLE != PUBLISHED`. A valid token proves only that its holder was
handed this specific capability; it does not by itself prove the referenced
NativeListing's durable chain is complete (see
`hullq.application.preview_read`).

Verification is fail-closed: a tampered signature, wrong secret, malformed
structure, unsupported version or expired token all collapse to the same
`InvalidPreviewTokenError` so a caller cannot distinguish "wrong token" from
"right token, wrong reason" from response shape alone.
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

from hullq.domain.market_identity import NativeListingId

__all__ = [
    "DEFAULT_PREVIEW_TTL_SECONDS",
    "MAX_PREVIEW_TTL_SECONDS",
    "InvalidPreviewTokenError",
    "MintedPreviewToken",
    "PreviewTokenClaims",
    "mint_preview_token",
    "verify_and_decode_preview_token",
]

_TOKEN_VERSION = 1

DEFAULT_PREVIEW_TTL_SECONDS = 24 * 3600
MAX_PREVIEW_TTL_SECONDS = 7 * 24 * 3600


class InvalidPreviewTokenError(ValueError):
    """*token* is malformed, tampered, expired, or signed under a different secret.

    Deliberately carries no further structured detail: the previewable-read
    predicate (SLICE-0048 §6.2) must collapse every one of these cases to
    the same ordinary external not-found class, so this endpoint is never a
    NativeListingId existence oracle.
    """


@dataclass(frozen=True)
class PreviewTokenClaims:
    """The exact claims bound into one verified preview token."""

    native_listing_id: NativeListingId
    expires_at: datetime


_B64URL_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    """Strictly decode one unpadded base64url token segment.

    Every token this module mints is built purely from `_b64url_encode`,
    which never emits '=' padding or any character outside the base64url
    alphabet -- so a genuine token segment always matches
    `_B64URL_SEGMENT_RE` exactly, and re-encoding its decoded bytes always
    reproduces it byte-for-byte. Two distinct non-canonical-input problems
    must both be rejected, not just one:

    1. `base64.b64decode`/`urlsafe_b64decode` with the default
       `validate=False` silently *discards* any character outside the
       base64 alphabet before decoding rather than rejecting it, so e.g.
       "AB!!!!CD" and "ABCD" would decode identically. Rejecting non-
       alphabet characters via `_B64URL_SEGMENT_RE` first, then decoding
       with `validate=True` too, closes that.

    2. Even with only alphabet-valid characters, a base64 group whose byte
       count isn't a multiple of 3 has a final character encoding some
       "don't-care" trailing bits that carry no information -- e.g. for a
       32-byte SHA-256 signature the last of 43 base64url characters has 2
       significant bits and 2 don't-care bits, so up to 4 *different*,
       fully alphabet-valid characters there all decode to the identical
       signature bytes. A verifier that only checks decoded bytes would
       therefore accept several distinct token strings as "the same"
       token, silently defeating the requirement that a malformed/non-
       canonical token variant fail closed. Re-encoding the decoded bytes
       and requiring an exact match against *text* rejects any such
       non-canonical (nonzero don't-care-bit) alias -- only the one
       canonical encoding of a given byte string is ever accepted.
    """
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
class MintedPreviewToken:
    """One freshly minted preview token and the exact expiry it carries."""

    token: str
    expires_at: datetime


def mint_preview_token(
    native_listing_id: NativeListingId,
    *,
    secret: bytes,
    ttl_seconds: int = DEFAULT_PREVIEW_TTL_SECONDS,
    now: datetime | None = None,
) -> MintedPreviewToken:
    """Mint a finite, stateless, URL-safe signed preview token for *native_listing_id*.

    *ttl_seconds* must be a positive integer no greater than
    `MAX_PREVIEW_TTL_SECONDS` (seven days); the accepted default proof TTL is
    `DEFAULT_PREVIEW_TTL_SECONDS` (24 hours). Token generation performs no
    database read/write: it is pure and stateless.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool):
        raise TypeError(f"ttl_seconds must be an int, got {type(ttl_seconds).__name__}")
    if ttl_seconds <= 0:
        raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}")
    if ttl_seconds > MAX_PREVIEW_TTL_SECONDS:
        raise ValueError(
            f"ttl_seconds must not exceed MAX_PREVIEW_TTL_SECONDS ({MAX_PREVIEW_TTL_SECONDS}), "
            f"got {ttl_seconds}"
        )
    if len(secret) < 32:
        raise ValueError("secret must be at least 32 bytes")

    minted_at = _now(now)
    expires_at = datetime.fromtimestamp(int(minted_at.timestamp()) + ttl_seconds, tz=UTC)

    claims = {
        "v": _TOKEN_VERSION,
        "nlid": native_listing_id.value,
        "exp": int(expires_at.timestamp()),
    }
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = _sign(payload, secret)
    token = f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"
    return MintedPreviewToken(token=token, expires_at=expires_at)


def verify_and_decode_preview_token(
    token: str,
    *,
    secret: bytes,
    now: datetime | None = None,
) -> PreviewTokenClaims:
    """Verify *token*'s signature/expiry and return its bound claims.

    Raises `InvalidPreviewTokenError` for any malformed, tampered, wrong-
    secret, unsupported-version or expired token -- one exception type,
    deliberately no finer-grained reason, so callers cannot use error shape
    to probe listing existence.
    """
    if not isinstance(token, str) or not token:
        raise InvalidPreviewTokenError("token must be a non-empty string")

    parts = token.split(".")
    if len(parts) != 2:
        raise InvalidPreviewTokenError("malformed token structure")
    payload_part, signature_part = parts

    try:
        payload = _b64url_decode(payload_part)
        signature = _b64url_decode(signature_part)
    except (binascii.Error, ValueError) as exc:
        raise InvalidPreviewTokenError("malformed token encoding") from exc

    expected_signature = _sign(payload, secret)
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidPreviewTokenError("invalid token signature")

    try:
        claims = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidPreviewTokenError("malformed token payload") from exc

    if not isinstance(claims, dict):
        raise InvalidPreviewTokenError("malformed token claims")

    version = claims.get("v")
    native_listing_id_value = claims.get("nlid")
    expires_at_epoch = claims.get("exp")

    if version != _TOKEN_VERSION:
        raise InvalidPreviewTokenError(f"unsupported token version {version!r}")
    if not isinstance(native_listing_id_value, str) or not native_listing_id_value:
        raise InvalidPreviewTokenError("malformed token claims: nlid")
    if not isinstance(expires_at_epoch, int) or isinstance(expires_at_epoch, bool):
        raise InvalidPreviewTokenError("malformed token claims: exp")

    expires_at = datetime.fromtimestamp(expires_at_epoch, tz=UTC)
    if expires_at <= _now(now):
        raise InvalidPreviewTokenError("token expired")

    return PreviewTokenClaims(
        native_listing_id=NativeListingId(native_listing_id_value), expires_at=expires_at
    )
