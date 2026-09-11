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
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from hullq.application.preview_read import get_preview_read_model
from hullq.application.public_listing_read import get_public_listing_read_model
from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request
from hullq.domain.market_identity import NativeListingId
from hullq.persistence.connection import get_database_url, open_connection
from hullq.search.draft_max_request import canonical_draft_max_str
from hullq.security.preview_signing import get_preview_signing_secret

__all__ = ["create_app"]

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
) -> FastAPI:
    """Build the SLICE-0048 preview FastAPI application.

    *database_url* / *preview_signing_secret* may be injected explicitly
    (used by tests against a disposable schema); otherwise both are resolved
    from the environment at app-creation time via the accepted fail-fast
    loaders (`hullq.persistence.connection.get_database_url`,
    `hullq.security.preview_signing.get_preview_signing_secret`) -- an
    invalid/missing signing secret must fail app creation, never fall back
    to an insecure default.
    """
    resolved_database_url = database_url if database_url is not None else get_database_url()
    resolved_secret = (
        preview_signing_secret
        if preview_signing_secret is not None
        else get_preview_signing_secret()
    )

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
            model = get_public_listing_read_model(conn, NativeListingId(native_listing_id))
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
            outcome = evaluate_search_request(conn, locale=locale, query_params=raw_query_params)
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
                    }
                    for match in search_outcome.confirmed_matches
                ],
                "confirmed_match_count": search_outcome.confirmed_match_count,
                "insufficient_data_count": search_outcome.insufficient_data_count,
            }
        )

    return app
