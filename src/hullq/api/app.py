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

SLICE-0053 current session-topology invariant (independent review
2026-09-14, exact-head 9777496): the HullQ session cookie is host-only (see
`require_same_host_session_topology` below). The browser-visible FastAPI
auth/callback endpoint (`HULLQ_AUTH_REDIRECT_URI`'s host) and the Astro
Broker Workspace surface the browser is sent back to after login
(`HULLQ_WEB_BASE_URL`'s host, when configured) MUST therefore share the
exact same hostname -- ports may differ, and a same-host reverse-proxy
layout in front of both is fine, but e.g. `api.hullq.com` for auth/callback
against `hullq.com` for `/broker` is not: it would produce a successful
Auth0 callback immediately followed by an unauthenticated `/broker`, since
the browser would never send the host-only session cookie set for
`api.hullq.com` to a request against `hullq.com`. `/api/auth/login` and
`/api/auth/callback` both fail closed (raise `SessionTopologyError`) rather
than silently completing that broken loop. This is the current session
architecture's invariant, not a general redesign; a later slice that needs
genuinely different auth/workspace hostnames must own that redesign
explicitly (e.g. a server-side session store keyed by an opaque id instead
of a host-only cookie carrying the claims directly).
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from hullq.application.broker_callback import CallbackOutcome, complete_login_callback
from hullq.application.broker_login import build_login_redirect
from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_broker_context_read_model,
    get_organization_workspace_result,
)
from hullq.application.inventory_search import DraftMaxSearchOutcome
from hullq.application.native_inventory_query import NativeInventorySearchOutcome
from hullq.application.owner_direct_draft import (
    CreateOwnerDirectDraftOutcome,
    GetOwnerDirectDraftOutcome,
    UpdateOwnerDirectDraftOutcome,
    create_owner_direct_draft_for_account,
    get_owner_direct_draft_for_account,
    list_owner_direct_drafts_for_account,
    record_to_public_dict,
    update_owner_direct_draft_for_account,
)
from hullq.application.preview_read import get_preview_read_model
from hullq.application.public_listing_read import get_public_listing_read_model
from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.connection import get_database_url, open_connection
from hullq.search.configuration_engine import DesignQueryEvaluation
from hullq.search.criteria import NumericLeafCriterion
from hullq.search.draft_max_request import canonical_draft_max_str
from hullq.search.query_mixed import MixedLeafCriterion
from hullq.security.oidc import AuthProviderConfig, get_auth_provider_config
from hullq.security.preview_signing import get_preview_signing_secret
from hullq.security.session_signing import get_session_signing_secret
from hullq.security.session_token import (
    InvalidSessionTokenError,
    SessionClaims,
    verify_and_decode_session_token,
)

__all__ = ["SessionTopologyError", "create_app", "require_same_host_session_topology"]


class SessionTopologyError(RuntimeError):
    """The configured auth/callback host and Broker Workspace host differ.

    See the module docstring's "SLICE-0053 current session-topology
    invariant" for why this is a hard requirement of the current
    host-only-cookie session design, not an arbitrary restriction.
    """


def require_same_host_session_topology(*, redirect_uri: str, web_base_url: str | None) -> None:
    """Fail closed if *redirect_uri* and *web_base_url* have different hosts.

    A `None` *web_base_url* means the post-login redirect target is a
    relative path, which the browser always resolves against the
    auth/callback's own origin -- inherently same-host, so there is nothing
    to check. Raises `SessionTopologyError` (never returns a bool) so a
    misconfiguration cannot be silently ignored by a caller that forgets to
    check a return value.
    """
    if web_base_url is None:
        return
    redirect_host = urlsplit(redirect_uri).hostname
    web_host = urlsplit(web_base_url).hostname
    if redirect_host != web_host:
        raise SessionTopologyError(
            f"HULLQ_WEB_BASE_URL host {web_host!r} does not match the "
            f"auth/callback host {redirect_host!r} (from HULLQ_AUTH_REDIRECT_URI "
            f"{redirect_uri!r}). SLICE-0053's host-only session cookie cannot cross "
            "hostnames: the Astro Broker Workspace and the FastAPI auth/callback "
            "endpoint must share the exact same hostname (ports may differ; a "
            "same-host reverse-proxy layout in front of both is fine)."
        )


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

#: SLICE-0054: owner-direct draft workspace is private workspace data, never
#: cached/indexed (contract §11) -- same private/no-store/noindex shape as
#: the broker surface, kept as its own constant so the two response-header
#: policies never need to be edited in lockstep by accident.
_OWNER_DIRECT_PATH_PREFIX = "/api/owner-direct/"
_OWNER_DIRECT_RESPONSE_HEADERS = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"}

#: SLICE-0054 contract §9: every state-changing draft request must carry
#: this exact fixed non-simple header. Its presence alone is not
#: authorization -- it only forces the browser into a CORS preflight for a
#: cross-site request, which the accepted mechanism combines with a strict
#: Origin match rather than any permissive credentialed CORS grant.
_OWNER_DIRECT_CSRF_HEADER_NAME = "x-hullq-requested-with"
_OWNER_DIRECT_CSRF_HEADER_VALUE = "owner-direct-draft-v1"
_WEB_ORIGIN_ENV = "HULLQ_WEB_ORIGIN"

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
    "en": "This search link isn't valid. Enter a maximum draft as a plain decimal number of metres (e.g. 1.6) and/or a supported keel configuration.",
    "de": "Dieser Suchlink ist ungültig. Geben Sie den maximalen Tiefgang als einfache Dezimalzahl in Metern an (z. B. 1.6) und/oder eine unterstützte Kielkonfiguration.",
    "fr": "Ce lien de recherche n'est pas valide. Indiquez le tirant d'eau maximal sous forme de nombre décimal simple en mètres (par exemple 1.6) et/ou une configuration de quille prise en charge.",
    "pt": "Esta ligação de pesquisa não é válida. Indique o calado máximo como um número decimal simples em metros (por exemplo 1.6) e/ou uma configuração de quilha suportada.",
    "es": "Este enlace de búsqueda no es válido. Indique el calado máximo como un número decimal simple en metros (por ejemplo 1.6) y/o una configuración de quilla admitida.",
}


