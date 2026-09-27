"""Marketplace mixed-media gallery persistence — SLICE-0068.

Implements `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md` §2/§6-§13/§16:
durable MediaAsset/MediaPlacement truth for an existing, Organization-owned
NativeListing.

Every mutation in this module assumes the caller already owns an open
top-level transaction (`with conn.transaction():`), mirroring
`hullq.persistence.professional_listing_draft`'s convention -- none of these
functions call `conn.commit()`/`conn.rollback()` themselves.

Ownership discipline (contract §2/§3): every mutation re-verifies, inside
its own statement(s), that *native_listing_id* is currently owned by the
caller-supplied, already-authorized *owner_organization_id* -- a foreign
NativeListingId and an unknown one collapse to the identical
`LISTING_NOT_FOUND`-shaped outcome everywhere in this module (mirrors
`hullq.persistence.professional_listing_draft`'s identical "foreign and
unknown must be indistinguishable" discipline, scoped by NativeListing
instead of by draft).

Gallery-head concurrency (contract §8/§16): `native_listing_media_state` is
lazily created (`INSERT ... ON CONFLICT DO NOTHING`) on first mutation for a
listing and always locked with `SELECT ... FOR UPDATE` before any
version-gated mutation proceeds -- reorder/cover/removal all require an
exact `expected_version` match or fail closed as `VERSION_CONFLICT`, writing
nothing (contract §16: "stale writes do not silently overwrite ordering/
cover"). Append-only mutations (new upload, reuse, YouTube add) do not
require a caller-supplied `expected_version` (contract does not require it
for pure appends) but still bump `gallery_version` themselves so a
subsequent reorder/cover call always observes the fresh value.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.media_gallery import (
    MediaAssetId,
    MediaPlacementId,
    MediaPlacementKind,
    MediaProcessingState,
    MediaRightsState,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "DEFAULT_LIBRARY_LIMIT",
    "GalleryPlacementRecord",
    "GalleryStateRecord",
    "MediaAssetRecord",
    "PlacementCreationOutcome",
    "PlacementCreationResult",
    "RemovePlacementOutcome",
    "RemovePlacementResult",
    "ReorderOutcome",
    "ReorderResult",
    "RetireAssetOutcome",
    "SetCoverOutcome",
    "SetCoverResult",
    "create_reused_image_placement",
    "create_uploaded_image_placement",
    "create_youtube_placement",
    "fetch_gallery_state",
    "fetch_media_asset",
    "insert_approved_media_asset",
    "insert_rejected_media_asset",
    "list_media_library",
    "remove_placement",
    "reorder_placements",
    "retire_media_asset",
    "set_cover",
]

DEFAULT_LIBRARY_LIMIT = 500


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MediaAssetRecord:
    """Exact typed readback of one persisted MediaAsset (contract §2/§7)."""

    media_asset_id: MediaAssetId
    owner_organization_id: MarketplaceOrganizationId
    uploaded_by_account_id: AccountId
    processing_state: MediaProcessingState
    rights_state: MediaRightsState
    rejection_reason: str | None
    object_key: str | None
    content_hash: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    byte_size: int | None
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_public_usable(self) -> bool:
        """Contract §7: approved processing AND declared rights AND not
        retired -- the one place this joint condition is computed."""
        return (
            self.processing_state is MediaProcessingState.APPROVED
            and self.rights_state is MediaRightsState.DECLARED
            and self.retired_at is None
        )


@dataclass(frozen=True)
class GalleryPlacementRecord:
    """One ordered MediaPlacement within a listing's gallery (contract §8)."""

    media_placement_id: MediaPlacementId
    kind: MediaPlacementKind
    position: int
    created_by_account_id: AccountId
    created_at: datetime
    media_asset: MediaAssetRecord | None  # set iff kind is IMAGE
    youtube_video_id: str | None  # set iff kind is YOUTUBE
    youtube_source_url: str | None  # set iff kind is YOUTUBE


