"""End-to-end FastAPI integration tests for SLICE-0054 owner-direct drafts.

Runs the real FastAPI app (`hullq.api.app.create_app`) and the real
deterministic local OIDC test issuer (`hullq.testing.oidc_test_issuer`) in
process over Starlette's `TestClient` (mirroring
`test_broker_workspace_access_api.py`'s SLICE-0053 pattern): real RSA
signing, real JWKS, real token exchange, real PostgreSQL JIT account
mapping, real `HttpOnly` cookies via each app's own cookie jar.

Covers contract §3 (ownership/non-enumeration), §7 (optimistic concurrency),
§9 (CSRF), §11 (privacy headers) and §13 items 1-11 of the retained proof
(item 12, "no marketplace-table row is created", plus item 13, "existing
Broker Workspace retained proof still passes", are covered by
`tests/persistence/test_owner_direct_draft_persistence.py`'s non-regression
test and by `test_broker_workspace_access_api.py` itself, respectively --
this file focuses on the owner-direct HTTP boundary itself).
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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.security.oidc import AuthProviderConfig, JwksCache
from hullq.testing.oidc_test_issuer import create_test_issuer_app

_ISSUER_BASE = "http://issuer.test/"
_API_BASE = "http://api.test"
_WEB_ORIGIN = "http://web.test"
_CLIENT_ID = "hullq-owner-direct-test-client"


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
    schema_name = f"hullq_s0054api_{uuid.uuid4().hex[:16]}"
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

    Mirrors a real browser holding two separate per-origin cookie jars, plus
    explicit `Origin`/CSRF-header control per request -- a real browser sets
    `Origin` for us, but `httpx.Client` does not, so tests set it explicitly
    to simulate exactly what a same-origin Astro proxy vs. a cross-site
    attacker page would send.
    """

    def __init__(self, main: TestClient, issuer: TestClient) -> None:
        self.main = main
        self.issuer = issuer

    def _for(self, url: str) -> TestClient:
        return self.issuer if url.startswith(_ISSUER_BASE) else self.main

    def get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
        return self._for(url).get(url, params=params)

    def post(
        self,
        url: str,
        *,
        json: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return self._for(url).post(url, json=json, headers=headers)

    def put(
        self,
        url: str,
        *,
        json: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return self._for(url).put(url, json=json, headers=headers)

    @property
    def cookies(self) -> httpx.Cookies:
        return self.main.cookies


def _build_client(api_url: str) -> _BrowserClient:
    from hullq.api.app import create_app

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
    jwks_cache = JwksCache(config.jwks_uri, http_client=issuer_client)

    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        auth_provider_config=config,
        session_signing_secret=os.urandom(32),
        auth_redirect_uri=redirect_uri,
        web_origin=_WEB_ORIGIN,
        auth_http_client=issuer_client,
        auth_jwks_cache=jwks_cache,
    )
    main_client = TestClient(app, base_url=_API_BASE, follow_redirects=False)
    return _BrowserClient(main=main_client, issuer=issuer_client)


@pytest.fixture()
def client(api_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[_BrowserClient]:
    # Plain HTTP test transport, no TLS -- see test_broker_workspace_access_api.py's
    # identical `client` fixture for why `Secure` cookies require this.
    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    browser = _build_client(api_url)
    try:
        yield browser
    finally:
        browser.main.close()
        browser.issuer.close()


def _login(client: _BrowserClient, *, login_hint: str, next_path: str = "/sell/direct") -> None:
    login_response = client.get(
        "/api/auth/login", params={"next": next_path, "login_hint": login_hint}
    )
    assert login_response.status_code == 302
    authorize_response = client.get(login_response.headers["location"])
    assert authorize_response.status_code == 302, authorize_response.text
    callback_response = client.get(authorize_response.headers["location"])
    assert callback_response.status_code == 302
    assert callback_response.headers["location"] == next_path


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": "owner-direct-draft-v1"}


class TestOwnerDirectDraftVertical:
    def test_unauthenticated_list_denied(self, client: _BrowserClient) -> None:
        response = client.get("/api/owner-direct/drafts")
        assert response.status_code == 401

    def test_login_next_reaches_sell_direct(self, client: _BrowserClient) -> None:
        # _login already asserts the callback redirects to /sell/direct;
        # this test exists to name that contract §4 behavior explicitly.
        _login(client, login_hint="owner-direct-subject-1")

    def test_create_list_read_roundtrip(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-2")

        created = client.post("/api/owner-direct/drafts", json={}, headers=_csrf_headers())
        assert created.status_code == 201
        body = created.json()
        assert body["version"] == 1
        draft_id = body["draft_id"]

        listed = client.get("/api/owner-direct/drafts")
        assert listed.status_code == 200
        assert [d["draft_id"] for d in listed.json()["drafts"]] == [draft_id]

        fetched = client.get(f"/api/owner-direct/drafts/{draft_id}")
        assert fetched.status_code == 200
        assert fetched.json()["draft_id"] == draft_id
        assert fetched.json()["version"] == 1

    def test_save_partial_payload_and_reopen_exact_values(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-3")
        created = client.post("/api/owner-direct/drafts", json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        updated = client.put(
            f"/api/owner-direct/drafts/{draft_id}",
            json={
                "expected_version": 1,
                "physical_boat.boat_name": "Sea Breeze",
                "listing_offer.asking_price_mode": "POA",
            },
            headers=_csrf_headers(),
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2

        reopened = client.get(f"/api/owner-direct/drafts/{draft_id}")
        assert reopened.status_code == 200
        assert reopened.json()["physical_boat.boat_name"] == "Sea Breeze"
        assert reopened.json()["listing_offer.asking_price_mode"] == "POA"
        assert reopened.json()["version"] == 2

    def test_stale_expected_version_returns_409_without_mutation(
        self, client: _BrowserClient
    ) -> None:
        _login(client, login_hint="owner-direct-subject-4")
        created = client.post("/api/owner-direct/drafts", json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        first_update = client.put(
            f"/api/owner-direct/drafts/{draft_id}",
            json={"expected_version": 1, "physical_boat.boat_name": "First"},
            headers=_csrf_headers(),
        )
        assert first_update.status_code == 200

        stale_update = client.put(
            f"/api/owner-direct/drafts/{draft_id}",
            json={"expected_version": 1, "physical_boat.boat_name": "Stale"},
            headers=_csrf_headers(),
        )
        assert stale_update.status_code == 409

        current = client.get(f"/api/owner-direct/drafts/{draft_id}")
        assert current.json()["physical_boat.boat_name"] == "First"
        assert current.json()["version"] == 2

    def test_invalid_payload_key_returns_400_without_mutation(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-invalid")
        created = client.post("/api/owner-direct/drafts", json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        response = client.put(
            f"/api/owner-direct/drafts/{draft_id}",
            json={"expected_version": 1, "physical_boat.hull_material": "GRP"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400

        current = client.get(f"/api/owner-direct/drafts/{draft_id}")
        assert current.json()["version"] == 1

    def test_foreign_account_cannot_read_or_write_another_accounts_draft(
        self, client: _BrowserClient, api_url: str
    ) -> None:
        _login(client, login_hint="owner-direct-subject-victim-2")
        created = client.post("/api/owner-direct/drafts", json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        attacker = _build_client(api_url)
        try:
            _login(attacker, login_hint="owner-direct-subject-attacker")

            foreign_read = attacker.get(f"/api/owner-direct/drafts/{draft_id}")
            unknown_read = attacker.get(f"/api/owner-direct/drafts/{uuid.uuid4()}")
            assert foreign_read.status_code == 404
            assert unknown_read.status_code == 404
            assert foreign_read.content == unknown_read.content

            foreign_write = attacker.put(
                f"/api/owner-direct/drafts/{draft_id}",
                json={"expected_version": 1, "physical_boat.boat_name": "Hijacked"},
                headers=_csrf_headers(),
            )
            assert foreign_write.status_code == 404

            still_original = client.get(f"/api/owner-direct/drafts/{draft_id}")
            assert "physical_boat.boat_name" not in still_original.json()
        finally:
            attacker.main.close()
            attacker.issuer.close()

    def test_tampered_session_cookie_denied(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-tamper")
        real_cookie = client.cookies.get("hullq_session")
        assert real_cookie
        client.main.cookies.set(
            "hullq_session", real_cookie[:-1] + ("A" if real_cookie[-1] != "A" else "B")
        )
        response = client.get("/api/owner-direct/drafts")
        assert response.status_code == 401

    def test_create_without_csrf_headers_fails_closed(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-csrf-1")
        response = client.post("/api/owner-direct/drafts", json={})
        assert response.status_code == 403

    def test_create_with_wrong_origin_fails_closed(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-csrf-2")
        response = client.post(
            "/api/owner-direct/drafts",
            json={},
            headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": "owner-direct-draft-v1",
            },
        )
        assert response.status_code == 403

    def test_create_with_correct_origin_missing_requested_header_fails_closed(
        self, client: _BrowserClient
    ) -> None:
        _login(client, login_hint="owner-direct-subject-csrf-3")
        response = client.post("/api/owner-direct/drafts", json={}, headers={"Origin": _WEB_ORIGIN})
        assert response.status_code == 403

    def test_valid_same_origin_mutation_succeeds(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-csrf-4")
        response = client.post("/api/owner-direct/drafts", json={}, headers=_csrf_headers())
        assert response.status_code == 201

    def test_draft_responses_are_private_no_store_and_noindex(self, client: _BrowserClient) -> None:
        _login(client, login_hint="owner-direct-subject-headers")
        response = client.get("/api/owner-direct/drafts")
        assert response.headers.get("cache-control") == "private, no-store"
        assert response.headers.get("x-robots-tag") == "noindex"
