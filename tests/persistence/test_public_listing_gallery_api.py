"""PostgreSQL + real HTTP tests for the SLICE-0069 public mixed-media gallery
projection and listing-scoped public derivative media route.

Covers contract §14/§15/§21/§22 "Public gallery" required proof: only
public-usable image derivatives appear, the explicit cover is reported,
YouTube renders from a normalized id only, the listing-scoped image route
serves the correct bytes for a genuine placement and rejects a foreign/
unknown listing or placement id with the identical bounded 404 -- never a
distinguishable error, and never a raw object key.
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
from hullq.domain.media_gallery import MediaPlacementId, MediaSourceKind
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
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
    create_youtube_placement,
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
from hullq.storage.object_storage import InMemoryObjectStorage

# ---------------------------------------------------------------------------
# Disposable-schema fixture
# ---------------------------------------------------------------------------


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
    schema_name = f"hullq_s0069gallery_{uuid.uuid4().hex[:16]}"
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


@pytest.fixture()
def object_storage() -> InMemoryObjectStorage:
    return InMemoryObjectStorage()


@pytest.fixture()
def client(api_url: str, object_storage: InMemoryObjectStorage) -> TestClient:
    from hullq.api.app import create_app

    app = create_app(
        database_url=api_url, preview_signing_secret=b"0" * 32, object_storage=object_storage
    )
    return TestClient(app)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


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


def _make_active_listing(
    conn: Any, *, listing_id: str, physical_boat_id: str, market_episode_id: str
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
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
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
        ),
    )
    return account, org, membership


def _attach_image(
    conn: Any,
    object_storage: InMemoryObjectStorage,
    *,
    listing_id: str,
    org: MarketplaceOrganization,
    account: AccountId,
    suffix: str,
    content: bytes,
) -> str:
    """Attach one approved, rights-declared IMAGE placement whose derivative
    bytes are actually stored in *object_storage* (unlike the bare-metadata
    D22-placeholder helpers elsewhere, this test needs real retrievable
    bytes). Returns the new placement id."""
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [account.value],
            )
        seed_marketplace_organization(conn, org)
        derivative_key = f"derivative/{listing_id}-{suffix}"
        object_storage.put_object(derivative_key, content, content_type="image/jpeg")
        asset = insert_approved_media_asset(
            conn,
            owner_organization_id=org.id,
            uploaded_by_account_id=account,
            rights_declared=True,
            source_kind=MediaSourceKind.BROKER_UPLOAD,
            source_reference=None,
            original_object_key=f"original/{listing_id}-{suffix}",
            derivative_object_key=derivative_key,
            content_hash=f"hash-{listing_id}-{suffix}",
            mime_type="image/jpeg",
            width=800,
            height=600,
            byte_size=len(content),
        )
        placement_result = create_uploaded_image_placement(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_asset=asset,
        )
        assert placement_result.media_placement_id is not None
        return placement_result.media_placement_id.value


def test_public_gallery_and_media_route(
    api_conn: Any, client: TestClient, object_storage: InMemoryObjectStorage
) -> None:
    listing_id = "NL-GALLERY-1"
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id=listing_id,
        physical_boat_id="PB-GALLERY-1",
        market_episode_id="ME-GALLERY-1",
    )

    cover_placement_id = _attach_image(
        api_conn,
        object_storage,
        listing_id=listing_id,
        org=org,
        account=account,
        suffix="cover",
        content=b"\xff\xd8cover-bytes",
    )
    second_placement_id = _attach_image(
        api_conn,
        object_storage,
        listing_id=listing_id,
        org=org,
        account=account,
        suffix="second",
        content=b"\xff\xd8second-bytes",
    )
    with api_conn.transaction():
        # The gallery head row already exists (created by the placement
        # appends above); its version is 2 after two appends.
        cover_result = set_cover(
            api_conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=MediaPlacementId(cover_placement_id),
            expected_version=2,
        )
    assert cover_result.outcome.value == "SET", cover_result

    youtube_result = create_youtube_placement(
        api_conn,
        native_listing_id=NativeListingId(listing_id),
        owner_organization_id=org.id,
        created_by_account_id=account,
        youtube_video_id="dQw4w9WgXcQ",
        youtube_source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    assert youtube_result.outcome.value == "CREATED"

    api_conn.commit()
    publish_result = publish_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result

    body = client.get(f"/api/listings/{listing_id}").json()
    assert body["cover_media_placement_id"] == cover_placement_id
    gallery = body["gallery"]
    assert [item["kind"] for item in gallery] == ["IMAGE", "IMAGE", "YOUTUBE"]
    assert {item["media_placement_id"] for item in gallery if item["kind"] == "IMAGE"} == {
        cover_placement_id,
        second_placement_id,
    }
    youtube_item = next(item for item in gallery if item["kind"] == "YOUTUBE")
    assert youtube_item["youtube_video_id"] == "dQw4w9WgXcQ"
    # Never a raw object key, uploader Account or provenance/source note.
    for item in gallery:
        assert "derivative_object_key" not in item
        assert "media_asset_id" not in item
        assert "uploaded_by_account_id" not in item

    cover_response = client.get(f"/api/listings/{listing_id}/media/{cover_placement_id}")
    assert cover_response.status_code == 200
    assert cover_response.content == b"\xff\xd8cover-bytes"
    assert cover_response.headers["content-type"] == "image/jpeg"

    second_response = client.get(f"/api/listings/{listing_id}/media/{second_placement_id}")
    assert second_response.status_code == 200
    assert second_response.content == b"\xff\xd8second-bytes"


def test_public_media_route_rejects_foreign_and_unknown_ids(
    api_conn: Any, client: TestClient, object_storage: InMemoryObjectStorage
) -> None:
    listing_id = "NL-GALLERY-2"
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id=listing_id,
        physical_boat_id="PB-GALLERY-2",
        market_episode_id="ME-GALLERY-2",
    )
    placement_id = _attach_image(
        api_conn,
        object_storage,
        listing_id=listing_id,
        org=org,
        account=account,
        suffix="only",
        content=b"\xff\xd8only-bytes",
    )
    with api_conn.transaction():
        cover_result = set_cover(
            api_conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=MediaPlacementId(placement_id),
            expected_version=1,
        )
    assert cover_result.outcome.value == "SET"
    api_conn.commit()
    publish_result = publish_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result

    other_listing_id = "NL-GALLERY-2-OTHER"
    other_account, other_org, other_membership = _make_active_listing(
        api_conn,
        listing_id=other_listing_id,
        physical_boat_id="PB-GALLERY-2-OTHER",
        market_episode_id="ME-GALLERY-2-OTHER",
    )
    other_placement_id = _attach_image(
        api_conn,
        object_storage,
        listing_id=other_listing_id,
        org=other_org,
        account=other_account,
        suffix="only",
        content=b"\xff\xd8other-bytes",
    )
    with api_conn.transaction():
        other_cover_result = set_cover(
            api_conn,
            native_listing_id=NativeListingId(other_listing_id),
            owner_organization_id=other_org.id,
            media_placement_id=MediaPlacementId(other_placement_id),
            expected_version=1,
        )
    assert other_cover_result.outcome.value == "SET"
    api_conn.commit()
    other_publish_result = publish_native_listing(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId(other_listing_id),
    )
    assert other_publish_result.status.value == "transitioned", other_publish_result

    # Unknown listing id entirely.
    unknown_listing = client.get(f"/api/listings/NL-NEVER-CREATED/media/{placement_id}")
    assert unknown_listing.status_code == 404

    # A real placement id, but requested under a different, real, public listing.
    foreign_pairing = client.get(f"/api/listings/{other_listing_id}/media/{placement_id}")
    assert foreign_pairing.status_code == 404

    # Unknown placement id under the real, public listing.
    unknown_placement = client.get(f"/api/listings/{listing_id}/media/PLACEMENT-NEVER-CREATED")
    assert unknown_placement.status_code == 404
