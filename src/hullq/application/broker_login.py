"""Auth0-compatible login-redirect construction — SLICE-0053.

Builds the outbound authorization-code request (contract §6) and the
short-lived, browser-held "login state" needed to validate the callback:
OAuth `state` (CSRF binding) and OIDC `nonce` (ID-token replay binding).

The state/nonce cookie payload is HMAC-signed, not merely opaque JSON.
Independent review (2026-09-14, exact-head a7fee1a0) found that a host-only
cookie is not, by itself, sufficient protection: a compromised/hostile
sibling subdomain sharing HullQ's parent domain can still set a
`Set-Cookie: hullq_login_state=...; Domain=<parent-domain>` cookie that this
service would otherwise accept ("cookie tossing"), since the callback only
ever inspected the cookie's *value*, never who was actually allowed to set
it. Signing closes that gap independently of the `__Host-` cookie-name
prefix defense in `hullq.api.app` (which stops the browser from ever
accepting such a tossed cookie in the first place): even if a forged/tossed
value somehow reached this service, it fails signature verification here
and is treated identically to "no state cookie at all" -- defense in depth,
not a replacement for the cookie-prefix defense.

The cookie value is `base64url(json).base64url(hmac_sha256(json, secret))`,
mirroring `hullq.security.session_token`'s shape. base64url is used for the
JSON payload itself too (not only the signature): RFC 6265 cookie values
exclude double-quote, comma, semicolon, backslash and whitespace, so a raw
JSON payload forces the cookie library into quoted/escaped encoding --
and different HTTP client/server cookie parsers do not all reverse that
quoting identically, which can silently corrupt the payload in transit.
base64url's restricted alphabet has no such ambiguity.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
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

#: SLICE-0054 bounded extension (contract §4): the login-state internal-path
#: allowlist accepted `/broker...` only; owner-direct draft login return now
#: also accepts `/sell/direct` and its child paths. Deliberately still a
#: plain `str.startswith` prefix check -- exactly the pre-existing `/broker`
#: discipline, just widened to one more accepted internal prefix -- so every
#: absolute/scheme-relative/external candidate (which never starts with `/`
#: followed by one of these exact literals) is rejected exactly as before.
_ALLOWED_NEXT_PATH_PREFIXES = ("/broker", "/sell/direct")

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
    if candidate is None or not candidate.startswith(_ALLOWED_NEXT_PATH_PREFIXES):
        return DEFAULT_NEXT_PATH
    return candidate


_B64URL_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    """Strictly decode one unpadded base64url segment (mirrors
    `hullq.security.session_token`'s canonical-encoding discipline).

    A base64 group whose bit-length isn't a multiple of 6 has a trailing
    character with "don't-care" bits -- several distinct alphabet-valid
    strings can decode to the identical byte string. Re-encoding the
    decoded bytes and requiring an exact match against *text* rejects any
    such non-canonical alias, so a signature/payload comparison downstream
    can rely on exact byte equality actually implying exact string
    equality (and vice versa) -- no tampered-but-aliasing variant of a
    valid segment is ever silently accepted as equivalent.
    """
    if not text or not _B64URL_SEGMENT_RE.fullmatch(text):
        raise ValueError("segment is not strict, canonical, unpadded base64url")
    padded = text + ("=" * ((-len(text)) % 4))
    decoded = base64.urlsafe_b64decode(padded)
    if _b64url_encode(decoded) != text:
        raise ValueError("segment is not the canonical base64url encoding of its bytes")
    return decoded


def _sign(payload: bytes, secret: bytes) -> bytes:
    return hmac.new(secret, payload, hashlib.sha256).digest()


def build_login_redirect(
    config: AuthProviderConfig,
    *,
    redirect_uri: str,
    secret: bytes,
    next_path: str | None = None,
    extra_params: dict[str, str] | None = None,
) -> LoginRedirect:
    """Build the Auth0-compatible `/authorize` redirect URL + signed state cookie value.

    *extra_params* are forwarded verbatim to the provider (e.g. standard
    OIDC `login_hint`/`acr_values`/`prompt`) -- never given HullQ-specific
    meaning here, and never allowed to override a reserved parameter.

    *secret* HMAC-signs the state cookie payload (see module docstring); the
    caller passes the same secret used to sign/verify HullQ session tokens.
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
    signature = _sign(payload, secret)
    state_cookie_value = f"{_b64url_encode(payload)}.{_b64url_encode(signature)}"
    return LoginRedirect(authorize_url=authorize_url, state_cookie_value=state_cookie_value)


def decode_login_state_cookie(raw: str | None, *, secret: bytes) -> LoginState | None:
    """Verify and parse the signed login-state cookie value.

    Returns `None` for anything malformed, missing or carrying an invalid
    signature -- including a value injected via a cookie set by a different
    (e.g. sibling-subdomain) origin, which cannot know *secret*. Malformed/
    missing/unsigned state is a caller error, never a security bypass: the
    callback always fails closed when this returns None.
    """
    if not raw:
        return None

    parts = raw.split(".")
    if len(parts) != 2:
        return None
    payload_part, signature_part = parts

    try:
        payload = _b64url_decode(payload_part)
        signature = _b64url_decode(signature_part)
    except binascii.Error, ValueError:
        return None

    expected_signature = _sign(payload, secret)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        data = json.loads(payload.decode("utf-8"))
    except ValueError, UnicodeDecodeError:
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
