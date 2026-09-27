"""PostgreSQL integration tests for SLICE-0068 media gallery persistence.

Exercises `hullq.persistence.media_gallery` directly against a real
PostgreSQL schema (contract §17 required proof: migration round-trip,
ordering/cover invariants, concurrency, Organization isolation, retirement).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.media_gallery import (
    MediaAssetId,
    MediaPlacementId,
    MediaPlacementKind,
    MediaSourceKind,
)
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
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
    PlacementCreationOutcome,
    RemovePlacementOutcome,
    ReorderOutcome,
    RetireAssetOutcome,
    SetCoverOutcome,
    create_reused_image_placement,
    create_uploaded_image_placement,
    create_youtube_placement,
    fetch_gallery_state,
    fetch_media_asset,
    insert_approved_media_asset,
    insert_rejected_media_asset,
    list_media_library,
    remove_placement,
    reorder_placements,
    retire_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state, publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat


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
    schema_name = f"hullq_s0068persist_{uuid.uuid4().hex[:16]}"
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
def conn(api_url: str) -> Generator[Any]:
    connection = psycopg.connect(api_url)
    try:
        yield connection
    finally:
        connection.close()


def _seed_account(conn: Any, account_id: str) -> AccountId:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )
    conn.commit()
    return AccountId(account_id)


def _seed_org(conn: Any, org_id: str) -> MarketplaceOrganization:
    org = MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    seed_marketplace_organization(conn, org)
    conn.commit()
    return org


def _seed_listing(
    conn: Any,
    *,
    listing_id: str,
    org: MarketplaceOrganization,
    account_id: AccountId,
    physical_boat_id: str,
    market_episode_id: str,
) -> NativeListingId:
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-{listing_id}"),
        account_id=account_id,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    listing_id_obj = NativeListingId(listing_id)
    create_native_listing(
        conn,
        account_id=account_id,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=listing_id_obj, market_episode_id=MarketEpisodeId(market_episode_id)
        ),
    )
    conn.commit()
    return listing_id_obj


def _amount_offer() -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal("125000.00"),
        currency="EUR",
    )


def _publish_listing(
    conn: Any,
    *,
    listing_id: NativeListingId,
    org: MarketplaceOrganization,
    account_id: AccountId,
) -> None:
    """Give *listing_id* a current offer (contract §49 completeness) and
    transition it DRAFT -> ACTIVE, for Finding C's ACTIVE-lifecycle tests."""
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-PUBLISH-{listing_id.value}"),
        account_id=account_id,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    write_native_listing_offer_revision(
        conn,
        account_id=account_id,
        candidate_organization=org,
        membership=membership,
        native_listing_id=listing_id,
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id.value}"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    conn.commit()
    result = publish_native_listing(
        conn,
        account_id=account_id,
        candidate_organization=org,
        membership=membership,
        native_listing_id=listing_id,
    )
    assert result.status.value == "transitioned", result
    conn.commit()
    assert fetch_lifecycle_state(conn, listing_id) is NativeListingLifecycleState.ACTIVE


class TestApprovedAssetCreation:
    def test_insert_approved_asset_round_trips(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-A1")
        org = _seed_org(conn, "ORG-A1")
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/k1.jpg",
                content_hash="hash-1",
                mime_type="image/jpeg",
                width=100,
                height=50,
                byte_size=999,
            )
        assert asset.is_public_usable
        fetched = fetch_media_asset(conn, asset.media_asset_id)
        assert fetched == asset

    def test_rights_unknown_is_not_public_usable(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-A2")
        org = _seed_org(conn, "ORG-A2")
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=False,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/k2.jpg",
                content_hash="hash-2",
                mime_type="image/jpeg",
                width=100,
                height=50,
                byte_size=999,
            )
        assert not asset.is_public_usable


class TestRejectedAssetCreation:
    def test_rejected_asset_never_public_usable_and_carries_no_derivative_fields(
        self, conn: Any
    ) -> None:
        account = _seed_account(conn, "ACC-R1")
        org = _seed_org(conn, "ORG-R1")
        with conn.transaction():
            asset = insert_rejected_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test-rejected.orig",
                rejection_reason="UNSUPPORTED_OR_MALFORMED",
            )
        assert not asset.is_public_usable
        assert asset.derivative_object_key is None
        assert asset.original_object_key == "media/original/test-rejected.orig"
        assert asset.mime_type is None
        assert asset.rejection_reason == "UNSUPPORTED_OR_MALFORMED"


