"""Persistence result types — SLICE-0013."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ImportStatus(StrEnum):
    """Outcome of a single import_research_evidence_bundle call."""

    IMPORTED = "imported"
    ALREADY_IMPORTED = "already_imported"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class ImportResult:
    """Deterministic result returned by the bundle importer."""

    status: ImportStatus
    bundle_id: str
    bundle_version: str
    content_hash: str
    detail: str | None = field(default=None)


class PersistenceConflictError(RuntimeError):
    """Raised internally when an immutable identity collision is detected.

    The importer catches this, rolls back the transaction, and returns
    ImportResult(status=CONFLICT, ...) instead of propagating the exception.
    Callers of import_research_evidence_bundle never receive this exception.
    """
