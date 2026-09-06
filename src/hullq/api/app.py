"""SLICE-0048 preview FastAPI application.

The repository's first FastAPI surface. FastAPI remains the sole Python HTTP
backend; this module adds exactly one explicitly unstable, non-canonical
route (`GET /api/_preview/listings/{preview_token}`) and freezes no
`/api/v1/...` contract. The route handler stays thin: all previewable-read
composition lives in `hullq.application.preview_read`.

No third-party analytics/tracker/subresource is loaded by this API; the
interactive OpenAPI/Swagger docs routes are disabled so this proof surface
never pulls in a third-party CDN asset.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from hullq.application.preview_read import get_preview_read_model
from hullq.persistence.connection import get_database_url, open_connection
from hullq.security.preview_signing import get_preview_signing_secret

__all__ = ["create_app"]

# Sent on every response from this preview surface: a preview token is a
# bearer capability carried in the URL path, never a publicly indexable or
# cacheable resource (SLICE-0048 §5.2).
_PREVIEW_RESPONSE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
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
    async def _preview_response_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        for key, value in _PREVIEW_RESPONSE_HEADERS.items():
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

    return app