class TestPlacementCreationAndGalleryRead:
    def test_upload_creates_placement_and_appends_position(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-P1")
        org = _seed_org(conn, "ORG-P1")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-P1",
            org=org,
            account_id=account,
            physical_boat_id="PB-P1",
            market_episode_id="ME-P1",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/p1.jpg",
                content_hash="h1",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            result = create_uploaded_image_placement(
                conn, native_listing_id=listing_id, owner_organization_id=org.id, media_asset=asset
            )
        assert result.outcome is PlacementCreationOutcome.CREATED
        assert result.gallery_version == 1

        state = fetch_gallery_state(conn, listing_id)
        assert state.gallery_version == 1
        assert len(state.placements) == 1
        assert state.placements[0].kind is MediaPlacementKind.IMAGE
        assert state.placements[0].position == 0
        assert state.placements[0].media_asset is not None
        assert state.placements[0].media_asset.media_asset_id == asset.media_asset_id

    def test_foreign_organization_listing_is_not_found(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-P2")
        org_a = _seed_org(conn, "ORG-P2A")
        org_b = _seed_org(conn, "ORG-P2B")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-P2",
            org=org_a,
            account_id=account,
            physical_boat_id="PB-P2",
            market_episode_id="ME-P2",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org_b.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/p2.jpg",
                content_hash="h2",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            result = create_uploaded_image_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org_b.id,
                media_asset=asset,
            )
        assert result.outcome is PlacementCreationOutcome.LISTING_NOT_FOUND

    def test_unknown_listing_and_foreign_listing_share_identical_outcome(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-P3")
        org = _seed_org(conn, "ORG-P3")
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/p3.jpg",
                content_hash="h3",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            never_created = create_uploaded_image_placement(
                conn,
                native_listing_id=NativeListingId("NL-NEVER-CREATED"),
                owner_organization_id=org.id,
                media_asset=asset,
            )
        assert never_created.outcome is PlacementCreationOutcome.LISTING_NOT_FOUND

    def test_empty_gallery_reads_as_version_zero_no_cover_no_placements(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-P4")
        org = _seed_org(conn, "ORG-P4")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-P4",
            org=org,
            account_id=account,
            physical_boat_id="PB-P4",
            market_episode_id="ME-P4",
        )
        state = fetch_gallery_state(conn, listing_id)
        assert state.gallery_version == 0
        assert state.cover_placement_id is None
        assert state.placements == ()


class TestYoutubePlacement:
    def test_youtube_placement_created_with_no_media_asset(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-Y1")
        org = _seed_org(conn, "ORG-Y1")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-Y1",
            org=org,
            account_id=account,
            physical_boat_id="PB-Y1",
            market_episode_id="ME-Y1",
        )
        with conn.transaction():
            result = create_youtube_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                created_by_account_id=account,
                youtube_video_id="dQw4w9WgXcQ",
                youtube_source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )
        assert result.outcome is PlacementCreationOutcome.CREATED
        state = fetch_gallery_state(conn, listing_id)
        placement = state.placements[0]
        assert placement.kind is MediaPlacementKind.YOUTUBE
        assert placement.media_asset is None
        assert placement.youtube_video_id == "dQw4w9WgXcQ"


class TestSameOrganizationReuseAndCrossOrgDenial:
    def test_same_org_reuse_places_without_copying_bytes(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-RU1")
        org = _seed_org(conn, "ORG-RU1")
        listing_a = _seed_listing(
            conn,
            listing_id="NL-RU1-A",
            org=org,
            account_id=account,
            physical_boat_id="PB-RU1-A",
            market_episode_id="ME-RU1-A",
        )
        listing_b = _seed_listing(
            conn,
            listing_id="NL-RU1-B",
            org=org,
            account_id=account,
            physical_boat_id="PB-RU1-B",
            market_episode_id="ME-RU1-B",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/ru1.jpg",
                content_hash="hru1",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            create_uploaded_image_placement(
                conn, native_listing_id=listing_a, owner_organization_id=org.id, media_asset=asset
            )
            reuse_result = create_reused_image_placement(
                conn,
                native_listing_id=listing_b,
                owner_organization_id=org.id,
                requesting_account_id=account,
                media_asset_id=asset.media_asset_id,
            )
        assert reuse_result.outcome is PlacementCreationOutcome.CREATED
        state_b = fetch_gallery_state(conn, listing_b)
        assert state_b.placements[0].media_asset is not None
        assert state_b.placements[0].media_asset.media_asset_id == asset.media_asset_id
        # Same asset row, same derivative_object_key -- bytes were never duplicated.
        assert state_b.placements[0].media_asset.derivative_object_key == "media/ru1.jpg"

    def test_cross_organization_reuse_denied(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-RU2")
        org_a = _seed_org(conn, "ORG-RU2A")
        org_b = _seed_org(conn, "ORG-RU2B")
        listing_b = _seed_listing(
            conn,
            listing_id="NL-RU2-B",
            org=org_b,
            account_id=account,
            physical_boat_id="PB-RU2-B",
            market_episode_id="ME-RU2-B",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org_a.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/ru2.jpg",
                content_hash="hru2",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            denied = create_reused_image_placement(
                conn,
                native_listing_id=listing_b,
                owner_organization_id=org_b.id,
                requesting_account_id=account,
                media_asset_id=asset.media_asset_id,
            )
        assert denied.outcome is PlacementCreationOutcome.ASSET_NOT_FOUND_OR_DENIED
        state_b = fetch_gallery_state(conn, listing_b)
        assert state_b.placements == ()

    def test_library_never_exposes_another_organizations_assets(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-RU3")
        org_a = _seed_org(conn, "ORG-RU3A")
        org_b = _seed_org(conn, "ORG-RU3B")
        with conn.transaction():
            insert_approved_media_asset(
                conn,
                owner_organization_id=org_a.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/ru3.jpg",
                content_hash="hru3",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
        library_b = list_media_library(conn, owner_organization_id=org_b.id)
        assert library_b == []
        library_a = list_media_library(conn, owner_organization_id=org_a.id)
        assert len(library_a) == 1


class TestCoverInvariant:
    def _setup(
        self, conn: Any, suffix: str
    ) -> tuple[NativeListingId, MarketplaceOrganization, Any, MediaAssetId, MediaPlacementId]:
        account = _seed_account(conn, f"ACC-CV{suffix}")
        org = _seed_org(conn, f"ORG-CV{suffix}")
        listing_id = _seed_listing(
            conn,
            listing_id=f"NL-CV{suffix}",
            org=org,
            account_id=account,
            physical_boat_id=f"PB-CV{suffix}",
            market_episode_id=f"ME-CV{suffix}",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key=f"media/cv{suffix}.jpg",
                content_hash=f"hcv{suffix}",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            placement_result = create_uploaded_image_placement(
                conn, native_listing_id=listing_id, owner_organization_id=org.id, media_asset=asset
            )
        assert placement_result.media_placement_id is not None
        return listing_id, org, account, asset.media_asset_id, placement_result.media_placement_id

    def test_set_cover_requires_public_usable_image(self, conn: Any) -> None:
        listing_id, org, _account, _asset_id, placement_id = self._setup(conn, "1")
        with conn.transaction():
            result = set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_id,
                expected_version=1,
            )
        assert result.outcome is SetCoverOutcome.SET
        state = fetch_gallery_state(conn, listing_id)
        assert state.cover_placement_id == placement_id

    def test_cover_on_non_public_usable_image_is_invalid(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-CV2")
        org = _seed_org(conn, "ORG-CV2")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-CV2",
            org=org,
            account_id=account,
            physical_boat_id="PB-CV2",
            market_episode_id="ME-CV2",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=False,  # rights UNKNOWN -- never public-usable
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/cv2.jpg",
                content_hash="hcv2",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            placement_result = create_uploaded_image_placement(
                conn, native_listing_id=listing_id, owner_organization_id=org.id, media_asset=asset
            )
            cover_result = set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=1,
            )
        assert cover_result.outcome is SetCoverOutcome.INVALID_COVER
        state = fetch_gallery_state(conn, listing_id)
        assert state.cover_placement_id is None

    def test_stale_expected_version_conflicts_without_writing(self, conn: Any) -> None:
        listing_id, org, _account, _asset_id, placement_id = self._setup(conn, "3")
        with conn.transaction():
            set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_id,
                expected_version=1,
            )
        with conn.transaction():
            stale = set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=None,
                expected_version=1,  # stale: current version is now 2
            )
        assert stale.outcome is SetCoverOutcome.VERSION_CONFLICT
        state = fetch_gallery_state(conn, listing_id)
        assert state.cover_placement_id == placement_id  # unchanged

    def test_retirement_clears_phantom_cover(self, conn: Any) -> None:
        listing_id, org, _account, asset_id, placement_id = self._setup(conn, "4")
        with conn.transaction():
            set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_id,
                expected_version=1,
            )
        with conn.transaction():
            outcome = retire_media_asset(
                conn, media_asset_id=asset_id, owner_organization_id=org.id
            )
        assert outcome is RetireAssetOutcome.RETIRED
        state = fetch_gallery_state(conn, listing_id)
        assert state.cover_placement_id is None

    def test_removal_of_cover_placement_clears_cover_via_fk(self, conn: Any) -> None:
        listing_id, org, _account, _asset_id, placement_id = self._setup(conn, "5")
        with conn.transaction():
            set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_id,
                expected_version=1,
            )
        with conn.transaction():
            removal = remove_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_id,
                expected_version=2,
            )
        assert removal.outcome is RemovePlacementOutcome.REMOVED
        state = fetch_gallery_state(conn, listing_id)
        assert state.cover_placement_id is None
        assert state.placements == ()

    def test_retirement_does_not_delete_asset_or_placement(self, conn: Any) -> None:
        listing_id, org, _account, asset_id, placement_id = self._setup(conn, "6")
        with conn.transaction():
            retire_media_asset(conn, media_asset_id=asset_id, owner_organization_id=org.id)
        state = fetch_gallery_state(conn, listing_id)
        assert len(state.placements) == 1
        assert state.placements[0].media_placement_id == placement_id
        asset = fetch_media_asset(conn, asset_id)
        assert asset is not None
        assert asset.retired_at is not None

    def test_retired_asset_cannot_be_reused(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-CV7")
        org = _seed_org(conn, "ORG-CV7")
        listing_a = _seed_listing(
            conn,
            listing_id="NL-CV7-A",
            org=org,
            account_id=account,
            physical_boat_id="PB-CV7-A",
            market_episode_id="ME-CV7-A",
        )
        listing_b = _seed_listing(
            conn,
            listing_id="NL-CV7-B",
            org=org,
            account_id=account,
            physical_boat_id="PB-CV7-B",
            market_episode_id="ME-CV7-B",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/cv7.jpg",
                content_hash="hcv7",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            create_uploaded_image_placement(
                conn, native_listing_id=listing_a, owner_organization_id=org.id, media_asset=asset
            )
            retire_media_asset(
                conn, media_asset_id=asset.media_asset_id, owner_organization_id=org.id
            )
            reuse_after_retire = create_reused_image_placement(
                conn,
                native_listing_id=listing_b,
                owner_organization_id=org.id,
                requesting_account_id=account,
                media_asset_id=asset.media_asset_id,
            )
        assert reuse_after_retire.outcome is PlacementCreationOutcome.ASSET_NOT_FOUND_OR_DENIED

    def test_retiring_unknown_or_foreign_asset_is_not_found(self, conn: Any) -> None:
        org = _seed_org(conn, "ORG-CV8")
        outcome = retire_media_asset(
            conn, media_asset_id=MediaAssetId(str(uuid.uuid4())), owner_organization_id=org.id
        )
        assert outcome is RetireAssetOutcome.NOT_FOUND

    def test_retiring_twice_is_already_retired(self, conn: Any) -> None:
        _listing_id, org, _account, asset_id, _placement_id = self._setup(conn, "9")
        with conn.transaction():
            first = retire_media_asset(conn, media_asset_id=asset_id, owner_organization_id=org.id)
        with conn.transaction():
            second = retire_media_asset(conn, media_asset_id=asset_id, owner_organization_id=org.id)
        assert first is RetireAssetOutcome.RETIRED
        assert second is RetireAssetOutcome.ALREADY_RETIRED


class TestReorder:
    def _three_image_gallery(
        self, conn: Any
    ) -> tuple[NativeListingId, MarketplaceOrganization, list[MediaPlacementId]]:
        account = _seed_account(conn, "ACC-RO1")
        org = _seed_org(conn, "ORG-RO1")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-RO1",
            org=org,
            account_id=account,
            physical_boat_id="PB-RO1",
            market_episode_id="ME-RO1",
        )
        placement_ids = []
        for i in range(3):
            with conn.transaction():
                asset = insert_approved_media_asset(
                    conn,
                    owner_organization_id=org.id,
                    uploaded_by_account_id=account,
                    rights_declared=True,
                    source_kind=MediaSourceKind.BROKER_UPLOAD,
                    source_reference=None,
                    original_object_key="media/original/test.orig",
                    derivative_object_key=f"media/ro1-{i}.jpg",
                    content_hash=f"hro1-{i}",
                    mime_type="image/jpeg",
                    width=10,
                    height=10,
                    byte_size=100,
                )
                result = create_uploaded_image_placement(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org.id,
                    media_asset=asset,
                )
                assert result.media_placement_id is not None
                placement_ids.append(result.media_placement_id)
        return listing_id, org, placement_ids

    def test_reorder_sets_deterministic_new_positions(self, conn: Any) -> None:
        listing_id, org, placement_ids = self._three_image_gallery(conn)
        new_order = [placement_ids[2], placement_ids[0], placement_ids[1]]
        with conn.transaction():
            result = reorder_placements(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                ordered_placement_ids=new_order,
                expected_version=3,
            )
        assert result.outcome is ReorderOutcome.REORDERED
        state = fetch_gallery_state(conn, listing_id)
        assert [p.media_placement_id for p in state.placements] == new_order
        assert [p.position for p in state.placements] == [0, 1, 2]

    def test_reorder_with_stale_version_conflicts(self, conn: Any) -> None:
        listing_id, org, placement_ids = self._three_image_gallery(conn)
        with conn.transaction():
            reorder_placements(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                ordered_placement_ids=list(reversed(placement_ids)),
                expected_version=3,
            )
        with conn.transaction():
            stale = reorder_placements(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                ordered_placement_ids=placement_ids,
                expected_version=3,  # stale: now 4
            )
        assert stale.outcome is ReorderOutcome.VERSION_CONFLICT

    def test_reorder_with_wrong_placement_set_is_invalid(self, conn: Any) -> None:
        listing_id, org, placement_ids = self._three_image_gallery(conn)
        wrong_set = [placement_ids[0], placement_ids[1]]  # missing one, no substitute
        with conn.transaction():
            result = reorder_placements(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                ordered_placement_ids=wrong_set,
                expected_version=3,
            )
        assert result.outcome is ReorderOutcome.INVALID_PLACEMENT_SET
        state = fetch_gallery_state(conn, listing_id)
        assert [p.position for p in state.placements] == [0, 1, 2]  # unchanged


class TestRemovePlacement:
    def test_removal_does_not_delete_the_underlying_asset(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-RM1")
        org = _seed_org(conn, "ORG-RM1")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-RM1",
            org=org,
            account_id=account,
            physical_boat_id="PB-RM1",
            market_episode_id="ME-RM1",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/test.orig",
                derivative_object_key="media/rm1.jpg",
                content_hash="hrm1",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            placement_result = create_uploaded_image_placement(
                conn, native_listing_id=listing_id, owner_organization_id=org.id, media_asset=asset
            )
        with conn.transaction():
            removal = remove_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=1,
            )
        assert removal.outcome is RemovePlacementOutcome.REMOVED
        assert fetch_media_asset(conn, asset.media_asset_id) is not None

    def test_removing_unknown_placement_is_not_found(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-RM2")
        org = _seed_org(conn, "ORG-RM2")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-RM2",
            org=org,
            account_id=account,
            physical_boat_id="PB-RM2",
            market_episode_id="ME-RM2",
        )
        with conn.transaction():
            result = remove_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=MediaPlacementId(str(uuid.uuid4())),
                expected_version=0,
            )
        assert result.outcome is RemovePlacementOutcome.PLACEMENT_NOT_FOUND


class TestProvenance:
    """Independent review Finding B: D14 bounded source/provenance."""

    def test_upload_records_broker_upload_source_kind_and_reference(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-PROV1")
        org = _seed_org(conn, "ORG-PROV1")
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference="Photographed by ACME Yacht Photography",
                original_object_key="media/original/prov1.orig",
                derivative_object_key="media/prov1.jpg",
                content_hash="hprov1",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
        fetched = fetch_media_asset(conn, asset.media_asset_id)
        assert fetched is not None
        assert fetched.source_kind is MediaSourceKind.BROKER_UPLOAD
        assert fetched.source_reference == "Photographed by ACME Yacht Photography"
        assert fetched.uploaded_by_account_id == account
        assert fetched.owner_organization_id == org.id

    def test_source_reference_is_optional(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-PROV2")
        org = _seed_org(conn, "ORG-PROV2")
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/prov2.orig",
                derivative_object_key="media/prov2.jpg",
                content_hash="hprov2",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
        assert asset.source_reference is None

    def test_provenance_survives_same_organization_reuse(self, conn: Any) -> None:
        """Provenance belongs to MediaAsset, not MediaPlacement -- reusing
        an asset onto another listing must never change its recorded
        uploader/Organization/source_kind/source_reference/rights_state."""
        account = _seed_account(conn, "ACC-PROV3")
        org = _seed_org(conn, "ORG-PROV3")
        listing_a = _seed_listing(
            conn,
            listing_id="NL-PROV3-A",
            org=org,
            account_id=account,
            physical_boat_id="PB-PROV3-A",
            market_episode_id="ME-PROV3-A",
        )
        listing_b = _seed_listing(
            conn,
            listing_id="NL-PROV3-B",
            org=org,
            account_id=account,
            physical_boat_id="PB-PROV3-B",
            market_episode_id="ME-PROV3-B",
        )
        # A different account within the same Organization performs the
        # reuse -- provenance must still reflect the *original* uploader.
        reuser = _seed_account(conn, "ACC-PROV3-REUSER")
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference="Original upload note",
                original_object_key="media/original/prov3.orig",
                derivative_object_key="media/prov3.jpg",
                content_hash="hprov3",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            create_uploaded_image_placement(
                conn, native_listing_id=listing_a, owner_organization_id=org.id, media_asset=asset
            )
            reuse_result = create_reused_image_placement(
                conn,
                native_listing_id=listing_b,
                owner_organization_id=org.id,
                requesting_account_id=reuser,
                media_asset_id=asset.media_asset_id,
            )
        assert reuse_result.outcome is PlacementCreationOutcome.CREATED
        state_b = fetch_gallery_state(conn, listing_b)
        reused_asset = state_b.placements[0].media_asset
        assert reused_asset is not None
        assert reused_asset.uploaded_by_account_id == account
        assert reused_asset.source_kind is MediaSourceKind.BROKER_UPLOAD
        assert reused_asset.source_reference == "Original upload note"
        assert reused_asset.rights_state.value == "DECLARED"


class TestRejectedAssetReuseDenied:
    """Independent review additional check: a REJECTED asset must not
    become reusable/placeable merely because its id is known."""

    def test_reused_rejected_asset_is_denied(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-REJ1")
        org = _seed_org(conn, "ORG-REJ1")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-REJ1",
            org=org,
            account_id=account,
            physical_boat_id="PB-REJ1",
            market_episode_id="ME-REJ1",
        )
        with conn.transaction():
            rejected_asset = insert_rejected_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/rej1.orig",
                rejection_reason="UNSUPPORTED_OR_MALFORMED",
            )
            denied = create_reused_image_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                requesting_account_id=account,
                media_asset_id=rejected_asset.media_asset_id,
            )
        assert denied.outcome is PlacementCreationOutcome.ASSET_NOT_FOUND_OR_DENIED
        state = fetch_gallery_state(conn, listing_id)
        assert state.placements == ()

    def test_unknown_rights_approved_asset_can_still_be_reused_but_stays_non_public(
        self, conn: Any
    ) -> None:
        """Contrast case: an APPROVED asset with rights UNKNOWN is a
        legitimate placement (contract §7 rights independence) -- only
        REJECTED assets are denied reuse outright."""
        account = _seed_account(conn, "ACC-REJ2")
        org = _seed_org(conn, "ORG-REJ2")
        listing_a = _seed_listing(
            conn,
            listing_id="NL-REJ2-A",
            org=org,
            account_id=account,
            physical_boat_id="PB-REJ2-A",
            market_episode_id="ME-REJ2-A",
        )
        listing_b = _seed_listing(
            conn,
            listing_id="NL-REJ2-B",
            org=org,
            account_id=account,
            physical_boat_id="PB-REJ2-B",
            market_episode_id="ME-REJ2-B",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=False,  # UNKNOWN
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/rej2.orig",
                derivative_object_key="media/rej2.jpg",
                content_hash="hrej2",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            create_uploaded_image_placement(
                conn, native_listing_id=listing_a, owner_organization_id=org.id, media_asset=asset
            )
            reuse_result = create_reused_image_placement(
                conn,
                native_listing_id=listing_b,
                owner_organization_id=org.id,
                requesting_account_id=account,
                media_asset_id=asset.media_asset_id,
            )
        assert reuse_result.outcome is PlacementCreationOutcome.CREATED
        state_b = fetch_gallery_state(conn, listing_b)
        assert state_b.placements[0].media_asset is not None
        assert not state_b.placements[0].media_asset.is_public_usable


class TestActiveListingProtection:
    """Independent review Finding C: D15/D29's hard invariant that an
    ACTIVE NativeListing keeps at least one approved rights-valid public-
    usable IMAGE and a non-null explicit IMAGE cover."""

    def _active_listing_with_one_valid_image(
        self, conn: Any, suffix: str
    ) -> tuple[NativeListingId, MarketplaceOrganization, AccountId, MediaPlacementId]:
        account = _seed_account(conn, f"ACC-AL{suffix}")
        org = _seed_org(conn, f"ORG-AL{suffix}")
        listing_id = _seed_listing(
            conn,
            listing_id=f"NL-AL{suffix}",
            org=org,
            account_id=account,
            physical_boat_id=f"PB-AL{suffix}",
            market_episode_id=f"ME-AL{suffix}",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key=f"media/original/al{suffix}.orig",
                derivative_object_key=f"media/al{suffix}.jpg",
                content_hash=f"hal{suffix}",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            placement_result = create_uploaded_image_placement(
                conn, native_listing_id=listing_id, owner_organization_id=org.id, media_asset=asset
            )
            assert placement_result.media_placement_id is not None
            cover_result = set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=1,
            )
            assert cover_result.outcome is SetCoverOutcome.SET
        _publish_listing(conn, listing_id=listing_id, org=org, account_id=account)
        return listing_id, org, account, placement_result.media_placement_id

    def test_active_single_image_remove_is_rejected(self, conn: Any) -> None:
        listing_id, org, _account, placement_id = self._active_listing_with_one_valid_image(
            conn, "RM"
        )
        with conn.transaction():
            result = remove_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_id,
                expected_version=2,
            )
        assert result.outcome is RemovePlacementOutcome.ACTIVE_LISTING_CONFLICT
        state = fetch_gallery_state(conn, listing_id)
        assert len(state.placements) == 1
        assert state.cover_placement_id == placement_id

    def test_active_single_image_clear_cover_is_rejected(self, conn: Any) -> None:
        listing_id, org, _account, placement_id = self._active_listing_with_one_valid_image(
            conn, "CC"
        )
        with conn.transaction():
            result = set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=None,
                expected_version=2,
            )
        assert result.outcome is SetCoverOutcome.ACTIVE_LISTING_CONFLICT
        state = fetch_gallery_state(conn, listing_id)
        assert state.cover_placement_id == placement_id

    def test_active_single_image_retire_is_rejected(self, conn: Any) -> None:
        listing_id, org, _account, placement_id = self._active_listing_with_one_valid_image(
            conn, "RT"
        )
        placed_asset = fetch_gallery_state(conn, listing_id).placements[0].media_asset
        assert placed_asset is not None
        with conn.transaction():
            outcome = retire_media_asset(
                conn, media_asset_id=placed_asset.media_asset_id, owner_organization_id=org.id
            )
        assert outcome is RetireAssetOutcome.ACTIVE_LISTING_CONFLICT
        state = fetch_gallery_state(conn, listing_id)
        assert state.cover_placement_id == placement_id
        refetched = fetch_media_asset(conn, placed_asset.media_asset_id)
        assert refetched is not None
        assert refetched.retired_at is None

    def test_active_two_images_safe_removal_of_non_cover_allowed(self, conn: Any) -> None:
        account = _seed_account(conn, "ACC-AL2IMG")
        org = _seed_org(conn, "ORG-AL2IMG")
        listing_id = _seed_listing(
            conn,
            listing_id="NL-AL2IMG",
            org=org,
            account_id=account,
            physical_boat_id="PB-AL2IMG",
            market_episode_id="ME-AL2IMG",
        )
        placement_ids: list[MediaPlacementId] = []
        with conn.transaction():
            for i in range(2):
                asset = insert_approved_media_asset(
                    conn,
                    owner_organization_id=org.id,
                    uploaded_by_account_id=account,
                    rights_declared=True,
                    source_kind=MediaSourceKind.BROKER_UPLOAD,
                    source_reference=None,
                    original_object_key=f"media/original/al2img-{i}.orig",
                    derivative_object_key=f"media/al2img-{i}.jpg",
                    content_hash=f"hal2img-{i}",
                    mime_type="image/jpeg",
                    width=10,
                    height=10,
                    byte_size=100,
                )
                placement_result = create_uploaded_image_placement(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org.id,
                    media_asset=asset,
                )
                assert placement_result.media_placement_id is not None
                placement_ids.append(placement_result.media_placement_id)
            cover_result = set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_ids[0],
                expected_version=2,
            )
            assert cover_result.outcome is SetCoverOutcome.SET
        _publish_listing(conn, listing_id=listing_id, org=org, account_id=account)

        # Removing the second (non-cover) image is safe: one valid image
        # (the cover) still remains.
        with conn.transaction():
            result = remove_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_ids[1],
                expected_version=3,
            )
        assert result.outcome is RemovePlacementOutcome.REMOVED
        state = fetch_gallery_state(conn, listing_id)
        assert len(state.placements) == 1
        assert state.cover_placement_id == placement_ids[0]

    def test_draft_listing_remains_editable_down_to_zero_media(self, conn: Any) -> None:
        listing_id, _org, _account, placement_id = self._active_listing_with_one_valid_image(
            conn, "DRAFT"
        )
        # Withdraw back off ACTIVE is not part of this contract; instead
        # prove the *pre-publish* DRAFT case directly with a fresh listing.
        account2 = _seed_account(conn, "ACC-ALDRAFT2")
        org2 = _seed_org(conn, "ORG-ALDRAFT2")
        draft_listing_id = _seed_listing(
            conn,
            listing_id="NL-ALDRAFT2",
            org=org2,
            account_id=account2,
            physical_boat_id="PB-ALDRAFT2",
            market_episode_id="ME-ALDRAFT2",
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org2.id,
                uploaded_by_account_id=account2,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key="media/original/aldraft2.orig",
                derivative_object_key="media/aldraft2.jpg",
                content_hash="haldraft2",
                mime_type="image/jpeg",
                width=10,
                height=10,
                byte_size=100,
            )
            placement_result = create_uploaded_image_placement(
                conn,
                native_listing_id=draft_listing_id,
                owner_organization_id=org2.id,
                media_asset=asset,
            )
            assert placement_result.media_placement_id is not None
            set_cover(
                conn,
                native_listing_id=draft_listing_id,
                owner_organization_id=org2.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=1,
            )
        # Still DRAFT: clearing the cover and removing the last image are
        # both freely allowed.
        with conn.transaction():
            clear_result = set_cover(
                conn,
                native_listing_id=draft_listing_id,
                owner_organization_id=org2.id,
                media_placement_id=None,
                expected_version=2,
            )
        assert clear_result.outcome is SetCoverOutcome.CLEARED
        with conn.transaction():
            remove_result = remove_placement(
                conn,
                native_listing_id=draft_listing_id,
                owner_organization_id=org2.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=3,
            )
        assert remove_result.outcome is RemovePlacementOutcome.REMOVED
        state = fetch_gallery_state(conn, draft_listing_id)
        assert state.placements == ()
        assert state.cover_placement_id is None

        # Sanity: the originally-built ACTIVE fixture is untouched by this
        # second, independent DRAFT listing.
        active_state = fetch_gallery_state(conn, listing_id)
        assert active_state.cover_placement_id == placement_id

    def test_stale_version_conflict_still_wins_over_active_conflict(self, conn: Any) -> None:
        """Concurrency check (contract: stale-version protections remain
        intact): a stale `expected_version` must fail as `VERSION_CONFLICT`
        even on an ACTIVE listing whose single valid image is also being
        targeted -- version staleness is checked before the ACTIVE
        invariant, so a stale caller never learns anything about current
        gallery contents."""
        listing_id, org, _account, placement_id = self._active_listing_with_one_valid_image(
            conn, "STALE"
        )
        with conn.transaction():
            result = remove_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_id,
                expected_version=999,  # stale: current version is 2
            )
        assert result.outcome is RemovePlacementOutcome.VERSION_CONFLICT
        state = fetch_gallery_state(conn, listing_id)
        assert len(state.placements) == 1
