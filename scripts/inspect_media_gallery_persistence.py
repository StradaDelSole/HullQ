"""Ad-hoc round-trip smoke check for hullq.persistence.media_gallery —
SLICE-0068. Not a pytest test; reads HULLQ_TEST_DATABASE_URL, mirrors the
repository's `scripts/inspect_*.py` convention.
"""

from __future__ import annotations

import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
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
    PlacementCreationOutcome,
    RemovePlacementOutcome,
    ReorderOutcome,
    RetireAssetOutcome,
    SetCoverOutcome,
    create_reused_image_placement,
    create_uploaded_image_placement,
    create_youtube_placement,
    fetch_gallery_state,
    insert_approved_media_asset,
    remove_placement,
    reorder_placements,
    retire_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.physical_boat import create_physical_boat


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def main() -> None:
    import os

    base_url = os.environ["HULLQ_TEST_DATABASE_URL"]
    schema_name = f"hullq_s0068_persist_{uuid.uuid4().hex[:16]}"
    admin = psycopg.connect(base_url, autocommit=True)
    try:
        with admin.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        admin.close()

    url = _with_search_path(base_url, schema_name)
    try:
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)

        conn = psycopg.connect(url)
        try:
            account = AccountId("ACC-1")
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [account.value],
                )
            conn.commit()

            org_a = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-A"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            org_b = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-B"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org_a)
            seed_marketplace_organization(conn, org_b)
            conn.commit()

            membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-1"),
                account_id=account,
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )

            physical_boat_id = PhysicalBoatId("PB-1")
            market_episode_id = MarketEpisodeId("ME-1")
            listing_id = NativeListingId("NL-1")
            create_physical_boat(conn, physical_boat=PhysicalBoat(id=physical_boat_id))
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=market_episode_id, physical_boat_id=physical_boat_id
                ),
            )
            create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership,
                listing=NativeListing(id=listing_id, market_episode_id=market_episode_id),
            )
            conn.commit()

            # A second listing owned by ORG-A, for reuse tests.
            listing_id_2 = NativeListingId("NL-2")
            market_episode_id_2 = MarketEpisodeId("ME-2")
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=market_episode_id_2, physical_boat_id=physical_boat_id
                ),
            )
            create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership,
                listing=NativeListing(id=listing_id_2, market_episode_id=market_episode_id_2),
            )
            conn.commit()

            with conn.transaction():
                asset = insert_approved_media_asset(
                    conn,
                    owner_organization_id=org_a.id,
                    uploaded_by_account_id=account,
                    rights_declared=True,
                    object_key="media/test-1.jpg",
                    content_hash="hash1",
                    mime_type="image/jpeg",
                    width=100,
                    height=50,
                    byte_size=1234,
                )
            print("asset created:", asset.media_asset_id.value, asset.is_public_usable)

            with conn.transaction():
                result1 = create_uploaded_image_placement(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org_a.id,
                    media_asset=asset,
                )
            assert result1.outcome is PlacementCreationOutcome.CREATED, result1
            print("placement1:", result1.media_placement_id.value, result1.gallery_version)

            with conn.transaction():
                yt_result = create_youtube_placement(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org_a.id,
                    created_by_account_id=account,
                    youtube_video_id="dQw4w9WgXcQ",
                    youtube_source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                )
            assert yt_result.outcome is PlacementCreationOutcome.CREATED, yt_result
            print(
                "youtube placement:", yt_result.media_placement_id.value, yt_result.gallery_version
            )

            state = fetch_gallery_state(conn, listing_id)
            print(
                "gallery state placements:", [(p.kind.value, p.position) for p in state.placements]
            )
            assert state.gallery_version == 2
            assert len(state.placements) == 2

            with conn.transaction():
                cover_result = set_cover(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org_a.id,
                    media_placement_id=result1.media_placement_id,
                    expected_version=state.gallery_version,
                )
            assert cover_result.outcome is SetCoverOutcome.SET, cover_result
            print("cover set, new version:", cover_result.gallery_version)

            # Stale version must conflict.
            with conn.transaction():
                stale = set_cover(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org_a.id,
                    media_placement_id=None,
                    expected_version=state.gallery_version,  # now stale
                )
            assert stale.outcome is SetCoverOutcome.VERSION_CONFLICT, stale
            print("stale cover write correctly rejected")

            # Reorder: swap the two placements.
            state = fetch_gallery_state(conn, listing_id)
            reversed_ids = [p.media_placement_id for p in reversed(state.placements)]
            with conn.transaction():
                reorder_result = reorder_placements(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org_a.id,
                    ordered_placement_ids=reversed_ids,
                    expected_version=state.gallery_version,
                )
            assert reorder_result.outcome is ReorderOutcome.REORDERED, reorder_result
            state = fetch_gallery_state(conn, listing_id)
            print(
                "reordered positions:",
                [(p.media_placement_id.value, p.position) for p in state.placements],
            )

            # Cross-org reuse must be denied.
            with conn.transaction():
                cross_org = create_reused_image_placement(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org_b.id,
                    requesting_account_id=account,
                    media_asset_id=asset.media_asset_id,
                )
            assert cross_org.outcome is PlacementCreationOutcome.LISTING_NOT_FOUND, cross_org
            print("cross-org listing ownership denied as expected")

            # Same-org reuse onto the second listing must succeed.
            with conn.transaction():
                reuse_result = create_reused_image_placement(
                    conn,
                    native_listing_id=listing_id_2,
                    owner_organization_id=org_a.id,
                    requesting_account_id=account,
                    media_asset_id=asset.media_asset_id,
                )
            assert reuse_result.outcome is PlacementCreationOutcome.CREATED, reuse_result
            print("same-org reuse created:", reuse_result.media_placement_id.value)

            # Retire the asset: cover on listing_id must clear.
            with conn.transaction():
                retire_result = retire_media_asset(
                    conn, media_asset_id=asset.media_asset_id, owner_organization_id=org_a.id
                )
            assert retire_result is RetireAssetOutcome.RETIRED, retire_result
            state = fetch_gallery_state(conn, listing_id)
            assert state.cover_placement_id is None, state.cover_placement_id
            print("retirement cleared phantom cover as expected")

            # Removal of the youtube placement must not affect the asset row.
            state = fetch_gallery_state(conn, listing_id)
            youtube_placement = next(p for p in state.placements if p.kind.value == "YOUTUBE")
            with conn.transaction():
                remove_result = remove_placement(
                    conn,
                    native_listing_id=listing_id,
                    owner_organization_id=org_a.id,
                    media_placement_id=youtube_placement.media_placement_id,
                    expected_version=state.gallery_version,
                )
            assert remove_result.outcome is RemovePlacementOutcome.REMOVED, remove_result
            state = fetch_gallery_state(conn, listing_id)
            assert len(state.placements) == 1
            print("removal ok, remaining placements:", len(state.placements))

            print("ALL OK")
        finally:
            conn.close()
    finally:
        admin2 = psycopg.connect(base_url, autocommit=True)
        try:
            with admin2.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        finally:
            admin2.close()


if __name__ == "__main__":
    main()
