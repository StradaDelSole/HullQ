"""Pure unit tests for SLICE-0068 server-controlled IMAGE ingestion —
`hullq.media.image_processing`.

No PostgreSQL/FastAPI/object-storage dependency. Covers contract §6/§17
required proof: supported acceptance, unsupported/malformed/oversized/
animated rejection, EXIF/metadata stripping, bounded output dimensions.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from hullq.domain.media_gallery import (
    MAX_IMAGE_OUTPUT_DIMENSION_PX,
    MAX_IMAGE_UPLOAD_BYTES,
    OUTPUT_IMAGE_MIME_TYPE,
)
from hullq.media.image_processing import (
    ImageRejectionReason,
    ProcessedImage,
    RejectedImage,
    process_uploaded_image,
)


def _jpeg_bytes(
    size: tuple[int, int] = (100, 50), color: tuple[int, int, int] = (255, 0, 0)
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _png_rgba_bytes(size: tuple[int, int] = (30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, (0, 255, 0, 128)).save(buf, format="PNG")
    return buf.getvalue()


def _webp_bytes(size: tuple[int, int] = (40, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="WEBP")
    return buf.getvalue()


class TestAcceptedFormats:
    @pytest.mark.parametrize("factory", [_jpeg_bytes, _png_rgba_bytes, _webp_bytes])
    def test_supported_format_is_accepted_and_reencoded_to_jpeg(self, factory) -> None:
        result = process_uploaded_image(factory())
        assert isinstance(result, ProcessedImage)
        assert result.mime_type == OUTPUT_IMAGE_MIME_TYPE
        assert result.width > 0 and result.height > 0
        assert result.byte_size == len(result.data)
        assert len(result.content_hash) == 64  # sha256 hex digest length
        # Contract §6.7: authoritative output MIME/dimensions come from
        # processing itself, never the client's claimed Content-Type.
        reopened = Image.open(io.BytesIO(result.data))
        assert reopened.format == "JPEG"
        assert reopened.size == (result.width, result.height)

    def test_rgba_png_is_flattened_onto_white_not_black(self) -> None:
        buf = io.BytesIO()
        Image.new("RGBA", (10, 10), (0, 0, 255, 0)).save(buf, format="PNG")  # fully transparent
        result = process_uploaded_image(buf.getvalue())
        assert isinstance(result, ProcessedImage)
        reopened = Image.open(io.BytesIO(result.data)).convert("RGB")
        assert reopened.getpixel((5, 5)) == (255, 255, 255)


class TestRejections:
    def test_empty_bytes_rejected(self) -> None:
        result = process_uploaded_image(b"")
        assert isinstance(result, RejectedImage)
        assert result.reason == ImageRejectionReason.UNSUPPORTED_OR_MALFORMED

    def test_garbage_bytes_rejected(self) -> None:
        result = process_uploaded_image(b"this is not an image at all, just text bytes")
        assert isinstance(result, RejectedImage)
        assert result.reason == ImageRejectionReason.UNSUPPORTED_OR_MALFORMED

    def test_truncated_jpeg_rejected(self) -> None:
        full = _jpeg_bytes()
        truncated = full[: len(full) // 2]
        result = process_uploaded_image(truncated)
        assert isinstance(result, RejectedImage)
        assert result.reason == ImageRejectionReason.UNSUPPORTED_OR_MALFORMED

    def test_unsupported_format_rejected(self) -> None:
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), (1, 2, 3)).save(buf, format="BMP")
        result = process_uploaded_image(buf.getvalue())
        assert isinstance(result, RejectedImage)
        assert result.reason == ImageRejectionReason.UNSUPPORTED_OR_MALFORMED

    def test_oversized_bytes_rejected_before_decode(self) -> None:
        oversized = b"\x00" * (MAX_IMAGE_UPLOAD_BYTES + 1)
        result = process_uploaded_image(oversized)
        assert isinstance(result, RejectedImage)
        assert result.reason == ImageRejectionReason.TOO_LARGE_BYTES

    def test_oversized_pixel_count_rejected(self) -> None:
        buf = io.BytesIO()
        Image.new("RGB", (8000, 8000), (1, 2, 3)).save(buf, format="PNG")
        result = process_uploaded_image(buf.getvalue())
        assert isinstance(result, RejectedImage)
        assert result.reason == ImageRejectionReason.TOO_LARGE_PIXELS

    def test_animated_png_rejected(self) -> None:
        frames = [Image.new("RGB", (10, 10), (i * 40, i * 40, i * 40)) for i in range(3)]
        buf = io.BytesIO()
        frames[0].save(
            buf, format="PNG", save_all=True, append_images=frames[1:], duration=100, loop=0
        )
        result = process_uploaded_image(buf.getvalue())
        assert isinstance(result, RejectedImage)
        assert result.reason == ImageRejectionReason.ANIMATED_UNSUPPORTED


class TestMetadataStripping:
    def test_exif_is_removed_from_output(self) -> None:
        buf = io.BytesIO()
        im = Image.new("RGB", (20, 10), (10, 20, 30))
        exif = im.getexif()
        exif[271] = "SomeCameraMake"  # Make tag -- would leak camera/provenance data
        exif[272] = "SomeCameraModel"  # Model tag
        im.save(buf, format="JPEG", exif=exif)

        result = process_uploaded_image(buf.getvalue())
        assert isinstance(result, ProcessedImage)
        reopened = Image.open(io.BytesIO(result.data))
        assert dict(reopened.getexif()) == {}
        assert "exif" not in reopened.info


class TestDownscaling:
    def test_oversized_dimensions_are_downscaled_never_upscaled(self) -> None:
        buf = io.BytesIO()
        # Within the pixel-count bound but exceeds the output dimension bound
        # on its longest side.
        Image.new("RGB", (6000, 10), (1, 2, 3)).save(buf, format="PNG")
        result = process_uploaded_image(buf.getvalue())
        assert isinstance(result, ProcessedImage)
        assert result.width <= MAX_IMAGE_OUTPUT_DIMENSION_PX
        assert result.height <= MAX_IMAGE_OUTPUT_DIMENSION_PX

    def test_small_image_is_not_upscaled(self) -> None:
        result = process_uploaded_image(_jpeg_bytes(size=(20, 10)))
        assert isinstance(result, ProcessedImage)
        assert result.width == 20
        assert result.height == 10


def test_non_bytes_input_raises_type_error() -> None:
    with pytest.raises(TypeError):
        process_uploaded_image("not bytes")  # type: ignore[arg-type]
