"""Contract tests for SLICE-0005 identity schemas.

Verifies that:
- new identity schemas are valid Draft 2020-12 and load without error;
- legacy BOAT_MODEL_SCHEMA.v0.1 and BOAT_DESIGN_SCHEMA.v0.4 remain loadable;
- BoatModel v0.2 and BoatDesign v0.5 validate correct fixtures and reject
  the old free-text manufacturer/builder fields;
- AliasClass enum values match the schema exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from hullq.contracts import ContractRegistry
from hullq.domain.identity import AliasClass

SPECS = Path(__file__).resolve().parents[2] / "specs"


@pytest.fixture(scope="module")
def registry() -> ContractRegistry:
    return ContractRegistry.from_directory(SPECS)


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------


class TestSchemaLoading:
    def test_identity_alias_schema_loads(self, registry: ContractRegistry) -> None:
        assert "IDENTITY_ALIAS_SCHEMA.v0.1.json" in registry.schema_names

    def test_organization_schema_loads(self, registry: ContractRegistry) -> None:
        assert "ORGANIZATION_SCHEMA.v0.1.json" in registry.schema_names

    def test_brand_schema_loads(self, registry: ContractRegistry) -> None:
        assert "BRAND_SCHEMA.v0.1.json" in registry.schema_names

    def test_brand_model_rel_schema_loads(self, registry: ContractRegistry) -> None:
        assert "BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1.json" in registry.schema_names

    def test_org_design_rel_schema_loads(self, registry: ContractRegistry) -> None:
        assert "ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json" in registry.schema_names

    def test_boat_model_v02_loads(self, registry: ContractRegistry) -> None:
        assert "BOAT_MODEL_SCHEMA.v0.2.json" in registry.schema_names

    def test_boat_design_v05_loads(self, registry: ContractRegistry) -> None:
        assert "BOAT_DESIGN_SCHEMA.v0.5.json" in registry.schema_names

    def test_legacy_boat_model_v01_still_loads(self, registry: ContractRegistry) -> None:
        assert "BOAT_MODEL_SCHEMA.v0.1.json" in registry.schema_names

    def test_legacy_boat_design_v04_still_loads(self, registry: ContractRegistry) -> None:
        assert "BOAT_DESIGN_SCHEMA.v0.4.json" in registry.schema_names


# ---------------------------------------------------------------------------
# IdentityAlias contract
# ---------------------------------------------------------------------------

VALID_ALIAS = {
    "id": "A_001",
    "alias_class": "common_name",
    "name": "Example Yachts",
}


class TestIdentityAliasSchema:
    def test_valid_alias_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("IDENTITY_ALIAS_SCHEMA.v0.1.json")
        v.validate(VALID_ALIAS)

    def test_alias_with_notes_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("IDENTITY_ALIAS_SCHEMA.v0.1.json")
        v.validate({**VALID_ALIAS, "notes": "Used in early marketing materials"})

    def test_missing_id_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("IDENTITY_ALIAS_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({"alias_class": "common_name", "name": "X"})

    def test_invalid_alias_class_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("IDENTITY_ALIAS_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({**VALID_ALIAS, "alias_class": "nickname"})

    def test_alias_class_enum_matches_python_enum(self, registry: ContractRegistry) -> None:
        schema = json.loads((SPECS / "IDENTITY_ALIAS_SCHEMA.v0.1.json").read_text(encoding="utf-8"))
        schema_enum = set(schema["properties"]["alias_class"]["enum"])
        python_enum = {m.value for m in AliasClass}
        assert schema_enum == python_enum

    def test_extra_properties_rejected(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("IDENTITY_ALIAS_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({**VALID_ALIAS, "extra_field": "oops"})


# ---------------------------------------------------------------------------
# Organization contract
# ---------------------------------------------------------------------------

VALID_ORGANIZATION = {
    "schema_version": "0.1",
    "id": "ORG_EXAMPLE_001",
    "canonical_name": "Example Works Ltd.",
    "aliases": [],
}


class TestOrganizationSchema:
    def test_valid_org_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_SCHEMA.v0.1.json")
        v.validate(VALID_ORGANIZATION)

    def test_org_with_alias_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_SCHEMA.v0.1.json")
        v.validate(
            {
                **VALID_ORGANIZATION,
                "aliases": [VALID_ALIAS],
            }
        )

    def test_missing_canonical_name_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({"schema_version": "0.1", "id": "ORG_1", "aliases": []})

    def test_wrong_schema_version_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({**VALID_ORGANIZATION, "schema_version": "0.0"})

    def test_manufacturer_name_not_in_schema(self, registry: ContractRegistry) -> None:
        schema = json.loads((SPECS / "ORGANIZATION_SCHEMA.v0.1.json").read_text(encoding="utf-8"))
        assert "manufacturer_name" not in schema.get("properties", {})


# ---------------------------------------------------------------------------
# Brand contract
# ---------------------------------------------------------------------------

VALID_BRAND = {
    "schema_version": "0.1",
    "id": "BR_EXAMPLE_001",
    "canonical_name": "Example",
    "aliases": [],
}


class TestBrandSchema:
    def test_valid_brand_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_SCHEMA.v0.1.json")
        v.validate(VALID_BRAND)

    def test_brand_with_alias_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_SCHEMA.v0.1.json")
        v.validate(
            {
                **VALID_BRAND,
                "aliases": [
                    {
                        "id": "A_BR_1",
                        "alias_class": "trade_name",
                        "name": "Example Yachts",
                    }
                ],
            }
        )

    def test_missing_id_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({"schema_version": "0.1", "canonical_name": "Example", "aliases": []})

    def test_brand_schema_has_no_manufacturer_name(self, registry: ContractRegistry) -> None:
        schema = json.loads((SPECS / "BRAND_SCHEMA.v0.1.json").read_text(encoding="utf-8"))
        assert "manufacturer_name" not in schema.get("properties", {})


# ---------------------------------------------------------------------------
# BrandModelRelationship contract
# ---------------------------------------------------------------------------

VALID_BMR = {
    "id": "BMR_001",
    "brand_id": "BR_EXAMPLE_001",
    "boat_model_id": "BM_EXAMPLE_36",
}


class TestBrandModelRelationshipSchema:
    def test_minimal_rel_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1.json")
        v.validate(VALID_BMR)

    def test_with_year_bounds_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1.json")
        v.validate({**VALID_BMR, "first_year": 1985, "last_year": 1998})

    def test_null_bounds_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1.json")
        v.validate({**VALID_BMR, "first_year": None, "last_year": None})

    def test_missing_brand_id_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({"id": "BMR_X", "boat_model_id": "BM_X"})

    def test_with_market_annotation(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1.json")
        v.validate({**VALID_BMR, "market": "North America"})


# ---------------------------------------------------------------------------
# OrganizationDesignRelationship contract
# ---------------------------------------------------------------------------

VALID_ODR = {
    "id": "ODR_001",
    "organization_id": "ORG_EXAMPLE_001",
    "boat_design_id": "BD_EXAMPLE_36_MK1",
    "role": "builder",
}


class TestOrganizationDesignRelationshipSchema:
    def test_minimal_rel_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json")
        v.validate(VALID_ODR)

    def test_licensed_builder_role_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json")
        v.validate({**VALID_ODR, "role": "licensed_builder"})

    def test_invalid_role_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({**VALID_ODR, "role": "constructor"})

    def test_with_year_and_hull_bounds_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json")
        v.validate(
            {
                **VALID_ODR,
                "first_year": 1988,
                "last_year": 1998,
                "hull_number_from": "001",
                "hull_number_to": "523",
            }
        )

    def test_missing_organization_id_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json")
        with pytest.raises(ValidationError):
            v.validate({"id": "ODR_X", "boat_design_id": "BD_X", "role": "builder"})


# ---------------------------------------------------------------------------
# BoatModel v0.2 — no free-text manufacturer/brand identity fields
# ---------------------------------------------------------------------------

VALID_BM_V02 = {
    "schema_version": "0.2",
    "id": "BM_EXAMPLE_36_A",
    "canonical_name": "Example 36",
    "aliases": [],
    "brand_relationships": [],
    "first_built": 1988,
    "last_built": 1998,
    "boat_design_ids": ["BD_EXAMPLE_36_MK1"],
}


class TestBoatModelV02Schema:
    def test_valid_v02_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
        v.validate(VALID_BM_V02)

    def test_with_typed_alias_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
        v.validate(
            {
                **VALID_BM_V02,
                "aliases": [
                    {"id": "A_BM_1", "alias_class": "common_name", "name": "Example Thirty-Six"}
                ],
            }
        )

    def test_with_brand_relationship_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
        v.validate(
            {
                **VALID_BM_V02,
                "brand_relationships": [VALID_BMR],
            }
        )

    def test_manufacturer_name_field_rejected(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
        with pytest.raises(ValidationError):
            v.validate({**VALID_BM_V02, "manufacturer_name": "Example Yachts"})

    def test_brand_name_field_rejected(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
        with pytest.raises(ValidationError):
            v.validate({**VALID_BM_V02, "brand_name": "Example"})

    def test_plain_string_aliases_field_rejected(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
        with pytest.raises(ValidationError):
            v.validate({**VALID_BM_V02, "aliases": ["Example Thirty-Six"]})

    def test_v01_fixture_fails_v02_schema(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json")
        v01_data = {
            "schema_version": "0.1",
            "id": "BM_EXAMPLE_36_A",
            "canonical_name": "Example 36",
            "manufacturer_name": "Example Yachts",
            "brand_name": "Example",
            "aliases": [],
            "first_built": 1988,
            "last_built": 1998,
            "boat_design_ids": [],
        }
        with pytest.raises(ValidationError):
            v.validate(v01_data)

    def test_legacy_v01_still_validates_against_v01_schema(
        self, registry: ContractRegistry
    ) -> None:
        v = registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.1.json")
        v01_data = {
            "schema_version": "0.1",
            "id": "BM_EXAMPLE_36_A",
            "canonical_name": "Example 36",
            "manufacturer_name": "Example Yachts",
            "brand_name": "Example",
            "aliases": [],
            "first_built": 1988,
            "last_built": 1998,
            "boat_design_ids": ["BD_EXAMPLE_36_MK1"],
        }
        v.validate(v01_data)


# ---------------------------------------------------------------------------
# BoatDesign v0.5 — no free-text builder name
# ---------------------------------------------------------------------------

VALID_BD_V05: dict = {
    "schema_version": "0.5",
    "id": "BD_EXAMPLE_36_MK1",
    "boat_model_id": "BM_EXAMPLE_36_A",
    "generation": {
        "label": "Mk I",
        "sequence": 1,
        "aliases": [],
        "first_built": 1988,
        "last_built": 1998,
        "hull_number_from": None,
        "hull_number_to": None,
        "boundary_confidence": "medium",
    },
    "relationships": {
        "builders": [
            {
                "organization_id": "ORG_EXAMPLE_001",
                "role": "builder",
                "first_year": 1988,
                "last_year": 1998,
                "hull_number_from": None,
                "hull_number_to": None,
                "market": None,
                "notes": None,
            }
        ],
        "designers": [{"name": "Example Designer", "role": "naval_architect"}],
        "number_built": None,
    },
    "baseline": {
        "dimensions": {
            "loa_m": 10.97,
            "lwl_m": 8.9,
            "beam_m": 3.4,
            "draft_min_m": 1.8,
            "draft_max_m": 1.8,
            "displacement_kg": 6500,
            "ballast_kg": 2400,
            "sail_area_m2": 58.0,
        },
        "configuration": {
            "hull_configuration": "monohull",
            "hull_count": 1,
            "keel_type": "fin",
            "keel_subtype": None,
            "rudder_type": "skeg_hung",
            "rudder_count": 1,
            "skeg_type": "partial",
            "rig_type": "masthead_sloop",
            "daggerboard_count": 0,
            "centerboard_count": 0,
        },
        "construction": {
            "hull_material": "grp_fiberglass",
            "construction_method": None,
        },
        "cruising": {
            "engine_make": None,
            "engine_model": None,
            "engine_type": "inboard_diesel",
            "engine_power_hp": 28,
            "fuel_capacity_l": 120,
            "water_capacity_l": 240,
            "headroom_m": 1.9,
            "bridgedeck_clearance_m": None,
        },
        "ratio_input_basis": {
            "displacement_basis": "design",
            "sail_area_basis": "nominal_main_plus_foretriangle",
        },
    },
    "named_variants": [],
    "design_options": [],
    "quality": {
        "status": "partial",
        "confidence": "medium",
        "notes": "Synthetic contract fixture for SLICE-0005.",
    },
}


class TestBoatDesignV05Schema:
    def test_valid_v05_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json")
        v.validate(VALID_BD_V05)

    def test_multiple_builders_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json")
        import copy

        data = copy.deepcopy(VALID_BD_V05)
        data["relationships"]["builders"] = [
            {
                "organization_id": "ORG_A",
                "role": "builder",
                "first_year": 1988,
                "last_year": 1993,
                "hull_number_from": None,
                "hull_number_to": None,
                "market": None,
                "notes": None,
            },
            {
                "organization_id": "ORG_B",
                "role": "licensed_builder",
                "first_year": 1993,
                "last_year": None,
                "hull_number_from": None,
                "hull_number_to": None,
                "market": None,
                "notes": None,
            },
        ]
        v.validate(data)

    def test_empty_builders_passes(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json")
        import copy

        data = copy.deepcopy(VALID_BD_V05)
        data["relationships"]["builders"] = []
        v.validate(data)

    def test_free_text_name_in_builder_rejected(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json")
        import copy

        data = copy.deepcopy(VALID_BD_V05)
        data["relationships"]["builders"] = [
            {
                "name": "Example Yachts",
                "first_built": 1988,
                "last_built": 1998,
                "hull_number_from": None,
                "hull_number_to": None,
            }
        ]
        with pytest.raises(ValidationError):
            v.validate(data)

    def test_invalid_role_fails(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json")
        import copy

        data = copy.deepcopy(VALID_BD_V05)
        data["relationships"]["builders"] = [{"organization_id": "ORG_X", "role": "contractor"}]
        with pytest.raises(ValidationError):
            v.validate(data)

    def test_v04_fixture_fails_v05_schema(self, registry: ContractRegistry) -> None:
        v = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json")
        import copy

        data = copy.deepcopy(VALID_BD_V05)
        data["schema_version"] = "0.4"
        data["relationships"]["builders"] = [
            {
                "name": "Example Yachts",
                "first_built": 1988,
                "last_built": 1998,
                "hull_number_from": None,
                "hull_number_to": None,
            }
        ]
        with pytest.raises(ValidationError):
            v.validate(data)

    def test_legacy_v04_still_validates_against_v04_schema(
        self, registry: ContractRegistry
    ) -> None:
        v = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.4.json")
        import copy

        data = copy.deepcopy(VALID_BD_V05)
        data["schema_version"] = "0.4"
        data["relationships"]["builders"] = [
            {
                "name": "Example Yachts",
                "first_built": 1988,
                "last_built": 1998,
                "hull_number_from": None,
                "hull_number_to": None,
            }
        ]
        v.validate(data)
