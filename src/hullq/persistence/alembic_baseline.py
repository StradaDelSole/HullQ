"""Safe Alembic migration baseline adoption — SLICE-0042.

Establishes the migration ownership boundary required by the 2026-09-02
Architecture Rebaseline: the accepted legacy schema produced by
``hullq.persistence.migrations`` (001_initial_schema + 002_canonical_identity
_schema) can be deterministically and safely placed under Alembic revision
control, without replaying/rewriting that accepted schema and without
mutating existing application data. All future schema migrations must start
from the Alembic baseline revision defined in
``alembic/versions/6f1c2a9d0001_legacy_002_baseline.py``.

No database URL or credential is hard-coded anywhere in this module;
``prepare_alembic_baseline`` always takes an explicit connection string
supplied by the caller (mirroring ``hullq.persistence.connection``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from hullq.persistence.migrations import MIGRATIONS_TABLE, apply_migrations

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = REPO_ROOT / "alembic"

# Must equal `revision` in alembic/versions/6f1c2a9d0001_legacy_002_baseline.py.
BASELINE_REVISION = "6f1c2a9d0001"

REQUIRED_LEGACY_MIGRATION_IDS: set[str] = {"001_initial_schema", "002_canonical_identity_schema"}

# A deliberately small, representative structural fingerprint of the
# accepted 001+002 schema — not a full semantic reconstruction (per the
# SLICE-0042 locked boundary), just enough independent evidence that the
# migration-history claim and the actual database structure agree.
REPRESENTATIVE_LEGACY_TABLES: set[str] = {
    "research_bundles",
    "research_observations",
    "research_evidence",
    "canonical_boat_designs",
    "canonical_admission_evidence_links",
}

ALEMBIC_VERSION_TABLE = "alembic_version"


class BaselineOutcome(StrEnum):
    FRESH_BOOTSTRAPPED_AND_STAMPED = "FRESH_BOOTSTRAPPED_AND_STAMPED"
    LEGACY_VERIFIED_AND_STAMPED = "LEGACY_VERIFIED_AND_STAMPED"
    ALREADY_BASELINED = "ALREADY_BASELINED"
    REJECTED_UNSAFE_STATE = "REJECTED_UNSAFE_STATE"


@dataclass(frozen=True)
class BaselineResult:
    outcome: BaselineOutcome
    reason: str | None = None

    @property
    def accepted(self) -> bool:
        return self.outcome is not BaselineOutcome.REJECTED_UNSAFE_STATE


class UnexpectedLegacyMigrationError(RuntimeError):
    """A post-002 legacy SQL migration file was found.

    After SLICE-0042, all future schema evolution must be an Alembic
    revision; the historical runner is a frozen bootstrap mechanism for
    001/002 only.
    """


def guard_no_post_002_legacy_migrations(directory: Path | None = None) -> None:
    """Fail closed if a 003+ legacy SQL migration file has appeared."""
    from hullq.persistence.migrations import MIGRATIONS_DIR, list_migration_files

    resolved = directory if directory is not None else MIGRATIONS_DIR
    found = {p.stem for p in list_migration_files(resolved)}
    unexpected = found - REQUIRED_LEGACY_MIGRATION_IDS
    if unexpected:
        raise UnexpectedLegacyMigrationError(
            "unexpected post-002 legacy SQL migration file(s): "
            f"{sorted(unexpected)}; add new schema changes as Alembic revisions instead"
        )


def _table_exists(conn: Any, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name = %s",
            [table_name],
        )
        return cur.fetchone() is not None


def _existing_table_names(conn: Any, candidates: set[str]) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name = ANY(%s)",
            [list(candidates)],
        )
        return {row[0] for row in cur.fetchall()}


def _schema_has_any_table(conn: Any) -> bool:
    """True if the target schema already contains any table/view at all.

    Used only to gate the "genuinely empty" fresh-bootstrap path. Checking
    only against the tables 001/002 are known to create is not sufficient:
    an unrecognized/untracked user or application relation (e.g. a
    ``native_listings`` or other table that belongs to neither the legacy
    schema nor Alembic) must also block bootstrap — "genuinely empty" means
    the schema has no relation of any kind, not merely "no table we happen
    to recognize."
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() LIMIT 1"
        )
        return cur.fetchone() is not None


def _applied_legacy_migration_ids(conn: Any) -> set[str] | None:
    """Return applied legacy migration ids, or None if the tracking table is absent."""
    if not _table_exists(conn, MIGRATIONS_TABLE):
        return None
    with conn.cursor() as cur:
        cur.execute(f"SELECT migration_id FROM {MIGRATIONS_TABLE}")
        return {row[0] for row in cur.fetchall()}


def _alembic_version_rows(conn: Any) -> list[str] | None:
    """Return alembic_version rows, or None if the table is absent."""
    if not _table_exists(conn, ALEMBIC_VERSION_TABLE):
        return None
    with conn.cursor() as cur:
        cur.execute(f"SELECT version_num FROM {ALEMBIC_VERSION_TABLE}")
        return [row[0] for row in cur.fetchall()]


def read_alembic_version(database_url: str) -> str | None:
    """Direct structural read of alembic_version; None if not yet stamped."""
    import psycopg

    conn = psycopg.connect(database_url)
    try:
        rows = _alembic_version_rows(conn)
    finally:
        conn.close()
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    raise RuntimeError(f"alembic_version table has {len(rows)} rows; expected at most 1")