@dataclass(frozen=True)
class GalleryStateRecord:
    """The full authoritative gallery state for one NativeListing (contract
    §8): deterministic ordering, the current version and the current
    explicit cover (if any)."""

    native_listing_id: NativeListingId
    gallery_version: int
    cover_placement_id: MediaPlacementId | None
    placements: tuple[GalleryPlacementRecord, ...]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ASSET_COLUMNS = (
    "media_asset_id, owner_organization_id, uploaded_by_account_id, processing_state, "
    "rights_state, rejection_reason, object_key, content_hash, mime_type, width, height, "
    "byte_size, retired_at, created_at, updated_at"
)


def _row_to_asset(row: tuple[Any, ...]) -> MediaAssetRecord:
    (
        asset_id,
        owner_org_id,
        uploaded_by,
        processing_state,
        rights_state,
        rejection_reason,
        object_key,
        content_hash,
        mime_type,
        width,
        height,
        byte_size,
        retired_at,
        created_at,
        updated_at,
    ) = row
    return MediaAssetRecord(
        media_asset_id=MediaAssetId(asset_id),
        owner_organization_id=MarketplaceOrganizationId(owner_org_id),
        uploaded_by_account_id=AccountId(uploaded_by),
        processing_state=MediaProcessingState(processing_state),
        rights_state=MediaRightsState(rights_state),
        rejection_reason=rejection_reason,
        object_key=object_key,
        content_hash=content_hash,
        mime_type=mime_type,
        width=width,
        height=height,
        byte_size=byte_size,
        retired_at=retired_at,
        created_at=created_at,
        updated_at=updated_at,
    )


def _verify_listing_owned_by(
    cur: Any, native_listing_id: NativeListingId, owner_organization_id: MarketplaceOrganizationId
) -> bool:
    cur.execute(
        "SELECT 1 FROM native_listings WHERE native_listing_id = %s AND publishing_organization_id = %s",
        [native_listing_id.value, owner_organization_id.value],
    )
    return cur.fetchone() is not None


def _ensure_media_state_row(cur: Any, native_listing_id: NativeListingId) -> None:
    cur.execute(
        "INSERT INTO native_listing_media_state (native_listing_id) VALUES (%s) "
        "ON CONFLICT (native_listing_id) DO NOTHING",
        [native_listing_id.value],
    )


def _lock_media_state_row(cur: Any, native_listing_id: NativeListingId) -> int:
    """Lazily create then lock the gallery head row, returning its current
    `gallery_version`."""
    _ensure_media_state_row(cur, native_listing_id)
    cur.execute(
        "SELECT gallery_version FROM native_listing_media_state WHERE native_listing_id = %s "
        "FOR UPDATE",
        [native_listing_id.value],
    )
    row = cur.fetchone()
    assert row is not None
    return int(row[0])


def _bump_media_state_version(cur: Any, native_listing_id: NativeListingId) -> int:
    cur.execute(
        "UPDATE native_listing_media_state SET gallery_version = gallery_version + 1, "
        "updated_at = NOW() WHERE native_listing_id = %s RETURNING gallery_version",
        [native_listing_id.value],
    )
    row = cur.fetchone()
    assert row is not None
    return int(row[0])


def _next_position(cur: Any, native_listing_id: NativeListingId) -> int:
    cur.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 FROM media_placements WHERE native_listing_id = %s",
        [native_listing_id.value],
    )
    row = cur.fetchone()
    assert row is not None
    return int(row[0])


# ---------------------------------------------------------------------------
# MediaAsset creation
# ---------------------------------------------------------------------------

_INSERT_APPROVED_ASSET = f"""
INSERT INTO media_assets
    (media_asset_id, owner_organization_id, uploaded_by_account_id, processing_state,
     rights_state, object_key, content_hash, mime_type, width, height, byte_size)
VALUES (%s, %s, %s, 'APPROVED', %s, %s, %s, %s, %s, %s, %s)
RETURNING {_ASSET_COLUMNS}
"""

_INSERT_REJECTED_ASSET = f"""
INSERT INTO media_assets
    (media_asset_id, owner_organization_id, uploaded_by_account_id, processing_state,
     rights_state, rejection_reason)
VALUES (%s, %s, %s, 'REJECTED', %s, %s)
RETURNING {_ASSET_COLUMNS}
"""

_SELECT_ASSET = f"SELECT {_ASSET_COLUMNS} FROM media_assets WHERE media_asset_id = %s"


