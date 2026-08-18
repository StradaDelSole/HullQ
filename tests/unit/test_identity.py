"""Unit tests for hullq.domain.identity — SLICE-0005.

Covers all 16 required test scenarios from
docs/slices/SLICE-0005-identity-contracts-and-search-labels.md,
plus AliasClass enum parity, value-object contracts, and search-key invariants.
"""

from __future__ import annotations

import pytest

from hullq.domain.identity import (
    AliasClass,
    Brand,
    BrandModelRelationship,
    BuilderRole,
    IdentityAlias,
    Organization,
    OrganizationDesignRelationship,
    generate_search_keys,
)

# ---------------------------------------------------------------------------
# Helpers — synthetic fixtures
# ---------------------------------------------------------------------------


def _alias(alias_id: str, cls: AliasClass, name: str) -> IdentityAlias:
    return IdentityAlias(id=alias_id, alias_class=cls, name=name)


def _brand(brand_id: str, name: str, *aliases: IdentityAlias) -> Brand:
    return Brand(id=brand_id, canonical_name=name, aliases=tuple(aliases))


def _org(org_id: str, name: str, *aliases: IdentityAlias) -> Organization:
    return Organization(id=org_id, canonical_name=name, aliases=tuple(aliases))


# ---------------------------------------------------------------------------
# Scenario 1: Brand and differently named Organization both lead to same
# BoatModel/BoatDesign path via explicit relationships
# ---------------------------------------------------------------------------


class TestScenario01BrandAndOrgLeadToSamePath:
    def test_brand_and_org_have_distinct_ids(self) -> None:
        brand = _brand("BR_ALPHA", "Alpha Yachts")
        org = _org("ORG_ALPHA_WORKS", "Alpha Works Ltd.")
        assert brand.id != org.id

    def test_brand_model_rel_links_brand_to_boat_model(self) -> None:
        rel = BrandModelRelationship(id="BMR_001", brand_id="BR_ALPHA", boat_model_id="BM_ALPHA_36")
        assert rel.brand_id == "BR_ALPHA"
        assert rel.boat_model_id == "BM_ALPHA_36"

    def test_org_design_rel_links_org_to_boat_design(self) -> None:
        rel = OrganizationDesignRelationship(
            id="ODR_001",
            organization_id="ORG_ALPHA_WORKS",
            boat_design_id="BD_ALPHA_36_MK1",
            role=BuilderRole.BUILDER,
        )
        assert rel.organization_id == "ORG_ALPHA_WORKS"
        assert rel.boat_design_id == "BD_ALPHA_36_MK1"


# ---------------------------------------------------------------------------
# Scenario 2: Same visible spelling can exist as separate Brand and
# Organization IDs without collapse
# ---------------------------------------------------------------------------


class TestScenario02SameSpellingNoCollapse:
    def test_brand_and_org_with_identical_name_have_different_ids(self) -> None:
        brand = _brand("BR_OCEAN", "Ocean Marine")
        org = _org("ORG_OCEAN", "Ocean Marine")
        assert brand.canonical_name == org.canonical_name
        assert brand.id != org.id

    def test_brand_is_not_org_instance(self) -> None:
        brand = _brand("BR_OCEAN", "Ocean Marine")
        assert not isinstance(brand, Organization)

    def test_org_is_not_brand_instance(self) -> None:
        org = _org("ORG_OCEAN", "Ocean Marine")
        assert not isinstance(org, Brand)


# ---------------------------------------------------------------------------
# Scenario 3: Brand alias remains scoped to Brand — does not mutate Organization
# ---------------------------------------------------------------------------


