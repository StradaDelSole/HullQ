"""Broker-facing marketplace mixed-media gallery orchestration — SLICE-0068.

Implements `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md` §3/§6/§8-§13:
thin orchestration over `hullq.media.image_processing` (server-controlled
IMAGE validation/re-encoding), `hullq.storage.object_storage` (the S3-
compatible boundary) and `hullq.persistence.media_gallery` (durable truth),
translating a signed `SessionClaims`, an explicit Organization/NativeListing
selection and caller-supplied raw input into one deterministic outcome
FastAPI can render.

Authorization on every request (contract §3) reuses the exact accepted
SLICE-0053 Organization workspace boundary
(`hullq.application.broker_workspace_read.get_organization_workspace_result`)
and additionally requires `PUBLISHER` in that exact current matching ACTIVE
membership, mirroring `hullq.application.professional_listing_draft`'s
identical `_authorize_draft_actor` discipline -- media authoring is gated
exactly like draft authoring, not a weaker boundary.

Every mutating helper re-opens a fresh top-level transaction on *conn*
before invoking a persistence primitive (contract §3/§16): the
authorization read issued by `get_organization_workspace_result` leaves an
implicit read transaction open under psycopg's default `autocommit=False`,
so `conn.commit()` ends it first -- mirrors
`hullq.application.professional_listing_draft`'s identical comment.

Object-storage failures (contract §16: "partial storage/database failures
never promote missing/unprocessed bytes to public truth") are handled by
strict ordering: this module always writes bytes to *object_storage* before
it ever inserts the corresponding durable `APPROVED` MediaAsset row. A
storage failure therefore leaves zero database trace -- there is nothing to
roll back.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.market_identity import NativeListingId
from hullq.domain.media_gallery import (
    MAX_SOURCE_REFERENCE_LENGTH,
    MediaAssetId,
    MediaPlacementId,
    MediaSourceKind,
    parse_youtube_reference,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.media.image_processing import ProcessedImage, RejectedImage, process_uploaded_image
from hullq.persistence.media_gallery import (
    GalleryStateRecord,
    MediaAssetRecord,
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
from hullq.persistence.native_listing import fetch_native_listing
from hullq.security.session_token import SessionClaims
from hullq.storage.object_storage import ObjectStorage

__all__ = [
    "AddYoutubeOutcome",
    "AddYoutubeResult",
    "GalleryReadOutcome",
    "GalleryReadResult",
    "GetAssetBytesOutcome",
    "GetAssetBytesResult",
    "LibraryReadOutcome",
    "LibraryReadResult",
    "RemovePlacementRequestOutcome",
    "RemovePlacementRequestResult",
    "ReorderGalleryOutcome",
    "ReorderGalleryResult",
    "RetireAssetRequestOutcome",
    "RetireAssetRequestResult",
    "ReuseAssetOutcome",
    "ReuseAssetResult",
    "SetCoverRequestOutcome",
    "SetCoverRequestResult",
    "UploadImageOutcome",
    "UploadImageResult",
    "add_youtube_for_organization",
    "gallery_state_to_public_dict",
    "get_asset_bytes_for_organization",
    "get_gallery_state_for_organization",
    "list_media_library_for_organization",
    "media_asset_to_public_dict",
    "remove_placement_for_organization",
    "reorder_gallery_for_organization",
    "retire_asset_for_organization",
    "reuse_asset_for_organization",
    "set_cover_for_organization",
    "upload_image_for_organization",
]

#: Contract §11 v0.1 choice: bounded FastAPI-proxied transport, not direct-
#: to-R2 presigned upload (see this module's docstring and the migration's
#: docstring for the accepted GENUINELY_OPEN rationale). *raw* is always the
#: complete request body of exactly one image; the multi-file requirement
#: (contract §13) is satisfied at the Broker Workspace layer issuing one
#: call per file, never by parsing a multipart body here.
#:
#: Independent review Finding A: the original/quarantine object and the
#: public derivative object always live under distinct key prefixes, so an
#: opaque key alone reveals which role it plays -- neither route ever
#: serves an `_ORIGINAL_KEY_PREFIX` key.
_ORIGINAL_KEY_PREFIX = "media/original"
_DERIVATIVE_KEY_PREFIX = "media/derivative"

#: Independent review Finding B: v0.1's only source/provenance classification.
_UPLOAD_SOURCE_KIND = MediaSourceKind.BROKER_UPLOAD


def _validate_source_reference(raw: Any) -> str | None:
    """Bound the optional D14 broker-supplied note (independent review
    Finding B) -- `None`/absent stays `None`; anything present must be a
    non-empty string within `MAX_SOURCE_REFERENCE_LENGTH` or the whole
    upload is rejected before any storage/database write."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise _InvalidSourceReferenceError()
    stripped = raw.strip()
    if not stripped or len(stripped) > MAX_SOURCE_REFERENCE_LENGTH:
        raise _InvalidSourceReferenceError()
    return stripped


