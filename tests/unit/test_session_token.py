"""Unit tests for hullq.security.session_token — SLICE-0053.

Mirrors the SLICE-0048 preview-token test discipline: roundtrip, tamper,
expiry, wrong-secret and malformed-structure all fail closed to the same
`InvalidSessionTokenError`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.publishing_eligibility import AccountId
from hullq.security.session_token import (
    InvalidSessionTokenError,
    mint_session_token,
    verify_and_decode_session_token,
)

SECRET = b"0" * 32
OTHER_SECRET = b"1" * 32


def _identity(*, mfa: bool = False) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://hullq-dev.eu.auth0.com/",
        subject="auth0|abc123",
        auth_time=datetime(2026, 9, 14, 12, 0, 0, tzinfo=UTC),
        mfa_satisfied=mfa,
    )


def test_roundtrip_preserves_claims() -> None:
    identity = _identity(mfa=True)
    account_id = AccountId("ACC-1")
    minted = mint_session_token(identity, account_id, secret=SECRET)
    claims = verify_and_decode_session_token(minted.token, secret=SECRET)
    assert claims.account_id == account_id
    assert claims.identity == identity
    assert claims.expires_at == minted.expires_at


def test_roundtrip_with_null_auth_time() -> None:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0, issuer="iss", subject="sub", auth_time=None, mfa_satisfied=False
    )
    minted = mint_session_token(identity, AccountId("ACC-1"), secret=SECRET)
    claims = verify_and_decode_session_token(minted.token, secret=SECRET)
    assert claims.identity.auth_time is None


def test_tampered_signature_rejected() -> None:
    minted = mint_session_token(_identity(), AccountId("ACC-1"), secret=SECRET)
    payload_part, signature_part = minted.token.split(".")
    tampered = f"{payload_part}.{signature_part[:-1]}{'A' if signature_part[-1] != 'A' else 'B'}"
    with pytest.raises(InvalidSessionTokenError):
        verify_and_decode_session_token(tampered, secret=SECRET)


def test_wrong_secret_rejected() -> None:
    minted = mint_session_token(_identity(), AccountId("ACC-1"), secret=SECRET)
    with pytest.raises(InvalidSessionTokenError):
        verify_and_decode_session_token(minted.token, secret=OTHER_SECRET)


def test_expired_token_rejected() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    minted = mint_session_token(
        _identity(), AccountId("ACC-1"), secret=SECRET, ttl_seconds=60, now=now
    )
    with pytest.raises(InvalidSessionTokenError):
        verify_and_decode_session_token(minted.token, secret=SECRET, now=now + timedelta(hours=1))


@pytest.mark.parametrize("bad", ["", "not-a-token", "a.b.c", "a", ".", "..", "a.!!!"])
def test_malformed_structure_rejected(bad: str) -> None:
    with pytest.raises(InvalidSessionTokenError):
        verify_and_decode_session_token(bad, secret=SECRET)


def test_secret_too_short_rejected() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        mint_session_token(_identity(), AccountId("ACC-1"), secret=b"short")


def test_ttl_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        mint_session_token(_identity(), AccountId("ACC-1"), secret=SECRET, ttl_seconds=0)


def test_ttl_capped() -> None:
    with pytest.raises(ValueError, match="MAX_SESSION_TTL_SECONDS"):
        mint_session_token(_identity(), AccountId("ACC-1"), secret=SECRET, ttl_seconds=999_999)


def test_never_carries_roles_or_membership_fields() -> None:
    """Structural guard for contract §D: the session must never carry
    Organization/membership/role state -- only identity + MFA evidence."""
    minted = mint_session_token(_identity(mfa=True), AccountId("ACC-1"), secret=SECRET)
    import base64
    import json

    payload_part = minted.token.split(".")[0]
    padded = payload_part + ("=" * ((-len(payload_part)) % 4))
    claims = json.loads(base64.urlsafe_b64decode(padded))
    assert set(claims.keys()) == {
        "v",
        "aid",
        "provider",
        "iss",
        "sub",
        "auth_time",
        "mfa",
        "iat",
        "exp",
    }
