"""SLICE-0048/0049 FastAPI application.

The repository's first FastAPI surface. FastAPI remains the sole Python HTTP
backend. This module adds:

- `GET /api/_preview/listings/{preview_token}` (SLICE-0048): an explicitly
  unstable, non-canonical, bearer-capability-gated preview route;
- `GET /api/listings/{native_listing_id}` (SLICE-0049): the first
  production-public NativeListing read route -- no preview token required,
  gated solely on the accepted ACTIVE + complete-chain predicate.

Neither route freezes an `/api/v1/...` contract. Both handlers stay thin:
all read composition lives in `hullq.application.preview_read` /
`hullq.application.public_listing_read`.

The two routes deliberately carry different response-header semantics
(SLICE-0049 §12): the preview route's private/no-store/no-referrer bearer-
capability headers apply only to `/api/_preview/...` and MUST NOT be copied
onto the public route, which is intentionally public-but-noindex rather than
confidential.

No third-party analytics/tracker/subresource is loaded by this API; the
interactive OpenAPI/Swagger docs routes are disabled so this proof surface
never pulls in a third-party CDN asset.

SLICE-0052 adds one internal, server-side-only current-time boundary
(`_FRESHNESS_AS_OF_OVERRIDE_ENV`) used to resolve freshness on both routes.
It is resolved once at app-creation time from an explicit constructor
parameter or the environment -- never from an HTTP request -- so a client
can never supply an arbitrary "as of" instant (contract §8/§4.2 forbid a
caller-supplied confirmation timestamp; this is the equivalent guarantee for
the read-side clock boundary). Production deployments never set the
environment variable, so `datetime.now(timezone.utc)` is read fresh on every
request; the retained SLICE-0052 proof and tests are the only intended
callers of the override.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from hullq.application.broker_callback import CallbackOutcome, complete_login_callback
from hullq.application.broker_login import build_login_redirect
from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_broker_context_read_model,
    get_organization_workspace_result,
)
from hullq.application.preview_read import get_preview_read_model
from hullq.application.public_listing_read import get_public_listing_read_model
from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.connection import get_database_url, open_connection
from hullq.search.draft_max_request import canonical_draft_max_str
from hullq.security.oidc import AuthProviderConfig, get_auth_provider_config
from hullq.security.preview_signing import get_preview_signing_secret
from hullq.security.session_signing import get_session_signing_secret
from hullq.security.session_token import (
    InvalidSessionTokenError,
    SessionClaims,
    verify_and_decode_session_token,
)

__all__ = ["create_app"]

#: SLICE-0053: HullQ-owned browser cookies. Neither is ever readable by
#: ordinary browser JavaScript (`HttpOnly`), both are scoped `Path=/` and
#: never carry a `Domain` attribute (contract §6/§11/§12).
#:
#: Independent review (2026-09-14, exact-head a7fee1a0): a host-only cookie
#: alone is not sufficient defense. A compromised/hostile sibling subdomain
#: sharing HullQ's parent domain (e.g. a subdomain takeover) can still set a
#: `Set-Cookie: hullq_session=...; Domain=<parent-domain>` cookie that this
#: app -- like any other host under that parent -- would receive and, absent
#: further defense, accept ("cookie tossing" / session fixation). Two
#: independent defenses close this:
#:
#: 1. `__Host-`-prefixed cookie names in production (`_cookie_name` below):
#:    per RFC 6265bis, a browser refuses to store a `__Host-`-prefixed
#:    cookie at all unless it is `Secure`, has no `Domain` attribute and has
#:    `Path=/` -- exactly the three properties always set below. A sibling
#:    subdomain cannot set a `Domain=<parent>` cookie under this prefix: the
#:    browser rejects it outright, so it can never reach this app's request
#:    handlers. (Requires a real Secure/HTTPS context; the deterministic
#:    local/CI HTTP proof cannot use it and falls back to the unprefixed
#:    name via `HULLQ_SESSION_COOKIE_SECURE=false` -- see `_cookie_secure`.)
#: 2. the login-state cookie's payload is HMAC-signed
#:    (`hullq.application.broker_login`), not merely opaque: even if a
#:    tossed/forged cookie somehow reached the callback, it would still
#:    fail signature verification and be treated as
#:    `STATE_MISSING_OR_MISMATCH` -- defense in depth independent of the
#:    cookie-prefix protection above.
_SESSION_COOKIE_BASE_NAME = "hullq_session"
_LOGIN_STATE_COOKIE_BASE_NAME = "hullq_login_state"
_HOST_COOKIE_PREFIX = "__Host-"
_LOGIN_STATE_COOKIE_MAX_AGE_SECONDS = 600
_AUTH_REDIRECT_URI_ENV = "HULLQ_AUTH_REDIRECT_URI"
_WEB_BASE_URL_ENV = "HULLQ_WEB_BASE_URL"
_SESSION_COOKIE_SECURE_ENV = "HULLQ_SESSION_COOKIE_SECURE"
_BROKER_PATH_PREFIXES = ("/api/auth/", "/api/broker/")
_BROKER_RESPONSE_HEADERS = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"}

#: SLICE-0052: server-side-only freshness clock override, resolved once at
#: app-creation time. Never read from an HTTP request. Unset in every
#: production deployment.
_FRESHNESS_AS_OF_OVERRIDE_ENV = "HULLQ_FRESHNESS_AS_OF_OVERRIDE_ISO"


def _resolve_as_of_override_from_env() -> datetime | None:
    raw = os.environ.get(_FRESHNESS_AS_OF_OVERRIDE_ENV, "").strip()
    if not raw:
        return None
    value = datetime.fromisoformat(raw)
    if value.tzinfo is None or value.utcoffset() is None:
        raise RuntimeError(
            f"{_FRESHNESS_AS_OF_OVERRIDE_ENV} must be a timezone-aware ISO-8601 "
            f"datetime, got {raw!r}"
        )
    return value


_PREVIEW_PATH_PREFIX = "/api/_preview/"
_PUBLIC_LISTINGS_PATH_PREFIX = "/api/listings/"
_SEARCH_PATH_PREFIX = "/api/search/"

#: SLICE-0051 bounded public Search surface — HullQ's required public
#: languages (docs/PRODUCT_LANGUAGE_AND_I18N_REQUIREMENT.md). Locale affects
#: presentation only; draft_max and its meaning stay language-neutral.
_SUPPORTED_SEARCH_LOCALES = ("en", "de", "fr", "pt", "es")

#: Localized buyer-friendly 400 recovery guidance (slice §C: "a localized
#: buyer-friendly 400 recovery response"). Technical parameter names/values
#: remain language-neutral; only this guidance text is translated.
_INVALID_SEARCH_REQUEST_MESSAGE = {
    "en": "This search link isn't valid. Enter a maximum draft as a plain decimal number of metres, for example 1.6.",
    "de": "Dieser Suchlink ist ungültig. Geben Sie den maximalen Tiefgang als einfache Dezimalzahl in Metern an, zum Beispiel 1.6.",
    "fr": "Ce lien de recherche n'est pas valide. Indiquez le tirant d'eau maximal sous forme de nombre décimal simple en mètres, par exemple 1.6.",
    "pt": "Esta ligação de pesquisa não é válida. Indique o calado máximo como um número decimal simples em metros, por exemplo 1.6.",
    "es": "Este enlace de búsqueda no es válido. Indique el calado máximo como un número decimal simple en metros, por ejemplo 1.6.",
}

# Sent on every response from the preview surface only: a preview token is a
# bearer capability carried in the URL path, never a publicly indexable or
# cacheable resource (SLICE-0048 §5.2).
_PREVIEW_RESPONSE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
}

# Sent on every response from the public listing surface only (SLICE-0049
# §9.1/§12): public availability is not equivalent to organic indexation,
# but the public route is otherwise ordinary -- no private/no-store/
# no-referrer bearer-capability confidentiality is copied onto it.
_PUBLIC_LISTING_RESPONSE_HEADERS = {
    "X-Robots-Tag": "noindex",
}


def create_app(
    *,
    database_url: str | None = None,
    preview_signing_secret: bytes | None = None,
    freshness_as_of_override: datetime | None = None,
    auth_provider_config: AuthProviderConfig | None = None,
    session_signing_secret: bytes | None = None,
    auth_redirect_uri: str | None = None,
    web_base_url: str | None = None,
    auth_http_client: Any | None = None,
    auth_jwks_cache: Any | None = None,
) -> FastAPI:
    """Build the SLICE-0048 preview FastAPI application.

    *database_url* / *preview_signing_secret* may be injected explicitly
    (used by tests against a disposable schema); otherwise both are resolved
    from the environment at app-creation time via the accepted fail-fast
    loaders (`hullq.persistence.connection.get_database_url`,
    `hullq.security.preview_signing.get_preview_signing_secret`) -- an
    invalid/missing signing secret must fail app creation, never fall back
    to an insecure default.

    *freshness_as_of_override* fixes the freshness evaluation clock for
    every request this app instance serves (used by tests and the retained
    SLICE-0052 proof); otherwise it falls back to
    `_FRESHNESS_AS_OF_OVERRIDE_ENV`, and when neither is set every request
    resolves freshness against the real `datetime.now(timezone.utc)` read at
    request time. Never derived from an HTTP request.

    SLICE-0053's auth/broker configuration (*auth_provider_config*,
    *session_signing_secret*, *auth_redirect_uri*) is deliberately resolved
    lazily, per-request, inside the `/api/auth/*` and `/api/broker/*`
    handlers only -- never eagerly here at app-creation time -- so that
    every pre-existing non-broker route/test continues to work unchanged in
    an environment that has not configured an authentication provider at
    all. *auth_http_client*/*auth_jwks_cache* let tests/the retained proof
    inject a deterministic transport instead of real outbound network I/O.
    """
    resolved_database_url = database_url if database_url is not None else get_database_url()
    resolved_secret = (
        preview_signing_secret
        if preview_signing_secret is not None
        else get_preview_signing_secret()
    )
    resolved_as_of_override = (
        freshness_as_of_override
        if freshness_as_of_override is not None
        else _resolve_as_of_override_from_env()
    )

    def _current_as_of() -> datetime:
        return resolved_as_of_override if resolved_as_of_override is not None else datetime.now(UTC)

    def _resolve_auth_config() -> AuthProviderConfig:
        return (
            auth_provider_config if auth_provider_config is not None else get_auth_provider_config()
        )

    def _resolve_session_secret() -> bytes:
        return (
            session_signing_secret
            if session_signing_secret is not None
            else get_session_signing_secret()
        )

    def _resolve_redirect_uri() -> str:
        if auth_redirect_uri is not None:
            return auth_redirect_uri
        raw = os.environ.get(_AUTH_REDIRECT_URI_ENV, "").strip()
        if not raw:
            raise RuntimeError(f"{_AUTH_REDIRECT_URI_ENV} is not set or empty")
        return raw

    def _resolve_web_base_url() -> str | None:
        if web_base_url is not None:
            return web_base_url
        raw = os.environ.get(_WEB_BASE_URL_ENV, "").strip()
        return raw or None

    def _cookie_secure() -> bool:
        raw = os.environ.get(_SESSION_COOKIE_SECURE_ENV, "true").strip().lower()
        return raw not in {"false", "0", "no"}

    def _cookie_name(base_name: str) -> str:
        return f"{_HOST_COOKIE_PREFIX}{base_name}" if _cookie_secure() else base_name

    def _session_cookie_name() -> str:
        return _cookie_name(_SESSION_COOKIE_BASE_NAME)

    def _login_state_cookie_name() -> str:
        return _cookie_name(_LOGIN_STATE_COOKIE_BASE_NAME)

    def _require_session(request: Request) -> SessionClaims | None:
        raw = request.cookies.get(_session_cookie_name())
        if not raw:
            return None
        try:
            return verify_and_decode_session_token(raw, secret=_resolve_session_secret())
        except InvalidSessionTokenError:
            return None

    app = FastAPI(
        title="HullQ preview API (SLICE-0048, unstable, non-canonical)",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def _scoped_response_headers(request: Request, call_next: Any) -> Any:
        # Scoped by exact path prefix so neither route's header semantics
        # ever leaks onto the other (SLICE-0049 §12): the preview route's
        # bearer-capability confidentiality headers must never appear on the
        # public route, and vice versa.
        response = await call_next(request)
        path = request.url.path
        if path.startswith(_PREVIEW_PATH_PREFIX):
            for key, value in _PREVIEW_RESPONSE_HEADERS.items():
                response.headers[key] = value
        elif path.startswith(_PUBLIC_LISTINGS_PATH_PREFIX):
            for key, value in _PUBLIC_LISTING_RESPONSE_HEADERS.items():
                response.headers[key] = value
        elif path.startswith(_SEARCH_PATH_PREFIX):
            # SLICE-0051 item L: every Search surface is noindex, including
            # a canonical 200 result page.
            response.headers["X-Robots-Tag"] = "noindex"
        elif path.startswith(_BROKER_PATH_PREFIXES):
            # SLICE-0053: auth/session/membership responses are never
            # cached and never indexed.
            for key, value in _BROKER_RESPONSE_HEADERS.items():
                response.headers[key] = value
        return response

    @app.get("/api/_preview/listings/{preview_token}")
    def get_listing_preview(preview_token: str) -> JSONResponse:
        conn = open_connection(resolved_database_url)
        try:
            model = get_preview_read_model(conn, preview_token, secret=resolved_secret)
        finally:
            conn.close()
        if model is None:
            # Invalid/tampered/expired token, missing listing and an
            # incomplete durable chain all collapse to this identical
            # ordinary not-found response (SLICE-0048 §6.2): this route must
            # never be usable as a NativeListingId existence oracle.
            raise HTTPException(status_code=404, detail="listing preview not found")
        return JSONResponse(model.to_public_dict())

    @app.get("/api/listings/{native_listing_id}")
    def get_public_listing(native_listing_id: str) -> JSONResponse:
        conn = open_connection(resolved_database_url)
        try:
            model = get_public_listing_read_model(
                conn, NativeListingId(native_listing_id), as_of=_current_as_of()
            )
        finally:
            conn.close()
        if model is None:
            # DRAFT, WITHDRAWN, missing and incomplete all collapse to this
            # identical ordinary not-found response (SLICE-0049 §8/§9): this
            # route must never be usable as a NativeListingId existence
            # oracle, and no preview token is required or accepted here.
            raise HTTPException(status_code=404, detail="listing not found")
        return JSONResponse(model.to_public_dict())

    @app.get("/api/search/{locale}")
    def get_search(locale: str, request: Request) -> Response:
        # SLICE-0051 item C: bare-locale-routing 404 for an unsupported
        # locale, independent of any query-parameter validity.
        if locale not in _SUPPORTED_SEARCH_LOCALES:
            raise HTTPException(status_code=404, detail="unsupported search locale")

        raw_query_params: dict[str, list[str]] = {
            key: request.query_params.getlist(key) for key in dict(request.query_params)
        }

        conn = open_connection(resolved_database_url)
        try:
            outcome = evaluate_search_request(
                conn, locale=locale, query_params=raw_query_params, as_of=_current_as_of()
            )
        finally:
            conn.close()

        if outcome.kind is SearchOutcomeKind.INVALID:
            message = _INVALID_SEARCH_REQUEST_MESSAGE[locale]
            return JSONResponse(
                {"error": "invalid_search_request", "message": message}, status_code=400
            )

        if outcome.kind is SearchOutcomeKind.REDIRECT:
            assert outcome.canonical_path is not None
            return RedirectResponse(url=outcome.canonical_path, status_code=308)

        if outcome.kind is SearchOutcomeKind.BASE:
            return JSONResponse({"locale": locale, "active_requirement": None})

        assert outcome.kind is SearchOutcomeKind.RESULT
        assert outcome.draft_max is not None
        assert outcome.search_outcome is not None
        search_outcome = outcome.search_outcome
        return JSONResponse(
            {
                "locale": locale,
                "active_requirement": {"draft_max": canonical_draft_max_str(outcome.draft_max)},
                "confirmed_matches": [
                    {
                        "native_listing_id": match.native_listing_id.value,
                        "resolved_draft_m": str(match.resolved_draft_m),
                        "publishing_organization_id": match.publishing_organization_id.value,
                        "freshness_status": match.freshness_status.value,
                        "last_confirmed_at": (
                            match.last_confirmed_at.isoformat()
                            if match.last_confirmed_at is not None
                            else None
                        ),
                    }
                    for match in search_outcome.confirmed_matches
                ],
                "confirmed_match_count": search_outcome.confirmed_match_count,
                "insufficient_data_count": search_outcome.insufficient_data_count,
            }
        )

    @app.get("/api/auth/login")
    def broker_login(request: Request) -> Response:
        auth_config = _resolve_auth_config()
        redirect_uri = _resolve_redirect_uri()
        session_secret = _resolve_session_secret()
        next_path = request.query_params.get("next")
        extra_params = {key: value for key, value in request.query_params.items() if key != "next"}
        login_redirect = build_login_redirect(
            auth_config,
            redirect_uri=redirect_uri,
            next_path=next_path,
            extra_params=extra_params,
            secret=session_secret,
        )
        response = RedirectResponse(url=login_redirect.authorize_url, status_code=302)
        response.set_cookie(
            _login_state_cookie_name(),
            login_redirect.state_cookie_value,
            max_age=_LOGIN_STATE_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax",
            secure=_cookie_secure(),
            path="/",
        )
        return response

    @app.get("/api/auth/callback")
    def broker_callback(request: Request) -> Response:
        auth_config = _resolve_auth_config()
        redirect_uri = _resolve_redirect_uri()
        session_secret = _resolve_session_secret()
        code = request.query_params.get("code")
        query_state = request.query_params.get("state")
        state_cookie_value = request.cookies.get(_login_state_cookie_name())

        conn = open_connection(resolved_database_url)
        try:
            result = complete_login_callback(
                conn,
                config=auth_config,
                code=code,
                query_state=query_state,
                state_cookie_value=state_cookie_value,
                redirect_uri=redirect_uri,
                session_signing_secret=session_secret,
                http_client=auth_http_client,
                jwks_cache=auth_jwks_cache,
            )
        finally:
            conn.close()

        if result.outcome is not CallbackOutcome.SUCCEEDED:
            failure_response = JSONResponse({"error": "authentication_failed"}, status_code=400)
            failure_response.delete_cookie(
                _login_state_cookie_name(), path="/", secure=_cookie_secure(), samesite="lax"
            )
            return failure_response

        assert result.session_token is not None
        assert result.next_path is not None
        resolved_web_base_url = _resolve_web_base_url()
        target = (
            f"{resolved_web_base_url}{result.next_path}"
            if resolved_web_base_url is not None
            else result.next_path
        )
        response = RedirectResponse(url=target, status_code=302)
        response.delete_cookie(
            _login_state_cookie_name(), path="/", secure=_cookie_secure(), samesite="lax"
        )
        response.set_cookie(
            _session_cookie_name(),
            result.session_token.token,
            max_age=max(
                1, int((result.session_token.expires_at - datetime.now(UTC)).total_seconds())
            ),
            httponly=True,
            samesite="lax",
            secure=_cookie_secure(),
            path="/",
        )
        return response

    @app.post("/api/auth/logout")
    def broker_logout() -> JSONResponse:
        response = JSONResponse({"status": "logged_out"})
        response.delete_cookie(
            _session_cookie_name(), path="/", secure=_cookie_secure(), samesite="lax"
        )
        return response

    @app.get("/api/broker/context")
    def broker_context(request: Request) -> JSONResponse:
        session = _require_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="authentication required")
        conn = open_connection(resolved_database_url)
        try:
            model = get_broker_context_read_model(conn, session)
        finally:
            conn.close()
        return JSONResponse(model.to_public_dict())

    @app.get("/api/broker/organizations/{organization_id}")
    def broker_organization_context(organization_id: str, request: Request) -> JSONResponse:
        session = _require_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="authentication required")
        conn = open_connection(resolved_database_url)
        try:
            result = get_organization_workspace_result(
                conn, session, MarketplaceOrganizationId(organization_id)
            )
        finally:
            conn.close()
        if result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
            # Contract §9/§E: unknown Organization and unauthorized
            # Organization membership must be indistinguishable.
            raise HTTPException(status_code=404, detail="organization not found")
        if result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
            return JSONResponse({"error": "mfa_required"}, status_code=403)
        assert result.context is not None
        return JSONResponse(result.context.to_public_dict())

    return app