def _serialize_leaf_criterion(criterion: MixedLeafCriterion) -> dict[str, Any]:
    """SLICE-0055: the requested value/comparison for one active criterion
    (contract §7), never encoded only inside human-readable explanation
    text."""
    if isinstance(criterion, NumericLeafCriterion):
        return {
            "kind": "NUMERIC",
            "field": criterion.field,
            "comparison": criterion.comparison.value,
            "threshold_min": (
                str(criterion.threshold_min) if criterion.threshold_min is not None else None
            ),
            "threshold_max": (
                str(criterion.threshold_max) if criterion.threshold_max is not None else None
            ),
        }
    return {"kind": "CATEGORICAL", "field": criterion.field, "equals": criterion.equals}


def _serialize_criterion_evidence(evidence: Any) -> dict[str, Any]:
    """SLICE-0055: one `hullq.application.native_inventory_query.
    SearchCriterionEvidence` -- requested criterion, typed truth/reason, and
    the safely observed concrete canonical value when one exists."""
    return {
        "criterion": _serialize_leaf_criterion(evidence.criterion),
        "field": evidence.evaluation.field,
        "truth": evidence.evaluation.truth.value,
        "reason": (
            evidence.evaluation.reason.value if evidence.evaluation.reason is not None else None
        ),
        "explanation": evidence.evaluation.explanation,
        "observed_value": (
            str(evidence.observed_value) if evidence.observed_value is not None else None
        ),
    }


