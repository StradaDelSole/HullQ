"""PostgreSQL persistence boundary for HullQ research/evidence records — SLICE-0013.

Public API:
- import_research_evidence_bundle: atomic transactional importer
- apply_migrations: schema migration runner
- fetch_bundle_snapshot: minimal round-trip readback
- ImportResult, ImportStatus: importer result types
- open_connection, get_database_url: connection helpers

Does not implement: identity resolution, automatic promotion, FieldResolution,
broad ingestion, query engine, API or marketplace integration.
"""

from hullq.persistence._types import ImportResult, ImportStatus, PersistenceConflictError
from hullq.persistence.connection import get_database_url, open_connection
from hullq.persistence.importer import import_research_evidence_bundle
from hullq.persistence.migrations import apply_migrations
from hullq.persistence.readback import fetch_bundle_snapshot

__all__ = [
    "ImportResult",
    "ImportStatus",
    "PersistenceConflictError",
    "apply_migrations",
    "fetch_bundle_snapshot",
    "get_database_url",
    "import_research_evidence_bundle",
    "open_connection",
]