class _InvalidSourceReferenceError(ValueError):
    """*source_reference* failed the bounded-length/shape check."""


# ---------------------------------------------------------------------------
# Authorization -- reuses the accepted Organization workspace boundary, plus
# the exact-current PUBLISHER media-authoring role gate (contract §3).
# ---------------------------------------------------------------------------


class _MediaActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


def _authorize_media_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> _MediaActorAuthorizationOutcome:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _MediaActorAuthorizationOutcome.MFA_REQUIRED
    assert workspace_result.context is not None
    if "PUBLISHER" not in workspace_result.context.roles:
        return _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED
    return _MediaActorAuthorizationOutcome.AUTHORIZED


def _verify_listing_ownership(
    conn: Any, native_listing_id: NativeListingId, organization_id: MarketplaceOrganizationId
) -> bool:
    """Contract §2/§4: a foreign NativeListing and an unknown one must be
    indistinguishable to the caller -- both collapse to the identical
    `LISTING_NOT_FOUND`-shaped outcome in every function below."""
    record = fetch_native_listing(conn, native_listing_id)
    return record is not None and record.publishing_organization_id == organization_id


# ---------------------------------------------------------------------------
# Public wire shapes
# ---------------------------------------------------------------------------


def media_asset_to_public_dict(asset: MediaAssetRecord) -> dict[str, Any]:
    return {
        "media_asset_id": asset.media_asset_id.value,
        "source_kind": asset.source_kind.value,
        "source_reference": asset.source_reference,
        "processing_state": asset.processing_state.value,
        "rights_state": asset.rights_state.value,
        "rejection_reason": asset.rejection_reason,
        "mime_type": asset.mime_type,
        "width": asset.width,
        "height": asset.height,
        "byte_size": asset.byte_size,
        "retired": asset.retired_at is not None,
        "is_public_usable": asset.is_public_usable,
        "created_at": asset.created_at.isoformat(),
    }


def _placement_to_public_dict(placement: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "media_placement_id": placement.media_placement_id.value,
        "kind": placement.kind.value,
        "position": placement.position,
        "created_at": placement.created_at.isoformat(),
    }
    if placement.media_asset is not None:
        body["media_asset"] = media_asset_to_public_dict(placement.media_asset)
    if placement.youtube_video_id is not None:
        body["youtube_video_id"] = placement.youtube_video_id
        body["youtube_source_url"] = placement.youtube_source_url
    return body


def gallery_state_to_public_dict(state: GalleryStateRecord) -> dict[str, Any]:
    return {
        "native_listing_id": state.native_listing_id.value,
        "gallery_version": state.gallery_version,
        "cover_placement_id": (
            state.cover_placement_id.value if state.cover_placement_id is not None else None
        ),
        "placements": [_placement_to_public_dict(p) for p in state.placements],
    }


# ---------------------------------------------------------------------------
# Read: gallery state
# ---------------------------------------------------------------------------


class GalleryReadOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    OK = "OK"


@dataclass(frozen=True)
class GalleryReadResult:
    outcome: GalleryReadOutcome
    gallery: GalleryStateRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is GalleryReadOutcome.OK and self.gallery is None:
            raise ValueError("An OK result must carry a gallery state")
        if self.outcome is not GalleryReadOutcome.OK and self.gallery is not None:
            raise ValueError("Only an OK result may carry a gallery state")


