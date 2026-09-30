"""Unit tests for hullq.security.discovery_surface_signing — SLICE-0071
Finding A amendment.

Mirrors the SLICE-0053 session-token test discipline: roundtrip, listing-
binding mismatch, tamper, expiry, wrong-secret and malformed-structure all
fail closed to `None` (never raise, never guess) so a caller can uniformly
treat any failure as `DiscoverySurface.UNKNOWN`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hullq.domain.lead_provenance import DiscoverySurface
from hullq.security.discovery_surface_signing import (
    mint_discovery_surface_token,
    verify_discovery_surface_token,
)

SECRET = b"0" * 32
OTHER_SECRET = b"1" * 32


def test_roundtrip_preserves_surface_and_listing_binding() -> None:
    token = mint_discovery_surface_token(DiscoverySurface.TECHNICAL_SEARCH, "NL-1", secret=SECRET)
    assert (
        verify_discovery_surface_token(token, "NL-1", secret=SECRET)
        is DiscoverySurface.TECHNICAL_SEARCH
    )


def test_every_bounded_surface_roundtrips() -> None:
    for surface in DiscoverySurface:
        token = mint_discovery_surface_token(surface, "NL-1", secret=SECRET)
        assert verify_discovery_surface_token(token, "NL-1", secret=SECRET) is surface


def test_wrong_listing_id_binding_fails_closed() -> None:
    token = mint_discovery_surface_token(DiscoverySurface.SHORTLIST, "NL-1", secret=SECRET)
    assert verify_discovery_surface_token(token, "NL-2", secret=SECRET) is None


def test_wrong_secret_fails_closed() -> None:
    token = mint_discovery_surface_token(DiscoverySurface.COMPARE, "NL-1", secret=SECRET)
    assert verify_discovery_surface_token(token, "NL-1", secret=OTHER_SECRET) is None


def test_tampered_signature_fails_closed() -> None:
    token = mint_discovery_surface_token(DiscoverySurface.COMPARE, "NL-1", secret=SECRET)
    payload_part, signature_part = token.split(".")
    tampered = f"{payload_part}.{signature_part[:-1]}{'a' if signature_part[-1] != 'a' else 'b'}"
    assert verify_discovery_surface_token(tampered, "NL-1", secret=SECRET) is None


def test_expired_token_fails_closed() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token = mint_discovery_surface_token(
        DiscoverySurface.DIRECT_LISTING, "NL-1", secret=SECRET, ttl_seconds=60, now=now
    )
    assert (
        verify_discovery_surface_token(
            token, "NL-1", secret=SECRET, now=now + timedelta(seconds=61)
        )
        is None
    )
    assert (
        verify_discovery_surface_token(
            token, "NL-1", secret=SECRET, now=now + timedelta(seconds=59)
        )
        is DiscoverySurface.DIRECT_LISTING
    )


def test_malformed_structure_fails_closed() -> None:
    assert verify_discovery_surface_token("not-a-real-token", "NL-1", secret=SECRET) is None
    assert verify_discovery_surface_token("a.b.c", "NL-1", secret=SECRET) is None
    assert verify_discovery_surface_token("", "NL-1", secret=SECRET) is None


def test_none_and_non_string_input_fail_closed_without_raising() -> None:
    assert verify_discovery_surface_token(None, "NL-1", secret=SECRET) is None
    assert verify_discovery_surface_token(123, "NL-1", secret=SECRET) is None
    assert verify_discovery_surface_token(["not", "a", "token"], "NL-1", secret=SECRET) is None


def test_an_arbitrary_client_supplied_string_is_never_trusted_as_a_surface() -> None:
    """The exact independent-review invariant: 'no arbitrary discovery value
    can be injected as authoritative provenance'."""
    for forged in ("SHORTLIST", "TECHNICAL_SEARCH", '{"surface":"SHORTLIST","nlid":"NL-1"}'):
        assert verify_discovery_surface_token(forged, "NL-1", secret=SECRET) is None


def test_token_minted_for_a_different_token_purpose_is_rejected() -> None:
    """A token minted by an unrelated HMAC-signing scheme (same secret,
    different payload shape/purpose) must never be accepted -- domain
    separation via the embedded `typ` claim, not merely the signature."""
    import base64
    import hashlib
    import hmac
    import json

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    foreign_claims = {
        "v": 1,
        "typ": "some_other_token_type",
        "surface": DiscoverySurface.SHORTLIST.value,
        "nlid": "NL-1",
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
    }
    payload = json.dumps(foreign_claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(SECRET, payload, hashlib.sha256).digest()
    forged_token = f"{_b64url(payload)}.{_b64url(signature)}"
    assert verify_discovery_surface_token(forged_token, "NL-1", secret=SECRET) is None