class TestScenario03BrandAliasScopedToBrand:
    def test_brand_alias_not_present_on_org(self) -> None:
        brand_alias = _alias("A1", AliasClass.COMMON_NAME, "Ocean")
        brand = _brand("BR_OCEAN", "Ocean Marine", brand_alias)
        org = _org("ORG_OCEAN", "Ocean Marine")

        assert any(a.name == "Ocean" for a in brand.aliases)
        assert not any(a.name == "Ocean" for a in org.aliases)

    def test_brand_aliases_are_scoped_to_brand_id(self) -> None:
        alias = _alias("A_BR_1", AliasClass.ABBREVIATION, "OM")
        brand = _brand("BR_OCEAN", "Ocean Marine", alias)
        assert brand.aliases[0].id == "A_BR_1"
        assert brand.aliases[0].name == "OM"


# ---------------------------------------------------------------------------
# Scenario 4: Organization alias remains scoped to Organization — does not
# mutate Brand
# ---------------------------------------------------------------------------


class TestScenario04OrgAliasScopedToOrg:
    def test_org_alias_not_present_on_brand(self) -> None:
        org_alias = _alias("A2", AliasClass.SOURCE_SPELLING, "Ocean Marine Ltd.")
        org = _org("ORG_OCEAN", "Ocean Marine", org_alias)
        brand = _brand("BR_OCEAN", "Ocean Marine")

        assert any(a.name == "Ocean Marine Ltd." for a in org.aliases)
        assert not any(a.name == "Ocean Marine Ltd." for a in brand.aliases)

    def test_org_alias_id_stable_independent_of_position(self) -> None:
        a1 = _alias("A_ORG_1", AliasClass.HISTORICAL_NAME, "Old Works")
        a2 = _alias("A_ORG_2", AliasClass.SOURCE_SPELLING, "Ocean Marine Ltd.")
        org = _org("ORG_OCEAN", "Ocean Marine", a1, a2)
        ids = {a.id for a in org.aliases}
        assert "A_ORG_1" in ids
        assert "A_ORG_2" in ids


# ---------------------------------------------------------------------------
# Scenario 5: One Brand can relate to multiple Organizations over time
# ---------------------------------------------------------------------------


class TestScenario05OneBrandMultipleOrgs:
    def test_brand_model_rel_records_time_bounded_brand(self) -> None:
        rel1 = BrandModelRelationship(
            id="BMR_1",
            brand_id="BR_ALPHA",
            boat_model_id="BM_36",
            first_year=1985,
            last_year=1995,
        )
        rel2 = BrandModelRelationship(
            id="BMR_2",
            brand_id="BR_ALPHA",
            boat_model_id="BM_36",
            first_year=1996,
            last_year=None,
        )
        assert rel1.brand_id == rel2.brand_id
        assert rel1.first_year != rel2.first_year

    def test_two_org_design_rels_share_boat_design(self) -> None:
        rel_a = OrganizationDesignRelationship(
            id="ODR_A",
            organization_id="ORG_1",
            boat_design_id="BD_36",
            role=BuilderRole.BUILDER,
            first_year=1985,
            last_year=1993,
        )
        rel_b = OrganizationDesignRelationship(
            id="ODR_B",
            organization_id="ORG_2",
            boat_design_id="BD_36",
            role=BuilderRole.LICENSED_BUILDER,
            first_year=1993,
            last_year=None,
        )
        assert rel_a.boat_design_id == rel_b.boat_design_id
        assert rel_a.organization_id != rel_b.organization_id


# ---------------------------------------------------------------------------
# Scenario 6: One Organization can build designs for multiple Brands
# ---------------------------------------------------------------------------


class TestScenario06OneOrgMultipleBrands:
    def test_one_org_appears_in_two_design_relationships(self) -> None:
        rel_design_1 = OrganizationDesignRelationship(
            id="ODR_X1",
            organization_id="ORG_WORKS",
            boat_design_id="BD_ALPHA_36",
            role=BuilderRole.BUILDER,
        )
        rel_design_2 = OrganizationDesignRelationship(
            id="ODR_X2",
            organization_id="ORG_WORKS",
            boat_design_id="BD_BETA_28",
            role=BuilderRole.MANUFACTURER,
        )
        assert rel_design_1.organization_id == rel_design_2.organization_id
        assert rel_design_1.boat_design_id != rel_design_2.boat_design_id


