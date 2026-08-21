"""Canonical identity persistence result/request types — SLICE-0016.

SLICE-0016 starts at the already-admitted canonical payload boundary
(docs/slices/SLICE-0016-canonical-identity-persistence-bootstrap-admission.md).
Every entity/relationship/link here is caller-supplied and already satisfies
the accepted identity semantics; this module performs no identity resolution.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from hullq.domain.identity import Brand, Organization
from hullq.domain.provenance import SubjectKind

__all__ = [
    "CanonicalEvidenceLink",
    "CanonicalIdentityAdmission",
    "CanonicalImportResult",
    "CanonicalImportStatus",
    "CanonicalPersistenceConflictError",
    "CanonicalReferenceError",
]


class CanonicalImportStatus(StrEnum):
    """Outcome of a single import_canonical_identity_admission call."""

    IMPORTED = "imported"
    ALREADY_IMPORTED = "already_imported"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class CanonicalImportResult:
    """Deterministic result returned by the canonical identity importer."""

    status: CanonicalImportStatus
    detail: str | None = field(default=None)


class CanonicalPersistenceConflictError(RuntimeError):
    """Raised internally when an immutable canonical identity collision is detected.

    The importer catches this, rolls back the transaction, and returns
    CanonicalImportResult(status=CONFLICT, ...) instead of propagating it.
    Callers of import_canonical_identity_admission never receive this exception.
    """


class CanonicalReferenceError(RuntimeError):
    """Raised when an admission references a canonical ID or evidence/observation
    ID that does not exist.

    This is distinct from CanonicalPersistenceConflictError: it signals a
    missing/invalid reference (fail closed on a caller input error), not a
    collision between two pieces of immutable content sharing one ID. The
    triggering PostgreSQL transaction is always rolled back before this is
    raised to the caller.
    """


# Entity kinds this slice admits links for. Reuses the single SubjectKind
# vocabulary already shared with FieldEvidence/FieldResolution provenance.
_LINKABLE_ENTITY_KINDS = frozenset(
    {
        SubjectKind.BRAND,
        SubjectKind.ORGANIZATION,
        SubjectKind.BOAT_MODEL,
        SubjectKind.BOAT_DESIGN,
        SubjectKind.BRAND_MODEL_RELATIONSHIP,
        SubjectKind.ORGANIZATION_DESIGN_RELATIONSHIP,
    }
)


@dataclass(frozen=True)
class CanonicalEvidenceLink:
    """A stable, auditable link from one canonical identity/relationship to
    exactly one retained HullQ research observation or evidence record that
    supported its admission.

    Exactly one of observation_id / evidence_id MUST be set. Addressing is by
    the observation's/evidence's own stable ID — never by array position.
    Neither field may reference a ReferenceCrosscheck: crosschecks are
    structurally outside HullQ evidence/provenance and cannot satisfy this
    linkage (enforced further by the absence of any such foreign key at the
    database layer).
    """

    link_id: str
    entity_kind: SubjectKind
    entity_id: str
    observation_id: str | None = None
    evidence_id: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.link_id:
            raise ValueError("CanonicalEvidenceLink.link_id must be non-empty")
        if self.entity_kind not in _LINKABLE_ENTITY_KINDS:
            raise ValueError(
                f"CanonicalEvidenceLink.entity_kind {self.entity_kind!r} is not a "
                f"linkable canonical identity kind: {sorted(_LINKABLE_ENTITY_KINDS)}"
            )
        if not self.entity_id:
            raise ValueError("CanonicalEvidenceLink.entity_id must be non-empty")
        has_obs = self.observation_id is not None
        has_ev = self.evidence_id is not None
        if has_obs == has_ev:
            raise ValueError(
                "CanonicalEvidenceLink requires exactly one of observation_id / "
                "evidence_id to be set"
            )


@dataclass(frozen=True)
class CanonicalIdentityAdmission:
    """A bounded, transactional admission of already-decided canonical identity
    records into PostgreSQL.

    boat_models / boat_designs are already schema-validated dict payloads
    (BOAT_MODEL_SCHEMA.v0.2 / BOAT_DESIGN_SCHEMA.v0.5) rather than a Python
    domain dataclass: no such canonical dataclass exists yet, and this slice
    does not introduce one. brand_relationships embedded in a boat_model
    payload and relationships.builders embedded in a boat_design payload are
    decomposed by the importer into standalone
    canonical_brand_model_relationships / canonical_organization_design_relationships
    rows using the enclosing entity's own ID.

    This is intentionally the entire admission surface: it is not a generic
    ingestion manifest and carries no orchestration, retry, or scheduling
    semantics.
    """

    brands: tuple[Brand, ...] = ()
    organizations: tuple[Organization, ...] = ()
    boat_models: tuple[Mapping[str, Any], ...] = ()
    boat_designs: tuple[Mapping[str, Any], ...] = ()
    evidence_links: tuple[CanonicalEvidenceLink, ...] = ()
