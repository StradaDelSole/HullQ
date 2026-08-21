"""PostgreSQL 18 integration tests for canonical identity persistence — SLICE-0016.

Covers the required-tests list in
docs/slices/SLICE-0016-canonical-identity-persistence-bootstrap-admission.md
that require a real PostgreSQL database (items 1-21, 26). Items 24-25
(existing research tests remain green; full quality gate) are covered by the
rest of the test suite / CI, not by this file.

Skipped automatically when HULLQ_TEST_DATABASE_URL is not set (see conftest.py).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError

from hullq.contracts import ContractRegistry
from hullq.domain.identity import AliasClass, Brand, IdentityAlias, Organization
from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    ProducerKind,
    ProducerMetadata,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.persistence.identity_importer import import_canonical_identity_admission
from hullq.persistence.identity_readback import (
    fetch_boat_design,
    fetch_boat_model,
    fetch_brand,
    fetch_evidence_links_for_entity,
    fetch_organization,
    fetch_organization_design_relationship,
)
from hullq.persistence.identity_types import (
    CanonicalEvidenceLink,
    CanonicalIdentityAdmission,
    CanonicalImportStatus,
    CanonicalReferenceError,
)
from hullq.persistence.importer import import_research_evidence_bundle
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ObservationApplicability,
    ResearchEvidenceBundle,
    ResearchObservation,
)

SPECS = Path(__file__).resolve().parents[2] / "specs"


@pytest.fixture(scope="module")
def registry() -> ContractRegistry:
    return ContractRegistry.from_directory(SPECS)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _alias(
    alias_id: str = "A_1",
    alias_class: AliasClass = AliasClass.COMMON_NAME,
    name: str = "Alias Name",
    notes: str | None = None,
) -> IdentityAlias:
    return IdentityAlias(id=alias_id, alias_class=alias_class, name=name, notes=notes)


def _brand(brand_id: str, name: str = "Example", aliases: tuple[IdentityAlias, ...] = ()) -> Brand:
    return Brand(id=brand_id, canonical_name=name, aliases=aliases)


def _organization(
    org_id: str, name: str = "Example Works", aliases: tuple[IdentityAlias, ...] = ()
) -> Organization:
    return Organization(id=org_id, canonical_name=name, aliases=aliases)


def _boat_model_payload(
    model_id: str,
    name: str = "Example 36",
    first_built: int | None = 1988,
    last_built: int | None = 1998,
    aliases: list[dict[str, Any]] | None = None,
    brand_relationships: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "0.2",
        "id": model_id,
        "canonical_name": name,
        "aliases": aliases or [],
        "brand_relationships": brand_relationships or [],
        "first_built": first_built,
        "last_built": last_built,
        "boat_design_ids": [],
    }


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
    design_id: str,
    boat_model_id: str,
    builders: list[dict[str, Any]] | None = None,
    first_built: int | None = 1988,
    last_built: int | None = 1998,
    number_built: int | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "0.5",
        "id": design_id,
        "boat_model_id": boat_model_id,
        "generation": {
            "label": "Mk I",
            "sequence": 1,
            "aliases": [],
            "first_built": first_built,
            "last_built": last_built,
            "hull_number_from": None,
            "hull_number_to": None,
            "boundary_confidence": "medium",
        },
        "relationships": {
            "builders": builders or [],
            "designers": [],
            "number_built": number_built,
        },
        "baseline": _sparse_baseline(),
        "named_variants": [],
        "design_options": [],
        "quality": {"status": "partial", "confidence": "medium", "notes": None},
    }


def _builder(
    rel_id: str = "ODR_1", organization_id: str = "ORG_1", role: str = "builder"
) -> dict[str, Any]:
    return {"id": rel_id, "organization_id": organization_id, "role": role}


def _brand_rel(rel_id: str = "BMR_1", brand_id: str = "BR_1") -> dict[str, Any]:
    return {"id": rel_id, "brand_id": brand_id}


def _admission(
    brands: tuple[Brand, ...] = (),
    organizations: tuple[Organization, ...] = (),
    boat_models: tuple[dict[str, Any], ...] = (),
    boat_designs: tuple[dict[str, Any], ...] = (),
    evidence_links: tuple[CanonicalEvidenceLink, ...] = (),
) -> CanonicalIdentityAdmission:
    return CanonicalIdentityAdmission(
        brands=brands,
        organizations=organizations,
        boat_models=boat_models,
        boat_designs=boat_designs,
        evidence_links=evidence_links,
    )


def _observation(obs_id: str = "OBS-CANON-001") -> ResearchObservation:
    return ResearchObservation(
        observation_id=obs_id,
        research_target=ResearchTarget(manufacturer=None, model="Test 35", first_built=None),
        source_id="SRC-001",
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.LITERAL, value="Example 36", unit=None, excerpt=None
        ),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=True,
        ),
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="slice-0016-test",
            version="0.1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id="JOB-1", activity_id="WAVE-1"),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes=None,
    )


def _bundle_with_observation(obs: ResearchObservation) -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(
        bundle_id=f"BUNDLE-{obs.observation_id}",
        bundle_version="1.0",
        research_target=obs.research_target,
        research_job_id="JOB-1",
        activity_id="WAVE-1",
        observations=(obs,),
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# 1-2: migration
# ---------------------------------------------------------------------------


def test_migration_creates_canonical_identity_schema(clean_conn: Any) -> None:
    with clean_conn.cursor() as cur:
        cur.execute("SELECT migration_id FROM hullq_schema_migrations ORDER BY migration_id")
        ids = [r[0] for r in cur.fetchall()]
    assert "001_initial_schema" in ids
    assert "002_canonical_identity_schema" in ids
    with clean_conn.cursor() as cur:
        for table in (
            "canonical_brands",
            "canonical_organizations",
            "canonical_brand_aliases",
            "canonical_organization_aliases",
            "canonical_boat_models",
            "canonical_boat_model_aliases",
            "canonical_brand_model_relationships",
            "canonical_boat_designs",
            "canonical_organization_design_relationships",
            "canonical_admission_evidence_links",
        ):
            cur.execute("SELECT to_regclass(%s)", [table])
            assert cur.fetchone()[0] is not None, f"table {table} missing"  # type: ignore[index]


def test_upgrade_from_research_only_schema_preserves_data(
    db_url: str, registry: ContractRegistry
) -> None:
    """Applying migration 002 on top of an existing 001-only schema must not
    disturb previously persisted research data.

    Forces a genuine 001-only starting state (drops canonical_* tables and
    un-tracks migration 002) regardless of what earlier tests in this session
    already applied, so this test proves the upgrade path deterministically
    rather than relying on test execution order.
    """
    import psycopg

    from hullq.persistence.migrations import MIGRATIONS_DIR, apply_migrations

    conn = psycopg.connect(db_url)
    obs = _observation("OBS-UPGRADE-001")
    try:
        apply_migrations(conn)  # ensure the tracking table + full schema exist at least once

        with conn.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS
                    canonical_admission_evidence_links,
                    canonical_organization_design_relationships,
                    canonical_boat_designs,
                    canonical_brand_model_relationships,
                    canonical_boat_model_aliases,
                    canonical_boat_models,
                    canonical_organization_aliases,
                    canonical_organizations,
                    canonical_brand_aliases,
                    canonical_brands
                CASCADE
            """)
            cur.execute(
                "DELETE FROM hullq_schema_migrations WHERE migration_id = %s",
                ["002_canonical_identity_schema"],
            )
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('canonical_brands')")
            assert cur.fetchone()[0] is None  # type: ignore[index]  # genuinely 001-only now

        bundle = _bundle_with_observation(obs)
        result = import_research_evidence_bundle(conn, bundle)
        assert result.status.value in ("imported", "already_imported")

        applied = apply_migrations(conn, MIGRATIONS_DIR)
        assert applied == ["002_canonical_identity_schema"]

        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('canonical_brands')")
            assert cur.fetchone()[0] is not None  # type: ignore[index]
            cur.execute(
                "SELECT content_hash FROM research_observations WHERE observation_id = %s",
                [obs.observation_id],
            )
            assert cur.fetchone() is not None

        # Canonical admission works against the freshly-upgraded schema.
        admission = _admission(brands=(_brand("BR-UPGRADE-1"),))
        canon_result = import_canonical_identity_admission(conn, admission, registry)
        assert canon_result.status == CanonicalImportStatus.IMPORTED
    finally:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM research_observations WHERE observation_id = %s", [obs.observation_id]
            )
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# 3-6: Brand / Organization round-trip and identity independence
# ---------------------------------------------------------------------------


