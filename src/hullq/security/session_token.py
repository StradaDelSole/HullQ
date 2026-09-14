"""Stateless signed HullQ browser-session token — SLICE-0053.

Deliberately mirrors the accepted `hullq.security.preview_token` (SLICE-0048)
shape and canonical-base64url discipline: a finite, HMAC-SHA-256-signed,
URL-safe bearer value bound into an `HttpOnly` browser cookie.

The session token carries only account identity and authentication-strength
evidence -- `account_id`, `provider`, `issuer`, `subject`, `auth_time`,
`mfa_satisfied` -- and NEVER any Organization/membership/role claim. Contract
§9/§D requires every Organization-authorization decision to be read fresh
from current HullQ membership state on every request; embedding
roles/membership into this token would let a stale session outlive a
revoked membership, which this module makes structurally impossible.

Verification is fail-closed: a tampered signature, wrong secret, malformed
structure, unsupported version or expired token all collapse to the same
`InvalidSessionTokenError`.
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

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.publishing_eligibility import AccountId

__all__ = [
    "DEFAULT_SESSION_TTL_SECONDS",
    "MAX_SESSION_TTL_SECONDS",
    "InvalidSessionTokenError",
    "MintedSessionToken",
    "SessionClaims",
    "mint_session_token",
    "verify_and_decode_session_token",
]

_TOKEN_VERSION = 1

DEFAULT_SESSION_TTL_SECONDS = 12 * 3600
MAX_SESSION_TTL_SECONDS = 24 * 3600


class InvalidSessionTokenError(ValueError):
    """*token* is malformed, tampered, expired, or signed under a different secret.

    Deliberately carries no further structured detail, matching the
    SLICE-0048 preview-token fail-closed philosophy: a session boundary must
    never let error shape distinguish "wrong session" from "right session,
    wrong reason".
    """


@dataclass(frozen=True)
class SessionClaims:
    """The exact claims bound into one verified HullQ session token."""

    account_id: AccountId
    identity: AuthenticatedIdentity
    issued_at: datetime
    expires_at: datetime


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
class MintedSessionToken:
    token: str
    expires_at: datetime


def mint_session_token(
    identity: AuthenticatedIdentity,
    account_id: AccountId,
    *,
    secret: bytes,
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    now: datetime | None = None,
) -> MintedSessionToken:
    """Mint a finite, stateless, signed HullQ session token.

    Performs no database read/write: pure and stateless, exactly like
    `hullq.security.preview_token.mint_preview_token`.
    """
    if not isinstance(identity, AuthenticatedIdentity):
        raise TypeError(f"identity must be an AuthenticatedIdentity, got {type(identity).__name__}")
    if not isinstance(account_id, AccountId):
        raise TypeError(f"account_id must be an AccountId, got {type(account_id).__name__}")
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool):
        raise TypeError(f"ttl_seconds must be an int, got {type(ttl_seconds).__name__}")
    if ttl_seconds <= 0:
        raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}")
    if ttl_seconds > MAX_SESSION_TTL_SECONDS:
        raise ValueError(
            f"ttl_seconds must not exceed MAX_SESSION_TTL_SECONDS ({MAX_SESSION_TTL_SECONDS}), "
            f"got {ttl_seconds}"
        )
    if len(secret) < 32:
        raise ValueError("secret must be at least 32 bytes")

    minted_at = _now(now)
    expires_at = datetime.fromtimestamp(int(minted_at.timestamp()) + ttl_seconds, tz=UTC)

    claims = {
        "v": _TOKEN_VERSION,
        "aid": account_id.value,
        "provider": identity.provider.value,
        "iss": identity.issuer,
        "sub": identity.subject,
        "auth_time": (
            int(identity.auth_time.timestamp()) if identity.auth_time is not None else None
        ),
        "mfa": identity.mfa_satisfied,
        "iat": int(minted_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = _sign(payload, secret)
    token = f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"
    return MintedSessionToken(token=token, expires_at=expires_at)


def verify_and_decode_session_token(
    token: str,
    *,
    secret: bytes,
    now: datetime | None = None,
) -> SessionClaims:
    """Verify *token*'s signature/expiry and return its bound claims.

    Raises `InvalidSessionTokenError` for any malformed, tampered,
    wrong-secret, unsupported-version or expired token.
    """
    if not isinstance(token, str) or not token:
        raise InvalidSessionTokenError("token must be a non-empty string")

    parts = token.split(".")
    if len(parts) != 2:
        raise InvalidSessionTokenError("malformed token structure")
    payload_part, signature_part = parts

    try:
        payload = _b64url_decode(payload_part)
        signature = _b64url_decode(signature_part)
    except (binascii.Error, ValueError) as exc:
        raise InvalidSessionTokenError("malformed token encoding") from exc

    expected_signature = _sign(payload, secret)
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidSessionTokenError("invalid token signature")

    try:
        claims = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidSessionTokenError("malformed token payload") from exc

    if not isinstance(claims, dict):
        raise InvalidSessionTokenError("malformed token claims")

    version = claims.get("v")
    account_id_value = claims.get("aid")
    provider_value = claims.get("provider")
    issuer_value = claims.get("iss")
    subject_value = claims.get("sub")
    auth_time_epoch = claims.get("auth_time")
    mfa_value = claims.get("mfa")
    issued_at_epoch = claims.get("iat")
    expires_at_epoch = claims.get("exp")

    if version != _TOKEN_VERSION:
        raise InvalidSessionTokenError(f"unsupported token version {version!r}")
    if not isinstance(account_id_value, str) or not account_id_value:
        raise InvalidSessionTokenError("malformed token claims: aid")
    if not isinstance(provider_value, str):
        raise InvalidSessionTokenError("malformed token claims: provider")
    try:
        provider = Provider(provider_value)
    except ValueError as exc:
        raise InvalidSessionTokenError("malformed token claims: provider") from exc
    if not isinstance(issuer_value, str) or not issuer_value:
        raise InvalidSessionTokenError("malformed token claims: iss")
    if not isinstance(subject_value, str) or not subject_value:
        raise InvalidSessionTokenError("malformed token claims: sub")
    if auth_time_epoch is not None and (
        not isinstance(auth_time_epoch, int) or isinstance(auth_time_epoch, bool)
    ):
        raise InvalidSessionTokenError("malformed token claims: auth_time")
    if not isinstance(mfa_value, bool):
        raise InvalidSessionTokenError("malformed token claims: mfa")
    if not isinstance(issued_at_epoch, int) or isinstance(issued_at_epoch, bool):
        raise InvalidSessionTokenError("malformed token claims: iat")
    if not isinstance(expires_at_epoch, int) or isinstance(expires_at_epoch, bool):
        raise InvalidSessionTokenError("malformed token claims: exp")

    expires_at = datetime.fromtimestamp(expires_at_epoch, tz=UTC)
    if expires_at <= _now(now):
        raise InvalidSessionTokenError("token expired")

    return SessionClaims(
        account_id=AccountId(account_id_value),
        identity=AuthenticatedIdentity(
            provider=provider,
            issuer=issuer_value,
            subject=subject_value,
            auth_time=(
                datetime.fromtimestamp(auth_time_epoch, tz=UTC)
                if auth_time_epoch is not None
                else None
            ),
            mfa_satisfied=mfa_value,
        ),
        issued_at=datetime.fromtimestamp(issued_at_epoch, tz=UTC),
        expires_at=expires_at,
    )