def insert_approved_media_asset(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    uploaded_by_account_id: AccountId,
    rights_declared: bool,
    object_key: str,
    content_hash: str,
    mime_type: str,
    width: int,
    height: int,
    byte_size: int,
) -> MediaAssetRecord:
    """Durably create one APPROVED MediaAsset (contract §6/§7).

    The caller must already have produced *object_key*/*content_hash*/
    *mime_type*/*width*/*height*/*byte_size* from a successful
    `hullq.media.image_processing.process_uploaded_image` call and already
    have durably stored the processed bytes at *object_key* in object
    storage -- this function never itself touches object storage.
    """
    media_asset_id = MediaAssetId(str(uuid.uuid4()))
    rights_state = MediaRightsState.DECLARED if rights_declared else MediaRightsState.UNKNOWN
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_APPROVED_ASSET,
            [
                media_asset_id.value,
                owner_organization_id.value,
                uploaded_by_account_id.value,
                rights_state.value,
                object_key,
                content_hash,
                mime_type,
                width,
                height,
                byte_size,
            ],
        )
        row = cur.fetchone()
    assert row is not None
    return _row_to_asset(row)


def insert_rejected_media_asset(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    uploaded_by_account_id: AccountId,
    rights_declared: bool,
    rejection_reason: str,
) -> MediaAssetRecord:
    """Durably record one REJECTED upload attempt (contract §6.4/§7).

    Never public-usable, never placeable -- an audit record only.
    """
    if not rejection_reason:
        raise ValueError("rejection_reason must be non-empty")
    media_asset_id = MediaAssetId(str(uuid.uuid4()))
    rights_state = MediaRightsState.DECLARED if rights_declared else MediaRightsState.UNKNOWN
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_REJECTED_ASSET,
            [
                media_asset_id.value,
                owner_organization_id.value,
                uploaded_by_account_id.value,
                rights_state.value,
                rejection_reason,
            ],
        )
        row = cur.fetchone()
    assert row is not None
    return _row_to_asset(row)


