"""PostgreSQL + real HTTP tests for the SLICE-0093 `/api/search/{locale}/power`
Power-only Search route.

Covers the HTTP contract (200 base/result, 308 canonical redirect, 400
invalid, 404 unsupported locale, noindex) end to end through the real
FastAPI app -- the underlying Search truth itself is proven separately in
`tests/persistence/test_power_inventory_query_slice_0093.py`. Mirrors
`tests/persistence/test_inventory_search_draft_max_api.py`'s disposable-
schema isolation pattern.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from hullq.domain.market_identity import (
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
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
    VesselCategory,
    VesselCategoryClaim,
)
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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
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
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0093api_{uuid.uuid4().hex[:16]}"
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
def api_conn(api_url: str) -> Generator[Any]:
    conn = psycopg.connect(api_url)
    try:
        yield conn
    finally:
        conn.close()


_SECRET = b"0" * 32


@pytest.fixture()
def client(api_url: str) -> TestClient:
    from hullq.api.app import create_app

    app = create_app(database_url=api_url, preview_signing_secret=_SECRET)
    return TestClient(app)


def _seed_design_unresolved_power_listing(conn: Any, *, listing_id: str, drive: str) -> None:
    account = AccountId(f"ACC-{listing_id}")
    org = MarketplaceOrganization(
        id=MarketplaceOrganizationId(f"ORG-{listing_id}"),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-{listing_id}"),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(id=PhysicalBoatId(f"PB-{listing_id}"), boat_design_ref=None),
    )
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(f"ME-{listing_id}"),
            physical_boat_id=PhysicalBoatId(f"PB-{listing_id}"),
        ),
    )
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(f"ME-{listing_id}")
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
            broker_description="A well-maintained motor yacht.",
            asking_price_amount=Decimal("250000.00"),
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
            model_designation_claim="Swift Trawler 35",
            build_year=BuildYearClaim(assertion_kind=VA, value=2020),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration(drive)
            ),
        ),
    )
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
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    conn.commit()


def test_base_state_returns_200_with_no_active_requirement(client: TestClient) -> None:
    response = client.get("/api/search/de/power")
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] is None
    assert response.headers.get("x-robots-tag") == "noindex"


def test_unsupported_locale_404(client: TestClient) -> None:
    response = client.get("/api/search/it/power?power_drive=POD", follow_redirects=False)
    assert response.status_code == 404


def test_unsupported_power_drive_value_400(client: TestClient) -> None:
    response = client.get(
        "/api/search/de/power?power_drive=DIESEL_ELECTRIC", follow_redirects=False
    )
    assert response.status_code == 400


def test_sail_key_on_power_surface_is_400(client: TestClient) -> None:
    """Required Behavior §3: the Power route never accepts a Sail key."""
    response = client.get("/api/search/de/power?draft_max=1.6", follow_redirects=False)
    assert response.status_code == 400


def test_equal_duplicates_redirect_308(client: TestClient) -> None:
    response = client.get(
        "/api/search/de/power?power_drive=POD&power_drive=POD", follow_redirects=False
    )
    assert response.status_code == 308
    assert response.headers["location"] == "/de/power/search?power_drive=POD"


def test_conflicting_duplicates_400(client: TestClient) -> None:
    response = client.get(
        "/api/search/de/power?power_drive=POD&power_drive=SHAFT", follow_redirects=False
    )
    assert response.status_code == 400


def test_design_unresolved_power_pod_claim_is_a_confirmed_publisher_claim_match(
    client: TestClient, api_conn: Any
) -> None:
    _seed_design_unresolved_power_listing(api_conn, listing_id="NL-93API-POD", drive="POD")
    response = client.get("/api/search/en/power?power_drive=POD", follow_redirects=False)
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] == {"power_drive": "POD"}
    assert body["design_linked_match_count"] == 0
    assert body["publisher_claim_match_count"] == 1
    match = body["publisher_claim_matches"][0]
    assert match["native_listing_id"] == "NL-93API-POD"
    assert match["source_basis"] == "PUBLISHER_CLAIM"
    assert response.headers.get("x-robots-tag") == "noindex"


def test_sail_search_route_never_accepts_power_drive_key(client: TestClient) -> None:
    """Required Behavior §3: the existing Sail parser never widens to accept
    a Power key -- unknown-key 400, exactly like any other foreign key."""
    response = client.get("/api/search/en?power_drive=POD", follow_redirects=False)
    assert response.status_code == 400