def get_gallery_state_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str, native_listing_id_value: str
) -> GalleryReadResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return GalleryReadResult(outcome=GalleryReadOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return GalleryReadResult(outcome=GalleryReadOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return GalleryReadResult(outcome=GalleryReadOutcome.PUBLISHER_ROLE_REQUIRED)

    native_listing_id = NativeListingId(native_listing_id_value)
    if not _verify_listing_ownership(conn, native_listing_id, organization_id):
        return GalleryReadResult(outcome=GalleryReadOutcome.LISTING_NOT_FOUND)

    gallery = fetch_gallery_state(conn, native_listing_id)
    return GalleryReadResult(outcome=GalleryReadOutcome.OK, gallery=gallery)


# ---------------------------------------------------------------------------
# Read: same-Organization media library (contract §9)
# ---------------------------------------------------------------------------


class LibraryReadOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    OK = "OK"


@dataclass(frozen=True)
class LibraryReadResult:
    outcome: LibraryReadOutcome
    assets: tuple[MediaAssetRecord, ...] | None = None

    def __post_init__(self) -> None:
        if self.outcome is LibraryReadOutcome.OK and self.assets is None:
            raise ValueError("An OK result must carry assets")
        if self.outcome is not LibraryReadOutcome.OK and self.assets is not None:
            raise ValueError("Only an OK result may carry assets")


def list_media_library_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str
) -> LibraryReadResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return LibraryReadResult(outcome=LibraryReadOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return LibraryReadResult(outcome=LibraryReadOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return LibraryReadResult(outcome=LibraryReadOutcome.PUBLISHER_ROLE_REQUIRED)

    assets = list_media_library(conn, owner_organization_id=organization_id)
    return LibraryReadResult(outcome=LibraryReadOutcome.OK, assets=tuple(assets))


# ---------------------------------------------------------------------------
# Read: broker workspace preview of one own asset's bytes (private, no-store)
# ---------------------------------------------------------------------------


class GetAssetBytesOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    NOT_STORED = "NOT_STORED"
    OK = "OK"


@dataclass(frozen=True)
class GetAssetBytesResult:
    outcome: GetAssetBytesOutcome
    data: bytes | None = None
    mime_type: str | None = None

    def __post_init__(self) -> None:
        carries = self.outcome is GetAssetBytesOutcome.OK
        if carries and (self.data is None or self.mime_type is None):
            raise ValueError("An OK result must carry data and mime_type")
        if not carries and (self.data is not None or self.mime_type is not None):
            raise ValueError("Only an OK result may carry data/mime_type")


def get_asset_bytes_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    media_asset_id_value: str,
    *,
    object_storage: ObjectStorage,
) -> GetAssetBytesResult:
    """Broker-only preview of one own MediaAsset's bytes (never public).

    Served regardless of rights/retirement state -- this is the org's own
    audit view of its own upload, not the public-usability gate (contract
    §7 governs *public* usability only).
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return GetAssetBytesResult(outcome=GetAssetBytesOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return GetAssetBytesResult(outcome=GetAssetBytesOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return GetAssetBytesResult(outcome=GetAssetBytesOutcome.PUBLISHER_ROLE_REQUIRED)

    asset = fetch_media_asset(conn, MediaAssetId(media_asset_id_value))
    if asset is None or asset.owner_organization_id != organization_id:
        return GetAssetBytesResult(outcome=GetAssetBytesOutcome.ASSET_NOT_FOUND)
    if asset.derivative_object_key is None:
        return GetAssetBytesResult(outcome=GetAssetBytesOutcome.NOT_STORED)

    # Only ever the public derivative -- the private/quarantine original
    # (independent review Finding A) is never served by any route.
    data = object_storage.get_object(asset.derivative_object_key)
    assert asset.mime_type is not None
    return GetAssetBytesResult(
        outcome=GetAssetBytesOutcome.OK, data=data, mime_type=asset.mime_type
    )


# ---------------------------------------------------------------------------
# Upload (contract §6/§11)
# ---------------------------------------------------------------------------


class UploadImageOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_SOURCE_REFERENCE = "INVALID_SOURCE_REFERENCE"
    REJECTED = "REJECTED"
    CREATED = "CREATED"


@dataclass(frozen=True)
class UploadImageResult:
    outcome: UploadImageOutcome
    rejection_reason: str | None = None
    media_asset_id: str | None = None
    media_placement_id: str | None = None
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        if self.outcome is UploadImageOutcome.REJECTED and self.rejection_reason is None:
            raise ValueError("A REJECTED result must carry a rejection_reason")
        if self.outcome is not UploadImageOutcome.REJECTED and self.rejection_reason is not None:
            raise ValueError("Only a REJECTED result may carry a rejection_reason")
        carries_created = self.outcome is UploadImageOutcome.CREATED
        if carries_created and (
            self.media_asset_id is None
            or self.media_placement_id is None
            or self.gallery_version is None
        ):
            raise ValueError(
                "A CREATED result must carry media_asset_id/media_placement_id/gallery_version"
            )
        if not carries_created and (
            self.media_asset_id is not None
            or self.media_placement_id is not None
            or self.gallery_version is not None
        ):
            raise ValueError("Only a CREATED result may carry those fields")


def upload_image_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    *,
    raw_bytes: bytes,
    rights_confirmed: bool,
    object_storage: ObjectStorage,
    raw_source_reference: Any = None,
) -> UploadImageResult:
    """Validate, safely re-encode, store and durably place one uploaded
    IMAGE (contract §6/§8/§11).

    Independent review Finding A: *raw_bytes* is durably stored, verbatim,
    at a fresh private/quarantine `original_object_key` *before* processing
    ever decides accept/reject (contract §6: quarantine storage is the first
    ingestion step) -- a REJECTED outcome still leaves that original
    durably quarantined, never promoted to a derivative. Only on successful
    processing is a second, independently-purgeable public derivative
    stored under its own `derivative_object_key`. A storage failure at
    either step leaves zero database trace to roll back (contract §16).

    Independent review Finding B: *raw_source_reference* is the optional
    bounded D14 broker note, validated before any processing/storage is
    attempted; an out-of-bounds value fails the whole upload closed as
    `INVALID_SOURCE_REFERENCE`.
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return UploadImageResult(outcome=UploadImageOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return UploadImageResult(outcome=UploadImageOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return UploadImageResult(outcome=UploadImageOutcome.PUBLISHER_ROLE_REQUIRED)

    native_listing_id = NativeListingId(native_listing_id_value)
    if not _verify_listing_ownership(conn, native_listing_id, organization_id):
        return UploadImageResult(outcome=UploadImageOutcome.LISTING_NOT_FOUND)

    try:
        source_reference = _validate_source_reference(raw_source_reference)
    except _InvalidSourceReferenceError:
        return UploadImageResult(outcome=UploadImageOutcome.INVALID_SOURCE_REFERENCE)

    # Ends the authorization/ownership reads' implicit transaction so the
    # write(s) below commit independently (see module docstring).
    conn.commit()

    # Contract §6: quarantine storage is the very first ingestion step,
    # before any accept/reject decision -- durable regardless of outcome.
    original_object_key = f"{_ORIGINAL_KEY_PREFIX}/{uuid.uuid4().hex}"
    object_storage.put_object(
        original_object_key, raw_bytes, content_type="application/octet-stream"
    )

    processed = process_uploaded_image(raw_bytes)

    if isinstance(processed, RejectedImage):
        with conn.transaction():
            insert_rejected_media_asset(
                conn,
                owner_organization_id=organization_id,
                uploaded_by_account_id=session.account_id,
                rights_declared=rights_confirmed,
                source_kind=_UPLOAD_SOURCE_KIND,
                source_reference=source_reference,
                original_object_key=original_object_key,
                rejection_reason=processed.reason.value,
            )
        return UploadImageResult(
            outcome=UploadImageOutcome.REJECTED, rejection_reason=processed.reason.value
        )

    assert isinstance(processed, ProcessedImage)
    derivative_object_key = f"{_DERIVATIVE_KEY_PREFIX}/{uuid.uuid4().hex}.jpg"
    # Contract §16: bytes are durable in object storage *before* any database
    # row claims this asset exists -- a storage failure here leaves zero
    # database trace to roll back.
    object_storage.put_object(
        derivative_object_key, processed.data, content_type=processed.mime_type
    )

    with conn.transaction():
        asset = insert_approved_media_asset(
            conn,
            owner_organization_id=organization_id,
            uploaded_by_account_id=session.account_id,
            rights_declared=rights_confirmed,
            source_kind=_UPLOAD_SOURCE_KIND,
            source_reference=source_reference,
            original_object_key=original_object_key,
            derivative_object_key=derivative_object_key,
            content_hash=processed.content_hash,
            mime_type=processed.mime_type,
            width=processed.width,
            height=processed.height,
            byte_size=processed.byte_size,
        )
        placement_result = create_uploaded_image_placement(
            conn,
            native_listing_id=native_listing_id,
            owner_organization_id=organization_id,
            media_asset=asset,
        )
        # Organization ownership of an already-created NativeListing never
        # changes after creation (no reassignment/deletion path exists in
        # the accepted implementation) -- having just verified it above in
        # this same request, a LISTING_NOT_FOUND race here would indicate a
        # structural invariant violation elsewhere, not an ordinary outcome
        # to branch on.
        assert placement_result.outcome is PlacementCreationOutcome.CREATED
        assert placement_result.media_placement_id is not None
        assert placement_result.gallery_version is not None

    return UploadImageResult(
        outcome=UploadImageOutcome.CREATED,
        media_asset_id=asset.media_asset_id.value,
        media_placement_id=placement_result.media_placement_id.value,
        gallery_version=placement_result.gallery_version,
    )


# ---------------------------------------------------------------------------
# Reuse (contract §9)
# ---------------------------------------------------------------------------


class ReuseAssetOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    ASSET_NOT_FOUND_OR_DENIED = "ASSET_NOT_FOUND_OR_DENIED"
    CREATED = "CREATED"


@dataclass(frozen=True)
class ReuseAssetResult:
    outcome: ReuseAssetOutcome
    media_placement_id: str | None = None
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        carries = self.outcome is ReuseAssetOutcome.CREATED
        if carries and (self.media_placement_id is None or self.gallery_version is None):
            raise ValueError("A CREATED result must carry media_placement_id/gallery_version")
        if not carries and (
            self.media_placement_id is not None or self.gallery_version is not None
        ):
            raise ValueError("Only a CREATED result may carry those fields")


def reuse_asset_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    media_asset_id_value: str,
) -> ReuseAssetResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return ReuseAssetResult(outcome=ReuseAssetOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return ReuseAssetResult(outcome=ReuseAssetOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return ReuseAssetResult(outcome=ReuseAssetOutcome.PUBLISHER_ROLE_REQUIRED)

    conn.commit()
    with conn.transaction():
        result = create_reused_image_placement(
            conn,
            native_listing_id=NativeListingId(native_listing_id_value),
            owner_organization_id=organization_id,
            requesting_account_id=session.account_id,
            media_asset_id=MediaAssetId(media_asset_id_value),
        )
    if result.outcome is PlacementCreationOutcome.LISTING_NOT_FOUND:
        return ReuseAssetResult(outcome=ReuseAssetOutcome.LISTING_NOT_FOUND)
    if result.outcome is PlacementCreationOutcome.ASSET_NOT_FOUND_OR_DENIED:
        return ReuseAssetResult(outcome=ReuseAssetOutcome.ASSET_NOT_FOUND_OR_DENIED)
    assert result.outcome is PlacementCreationOutcome.CREATED
    assert result.media_placement_id is not None
    assert result.gallery_version is not None
    return ReuseAssetResult(
        outcome=ReuseAssetOutcome.CREATED,
        media_placement_id=result.media_placement_id.value,
        gallery_version=result.gallery_version,
    )


# ---------------------------------------------------------------------------
# YouTube add (contract §10)
# ---------------------------------------------------------------------------


class AddYoutubeOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_URL = "INVALID_URL"
    CREATED = "CREATED"


@dataclass(frozen=True)
class AddYoutubeResult:
    outcome: AddYoutubeOutcome
    media_placement_id: str | None = None
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        carries = self.outcome is AddYoutubeOutcome.CREATED
        if carries and (self.media_placement_id is None or self.gallery_version is None):
            raise ValueError("A CREATED result must carry media_placement_id/gallery_version")
        if not carries and (
            self.media_placement_id is not None or self.gallery_version is not None
        ):
            raise ValueError("Only a CREATED result may carry those fields")


def add_youtube_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_url: Any,
) -> AddYoutubeResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return AddYoutubeResult(outcome=AddYoutubeOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return AddYoutubeResult(outcome=AddYoutubeOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return AddYoutubeResult(outcome=AddYoutubeOutcome.PUBLISHER_ROLE_REQUIRED)

    native_listing_id = NativeListingId(native_listing_id_value)
    if not _verify_listing_ownership(conn, native_listing_id, organization_id):
        return AddYoutubeResult(outcome=AddYoutubeOutcome.LISTING_NOT_FOUND)

    if not isinstance(raw_url, str):
        return AddYoutubeResult(outcome=AddYoutubeOutcome.INVALID_URL)
    video_id = parse_youtube_reference(raw_url)
    if video_id is None:
        return AddYoutubeResult(outcome=AddYoutubeOutcome.INVALID_URL)

    conn.commit()
    with conn.transaction():
        result = create_youtube_placement(
            conn,
            native_listing_id=native_listing_id,
            owner_organization_id=organization_id,
            created_by_account_id=session.account_id,
            youtube_video_id=video_id.value,
            youtube_source_url=raw_url,
        )
    assert result.outcome is PlacementCreationOutcome.CREATED
    assert result.media_placement_id is not None
    assert result.gallery_version is not None
    return AddYoutubeResult(
        outcome=AddYoutubeOutcome.CREATED,
        media_placement_id=result.media_placement_id.value,
        gallery_version=result.gallery_version,
    )


# ---------------------------------------------------------------------------
# Reorder (contract §8/§16)
# ---------------------------------------------------------------------------


class ReorderGalleryOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    INVALID_PLACEMENT_SET = "INVALID_PLACEMENT_SET"
    REORDERED = "REORDERED"


@dataclass(frozen=True)
class ReorderGalleryResult:
    outcome: ReorderGalleryOutcome
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        if self.outcome is ReorderGalleryOutcome.REORDERED and self.gallery_version is None:
            raise ValueError("A REORDERED result must carry gallery_version")
        if self.outcome is not ReorderGalleryOutcome.REORDERED and self.gallery_version is not None:
            raise ValueError("Only a REORDERED result may carry gallery_version")


def _parse_expected_version(raw_body: Any) -> int | None:
    if not isinstance(raw_body, dict):
        return None
    value = raw_body.get("expected_version")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def reorder_gallery_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_body: Any,
) -> ReorderGalleryResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return ReorderGalleryResult(outcome=ReorderGalleryOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return ReorderGalleryResult(outcome=ReorderGalleryOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return ReorderGalleryResult(outcome=ReorderGalleryOutcome.PUBLISHER_ROLE_REQUIRED)

    expected_version = _parse_expected_version(raw_body)
    placement_ids_raw = raw_body.get("placement_ids") if isinstance(raw_body, dict) else None
    if (
        expected_version is None
        or not isinstance(placement_ids_raw, list)
        or not all(isinstance(item, str) and item for item in placement_ids_raw)
    ):
        return ReorderGalleryResult(outcome=ReorderGalleryOutcome.INVALID_PAYLOAD)

    conn.commit()
    with conn.transaction():
        result = reorder_placements(
            conn,
            native_listing_id=NativeListingId(native_listing_id_value),
            owner_organization_id=organization_id,
            ordered_placement_ids=[MediaPlacementId(v) for v in placement_ids_raw],
            expected_version=expected_version,
        )
    if result.outcome is ReorderOutcome.LISTING_NOT_FOUND:
        return ReorderGalleryResult(outcome=ReorderGalleryOutcome.LISTING_NOT_FOUND)
    if result.outcome is ReorderOutcome.VERSION_CONFLICT:
        return ReorderGalleryResult(outcome=ReorderGalleryOutcome.VERSION_CONFLICT)
    if result.outcome is ReorderOutcome.INVALID_PLACEMENT_SET:
        return ReorderGalleryResult(outcome=ReorderGalleryOutcome.INVALID_PLACEMENT_SET)
    assert result.outcome is ReorderOutcome.REORDERED
    assert result.gallery_version is not None
    return ReorderGalleryResult(
        outcome=ReorderGalleryOutcome.REORDERED, gallery_version=result.gallery_version
    )


# ---------------------------------------------------------------------------
# Cover (contract §8)
# ---------------------------------------------------------------------------


class SetCoverRequestOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    INVALID_COVER = "INVALID_COVER"
    #: Independent review Finding C: this ACTIVE listing currently has an
    #: explicit cover and this call would clear it to nothing.
    ACTIVE_LISTING_CONFLICT = "ACTIVE_LISTING_CONFLICT"
    SET = "SET"
    CLEARED = "CLEARED"


@dataclass(frozen=True)
class SetCoverRequestResult:
    outcome: SetCoverRequestOutcome
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        carries = self.outcome in (SetCoverRequestOutcome.SET, SetCoverRequestOutcome.CLEARED)
        if carries and self.gallery_version is None:
            raise ValueError("A SET/CLEARED result must carry gallery_version")
        if not carries and self.gallery_version is not None:
            raise ValueError("Only a SET/CLEARED result may carry gallery_version")


def set_cover_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_body: Any,
) -> SetCoverRequestResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.PUBLISHER_ROLE_REQUIRED)

    expected_version = _parse_expected_version(raw_body)
    if (
        expected_version is None
        or not isinstance(raw_body, dict)
        or set(raw_body)
        - {
            "expected_version",
            "media_placement_id",
        }
    ):
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.INVALID_PAYLOAD)
    raw_placement_id = raw_body.get("media_placement_id")
    if raw_placement_id is not None and (
        not isinstance(raw_placement_id, str) or not raw_placement_id
    ):
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.INVALID_PAYLOAD)

    conn.commit()
    with conn.transaction():
        result = set_cover(
            conn,
            native_listing_id=NativeListingId(native_listing_id_value),
            owner_organization_id=organization_id,
            media_placement_id=(
                MediaPlacementId(raw_placement_id) if raw_placement_id is not None else None
            ),
            expected_version=expected_version,
        )
    if result.outcome is SetCoverOutcome.LISTING_NOT_FOUND:
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.LISTING_NOT_FOUND)
    if result.outcome is SetCoverOutcome.VERSION_CONFLICT:
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.VERSION_CONFLICT)
    if result.outcome is SetCoverOutcome.INVALID_COVER:
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.INVALID_COVER)
    if result.outcome is SetCoverOutcome.ACTIVE_LISTING_CONFLICT:
        return SetCoverRequestResult(outcome=SetCoverRequestOutcome.ACTIVE_LISTING_CONFLICT)
    assert result.gallery_version is not None
    mapped_outcome = (
        SetCoverRequestOutcome.SET
        if result.outcome is SetCoverOutcome.SET
        else SetCoverRequestOutcome.CLEARED
    )
    return SetCoverRequestResult(outcome=mapped_outcome, gallery_version=result.gallery_version)


