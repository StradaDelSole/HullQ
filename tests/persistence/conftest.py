"""Conftest for PostgreSQL integration tests — SLICE-0013.

Tests in this package require a real PostgreSQL 18 instance. They are skipped
automatically when HULLQ_TEST_DATABASE_URL is not set in the environment so
that the standard quality CI job (no PostgreSQL) remains unaffected.

In the dedicated db-integration CI job, HULLQ_TEST_DATABASE_URL is set to a
local service-container connection string and all tests run.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import pytest


def _get_test_url() -> str | None:
    return os.environ.get("HULLQ_TEST_DATABASE_URL", "").strip() or None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip all tests in tests/persistence/ when HULLQ_TEST_DATABASE_URL is not set."""
    if _get_test_url() is not None:
        return
    skip = pytest.mark.skip(reason="HULLQ_TEST_DATABASE_URL not set; skipping DB integration tests")
    for item in items:
        fspath = str(item.fspath)
        # Match only tests actually inside the tests/persistence/ directory.
        if "/tests/persistence/" in fspath.replace("\\", "/"):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def db_url() -> str:
    url = _get_test_url()
    if url is None:
        pytest.skip("HULLQ_TEST_DATABASE_URL not set")
    return url


@pytest.fixture(scope="session")
def migrated_conn(db_url: str) -> Generator[Any]:
    """Session-scoped connection with migrations applied to a fresh test schema."""
    import psycopg

    from hullq.persistence.migrations import apply_migrations

    conn = psycopg.connect(db_url)
    try:
        apply_migrations(conn)
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def clean_conn(db_url: str) -> Generator[Any]:
    """Function-scoped connection with migrations applied; each test gets a clean state."""
    import psycopg

    from hullq.persistence.migrations import apply_migrations

    conn = psycopg.connect(db_url)
    try:
        apply_migrations(conn)
        # Truncate all data tables in dependency order so each test is isolated.
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE TABLE
                    canonical_admission_evidence_links,
                    canonical_organization_design_relationships,
                    canonical_boat_designs,
                    canonical_brand_model_relationships,
                    canonical_boat_model_aliases,
                    canonical_boat_models,
                    canonical_organization_aliases,
                    canonical_organizations,
                    canonical_brand_aliases,
                    canonical_brands,
                    bundle_evidence_members,
                    bundle_reference_crosschecks,
                    bundle_unresolved_findings,
                    bundle_observation_members,
                    research_evidence,
                    research_observations,
                    research_bundles
                RESTART IDENTITY CASCADE
            """)
        conn.commit()
        yield conn
    finally:
        conn.close()
