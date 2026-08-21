"""Conversion helpers: domain objects / payload dicts <-> schema-validation
shapes and PostgreSQL row parameters — SLICE-0016.

Pure Python, no database dependencies. Mirrors the persistence.schema module
from SLICE-0013.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hullq.domain.identity import Brand, IdentityAlias, Organization

__all__ = [
    "alias_to_schema_dict",
    "brand_model_relationship_standalone_dict",
    "brand_to_schema_dict",
    "organization_design_relationship_standalone_dict",
    "organization_to_schema_dict",
]


# ---------------------------------------------------------------------------
# Domain object -> accepted-schema-shaped dict (for pre-persistence validation)
# ---------------------------------------------------------------------------


def alias_to_schema_dict(alias: IdentityAlias) -> dict[str, Any]:
    """IdentityAlias -> IDENTITY_ALIAS_SCHEMA.v0.1 shape."""
    d: dict[str, Any] = {"id": alias.id, "alias_class": str(alias.alias_class), "name": alias.name}
    if alias.notes is not None:
        d["notes"] = alias.notes
    return d


def brand_to_schema_dict(brand: Brand) -> dict[str, Any]:
    """Brand -> BRAND_SCHEMA.v0.1 shape."""
    return {
        "schema_version": "0.1",
        "id": brand.id,
        "canonical_name": brand.canonical_name,
        "aliases": [alias_to_schema_dict(a) for a in brand.aliases],
    }


def organization_to_schema_dict(organization: Organization) -> dict[str, Any]:
    """Organization -> ORGANIZATION_SCHEMA.v0.1 shape."""
    return {
        "schema_version": "0.1",
        "id": organization.id,
        "canonical_name": organization.canonical_name,
        "aliases": [alias_to_schema_dict(a) for a in organization.aliases],
    }


def brand_model_relationship_standalone_dict(
    embedded: Mapping[str, Any], boat_model_id: str
) -> dict[str, Any]:
    """Embedded BoatModel.brand_relationships[i] + resolved boat_model_id ->
    standalone BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1 shape.
    """
    return {**dict(embedded), "boat_model_id": boat_model_id}


def organization_design_relationship_standalone_dict(
    embedded: Mapping[str, Any], boat_design_id: str
) -> dict[str, Any]:
    """Embedded BoatDesign.relationships.builders[i] + resolved boat_design_id ->
    standalone ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1 shape.
    """
    return {**dict(embedded), "boat_design_id": boat_design_id}


# ---------------------------------------------------------------------------
# PostgreSQL row parameter helpers
# ---------------------------------------------------------------------------


def brand_row_params(brand: Brand, content_hash: str) -> tuple[Any, ...]:
    return (brand.id, brand.canonical_name, content_hash)


def organization_row_params(organization: Organization, content_hash: str) -> tuple[Any, ...]:
    return (organization.id, organization.canonical_name, content_hash)


def alias_row_params(owner_id: str, alias: IdentityAlias, content_hash: str) -> tuple[Any, ...]:
    return (owner_id, alias.id, str(alias.alias_class), alias.name, alias.notes, content_hash)


def boat_model_row_params(payload: Mapping[str, Any], content_hash: str) -> tuple[Any, ...]:
    return (
        payload["id"],
        payload["canonical_name"],
        payload.get("first_built"),
        payload.get("last_built"),
        content_hash,
    )


def boat_design_row_params(payload: Mapping[str, Any], content_hash: str) -> tuple[Any, ...]:
    relationships = payload["relationships"]
    return (
        payload["id"],
        payload["boat_model_id"],
        payload["generation"],
        relationships["designers"],
        relationships["number_built"],
        payload["baseline"],
        payload["named_variants"],
        payload["design_options"],
        payload["quality"],
        content_hash,
    )


def brand_model_relationship_row_params(
    rel: Mapping[str, Any], content_hash: str
) -> tuple[Any, ...]:
    return (
        rel["id"],
        rel["brand_id"],
        rel["boat_model_id"],
        rel.get("first_year"),
        rel.get("last_year"),
        rel.get("hull_number_from"),
        rel.get("hull_number_to"),
        rel.get("market"),
        rel.get("notes"),
        content_hash,
    )


def organization_design_relationship_row_params(
    rel: Mapping[str, Any], content_hash: str
) -> tuple[Any, ...]:
    return (
        rel["id"],
        rel["organization_id"],
        rel["boat_design_id"],
        rel["role"],
        rel.get("first_year"),
        rel.get("last_year"),
        rel.get("hull_number_from"),
        rel.get("hull_number_to"),
        rel.get("market"),
        rel.get("notes"),
        content_hash,
    )
