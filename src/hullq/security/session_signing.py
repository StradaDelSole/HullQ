"""HullQ browser-session signing-secret loading — SLICE-0053.

Mirrors `hullq.security.preview_signing` (SLICE-0048)'s accepted fail-fast
base64url secret-loading boundary, kept as its own module rather than a
shared refactor so this new session-cookie signing boundary cannot
accidentally regress the already-accepted preview-token boundary.

`HULLQ_SESSION_SIGNING_SECRET` MUST be a strict base64url-encoded secret
representing at least 32 bytes of cryptographically random key material.
Invalid base64url, decoded length below 32 bytes, or absent configuration
MUST fail fast. There is no hard-coded/default/development fallback secret.
"""

from __future__ import annotations

import base64
import binascii
import os
import re

__all__ = [
    "HULLQ_SESSION_SIGNING_SECRET_ENV",
    "MIN_SESSION_SIGNING_SECRET_BYTES",
    "SessionSigningSecretError",
    "get_session_signing_secret",
    "load_session_signing_secret",
]

HULLQ_SESSION_SIGNING_SECRET_ENV = "HULLQ_SESSION_SIGNING_SECRET"
MIN_SESSION_SIGNING_SECRET_BYTES = 32

_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


class SessionSigningSecretError(RuntimeError):
    """The configured session-signing secret is missing or invalid.

    Raised before any session cookie is minted or verified. There is no
    insecure fallback.
    """


def load_session_signing_secret(raw: str) -> bytes:
    """Strictly decode *raw* as base64url and enforce the minimum key length."""
    candidate = raw.strip()
    if not candidate:
        raise SessionSigningSecretError(
            f"{HULLQ_SESSION_SIGNING_SECRET_ENV} is not set or empty; a strict base64url "
            f"secret of at least {MIN_SESSION_SIGNING_SECRET_BYTES} decoded bytes is required"
        )
    if not _BASE64URL_RE.fullmatch(candidate):
        raise SessionSigningSecretError(
            f"{HULLQ_SESSION_SIGNING_SECRET_ENV} is not strict base64url "
            "(only 'A'-'Z', 'a'-'z', '0'-'9', '-', '_' and optional trailing '=' padding "
            "are accepted)"
        )
    stripped = candidate.rstrip("=")
    padded = stripped + ("=" * ((-len(stripped)) % 4))
    try:
        decoded = base64.urlsafe_b64decode(padded)
    except (binascii.Error, ValueError) as exc:
        raise SessionSigningSecretError(
            f"{HULLQ_SESSION_SIGNING_SECRET_ENV} could not be decoded as base64url: {exc}"
        ) from exc
    if len(decoded) < MIN_SESSION_SIGNING_SECRET_BYTES:
        raise SessionSigningSecretError(
            f"{HULLQ_SESSION_SIGNING_SECRET_ENV} decodes to {len(decoded)} bytes; at least "
            f"{MIN_SESSION_SIGNING_SECRET_BYTES} decoded bytes of key material are required"
        )
    return decoded


def get_session_signing_secret(env_var: str = HULLQ_SESSION_SIGNING_SECRET_ENV) -> bytes:
    """Read and strictly validate the session signing secret from the environment."""
    raw = os.environ.get(env_var, "")
    if not raw.strip():
        raise SessionSigningSecretError(
            f"{env_var} is not set or empty; a strict base64url secret of at least "
            f"{MIN_SESSION_SIGNING_SECRET_BYTES} decoded bytes is required"
        )
    return load_session_signing_secret(raw)
