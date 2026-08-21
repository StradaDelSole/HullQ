"""Deterministic semantic fingerprinting for canonical identity rows — SLICE-0016.

Reuses the SHA-256-of-canonical-JSON approach from persistence.fingerprint
(SLICE-0013). Each canonical row (Brand, Organization, alias, BoatModel,
BoatDesign, relationship, evidence link) is fingerprinted independently and
keyed by its own stable caller-supplied ID, so reordering a semantically
unordered collection (aliases, relationships, evidence links) on repeat
admission never produces a different fingerprint for an unrelated row.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hullq.domain.identity import Brand, IdentityAlias, Organization
from hullq.persistence.fingerprint import fingerprint_dict
from hullq.persistence.identity_types import CanonicalEvidenceLink

__all__ = [
    "fingerprint_alias",
    "fingerprint_boat_design_row",
    "fingerprint_boat_model_row",
    "fingerprint_brand_model_relationship",
    "fingerprint_brand_row",
    "fingerprint_evidence_link",
    "fingerprint_organization_design_relationship",
    "fingerprint_organization_row",
]


def fingerprint_alias(alias: IdentityAlias) -> str:
    """Fingerprint of one entity-scoped alias's content.

    Excludes ``id`` and the owning entity: those form the row's stable
    identity (the PostgreSQL primary key), not its comparable content.
    """
    return fingerprint_dict(
        {"alias_class": str(alias.alias_class), "name": alias.name, "notes": alias.notes}
    )


def fingerprint_brand_row(brand: Brand) -> str:
    """Fingerprint of one canonical_brands row's content (excludes id)."""
    return fingerprint_dict({"canonical_name": brand.canonical_name})


def fingerprint_organization_row(organization: Organization) -> str:
    """Fingerprint of one canonical_organizations row's content (excludes id)."""
    return fingerprint_dict({"canonical_name": organization.canonical_name})


def fingerprint_boat_model_row(payload: Mapping[str, Any]) -> str:
    """Fingerprint of one canonical_boat_models row's content.

    Covers only the columns actually stored on that row. ``aliases``,
    ``brand_relationships`` and ``boat_design_ids`` are independently
    fingerprinted per child row and must not be folded in here, or reordering
    those unordered collections would falsely change this fingerprint.
    """
    return fingerprint_dict(
        {
            "canonical_name": payload["canonical_name"],
            "first_built": payload.get("first_built"),
            "last_built": payload.get("last_built"),
        }
    )


def fingerprint_boat_design_row(payload: Mapping[str, Any]) -> str:
    """Fingerprint of one canonical_boat_designs row's full technical content.

    Includes boat_model_id: a later admission of the same BoatDesign ID under
    a different BoatModel is genuine conflicting content, not a no-op repeat.
    Excludes relationships.builders, which is independently fingerprinted per
    extracted canonical_organization_design_relationships row.
    """
    return fingerprint_dict(
        {
            "boat_model_id": payload["boat_model_id"],
            "generation": payload["generation"],
            "designers": payload["relationships"]["designers"],
            "number_built": payload["relationships"]["number_built"],
            "baseline": payload["baseline"],
            "named_variants": payload["named_variants"],
            "design_options": payload["design_options"],
            "quality": payload["quality"],
        }
    )


def fingerprint_brand_model_relationship(rel: Mapping[str, Any]) -> str:
    """Fingerprint of one canonical_brand_model_relationships row's content.

    *rel* must already contain the resolved ``boat_model_id`` (supplied by
    the importer from the enclosing BoatModel, not trusted from the embedded
    payload shape).
    """
    return fingerprint_dict(
        {
            "brand_id": rel["brand_id"],
            "boat_model_id": rel["boat_model_id"],
            "first_year": rel.get("first_year"),
            "last_year": rel.get("last_year"),
            "hull_number_from": rel.get("hull_number_from"),
            "hull_number_to": rel.get("hull_number_to"),
            "market": rel.get("market"),
            "notes": rel.get("notes"),
        }
    )


def fingerprint_organization_design_relationship(rel: Mapping[str, Any]) -> str:
    """Fingerprint of one canonical_organization_design_relationships row's content.

    *rel* must already contain the resolved ``boat_design_id``.
    """
    return fingerprint_dict(
        {
            "organization_id": rel["organization_id"],
            "boat_design_id": rel["boat_design_id"],
            "role": rel["role"],
            "first_year": rel.get("first_year"),
            "last_year": rel.get("last_year"),
            "hull_number_from": rel.get("hull_number_from"),
            "hull_number_to": rel.get("hull_number_to"),
            "market": rel.get("market"),
            "notes": rel.get("notes"),
        }
    )


def fingerprint_evidence_link(link: CanonicalEvidenceLink) -> str:
    """Fingerprint of one canonical_admission_evidence_links row's content."""
    return fingerprint_dict(
        {
            "entity_kind": str(link.entity_kind),
            "entity_id": link.entity_id,
            "observation_id": link.observation_id,
            "evidence_id": link.evidence_id,
            "notes": link.notes,
        }
    )