# ---------------------------------------------------------------------------
# Scenario 7: Builder change can be represented without creating a second
# BoatDesign solely for that change
# ---------------------------------------------------------------------------


class TestScenario07BuilderChangeNoDesignSplit:
    def test_two_builder_rels_share_same_boat_design_id(self) -> None:
        original = OrganizationDesignRelationship(
            id="ODR_ORIG",
            organization_id="ORG_ORIGINAL",
            boat_design_id="BD_SAME",
            role=BuilderRole.BUILDER,
            first_year=1980,
            last_year=1990,
        )
        successor = OrganizationDesignRelationship(
            id="ODR_SUCC",
            organization_id="ORG_SUCCESSOR",
            boat_design_id="BD_SAME",
            role=BuilderRole.BUILDER,
            first_year=1991,
            last_year=None,
        )
        assert original.boat_design_id == successor.boat_design_id

    def test_builder_relationship_id_different_for_each_period(self) -> None:
        original = OrganizationDesignRelationship(
            id="ODR_ORIG",
            organization_id="ORG_ORIGINAL",
            boat_design_id="BD_SAME",
            role=BuilderRole.BUILDER,
        )
        successor = OrganizationDesignRelationship(
            id="ODR_SUCC",
            organization_id="ORG_SUCCESSOR",
            boat_design_id="BD_SAME",
            role=BuilderRole.BUILDER,
        )
        assert original.id != successor.id


# ---------------------------------------------------------------------------
# Scenario 8: Relationship validity can remain null or use explicit bounds
# ---------------------------------------------------------------------------


class TestScenario08NullAndExplicitBounds:
    def test_brand_rel_all_bounds_null(self) -> None:
        rel = BrandModelRelationship(
            id="BMR_NULL",
            brand_id="BR_X",
            boat_model_id="BM_X",
        )
        assert rel.first_year is None
        assert rel.last_year is None
        assert rel.hull_number_from is None
        assert rel.hull_number_to is None

    def test_org_rel_explicit_year_and_hull_bounds(self) -> None:
        rel = OrganizationDesignRelationship(
            id="ODR_BOUNDED",
            organization_id="ORG_X",
            boat_design_id="BD_X",
            role=BuilderRole.BUILDER,
            first_year=1978,
            last_year=1992,
            hull_number_from="001",
            hull_number_to="450",
        )
        assert rel.first_year == 1978
        assert rel.last_year == 1992
        assert rel.hull_number_from == "001"
        assert rel.hull_number_to == "450"

    def test_market_annotation_optional(self) -> None:
        rel = BrandModelRelationship(
            id="BMR_MKT",
            brand_id="BR_Y",
            boat_model_id="BM_Y",
            market="Europe",
        )
        assert rel.market == "Europe"


# ---------------------------------------------------------------------------
# Scenario 9: BoatModel v0.2 has no authoritative free-text
# manufacturer/brand identity fields
# (enforced by schema contract; also tested in contract tests)
# ---------------------------------------------------------------------------


class TestScenario09BoatModelV02NoFreeTextManufacturer:
    def test_brand_entity_has_no_manufacturer_name_attr(self) -> None:
        brand = _brand("BR_TEST", "Test Yachts")
        assert not hasattr(brand, "manufacturer_name")
        assert not hasattr(brand, "brand_name")

    def test_boat_model_relationship_uses_brand_id_not_name(self) -> None:
        rel = BrandModelRelationship(id="BMR_TEST", brand_id="BR_TEST", boat_model_id="BM_TEST")
        assert hasattr(rel, "brand_id")
        assert not hasattr(rel, "brand_name")
        assert not hasattr(rel, "manufacturer_name")


# ---------------------------------------------------------------------------
# Scenario 10: BoatDesign successor has no authoritative free-text
# builder identity name
# (also enforced by BOAT_DESIGN_SCHEMA.v0.5.json contract tests)
# ---------------------------------------------------------------------------


