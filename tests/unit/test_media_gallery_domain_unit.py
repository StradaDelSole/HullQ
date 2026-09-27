"""Pure unit tests for SLICE-0068 media gallery domain vocabulary.

No PostgreSQL/FastAPI/object-storage dependency: exercises only
`hullq.domain.media_gallery`'s value types and YouTube URL normalization
(contract §2/§10).
"""

from __future__ import annotations

import pytest

from hullq.domain.media_gallery import (
    MediaAssetId,
    MediaPlacementId,
    YouTubeVideoId,
    parse_youtube_reference,
)


class TestIdentityKinds:
    def test_media_asset_id_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            MediaAssetId("")

    def test_media_placement_id_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            MediaPlacementId("")

    def test_media_asset_id_and_media_placement_id_are_runtime_distinct(self) -> None:
        """Equal raw text across different identity kinds must not be
        interchangeable (contract §2), mirroring
        `hullq.domain.market_identity`'s identical discipline."""
        asset_id = MediaAssetId("SAME-VALUE")
        placement_id = MediaPlacementId("SAME-VALUE")
        assert asset_id != placement_id
        assert type(asset_id) is not type(placement_id)


class TestYouTubeVideoId:
    def test_valid_eleven_char_id_accepted(self) -> None:
        assert YouTubeVideoId("dQw4w9WgXcQ").value == "dQw4w9WgXcQ"

    @pytest.mark.parametrize("raw", ["", "short", "waytoolongvideoid123", "has spaces!"])
    def test_invalid_shape_rejected(self, raw: str) -> None:
        with pytest.raises(ValueError, match="11-character"):
            YouTubeVideoId(raw)


class TestParseYoutubeReference:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ],
    )
    def test_accepted_forms_normalize_to_the_video_id(self, url: str) -> None:
        result = parse_youtube_reference(url)
        assert result == YouTubeVideoId("dQw4w9WgXcQ")

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "not a url",
            "https://vimeo.com/12345678",
            "https://evil.example/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",  # not https
            "https://www.youtube.com/watch?v=short",  # wrong-length id
            "https://www.youtube.com/watch",  # missing v=
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&v=anotherid12",  # duplicate v=
            '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>',
            "javascript:alert(1)",
        ],
    )
    def test_unsupported_or_malformed_input_rejected(self, url: str) -> None:
        assert parse_youtube_reference(url) is None

    def test_non_string_input_rejected(self) -> None:
        assert parse_youtube_reference(None) is None  # type: ignore[arg-type]
