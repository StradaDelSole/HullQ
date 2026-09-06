"""Preview-capability signing-secret loading — SLICE-0048.

`HULLQ_PREVIEW_SIGNING_SECRET` MUST be a strict base64url-encoded secret
representing at least 32 bytes of cryptographically random key material.
Invalid base64url, decoded length below 32 bytes, or absent configuration
MUST fail fast. There is no hard-coded/default/development fallback secret:
a caller that cannot supply a valid secret cannot mint or verify preview
tokens at all.
"""

from __future__ import annotations

import base64
import binascii
import os
import re

__all__ = [
    "HULLQ_PREVIEW_SIGNING_SECRET_ENV",
    "MIN_PREVIEW_SIGNING_SECRET_BYTES",
    "PreviewSigningSecretError",
    "get_preview_signing_secret",
    "load_preview_signing_secret",
]

HULLQ_PREVIEW_SIGNING_SECRET_ENV = "HULLQ_PREVIEW_SIGNING_SECRET"
MIN_PREVIEW_SIGNING_SECRET_BYTES = 32

_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


class PreviewSigningSecretError(RuntimeError):
    """The configured preview-signing secret is missing or invalid.

    Raised before any token is minted or verified. There is no insecure
    fallback: every message here must be actionable enough for an operator
    to fix the environment configuration.
    """


def load_preview_signing_secret(raw: str) -> bytes:
    """Strictly decode *raw* as base64url and enforce the minimum key length.

    Rejects any character outside the base64url alphabet (never silently
    ignored), rejects a decoded length below
    `MIN_PREVIEW_SIGNING_SECRET_BYTES`, and never falls back to a
    hard-coded/default secret.
    """
    candidate = raw.strip()
    if not candidate:
        raise PreviewSigningSecretError(
            f"{HULLQ_PREVIEW_SIGNING_SECRET_ENV} is not set or empty; a strict base64url "
            f"secret of at least {MIN_PREVIEW_SIGNING_SECRET_BYTES} decoded bytes is required"
        )
    if not _BASE64URL_RE.fullmatch(candidate):
        raise PreviewSigningSecretError(
            f"{HULLQ_PREVIEW_SIGNING_SECRET_ENV} is not strict base64url "
            "(only 'A'-'Z', 'a'-'z', '0'-'9', '-', '_' and optional trailing '=' padding "
            "are accepted)"
        )
    stripped = candidate.rstrip("=")
    padded = stripped + ("=" * ((-len(stripped)) % 4))
    try:
        decoded = base64.urlsafe_b64decode(padded)
    except (binascii.Error, ValueError) as exc:
        raise PreviewSigningSecretError(
            f"{HULLQ_PREVIEW_SIGNING_SECRET_ENV} could not be decoded as base64url: {exc}"
        ) from exc
    if len(decoded) < MIN_PREVIEW_SIGNING_SECRET_BYTES:
        raise PreviewSigningSecretError(
            f"{HULLQ_PREVIEW_SIGNING_SECRET_ENV} decodes to {len(decoded)} bytes; at least "
            f"{MIN_PREVIEW_SIGNING_SECRET_BYTES} decoded bytes of key material are required"
        )
    return decoded


def get_preview_signing_secret(env_var: str = HULLQ_PREVIEW_SIGNING_SECRET_ENV) -> bytes:
    """Read and strictly validate the preview signing secret from the environment.

    Fails fast (raises `PreviewSigningSecretError`) when *env_var* is unset,
    empty, not strict base64url, or decodes below the minimum key length.
    """
    raw = os.environ.get(env_var, "")
    if not raw.strip():
        raise PreviewSigningSecretError(
            f"{env_var} is not set or empty; a strict base64url secret of at least "
            f"{MIN_PREVIEW_SIGNING_SECRET_BYTES} decoded bytes is required"
        )
    return load_preview_signing_secret(raw)