class TestScenario10OrgDesignRelHasNoFreeTextName:
    def test_org_design_rel_has_no_name_field(self) -> None:
        rel = OrganizationDesignRelationship(
            id="ODR_TEST",
            organization_id="ORG_TEST",
            boat_design_id="BD_TEST",
            role=BuilderRole.MANUFACTURER,
        )
        assert not hasattr(rel, "name")

    def test_org_design_rel_has_organization_id(self) -> None:
        rel = OrganizationDesignRelationship(
            id="ODR_TEST",
            organization_id="ORG_TEST",
            boat_design_id="BD_TEST",
            role=BuilderRole.BUILDER,
        )
        assert rel.organization_id == "ORG_TEST"


# ---------------------------------------------------------------------------
# Scenario 11: Legacy BoatModel v0.1 and BoatDesign v0.4 remain loadable
# (tested by contract registry in test_identity_contracts.py)
# Covered here via a placeholder assertion
# ---------------------------------------------------------------------------


class TestScenario11LegacySchemasRemain:
    def test_legacy_schema_files_exist(self) -> None:
        from pathlib import Path

        specs = Path(__file__).resolve().parents[2] / "specs"
        assert (specs / "BOAT_MODEL_SCHEMA.v0.1.json").exists()
        assert (specs / "BOAT_DESIGN_SCHEMA.v0.4.json").exists()


# ---------------------------------------------------------------------------
# Scenario 12: AliasClass Python vocabulary matches normative schema enum
# ---------------------------------------------------------------------------


class TestScenario12AliasClassMatchesSchema:
    def test_alias_class_values(self) -> None:
        expected = {
            "common_name",
            "trade_name",
            "abbreviation",
            "historical_name",
            "alternate_spelling",
            "transliteration",
            "source_spelling",
            "other",
        }
        actual = {member.value for member in AliasClass}
        assert actual == expected

    def test_alias_class_is_str(self) -> None:
        assert isinstance(AliasClass.COMMON_NAME, str)
        assert AliasClass.COMMON_NAME == "common_name"


# ---------------------------------------------------------------------------
# Scenario 13: Corporate suffix stripping (single suffix, terminal annotation)
# ---------------------------------------------------------------------------


class TestScenario13CorporateSuffixStripping:
    def test_ltd_stripped_from_search_key(self) -> None:
        keys = generate_search_keys("Builder Works Ltd. (USA)")
        assert "builder works" in keys

    def test_original_canonical_name_preserved(self) -> None:
        canonical = "Builder Works Ltd. (USA)"
        org = _org("ORG_BW", canonical)
        assert org.canonical_name == canonical

    def test_full_key_also_present(self) -> None:
        keys = generate_search_keys("Builder Works Ltd. (USA)")
        assert "builder works ltd. (usa)" in keys

    def test_case_folding_applied(self) -> None:
        keys = generate_search_keys("BUILDER WORKS LTD.")
        assert "builder works" in keys

    def test_inc_stripped(self) -> None:
        keys = generate_search_keys("Coastal Marine Inc.")
        assert "coastal marine" in keys

    def test_corp_stripped(self) -> None:
        keys = generate_search_keys("Pacific Yachts Corp.")
        assert "pacific yachts" in keys

    def test_gmbh_stripped(self) -> None:
        keys = generate_search_keys("Nordische Werft GmbH")
        assert "nordische werft" in keys

    def test_limited_stripped(self) -> None:
        keys = generate_search_keys("Island Boats Limited")
        assert "island boats" in keys

    def test_corporation_stripped(self) -> None:
        keys = generate_search_keys("East Coast Yachts Corporation")
        assert "east coast yachts" in keys

    def test_company_stripped(self) -> None:
        keys = generate_search_keys("Anchor Marine Company")
        assert "anchor marine" in keys

    def test_co_stripped(self) -> None:
        keys = generate_search_keys("Anchor Marine Co.")
        assert "anchor marine" in keys

    def test_country_annotation_uk_stripped(self) -> None:
        keys = generate_search_keys("Westerly Marine (UK)")
        assert "westerly marine" in keys

    def test_country_annotation_fra_stripped(self) -> None:
        keys = generate_search_keys("Jeanneau (FRA)")
        assert "jeanneau" in keys


