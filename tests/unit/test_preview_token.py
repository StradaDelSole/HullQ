"""Unit tests for finite signed preview-capability bearer tokens — SLICE-0048.

Covers the signing contract required by §5.1: valid round-trip, expiry, max
TTL, tamper, malformed token, wrong secret, and that a tampered/expired/
malformed token always raises the identical `InvalidPreviewTokenError` --
never a distinguishable reason.
"""

from __future__ import annotations

import base64
import os
import string
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


# ---------------------------------------------------------------------------
# AMEND regression (PR #156, review 5123788117, finding 2).
#
# `base64.urlsafe_b64decode()` with its default `validate=False` silently
# *discards* characters outside the base64 alphabet before decoding, rather
# than rejecting them. Injecting non-alphabet junk into an otherwise-valid
# segment can therefore decode to the *exact same bytes* as the clean
# original -- letting a formally malformed, non-URL-safe alias of a valid
# bearer token still verify successfully. Every such alias must be rejected.
# ---------------------------------------------------------------------------

_JUNK_INSERTS = ["!!!!", "%20", "~", "@", "#", "\\", "`", "\t"]


@pytest.mark.parametrize("junk", _JUNK_INSERTS)
def test_junk_characters_injected_into_payload_segment_are_rejected(junk: str) -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    payload_part, signature_part = minted.token.split(".")
    tampered = payload_part[:4] + junk + payload_part[4:] + "." + signature_part
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(tampered, secret=_SECRET)


@pytest.mark.parametrize("junk", _JUNK_INSERTS)
def test_junk_characters_injected_into_signature_segment_are_rejected(junk: str) -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    payload_part, signature_part = minted.token.split(".")
    tampered = payload_part + "." + signature_part[:4] + junk + signature_part[4:]
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(tampered, secret=_SECRET)


def test_legacy_lax_decoder_would_have_ignored_this_junk_proving_the_attack_is_real() -> None:
    """Documents *why* the above cases matter: pre-fix, junk characters like
    these were silently stripped by `base64.urlsafe_b64decode`'s default lax
    mode, so the tampered segment decoded to the identical bytes as the
    original -- the exact non-canonical-alias vulnerability this regression
    guards against.
    """
    import base64 as _base64

    original = "AB" + "CDEFGH"
    junked = "AB!!!!CDEFGH"
    padded_original = original + ("=" * ((-len(original)) % 4))
    padded_junked = junked + ("=" * ((-len(junked)) % 4))
    assert _base64.urlsafe_b64decode(padded_original) == _base64.urlsafe_b64decode(padded_junked)


def test_stray_padding_character_inside_segment_is_rejected() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    payload_part, signature_part = minted.token.split(".")
    # A genuine token this module mints never contains '=' in either
    # segment (encoding always strips padding); a variant that reintroduces
    # one must be rejected, not silently re-padded/accepted.
    tampered = payload_part + "=" + "." + signature_part
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(tampered, secret=_SECRET)


def test_non_ascii_lookalike_character_is_rejected() -> None:
    minted = mint_preview_token(_NLID, secret=_SECRET)
    payload_part, signature_part = minted.token.split(".")
    tampered = payload_part[:4] + chr(0x2013) + payload_part[5:] + "." + signature_part  # en dash
    with pytest.raises(InvalidPreviewTokenError):
        verify_and_decode_preview_token(tampered, secret=_SECRET)


def test_non_canonical_dont_care_trailing_bits_are_rejected() -> None:
    """AMEND regression (PR #156, review 5123788117, finding 2 -- extended).

    A 32-byte SHA-256 signature base64url-encodes to 43 characters whose
    final character has 2 significant bits and 2 "don't-care" trailing
    bits: up to 4 distinct, fully alphabet-valid characters there all
    decode to the identical signature bytes. Accepting any of those
    non-canonical aliases would let a formally different token string
    still verify as the original -- exactly the "strict, canonical
    base64url" violation the review's alphabet/`validate=True` fix alone
    does not catch. Every alphabet-valid substitution of the final
    signature character other than the one the encoder actually produced
    must be rejected.
    """
    minted = mint_preview_token(_NLID, secret=_SECRET)
    payload_part, signature_part = minted.token.split(".")
    assert len(signature_part) == 43  # 32-byte digest -> 43 unpadded base64url chars

    alphabet = string.ascii_letters + string.digits + "-_"
    rejected_count = 0
    for candidate_char in alphabet:
        if candidate_char == signature_part[-1]:
            continue
        candidate_token = payload_part + "." + signature_part[:-1] + candidate_char
        with pytest.raises(InvalidPreviewTokenError):
            verify_and_decode_preview_token(candidate_token, secret=_SECRET)
        rejected_count += 1
    assert rejected_count == len(alphabet) - 1


def test_canonical_round_trip_still_accepts_the_real_token() -> None:
    """Companion to the canonicalization regression: the fix must not
    over-correct into rejecting the one genuine, correctly encoded token.
    """
    minted = mint_preview_token(_NLID, secret=_SECRET)
    claims = verify_and_decode_preview_token(minted.token, secret=_SECRET)
    assert claims.native_listing_id == _NLID
