"""Marketplace mixed-media gallery domain — SLICE-0068.

Implements the identity/kind vocabulary required by
`specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md` §2/§4/§10: runtime-distinct
`MediaAssetId`/`MediaPlacementId` identity kinds (mirrors
`hullq.domain.market_identity`'s identical "equal raw text across different
identity kinds must not be interchangeable" discipline), the finite v0.1
media-kind/processing/rights vocabulary, and pure YouTube URL normalization.

This module holds no persistence/network/storage concern -- only pure, frozen
value objects and pure parsing functions.

Contract §7/§0.1 processing model: this implementation processes an uploaded
IMAGE synchronously within one request (`hullq.media.image_processing`
+ `hullq.persistence.media_gallery`), so a `MediaAsset` row is only ever
durably created already in a terminal state -- `APPROVED` (successfully
decoded/validated/re-encoded and stored) or `REJECTED` (validation failed,
nothing stored). There is no separate durably-observable `QUARANTINED`/
`PROCESSING` row: contract §7 requires only that "no intermediate/failure
state can be mistaken for APPROVED", which this two-terminal-state model
satisfies trivially -- a request either completes with a real, already-stored,
approved derivative, or nothing is ever persisted/exposed as usable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import parse_qs, urlsplit

__all__ = [
    "ACCEPTED_IMAGE_INPUT_MIME_TYPES",
    "MAX_IMAGE_OUTPUT_DIMENSION_PX",
    "MAX_IMAGE_UPLOAD_BYTES",
    "MAX_IMAGE_UPLOAD_PIXELS",
    "OUTPUT_IMAGE_MIME_TYPE",
    "MediaAssetId",
    "MediaPlacementId",
    "MediaPlacementKind",
    "MediaProcessingState",
    "MediaRightsState",
    "YouTubeVideoId",
    "parse_youtube_reference",
]


def _require_non_empty(value: str, field_label: str) -> None:
    if not value:
        raise ValueError(f"{field_label} must be non-empty")


@dataclass(frozen=True)
class MediaAssetId:
    """Identifies one Organization-controlled uploaded media asset.

    Runtime-distinct from `MediaPlacementId` and every `hullq.domain.
    market_identity` identity kind even when the raw text value collides
    (contract §2).
    """

    value: str

    def __post_init__(self) -> None:
        _require_non_empty(self.value, "MediaAssetId.value")


@dataclass(frozen=True)
class MediaPlacementId:
    """Identifies one listing-specific placement of a media item.

    Removing a placement never deletes the `MediaAssetId` it references
    (contract §2/§12).
    """

    value: str

    def __post_init__(self) -> None:
        _require_non_empty(self.value, "MediaPlacementId.value")


class MediaPlacementKind(StrEnum):
    """The finite v0.1 gallery media kinds (contract §4).

    `VIDEO`/`BROKER_CI` are contract-recognized future kinds -- neither is
    ever creatable in v0.1 (no direct uploaded-video path exists, and
    Broker-CI is a presentation-only composition-time insertion, never a
    persisted `MediaPlacement` row per contract §4/§15) -- so only `IMAGE`
    and `YOUTUBE` are represented as constructible member values here.
    """

    IMAGE = "IMAGE"
    YOUTUBE = "YOUTUBE"


class MediaProcessingState(StrEnum):
    """Mechanically distinct terminal processing outcomes (contract §7).

    Only `APPROVED` may ever be public-usable or cover; `REJECTED` never can
    be, unconditionally of rights state.
    """

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MediaRightsState(StrEnum):
    """Declared-rights state, independent of processing state (contract §7).

    `UNKNOWN` is the default for any upload that did not carry an explicit
    uploader rights attestation; it never becomes public-usable merely
    because processing succeeded.
    """

    UNKNOWN = "UNKNOWN"
    DECLARED = "DECLARED"


#: Contract §4 v0.1 accepted IMAGE source formats. HEIC/HEIF/SVG/arbitrary
#: binary uploads are never accepted (contract §4/§12).
ACCEPTED_IMAGE_INPUT_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

#: Contract §6 finite implementation constants (contract §6: "must be finite
#: and operationally reasonable" -- exact values are GENUINELY_OPEN policy,
#: not media identity). Enforced *before* unbounded buffering (contract §6.1).
MAX_IMAGE_UPLOAD_BYTES = 15_000_000

#: Enforced against decoded width * height (contract §6.3) to bound
#: decompression/resource abuse independent of the compressed byte size.
MAX_IMAGE_UPLOAD_PIXELS = 40_000_000

#: The public derivative is always re-encoded/resized to at most this many
#: pixels on its longest side (contract §6.6), never the original resolution.
MAX_IMAGE_OUTPUT_DIMENSION_PX = 2400

#: Contract §6.6: one supported controlled output format for every v0.1
#: public derivative, independent of the accepted input format.
OUTPUT_IMAGE_MIME_TYPE = "image/jpeg"


@dataclass(frozen=True)
class YouTubeVideoId:
    """A normalized YouTube video identifier (contract §10).

    Never carries broker-supplied HTML/embed markup -- only the bounded
    11-character video id token itself.
    """

    value: str

    def __post_init__(self) -> None:
        if not _YOUTUBE_VIDEO_ID_RE.fullmatch(self.value):
            raise ValueError(
                f"YouTubeVideoId.value must be an 11-character YouTube video id, got {self.value!r}"
            )


#: A YouTube video id is always exactly 11 characters from this alphabet.
_YOUTUBE_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

#: Accepted YouTube hostnames (contract §10: "Accepted YouTube URL forms").
#: Deliberately excludes every other domain -- this is not a general
#: external-embed mechanism (contract §4/§18).
_YOUTUBE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}
)


def parse_youtube_reference(raw: str) -> YouTubeVideoId | None:
    """Parse *raw* into a canonical `YouTubeVideoId`, or `None` if unsupported.

    Accepts only `https://www.youtube.com/watch?v=<id>` (and the `m.`/bare
    `youtube.com` host variants), `https://youtu.be/<id>` and
    `https://www.youtube.com/embed/<id>` forms (contract §10). Any other
    host, scheme, malformed URL, or a syntactically-URL-shaped string that
    does not resolve to exactly one valid 11-character video id is rejected
    -- never partially accepted, and never treated as HTML/embed code
    (contract §4/§18: "Arbitrary iframe/embed HTML ... are prohibited").
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = raw.strip()

    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None

    if parts.scheme != "https":
        return None
    host = parts.hostname.lower() if parts.hostname else None
    if host not in _YOUTUBE_HOSTS:
        return None

    video_id_text: str | None = None
    if host == "youtu.be":
        segments = [seg for seg in parts.path.split("/") if seg]
        if len(segments) == 1:
            video_id_text = segments[0]
    else:
        path = parts.path
        if path == "/watch":
            query = parse_qs(parts.query)
            values = query.get("v")
            if values is not None and len(values) == 1:
                video_id_text = values[0]
        elif path.startswith("/embed/"):
            segments = [seg for seg in path[len("/embed/") :].split("/") if seg]
            if len(segments) == 1:
                video_id_text = segments[0]
        elif path.startswith("/shorts/"):
            segments = [seg for seg in path[len("/shorts/") :].split("/") if seg]
            if len(segments) == 1:
                video_id_text = segments[0]

    if video_id_text is None or not _YOUTUBE_VIDEO_ID_RE.fullmatch(video_id_text):
        return None
    return YouTubeVideoId(video_id_text)
