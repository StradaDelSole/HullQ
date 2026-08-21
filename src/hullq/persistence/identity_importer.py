"""Deterministic transactional canonical identity importer — SLICE-0016.

Entry point: import_canonical_identity_admission(conn, admission, registry) -> CanonicalImportResult

Importer guarantees:
- every payload is schema-validated against the accepted contracts before any
  database mutation (fail closed, no partial write on a validation failure);
- one deterministic content fingerprint per canonical row, independent of the
  order of any unordered collection it belongs to;
- one database transaction for the whole admission: a dependent multi-entity
  admission (e.g. BoatDesign + its BoatModel) is atomic;
- idempotent: exact repeated admission returns ALREADY_IMPORTED, no duplicates;
- fail-closed: same identity (same ID) with different content returns CONFLICT;
- race-safe: INSERT ... ON CONFLICT ... DO NOTHING eliminates check-then-insert
  races, exactly like the SLICE-0013 research-evidence importer;
- a missing/invalid canonical or evidence/observation reference raises
  CanonicalReferenceError (a caller input error, not a content conflict) and
  never leaves a partially admitted graph;
- a CanonicalEvidenceLink's (entity_kind, entity_id) must address a real
  canonical row of that exact kind — a nonexistent target, or a target ID
  that exists only under a different kind, fails closed;
- a BoatModel's caller-supplied boat_design_ids projection must exactly
  match (order-independent) the canonical BoatDesign graph actually admitted
  for it — a missing/extra/misattributed design fails closed;
- no identity resolution, no automatic ID minting from names/source IDs, no
  automatic Brand/Organization/BoatModel/BoatDesign inference.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from hullq.contracts import ContractRegistry
from hullq.domain.identity import AliasClass, Brand, IdentityAlias, Organization
from hullq.domain.provenance import SubjectKind
from hullq.persistence.identity_fingerprint import (
    fingerprint_alias,
    fingerprint_boat_design_row,
    fingerprint_boat_model_row,
    fingerprint_brand_model_relationship,
    fingerprint_brand_row,
    fingerprint_evidence_link,
    fingerprint_organization_design_relationship,
    fingerprint_organization_row,
)
from hullq.persistence.identity_schema import (
    alias_row_params,
    boat_design_row_params,
    boat_model_row_params,
    brand_model_relationship_row_params,
    brand_model_relationship_standalone_dict,
    brand_row_params,
    brand_to_schema_dict,
    organization_design_relationship_row_params,
    organization_design_relationship_standalone_dict,
    organization_row_params,
    organization_to_schema_dict,
)
from hullq.persistence.identity_types import (
    CanonicalEvidenceLink,
    CanonicalIdentityAdmission,
    CanonicalImportResult,
    CanonicalImportStatus,
    CanonicalPersistenceConflictError,
    CanonicalReferenceError,
)

# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

_INSERT_BRAND = """
INSERT INTO canonical_brands (id, canonical_name, content_hash)
VALUES (%s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""
_SELECT_BRAND_HASH = "SELECT content_hash FROM canonical_brands WHERE id = %s"

_INSERT_ORGANIZATION = """
INSERT INTO canonical_organizations (id, canonical_name, content_hash)
VALUES (%s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""
_SELECT_ORGANIZATION_HASH = "SELECT content_hash FROM canonical_organizations WHERE id = %s"

_INSERT_BRAND_ALIAS = """
INSERT INTO canonical_brand_aliases
    (brand_id, alias_id, alias_class, name, notes, content_hash)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (brand_id, alias_id) DO NOTHING
"""
_SELECT_BRAND_ALIAS_HASH = (
    "SELECT content_hash FROM canonical_brand_aliases WHERE brand_id = %s AND alias_id = %s"
)

_INSERT_ORGANIZATION_ALIAS = """
INSERT INTO canonical_organization_aliases
    (organization_id, alias_id, alias_class, name, notes, content_hash)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (organization_id, alias_id) DO NOTHING
"""
_SELECT_ORGANIZATION_ALIAS_HASH = (
    "SELECT content_hash FROM canonical_organization_aliases "
    "WHERE organization_id = %s AND alias_id = %s"
)

_INSERT_BOAT_MODEL = """
INSERT INTO canonical_boat_models (id, canonical_name, first_built, last_built, content_hash)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""
_SELECT_BOAT_MODEL_HASH = "SELECT content_hash FROM canonical_boat_models WHERE id = %s"

_INSERT_BOAT_MODEL_ALIAS = """
INSERT INTO canonical_boat_model_aliases
    (boat_model_id, alias_id, alias_class, name, notes, content_hash)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (boat_model_id, alias_id) DO NOTHING
"""
_SELECT_BOAT_MODEL_ALIAS_HASH = (
    "SELECT content_hash FROM canonical_boat_model_aliases "
    "WHERE boat_model_id = %s AND alias_id = %s"
)

_INSERT_BRAND_MODEL_REL = """
INSERT INTO canonical_brand_model_relationships
    (id, brand_id, boat_model_id, first_year, last_year,
     hull_number_from, hull_number_to, market, notes, content_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""
_SELECT_BRAND_MODEL_REL_HASH = (
    "SELECT content_hash FROM canonical_brand_model_relationships WHERE id = %s"
)

_INSERT_BOAT_DESIGN = """
INSERT INTO canonical_boat_designs
    (id, boat_model_id, generation, designers, number_built,
     baseline, named_variants, design_options, quality, content_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""
_SELECT_BOAT_DESIGN_HASH = "SELECT content_hash FROM canonical_boat_designs WHERE id = %s"

_INSERT_ORG_DESIGN_REL = """
INSERT INTO canonical_organization_design_relationships
    (id, organization_id, boat_design_id, role, first_year, last_year,
     hull_number_from, hull_number_to, market, notes, content_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""
_SELECT_ORG_DESIGN_REL_HASH = (
    "SELECT content_hash FROM canonical_organization_design_relationships WHERE id = %s"
)

_INSERT_EVIDENCE_LINK = """
INSERT INTO canonical_admission_evidence_links
    (link_id, entity_kind, entity_id, observation_id, evidence_id, notes, content_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (link_id) DO NOTHING
"""
_SELECT_EVIDENCE_LINK_HASH = (
    "SELECT content_hash FROM canonical_admission_evidence_links WHERE link_id = %s"
)

_SELECT_BOAT_DESIGNS_FOR_MODEL = "SELECT id FROM canonical_boat_designs WHERE boat_model_id = %s"

# Fixed, explicit per-kind existence check for CanonicalEvidenceLink targets.
# Never build SQL from caller-controlled table/column names: entity_kind is
# restricted by CanonicalEvidenceLink.__post_init__ to exactly these six
# values, so this mapping is total over every value that can reach here.
# A canonical ID that exists only under a *different* kind's table correctly
# fails to satisfy the link (each kind queries its own distinct table).
_EVIDENCE_LINK_TARGET_EXISTENCE_SQL: dict[SubjectKind, str] = {
    SubjectKind.BRAND: "SELECT 1 FROM canonical_brands WHERE id = %s",
    SubjectKind.ORGANIZATION: "SELECT 1 FROM canonical_organizations WHERE id = %s",
    SubjectKind.BOAT_MODEL: "SELECT 1 FROM canonical_boat_models WHERE id = %s",
    SubjectKind.BOAT_DESIGN: "SELECT 1 FROM canonical_boat_designs WHERE id = %s",
    SubjectKind.BRAND_MODEL_RELATIONSHIP: (
        "SELECT 1 FROM canonical_brand_model_relationships WHERE id = %s"
    ),
    SubjectKind.ORGANIZATION_DESIGN_RELATIONSHIP: (
        "SELECT 1 FROM canonical_organization_design_relationships WHERE id = %s"
    ),
}


# ---------------------------------------------------------------------------
# Generic race-safe upsert
# ---------------------------------------------------------------------------


def _upsert_row(
    cur: Any,
    insert_sql: str,
    select_hash_sql: str,
    select_params: Sequence[Any],
    insert_params: Sequence[Any],
    content_hash: str,
    conflict_label: str,
) -> bool:
    """Race-safe insert of one immutable row, keyed by its own primary key.

    Returns True if a new row was inserted, False if an identical row already
    existed (idempotent no-op). Raises CanonicalPersistenceConflictError if a
    row with the same key already exists with different content.
    """
    from psycopg.types.json import Jsonb

    adapted = [Jsonb(p) if isinstance(p, dict | list) else p for p in insert_params]
    cur.execute(insert_sql, adapted)
    if cur.rowcount > 0:
        return True
    cur.execute(select_hash_sql, list(select_params))
    existing = cur.fetchone()
    if existing is None or existing[0] != content_hash:
        raise CanonicalPersistenceConflictError(
            f"{conflict_label} already persisted with a different content hash."
        )
    return False


def _alias_from_dict(d: Mapping[str, Any]) -> IdentityAlias:
    return IdentityAlias(
        id=d["id"], alias_class=AliasClass(d["alias_class"]), name=d["name"], notes=d.get("notes")
    )


# ---------------------------------------------------------------------------
# Per-entity upsert
# ---------------------------------------------------------------------------


def _upsert_brand(cur: Any, brand: Brand) -> bool:
    content_hash = fingerprint_brand_row(brand)
    any_new = _upsert_row(
        cur,
        _INSERT_BRAND,
        _SELECT_BRAND_HASH,
        [brand.id],
        brand_row_params(brand, content_hash),
        content_hash,
        f"Brand {brand.id!r}",
    )
    for alias in brand.aliases:
        any_new |= _upsert_alias(
            cur, _INSERT_BRAND_ALIAS, _SELECT_BRAND_ALIAS_HASH, brand.id, alias, "Brand alias"
        )
    return any_new


def _upsert_organization(cur: Any, organization: Organization) -> bool:
    content_hash = fingerprint_organization_row(organization)
    any_new = _upsert_row(
        cur,
        _INSERT_ORGANIZATION,
        _SELECT_ORGANIZATION_HASH,
        [organization.id],
        organization_row_params(organization, content_hash),
        content_hash,
        f"Organization {organization.id!r}",
    )
    for alias in organization.aliases:
        any_new |= _upsert_alias(
            cur,
            _INSERT_ORGANIZATION_ALIAS,
            _SELECT_ORGANIZATION_ALIAS_HASH,
            organization.id,
            alias,
            "Organization alias",
        )
    return any_new


def _upsert_alias(
    cur: Any,
    insert_sql: str,
    select_hash_sql: str,
    owner_id: str,
    alias: IdentityAlias,
    label: str,
) -> bool:
    content_hash = fingerprint_alias(alias)
    return _upsert_row(
        cur,
        insert_sql,
        select_hash_sql,
        [owner_id, alias.id],
        alias_row_params(owner_id, alias, content_hash),
        content_hash,
        f"{label} ({owner_id!r}, {alias.id!r})",
    )


def _upsert_boat_model(cur: Any, payload: Mapping[str, Any]) -> bool:
    model_id = payload["id"]
    content_hash = fingerprint_boat_model_row(payload)
    any_new = _upsert_row(
        cur,
        _INSERT_BOAT_MODEL,
        _SELECT_BOAT_MODEL_HASH,
        [model_id],
        boat_model_row_params(payload, content_hash),
        content_hash,
        f"BoatModel {model_id!r}",
    )
    for alias_dict in payload.get("aliases", []):
        any_new |= _upsert_alias(
            cur,
            _INSERT_BOAT_MODEL_ALIAS,
            _SELECT_BOAT_MODEL_ALIAS_HASH,
            model_id,
            _alias_from_dict(alias_dict),
            "BoatModel alias",
        )
    for rel in payload.get("brand_relationships", []):
        full_rel = brand_model_relationship_standalone_dict(rel, model_id)
        rel_hash = fingerprint_brand_model_relationship(full_rel)
        any_new |= _upsert_row(
            cur,
            _INSERT_BRAND_MODEL_REL,
            _SELECT_BRAND_MODEL_REL_HASH,
            [full_rel["id"]],
            brand_model_relationship_row_params(full_rel, rel_hash),
            rel_hash,
            f"BrandModelRelationship {full_rel['id']!r}",
        )
    return any_new


def _upsert_boat_design(cur: Any, payload: Mapping[str, Any]) -> bool:
    design_id = payload["id"]
    content_hash = fingerprint_boat_design_row(payload)
    any_new = _upsert_row(
        cur,
        _INSERT_BOAT_DESIGN,
        _SELECT_BOAT_DESIGN_HASH,
        [design_id],
        boat_design_row_params(payload, content_hash),
        content_hash,
        f"BoatDesign {design_id!r}",
    )
    builders = payload.get("relationships", {}).get("builders", [])
    for builder in builders:
        full_rel = organization_design_relationship_standalone_dict(builder, design_id)
        rel_hash = fingerprint_organization_design_relationship(full_rel)
        any_new |= _upsert_row(
            cur,
            _INSERT_ORG_DESIGN_REL,
            _SELECT_ORG_DESIGN_REL_HASH,
            [full_rel["id"]],
            organization_design_relationship_row_params(full_rel, rel_hash),
            rel_hash,
            f"OrganizationDesignRelationship {full_rel['id']!r}",
        )
    return any_new


def _check_evidence_link_target_exists(cur: Any, link: CanonicalEvidenceLink) -> None:
    """Verify link.entity_id addresses a real row of kind link.entity_kind.

    Runs inside the same transaction/cursor as every other upsert in this
    admission, so a target Brand/Organization/BoatModel/BoatDesign/
    relationship created earlier in the *same* admission is already visible
    here (uncommitted writes are visible to later statements in one
    PostgreSQL transaction). A target ID that only exists under a different
    entity_kind's table does not satisfy the link.
    """
    exists_sql = _EVIDENCE_LINK_TARGET_EXISTENCE_SQL[link.entity_kind]
    cur.execute(exists_sql, [link.entity_id])
    if cur.fetchone() is None:
        raise CanonicalReferenceError(
            f"CanonicalEvidenceLink {link.link_id!r} references "
            f"{link.entity_kind!s} {link.entity_id!r}, which does not exist "
            "in the canonical identity graph."
        )


def _check_boat_model_design_consistency(cur: Any, payload: Mapping[str, Any]) -> None:
    """Verify a caller-asserted boat_design_ids projection matches the actual
    canonical BoatDesign graph for this BoatModel, order-independent.

    Must run only after every BoatDesign in the same admission has already
    been upserted, so a same-admission BoatDesign is visible in the query.
    Comparing as sets means reordering the declared list never causes a
    false mismatch. Also catches a BoatDesign that silently belongs to a
    *different* BoatModel: such a design is absent from this model's actual
    set even though its ID might appear in the declared list.
    """
    model_id = payload["id"]
    declared = frozenset(payload.get("boat_design_ids", []))
    cur.execute(_SELECT_BOAT_DESIGNS_FOR_MODEL, [model_id])
    actual = frozenset(row[0] for row in cur.fetchall())
    if declared != actual:
        raise CanonicalReferenceError(
            f"BoatModel {model_id!r} boat_design_ids {sorted(declared)!r} does not "
            f"match the canonical BoatDesign graph {sorted(actual)!r}."
        )


def _upsert_evidence_link(cur: Any, link: CanonicalEvidenceLink) -> bool:
    _check_evidence_link_target_exists(cur, link)
    content_hash = fingerprint_evidence_link(link)
    return _upsert_row(
        cur,
        _INSERT_EVIDENCE_LINK,
        _SELECT_EVIDENCE_LINK_HASH,
        [link.link_id],
        (
            link.link_id,
            str(link.entity_kind),
            link.entity_id,
            link.observation_id,
            link.evidence_id,
            link.notes,
            content_hash,
        ),
        content_hash,
        f"CanonicalEvidenceLink {link.link_id!r}",
    )


# ---------------------------------------------------------------------------
# Pre-persistence schema validation (fail closed, before any DB mutation)
# ---------------------------------------------------------------------------


def _validate_admission(admission: CanonicalIdentityAdmission, registry: ContractRegistry) -> None:
    """Validate every payload against its accepted schema.

    Raises jsonschema.ValidationError on the first invalid payload. No
    database call has been made by the time this returns or raises.
    """
    brand_validator = registry.validator_by_name("BRAND_SCHEMA.v0.1.json")
    for brand in admission.brands:
        brand_validator.validate(brand_to_schema_dict(brand))

    organization_validator = registry.validator_by_name("ORGANIZATION_SCHEMA.v0.1.json")
    for organization in admission.organizations:
        organization_validator.validate(organization_to_schema_dict(organization))

    boat_model_validator = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
    brand_rel_validator = registry.validator_by_name("BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1.json")
    for payload in admission.boat_models:
        boat_model_validator.validate(dict(payload))
        for rel in payload.get("brand_relationships", []):
            brand_rel_validator.validate(
                brand_model_relationship_standalone_dict(rel, payload["id"])
            )

    boat_design_validator = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json")
    org_rel_validator = registry.validator_by_name(
        "ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json"
    )
    for payload in admission.boat_designs:
        boat_design_validator.validate(dict(payload))
        builders = payload.get("relationships", {}).get("builders", [])
        for builder in builders:
            org_rel_validator.validate(
                organization_design_relationship_standalone_dict(builder, payload["id"])
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def import_canonical_identity_admission(
    conn: Any,
    admission: CanonicalIdentityAdmission,
    registry: ContractRegistry,
) -> CanonicalImportResult:
    """Atomically admit a CanonicalIdentityAdmission into PostgreSQL.

    Returns CanonicalImportResult with status IMPORTED, ALREADY_IMPORTED, or
    CONFLICT:

    - IMPORTED: at least one row was newly persisted; nothing conflicted.
    - ALREADY_IMPORTED: every row already existed with identical content; the
      admission is a no-op and no duplicates were created.
    - CONFLICT: some canonical ID already exists with different content. The
      full admission is rolled back.

    Raises jsonschema.ValidationError if any payload fails schema validation
    (before any database mutation).

    Raises CanonicalReferenceError if the admission references a canonical
    Brand/Organization/BoatModel/BoatDesign ID or a research
    observation/evidence ID that does not exist, if a CanonicalEvidenceLink's
    (entity_kind, entity_id) does not address a real canonical row of that
    exact kind, or if a BoatModel's boat_design_ids projection does not match
    the actual canonical BoatDesign graph admitted for it. The triggering
    transaction is rolled back before this is raised.

    Performs no identity resolution, no automatic ID minting, and no
    automatic FieldResolution.
    """
    from psycopg.errors import ForeignKeyViolation

    _validate_admission(admission, registry)

    any_new = False
    try:
        with conn.transaction(), conn.cursor() as cur:
            for brand in admission.brands:
                any_new |= _upsert_brand(cur, brand)
            for organization in admission.organizations:
                any_new |= _upsert_organization(cur, organization)
            for boat_model in admission.boat_models:
                any_new |= _upsert_boat_model(cur, boat_model)
            for boat_design in admission.boat_designs:
                any_new |= _upsert_boat_design(cur, boat_design)
            for boat_model in admission.boat_models:
                _check_boat_model_design_consistency(cur, boat_model)
            for link in admission.evidence_links:
                any_new |= _upsert_evidence_link(cur, link)
    except CanonicalPersistenceConflictError as exc:
        return CanonicalImportResult(status=CanonicalImportStatus.CONFLICT, detail=str(exc))
    except ForeignKeyViolation as exc:
        raise CanonicalReferenceError(
            "Canonical identity admission references a canonical entity ID or "
            f"research observation/evidence ID that does not exist: {exc}"
        ) from exc

    return CanonicalImportResult(
        status=CanonicalImportStatus.IMPORTED if any_new else CanonicalImportStatus.ALREADY_IMPORTED
    )
