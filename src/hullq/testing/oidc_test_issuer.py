"""Deterministic local OIDC/JWKS test issuer — SLICE-0053.

Contract §14 requires the retained CI proof to run against "a local
deterministic OIDC/JWKS test issuer" that "exercise[s] the same
issuer/audience/signature/expiry/MFA normalization boundary as the Auth0
adapter" and "may not bypass authentication by monkeypatching an Account
directly into application code." This module is that issuer: a real,
minimal, RS256-signing authorization-code OIDC provider, used only in tests
and the retained proof script -- never imported by `hullq.api.app` or any
other production request path.

It auto-approves every `/authorize` request (there is no real end user), but
otherwise performs the same authorization-code + token-exchange + signed-JWT
mechanics a real OIDC provider performs: an opaque one-time code, a real
RSA keypair, real JWKS publication, and real client_id/client_secret/
redirect_uri checks at the token endpoint.

Test control knobs (never present on a real Auth0 tenant, and never
interpreted by `hullq.security.oidc`, which only ever consumes the signed
ID token): `/authorize`'s `login_hint` selects which synthetic `sub` is
authenticated (default `_DEFAULT_SUBJECT`), and `acr_values=mfa` asserts
`amr=["mfa"]` on the issued ID token; both parameters are standard,
harmless-if-ignored OIDC request parameters that Auth0 also accepts (Auth0
just uses them differently) -- FastAPI's login endpoint forwards them
verbatim without giving them any HullQ-specific meaning.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

__all__ = ["create_test_issuer_app"]

_DEFAULT_SUBJECT = "test-subject"
_ID_TOKEN_TTL_SECONDS = 300
_KID = "test-issuer-key-1"


@dataclass(frozen=True)
class _PendingAuthorization:
    subject: str
    nonce: str
    mfa: bool
    redirect_uri: str
    auth_time: int


def create_test_issuer_app(
    *,
    issuer: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> FastAPI:
    """Build a real, minimal, deterministic RS256 OIDC test issuer.

    *issuer* must be the exact base URL this app will be served at (e.g.
    ``http://127.0.0.1:{port}/``): it is embedded verbatim as the token
    `iss` claim and in the discovery document, so the FastAPI Auth0 adapter
    under test can validate against it exactly like a real tenant issuer.
    """
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jwt import encode as jwt_encode
    from jwt.algorithms import RSAAlgorithm

    # Aliased so the `/token` handler's identically-named Form(...)
    # parameters (which must be named client_id/client_secret/redirect_uri
    # to bind the corresponding POST fields) can be compared against the
    # configured values without shadowing them.
    client_id_outer = client_id
    client_secret_outer = client_secret

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk: dict[str, Any] = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk["kid"] = _KID
    public_jwk["use"] = "sig"
    public_jwk["alg"] = "RS256"

    pending: dict[str, _PendingAuthorization] = {}

    app = FastAPI(title="HullQ deterministic OIDC test issuer (SLICE-0053, never production)")

    @app.get("/.well-known/openid-configuration")
    def openid_configuration() -> JSONResponse:
        base = issuer.rstrip("/")
        return JSONResponse(
            {
                "issuer": issuer,
                "authorization_endpoint": f"{base}/authorize",
                "token_endpoint": f"{base}/token",
                "jwks_uri": f"{base}/.well-known/jwks.json",
                "response_types_supported": ["code"],
                "subject_types_supported": ["public"],
                "id_token_signing_alg_values_supported": ["RS256"],
            }
        )

    @app.get("/.well-known/jwks.json")
    def jwks() -> JSONResponse:
        return JSONResponse({"keys": [public_jwk]})

    @app.get("/authorize")
    def authorize(request: Request) -> Any:
        params = request.query_params
        response_type = params.get("response_type")
        req_client_id = params.get("client_id")
        req_redirect_uri = params.get("redirect_uri")
        state = params.get("state")
        nonce = params.get("nonce")
        login_hint = params.get("login_hint") or _DEFAULT_SUBJECT
        acr_values = params.get("acr_values") or ""

        if (
            response_type != "code"
            or req_client_id != client_id
            or req_redirect_uri != redirect_uri
        ):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "unrecognized client/redirect_uri",
                },
                status_code=400,
            )
        if not state or not nonce:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "missing state/nonce"},
                status_code=400,
            )

        code = secrets.token_urlsafe(24)
        pending[code] = _PendingAuthorization(
            subject=login_hint,
            nonce=nonce,
            mfa="mfa" in acr_values.split(),
            redirect_uri=req_redirect_uri,
            auth_time=int(time.time()),
        )
        query = urlencode({"code": code, "state": state})
        return RedirectResponse(url=f"{req_redirect_uri}?{query}", status_code=302)

    @app.post("/token")
    def token(
        grant_type: str = Form(...),
        code: str = Form(...),
        redirect_uri: str = Form(...),
        client_id: str = Form(...),
        client_secret: str = Form(...),
    ) -> JSONResponse:
        req_redirect_uri = redirect_uri
        req_client_id = client_id
        req_client_secret = client_secret

        if grant_type != "authorization_code":
            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
        if req_client_id != client_id_outer or req_client_secret != client_secret_outer:
            return JSONResponse({"error": "invalid_client"}, status_code=401)

        entry = pending.pop(code, None)
        if entry is None or entry.redirect_uri != req_redirect_uri:
            return JSONResponse({"error": "invalid_grant"}, status_code=400)

        now = int(time.time())
        claims = {
            "iss": issuer,
            "aud": client_id_outer,
            "sub": entry.subject,
            "iat": now,
            "exp": now + _ID_TOKEN_TTL_SECONDS,
            "auth_time": entry.auth_time,
            "nonce": entry.nonce,
            "amr": ["mfa"] if entry.mfa else [],
        }
        id_token = jwt_encode(claims, private_key, algorithm="RS256", headers={"kid": _KID})
        return JSONResponse(
            {
                "id_token": id_token,
                "access_token": secrets.token_urlsafe(16),
                "token_type": "Bearer",
                "expires_in": _ID_TOKEN_TTL_SECONDS,
            }
        )

    return app
