"""SLICE-0069 shared owner-visible-proof fixture helper.

`specs/MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md` D22 requires an
approved, rights-declared IMAGE placement set as the explicit cover before a
NativeListing can publish -- several pre-existing `scripts/inspect_*.py`
owner-visible proofs (SLICE-0049/0052/etc.) only built an episode/boat/offer/
claim chain, which is no longer sufficient. This module centralizes the one
extra fixture step every such script now needs, rather than duplicating it
independently in each file.
"""

from __future__ import annotations

from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.media_gallery import MediaSourceKind
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganization
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)


def attach_d22_minimum_cover_image(
    conn: Any, *, listing_id: str, account: AccountId, org: MarketplaceOrganization
) -> None:
    """Attach one approved, rights-declared IMAGE placement and set it as the
    explicit cover -- the D22 minimum public-media state a DRAFT listing
    needs to actually publish. Does not touch the offer/PhysicalBoat-claim
    chain, which each caller already builds its own way.

    `media_assets` carries real FKs to `accounts`/`marketplace_organizations`;
    both rows are idempotently seeded here first. The caller must pass an
    IDLE connection and is responsible for committing afterward -- mirrors
    every other function in `hullq.persistence.media_gallery`.
    """
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
