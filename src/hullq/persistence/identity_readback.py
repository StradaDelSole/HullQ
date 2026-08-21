"""Minimal round-trip readback for canonical identity persistence — SLICE-0016.

Provides the smallest read support needed to verify that persisted canonical
identity data survives the round trip losslessly. Not a general query/search
repository API (OQ-009 remains unresolved).
"""

from __future__ import annotations

from typing import Any

from hullq.domain.identity import (
    AliasClass,
    Brand,
    BrandModelRelationship,
    BuilderRole,
    IdentityAlias,
    Organization,
    OrganizationDesignRelationship,
)
from hullq.domain.provenance import SubjectKind
from hullq.persistence.identity_types import CanonicalEvidenceLink

__all__ = [
    "fetch_boat_design",
    "fetch_boat_model",
    "fetch_brand",
    "fetch_brand_model_relationship",
    "fetch_evidence_links_for_entity",
    "fetch_organization",
    "fetch_organization_design_relationship",
]


def _fetch_aliases(
    cur: Any, table: str, owner_column: str, owner_id: str
) -> tuple[IdentityAlias, ...]:
    cur.execute(
        f"SELECT alias_id, alias_class, name, notes FROM {table} "
        f"WHERE {owner_column} = %s ORDER BY alias_id",
        [owner_id],
    )
    rows = cur.fetchall()
    return tuple(
        IdentityAlias(id=r[0], alias_class=AliasClass(r[1]), name=r[2], notes=r[3]) for r in rows
    )


# ---------------------------------------------------------------------------
# Brand / Organization
# ---------------------------------------------------------------------------


def fetch_brand(conn: Any, brand_id: str) -> Brand | None:
    """Reconstruct a Brand (with entity-scoped aliases) from the database, or None."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, canonical_name FROM canonical_brands WHERE id = %s", [brand_id])
        row = cur.fetchone()
        if row is None:
            return None
        aliases = _fetch_aliases(cur, "canonical_brand_aliases", "brand_id", brand_id)
    return Brand(id=row[0], canonical_name=row[1], aliases=aliases)


def fetch_organization(conn: Any, organization_id: str) -> Organization | None:
    """Reconstruct an Organization (with entity-scoped aliases) from the database, or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, canonical_name FROM canonical_organizations WHERE id = %s",
            [organization_id],
        )
        row = cur.fetchone()
        if row is None:
            return None
        aliases = _fetch_aliases(
            cur, "canonical_organization_aliases", "organization_id", organization_id
        )
    return Organization(id=row[0], canonical_name=row[1], aliases=aliases)


# ---------------------------------------------------------------------------
# BoatModel / BoatDesign — reconstructed as accepted-schema-shaped dicts
# ---------------------------------------------------------------------------


def _alias_to_embedded_dict(alias: IdentityAlias) -> dict[str, Any]:
    return {
        "id": alias.id,
        "alias_class": str(alias.alias_class),
        "name": alias.name,
        "notes": alias.notes,
    }


