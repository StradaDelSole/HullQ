"""Public listing-scoped media derivative delivery — SLICE-0069.

Implements `specs/MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md` §15:
the public derivative-byte boundary is listing-scoped and fails closed. A
request only ever succeeds when every one of these holds simultaneously:

    the requested listing is currently public eligible
    (hullq.application.current_public_eligibility)
    AND the requested MediaPlacementId belongs to that exact listing
    AND its kind is IMAGE
    AND its MediaAsset is currently public-usable
    AND a derivative object reference exists

Every other case -- unknown/foreign listing, unknown/foreign placement, a
YOUTUBE placement, a REJECTED/rights-UNKNOWN/retired asset, a missing
derivative, or an object-storage retrieval failure -- collapses to the
identical bounded `NOT_FOUND` outcome. This route never accepts or exposes a
raw object key and never serves the private original/quarantine object
(only ever `MediaAssetRecord.derivative_object_key`). No lifecycle/gallery
state is ever mutated by this read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.current_public_eligibility import resolve_current_public_eligibility
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId
from hullq.domain.media_gallery import MediaPlacementId, MediaPlacementKind
from hullq.persistence.media_gallery import fetch_gallery_state
from hullq.storage.object_storage import ObjectNotFoundError, ObjectStorage

__all__ = [
    "GetPublicMediaBytesOutcome",
    "GetPublicMediaBytesResult",
    "get_public_listing_media_bytes",
]


class GetPublicMediaBytesOutcome(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    OK = "OK"


@dataclass(frozen=True, slots=True)
class GetPublicMediaBytesResult:
    outcome: GetPublicMediaBytesOutcome
    data: bytes | None = None
    mime_type: str | None = None

    def __post_init__(self) -> None:
        carries = self.outcome is GetPublicMediaBytesOutcome.OK
        if carries and (self.data is None or self.mime_type is None):
            raise ValueError("An OK result must carry data and mime_type")
        if not carries and (self.data is not None or self.mime_type is not None):
            raise ValueError("Only an OK result may carry data/mime_type")


def get_public_listing_media_bytes(
    conn: Any,
    native_listing_id_value: str,
    media_placement_id_value: str,
    *,
    object_storage: ObjectStorage,
    as_of: datetime,
) -> GetPublicMediaBytesResult:
    """Resolve one public derivative image, or the bounded `NOT_FOUND` outcome.

    A malformed/empty identifier is rejected exactly like an unknown one --
    never a distinguishable validation error on this public, non-enumerating
    surface.
    """
    if not native_listing_id_value or not media_placement_id_value:
        return GetPublicMediaBytesResult(outcome=GetPublicMediaBytesOutcome.NOT_FOUND)

    native_listing_id = NativeListingId(native_listing_id_value)
    media_placement_id = MediaPlacementId(media_placement_id_value)

    eligibility = resolve_current_public_eligibility(conn, native_listing_id, as_of=as_of)
    if eligibility is None or eligibility.status is not CurrentPublicEligibilityStatus.ELIGIBLE:
        return GetPublicMediaBytesResult(outcome=GetPublicMediaBytesOutcome.NOT_FOUND)

    gallery = fetch_gallery_state(conn, native_listing_id)
    placement = next(
        (p for p in gallery.placements if p.media_placement_id == media_placement_id), None
    )
    if placement is None or placement.kind is not MediaPlacementKind.IMAGE:
        return GetPublicMediaBytesResult(outcome=GetPublicMediaBytesOutcome.NOT_FOUND)

    asset = placement.media_asset
    if asset is None or not asset.is_public_usable or asset.derivative_object_key is None:
        return GetPublicMediaBytesResult(outcome=GetPublicMediaBytesOutcome.NOT_FOUND)

    try:
        data = object_storage.get_object(asset.derivative_object_key)
    except ObjectNotFoundError:
        # Object-storage retrieval failure fails closed (contract §15) --
        # never a lifecycle/gallery mutation, never a distinguishable error.
        return GetPublicMediaBytesResult(outcome=GetPublicMediaBytesOutcome.NOT_FOUND)

    assert asset.mime_type is not None
    return GetPublicMediaBytesResult(
        outcome=GetPublicMediaBytesOutcome.OK, data=data, mime_type=asset.mime_type
    )
