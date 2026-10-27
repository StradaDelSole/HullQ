"""PostgreSQL-backed vessel category Search-exclusion integration tests -- SLICE-0091.

Proves the fail-closed category pre-filter wired into
`hullq.application.native_inventory_query.evaluate_native_inventory_requirements`
through the real accepted nine-criterion Sail funnel end to end: legacy
null-category inventory keeps matching unchanged (SLICE-0091 §C), while an
explicit concrete/design/cross-source category state that is not SAIL
(POWER, MOTORSAILER, CONFLICT) is excluded from a confirmed Sail match --
never a falsely confirmed Sail result. Also proves the application-level
`resolve_physical_boat_vessel_category` resolver directly for the
design-unresolved case (SLICE-0090 hard-case corpus FIX-0090-03/08/11,
control 01/02, category-only).

Each test runs against its own disposable PostgreSQL schema, mirroring
`tests/persistence/test_native_inventory_query_slice_0087.py`'s isolation
pattern (deliberately not importing that file's private helpers --
established repo convention duplicates the minimal seeding boilerplate per
slice test file rather than cross-importing between test modules).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.native_inventory_query import evaluate_native_inventory_requirements
from hullq.application.vessel_category_resolution import resolve_physical_boat_vessel_category
from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.media_gallery import MediaSourceKind
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.provenance import ResolverKind, ResolverMetadata, SubjectKind
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
)
from hullq.domain.vessel_category import (
    BoatDesignCategoryAssertionId,
    DesignVesselCategoryAssertion,
    VesselCategoryResolution,
    VesselCategoryResolutionReason,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.boat_design_category import (
    CATALOG_ADMISSION_SECRET_ENV_VAR,
    write_boat_design_category_assertion,
)
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.market_episode import create_market_episode, fetch_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing, fetch_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision,
)
from hullq.search.keel_design_bridge import lookup_keel_canonical_value

from ._field_resolution_support import admit_resolved_categorical_field

VA = AssertionKind.VALUE_ASSERTION
UNK = AssertionKind.UNKNOWN
_TEST_ADMISSION_SECRET = "slice-0091-test-catalog-admission-secret"


@pytest.fixture(autouse=True)
def _configured_admission_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CATALOG_ADMISSION_SECRET_ENV_VAR, _TEST_ADMISSION_SECRET)


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


@pytest.fixture()
def cat_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0091niq_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def cat_conn(cat_url: str) -> Generator[Any]:
    conn = psycopg.connect(cat_url)
    try:
        yield conn
    finally:
        conn.close()


def _as_of() -> datetime:
    return datetime.now(UTC)


def _insert_boat_design(conn: Any, design_id: str, model_id: str, *, keel_type: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"appendages": {"keel_type": keel_type}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    conn.commit()


def _admit_design_keel_type(conn: Any, design_id: str, *, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/appendages/keel_type",
        value=value,
        resolution_id=f"FR-KEEL-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    org: MarketplaceOrganization, account: AccountId, membership_id: str
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _attach_ready_cover_image(
    conn: Any, *, listing_id: str, org: MarketplaceOrganization, account: AccountId
) -> None:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [account.value],
            )
        seed_marketplace_organization(conn, org)
        asset = insert_approved_media_asset(
            conn,
            owner_organization_id=org.id,
            uploaded_by_account_id=account,
            rights_declared=True,
            source_kind=MediaSourceKind.BROKER_UPLOAD,
            source_reference=None,
            original_object_key=f"original/{listing_id}",
            derivative_object_key=f"derivative/{listing_id}",
            content_hash=f"hash-{listing_id}",
            mime_type="image/jpeg",
            width=800,
            height=600,
            byte_size=12345,
        )
        placement_result = create_uploaded_image_placement(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_asset=asset,
        )
        assert placement_result.media_placement_id is not None
        assert placement_result.gallery_version is not None
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _current_claim_revision_id(
    conn: Any, *, listing_id: str, org: MarketplaceOrganization
) -> PhysicalBoatClaimRevisionId | None:
    listing_record = fetch_native_listing(conn, NativeListingId(listing_id))
    assert listing_record is not None
    assert listing_record.listing.market_episode_id is not None
    episode_record = fetch_market_episode(conn, listing_record.listing.market_episode_id)
    assert episode_record is not None
    claim_record = fetch_current_physical_boat_claim(
        conn, episode_record.market_episode.physical_boat_id, org.id
    )
    return claim_record.revision_id if claim_record is not None else None


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_id: str,
    keel_configuration: KeelConfiguration,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(boat_design_id)
        ),
    )
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
        ),
    )
    write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising boat.",
            asking_price_amount=Decimal("180000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-PLACEHOLDER-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 40",
            build_year=BuildYearClaim(assertion_kind=VA, value=2019),
            keel_configuration=KeelConfigurationClaim(assertion_kind=VA, value=keel_configuration),
        ),
    )
    _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    return account, org, membership


def _write_vessel_category_claim(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    listing_id: str,
    revision_id: str,
    keel_configuration: KeelConfiguration,
    vessel_category: VesselCategoryClaim | None,
) -> None:
    expected_current_revision_id = _current_claim_revision_id(conn, listing_id=listing_id, org=org)
    conn.commit()
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(revision_id),
        expected_current_revision_id=expected_current_revision_id,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 40",
            build_year=BuildYearClaim(assertion_kind=VA, value=2019),
            keel_configuration=KeelConfigurationClaim(assertion_kind=VA, value=keel_configuration),
            vessel_category=vessel_category,
        ),
    )
    assert result.status.value in ("created", "revised"), result
    conn.commit()


def _issuer() -> ResolverMetadata:
    return ResolverMetadata(
        kind=ResolverKind.DETERMINISTIC_TOOL,
        identifier="slice-0091-test-harness",
        version="1",
    )


def _query_result(conn: Any) -> set[str]:
    outcome = evaluate_native_inventory_requirements(
        conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    return {m.native_listing_id.value for m in outcome.confirmed_matches}


# ---------------------------------------------------------------------------
# Control: legacy null-category Sail inventory -- unaffected (SLICE-0091 §C)
# ---------------------------------------------------------------------------


def test_legacy_null_category_listing_still_confirmed_match(cat_conn: Any) -> None:
    _insert_boat_design(cat_conn, "BD-91-LEG", "BM-91-LEG", keel_type="fin")
    _admit_design_keel_type(cat_conn, "BD-91-LEG", value="fin")
    _make_active_listing(
        cat_conn,
        listing_id="NL-91-LEG",
        physical_boat_id="PB-91-LEG",
        market_episode_id="ME-91-LEG",
        boat_design_id="BD-91-LEG",
        keel_configuration=KeelConfiguration.FIN,
    )
    assert _query_result(cat_conn) == {"NL-91-LEG"}


# ---------------------------------------------------------------------------
# Explicit concrete POWER claim excludes an otherwise-matching Sail listing
# ---------------------------------------------------------------------------


def test_explicit_concrete_power_excludes_confirmed_sail_match(cat_conn: Any) -> None:
    _insert_boat_design(cat_conn, "BD-91-PWR", "BM-91-PWR", keel_type="fin")
    _admit_design_keel_type(cat_conn, "BD-91-PWR", value="fin")
    account, org, membership = _make_active_listing(
        cat_conn,
        listing_id="NL-91-PWR",
        physical_boat_id="PB-91-PWR",
        market_episode_id="ME-91-PWR",
        boat_design_id="BD-91-PWR",
        keel_configuration=KeelConfiguration.FIN,
    )
    _write_vessel_category_claim(
        cat_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-91-PWR",
        revision_id="PBCREV-91-PWR-2",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    # Never a falsely confirmed Sail match -- the single most important
    # negative risk-register proof for this slice.
    assert "NL-91-PWR" not in _query_result(cat_conn)


# ---------------------------------------------------------------------------
# Explicit design-side MOTORSAILER excludes, with no concrete claim at all
# ---------------------------------------------------------------------------


def test_explicit_design_motorsailer_excludes_confirmed_sail_match(cat_conn: Any) -> None:
    _insert_boat_design(cat_conn, "BD-91-MS", "BM-91-MS", keel_type="fin")
    _admit_design_keel_type(cat_conn, "BD-91-MS", value="fin")
    write_boat_design_category_assertion(
        cat_conn,
        boat_design_id="BD-91-MS",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-91-MS"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(
            assertion_kind=VA, value=VesselCategory.MOTORSAILER
        ),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    cat_conn.commit()
    _make_active_listing(
        cat_conn,
        listing_id="NL-91-MS",
        physical_boat_id="PB-91-MS",
        market_episode_id="ME-91-MS",
        boat_design_id="BD-91-MS",
        keel_configuration=KeelConfiguration.FIN,
    )
    assert "NL-91-MS" not in _query_result(cat_conn)


# ---------------------------------------------------------------------------
# Design/concrete disagreement -> CONFLICT -> excluded, never a best guess
# ---------------------------------------------------------------------------


def test_design_concrete_disagreement_excludes_confirmed_sail_match(cat_conn: Any) -> None:
    _insert_boat_design(cat_conn, "BD-91-CFL", "BM-91-CFL", keel_type="fin")
    _admit_design_keel_type(cat_conn, "BD-91-CFL", value="fin")
    write_boat_design_category_assertion(
        cat_conn,
        boat_design_id="BD-91-CFL",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-91-CFL"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    cat_conn.commit()
    account, org, membership = _make_active_listing(
        cat_conn,
        listing_id="NL-91-CFL",
        physical_boat_id="PB-91-CFL",
        market_episode_id="ME-91-CFL",
        boat_design_id="BD-91-CFL",
        keel_configuration=KeelConfiguration.FIN,
    )
    _write_vessel_category_claim(
        cat_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-91-CFL",
        revision_id="PBCREV-91-CFL-2",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    assert "NL-91-CFL" not in _query_result(cat_conn)


# ---------------------------------------------------------------------------
# Retraction: POWER -> UNKNOWN restores the confirmed Sail match
# ---------------------------------------------------------------------------


def test_retraction_to_unknown_restores_confirmed_sail_match(cat_conn: Any) -> None:
    _insert_boat_design(cat_conn, "BD-91-RET", "BM-91-RET", keel_type="fin")
    _admit_design_keel_type(cat_conn, "BD-91-RET", value="fin")
    account, org, membership = _make_active_listing(
        cat_conn,
        listing_id="NL-91-RET",
        physical_boat_id="PB-91-RET",
        market_episode_id="ME-91-RET",
        boat_design_id="BD-91-RET",
        keel_configuration=KeelConfiguration.FIN,
    )
    _write_vessel_category_claim(
        cat_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-91-RET",
        revision_id="PBCREV-91-RET-2",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    assert "NL-91-RET" not in _query_result(cat_conn)

    _write_vessel_category_claim(
        cat_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-91-RET",
        revision_id="PBCREV-91-RET-3",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=UNK, value=None),
    )
    assert "NL-91-RET" in _query_result(cat_conn)


# ---------------------------------------------------------------------------
# Missing design link: resolver-level proof (the funnel itself never admits
# a design-unresolved PhysicalBoat at all -- SLICE-0090 row B, not 0091).
# ---------------------------------------------------------------------------


def test_confirmed_non_match_retains_vessel_category_exclusion_evidence(cat_conn: Any) -> None:
    """Amendment review Finding I: a Sail-funnel exclusion produced by the
    SLICE-0091 category pre-filter is never a bare `CONFIRMED_NON_MATCH`
    mechanically indistinguishable from an ordinary technical mismatch --
    the resolved category/reason is retained, bounded to enum values only.
    """
    _insert_boat_design(cat_conn, "BD-91-EVID", "BM-91-EVID", keel_type="fin")
    _admit_design_keel_type(cat_conn, "BD-91-EVID", value="fin")
    account, org, membership = _make_active_listing(
        cat_conn,
        listing_id="NL-91-EVID",
        physical_boat_id="PB-91-EVID",
        market_episode_id="ME-91-EVID",
        boat_design_id="BD-91-EVID",
        keel_configuration=KeelConfiguration.FIN,
    )
    _write_vessel_category_claim(
        cat_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-91-EVID",
        revision_id="PBCREV-91-EVID-2",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    outcome = evaluate_native_inventory_requirements(
        cat_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    non_match = next(
        m for m in outcome.confirmed_non_matches if m.native_listing_id.value == "NL-91-EVID"
    )
    assert non_match.vessel_category_exclusion is not None
    assert non_match.vessel_category_exclusion.resolution is VesselCategoryResolution.POWER
    assert (
        non_match.vessel_category_exclusion.reason is VesselCategoryResolutionReason.CONCRETE_ONLY
    )
    # An ordinary confirmed Sail match never carries this evidence.
    for match in outcome.confirmed_matches:
        assert match.vessel_category_exclusion is None


def test_resolver_handles_design_unresolved_physical_boat(cat_conn: Any) -> None:
    with cat_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO physical_boats (physical_boat_id, boat_design_ref) VALUES (%s, NULL)",
            ["PB-91-NODSGN"],
        )
    cat_conn.commit()
    result = resolve_physical_boat_vessel_category(
        cat_conn, physical_boat_id=PhysicalBoatId("PB-91-NODSGN"), boat_design_ref=None
    )
    assert result.resolution.value == "UNKNOWN"
    assert result.is_explicitly_non_sail_or_conflicted is False
