"""Unit tests for canonical identity persistence using mock connections — SLICE-0016.

No PostgreSQL required; no network access occurs. Covers: dataclass
validation, fingerprint determinism, schema-dict conversion helpers, row
param helpers, the generic race-safe upsert helper, and
import_canonical_identity_admission control flow (validation-before-DB,
idempotent/conflict/reference-error paths) against mocked cursors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from jsonschema import ValidationError

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
from hullq.persistence.identity_importer import (
    _upsert_row,
    import_canonical_identity_admission,
)
from hullq.persistence.identity_schema import (
    alias_row_params,
    alias_to_schema_dict,
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
    CanonicalImportStatus,
    CanonicalPersistenceConflictError,
    CanonicalReferenceError,
)

SPECS = Path(__file__).resolve().parents[2] / "specs"


@pytest.fixture(scope="module")
def registry() -> ContractRegistry:
    return ContractRegistry.from_directory(SPECS)


# ---------------------------------------------------------------------------
# Shared builders
# ---------------------------------------------------------------------------


def _alias(alias_id: str = "A1", name: str = "Alias", notes: str | None = None) -> IdentityAlias:
    return IdentityAlias(id=alias_id, alias_class=AliasClass.COMMON_NAME, name=name, notes=notes)


def _brand(brand_id: str = "BR_1", name: str = "Example", aliases: tuple = ()) -> Brand:
    return Brand(id=brand_id, canonical_name=name, aliases=aliases)


def _organization(
    org_id: str = "ORG_1", name: str = "Example Works", aliases: tuple = ()
) -> Organization:
    return Organization(id=org_id, canonical_name=name, aliases=aliases)


def _boat_model_payload(model_id: str = "BM_1", **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "0.2",
        "id": model_id,
        "canonical_name": "Example 36",
        "aliases": [],
        "brand_relationships": [],
        "first_built": 1988,
        "last_built": 1998,
        "boat_design_ids": [],
    }
    payload.update(overrides)
    return payload


def _sparse_baseline() -> dict[str, Any]:
    return {
        "dimensions": dict.fromkeys(
            (
                "loa_m",
                "lwl_m",
                "beam_m",
                "draft_min_m",
                "draft_max_m",
                "displacement_kg",
                "ballast_kg",
                "sail_area_m2",
            )
        ),
        "configuration": {
            "hull_configuration": "unknown",
            "hull_count": None,
            "keel_type": "unknown",
            "keel_subtype": None,
            "rudder_type": "unknown",
            "rudder_count": None,
            "skeg_type": "unknown",
            "rig_type": "unknown",
            "daggerboard_count": None,
            "centerboard_count": None,
        },
        "construction": {"hull_material": "unknown", "construction_method": None},
        "cruising": dict.fromkeys(
            (
                "engine_make",
                "engine_model",
                "engine_type",
                "engine_power_hp",
                "fuel_capacity_l",
                "water_capacity_l",
                "headroom_m",
                "bridgedeck_clearance_m",
            )
        ),
        "ratio_input_basis": {"displacement_basis": "unknown", "sail_area_basis": "unknown"},
    }


def _boat_design_payload(
    design_id: str = "BD_1", boat_model_id: str = "BM_1", builders: list | None = None
) -> dict[str, Any]:
    return {
        "schema_version": "0.5",
        "id": design_id,
        "boat_model_id": boat_model_id,
        "generation": {
            "label": None,
            "sequence": None,
            "aliases": [],
            "first_built": None,
            "last_built": None,
            "hull_number_from": None,
            "hull_number_to": None,
            "boundary_confidence": "unknown",
        },
        "relationships": {"builders": builders or [], "designers": [], "number_built": None},
        "baseline": _sparse_baseline(),
        "named_variants": [],
        "design_options": [],
        "quality": {"status": "needs_review", "confidence": "unknown", "notes": None},
    }


def _make_mock_conn(
    fetchone_return: Any = None, rowcount: int = 1, fetchall_return: Any = None
) -> MagicMock:
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.rowcount = rowcount
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    return mock_conn


# ---------------------------------------------------------------------------
# CanonicalEvidenceLink validation
# ---------------------------------------------------------------------------


class TestCanonicalEvidenceLink:
    def test_requires_exactly_one_reference_neither_set_raises(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            CanonicalEvidenceLink(link_id="L1", entity_kind=SubjectKind.BRAND, entity_id="BR_1")

    def test_requires_exactly_one_reference_both_set_raises(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            CanonicalEvidenceLink(
                link_id="L1",
                entity_kind=SubjectKind.BRAND,
                entity_id="BR_1",
                observation_id="OBS-1",
                evidence_id="EV-1",
            )

    def test_observation_only_is_valid(self) -> None:
        link = CanonicalEvidenceLink(
            link_id="L1", entity_kind=SubjectKind.BRAND, entity_id="BR_1", observation_id="OBS-1"
        )
        assert link.observation_id == "OBS-1"
        assert link.evidence_id is None

    def test_empty_link_id_raises(self) -> None:
        with pytest.raises(ValueError, match="link_id"):
            CanonicalEvidenceLink(
                link_id="", entity_kind=SubjectKind.BRAND, entity_id="BR_1", observation_id="OBS-1"
            )

    def test_empty_entity_id_raises(self) -> None:
        with pytest.raises(ValueError, match="entity_id"):
            CanonicalEvidenceLink(
                link_id="L1", entity_kind=SubjectKind.BRAND, entity_id="", observation_id="OBS-1"
            )

    def test_non_linkable_entity_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="entity_kind"):
            CanonicalEvidenceLink(
                link_id="L1",
                entity_kind=SubjectKind.NAMED_VARIANT,
                entity_id="NV_1",
                observation_id="OBS-1",
            )

    def test_all_linkable_kinds_accepted(self) -> None:
        for kind in (
            SubjectKind.BRAND,
            SubjectKind.ORGANIZATION,
            SubjectKind.BOAT_MODEL,
            SubjectKind.BOAT_DESIGN,
            SubjectKind.BRAND_MODEL_RELATIONSHIP,
            SubjectKind.ORGANIZATION_DESIGN_RELATIONSHIP,
        ):
            CanonicalEvidenceLink(
                link_id="L1", entity_kind=kind, entity_id="X_1", observation_id="OBS-1"
            )


class TestCanonicalIdentityAdmissionDefaults:
    def test_empty_admission_has_empty_tuples(self) -> None:
        admission = CanonicalIdentityAdmission()
        assert admission.brands == ()
        assert admission.organizations == ()
        assert admission.boat_models == ()
        assert admission.boat_designs == ()
        assert admission.evidence_links == ()


# ---------------------------------------------------------------------------
# Fingerprint determinism (pure Python)
# ---------------------------------------------------------------------------


class TestFingerprints:
    def test_brand_row_stable(self) -> None:
        b = _brand()
        assert fingerprint_brand_row(b) == fingerprint_brand_row(b)

    def test_brand_row_changes_with_name(self) -> None:
        assert fingerprint_brand_row(_brand(name="A")) != fingerprint_brand_row(_brand(name="B"))

    def test_brand_row_independent_of_id(self) -> None:
        # id is the row's stable identity, not its comparable content.
        assert fingerprint_brand_row(_brand("BR_A", "Same")) == fingerprint_brand_row(
            _brand("BR_B", "Same")
        )

    def test_organization_row_changes_with_name(self) -> None:
        assert fingerprint_organization_row(
            _organization(name="A")
        ) != fingerprint_organization_row(_organization(name="B"))

    def test_alias_fingerprint_ignores_id(self) -> None:
        a1 = _alias("A1", name="Same")
        a2 = _alias("A2", name="Same")
        assert fingerprint_alias(a1) == fingerprint_alias(a2)

    def test_alias_fingerprint_changes_with_name(self) -> None:
        assert fingerprint_alias(_alias(name="A")) != fingerprint_alias(_alias(name="B"))

    def test_boat_model_row_changes_with_first_built(self) -> None:
        p1 = _boat_model_payload(first_built=1988)
        p2 = _boat_model_payload(first_built=1990)
        assert fingerprint_boat_model_row(p1) != fingerprint_boat_model_row(p2)

    def test_boat_model_row_ignores_aliases_and_relationships(self) -> None:
        # Those are independently fingerprinted per child row.
        p1 = _boat_model_payload(aliases=[{"id": "A1", "alias_class": "common_name", "name": "X"}])
        p2 = _boat_model_payload(aliases=[])
        assert fingerprint_boat_model_row(p1) == fingerprint_boat_model_row(p2)

    def test_boat_design_row_changes_with_boat_model_id(self) -> None:
        p1 = _boat_design_payload(boat_model_id="BM_A")
        p2 = _boat_design_payload(boat_model_id="BM_B")
        assert fingerprint_boat_design_row(p1) != fingerprint_boat_design_row(p2)

    def test_boat_design_row_changes_with_baseline(self) -> None:
        p1 = _boat_design_payload()
        p2 = _boat_design_payload()
        p2["baseline"]["dimensions"]["loa_m"] = 10.0
        assert fingerprint_boat_design_row(p1) != fingerprint_boat_design_row(p2)

    def test_boat_design_row_ignores_builders(self) -> None:
        p1 = _boat_design_payload(
            builders=[{"id": "ODR_1", "organization_id": "ORG_1", "role": "builder"}]
        )
        p2 = _boat_design_payload(builders=[])
        assert fingerprint_boat_design_row(p1) == fingerprint_boat_design_row(p2)

    def test_brand_model_relationship_fingerprint_changes_with_bounds(self) -> None:
        rel1 = {"brand_id": "BR_1", "boat_model_id": "BM_1", "first_year": 1988, "last_year": None}
        rel2 = {"brand_id": "BR_1", "boat_model_id": "BM_1", "first_year": 1990, "last_year": None}
        assert fingerprint_brand_model_relationship(rel1) != fingerprint_brand_model_relationship(
            rel2
        )

    def test_organization_design_relationship_fingerprint_changes_with_role(self) -> None:
        rel1 = {"organization_id": "ORG_1", "boat_design_id": "BD_1", "role": "builder"}
        rel2 = {"organization_id": "ORG_1", "boat_design_id": "BD_1", "role": "manufacturer"}
        assert fingerprint_organization_design_relationship(
            rel1
        ) != fingerprint_organization_design_relationship(rel2)

    def test_evidence_link_fingerprint_stable(self) -> None:
        link = CanonicalEvidenceLink(
            link_id="L1", entity_kind=SubjectKind.BRAND, entity_id="BR_1", observation_id="OBS-1"
        )
        assert fingerprint_evidence_link(link) == fingerprint_evidence_link(link)

    def test_evidence_link_fingerprint_changes_with_target(self) -> None:
        link1 = CanonicalEvidenceLink(
            link_id="L1", entity_kind=SubjectKind.BRAND, entity_id="BR_1", observation_id="OBS-1"
        )
        link2 = CanonicalEvidenceLink(
            link_id="L1", entity_kind=SubjectKind.BRAND, entity_id="BR_1", observation_id="OBS-2"
        )
        assert fingerprint_evidence_link(link1) != fingerprint_evidence_link(link2)

    def test_fingerprint_is_64_char_hex(self) -> None:
        h = fingerprint_brand_row(_brand())
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# identity_schema.py — conversion helpers (pure Python)
# ---------------------------------------------------------------------------


class TestSchemaDictConversion:
    def test_brand_to_schema_dict_shape(self, registry: ContractRegistry) -> None:
        b = _brand(aliases=(_alias(),))
        d = brand_to_schema_dict(b)
        registry.validator_by_name("BRAND_SCHEMA.v0.1.json").validate(d)

    def test_organization_to_schema_dict_shape(self, registry: ContractRegistry) -> None:
        o = _organization(aliases=(_alias(),))
        d = organization_to_schema_dict(o)
        registry.validator_by_name("ORGANIZATION_SCHEMA.v0.1.json").validate(d)

    def test_alias_to_schema_dict_omits_none_notes(self) -> None:
        a = _alias(notes=None)
        d = alias_to_schema_dict(a)
        assert "notes" not in d

    def test_alias_to_schema_dict_includes_notes_when_present(self) -> None:
        a = _alias(notes="A note")
        d = alias_to_schema_dict(a)
        assert d["notes"] == "A note"

    def test_brand_model_relationship_standalone_dict_injects_boat_model_id(self) -> None:
        embedded = {"id": "BMR_1", "brand_id": "BR_1"}
        full = brand_model_relationship_standalone_dict(embedded, "BM_1")
        assert full["boat_model_id"] == "BM_1"
        assert full["id"] == "BMR_1"

    def test_organization_design_relationship_standalone_dict_injects_boat_design_id(self) -> None:
        embedded = {"id": "ODR_1", "organization_id": "ORG_1", "role": "builder"}
        full = organization_design_relationship_standalone_dict(embedded, "BD_1")
        assert full["boat_design_id"] == "BD_1"
        assert full["role"] == "builder"


class TestRowParams:
    def test_brand_row_params_order(self) -> None:
        b = _brand("BR_X", "Name")
        params = brand_row_params(b, "hash1")
        assert params == ("BR_X", "Name", "hash1")

    def test_organization_row_params_order(self) -> None:
        o = _organization("ORG_X", "Name")
        params = organization_row_params(o, "hash1")
        assert params == ("ORG_X", "Name", "hash1")

    def test_alias_row_params_order(self) -> None:
        a = _alias("A1", name="N", notes="note")
        params = alias_row_params("OWNER_1", a, "hash1")
        assert params == ("OWNER_1", "A1", "common_name", "N", "note", "hash1")

    def test_boat_model_row_params_length(self) -> None:
        params = boat_model_row_params(_boat_model_payload(), "hash1")
        assert len(params) == 5

    def test_boat_design_row_params_length(self) -> None:
        params = boat_design_row_params(_boat_design_payload(), "hash1")
        assert len(params) == 10

    def test_brand_model_relationship_row_params_length(self) -> None:
        rel = {"id": "BMR_1", "brand_id": "BR_1", "boat_model_id": "BM_1"}
        params = brand_model_relationship_row_params(rel, "hash1")
        assert len(params) == 10

    def test_organization_design_relationship_row_params_length(self) -> None:
        rel = {
            "id": "ODR_1",
            "organization_id": "ORG_1",
            "boat_design_id": "BD_1",
            "role": "builder",
        }
        params = organization_design_relationship_row_params(rel, "hash1")
        assert len(params) == 11


# ---------------------------------------------------------------------------
# identity_importer._upsert_row — generic race-safe upsert (mocked cursor)
# ---------------------------------------------------------------------------


class TestUpsertRow:
    def test_new_row_inserted_returns_true(self) -> None:
        cur = MagicMock()
        cur.rowcount = 1
        result = _upsert_row(cur, "INSERT ...", "SELECT ...", ["k"], ["a", "b"], "hash1", "Thing")
        assert result is True
        assert cur.execute.call_count == 1

    def test_existing_same_hash_returns_false(self) -> None:
        cur = MagicMock()
        cur.rowcount = 0
        cur.fetchone.return_value = ("hash1",)
        result = _upsert_row(cur, "INSERT ...", "SELECT ...", ["k"], ["a", "b"], "hash1", "Thing")
        assert result is False
        assert cur.execute.call_count == 2

    def test_existing_different_hash_raises_conflict(self) -> None:
        cur = MagicMock()
        cur.rowcount = 0
        cur.fetchone.return_value = ("different-hash",)
        with pytest.raises(CanonicalPersistenceConflictError):
            _upsert_row(cur, "INSERT ...", "SELECT ...", ["k"], ["a", "b"], "hash1", "Thing")

    def test_missing_row_after_conflict_raises(self) -> None:
        cur = MagicMock()
        cur.rowcount = 0
        cur.fetchone.return_value = None
        with pytest.raises(CanonicalPersistenceConflictError):
            _upsert_row(cur, "INSERT ...", "SELECT ...", ["k"], ["a", "b"], "hash1", "Thing")


# ---------------------------------------------------------------------------
# import_canonical_identity_admission — validation-before-DB and control flow
# ---------------------------------------------------------------------------


class TestImportCanonicalIdentityAdmission:
    def test_invalid_payload_raises_before_touching_connection(
        self, registry: ContractRegistry
    ) -> None:
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = AssertionError("must not touch DB before validation")
        mock_conn.transaction.side_effect = AssertionError("must not touch DB before validation")

        bad_model = _boat_model_payload(manufacturer_name="Not allowed in v0.2")
        admission = CanonicalIdentityAdmission(boat_models=(bad_model,))
        with pytest.raises(ValidationError):
            import_canonical_identity_admission(mock_conn, admission, registry)

    def test_empty_admission_returns_already_imported(self, registry: ContractRegistry) -> None:
        mock_conn = _make_mock_conn()
        result = import_canonical_identity_admission(
            mock_conn, CanonicalIdentityAdmission(), registry
        )
        assert result.status == CanonicalImportStatus.ALREADY_IMPORTED

    def test_new_brand_returns_imported(self, registry: ContractRegistry) -> None:
        mock_conn = _make_mock_conn(rowcount=1)
        admission = CanonicalIdentityAdmission(brands=(_brand(),))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.IMPORTED

    def test_already_present_brand_returns_already_imported(
        self, registry: ContractRegistry
    ) -> None:
        brand = _brand()
        from hullq.persistence.identity_fingerprint import fingerprint_brand_row

        mock_conn = _make_mock_conn(rowcount=0, fetchone_return=(fingerprint_brand_row(brand),))
        admission = CanonicalIdentityAdmission(brands=(brand,))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.ALREADY_IMPORTED

    def test_conflicting_brand_returns_conflict(self, registry: ContractRegistry) -> None:
        mock_conn = _make_mock_conn(rowcount=0, fetchone_return=("some-other-hash",))
        admission = CanonicalIdentityAdmission(brands=(_brand(),))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.CONFLICT
        assert result.detail is not None

    def test_foreign_key_violation_raises_canonical_reference_error(
        self, registry: ContractRegistry
    ) -> None:
        from psycopg.errors import ForeignKeyViolation

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = ForeignKeyViolation("fk violation")

        design = _boat_design_payload(boat_model_id="BM_MISSING")
        admission = CanonicalIdentityAdmission(boat_designs=(design,))
        with pytest.raises(CanonicalReferenceError):
            import_canonical_identity_admission(mock_conn, admission, registry)

    def test_evidence_link_with_evidence_id_only_validates_and_flows_through(
        self, registry: ContractRegistry
    ) -> None:
        mock_conn = _make_mock_conn(rowcount=1)
        link = CanonicalEvidenceLink(
            link_id="L1", entity_kind=SubjectKind.BRAND, entity_id="BR_1", evidence_id="EV-1"
        )
        admission = CanonicalIdentityAdmission(brands=(_brand(),), evidence_links=(link,))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.IMPORTED

    def test_organization_with_aliases_returns_imported(self, registry: ContractRegistry) -> None:
        mock_conn = _make_mock_conn(rowcount=1)
        org = _organization(aliases=(_alias("A1", name="Alt Name"),))
        admission = CanonicalIdentityAdmission(organizations=(org,))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.IMPORTED

    def test_boat_model_with_aliases_and_brand_relationships_returns_imported(
        self, registry: ContractRegistry
    ) -> None:
        mock_conn = _make_mock_conn(rowcount=1)
        bm = _boat_model_payload(
            aliases=[{"id": "A1", "alias_class": "common_name", "name": "Alt"}],
            brand_relationships=[{"id": "BMR_1", "brand_id": "BR_1"}],
        )
        admission = CanonicalIdentityAdmission(boat_models=(bm,))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.IMPORTED

    def test_boat_design_with_builders_returns_imported(self, registry: ContractRegistry) -> None:
        mock_conn = _make_mock_conn(rowcount=1)
        design = _boat_design_payload(
            builders=[{"id": "ODR_1", "organization_id": "ORG_1", "role": "builder"}]
        )
        admission = CanonicalIdentityAdmission(boat_designs=(design,))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.IMPORTED

    def test_already_imported_boat_model_with_alias_and_relationship(
        self, registry: ContractRegistry
    ) -> None:
        """Exercises the ALREADY_IMPORTED (hash-match, no insert) path for the
        nested alias/relationship upsert loops, not just the top-level row.
        """
        from hullq.persistence.identity_fingerprint import (
            fingerprint_alias,
            fingerprint_boat_model_row,
            fingerprint_brand_model_relationship,
        )
        from hullq.persistence.identity_schema import brand_model_relationship_standalone_dict

        bm = _boat_model_payload(
            aliases=[{"id": "A1", "alias_class": "common_name", "name": "Alt"}],
            brand_relationships=[{"id": "BMR_1", "brand_id": "BR_1"}],
        )
        model_hash = fingerprint_boat_model_row(bm)
        alias_hash = fingerprint_alias(
            IdentityAlias(id="A1", alias_class=AliasClass.COMMON_NAME, name="Alt")
        )
        rel_hash = fingerprint_brand_model_relationship(
            brand_model_relationship_standalone_dict(bm["brand_relationships"][0], bm["id"])
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 0  # every INSERT conflicts; verify by hash instead
        mock_cursor.fetchone.side_effect = [(model_hash,), (alias_hash,), (rel_hash,)]

        admission = CanonicalIdentityAdmission(boat_models=(bm,))
        result = import_canonical_identity_admission(mock_conn, admission, registry)
        assert result.status == CanonicalImportStatus.ALREADY_IMPORTED


# ---------------------------------------------------------------------------
# identity_readback.py — mocked-cursor round-trip reconstruction
# ---------------------------------------------------------------------------


class TestReadbackMocked:
    def test_fetch_brand_not_found_returns_none(self) -> None:
        from hullq.persistence.identity_readback import fetch_brand

        mock_conn = _make_mock_conn(fetchone_return=None)
        assert fetch_brand(mock_conn, "BR_MISSING") is None

    def test_fetch_brand_found_reconstructs_with_aliases(self) -> None:
        from hullq.persistence.identity_readback import fetch_brand

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("BR_1", "Example")
        mock_cursor.fetchall.return_value = [("A1", "common_name", "Alt", None)]

        brand = fetch_brand(mock_conn, "BR_1")
        assert brand is not None
        assert brand.id == "BR_1"
        assert brand.canonical_name == "Example"
        assert len(brand.aliases) == 1
        assert brand.aliases[0].id == "A1"
        assert brand.aliases[0].name == "Alt"

    def test_fetch_organization_not_found_returns_none(self) -> None:
        from hullq.persistence.identity_readback import fetch_organization

        mock_conn = _make_mock_conn(fetchone_return=None)
        assert fetch_organization(mock_conn, "ORG_MISSING") is None

    def test_fetch_organization_found_reconstructs(self) -> None:
        from hullq.persistence.identity_readback import fetch_organization

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("ORG_1", "Example Works")
        mock_cursor.fetchall.return_value = []

        org = fetch_organization(mock_conn, "ORG_1")
        assert org is not None
        assert org.canonical_name == "Example Works"
        assert org.aliases == ()

    def test_fetch_boat_model_not_found_returns_none(self) -> None:
        from hullq.persistence.identity_readback import fetch_boat_model

        mock_conn = _make_mock_conn(fetchone_return=None)
        assert fetch_boat_model(mock_conn, "BM_MISSING") is None

    def test_fetch_boat_model_found_reconstructs_full_shape(self) -> None:
        from hullq.persistence.identity_readback import fetch_boat_model

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("BM_1", "Example 36", 1988, 1998)
        mock_cursor.fetchall.side_effect = [
            [("A1", "common_name", "Alt", None)],
            [("BMR_1", "BR_1", None, None, None, None, None, None)],
            [("BD_1",), ("BD_2",)],
        ]

        model = fetch_boat_model(mock_conn, "BM_1")
        assert model is not None
        assert model["schema_version"] == "0.2"
        assert model["id"] == "BM_1"
        assert model["aliases"][0]["id"] == "A1"
        assert model["brand_relationships"][0]["brand_id"] == "BR_1"
        assert model["boat_design_ids"] == ["BD_1", "BD_2"]

    def test_fetch_boat_design_not_found_returns_none(self) -> None:
        from hullq.persistence.identity_readback import fetch_boat_design

        mock_conn = _make_mock_conn(fetchone_return=None)
        assert fetch_boat_design(mock_conn, "BD_MISSING") is None

    def test_fetch_boat_design_found_reconstructs_full_shape(self) -> None:
        from hullq.persistence.identity_readback import fetch_boat_design

        generation = {
            "label": None,
            "sequence": None,
            "aliases": [],
            "first_built": None,
            "last_built": None,
            "hull_number_from": None,
            "hull_number_to": None,
            "boundary_confidence": "unknown",
        }
        baseline = _sparse_baseline()
        quality = {"status": "needs_review", "confidence": "unknown", "notes": None}

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            "BD_1",
            "BM_1",
            generation,
            [],
            None,
            baseline,
            [],
            [],
            quality,
        )
        mock_cursor.fetchall.return_value = [
            ("ODR_1", "ORG_1", "builder", None, None, None, None, None, None)
        ]

        design = fetch_boat_design(mock_conn, "BD_1")
        assert design is not None
        assert design["schema_version"] == "0.5"
        assert design["boat_model_id"] == "BM_1"
        assert design["relationships"]["builders"][0]["organization_id"] == "ORG_1"
        assert design["baseline"] == baseline
        assert design["quality"] == quality

    def test_fetch_brand_model_relationship_not_found_returns_none(self) -> None:
        from hullq.persistence.identity_readback import fetch_brand_model_relationship

        mock_conn = _make_mock_conn(fetchone_return=None)
        assert fetch_brand_model_relationship(mock_conn, "BMR_MISSING") is None

    def test_fetch_brand_model_relationship_found(self) -> None:
        from hullq.persistence.identity_readback import fetch_brand_model_relationship

        mock_conn = _make_mock_conn(
            fetchone_return=("BMR_1", "BR_1", "BM_1", 1988, 1998, None, None, None, None)
        )
        rel = fetch_brand_model_relationship(mock_conn, "BMR_1")
        assert rel is not None
        assert rel.brand_id == "BR_1"
        assert rel.boat_model_id == "BM_1"
        assert rel.first_year == 1988

    def test_fetch_organization_design_relationship_not_found_returns_none(self) -> None:
        from hullq.persistence.identity_readback import fetch_organization_design_relationship

        mock_conn = _make_mock_conn(fetchone_return=None)
        assert fetch_organization_design_relationship(mock_conn, "ODR_MISSING") is None

    def test_fetch_organization_design_relationship_found(self) -> None:
        from hullq.domain.identity import BuilderRole
        from hullq.persistence.identity_readback import fetch_organization_design_relationship

        mock_conn = _make_mock_conn(
            fetchone_return=(
                "ODR_1",
                "ORG_1",
                "BD_1",
                "manufacturer",
                None,
                None,
                None,
                None,
                None,
                None,
            )
        )
        rel = fetch_organization_design_relationship(mock_conn, "ODR_1")
        assert rel is not None
        assert rel.role == BuilderRole.MANUFACTURER
        assert rel.organization_id == "ORG_1"
        assert rel.boat_design_id == "BD_1"

    def test_fetch_evidence_links_for_entity_empty(self) -> None:
        from hullq.persistence.identity_readback import fetch_evidence_links_for_entity

        mock_conn = _make_mock_conn(fetchall_return=[])
        links = fetch_evidence_links_for_entity(mock_conn, SubjectKind.BRAND, "BR_1")
        assert links == ()

    def test_fetch_evidence_links_for_entity_found(self) -> None:
        from hullq.persistence.identity_readback import fetch_evidence_links_for_entity

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("LINK_1", "brand", "BR_1", "OBS-1", None, None),
        ]
        links = fetch_evidence_links_for_entity(mock_conn, SubjectKind.BRAND, "BR_1")
        assert len(links) == 1
        assert links[0].link_id == "LINK_1"
        assert links[0].observation_id == "OBS-1"
