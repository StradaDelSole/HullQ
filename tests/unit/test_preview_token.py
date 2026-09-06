"""Unit tests for finite signed preview-capability bearer tokens — SLICE-0048.

Covers the signing contract required by §5.1: valid round-trip, expiry, max
TTL, tamper, malformed token, wrong secret, and that a tampered/expired/
malformed token always raises the identical `InvalidPreviewTokenError` --
never a distinguishable reason.
"""

from __future__ import annotations

import base64
import os
from datetime import UTC, datetime, timedelta

import pytest

from hullq.domain.market_identity import NativeListingId
from hullq.security.preview_token import (
    DEFAULT_PREVIEW_TTL_SECONDS,
    MAX_PREVIEW_TTL_SECONDS,
    InvalidPreviewTokenError,
    mint_preview_token,
    verify_and_decode_preview_token,
)

_SECRET = os.urandom(32)
_OTHER_SECRET = os.urandom(32)
_NLID = NativeListingId("NL-TOKEN-TEST")


def test_round_trip_returns_the_exact_bound_listing_id() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    claims = verify_and_decode_preview_token(minted.token, secret=_SECRET)
    assert claims.native_listing_id == _NLID
    assert claims.expires_at == minted.expires_at


def test_token_is_url_safe() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    # URL-safe: no characters requiring percent-encoding in a URL path segment.
    assert all(c.isalnum() or c in "-_." for c in minted.token)


def test_default_ttl_matches_documented_24_hours() -> None:
    assert DEFAULT_PREVIEW_TTL_SECONDS == 24 * 3600


def test_max_ttl_matches_documented_seven_days() -> None:
    assert MAX_PREVIEW_TTL_SECONDS == 7 * 24 * 3600


def test_ttl_at_max_is_accepted() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET, ttl_seconds=MAX_PREVIEW_TTL_SECONDS)
    verify_and_decode_preview_token(minted.token, secret=_SECRET)


def test_ttl_above_max_is_rejected_at_mint_time() -> None:
    with pytest.raises(ValueError, match="MAX_PREVIEW_TTL_SECONDS"):
        mint_preview_token(_NLID, secret=_SECRET, ttl_seconds=MAX_PREVIEW_TTL_SECONDS + 1)


def test_zero_or_negative_ttl_is_rejected() -> None:
    with pytest.raises(ValueError):
        mint_preview_token(_NLID, secret=_SECRET, ttl_seconds=0)
    with pytest.raises(ValueError):
        mint_preview_token(_NLID, secret=_SECRET, ttl_seconds=-1)


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(days=2)
    minted = mint_preview_token(_NLID, secret=_SECRET, ttl_seconds=60, now=past)
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(minted.token, secret=_SECRET)


def test_token_still_valid_just_before_expiry() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET, ttl_seconds=100)
    almost_expired = minted.expires_at - timedelta(seconds=1)
    claims = verify_and_decode_preview_token(minted.token, secret=_SECRET, now=almost_expired)
    assert claims.native_listing_id == _NLID


def test_tampered_payload_is_rejected() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    payload_part, signature_part = minted.token.split(".")
    tampered = payload_part[:-1] + ("A" if payload_part[-1] != "A" else "B") + "." + signature_part
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(tampered, secret=_SECRET)


def test_tampered_signature_is_rejected() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    payload_part, signature_part = minted.token.split(".")
    tampered = (
        payload_part + "." + (signature_part[:-1] + ("A" if signature_part[-1] != "A" else "B"))
    )
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(tampered, secret=_SECRET)


def test_wrong_secret_is_rejected() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(minted.token, secret=_OTHER_SECRET)


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        "no-dot-in-this-token",
        "too.many.dots.here",
        "!!!not-base64!!!.alsoinvalid",
    ],
)
def test_malformed_token_structure_is_rejected(malformed: str) -> None:
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(malformed, secret=_SECRET)


def test_unsupported_version_is_rejected() -> None:
    import hashlib
    import hmac
    import json

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    claims = {"v": 999, "nlid": _NLID.value, "exp": int(datetime.now(UTC).timestamp()) + 3600}
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(_SECRET, payload, hashlib.sha256).digest()
    token = f"{b64url(payload)}.{b64url(signature)}"
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(token, secret=_SECRET)


def test_non_string_token_is_rejected() -> None:
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(None, secret=_SECRET)  # type: ignore[arg-type]


def test_mint_rejects_non_native_listing_id() -> None:
    with pytest.raises(TypeError):
        mint_preview_token("NL-RAW-STRING", secret=_SECRET)  # type: ignore[arg-type]


def test_mint_rejects_short_secret() -> None:
    with pytest.raises(ValueError):
        mint_preview_token(_NLID, secret=os.urandom(16))


def test_different_listing_ids_produce_different_tokens() -> None:
    token_a = mint_preview_token(NativeListingId("NL-A"), secret=_SECRET).token
    token_b = mint_preview_token(NativeListingId("NL-B"), secret=_SECRET).token
    assert token_a != token_b
