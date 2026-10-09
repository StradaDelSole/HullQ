"""SLICE-0079 production-readiness liveness/readiness HTTP proof.

`GET /healthz` must answer without any database dependency; `GET /readyz`
must actually probe PostgreSQL and fail closed (503, never a silent/false
"ok") when the configured database is unreachable.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline


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
    schema_name = f"hullq_s0079health_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def client(api_url: str) -> Generator[TestClient]:
    from hullq.api.app import create_app

    app = create_app(database_url=api_url, preview_signing_secret=b"0" * 32)
    with TestClient(app, base_url="http://api.test") as test_client:
        yield test_client


def test_liveness_returns_ok_without_touching_database(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"


def test_liveness_responds_even_when_database_is_unreachable() -> None:
    from hullq.api.app import create_app

    app = create_app(
        database_url="postgresql://hullq_unreachable:hullq_unreachable@localhost:1/hullq_unreachable",
        preview_signing_secret=b"0" * 32,
    )
    with TestClient(app, base_url="http://api.test") as test_client:
        response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_ok_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
    assert response.headers["cache-control"] == "no-store"


def test_readiness_fails_closed_when_database_is_unreachable() -> None:
    from hullq.api.app import create_app

    app = create_app(
        database_url="postgresql://hullq_unreachable:hullq_unreachable@localhost:1/hullq_unreachable",
        preview_signing_secret=b"0" * 32,
    )
    with TestClient(app, base_url="http://api.test") as test_client:
        response = test_client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unreachable"}


def test_every_response_carries_a_correlation_request_id(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.headers["x-request-id"]
    other = client.get("/healthz")
    assert other.headers["x-request-id"] != response.headers["x-request-id"]


def test_unhandled_exception_is_captured_and_never_leaks_detail(
    api_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hullq.api import app as app_module

    def _boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(app_module, "get_public_listing_read_model", _boom)
    app = app_module.create_app(database_url=api_url, preview_signing_secret=b"0" * 32)
    # Starlette's `ServerErrorMiddleware` always re-raises the original
    # exception after sending the registered handler's response (so a real
    # ASGI server's own logging still sees it) -- `TestClient`'s default
    # `raise_server_exceptions=True` surfaces that re-raise in the test
    # process itself. A real HTTP client (browser, API consumer) never sees
    # that re-raise, only the JSON response our handler actually sent, which
    # is what this test asserts on.
    with TestClient(app, base_url="http://api.test", raise_server_exceptions=False) as test_client:
        response = test_client.get("/api/listings/does-not-matter")
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"
    assert "request_id" in body
    assert "RuntimeError" not in response.text
    assert "simulated unexpected failure" not in response.text