# ---------------------------------------------------------------------------
# Remove placement (contract §12)
# ---------------------------------------------------------------------------


class RemovePlacementRequestOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    PLACEMENT_NOT_FOUND = "PLACEMENT_NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    #: Independent review Finding C: this placement is the ACTIVE listing's
    #: current cover, or its last remaining valid public IMAGE.
    ACTIVE_LISTING_CONFLICT = "ACTIVE_LISTING_CONFLICT"
    REMOVED = "REMOVED"


@dataclass(frozen=True)
class RemovePlacementRequestResult:
    outcome: RemovePlacementRequestOutcome
    gallery_version: int | None = None

    def __post_init__(self) -> None:
        if self.outcome is RemovePlacementRequestOutcome.REMOVED and self.gallery_version is None:
            raise ValueError("A REMOVED result must carry gallery_version")
        if (
            self.outcome is not RemovePlacementRequestOutcome.REMOVED
            and self.gallery_version is not None
        ):
            raise ValueError("Only a REMOVED result may carry gallery_version")


def remove_placement_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    media_placement_id_value: str,
    raw_body: Any,
) -> RemovePlacementRequestResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return RemovePlacementRequestResult(
            outcome=RemovePlacementRequestOutcome.NOT_FOUND_OR_DENIED
        )
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return RemovePlacementRequestResult(outcome=RemovePlacementRequestOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return RemovePlacementRequestResult(
            outcome=RemovePlacementRequestOutcome.PUBLISHER_ROLE_REQUIRED
        )

    expected_version = _parse_expected_version(raw_body)
    if expected_version is None:
        return RemovePlacementRequestResult(outcome=RemovePlacementRequestOutcome.INVALID_PAYLOAD)

    conn.commit()
    with conn.transaction():
        result = remove_placement(
            conn,
            native_listing_id=NativeListingId(native_listing_id_value),
            owner_organization_id=organization_id,
            media_placement_id=MediaPlacementId(media_placement_id_value),
            expected_version=expected_version,
        )
    if result.outcome is RemovePlacementOutcome.LISTING_NOT_FOUND:
        return RemovePlacementRequestResult(outcome=RemovePlacementRequestOutcome.LISTING_NOT_FOUND)
    if result.outcome is RemovePlacementOutcome.VERSION_CONFLICT:
        return RemovePlacementRequestResult(outcome=RemovePlacementRequestOutcome.VERSION_CONFLICT)
    if result.outcome is RemovePlacementOutcome.PLACEMENT_NOT_FOUND:
        return RemovePlacementRequestResult(
            outcome=RemovePlacementRequestOutcome.PLACEMENT_NOT_FOUND
        )
    if result.outcome is RemovePlacementOutcome.ACTIVE_LISTING_CONFLICT:
        return RemovePlacementRequestResult(
            outcome=RemovePlacementRequestOutcome.ACTIVE_LISTING_CONFLICT
        )
    assert result.outcome is RemovePlacementOutcome.REMOVED
    assert result.gallery_version is not None
    return RemovePlacementRequestResult(
        outcome=RemovePlacementRequestOutcome.REMOVED, gallery_version=result.gallery_version
    )


# ---------------------------------------------------------------------------
# Retire asset (contract §12) -- Organization-scoped, not listing-scoped.
# ---------------------------------------------------------------------------


class RetireAssetRequestOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    ALREADY_RETIRED = "ALREADY_RETIRED"
    #: Independent review Finding C: retiring this asset would leave at
    #: least one ACTIVE listing without its required last valid public
    #: image and/or its explicit valid cover.
    ACTIVE_LISTING_CONFLICT = "ACTIVE_LISTING_CONFLICT"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class RetireAssetRequestResult:
    outcome: RetireAssetRequestOutcome


def retire_asset_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str, media_asset_id_value: str
) -> RetireAssetRequestResult:
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_media_actor(conn, session, organization_id)
    if auth is _MediaActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return RetireAssetRequestResult(outcome=RetireAssetRequestOutcome.NOT_FOUND_OR_DENIED)
    if auth is _MediaActorAuthorizationOutcome.MFA_REQUIRED:
        return RetireAssetRequestResult(outcome=RetireAssetRequestOutcome.MFA_REQUIRED)
    if auth is _MediaActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return RetireAssetRequestResult(outcome=RetireAssetRequestOutcome.PUBLISHER_ROLE_REQUIRED)

    conn.commit()
    with conn.transaction():
        result = retire_media_asset(
            conn,
            media_asset_id=MediaAssetId(media_asset_id_value),
            owner_organization_id=organization_id,
        )
    if result is RetireAssetOutcome.NOT_FOUND:
        return RetireAssetRequestResult(outcome=RetireAssetRequestOutcome.ASSET_NOT_FOUND)
    if result is RetireAssetOutcome.ALREADY_RETIRED:
        return RetireAssetRequestResult(outcome=RetireAssetRequestOutcome.ALREADY_RETIRED)
    if result is RetireAssetOutcome.ACTIVE_LISTING_CONFLICT:
        return RetireAssetRequestResult(outcome=RetireAssetRequestOutcome.ACTIVE_LISTING_CONFLICT)
    assert result is RetireAssetOutcome.RETIRED
    return RetireAssetRequestResult(outcome=RetireAssetRequestOutcome.RETIRED)