def _serialize_design_evaluation(design_evaluation: DesignQueryEvaluation) -> dict[str, Any]:
    """SLICE-0055: the complete design/configuration-level evaluation that
    admitted or failed to admit a listing's BoatDesign (contract §7),
    including the resolved configuration identity/identities
    (`matching_configuration_ids`) rather than only a BoatDesign id."""
    return {
        "design_id": design_evaluation.design_id,
        "result_class": design_evaluation.result_class.value,
        "matching_configuration_ids": list(design_evaluation.matching_configuration_ids),
        "reason": (
            design_evaluation.reason.value if design_evaluation.reason is not None else None
        ),
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
    web_origin: str | None = None,
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

    SLICE-0054's *web_origin* is the one exact accepted browser `Origin`
    for owner-direct draft CSRF validation (contract §9); like the auth
    configuration above it is resolved lazily, per-request, falling back
    to `HULLQ_WEB_ORIGIN` -- so an environment that never configures
    owner-direct draft access is unaffected, and only the draft POST/PUT
    handlers ever call the resolver.
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

    def _resolve_web_origin() -> str:
        if web_origin is not None:
            return web_origin
        raw = os.environ.get(_WEB_ORIGIN_ENV, "").strip()
        if not raw:
            raise RuntimeError(f"{_WEB_ORIGIN_ENV} is not set or empty")
        return raw

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

    def _normalized_origin(raw: str) -> tuple[str, str, int] | None:
        parts = urlsplit(raw)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return None
        default_port = 443 if parts.scheme == "https" else 80
        port = parts.port if parts.port is not None else default_port
        return (parts.scheme, parts.hostname.lower(), port)

    def _require_owner_direct_csrf(request: Request) -> None:
        # Contract §9: an exact Origin match plus a fixed non-simple header
        # -- never permissive credentialed CORS. Both checked before any
        # mutation is attempted by the caller.
        origin_header = request.headers.get("origin")
        requested_with = request.headers.get(_OWNER_DIRECT_CSRF_HEADER_NAME)
        accepted = _normalized_origin(_resolve_web_origin())
        actual = _normalized_origin(origin_header) if origin_header else None
        if (
            actual is None
            or actual != accepted
            or requested_with != _OWNER_DIRECT_CSRF_HEADER_VALUE
        ):
            raise HTTPException(status_code=403, detail="csrf validation failed")

    async def _read_json_body(request: Request, *, allow_empty: bool) -> Any:
        raw_body = await request.body()
        if not raw_body:
            if allow_empty:
                return None
            raise HTTPException(status_code=400, detail="request body must be a JSON object")
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid JSON body") from exc

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
        elif path.startswith(_OWNER_DIRECT_PATH_PREFIX):
            # SLICE-0054 contract §11: owner-direct draft data is private
            # workspace data, never cached and never indexed.
            for key, value in _OWNER_DIRECT_RESPONSE_HEADERS.items():
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
        assert outcome.search_outcome is not None
        search_outcome = outcome.search_outcome

        active_requirement: dict[str, str] = {}
        if outcome.draft_max is not None:
            active_requirement["draft_max"] = canonical_draft_max_str(outcome.draft_max)
        if outcome.keel_configuration is not None:
            active_requirement["keel_configuration"] = outcome.keel_configuration

        if isinstance(search_outcome, DraftMaxSearchOutcome):
            # SLICE-0051 draft-only shape, unchanged (contract §8 non-regression).
            return JSONResponse(
                {
                    "locale": locale,
                    "active_requirement": active_requirement,
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

        # SLICE-0055: keel_configuration alone or combined with draft_max.
        # Retains typed design-level and concrete-level evidence separately
        # (contract §6/§7, amendment Finding 1) rather than a flat list of
        # bare criterion truths.
        assert isinstance(search_outcome, NativeInventorySearchOutcome)
        return JSONResponse(
            {
                "locale": locale,
                "active_requirement": active_requirement,
                "confirmed_matches": [
                    {
                        "native_listing_id": match.native_listing_id.value,
                        "publishing_organization_id": match.publishing_organization_id.value,
                        "freshness_status": match.freshness_status.value,
                        "last_confirmed_at": (
                            match.last_confirmed_at.isoformat()
                            if match.last_confirmed_at is not None
                            else None
                        ),
                        "design_evaluation": _serialize_design_evaluation(match.design_evaluation),
                        "criterion_evidence": [
                            _serialize_criterion_evidence(evidence)
                            for evidence in match.concrete_criterion_evidence
                        ],
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
        require_same_host_session_topology(
            redirect_uri=redirect_uri, web_base_url=_resolve_web_base_url()
        )
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
        resolved_web_base_url = _resolve_web_base_url()
        require_same_host_session_topology(
            redirect_uri=redirect_uri, web_base_url=resolved_web_base_url
        )
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

    @app.get("/api/owner-direct/drafts")
    def list_owner_direct_drafts_route(request: Request) -> JSONResponse:
        session = _require_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="authentication required")
        conn = open_connection(resolved_database_url)
        try:
            records = list_owner_direct_drafts_for_account(conn, session)
        finally:
            conn.close()
        return JSONResponse({"drafts": [record_to_public_dict(r) for r in records]})

    @app.post("/api/owner-direct/drafts")
    async def create_owner_direct_draft_route(request: Request) -> JSONResponse:
        session = _require_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="authentication required")
        _require_owner_direct_csrf(request)
        raw_initial_payload = await _read_json_body(request, allow_empty=True)
        conn = open_connection(resolved_database_url)
        try:
            result = create_owner_direct_draft_for_account(conn, session, raw_initial_payload)
        finally:
            conn.close()
        if result.outcome is CreateOwnerDirectDraftOutcome.INVALID_PAYLOAD:
            return JSONResponse({"error": "invalid_draft_payload"}, status_code=400)
        assert result.record is not None
        return JSONResponse(record_to_public_dict(result.record), status_code=201)

    @app.get("/api/owner-direct/drafts/{draft_id}")
    def get_owner_direct_draft_route(draft_id: str, request: Request) -> JSONResponse:
        session = _require_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="authentication required")
        conn = open_connection(resolved_database_url)
        try:
            result = get_owner_direct_draft_for_account(conn, session, draft_id)
        finally:
            conn.close()
        if result.outcome is GetOwnerDirectDraftOutcome.NOT_FOUND:
            # Contract §3/§9: foreign and unknown draft_id are indistinguishable.
            raise HTTPException(status_code=404, detail="draft not found")
        assert result.record is not None
        return JSONResponse(record_to_public_dict(result.record))

    @app.put("/api/owner-direct/drafts/{draft_id}")
    async def update_owner_direct_draft_route(draft_id: str, request: Request) -> JSONResponse:
        session = _require_session(request)
        if session is None:
            raise HTTPException(status_code=401, detail="authentication required")
        _require_owner_direct_csrf(request)
        raw_body = await _read_json_body(request, allow_empty=False)
        conn = open_connection(resolved_database_url)
        try:
            result = update_owner_direct_draft_for_account(conn, session, draft_id, raw_body)
        finally:
            conn.close()
        if result.outcome is UpdateOwnerDirectDraftOutcome.INVALID_PAYLOAD:
            return JSONResponse({"error": "invalid_draft_payload"}, status_code=400)
        if result.outcome is UpdateOwnerDirectDraftOutcome.NOT_FOUND:
            raise HTTPException(status_code=404, detail="draft not found")
        if result.outcome is UpdateOwnerDirectDraftOutcome.VERSION_CONFLICT:
            return JSONResponse({"error": "version_conflict"}, status_code=409)
        assert result.record is not None
        return JSONResponse(record_to_public_dict(result.record))

    return app
