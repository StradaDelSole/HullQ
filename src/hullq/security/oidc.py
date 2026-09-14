"""Auth0-compatible OIDC authentication-only boundary — SLICE-0053.

Implements contract §3/§6/§7: a validated Auth0 (or, in tests/CI, a
deterministic local OIDC/JWKS issuer exercising the identical boundary)
authorization-code login produces provider-neutral authentication evidence
(`hullq.domain.broker_access.AuthenticatedIdentity`) only. Nothing here ever
reads or trusts a provider role/Organization/app-metadata/email claim as
HullQ authorization truth.

Every failure path -- malformed header, disallowed algorithm, unknown
signing key, wrong issuer/audience, bad signature, expired token, nonce
mismatch -- collapses to `InvalidAuthenticationError` and fails closed
before any broker data is returned.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import jwt
from jwt.algorithms import RSAAlgorithm

from hullq.domain.broker_access import AuthenticatedIdentity, Provider

__all__ = [
    "AUTH0_MFA_STEP_UP_ACR_VALUE",
    "AUTH_ALLOWED_ALGORITHMS",
    "AuthProviderConfig",
    "AuthProviderConfigError",
    "InvalidAuthenticationError",
    "JwksCache",
    "exchange_authorization_code",
    "get_auth_provider_config",
    "validate_id_token",
]

#: The only signature algorithm this boundary ever accepts. `"none"` and any
#: symmetric (HS*) algorithm are never in this set -- an attacker cannot
#: downgrade verification by choosing a different `alg` header, because the
#: algorithm passed to `jwt.decode` is always exactly this fixed allowlist,
#: never derived from the untrusted token header.
AUTH_ALLOWED_ALGORITHMS = ("RS256",)

#: The standard OIDC/PAPE ACR value ("multi-factor") HullQ requests as
#: `acr_values` on the `/authorize` step-up redirect (contract §10;
#: independent review 2026-09-14, exact-head a7fee1a0). This replaces an
#: earlier test-only `acr_values=mfa` shorthand with Auth0's own documented
#: step-up request value -- see
#: https://auth0.com/docs/secure/multi-factor-authentication/step-up-authentication
#: -- so the production request FastAPI/Astro send is exactly what a real
#: Auth0 tenant expects, not a value invented for this repository.
#:
#: Requesting this ACR value has no effect by itself: Auth0 does not
#: interpret `acr_values` as a built-in MFA trigger. The Auth0 tenant must
#: be configured with a Post-Login Action (Auth0 Actions, "Login / Post
#: Login" flow) that:
#:
#:   1. inspects the incoming authentication request's requested ACR (e.g.
#:      `event.transaction.acr_values` / `event.request.query.acr_values`,
#:      exact API per the deployed Auth0 Actions runtime version);
#:   2. when it contains this exact value, calls
#:      `api.authentication.challengeWithAny(event.user.enrolledFactors)`
#:      (or `enrollWithAny(...)` when the user has no enrolled factor yet)
#:      to force an MFA challenge for that login;
#:   3. lets Auth0 record the satisfied factor in the issued ID token's
#:      standard `amr` claim (e.g. `"mfa"`) once the challenge succeeds.
#:
#: HullQ never reads Auth0 roles/Organizations/app_metadata to decide MFA;
#: it reads only the signed ID token's `amr` claim (`validate_id_token`
#: below) -- exactly the same validated-authentication-strength evidence
#: this module already required before this change. The ACR value only
#: ever selects *which* Auth0-side Action logic runs; it never becomes
#: HullQ authorization truth itself.
AUTH0_MFA_STEP_UP_ACR_VALUE = "http://schemas.openid.net/pape/policies/2007/06/multi-factor"

_ISSUER_ENV = "HULLQ_AUTH_ISSUER"
_AUTHORIZE_URL_ENV = "HULLQ_AUTH_AUTHORIZE_URL"
_TOKEN_URL_ENV = "HULLQ_AUTH_TOKEN_URL"
_JWKS_URL_ENV = "HULLQ_AUTH_JWKS_URL"
_CLIENT_ID_ENV = "HULLQ_AUTH_CLIENT_ID"
_CLIENT_SECRET_ENV = "HULLQ_AUTH_CLIENT_SECRET"

_REQUIRED_ENV_VARS = (
    _ISSUER_ENV,
    _AUTHORIZE_URL_ENV,
    _TOKEN_URL_ENV,
    _JWKS_URL_ENV,
    _CLIENT_ID_ENV,
    _CLIENT_SECRET_ENV,
)


class AuthProviderConfigError(RuntimeError):
    """The Auth0-compatible provider configuration is missing or invalid."""


class InvalidAuthenticationError(ValueError):
    """Authentication evidence is malformed, tampered, expired or inadmissible.

    One exception type, deliberately no finer-grained reason exposed to
    callers: this boundary must fail closed before any broker data is
    returned, and must never let error shape leak which specific validation
    step failed.
    """


@dataclass(frozen=True)
class AuthProviderConfig:
    """Explicit, fail-fast-loaded Auth0-compatible provider configuration.

    In production this points at the accepted Auth0 Public Cloud EU tenant;
    in CI/tests it points at the local deterministic OIDC/JWKS test issuer
    (`hullq.testing.oidc_test_issuer`) exercising the identical boundary.
    """

    provider: Provider
    issuer: str
    authorize_endpoint: str
    token_endpoint: str
    jwks_uri: str
    client_id: str
    client_secret: str


def get_auth_provider_config() -> AuthProviderConfig:
    """Fail-fast environment loader for the Auth0-compatible provider config.

    Raises `AuthProviderConfigError` if any required environment variable is
    unset or empty. There is no hard-coded default provider configuration.
    """
    values: dict[str, str] = {}
    missing: list[str] = []
    for env_var in _REQUIRED_ENV_VARS:
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            missing.append(env_var)
        else:
            values[env_var] = raw
    if missing:
        raise AuthProviderConfigError(
            "missing/empty required authentication provider environment variable(s): "
            f"{sorted(missing)}"
        )
    return AuthProviderConfig(
        provider=Provider.AUTH0,
        issuer=values[_ISSUER_ENV],
        authorize_endpoint=values[_AUTHORIZE_URL_ENV],
        token_endpoint=values[_TOKEN_URL_ENV],
        jwks_uri=values[_JWKS_URL_ENV],
        client_id=values[_CLIENT_ID_ENV],
        client_secret=values[_CLIENT_SECRET_ENV],
    )


class JwksCache:
    """Fetches and caches provider signing keys by `kid`, suitable for rotation.

    An unknown `kid` triggers exactly one refetch (the provider may have
    rotated keys since the last fetch) before failing closed; it never
    trusts a key supplied by anything other than *jwks_uri* itself.
    """

    def __init__(self, jwks_uri: str, *, http_client: Any | None = None) -> None:
        if not jwks_uri:
            raise ValueError("jwks_uri must be non-empty")
        self._jwks_uri = jwks_uri
        self._http_client = http_client
        self._keys: dict[str, Any] = {}

    def _refresh(self) -> None:
        import httpx  # deferred: no module-level network dependency

        owns_client = self._http_client is None
        client = self._http_client if self._http_client is not None else httpx.Client(timeout=10.0)
        try:
            response = client.get(self._jwks_uri)
            response.raise_for_status()
            data = response.json()
        finally:
            if owns_client:
                client.close()

        keys: dict[str, Any] = {}
        for jwk in data.get("keys", []):
            kid = jwk.get("kid")
            if not isinstance(kid, str) or not kid:
                continue
            keys[kid] = RSAAlgorithm.from_jwk(json.dumps(jwk))
        self._keys = keys

    def get_key(self, kid: str) -> Any:
        if kid not in self._keys:
            self._refresh()
        if kid not in self._keys:
            raise InvalidAuthenticationError("unknown signing key id")
        return self._keys[kid]


def exchange_authorization_code(
    *,
    config: AuthProviderConfig,
    code: str,
    redirect_uri: str,
    http_client: Any | None = None,
) -> dict[str, Any]:
    """Exchange an authorization code for tokens at the provider's token endpoint.

    Returns the parsed JSON token-endpoint response (expected to contain at
    least `id_token`). Fails closed with `InvalidAuthenticationError` on any
    non-2xx response or a response missing `id_token`.
    """
    import httpx  # deferred: no module-level network dependency

    owns_client = http_client is None
    client = http_client if http_client is not None else httpx.Client(timeout=10.0)
    try:
        response = client.post(
            config.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
            },
        )
    finally:
        if owns_client:
            client.close()

    if response.status_code != 200:
        raise InvalidAuthenticationError(
            f"token endpoint returned non-200 status {response.status_code}"
        )
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("id_token"), str):
        raise InvalidAuthenticationError("token endpoint response missing id_token")
    return body


def validate_id_token(
    id_token: str,
    *,
    config: AuthProviderConfig,
    expected_nonce: str,
    jwks_cache: JwksCache | None = None,
) -> AuthenticatedIdentity:
    """Validate *id_token* and return provider-neutral authentication evidence.

    Enforces: well-formed structure, algorithm allowlisted to
    `AUTH_ALLOWED_ALGORITHMS` (never `none`, never a symmetric algorithm),
    a signing key resolved only from *config.jwks_uri*, real signature
    verification, exact issuer/audience match, expiry, and OIDC nonce
    equality against *expected_nonce*. Raises `InvalidAuthenticationError`
    for any failure, before returning any claim.
    """
    if not isinstance(id_token, str) or not id_token:
        raise InvalidAuthenticationError("id_token must be a non-empty string")
    if not expected_nonce:
        raise InvalidAuthenticationError("expected_nonce must be non-empty")

    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError as exc:
        raise InvalidAuthenticationError("malformed token header") from exc

    alg = header.get("alg")
    if alg not in AUTH_ALLOWED_ALGORITHMS:
        raise InvalidAuthenticationError(f"disallowed token algorithm {alg!r}")

    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise InvalidAuthenticationError("token header missing kid")

    cache = jwks_cache if jwks_cache is not None else JwksCache(config.jwks_uri)
    signing_key = cache.get_key(kid)

    try:
        claims = jwt.decode(
            id_token,
            key=signing_key,
            algorithms=list(AUTH_ALLOWED_ALGORITHMS),
            audience=config.client_id,
            issuer=config.issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidAuthenticationError(
            "token failed issuer/audience/signature/expiry validation"
        ) from exc

    nonce = claims.get("nonce")
    if not isinstance(nonce, str) or nonce != expected_nonce:
        raise InvalidAuthenticationError("nonce mismatch")

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidAuthenticationError("missing subject claim")

    auth_time_claim = claims.get("auth_time")
    auth_time = (
        datetime.fromtimestamp(auth_time_claim, tz=UTC)
        if isinstance(auth_time_claim, int) and not isinstance(auth_time_claim, bool)
        else None
    )

    amr = claims.get("amr")
    mfa_satisfied = isinstance(amr, list) and "mfa" in amr

    return AuthenticatedIdentity(
        provider=config.provider,
        issuer=config.issuer,
        subject=subject,
        auth_time=auth_time,
        mfa_satisfied=mfa_satisfied,
    )
