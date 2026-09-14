"""End-to-end FastAPI integration tests for SLICE-0053 broker access.

Runs the real FastAPI app (`hullq.api.app.create_app`) and the real
deterministic local OIDC test issuer (`hullq.testing.oidc_test_issuer`)
in-process over Starlette's `TestClient` -- real RSA signing, real JWKS,
real token exchange, real PostgreSQL JIT mapping and membership reads, real
`HttpOnly` cookies via each app's own cookie jar. No Account is ever created
by monkeypatching.

Two hosts, two `TestClient`s: `main` talks to the FastAPI app (`api.test`),
`issuer` talks to the deterministic OIDC issuer (`issuer.test`) -- exactly
like a real browser holding separate cookie jars per origin, and exactly
matching FastAPI's own server-to-issuer calls (token exchange/JWKS), which
reuse the `issuer` client as their injected transport.

Complements `scripts/inspect_broker_workspace_access.py` (which additionally
exercises the built Astro SSR layer over real subprocesses/sockets) with a
fast, coverage-counted in-process equivalent of the FastAPI-side vertical.
"""

from __future__ import annotations

import os
import secrets
import uuid
from collections.abc import Generator
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
import psycopg
import pytest
from starlette.testclient import TestClient

from hullq.domain.broker_access import Provider
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import (
    get_or_create_account_for_identity,
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.security.oidc import AuthProviderConfig, JwksCache
from hullq.testing.oidc_test_issuer import create_test_issuer_app

_ISSUER_BASE = "http://issuer.test/"
_API_BASE = "http://api.test"
_CLIENT_ID = "hullq-int-test-client"
_ORG_A = "ORG-INT-A"
_ORG_B = "ORG-INT-B"


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


@pytest.fixture()
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0053api_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


class _BrowserClient:
    """Dispatches each absolute URL to whichever `TestClient` owns that host.

    Mirrors a real browser holding two separate per-origin cookie jars: the
    HullQ session/login-state cookies live only in `main`'s jar, and the
    issuer never sees or needs them.
    """

    def __init__(self, main: TestClient, issuer: TestClient) -> None:
        self.main = main
        self.issuer = issuer

    def _for(self, url: str) -> TestClient:
        return self.issuer if url.startswith(_ISSUER_BASE) else self.main

    def get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
        return self._for(url).get(url, params=params)

    def post(self, url: str) -> httpx.Response:
        return self._for(url).post(url)

    @property
    def cookies(self) -> httpx.Cookies:
        return self.main.cookies


@pytest.fixture()
def client(api_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[_BrowserClient]:
    from hullq.api.app import create_app

    # This fixture drives the app over plain HTTP (no TLS); a `Secure`
    # cookie would never be attached to a plain-HTTP request by a real
    # browser (or by httpx's own cookie jar, which enforces the same RFC
    # 6265 rule) -- production always leaves this unset/true.
    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")

    client_secret = secrets.token_urlsafe(24)
    redirect_uri = f"{_API_BASE}/api/auth/callback"
    issuer_app = create_test_issuer_app(
        issuer=_ISSUER_BASE,
        client_id=_CLIENT_ID,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    issuer_client = TestClient(issuer_app, base_url=_ISSUER_BASE, follow_redirects=False)

    config = AuthProviderConfig(
        provider=Provider.AUTH0,
        issuer=_ISSUER_BASE,
        authorize_endpoint=f"{_ISSUER_BASE}authorize",
        token_endpoint=f"{_ISSUER_BASE}token",
        jwks_uri=f"{_ISSUER_BASE}.well-known/jwks.json",
        client_id=_CLIENT_ID,
        client_secret=client_secret,
    )
    # FastAPI's own server-to-issuer calls (token exchange, JWKS) reuse this
    # same TestClient as their injected httpx-compatible transport -- no
    # real network I/O anywhere in this test.
    jwks_cache = JwksCache(config.jwks_uri, http_client=issuer_client)

    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        auth_provider_config=config,
        session_signing_secret=os.urandom(32),
        auth_redirect_uri=redirect_uri,
        web_base_url=None,
        auth_http_client=issuer_client,
        auth_jwks_cache=jwks_cache,
    )
    main_client = TestClient(app, base_url=_API_BASE, follow_redirects=False)

    try:
        yield _BrowserClient(main=main_client, issuer=issuer_client)
    finally:
        main_client.close()
        issuer_client.close()


def _login(
    client: _BrowserClient,
    *,
    login_hint: str,
    next_path: str = "/broker",
    acr_values: str | None = None,
) -> httpx.Response:
    params = {"next": next_path, "login_hint": login_hint}
    if acr_values:
        params["acr_values"] = acr_values
    login_response = client.get("/api/auth/login", params=params)
    assert login_response.status_code == 302
    authorize_response = client.get(login_response.headers["location"])
    assert authorize_response.status_code == 302, authorize_response.text
    return client.get(authorize_response.headers["location"])


class TestBrokerWorkspaceAccessVertical:
    def test_unauthenticated_broker_context_denied(self, client: httpx.Client) -> None:
        response = client.get("/api/broker/context")
        assert response.status_code == 401

    def test_full_login_creates_stable_account_with_httponly_cookie(
        self, client: httpx.Client
    ) -> None:
        callback_response = _login(client, login_hint="int-subject-1")
        assert callback_response.status_code == 302
        assert callback_response.headers["location"] == "/broker"
        set_cookie = callback_response.headers.get("set-cookie", "")
        assert "hullq_session=" in set_cookie
        assert "HttpOnly" in set_cookie

        context = client.get("/api/broker/context")
        assert context.status_code == 200
        body = context.json()
        assert body["organizations"] == []
        assert body["account_id"]

    def test_retry_login_same_identity_same_account(self, client: httpx.Client) -> None:
        _login(client, login_hint="int-subject-retry")
        first_account_id = client.get("/api/broker/context").json()["account_id"]

        # Fresh browser-style client sharing nothing but hitting the same app.
        _login(client, login_hint="int-subject-retry")
        second_account_id = client.get("/api/broker/context").json()["account_id"]
        assert first_account_id == second_account_id

    def test_membership_grants_context_and_mfa_gating(
        self, client: httpx.Client, api_url: str
    ) -> None:
        _login(client, login_hint="int-subject-mfa")
        account_id = client.get("/api/broker/context").json()["account_id"]

        conn = psycopg.connect(api_url)
        try:
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_A),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-INT-A"),
                    account_id=AccountId(account_id),
                    organization_id=MarketplaceOrganizationId(_ORG_A),
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        context = client.get("/api/broker/context").json()
        assert {o["organization_id"] for o in context["organizations"]} == {_ORG_A}

        blocked = client.get(f"/api/broker/organizations/{_ORG_A}")
        assert blocked.status_code == 403
        assert blocked.json() == {"error": "mfa_required"}

        _login(
            client,
            login_hint="int-subject-mfa",
            next_path=f"/broker/organizations/{_ORG_A}",
            acr_values="mfa",
        )

        authorized = client.get(f"/api/broker/organizations/{_ORG_A}")
        assert authorized.status_code == 200
        payload = authorized.json()
        assert payload["organization_id"] == _ORG_A
        assert payload["mfa_satisfied"] is True
        assert payload["roles"] == ["PUBLISHER"]

    def test_cross_organization_denial_is_non_enumerating(
        self, client: httpx.Client, api_url: str
    ) -> None:
        _login(client, login_hint="int-subject-cross")

        conn = psycopg.connect(api_url)
        try:
            # A real durable Account for the foreign membership -- never
            # created by monkeypatching, just via the same JIT mapping path
            # a real login would use, for an identity this test never logs
            # in as.
            other_account_id = get_or_create_account_for_identity(
                conn,
                provider=Provider.AUTH0,
                issuer=_ISSUER_BASE,
                subject="int-subject-someone-else",
            ).account_id
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_B),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-INT-B"),
                    account_id=other_account_id,
                    organization_id=MarketplaceOrganizationId(_ORG_B),
                    roles=frozenset({MembershipRole.OWNER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        foreign = client.get(f"/api/broker/organizations/{_ORG_B}")
        never_created = client.get("/api/broker/organizations/ORG-INT-NEVER-CREATED")
        assert foreign.status_code == 404
        assert never_created.status_code == 404
        assert foreign.content == never_created.content

    def test_state_mismatch_at_callback_fails_closed(self, client: httpx.Client) -> None:
        login_response = client.get(
            "/api/auth/login", params={"next": "/broker", "login_hint": "int-subject-x"}
        )
        authorize_response = client.get(login_response.headers["location"])
        real_callback_url = authorize_response.headers["location"]
        tampered = real_callback_url.replace("state=", "state=tampered-", 1)
        response = client.get(tampered)
        assert response.status_code == 400

    def test_logout_clears_session(self, client: httpx.Client) -> None:
        _login(client, login_hint="int-subject-logout")
        assert client.get("/api/broker/context").status_code == 200

        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        assert client.get("/api/broker/context").status_code == 401

    def test_tampered_session_cookie_rejected(self, client: httpx.Client) -> None:
        _login(client, login_hint="int-subject-tamper")
        client.cookies.set("hullq_session", "tampered-garbage-value", domain="api.test")
        response = client.get("/api/broker/context")
        assert response.status_code == 401