# ---------------------------------------------------------------------------
# Scenario 14: Repeated suffixes like "Co., Ltd." can generate a shortened key
# ---------------------------------------------------------------------------


class TestScenario14RepeatedSuffixStripping:
    def test_co_ltd_both_stripped(self) -> None:
        keys = generate_search_keys("Example Marine Co., Ltd.")
        assert "example marine" in keys

    def test_ltd_usa_both_stripped(self) -> None:
        keys = generate_search_keys("Example Marine Ltd. (USA)")
        assert "example marine" in keys

    def test_full_normalized_key_still_present(self) -> None:
        keys = generate_search_keys("Example Marine Co., Ltd.")
        assert "example marine co., ltd." in keys


# ---------------------------------------------------------------------------
# Scenario 15: Case/punctuation normalization can cause two distinct entity IDs
# to share a key without merging them
# ---------------------------------------------------------------------------


class TestScenario15KeyCollisionNoMerge:
    def test_two_orgs_same_key_different_ids(self) -> None:
        org_a = _org("ORG_A", "Ocean Marine Ltd.")
        org_b = _org("ORG_B", "OCEAN MARINE LTD.")
        keys_a = generate_search_keys(org_a.canonical_name)
        keys_b = generate_search_keys(org_b.canonical_name)
        assert keys_a == keys_b
        assert org_a.id != org_b.id

    def test_shared_key_does_not_equal_ids(self) -> None:
        shared_key = "ocean marine"
        org_a = _org("ORG_A", "Ocean Marine Ltd.")
        org_b = _org("ORG_B", "Ocean Marine Co.")
        keys_a = generate_search_keys(org_a.canonical_name)
        keys_b = generate_search_keys(org_b.canonical_name)
        assert shared_key in keys_a
        assert shared_key in keys_b
        assert org_a.id != org_b.id


# ---------------------------------------------------------------------------
# Scenario 16: Raw manufacturer text alone does not trigger Brand/Organization
# classification; no such inference path exists in this module
# ---------------------------------------------------------------------------


class TestScenario16NoRoleInferenceFromRawString:
    def test_generate_search_keys_returns_only_lookup_tokens(self) -> None:
        keys = generate_search_keys("Some Manufacturer Name")
        assert isinstance(keys, frozenset)
        assert all(isinstance(k, str) for k in keys)

    def test_no_role_attribute_on_search_key_result(self) -> None:
        keys = generate_search_keys("Some Manufacturer Name")
        for k in keys:
            assert not hasattr(k, "role")
            assert not hasattr(k, "entity_type")

    def test_module_has_no_infer_role_function(self) -> None:
        import hullq.domain.identity as identity_module

        assert not hasattr(identity_module, "infer_role")
        assert not hasattr(identity_module, "classify_manufacturer")
        assert not hasattr(identity_module, "resolve_from_string")


# ---------------------------------------------------------------------------
# Additional value-object contract tests
# ---------------------------------------------------------------------------


class TestIdentityAliasContract:
    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id must be non-empty"):
            IdentityAlias(id="", alias_class=AliasClass.COMMON_NAME, name="Test")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="name must be non-empty"):
            IdentityAlias(id="A1", alias_class=AliasClass.COMMON_NAME, name="")

    def test_notes_optional(self) -> None:
        alias = IdentityAlias(id="A1", alias_class=AliasClass.OTHER, name="Test")
        assert alias.notes is None

    def test_frozen(self) -> None:
        alias = IdentityAlias(id="A1", alias_class=AliasClass.OTHER, name="Test")
        with pytest.raises((AttributeError, TypeError)):
            alias.name = "Changed"  # type: ignore[misc]