def test_brand_admission_round_trips_exactly(clean_conn: Any, registry: ContractRegistry) -> None:
    brand = _brand(
        "BR_001", "Example", aliases=(_alias("A1", AliasClass.TRADE_NAME, "Example Yachts"),)
    )
    result = import_canonical_identity_admission(clean_conn, _admission(brands=(brand,)), registry)
    assert result.status == CanonicalImportStatus.IMPORTED

    fetched = fetch_brand(clean_conn, "BR_001")
    assert fetched is not None
    assert fetched.id == brand.id
    assert fetched.canonical_name == brand.canonical_name
    assert fetched.aliases == brand.aliases


def test_organization_admission_round_trips_exactly(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    org = _organization(
        "ORG_001", "Example Works Ltd.", aliases=(_alias("A1", AliasClass.ABBREVIATION, "EW"),)
    )
    result = import_canonical_identity_admission(
        clean_conn, _admission(organizations=(org,)), registry
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    fetched = fetch_organization(clean_conn, "ORG_001")
    assert fetched is not None
    assert fetched.canonical_name == org.canonical_name
    assert fetched.aliases == org.aliases


def test_brand_and_organization_same_name_remain_distinct(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    brand = _brand("BR_SAME", "Example")
    org = _organization("ORG_SAME", "Example")
    result = import_canonical_identity_admission(
        clean_conn, _admission(brands=(brand,), organizations=(org,)), registry
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    fetched_brand = fetch_brand(clean_conn, "BR_SAME")
    fetched_org = fetch_organization(clean_conn, "ORG_SAME")
    assert fetched_brand is not None
    assert fetched_org is not None
    assert fetched_brand.canonical_name == fetched_org.canonical_name
    assert fetched_brand.id != fetched_org.id


def test_two_boat_models_same_name_remain_distinct(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    bm1 = _boat_model_payload("BM_A", name="Voyager 30")
    bm2 = _boat_model_payload("BM_B", name="Voyager 30")
    result = import_canonical_identity_admission(
        clean_conn, _admission(boat_models=(bm1, bm2)), registry
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    f1 = fetch_boat_model(clean_conn, "BM_A")
    f2 = fetch_boat_model(clean_conn, "BM_B")
    assert f1 is not None
    assert f2 is not None
    assert f1["canonical_name"] == f2["canonical_name"] == "Voyager 30"
    assert f1["id"] != f2["id"]


# ---------------------------------------------------------------------------
# 7-9: referential integrity for BoatDesign / relationships
# ---------------------------------------------------------------------------


def test_boat_design_requires_valid_boat_model(clean_conn: Any, registry: ContractRegistry) -> None:
    design = _boat_design_payload("BD_ORPHAN", boat_model_id="BM_DOES_NOT_EXIST")
    with pytest.raises(CanonicalReferenceError):
        import_canonical_identity_admission(
            clean_conn, _admission(boat_designs=(design,)), registry
        )

    assert fetch_boat_design(clean_conn, "BD_ORPHAN") is None


def test_builder_relationship_requires_valid_organization_and_design(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    bm = _boat_model_payload("BM_BR1")
    design = _boat_design_payload(
        "BD_BR1", "BM_BR1", builders=[_builder("ODR_MISSING_ORG", "ORG_DOES_NOT_EXIST")]
    )
    with pytest.raises(CanonicalReferenceError):
        import_canonical_identity_admission(
            clean_conn, _admission(boat_models=(bm,), boat_designs=(design,)), registry
        )
    # Atomic: neither the model nor the design were left partially admitted.
    assert fetch_boat_model(clean_conn, "BM_BR1") is None
    assert fetch_boat_design(clean_conn, "BD_BR1") is None


def test_brand_model_relationship_requires_valid_brand_and_model(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    bm = _boat_model_payload(
        "BM_BMR1", brand_relationships=[_brand_rel("BMR_MISSING_BRAND", "BR_DOES_NOT_EXIST")]
    )
    with pytest.raises(CanonicalReferenceError):
        import_canonical_identity_admission(clean_conn, _admission(boat_models=(bm,)), registry)
    assert fetch_boat_model(clean_conn, "BM_BMR1") is None


# ---------------------------------------------------------------------------
# 10: builder change via relationship, not a new BoatDesign
# ---------------------------------------------------------------------------


def test_builder_change_represented_through_relationship_only(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    org_a = _organization("ORG_BUILDER_A")
    org_b = _organization("ORG_BUILDER_B")
    bm = _boat_model_payload("BM_BUILDER_CHANGE")
    design = _boat_design_payload(
        "BD_BUILDER_CHANGE",
        "BM_BUILDER_CHANGE",
        builders=[
            {**_builder("ODR_A", "ORG_BUILDER_A"), "first_year": 1988, "last_year": 1993},
        ],
    )
    result = import_canonical_identity_admission(
        clean_conn,
        _admission(organizations=(org_a, org_b), boat_models=(bm,), boat_designs=(design,)),
        registry,
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    # A later admission adds a second, later-dated builder relationship for the
    # *same* BoatDesign ID — the builder change never creates a new BoatDesign row.
    design_updated = _boat_design_payload(
        "BD_BUILDER_CHANGE",
        "BM_BUILDER_CHANGE",
        builders=[
            {**_builder("ODR_A", "ORG_BUILDER_A"), "first_year": 1988, "last_year": 1993},
            {**_builder("ODR_B", "ORG_BUILDER_B"), "first_year": 1993, "last_year": None},
        ],
    )
    result2 = import_canonical_identity_admission(
        clean_conn, _admission(boat_designs=(design_updated,)), registry
    )
    assert result2.status == CanonicalImportStatus.IMPORTED

    fetched = fetch_boat_design(clean_conn, "BD_BUILDER_CHANGE")
    assert fetched is not None
    builder_ids = {b["id"] for b in fetched["relationships"]["builders"]}
    assert builder_ids == {"ODR_A", "ODR_B"}

    rel_b = fetch_organization_design_relationship(clean_conn, "ODR_B")
    assert rel_b is not None
    assert rel_b.organization_id == "ORG_BUILDER_B"


# ---------------------------------------------------------------------------
# 11: aliases round-trip losslessly and stay entity-scoped
# ---------------------------------------------------------------------------


def test_aliases_round_trip_losslessly_and_entity_scoped(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    brand = _brand("BR_ALIAS", aliases=(_alias("A1", AliasClass.SOURCE_SPELLING, "ExampleCo"),))
    org = _organization(
        "ORG_ALIAS", aliases=(_alias("A1", AliasClass.HISTORICAL_NAME, "Old Works"),)
    )
    result = import_canonical_identity_admission(
        clean_conn, _admission(brands=(brand,), organizations=(org,)), registry
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    fetched_brand = fetch_brand(clean_conn, "BR_ALIAS")
    fetched_org = fetch_organization(clean_conn, "ORG_ALIAS")
    assert fetched_brand is not None
    assert fetched_org is not None
    # Same alias_id ("A1") legitimately reused under two different owning
    # entities without collision; content differs and stays scoped.
    assert fetched_brand.aliases[0].name == "ExampleCo"
    assert fetched_org.aliases[0].name == "Old Works"


# ---------------------------------------------------------------------------
# 12: schema-invalid payload fails before persistence
# ---------------------------------------------------------------------------


def test_schema_invalid_boat_model_fails_before_persistence(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    bad = _boat_model_payload("BM_INVALID")
    bad["manufacturer_name"] = "Not allowed in v0.2"  # rejected: additionalProperties false
    with pytest.raises(ValidationError):
        import_canonical_identity_admission(clean_conn, _admission(boat_models=(bad,)), registry)
    assert fetch_boat_model(clean_conn, "BM_INVALID") is None


# ---------------------------------------------------------------------------
# 13-14: provenance linkage fail-closed + crosscheck cannot satisfy it
# ---------------------------------------------------------------------------


def test_missing_evidence_reference_fails_closed(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    brand = _brand("BR_EVLINK_MISSING")
    link = CanonicalEvidenceLink(
        link_id="LINK_MISSING",
        entity_kind=SubjectKind.BRAND,
        entity_id="BR_EVLINK_MISSING",
        observation_id="OBS-DOES-NOT-EXIST",
    )
    with pytest.raises(CanonicalReferenceError):
        import_canonical_identity_admission(
            clean_conn, _admission(brands=(brand,), evidence_links=(link,)), registry
        )
    # Atomic: the brand itself was rolled back too.
    assert fetch_brand(clean_conn, "BR_EVLINK_MISSING") is None


def test_reference_crosscheck_cannot_satisfy_admission_provenance(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    from hullq.research.observations import ReferenceCheckOutcome, ReferenceCrosscheck

    obs = _observation("OBS-CC-BASE")
    crosscheck = ReferenceCrosscheck(
        crosscheck_id="CC-NOT-EVIDENCE",
        reference_source_id="SRC-REF",
        topic_or_field="canonical_name",
        outcome=ReferenceCheckOutcome.MATCH,
        notes=None,
    )
    bundle = ResearchEvidenceBundle(
        bundle_id="BUNDLE-CC-BASE",
        bundle_version="1.0",
        research_target=obs.research_target,
        research_job_id="JOB-1",
        activity_id="WAVE-1",
        observations=(obs,),
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(crosscheck,),
    )
    bundle_result = import_research_evidence_bundle(clean_conn, bundle)
    assert bundle_result.status.value in ("imported", "already_imported")

    brand = _brand("BR_CC")
    # Attempting to use the crosscheck_id as if it were an evidence/observation
    # id must fail closed: it does not exist in either FK'd table.
    link = CanonicalEvidenceLink(
        link_id="LINK_VIA_CROSSCHECK",
        entity_kind=SubjectKind.BRAND,
        entity_id="BR_CC",
        evidence_id="CC-NOT-EVIDENCE",
    )
    with pytest.raises(CanonicalReferenceError):
        import_canonical_identity_admission(
            clean_conn, _admission(brands=(brand,), evidence_links=(link,)), registry
        )
    assert fetch_brand(clean_conn, "BR_CC") is None

    # A correctly addressed link to the real observation succeeds.
    good_link = CanonicalEvidenceLink(
        link_id="LINK_VIA_OBSERVATION",
        entity_kind=SubjectKind.BRAND,
        entity_id="BR_CC",
        observation_id="OBS-CC-BASE",
    )
    result = import_canonical_identity_admission(
        clean_conn, _admission(brands=(brand,), evidence_links=(good_link,)), registry
    )
    assert result.status == CanonicalImportStatus.IMPORTED
    links = fetch_evidence_links_for_entity(clean_conn, SubjectKind.BRAND, "BR_CC")
    assert len(links) == 1
    assert links[0].observation_id == "OBS-CC-BASE"


# ---------------------------------------------------------------------------
# 15-17: idempotency / conflict / reordering
# ---------------------------------------------------------------------------


def test_exact_repeated_admission_is_idempotent(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    brand = _brand("BR_IDEMPOTENT", aliases=(_alias("A1", name="Alias One"),))
    admission = _admission(brands=(brand,))
    first = import_canonical_identity_admission(clean_conn, admission, registry)
    second = import_canonical_identity_admission(clean_conn, admission, registry)
    assert first.status == CanonicalImportStatus.IMPORTED
    assert second.status == CanonicalImportStatus.ALREADY_IMPORTED

    with clean_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM canonical_brands WHERE id = %s", ["BR_IDEMPOTENT"])
        assert cur.fetchone()[0] == 1  # type: ignore[index]


def test_changed_content_same_id_yields_conflict_no_overwrite(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    brand_v1 = _brand("BR_CONFLICT", "Original Name")
    brand_v2 = _brand("BR_CONFLICT", "Changed Name")
    r1 = import_canonical_identity_admission(clean_conn, _admission(brands=(brand_v1,)), registry)
    assert r1.status == CanonicalImportStatus.IMPORTED

    r2 = import_canonical_identity_admission(clean_conn, _admission(brands=(brand_v2,)), registry)
    assert r2.status == CanonicalImportStatus.CONFLICT
    assert r2.detail is not None

    fetched = fetch_brand(clean_conn, "BR_CONFLICT")
    assert fetched is not None
    assert fetched.canonical_name == "Original Name"  # no silent overwrite


def test_reordering_unordered_collections_does_not_create_false_conflict(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    aliases_order_a = (
        _alias("A1", name="First"),
        _alias("A2", name="Second"),
    )
    aliases_order_b = (
        _alias("A2", name="Second"),
        _alias("A1", name="First"),
    )
    brand_a = _brand("BR_REORDER", aliases=aliases_order_a)
    brand_b = _brand("BR_REORDER", aliases=aliases_order_b)

    r1 = import_canonical_identity_admission(clean_conn, _admission(brands=(brand_a,)), registry)
    r2 = import_canonical_identity_admission(clean_conn, _admission(brands=(brand_b,)), registry)
    assert r1.status == CanonicalImportStatus.IMPORTED
    assert (
        r2.status == CanonicalImportStatus.ALREADY_IMPORTED
    )  # reordering is a no-op, not a conflict


# ---------------------------------------------------------------------------
# 18: transaction rollback on dependent failure
# ---------------------------------------------------------------------------


def test_transaction_failure_rolls_back_full_dependent_graph(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    org = _organization("ORG_ROLLBACK")
    bm = _boat_model_payload("BM_ROLLBACK")
    design = _boat_design_payload(
        "BD_ROLLBACK",
        "BM_ROLLBACK",
        builders=[_builder("ODR_ROLLBACK", "ORG_DOES_NOT_EXIST")],  # invalid reference
    )
    with pytest.raises(CanonicalReferenceError):
        import_canonical_identity_admission(
            clean_conn,
            _admission(organizations=(org,), boat_models=(bm,), boat_designs=(design,)),
            registry,
        )

    # organization succeeded logically-first in-transaction but must also be
    # rolled back: the whole admission is one atomic unit.
    assert fetch_organization(clean_conn, "ORG_ROLLBACK") is None
    assert fetch_boat_model(clean_conn, "BM_ROLLBACK") is None
    assert fetch_boat_design(clean_conn, "BD_ROLLBACK") is None


# ---------------------------------------------------------------------------
# 21: sparse Tier-0 payload accepted without invented values
# ---------------------------------------------------------------------------


def test_sparse_tier0_boat_design_accepted_without_invented_values(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    bm = _boat_model_payload("BM_SPARSE", first_built=None, last_built=None)
    design = _boat_design_payload("BD_SPARSE", "BM_SPARSE", first_built=None, last_built=None)
    result = import_canonical_identity_admission(
        clean_conn, _admission(boat_models=(bm,), boat_designs=(design,)), registry
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    fetched_model = fetch_boat_model(clean_conn, "BM_SPARSE")
    fetched_design = fetch_boat_design(clean_conn, "BD_SPARSE")
    assert fetched_model is not None
    assert fetched_design is not None
    assert fetched_model["first_built"] is None
    assert fetched_design["baseline"]["dimensions"]["loa_m"] is None
    assert fetched_design["baseline"]["configuration"]["keel_type"] == "unknown"


# ---------------------------------------------------------------------------
# 22: no canonical IDs minted inside the persistence layer
# ---------------------------------------------------------------------------


def test_no_id_minted_missing_referenced_id_never_silently_created(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    """The importer never invents an ID for a caller-supplied name; a
    reference to a name with no matching stable ID fails closed instead of
    silently creating or matching an entity.
    """
    design = _boat_design_payload(
        "BD_NOMINT", "BM_NOMINT_DOES_NOT_EXIST"
    )  # BoatModel never admitted
    with pytest.raises(CanonicalReferenceError):
        import_canonical_identity_admission(
            clean_conn, _admission(boat_designs=(design,)), registry
        )
    with clean_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM canonical_boat_models")
        assert cur.fetchone()[0] == 0  # type: ignore[index]  # nothing minted


# ---------------------------------------------------------------------------
# BoatDesign round-trip (baseline/generation/quality fidelity)
# ---------------------------------------------------------------------------


def test_boat_design_round_trips_full_technical_baseline(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    bm = _boat_model_payload("BM_FULL")
    design = _boat_design_payload("BD_FULL", "BM_FULL")
    design["baseline"]["dimensions"]["loa_m"] = 10.97
    design["baseline"]["configuration"]["keel_type"] = "fin"
    design["baseline"]["construction"]["hull_material"] = "grp_fiberglass"
    design["quality"] = {"status": "verified", "confidence": "high", "notes": "Round-trip check."}

    result = import_canonical_identity_admission(
        clean_conn, _admission(boat_models=(bm,), boat_designs=(design,)), registry
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    fetched = fetch_boat_design(clean_conn, "BD_FULL")
    assert fetched is not None
    assert fetched["baseline"]["dimensions"]["loa_m"] == 10.97
    assert fetched["baseline"]["configuration"]["keel_type"] == "fin"
    assert fetched["quality"]["status"] == "verified"

    # And boat_design_ids on the parent model is derived correctly.
    fetched_model = fetch_boat_model(clean_conn, "BM_FULL")
    assert fetched_model is not None
    assert fetched_model["boat_design_ids"] == ["BD_FULL"]


def test_reconstructed_payloads_validate_against_accepted_schemas(
    clean_conn: Any, registry: ContractRegistry
) -> None:
    """Readback output must itself be schema-valid, proving lossless round-trip
    against the accepted contract rather than merely matching row counts.
    """
    brand = _brand("BR_SCHEMA_RT")
    bm = _boat_model_payload(
        "BM_SCHEMA_RT", brand_relationships=[_brand_rel("BMR_RT", "BR_SCHEMA_RT")]
    )
    org = _organization("ORG_SCHEMA_RT")
    design = _boat_design_payload(
        "BD_SCHEMA_RT", "BM_SCHEMA_RT", builders=[_builder("ODR_RT", "ORG_SCHEMA_RT")]
    )
    result = import_canonical_identity_admission(
        clean_conn,
        _admission(
            brands=(brand,), organizations=(org,), boat_models=(bm,), boat_designs=(design,)
        ),
        registry,
    )
    assert result.status == CanonicalImportStatus.IMPORTED

    fetched_model = fetch_boat_model(clean_conn, "BM_SCHEMA_RT")
    fetched_design = fetch_boat_design(clean_conn, "BD_SCHEMA_RT")
    assert fetched_model is not None
    assert fetched_design is not None

    registry.validator_by_name("BOAT_MODEL_SCHEMA.v0.2.json").validate(fetched_model)
    registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.5.json").validate(fetched_design)


# ---------------------------------------------------------------------------
# 19-20: concurrency (real PostgreSQL, two connections + threading.Barrier)
# ---------------------------------------------------------------------------


def test_concurrent_exact_admission_is_race_safe(db_url: str, registry: ContractRegistry) -> None:
    import threading

    import psycopg

    from hullq.persistence.migrations import apply_migrations

    setup_conn = psycopg.connect(db_url)
    try:
        apply_migrations(setup_conn)
        with setup_conn.cursor() as cur:
            cur.execute("DELETE FROM canonical_brands WHERE id = %s", ["BR_CONC_EXACT"])
        setup_conn.commit()
    finally:
        setup_conn.close()

    brand = _brand("BR_CONC_EXACT", "Concurrent Exact")
    admission = _admission(brands=(brand,))
    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        try:
            conn = psycopg.connect(db_url)
            try:
                barrier.wait(timeout=10)
                result = import_canonical_identity_admission(conn, admission, registry)
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = {r.status for r in results}
    assert statuses == {CanonicalImportStatus.IMPORTED, CanonicalImportStatus.ALREADY_IMPORTED}

    verify = psycopg.connect(db_url)
    try:
        with verify.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM canonical_brands WHERE id = %s", ["BR_CONC_EXACT"])
            assert cur.fetchone()[0] == 1  # type: ignore[index]
    finally:
        verify.close()


def test_concurrent_conflicting_admission_fails_closed_no_corruption(
    db_url: str, registry: ContractRegistry
) -> None:
    import threading

    import psycopg

    from hullq.persistence.migrations import apply_migrations

    setup_conn = psycopg.connect(db_url)
    try:
        apply_migrations(setup_conn)
        with setup_conn.cursor() as cur:
            cur.execute("DELETE FROM canonical_brands WHERE id = %s", ["BR_CONC_CONFLICT"])
        setup_conn.commit()
    finally:
        setup_conn.close()

    admission_a = _admission(brands=(_brand("BR_CONC_CONFLICT", "Name A"),))
    admission_b = _admission(brands=(_brand("BR_CONC_CONFLICT", "Name B"),))
    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(admission: CanonicalIdentityAdmission) -> None:
        try:
            conn = psycopg.connect(db_url)
            try:
                barrier.wait(timeout=10)
                result = import_canonical_identity_admission(conn, admission, registry)
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=(admission_a,)),
        threading.Thread(target=_worker, args=(admission_b,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    # Exactly one side wins the race (IMPORTED), the other observes a genuine
    # conflict (CONFLICT). No corruption: the row holds one consistent name.
    assert CanonicalImportStatus.IMPORTED in statuses
    assert CanonicalImportStatus.CONFLICT in statuses

    verify = psycopg.connect(db_url)
    try:
        with verify.cursor() as cur:
            cur.execute(
                "SELECT canonical_name FROM canonical_brands WHERE id = %s", ["BR_CONC_CONFLICT"]
            )
            rows = cur.fetchall()
            assert len(rows) == 1
            assert rows[0][0] in ("Name A", "Name B")
    finally:
        verify.close()


def test_boat_design_dict_helper_is_deep_copy_safe() -> None:
    """Sanity check for the test helper itself: mutating one payload copy must
    not leak into another (guards other tests in this module against a shared
    mutable-default bug).
    """
    a = _boat_design_payload("BD_X", "BM_X")
    b = copy.deepcopy(a)
    b["baseline"]["dimensions"]["loa_m"] = 99.0
    assert a["baseline"]["dimensions"]["loa_m"] is None