def _as_sqlalchemy_url(raw_url: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if raw_url.startswith(prefix):
            return "postgresql+psycopg://" + raw_url[len(prefix) :]
    return raw_url


def alembic_config(database_url: str) -> Any:
    """Build an Alembic Config bound to *database_url*, without touching alembic.ini's URL."""
    from alembic.config import Config

    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    url = _as_sqlalchemy_url(database_url)
    # Config is backed by configparser's BasicInterpolation, which treats a
    # literal "%" (e.g. from a percent-encoded query string such as
    # "options=-c%20search_path%3D...") as interpolation syntax unless
    # doubled. get_main_option() un-escapes it symmetrically on read.
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def alembic_heads(database_url: str) -> list[str]:
    """Real `alembic heads` equivalent: revisions with no children in the script directory."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(alembic_config(database_url))
    return list(script.get_heads())


def alembic_upgrade_head(database_url: str) -> None:
    """Real `alembic upgrade head` against *database_url*."""
    from alembic import command

    command.upgrade(alembic_config(database_url), "head")


def _stamp_baseline(database_url: str) -> None:
    """Real `alembic stamp <baseline>` — writes alembic_version without running upgrade()."""
    from alembic import command

    command.stamp(alembic_config(database_url), BASELINE_REVISION)


def prepare_alembic_baseline(database_url: str) -> BaselineResult:
    """Safely transition the database at *database_url* onto the Alembic baseline.

    Returns a ``BaselineResult`` describing which of the SLICE-0042 safe
    adoption states applied. Never replays or mutates an existing accepted
    legacy schema, never mutates application data, and never force-stamps
    an ambiguous/unsafe database — such states are rejected with an
    actionable ``reason`` instead.
    """
    import psycopg

    conn = psycopg.connect(database_url)
    try:
        return _prepare(conn, database_url)
    finally:
        conn.close()


def _prepare(conn: Any, database_url: str) -> BaselineResult:
    alembic_rows = _alembic_version_rows(conn)
    legacy_ids = _applied_legacy_migration_ids(conn)
    present_tables = _existing_table_names(conn, REPRESENTATIVE_LEGACY_TABLES)

    if alembic_rows is not None:
        return _prepare_already_stamped(alembic_rows, legacy_ids, present_tables)

    if legacy_ids is None and not _schema_has_any_table(conn):
        return _prepare_fresh(conn, database_url)

    if (
        legacy_ids == REQUIRED_LEGACY_MIGRATION_IDS
        and present_tables == REPRESENTATIVE_LEGACY_TABLES
    ):
        # Accepted legacy database: verify only, never replay, never mutate data.
        _stamp_baseline(database_url)
        return BaselineResult(BaselineOutcome.LEGACY_VERIFIED_AND_STAMPED)

    return BaselineResult(
        BaselineOutcome.REJECTED_UNSAFE_STATE, _unsafe_reason(legacy_ids, present_tables)
    )


def _prepare_already_stamped(
    alembic_rows: list[str], legacy_ids: set[str] | None, present_tables: set[str]
) -> BaselineResult:
    if len(alembic_rows) != 1:
        return BaselineResult(
            BaselineOutcome.REJECTED_UNSAFE_STATE,
            f"alembic_version table has {len(alembic_rows)} rows; expected exactly 1",
        )
    current = alembic_rows[0]
    if current != BASELINE_REVISION:
        return BaselineResult(
            BaselineOutcome.REJECTED_UNSAFE_STATE,
            f"alembic reports revision {current!r}, expected baseline {BASELINE_REVISION!r}",
        )
    if (
        legacy_ids != REQUIRED_LEGACY_MIGRATION_IDS
        or present_tables != REPRESENTATIVE_LEGACY_TABLES
    ):
        return BaselineResult(
            BaselineOutcome.REJECTED_UNSAFE_STATE,
            "database is stamped at the Alembic baseline but legacy migration "
            "history/structural evidence no longer matches the accepted state",
        )
    return BaselineResult(BaselineOutcome.ALREADY_BASELINED)


def _prepare_fresh(conn: Any, database_url: str) -> BaselineResult:
    # Fresh bootstrap must be mechanically bounded to legacy 001+002 only:
    # fail closed *before* the legacy runner can apply anything if a post-002
    # legacy SQL migration file has appeared.
    try:
        guard_no_post_002_legacy_migrations()
    except UnexpectedLegacyMigrationError as exc:
        return BaselineResult(BaselineOutcome.REJECTED_UNSAFE_STATE, str(exc))

    apply_migrations(conn)
    legacy_ids = _applied_legacy_migration_ids(conn)
    present_tables = _existing_table_names(conn, REPRESENTATIVE_LEGACY_TABLES)
    if (
        legacy_ids != REQUIRED_LEGACY_MIGRATION_IDS
        or present_tables != REPRESENTATIVE_LEGACY_TABLES
    ):
        return BaselineResult(
            BaselineOutcome.REJECTED_UNSAFE_STATE,
            "fresh bootstrap through the legacy runner did not produce the "
            "expected accepted 001/002 state",
        )
    _stamp_baseline(database_url)
    return BaselineResult(BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED)


def _unsafe_reason(legacy_ids: set[str] | None, present_tables: set[str]) -> str:
    if legacy_ids is None:
        return "application tables exist but hullq_schema_migrations tracking table is absent"
    if legacy_ids != REQUIRED_LEGACY_MIGRATION_IDS:
        missing = REQUIRED_LEGACY_MIGRATION_IDS - legacy_ids
        unexpected = legacy_ids - REQUIRED_LEGACY_MIGRATION_IDS
        return f"legacy migration history mismatch: missing={sorted(missing)} unexpected={sorted(unexpected)}"
    missing_tables = REPRESENTATIVE_LEGACY_TABLES - present_tables
    return f"legacy migration history recorded but expected structural evidence missing: {sorted(missing_tables)}"
