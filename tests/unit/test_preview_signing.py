"""Unit tests for preview-capability signing-secret loading — SLICE-0048.

Covers strict base64url validation, the >=32-decoded-byte minimum, absent
configuration and the environment-variable entry point -- all fail fast with
no insecure fallback.
"""

from __future__ import annotations

import base64
import os

import pytest

from hullq.security.preview_signing import (
    HULLQ_PREVIEW_SIGNING_SECRET_ENV,
    MIN_PREVIEW_SIGNING_SECRET_BYTES,
    PreviewSigningSecretError,
    get_preview_signing_secret,
    load_preview_signing_secret,
)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def test_valid_secret_decodes_to_exact_bytes() -> None:
    raw = os.urandom(32)
    assert load_preview_signing_secret(_b64url(raw)) == raw


def test_valid_secret_accepts_unpadded_form() -> None:
    raw = os.urandom(32)
    unpadded = _b64url(raw).rstrip("=")
    assert load_preview_signing_secret(unpadded) == raw


def test_longer_than_minimum_secret_accepted() -> None:
    raw = os.urandom(48)
    assert load_preview_signing_secret(_b64url(raw)) == raw


def test_empty_secret_rejected() -> None:
    with pytest.raises(PreviewSigningSecretError):
        load_preview_signing_secret("")


def test_whitespace_only_secret_rejected() -> None:
    with pytest.raises(PreviewSigningSecretError):
        load_preview_signing_secret("   ")


def test_invalid_base64url_characters_rejected() -> None:
    with pytest.raises(PreviewSigningSecretError):
        load_preview_signing_secret("not/valid+base64!!!")


def test_short_decoded_secret_rejected() -> None:
    short = _b64url(os.urandom(MIN_PREVIEW_SIGNING_SECRET_BYTES - 1))
    with pytest.raises(PreviewSigningSecretError):
        load_preview_signing_secret(short)


def test_exactly_minimum_length_accepted() -> None:
    exact = _b64url(os.urandom(MIN_PREVIEW_SIGNING_SECRET_BYTES))
    decoded = load_preview_signing_secret(exact)
    assert len(decoded) == MIN_PREVIEW_SIGNING_SECRET_BYTES


def test_get_preview_signing_secret_missing_env_var_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(HULLQ_PREVIEW_SIGNING_SECRET_ENV, raising=False)
    with pytest.raises(PreviewSigningSecretError):
        get_preview_signing_secret()


def test_get_preview_signing_secret_empty_env_var_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(HULLQ_PREVIEW_SIGNING_SECRET_ENV, "")
    with pytest.raises(PreviewSigningSecretError):
        get_preview_signing_secret()


def test_get_preview_signing_secret_reads_valid_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = os.urandom(32)
    monkeypatch.setenv(HULLQ_PREVIEW_SIGNING_SECRET_ENV, _b64url(raw))
    assert get_preview_signing_secret() == raw


def test_get_preview_signing_secret_custom_env_var_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = os.urandom(32)
    monkeypatch.setenv("CUSTOM_SECRET_ENV", _b64url(raw))
    assert get_preview_signing_secret("CUSTOM_SECRET_ENV") == raw
