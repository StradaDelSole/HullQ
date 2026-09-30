"""Conftest for PostgreSQL integration tests — SLICE-0013.

Tests in this package require a real PostgreSQL 18 instance. They are skipped
automatically when HULLQ_TEST_DATABASE_URL is not set in the environment so
that the standard quality CI job (no PostgreSQL) remains unaffected.

In the dedicated db-integration CI job, HULLQ_TEST_DATABASE_URL is set to a
local service-container connection string and all tests run.

SLICE-0073 safe-parallel-execution note
----------------------------------------
Most files in this package already isolate every test in its own throwaway
PostgreSQL schema (`_create_schema`/`_with_search_path`, created and dropped
per test) and are therefore already safe to schedule on any pytest-xdist
worker concurrently with any other test.

A small, explicit set of files instead reads/writes the connection's
*default* (unqualified search_path) schema directly -- via the shared
`clean_conn`/`migrated_conn` fixtures below, a file-local `benchmark_conn`
fixture, or an inline `TRUNCATE TABLE ...` against a bare
`psycopg.connect(db_url)` -- and rely on running strictly one-at-a-time
against that shared state. `_XDIST_SHARED_SCHEMA_MODULES` names exactly
those files (verified by scanning every tests/persistence/test_*.py file for
the absence of the per-test schema-isolation pattern; see SLICE-0073
CI_THROUGHPUT_EVIDENCE.md). `pytest_collection_modifyitems` below pins every
test collected from one of those files to a single shared `xdist_group` so
`pytest -n auto --dist loadgroup` never runs two of them concurrently, while
every other persistence test remains freely distributable across workers.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import pytest

_XDIST_SHARED_SCHEMA_GROUP = "hullq-persistence-shared-default-schema"
_XDIST_SHARED_SCHEMA_MODULES = frozenset(
    {
        "test_benchmark_persistence.py",
        "test_canonical_identity_integration.py",
        "test_persistence_integration.py",
        "test_wikidata_sl0022_alt_route_admission_integration.py",
        "test_wikidata_sl0026_tier1_enrichment_pilot_integration.py",
        "test_wikidata_sl0027_qualifier_semantics_correction_integration.py",
        "test_wikidata_sl0028_full_boundary_evidence_integration.py",
        "test_wikidata_sl0030_mass_unit_correction_integration.py",
        "test_wikidata_tier0_bootstrap_integration.py",
        "test_wikidata_tier0_sl0018_expansion_integration.py",
    }
)


def _get_test_url() -> str | None:
    return os.environ.get("HULLQ_TEST_DATABASE_URL", "").strip() or None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip DB tests without a database, and pin shared-schema tests to one worker."""
    url_present = _get_test_url() is not None
    skip = pytest.mark.skip(reason="HULLQ_TEST_DATABASE_URL not set; skipping DB integration tests")
    shared_group = pytest.mark.xdist_group(name=_XDIST_SHARED_SCHEMA_GROUP)
    for item in items:
        fspath = str(item.fspath)
        # Match only tests actually inside the tests/persistence/ directory.
        if "/tests/persistence/" not in fspath.replace("\\", "/"):
            continue
        if not url_present:
            item.add_marker(skip)
        if item.fspath.basename in _XDIST_SHARED_SCHEMA_MODULES:
            item.add_marker(shared_group)


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
