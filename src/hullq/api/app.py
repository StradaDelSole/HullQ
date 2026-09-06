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
from fastapi.responses import JSONResponse

from hullq.application.preview_read import get_preview_read_model
from hullq.application.public_listing_read import get_public_listing_read_model
from hullq.domain.market_identity import NativeListingId
from hullq.persistence.connection import get_database_url, open_connection
from hullq.security.preview_signing import get_preview_signing_secret

__all__ = ["create_app"]

_PREVIEW_PATH_PREFIX = "/api/_preview/"
_PUBLIC_LISTINGS_PATH_PREFIX = "/api/listings/"

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

    return app
