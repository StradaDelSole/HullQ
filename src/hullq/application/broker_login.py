"""Auth0-compatible login-redirect construction — SLICE-0053.

Builds the outbound authorization-code request (contract §6) and the
short-lived, browser-held "login state" needed to validate the callback:
OAuth `state` (CSRF binding) and OIDC `nonce` (ID-token replay binding).

The state/nonce cookie is not HMAC-signed: it is `HttpOnly` and host-only
(no `Domain` attribute), so only this server can ever set it for its own
origin -- an off-origin attacker cannot forge its value even without a
signature, and its sole job is exact byte-equality against what comes back
on the callback query string / inside the validated ID token.

The cookie value is base64url-encoded JSON, not raw JSON: RFC 6265 cookie
values exclude double-quote, comma, semicolon, backslash and whitespace, so
a raw JSON payload forces the cookie library into quoted/escaped encoding --
and different HTTP client/server cookie parsers do not all reverse that
quoting identically, which can silently corrupt the payload in transit.
base64url's restricted alphabet has no such ambiguity.
"""

from __future__ import annotations

import base64
import binascii
import json
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from hullq.security.oidc import AuthProviderConfig

__all__ = [
    "DEFAULT_NEXT_PATH",
    "LoginRedirect",
    "LoginState",
    "build_login_redirect",
    "decode_login_state_cookie",
]

DEFAULT_NEXT_PATH = "/broker"

#: Reserved query parameter names the caller may never override -- FastAPI's
#: login endpoint always sets these itself so a client cannot smuggle a
#: different response_type/client_id/redirect_uri/state/nonce/scope into the
#: provider request.
_RESERVED_PARAMS = frozenset(
    {"response_type", "client_id", "redirect_uri", "state", "nonce", "scope"}
)


@dataclass(frozen=True)
class LoginState:
    state: str
    nonce: str
    next_path: str


@dataclass(frozen=True)
class LoginRedirect:
    authorize_url: str
    state_cookie_value: str


def _safe_next_path(candidate: str | None) -> str:
    if candidate is None or not candidate.startswith("/broker"):
        return DEFAULT_NEXT_PATH
    return candidate


def build_login_redirect(
    config: AuthProviderConfig,
    *,
    redirect_uri: str,
    next_path: str | None = None,
    extra_params: dict[str, str] | None = None,
) -> LoginRedirect:
    """Build the Auth0-compatible `/authorize` redirect URL + state cookie value.

    *extra_params* are forwarded verbatim to the provider (e.g. standard
    OIDC `login_hint`/`acr_values`/`prompt`) -- never given HullQ-specific
    meaning here, and never allowed to override a reserved parameter.
    """
    safe_next = _safe_next_path(next_path)
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)

    query = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid",
        "state": state,
        "nonce": nonce,
    }
    for key, value in (extra_params or {}).items():
        if key in _RESERVED_PARAMS:
            continue
        query[key] = value

    authorize_url = f"{config.authorize_endpoint}?{urlencode(query)}"
    payload = json.dumps(
        {"state": state, "nonce": nonce, "next": safe_next}, separators=(",", ":")
    ).encode("utf-8")
    state_cookie_value = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    return LoginRedirect(authorize_url=authorize_url, state_cookie_value=state_cookie_value)


def decode_login_state_cookie(raw: str | None) -> LoginState | None:
    """Parse the login-state cookie value, or None if missing/malformed.

    Malformed/missing state is a caller error, never a security bypass: the
    callback always fails closed when this returns None.
    """
    if not raw:
        return None
    try:
        padded = raw + ("=" * ((-len(raw)) % 4))
        payload = base64.urlsafe_b64decode(padded)
        data = json.loads(payload.decode("utf-8"))
    except binascii.Error, ValueError, UnicodeDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    state = data.get("state")
    nonce = data.get("nonce")
    next_path = data.get("next")
    if not isinstance(state, str) or not state:
        return None
    if not isinstance(nonce, str) or not nonce:
        return None
    return LoginState(state=state, nonce=nonce, next_path=_safe_next_path(next_path))
