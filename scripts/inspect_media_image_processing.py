"""Ad-hoc smoke check for hullq.media.image_processing — SLICE-0068.

Not a pytest test; a quick manual sanity script, mirroring the repository's
existing `scripts/inspect_*.py` convention.
"""

from __future__ import annotations

import io

from PIL import Image

from hullq.media.image_processing import ProcessedImage, RejectedImage, process_uploaded_image


def main() -> None:
    im = Image.new("RGB", (100, 50), (255, 0, 0))
    buf = io.BytesIO()
    im.save(buf, format="JPEG")
    result = process_uploaded_image(buf.getvalue())
    assert isinstance(result, ProcessedImage), result
    print("jpeg ok:", result.width, result.height, result.mime_type, len(result.data))

    png_buf = io.BytesIO()
    im2 = Image.new("RGBA", (30, 30), (0, 255, 0, 128))
    im2.save(png_buf, format="PNG")
    png_result = process_uploaded_image(png_buf.getvalue())
    assert isinstance(png_result, ProcessedImage), png_result
    print("png rgba ok:", png_result.width, png_result.height, png_result.mime_type)

    bad = process_uploaded_image(b"not an image")
    assert isinstance(bad, RejectedImage)
    print("malformed rejected:", bad.reason)

    big = process_uploaded_image(b"\x00" * 16_000_000)
    assert isinstance(big, RejectedImage)
    print("too-large-bytes rejected:", big.reason)

    huge_pixels = Image.new("RGB", (8000, 8000), (1, 2, 3))
    huge_buf = io.BytesIO()
    huge_pixels.save(huge_buf, format="PNG")
    huge_result = process_uploaded_image(huge_buf.getvalue())
    assert isinstance(huge_result, RejectedImage), huge_result
    print("too-large-pixels rejected:", huge_result.reason)

    gif_buf = io.BytesIO()
    frames = [Image.new("RGB", (10, 10), (i, i, i)) for i in range(3)]
    frames[0].save(gif_buf, format="GIF", save_all=True, append_images=frames[1:])
    gif_result = process_uploaded_image(gif_buf.getvalue())
    assert isinstance(gif_result, RejectedImage), gif_result
    print("gif (unsupported format) rejected:", gif_result.reason)

    apng_buf = io.BytesIO()
    frames[0].save(
        apng_buf, format="PNG", save_all=True, append_images=frames[1:], duration=100, loop=0
    )
    animated_png_result = process_uploaded_image(apng_buf.getvalue())
    assert isinstance(animated_png_result, RejectedImage), animated_png_result
    print("animated png (apng) rejected:", animated_png_result.reason)

    exif_buf = io.BytesIO()
    exif_im = Image.new("RGB", (20, 10), (10, 20, 30))
    exif = exif_im.getexif()
    exif[271] = "TestMake"  # Make tag
    exif_im.save(exif_buf, format="JPEG", exif=exif)
    exif_result = process_uploaded_image(exif_buf.getvalue())
    assert isinstance(exif_result, ProcessedImage), exif_result
    reopened = Image.open(io.BytesIO(exif_result.data))
    print("exif stripped, remaining exif:", reopened.getexif())


if __name__ == "__main__":
    main()