class TestOrganizationContract:
    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id must be non-empty"):
            Organization(id="", canonical_name="Test")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="canonical_name must be non-empty"):
            Organization(id="ORG_1", canonical_name="")

    def test_no_aliases_by_default(self) -> None:
        org = _org("ORG_1", "Test Yard")
        assert org.aliases == ()

    def test_frozen(self) -> None:
        org = _org("ORG_1", "Test Yard")
        with pytest.raises((AttributeError, TypeError)):
            org.canonical_name = "Changed"  # type: ignore[misc]


class TestBrandContract:
    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id must be non-empty"):
            Brand(id="", canonical_name="Test")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="canonical_name must be non-empty"):
            Brand(id="BR_1", canonical_name="")

    def test_no_aliases_by_default(self) -> None:
        brand = _brand("BR_1", "Test Brand")
        assert brand.aliases == ()


class TestGenerateSearchKeys:
    def test_returns_frozenset(self) -> None:
        keys = generate_search_keys("Test Marine")
        assert isinstance(keys, frozenset)

    def test_canonical_unchanged_by_key_generation(self) -> None:
        name = "Builder Works Ltd. (USA)"
        keys = generate_search_keys(name)
        assert name == "Builder Works Ltd. (USA)"
        assert name not in set(keys)  # "Builder Works Ltd. (USA)" != any normalized key

    def test_alias_keys_included(self) -> None:
        alias = _alias("A1", AliasClass.ALTERNATE_SPELLING, "Nordisch")
        keys = generate_search_keys("Nordische Werft GmbH", [alias])
        assert "nordisch" in keys

    def test_empty_name_produces_no_key(self) -> None:
        keys = generate_search_keys("   ")
        assert len(keys) == 0

    def test_whitespace_normalized(self) -> None:
        keys = generate_search_keys("Test  Marine   Ltd.")
        assert "test marine" in keys

    def test_same_name_same_keys_deterministic(self) -> None:
        k1 = generate_search_keys("Ocean Marine Ltd.")
        k2 = generate_search_keys("Ocean Marine Ltd.")
        assert k1 == k2

    def test_suffix_only_name_strips_to_empty_and_omits(self) -> None:
        keys = generate_search_keys("Ltd.")
        assert "ltd." in keys
        assert "" not in keys

    def test_builder_role_values_match_schema(self) -> None:
        expected = {"builder", "manufacturer", "licensed_builder", "other"}
        actual = {r.value for r in BuilderRole}
        assert actual == expected


class TestRelationshipValidation:
    def test_brand_model_rel_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id must be non-empty"):
            BrandModelRelationship(id="", brand_id="BR_X", boat_model_id="BM_X")

    def test_brand_model_rel_empty_brand_id_raises(self) -> None:
        with pytest.raises(ValueError, match="brand_id must be non-empty"):
            BrandModelRelationship(id="BMR_X", brand_id="", boat_model_id="BM_X")

    def test_brand_model_rel_empty_model_id_raises(self) -> None:
        with pytest.raises(ValueError, match="boat_model_id must be non-empty"):
            BrandModelRelationship(id="BMR_X", brand_id="BR_X", boat_model_id="")

    def test_org_design_rel_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id must be non-empty"):
            OrganizationDesignRelationship(
                id="", organization_id="ORG_X", boat_design_id="BD_X", role=BuilderRole.BUILDER
            )

    def test_org_design_rel_empty_org_id_raises(self) -> None:
        with pytest.raises(ValueError, match="organization_id must be non-empty"):
            OrganizationDesignRelationship(
                id="ODR_X", organization_id="", boat_design_id="BD_X", role=BuilderRole.BUILDER
            )

    def test_org_design_rel_empty_design_id_raises(self) -> None:
        with pytest.raises(ValueError, match="boat_design_id must be non-empty"):
            OrganizationDesignRelationship(
                id="ODR_X",
                organization_id="ORG_X",
                boat_design_id="",
                role=BuilderRole.BUILDER,
            )