def fetch_boat_model(conn: Any, boat_model_id: str) -> dict[str, Any] | None:
    """Reconstruct a BOAT_MODEL_SCHEMA.v0.2-shaped dict from the database, or None.

    aliases and brand_relationships are returned sorted by their own stable
    id; boat_design_ids is derived from the normalized canonical_boat_designs
    table rather than stored redundantly.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, canonical_name, first_built, last_built "
            "FROM canonical_boat_models WHERE id = %s",
            [boat_model_id],
        )
        row = cur.fetchone()
        if row is None:
            return None

        aliases = _fetch_aliases(
            cur, "canonical_boat_model_aliases", "boat_model_id", boat_model_id
        )

        cur.execute(
            "SELECT id, brand_id, first_year, last_year, hull_number_from, hull_number_to, "
            "market, notes FROM canonical_brand_model_relationships "
            "WHERE boat_model_id = %s ORDER BY id",
            [boat_model_id],
        )
        brand_relationships = [
            {
                "id": r[0],
                "brand_id": r[1],
                "first_year": r[2],
                "last_year": r[3],
                "hull_number_from": r[4],
                "hull_number_to": r[5],
                "market": r[6],
                "notes": r[7],
            }
            for r in cur.fetchall()
        ]

        cur.execute(
            "SELECT id FROM canonical_boat_designs WHERE boat_model_id = %s ORDER BY id",
            [boat_model_id],
        )
        boat_design_ids = [r[0] for r in cur.fetchall()]

    return {
        "schema_version": "0.2",
        "id": row[0],
        "canonical_name": row[1],
        "aliases": [_alias_to_embedded_dict(a) for a in aliases],
        "brand_relationships": brand_relationships,
        "first_built": row[2],
        "last_built": row[3],
        "boat_design_ids": boat_design_ids,
    }


def fetch_boat_design(conn: Any, boat_design_id: str) -> dict[str, Any] | None:
    """Reconstruct a BOAT_DESIGN_SCHEMA.v0.5-shaped dict from the database, or None.

    relationships.builders is returned sorted by its own stable id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, boat_model_id, generation, designers, number_built, "
            "baseline, named_variants, design_options, quality "
            "FROM canonical_boat_designs WHERE id = %s",
            [boat_design_id],
        )
        row = cur.fetchone()
        if row is None:
            return None

        cur.execute(
            "SELECT id, organization_id, role, first_year, last_year, hull_number_from, "
            "hull_number_to, market, notes FROM canonical_organization_design_relationships "
            "WHERE boat_design_id = %s ORDER BY id",
            [boat_design_id],
        )
        builders = [
            {
                "id": r[0],
                "organization_id": r[1],
                "role": r[2],
                "first_year": r[3],
                "last_year": r[4],
                "hull_number_from": r[5],
                "hull_number_to": r[6],
                "market": r[7],
                "notes": r[8],
            }
            for r in cur.fetchall()
        ]

    return {
        "schema_version": "0.5",
        "id": row[0],
        "boat_model_id": row[1],
        "generation": row[2],
        "relationships": {
            "builders": builders,
            "designers": row[3],
            "number_built": row[4],
        },
        "baseline": row[5],
        "named_variants": row[6],
        "design_options": row[7],
        "quality": row[8],
    }


# ---------------------------------------------------------------------------
# Standalone relationships
# ---------------------------------------------------------------------------


def fetch_brand_model_relationship(
    conn: Any, relationship_id: str
) -> BrandModelRelationship | None:
    """Reconstruct a standalone BrandModelRelationship from the database, or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, brand_id, boat_model_id, first_year, last_year, "
            "hull_number_from, hull_number_to, market, notes "
            "FROM canonical_brand_model_relationships WHERE id = %s",
            [relationship_id],
        )
        row = cur.fetchone()
    if row is None:
        return None
    return BrandModelRelationship(
        id=row[0],
        brand_id=row[1],
        boat_model_id=row[2],
        first_year=row[3],
        last_year=row[4],
        hull_number_from=row[5],
        hull_number_to=row[6],
        market=row[7],
        notes=row[8],
    )


def fetch_organization_design_relationship(
    conn: Any, relationship_id: str
) -> OrganizationDesignRelationship | None:
    """Reconstruct a standalone OrganizationDesignRelationship from the database, or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, organization_id, boat_design_id, role, first_year, last_year, "
            "hull_number_from, hull_number_to, market, notes "
            "FROM canonical_organization_design_relationships WHERE id = %s",
            [relationship_id],
        )
        row = cur.fetchone()
    if row is None:
        return None
    return OrganizationDesignRelationship(
        id=row[0],
        organization_id=row[1],
        boat_design_id=row[2],
        role=BuilderRole(row[3]),
        first_year=row[4],
        last_year=row[5],
        hull_number_from=row[6],
        hull_number_to=row[7],
        market=row[8],
        notes=row[9],
    )


# ---------------------------------------------------------------------------
# Provenance linkage
# ---------------------------------------------------------------------------


def fetch_evidence_links_for_entity(
    conn: Any, entity_kind: SubjectKind, entity_id: str
) -> tuple[CanonicalEvidenceLink, ...]:
    """Return every CanonicalEvidenceLink recorded for one canonical entity/relationship,
    ordered by stable link_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT link_id, entity_kind, entity_id, observation_id, evidence_id, notes "
            "FROM canonical_admission_evidence_links "
            "WHERE entity_kind = %s AND entity_id = %s ORDER BY link_id",
            [str(entity_kind), entity_id],
        )
        rows = cur.fetchall()
    return tuple(
        CanonicalEvidenceLink(
            link_id=r[0],
            entity_kind=SubjectKind(r[1]),
            entity_id=r[2],
            observation_id=r[3],
            evidence_id=r[4],
            notes=r[5],
        )
        for r in rows
    )
