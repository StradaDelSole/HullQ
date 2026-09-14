"""Unit tests for hullq.application.broker_login — SLICE-0053.

Covers the HMAC-signed login-state cookie added by independent review
(2026-09-14, exact-head a7fee1a0): a host-only cookie alone is not
sufficient defense against a hostile sibling subdomain injecting a
same-named `Domain=<parent>` cookie ("cookie tossing"), so the payload
itself must be integrity-protected. This is the defense-in-depth layer
behind (not a replacement for) the `__Host-` cookie-name prefix defense in
`hullq.api.app`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

import pytest

from hullq.application.broker_login import (
    DEFAULT_NEXT_PATH,
    build_login_redirect,
    decode_login_state_cookie,
)
from hullq.domain.broker_access import Provider
from hullq.security.oidc import AuthProviderConfig

SECRET = b"0" * 32
OTHER_SECRET = b"1" * 32


def _correctly_signed_cookie(data: Any, *, secret: bytes = SECRET) -> str:
    """Build a *correctly signed* cookie value for arbitrary `data`,
    bypassing `build_login_redirect`'s own state/nonce generation --
    isolates `decode_login_state_cookie`'s post-signature-verification
    field validation from its signature check."""
    payload = json.dumps(data).encode("utf-8")
    signature = hmac.new(secret, payload, hashlib.sha256).digest()
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{encoded_payload}.{encoded_signature}"


def _config() -> AuthProviderConfig:
    return AuthProviderConfig(
        provider=Provider.AUTH0,
        issuer="https://hullq-dev.eu.auth0.com/",
        authorize_endpoint="https://hullq-dev.eu.auth0.com/authorize",
        token_endpoint="https://hullq-dev.eu.auth0.com/oauth/token",
        jwks_uri="https://hullq-dev.eu.auth0.com/.well-known/jwks.json",
        client_id="hullq-client",
        client_secret="hullq-client-secret",
    )


class TestBuildLoginRedirect:
    def test_authorize_url_carries_required_params(self) -> None:
        redirect = build_login_redirect(
            _config(), redirect_uri="https://hullq.example/api/auth/callback", secret=SECRET
        )
        url = redirect.authorize_url
        assert url.startswith(_config().authorize_endpoint)
        assert "response_type=code" in url
        assert "client_id=hullq-client" in url
        assert "scope=openid" in url
        assert "state=" in url
        assert "nonce=" in url

    def test_extra_params_forwarded_verbatim(self) -> None:
        redirect = build_login_redirect(
            _config(),
            redirect_uri="https://hullq.example/api/auth/callback",
            secret=SECRET,
            extra_params={"login_hint": "alice@example.test", "acr_values": "step-up"},
        )
        assert "login_hint=alice%40example.test" in redirect.authorize_url
        assert "acr_values=step-up" in redirect.authorize_url

    def test_reserved_params_cannot_be_overridden(self) -> None:
        redirect = build_login_redirect(
            _config(),
            redirect_uri="https://hullq.example/api/auth/callback",
            secret=SECRET,
            extra_params={"client_id": "attacker-client", "state": "attacker-state"},
        )
        assert "client_id=attacker-client" not in redirect.authorize_url
        assert "state=attacker-state" not in redirect.authorize_url
        assert "client_id=hullq-client" in redirect.authorize_url

    def test_state_cookie_value_is_not_raw_json(self) -> None:
        redirect = build_login_redirect(
            _config(), redirect_uri="https://hullq.example/api/auth/callback", secret=SECRET
        )
        assert not redirect.state_cookie_value.startswith("{")
        assert redirect.state_cookie_value.count(".") == 1


class TestDecodeLoginStateCookie:
    def test_roundtrip_recovers_state_nonce_next(self) -> None:
        redirect = build_login_redirect(
            _config(),
            redirect_uri="https://hullq.example/api/auth/callback",
            secret=SECRET,
            next_path="/broker/organizations/ORG-1",
        )
        decoded = decode_login_state_cookie(redirect.state_cookie_value, secret=SECRET)
        assert decoded is not None
        assert decoded.next_path == "/broker/organizations/ORG-1"
        assert decoded.state
        assert decoded.nonce

    def test_unsafe_next_path_falls_back_to_default(self) -> None:
        redirect = build_login_redirect(
            _config(),
            redirect_uri="https://hullq.example/api/auth/callback",
            secret=SECRET,
            next_path="https://attacker.example/phish",
        )
        decoded = decode_login_state_cookie(redirect.state_cookie_value, secret=SECRET)
        assert decoded is not None
        assert decoded.next_path == DEFAULT_NEXT_PATH

    def test_none_cookie_rejected(self) -> None:
        assert decode_login_state_cookie(None, secret=SECRET) is None

    def test_empty_cookie_rejected(self) -> None:
        assert decode_login_state_cookie("", secret=SECRET) is None

    @pytest.mark.parametrize(
        "bad", ["not-a-signed-value", "a.b.c", "onlyonepart", "..", "a.", ".b"]
    )
    def test_malformed_structure_rejected(self, bad: str) -> None:
        assert decode_login_state_cookie(bad, secret=SECRET) is None

    def test_wrong_secret_rejected(self) -> None:
        redirect = build_login_redirect(
            _config(), redirect_uri="https://hullq.example/api/auth/callback", secret=SECRET
        )
        assert decode_login_state_cookie(redirect.state_cookie_value, secret=OTHER_SECRET) is None

    def test_tampered_signature_rejected(self) -> None:
        redirect = build_login_redirect(
            _config(), redirect_uri="https://hullq.example/api/auth/callback", secret=SECRET
        )
        payload_part, signature_part = redirect.state_cookie_value.split(".")
        tampered_signature = signature_part[:-1] + ("A" if signature_part[-1] != "A" else "B")
        tampered = f"{payload_part}.{tampered_signature}"
        assert decode_login_state_cookie(tampered, secret=SECRET) is None

    def test_tampered_payload_rejected(self) -> None:
        """Changing the payload without re-signing (e.g. an attacker
        editing `state` to match a real callback) must fail: this is the
        exact sibling-subdomain cookie-tossing/session-fixation scenario
        the signature exists to close."""
        redirect = build_login_redirect(
            _config(), redirect_uri="https://hullq.example/api/auth/callback", secret=SECRET
        )
        _, signature_part = redirect.state_cookie_value.split(".")
        forged_payload = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"state": "attacker-chosen-state", "nonce": "n", "next": "/broker"}
                ).encode("utf-8")
            )
            .rstrip(b"=")
            .decode("ascii")
        )
        forged = f"{forged_payload}.{signature_part}"
        assert decode_login_state_cookie(forged, secret=SECRET) is None

    def test_forged_cookie_with_no_real_signature_rejected(self) -> None:
        """A cookie an attacker fabricates entirely (as if injected via a
        hostile sibling subdomain's `Domain=<parent>` cookie) with no
        access to *secret* at all must be rejected outright."""
        forged_payload = (
            base64.urlsafe_b64encode(
                json.dumps({"state": "s", "nonce": "n", "next": "/broker"}).encode("utf-8")
            )
            .rstrip(b"=")
            .decode("ascii")
        )
        forged_signature = base64.urlsafe_b64encode(b"attacker-guess").rstrip(b"=").decode("ascii")
        forged = f"{forged_payload}.{forged_signature}"
        assert decode_login_state_cookie(forged, secret=SECRET) is None

    def test_missing_state_field_rejected(self) -> None:
        cookie = _correctly_signed_cookie({"nonce": "n", "next": "/broker"})
        assert decode_login_state_cookie(cookie, secret=SECRET) is None

    def test_non_dict_payload_rejected(self) -> None:
        cookie = _correctly_signed_cookie([1, 2, 3])
        assert decode_login_state_cookie(cookie, secret=SECRET) is None
