"""Unit tests for hullq.domain.organization_display_name — SLICE-0063.

Covers `specs/PUBLISHING_ORGANIZATION_PUBLIC_IDENTITY_CONTRACT.v0.1.md` §4:
ordinary Unicode names are accepted, meaningful punctuation/corporate
suffixes are preserved, empty/whitespace-only/control-character/over-limit
input is rejected, and only boundary whitespace is trimmed.
"""

from __future__ import annotations

import pytest

from hullq.domain.organization_display_name import (
    MAX_PUBLIC_DISPLAY_NAME_LENGTH,
    normalize_public_display_name,
)


class TestAcceptedInput:
    def test_ordinary_name_is_preserved_unchanged(self) -> None:
        assert normalize_public_display_name("Ocean Yachts Brokerage") == "Ocean Yachts Brokerage"

    def test_corporate_suffix_preserved(self) -> None:
        assert normalize_public_display_name("Voile & Fils S.A.R.L.") == "Voile & Fils S.A.R.L."

    def test_unicode_name_preserved(self) -> None:
        assert (
            normalize_public_display_name("Segelyachten Müller GmbH") == "Segelyachten Müller GmbH"
        )

    def test_boundary_whitespace_is_trimmed(self) -> None:
        assert normalize_public_display_name("  Ocean Yachts  ") == "Ocean Yachts"

    def test_internal_whitespace_and_punctuation_preserved(self) -> None:
        assert normalize_public_display_name("  A. B.  Yacht Sales, Inc.  ") == (
            "A. B.  Yacht Sales, Inc."
        )

    def test_maximum_length_is_accepted(self) -> None:
        name = "A" * MAX_PUBLIC_DISPLAY_NAME_LENGTH
        assert normalize_public_display_name(name) == name


class TestRejectedInput:
    def test_non_str_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="str"):
            normalize_public_display_name(123)  # type: ignore[arg-type]

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_public_display_name("")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_public_display_name("   \t  ")

    def test_over_limit_rejected(self) -> None:
        with pytest.raises(ValueError, match="200"):
            normalize_public_display_name("A" * (MAX_PUBLIC_DISPLAY_NAME_LENGTH + 1))

    @pytest.mark.parametrize("control_char", ["\n", "\t", "\x00", "\x1f", "\x7f"])
    def test_control_characters_rejected(self, control_char: str) -> None:
        with pytest.raises(ValueError, match="control"):
            normalize_public_display_name(f"Ocean{control_char}Yachts")
