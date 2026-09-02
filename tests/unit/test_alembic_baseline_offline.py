"""Offline unit tests for the Alembic migration baseline — SLICE-0042.

No PostgreSQL connection required: these tests exercise the Alembic script
directory, configuration wiring and the frozen-legacy-boundary guard.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hullq.persistence.alembic_baseline import (
    ALEMBIC_INI_PATH,
    ALEMBIC_SCRIPT_LOCATION,
    BASELINE_REVISION,
    REQUIRED_LEGACY_MIGRATION_IDS,
    BaselineOutcome,
    BaselineResult,
    UnexpectedLegacyMigrationError,
    _as_sqlalchemy_url,
    alembic_config,
    alembic_heads,
    guard_no_post_002_legacy_migrations,
)


def test_alembic_ini_has_no_committed_secret() -> None:
    text = ALEMBIC_INI_PATH.read_text(encoding="utf-8")
    assert "sqlalchemy.url =" in text
    for line in text.splitlines():
        if line.strip().startswith("sqlalchemy.url"):
            assert line.split("=", 1)[1].strip() == ""


def test_alembic_ini_and_script_location_exist() -> None:
    assert ALEMBIC_INI_PATH.is_file()
    assert ALEMBIC_SCRIPT_LOCATION.is_dir()
    assert (ALEMBIC_SCRIPT_LOCATION / "env.py").is_file()
    assert (ALEMBIC_SCRIPT_LOCATION / "versions").is_dir()


def test_baseline_revision_is_the_single_head() -> None:
    heads = alembic_heads("postgresql://unused:unused@localhost/unused")
    assert heads == [BASELINE_REVISION]


def test_baseline_revision_introduces_no_application_ddl() -> None:
    revision_files = list((ALEMBIC_SCRIPT_LOCATION / "versions").glob("*.py"))
    assert len(revision_files) == 1
    text = revision_files[0].read_text(encoding="utf-8")
    assert BASELINE_REVISION in text
    assert "down_revision: str | None = None" in text
    # Must not invoke `op.*` DDL helpers — the revision is a pure marker.
    assert "op." not in text


def test_alembic_config_never_bakes_a_real_url_into_the_ini() -> None:
    cfg = alembic_config("postgresql+psycopg://user:pass@host/db")
    # The URL only ever lives on the in-memory Config object built here, not
    # on disk in alembic.ini.
    ini_text = ALEMBIC_INI_PATH.read_text(encoding="utf-8")
    assert "user:pass" not in ini_text
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql+psycopg://user:pass@host/db"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_as_sqlalchemy_url_forces_psycopg3_dialect(raw: str, expected: str) -> None:
    assert _as_sqlalchemy_url(raw) == expected


def test_guard_passes_on_the_accepted_repository_state() -> None:
    guard_no_post_002_legacy_migrations()  # must not raise


def test_guard_rejects_a_post_002_legacy_migration(tmp_path: Path) -> None:
    (tmp_path / "001_initial_schema.sql").write_text("-- noop", encoding="utf-8")
    (tmp_path / "002_canonical_identity_schema.sql").write_text("-- noop", encoding="utf-8")
    (tmp_path / "003_marketplace.sql").write_text("-- noop", encoding="utf-8")

    with pytest.raises(UnexpectedLegacyMigrationError, match="003_marketplace"):
        guard_no_post_002_legacy_migrations(directory=tmp_path)


def test_required_legacy_migration_ids_match_the_accepted_bootstrap_files() -> None:
    assert {"001_initial_schema", "002_canonical_identity_schema"} == REQUIRED_LEGACY_MIGRATION_IDS


def test_baseline_result_accepted_property() -> None:
    assert BaselineResult(BaselineOutcome.ALREADY_BASELINED).accepted is True
    assert BaselineResult(BaselineOutcome.REJECTED_UNSAFE_STATE, "reason").accepted is False