def fetch_media_asset(conn: Any, media_asset_id: MediaAssetId) -> MediaAssetRecord | None:
    with conn.cursor() as cur:
        cur.execute(_SELECT_ASSET, [media_asset_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_asset(row)


def list_media_library(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    limit: int = DEFAULT_LIBRARY_LIMIT,
) -> list[MediaAssetRecord]:
    """List this Organization's own reusable (approved, not retired) IMAGE
    assets (contract §9). Never includes another Organization's assets."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_ASSET_COLUMNS} FROM media_assets "
            "WHERE owner_organization_id = %s AND processing_state = 'APPROVED' "
            "AND retired_at IS NULL ORDER BY created_at DESC LIMIT %s",
            [owner_organization_id.value, limit],
        )
        rows = cur.fetchall()
    return [_row_to_asset(row) for row in rows]


# ---------------------------------------------------------------------------
# Retirement (contract §12)
# ---------------------------------------------------------------------------


class RetireAssetOutcome(StrEnum):
    RETIRED = "RETIRED"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_RETIRED = "ALREADY_RETIRED"


def retire_media_asset(
    conn: Any, *, media_asset_id: MediaAssetId, owner_organization_id: MarketplaceOrganizationId
) -> RetireAssetOutcome:
    """Retire one own MediaAsset (contract §12): prevents new placement/reuse
    and immediate public-usability, and clears any listing's current cover
    pointer that referenced a placement of this asset (contract §8: "must not
    leave a phantom cover reference")."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE media_assets SET retired_at = NOW(), updated_at = NOW() "
            "WHERE media_asset_id = %s AND owner_organization_id = %s AND retired_at IS NULL "
            "RETURNING media_asset_id",
            [media_asset_id.value, owner_organization_id.value],
        )
        updated = cur.fetchone()
        if updated is None:
            cur.execute(
                "SELECT 1 FROM media_assets WHERE media_asset_id = %s AND owner_organization_id = %s",
                [media_asset_id.value, owner_organization_id.value],
            )
            exists = cur.fetchone() is not None
            return RetireAssetOutcome.ALREADY_RETIRED if exists else RetireAssetOutcome.NOT_FOUND

        cur.execute(
            "UPDATE native_listing_media_state SET cover_placement_id = NULL, "
            "gallery_version = gallery_version + 1, updated_at = NOW() "
            "WHERE cover_placement_id IN "
            "(SELECT media_placement_id FROM media_placements WHERE media_asset_id = %s)",
            [media_asset_id.value],
        )
    return RetireAssetOutcome.RETIRED


# ---------------------------------------------------------------------------
# Placement creation (upload / reuse / YouTube) -- append-only
# ---------------------------------------------------------------------------


class PlacementCreationOutcome(StrEnum):
    CREATED = "CREATED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    ASSET_NOT_FOUND_OR_DENIED = "ASSET_NOT_FOUND_OR_DENIED"


@dataclass(frozen=True)
class PlacementCreationResult:
    outcome: PlacementCreationOutcome
    media_placement_id: MediaPlacementId | None = None
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        carries_result = self.outcome is PlacementCreationOutcome.CREATED
        if carries_result and (self.media_placement_id is None or self.gallery_version is None):
            raise ValueError("A CREATED result must carry media_placement_id and gallery_version")
        if not carries_result and (
            self.media_placement_id is not None or self.gallery_version is not None
        ):
            raise ValueError("Only a CREATED result may carry media_placement_id/gallery_version")


def _append_placement(
    cur: Any,
    *,
    native_listing_id: NativeListingId,
    kind: MediaPlacementKind,
    created_by_account_id: AccountId,
    media_asset_id: MediaAssetId | None,
    youtube_video_id: str | None,
    youtube_source_url: str | None,
) -> tuple[MediaPlacementId, int]:
    _lock_media_state_row(cur, native_listing_id)
    position = _next_position(cur, native_listing_id)
    placement_id = MediaPlacementId(str(uuid.uuid4()))
    cur.execute(
        "INSERT INTO media_placements "
        "(media_placement_id, native_listing_id, kind, media_asset_id, youtube_video_id, "
        " youtube_source_url, position, created_by_account_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        [
            placement_id.value,
            native_listing_id.value,
            kind.value,
            media_asset_id.value if media_asset_id is not None else None,
            youtube_video_id,
            youtube_source_url,
            position,
            created_by_account_id.value,
        ],
    )
    new_version = _bump_media_state_version(cur, native_listing_id)
    return placement_id, new_version


def create_uploaded_image_placement(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    owner_organization_id: MarketplaceOrganizationId,
    media_asset: MediaAssetRecord,
) -> PlacementCreationResult:
    """Append a placement for a freshly-uploaded, already-inserted
    APPROVED *media_asset* onto *native_listing_id* (contract §2/§8)."""
    with conn.cursor() as cur:
        if not _verify_listing_owned_by(cur, native_listing_id, owner_organization_id):
            return PlacementCreationResult(outcome=PlacementCreationOutcome.LISTING_NOT_FOUND)
        placement_id, new_version = _append_placement(
            cur,
            native_listing_id=native_listing_id,
            kind=MediaPlacementKind.IMAGE,
            created_by_account_id=media_asset.uploaded_by_account_id,
            media_asset_id=media_asset.media_asset_id,
            youtube_video_id=None,
            youtube_source_url=None,
        )
    return PlacementCreationResult(
        outcome=PlacementCreationOutcome.CREATED,
        media_placement_id=placement_id,
        gallery_version=new_version,
    )


def create_reused_image_placement(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    owner_organization_id: MarketplaceOrganizationId,
    requesting_account_id: AccountId,
    media_asset_id: MediaAssetId,
) -> PlacementCreationResult:
    """Place an existing same-Organization MediaAsset onto another
    Organization-owned listing without copying bytes (contract §9).

    Cross-Organization reuse and a retired asset both fail closed as
    `ASSET_NOT_FOUND_OR_DENIED`, writing nothing (contract §9: "must never
    expose another Organization's assets"; contract §12: retirement
    "prevent[s] new placement/reuse").
    """
    with conn.cursor() as cur:
        if not _verify_listing_owned_by(cur, native_listing_id, owner_organization_id):
            return PlacementCreationResult(outcome=PlacementCreationOutcome.LISTING_NOT_FOUND)

        cur.execute(
            "SELECT owner_organization_id, retired_at FROM media_assets WHERE media_asset_id = %s",
            [media_asset_id.value],
        )
        row = cur.fetchone()
        if row is None or row[0] != owner_organization_id.value or row[1] is not None:
            return PlacementCreationResult(
                outcome=PlacementCreationOutcome.ASSET_NOT_FOUND_OR_DENIED
            )

        placement_id, new_version = _append_placement(
            cur,
            native_listing_id=native_listing_id,
            kind=MediaPlacementKind.IMAGE,
            created_by_account_id=requesting_account_id,
            media_asset_id=media_asset_id,
            youtube_video_id=None,
            youtube_source_url=None,
        )
    return PlacementCreationResult(
        outcome=PlacementCreationOutcome.CREATED,
        media_placement_id=placement_id,
        gallery_version=new_version,
    )


def create_youtube_placement(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    owner_organization_id: MarketplaceOrganizationId,
    created_by_account_id: AccountId,
    youtube_video_id: str,
    youtube_source_url: str,
) -> PlacementCreationResult:
    """Append a normalized YouTube reference placement (contract §10).

    *youtube_video_id* must already be the normalized 11-character id
    (`hullq.domain.media_gallery.parse_youtube_reference`'s result) -- this
    function never re-validates or re-parses it.
    """
    with conn.cursor() as cur:
        if not _verify_listing_owned_by(cur, native_listing_id, owner_organization_id):
            return PlacementCreationResult(outcome=PlacementCreationOutcome.LISTING_NOT_FOUND)
        placement_id, new_version = _append_placement(
            cur,
            native_listing_id=native_listing_id,
            kind=MediaPlacementKind.YOUTUBE,
            created_by_account_id=created_by_account_id,
            media_asset_id=None,
            youtube_video_id=youtube_video_id,
            youtube_source_url=youtube_source_url,
        )
    return PlacementCreationResult(
        outcome=PlacementCreationOutcome.CREATED,
        media_placement_id=placement_id,
        gallery_version=new_version,
    )


# ---------------------------------------------------------------------------
# Removal (contract §12)
# ---------------------------------------------------------------------------


class RemovePlacementOutcome(StrEnum):
    REMOVED = "REMOVED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    PLACEMENT_NOT_FOUND = "PLACEMENT_NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"


@dataclass(frozen=True)
class RemovePlacementResult:
    outcome: RemovePlacementOutcome
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        if self.outcome is RemovePlacementOutcome.REMOVED and self.gallery_version is None:
            raise ValueError("A REMOVED result must carry gallery_version")
        if self.outcome is not RemovePlacementOutcome.REMOVED and self.gallery_version is not None:
            raise ValueError("Only a REMOVED result may carry gallery_version")


def remove_placement(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    owner_organization_id: MarketplaceOrganizationId,
    media_placement_id: MediaPlacementId,
    expected_version: int,
) -> RemovePlacementResult:
    """Remove one placement (contract §12: never deletes the underlying
    MediaAsset). A stale *expected_version* fails closed as
    `VERSION_CONFLICT`, writing nothing. If the removed placement was the
    listing's explicit cover, the FK `ON DELETE SET NULL` on
    `native_listing_media_state.cover_placement_id` clears it automatically
    (contract §8: no phantom cover reference)."""
    with conn.cursor() as cur:
        if not _verify_listing_owned_by(cur, native_listing_id, owner_organization_id):
            return RemovePlacementResult(outcome=RemovePlacementOutcome.LISTING_NOT_FOUND)

        current_version = _lock_media_state_row(cur, native_listing_id)
        if current_version != expected_version:
            return RemovePlacementResult(outcome=RemovePlacementOutcome.VERSION_CONFLICT)

        cur.execute(
            "DELETE FROM media_placements WHERE media_placement_id = %s AND native_listing_id = %s "
            "RETURNING media_placement_id",
            [media_placement_id.value, native_listing_id.value],
        )
        if cur.fetchone() is None:
            return RemovePlacementResult(outcome=RemovePlacementOutcome.PLACEMENT_NOT_FOUND)

        new_version = _bump_media_state_version(cur, native_listing_id)
    return RemovePlacementResult(
        outcome=RemovePlacementOutcome.REMOVED, gallery_version=new_version
    )


# ---------------------------------------------------------------------------
# Reorder (contract §8/§16)
# ---------------------------------------------------------------------------


class ReorderOutcome(StrEnum):
    REORDERED = "REORDERED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    INVALID_PLACEMENT_SET = "INVALID_PLACEMENT_SET"


@dataclass(frozen=True)
class ReorderResult:
    outcome: ReorderOutcome
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        if self.outcome is ReorderOutcome.REORDERED and self.gallery_version is None:
            raise ValueError("A REORDERED result must carry gallery_version")
        if self.outcome is not ReorderOutcome.REORDERED and self.gallery_version is not None:
            raise ValueError("Only a REORDERED result may carry gallery_version")


def reorder_placements(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    owner_organization_id: MarketplaceOrganizationId,
    ordered_placement_ids: list[MediaPlacementId],
    expected_version: int,
) -> ReorderResult:
    """Atomically set the full explicit ordering (contract §8).

    *ordered_placement_ids* must contain exactly the listing's current
    placement ids (no more, no fewer, each exactly once) or this fails
    closed as `INVALID_PLACEMENT_SET`, writing nothing. The listing's
    `uq_media_placements_listing_position` unique constraint is
    `DEFERRABLE INITIALLY DEFERRED` (see the owning migration's docstring),
    so writing every row's new `position` inside this one transaction is
    safe even though intermediate per-row states may transiently collide.
    """
    with conn.cursor() as cur:
        if not _verify_listing_owned_by(cur, native_listing_id, owner_organization_id):
            return ReorderResult(outcome=ReorderOutcome.LISTING_NOT_FOUND)

        current_version = _lock_media_state_row(cur, native_listing_id)
        if current_version != expected_version:
            return ReorderResult(outcome=ReorderOutcome.VERSION_CONFLICT)

        cur.execute(
            "SELECT media_placement_id FROM media_placements WHERE native_listing_id = %s "
            "FOR UPDATE",
            [native_listing_id.value],
        )
        current_ids = {row[0] for row in cur.fetchall()}
        requested_ids = {p.value for p in ordered_placement_ids}
        if current_ids != requested_ids or len(ordered_placement_ids) != len(requested_ids):
            return ReorderResult(outcome=ReorderOutcome.INVALID_PLACEMENT_SET)

        for index, placement_id in enumerate(ordered_placement_ids):
            cur.execute(
                "UPDATE media_placements SET position = %s "
                "WHERE media_placement_id = %s AND native_listing_id = %s",
                [index, placement_id.value, native_listing_id.value],
            )

        new_version = _bump_media_state_version(cur, native_listing_id)
    return ReorderResult(outcome=ReorderOutcome.REORDERED, gallery_version=new_version)


# ---------------------------------------------------------------------------
# Cover (contract §8)
# ---------------------------------------------------------------------------


class SetCoverOutcome(StrEnum):
    SET = "SET"
    CLEARED = "CLEARED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    INVALID_COVER = "INVALID_COVER"


@dataclass(frozen=True)
class SetCoverResult:
    outcome: SetCoverOutcome
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        carries = self.outcome in (SetCoverOutcome.SET, SetCoverOutcome.CLEARED)
        if carries and self.gallery_version is None:
            raise ValueError("A SET/CLEARED result must carry gallery_version")
        if not carries and self.gallery_version is not None:
            raise ValueError("Only a SET/CLEARED result may carry gallery_version")


def set_cover(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    owner_organization_id: MarketplaceOrganizationId,
    media_placement_id: MediaPlacementId | None,
    expected_version: int,
) -> SetCoverResult:
    """Set (or, if `None`, clear) the listing's single explicit cover
    (contract §8). A candidate cover must be an IMAGE placement belonging to
    this listing whose MediaAsset is currently public-usable (approved,
    rights-declared, not retired) -- anything else is `INVALID_COVER`,
    writing nothing."""
    with conn.cursor() as cur:
        if not _verify_listing_owned_by(cur, native_listing_id, owner_organization_id):
            return SetCoverResult(outcome=SetCoverOutcome.LISTING_NOT_FOUND)

        current_version = _lock_media_state_row(cur, native_listing_id)
        if current_version != expected_version:
            return SetCoverResult(outcome=SetCoverOutcome.VERSION_CONFLICT)

        if media_placement_id is None:
            cur.execute(
                "UPDATE native_listing_media_state SET cover_placement_id = NULL, "
                "gallery_version = gallery_version + 1, updated_at = NOW() "
                "WHERE native_listing_id = %s RETURNING gallery_version",
                [native_listing_id.value],
            )
            row = cur.fetchone()
            assert row is not None
            return SetCoverResult(outcome=SetCoverOutcome.CLEARED, gallery_version=int(row[0]))

        cur.execute(
            "SELECT ma.processing_state, ma.rights_state, ma.retired_at "
            "FROM media_placements mp "
            "JOIN media_assets ma ON ma.media_asset_id = mp.media_asset_id "
            "WHERE mp.media_placement_id = %s AND mp.native_listing_id = %s AND mp.kind = 'IMAGE'",
            [media_placement_id.value, native_listing_id.value],
        )
        candidate = cur.fetchone()
        if candidate is None:
            return SetCoverResult(outcome=SetCoverOutcome.INVALID_COVER)
        processing_state, rights_state, retired_at = candidate
        eligible = (
            processing_state == MediaProcessingState.APPROVED.value
            and rights_state == MediaRightsState.DECLARED.value
            and retired_at is None
        )
        if not eligible:
            return SetCoverResult(outcome=SetCoverOutcome.INVALID_COVER)

        cur.execute(
            "UPDATE native_listing_media_state SET cover_placement_id = %s, "
            "gallery_version = gallery_version + 1, updated_at = NOW() "
            "WHERE native_listing_id = %s RETURNING gallery_version",
            [media_placement_id.value, native_listing_id.value],
        )
        row = cur.fetchone()
        assert row is not None
    return SetCoverResult(outcome=SetCoverOutcome.SET, gallery_version=int(row[0]))


# ---------------------------------------------------------------------------
# Gallery state read (contract §8/§13)
# ---------------------------------------------------------------------------


def fetch_gallery_state(conn: Any, native_listing_id: NativeListingId) -> GalleryStateRecord:
    """Read the full authoritative gallery state (contract §8/§13).

    A listing with no `native_listing_media_state` row yet (no mutation has
    ever happened) reads as version 0, no cover, zero placements -- never an
    error.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT gallery_version, cover_placement_id FROM native_listing_media_state "
            "WHERE native_listing_id = %s",
            [native_listing_id.value],
        )
        head = cur.fetchone()
        gallery_version = int(head[0]) if head is not None else 0
        cover_placement_id = (
            MediaPlacementId(head[1]) if head is not None and head[1] is not None else None
        )

        cur.execute(
            "SELECT mp.media_placement_id, mp.kind, mp.position, mp.created_by_account_id, "
            "mp.created_at, mp.youtube_video_id, mp.youtube_source_url, "
            f"ma.{_ASSET_COLUMNS.replace(', ', ', ma.')} "
            "FROM media_placements mp "
            "LEFT JOIN media_assets ma ON ma.media_asset_id = mp.media_asset_id "
            "WHERE mp.native_listing_id = %s "
            "ORDER BY mp.position ASC",
            [native_listing_id.value],
        )
        rows = cur.fetchall()

    placements = []
    for row in rows:
        (
            placement_id,
            kind,
            position,
            created_by_account_id,
            created_at,
            youtube_video_id,
            youtube_source_url,
            *asset_columns,
        ) = row
        media_asset = _row_to_asset(tuple(asset_columns)) if asset_columns[0] is not None else None
        placements.append(
            GalleryPlacementRecord(
                media_placement_id=MediaPlacementId(placement_id),
                kind=MediaPlacementKind(kind),
                position=position,
                created_by_account_id=AccountId(created_by_account_id),
                created_at=created_at,
                media_asset=media_asset,
                youtube_video_id=youtube_video_id,
                youtube_source_url=youtube_source_url,
            )
        )

    return GalleryStateRecord(
        native_listing_id=native_listing_id,
        gallery_version=gallery_version,
        cover_placement_id=cover_placement_id,
        placements=tuple(placements),
    )
