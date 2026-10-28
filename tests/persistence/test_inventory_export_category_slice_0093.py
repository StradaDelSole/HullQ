"""PostgreSQL-backed NautiX category-resolution export guard tests -- SLICE-0093
review amendment Finding B.

Proves `hullq.application.inventory_export._claim_physical_boat_facts` now
populates `ExportRow.vessel_category` from the **resolved** current category
(design plane + every current claiming Organization, combined by
`hullq.domain.vessel_category.resolve_vessel_category`) rather than only the
exporting Organization's own raw claim -- so a design-linked BoatDesign
positively categorized POWER with no publisher claim at all, and a
publisher-SAIL-vs-design-POWER disagreement, both fail the NautiX preflight
closed exactly like an explicit publisher POWER claim. Ordinary SAIL and
legacy (no category evidence anywhere) listings keep exporting unchanged --
the other six accepted formats are never affected by any of this.

Calls `build_export_snapshot` directly (the snapshot-assembly entry point
Finding B concerns) rather than the full authenticated HTTP route -- export
authorization/session/CSRF are an orthogonal, already-covered concern
(`tests/persistence/test_inventory_export_api.py`).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.inventory_export import (
    ExportFormat,
    ExportSelectionItem,
    build_export_snapshot,
)
from hullq.domain.inventory_export import build_row_preflight
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
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.provenance import ResolverKind, ResolverMetadata
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
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.boat_design_category import (
    CATALOG_ADMISSION_SECRET_ENV_VAR,
    write_boat_design_category_assertion,
)
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision

VA = AssertionKind.VALUE_ASSERTION
_TEST_ADMISSION_SECRET = "slice-0093-export-test-catalog-admission-secret"


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
def exp_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0093exp_{uuid.uuid4().hex[:16]}"
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
def exp_conn(exp_url: str) -> Generator[Any]:
    conn = psycopg.connect(exp_url)
    try:
        yield conn
    finally:
        conn.close()


def _as_of() -> datetime:
    return datetime.now(UTC)


def _issuer() -> ResolverMetadata:
    return ResolverMetadata(
        kind=ResolverKind.DETERMINISTIC_TOOL,
        identifier="slice-0093-export-test-harness",
        version="1",
    )


def _insert_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, '{}'::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, "1" * 64],
        )
    conn.commit()


def _assert_design_category(conn: Any, design_id: str, *, value: VesselCategory) -> None:
    write_boat_design_category_assertion(
        conn,
        boat_design_id=design_id,
        assertion_id=BoatDesignCategoryAssertionId(f"BDCAT-{design_id}"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=value),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    conn.commit()


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
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_id: str | None,
    vessel_category: VesselCategoryClaim | None,
    nautix_account_token: str = "ACCT-93EXP",
    nautix_office_id: str = "OFFICE-93EXP",
    sale_class: str = "used",
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id),
            boat_design_ref=BoatDesignRef(boat_design_id) if boat_design_id is not None else None,
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
            broker_description="A well-maintained yacht.",
            asking_price_amount=Decimal("199000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 40",
            build_year=BuildYearClaim(assertion_kind=VA, value=2019),
            vessel_category=vessel_category,
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
    conn.commit()
    return account, org, membership


def _nautix_exportable(
    conn: Any, *, organization_id: MarketplaceOrganizationId, listing_id: str
) -> tuple[bool, tuple[str, ...], str | None]:
    """Build a real snapshot for *listing_id* and return
    `(exportable, reasons, resolved_vessel_category)` for the NautiX format."""
    outcome, snapshot = build_export_snapshot(
        conn,
        organization_id=organization_id,
        selection=[ExportSelectionItem(native_listing_id=listing_id)],
        as_of=_as_of(),
        public_base_url=None,
    )
    assert outcome.value == "OK", outcome
    assert snapshot is not None
    assert len(snapshot.rows) == 1
    row = snapshot.rows[0]
    preflight = build_row_preflight(row)
    nautix = preflight.formats[ExportFormat.NAUTIX]
    return nautix.exportable, nautix.reasons, row.vessel_category


def test_ordinary_sail_listing_is_nautix_exportable(exp_conn: Any) -> None:
    _, org, _ = _make_active_listing(
        exp_conn,
        listing_id="NL-93EXP-SAIL",
        physical_boat_id="PB-93EXP-SAIL",
        market_episode_id="ME-93EXP-SAIL",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    _exportable, reasons, resolved = _nautix_exportable(
        exp_conn, organization_id=org.id, listing_id="NL-93EXP-SAIL"
    )
    assert resolved == "SAIL"
    # NautiX also requires model/LOA/sale-profile fields this harness never
    # supplies, so `exportable` itself stays False here for unrelated
    # reasons -- the only thing this test proves is that `boat_type` is
    # NOT rejected for category, i.e. no "boat_type" reason is present.
    assert not any("boat_type" in r for r in reasons)


def test_legacy_unknown_category_listing_is_nautix_exportable(exp_conn: Any) -> None:
    """No category evidence anywhere (no design link, no publisher claim) --
    the existing pre-0093 default-SAIL NautiX assumption must be preserved."""
    _, org, _ = _make_active_listing(
        exp_conn,
        listing_id="NL-93EXP-UNK",
        physical_boat_id="PB-93EXP-UNK",
        market_episode_id="ME-93EXP-UNK",
        boat_design_id=None,
        vessel_category=None,
    )
    _exportable, reasons, resolved = _nautix_exportable(
        exp_conn, organization_id=org.id, listing_id="NL-93EXP-UNK"
    )
    assert resolved == "UNKNOWN"
    assert not any("boat_type" in r for r in reasons)


def test_pure_publisher_power_claim_blocks_nautix_export(exp_conn: Any) -> None:
    _, org, _ = _make_active_listing(
        exp_conn,
        listing_id="NL-93EXP-PWR",
        physical_boat_id="PB-93EXP-PWR",
        market_episode_id="ME-93EXP-PWR",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    exportable, reasons, resolved = _nautix_exportable(
        exp_conn, organization_id=org.id, listing_id="NL-93EXP-PWR"
    )
    assert resolved == "POWER"
    assert exportable is False
    assert any("boat_type" in r for r in reasons)


def test_design_only_power_with_no_publisher_claim_blocks_nautix_export(exp_conn: Any) -> None:
    """Review amendment Finding B's headline scenario: a design-linked
    BoatDesign positively categorized POWER, with the publisher asserting
    NO category claim at all, must still be rejected -- the pre-amendment
    guard (reading only the publisher's own raw claim) would have let this
    row through as a default `sail-yacht`."""
    _insert_boat_design(exp_conn, "BD-93EXP-DPWR", "BM-93EXP-DPWR")
    _assert_design_category(exp_conn, "BD-93EXP-DPWR", value=VesselCategory.POWER)
    _, org, _ = _make_active_listing(
        exp_conn,
        listing_id="NL-93EXP-DPWR",
        physical_boat_id="PB-93EXP-DPWR",
        market_episode_id="ME-93EXP-DPWR",
        boat_design_id="BD-93EXP-DPWR",
        vessel_category=None,
    )
    exportable, reasons, resolved = _nautix_exportable(
        exp_conn, organization_id=org.id, listing_id="NL-93EXP-DPWR"
    )
    assert resolved == "POWER"
    assert exportable is False
    assert any("boat_type" in r for r in reasons)


def test_publisher_sail_vs_design_power_conflict_blocks_nautix_export(exp_conn: Any) -> None:
    """Review amendment Finding B's second scenario: the publisher asserts
    SAIL but the linked BoatDesign is positively POWER -- a resolved
    `CONFLICT`, not a free pass to the legacy SAIL default."""
    _insert_boat_design(exp_conn, "BD-93EXP-CONF", "BM-93EXP-CONF")
    _assert_design_category(exp_conn, "BD-93EXP-CONF", value=VesselCategory.POWER)
    _, org, _ = _make_active_listing(
        exp_conn,
        listing_id="NL-93EXP-CONF",
        physical_boat_id="PB-93EXP-CONF",
        market_episode_id="ME-93EXP-CONF",
        boat_design_id="BD-93EXP-CONF",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    exportable, reasons, resolved = _nautix_exportable(
        exp_conn, organization_id=org.id, listing_id="NL-93EXP-CONF"
    )
    assert resolved == "CONFLICT"
    assert exportable is False
    assert any("boat_type" in r for r in reasons)


def test_design_linked_sail_agreeing_with_publisher_is_nautix_exportable(exp_conn: Any) -> None:
    """Control: a design-linked listing where design and publisher agree on
    SAIL keeps exporting -- the amendment must not newly block ordinary
    agreeing Sail inventory."""
    _insert_boat_design(exp_conn, "BD-93EXP-DSAIL", "BM-93EXP-DSAIL")
    _assert_design_category(exp_conn, "BD-93EXP-DSAIL", value=VesselCategory.SAIL)
    _, org, _ = _make_active_listing(
        exp_conn,
        listing_id="NL-93EXP-DSAIL",
        physical_boat_id="PB-93EXP-DSAIL",
        market_episode_id="ME-93EXP-DSAIL",
        boat_design_id="BD-93EXP-DSAIL",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    _exportable, reasons, resolved = _nautix_exportable(
        exp_conn, organization_id=org.id, listing_id="NL-93EXP-DSAIL"
    )
    assert resolved == "SAIL"
    assert not any("boat_type" in r for r in reasons)
