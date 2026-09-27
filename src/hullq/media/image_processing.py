"""Server-controlled IMAGE ingestion/trust boundary — SLICE-0068.

Implements `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md` §6: given
untrusted uploaded bytes plus an untrusted client-supplied `Content-Type`
hint, deterministically decode/validate/re-encode a public-usable derivative
-- or fail closed with a mechanically distinct rejection reason, storing and
processing nothing further.

Every check the contract requires runs here, in this exact order:

1. bounded raw byte size, before any decode is attempted (contract §6.1);
2. decode as a real, supported image (contract §6.2/§6.4);
3. bounded decoded pixel count, checked from the lazily-parsed header before
   full pixel-buffer decode is forced (contract §6.3);
4. reject animated input rather than silently preserving only one frame
   (contract §4);
5. force full pixel decode, catching truncated/corrupt data (contract §6.4);
6. bake EXIF orientation into the pixel data, then discard EXIF/ICC/other
   embedded metadata entirely -- including GPS/location tags -- by
   constructing a fresh in-memory RGB image carrying no `.info` at all
   (contract §6.5);
7. safe-re-encode to the one supported v0.1 output format, downscaling (never
   upscaling) to a bounded longest-side dimension (contract §6.6);
8. compute the authoritative output MIME type/dimensions/byte size and a
   content hash of the final derivative (contract §6.7/§6.8).

This module never writes to object storage or PostgreSQL and never sees an
Organization/Account/listing identity -- it is a pure bytes-in, bytes-or-
rejection-out boundary, deliberately reusable by both the real HTTP upload
handler and deterministic tests.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from enum import StrEnum

from PIL import Image, ImageOps

from hullq.domain.media_gallery import (
    MAX_IMAGE_OUTPUT_DIMENSION_PX,
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_IMAGE_UPLOAD_PIXELS,
    OUTPUT_IMAGE_MIME_TYPE,
)

__all__ = [
    "ImageRejectionReason",
    "ProcessedImage",
    "RejectedImage",
    "process_uploaded_image",
]

#: Pillow `Image.format` values this module accepts as real decoded input,
#: independent of any client-supplied `Content-Type` (contract §4/§6.2).
_ACCEPTED_PIL_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})

#: Exceptions Pillow may raise while identifying/decoding malformed or
#: adversarial input -- all collapse to the identical `MALFORMED` rejection
#: (contract §6.4: "reject unsupported/malformed content").
_PIL_DECODE_ERRORS = (Image.DecompressionBombError, OSError, ValueError, SyntaxError, EOFError)


class ImageRejectionReason(StrEnum):
    """Mechanically distinct rejection reasons (contract §6/§18: "reports
    failures" for a per-item error state, never a bare boolean)."""

    TOO_LARGE_BYTES = "TOO_LARGE_BYTES"
    UNSUPPORTED_OR_MALFORMED = "UNSUPPORTED_OR_MALFORMED"
    TOO_LARGE_PIXELS = "TOO_LARGE_PIXELS"
    ANIMATED_UNSUPPORTED = "ANIMATED_UNSUPPORTED"


@dataclass(frozen=True)
class ProcessedImage:
    """The authoritative safe public derivative (contract §6.6/§6.7/§6.8)."""

    data: bytes
    mime_type: str
    width: int
    height: int
    byte_size: int
    content_hash: str


@dataclass(frozen=True)
class RejectedImage:
    reason: ImageRejectionReason


def process_uploaded_image(raw: bytes) -> ProcessedImage | RejectedImage:
    """Validate and re-encode *raw* untrusted uploaded bytes.

    Never raises for ordinary malformed/oversized/animated/unsupported input
    -- every such case returns `RejectedImage`. Only a genuine programming
    error (e.g. *raw* not being `bytes`) raises.
    """
    if not isinstance(raw, bytes):
        raise TypeError(f"raw must be bytes, got {type(raw).__name__}")

    # Contract §6.1: bounded size before any decode/buffering is attempted.
    if len(raw) > MAX_IMAGE_UPLOAD_BYTES:
        return RejectedImage(reason=ImageRejectionReason.TOO_LARGE_BYTES)
    if len(raw) == 0:
        return RejectedImage(reason=ImageRejectionReason.UNSUPPORTED_OR_MALFORMED)

    try:
        img = Image.open(io.BytesIO(raw))
        # `Image.open` is lazy (header-only) for these formats -- `.format`
        # and `.size` are available without forcing a full pixel decode, so
        # the pixel-count bound below runs before any large allocation.
        pil_format = img.format
    except _PIL_DECODE_ERRORS:
        return RejectedImage(reason=ImageRejectionReason.UNSUPPORTED_OR_MALFORMED)

    if pil_format not in _ACCEPTED_PIL_FORMATS:
        return RejectedImage(reason=ImageRejectionReason.UNSUPPORTED_OR_MALFORMED)

    width, height = img.size
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_UPLOAD_PIXELS:
        return RejectedImage(reason=ImageRejectionReason.TOO_LARGE_PIXELS)

    # Contract §4: "An implementation may reject animated input rather than
    # preserve animation" -- v0.1 rejects it outright.
    if getattr(img, "n_frames", 1) > 1:
        return RejectedImage(reason=ImageRejectionReason.ANIMATED_UNSUPPORTED)

    try:
        img.load()  # Forces full pixel decode; raises on truncated/corrupt data.
        # `in_place` defaults to False, so this always returns a new `Image`
        # (never `None` -- that only happens with `in_place=True`).
        oriented = ImageOps.exif_transpose(img)
        if oriented.mode in ("RGBA", "LA") or (
            oriented.mode == "P" and "transparency" in oriented.info
        ):
            rgba = oriented.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, (255, 255, 255))
            flattened.paste(rgba, mask=rgba.split()[-1])
            rgb = flattened
        else:
            rgb = oriented.convert("RGB")
    except _PIL_DECODE_ERRORS:
        return RejectedImage(reason=ImageRejectionReason.UNSUPPORTED_OR_MALFORMED)

    # Contract §6.5: no EXIF/ICC/other embedded metadata survives -- a fresh
    # image built via convert()/paste() above carries no source `.info`
    # forward; clearing it explicitly here removes any doubt/future risk of
    # convert() propagating source metadata.
    rgb.info = {}

    # Contract §6.6: downscale (never upscale) to a bounded longest side.
    rgb.thumbnail(
        (MAX_IMAGE_OUTPUT_DIMENSION_PX, MAX_IMAGE_OUTPUT_DIMENSION_PX), Image.Resampling.LANCZOS
    )

    buffer = io.BytesIO()
    rgb.save(buffer, format="JPEG", quality=85, optimize=True)
    output_bytes = buffer.getvalue()

    return ProcessedImage(
        data=output_bytes,
        mime_type=OUTPUT_IMAGE_MIME_TYPE,
        width=rgb.width,
        height=rgb.height,
        byte_size=len(output_bytes),
        content_hash=hashlib.sha256(output_bytes).hexdigest(),
    )
