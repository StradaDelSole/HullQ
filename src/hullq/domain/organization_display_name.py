"""Bounded MarketplaceOrganization public display-name validation — SLICE-0063.

Implements `specs/PUBLISHING_ORGANIZATION_PUBLIC_IDENTITY_CONTRACT.v0.1.md`
§4: ordinary Unicode broker/Organization names are accepted, meaningful
punctuation and corporate suffixes are preserved, and only leading/trailing
whitespace is trimmed at the write boundary -- internal punctuation,
capitalization and corporate suffixes are never stripped merely for
branding aesthetics (contract §10).
"""

from __future__ import annotations

import unicodedata

__all__ = ["MAX_PUBLIC_DISPLAY_NAME_LENGTH", "normalize_public_display_name"]

#: Bounded per contract §3/§4. Generous enough for real-world corporate
#: broker/dealer names (including multi-part legal suffixes) while still
#: rejecting unbounded input.
MAX_PUBLIC_DISPLAY_NAME_LENGTH = 200


def normalize_public_display_name(raw: str) -> str:
    """Trim boundary whitespace and enforce the v0.1 display-name shape.

    Raises `TypeError`/`ValueError` (never silently coerces) for anything
    that cannot be safely presented: non-`str` input, empty/whitespace-only
    text, control characters, or text exceeding
    `MAX_PUBLIC_DISPLAY_NAME_LENGTH`. Only leading/trailing whitespace is
    removed -- internal whitespace, punctuation, capitalization and
    corporate suffixes are preserved exactly as supplied.
    """
    if not isinstance(raw, str):
        raise TypeError(f"public display name must be a str, got {type(raw).__name__}")

    trimmed = raw.strip()
    if not trimmed:
        raise ValueError("public display name must not be empty or whitespace-only")
    if len(trimmed) > MAX_PUBLIC_DISPLAY_NAME_LENGTH:
        raise ValueError(
            "public display name must be at most "
            f"{MAX_PUBLIC_DISPLAY_NAME_LENGTH} characters, got {len(trimmed)}"
        )
    for char in trimmed:
        # Unicode category "Cc" ("Control") covers exactly the ASCII C0
        # controls (< 0x20), DEL (0x7F), and the Unicode C1 controls
        # (0x80-0x9F, e.g. U+0085 NEL, U+009F APC) -- contract §4's "control
        # character input that cannot be safely presented". This is
        # deliberately narrower than "any non-printable-ish category": it
        # does not reject Cf/Cs/Co/Cn code points, so ordinary Unicode
        # letters/marks used in legitimate international Organization names
        # remain accepted.
        if unicodedata.category(char) == "Cc":
            raise ValueError("public display name must not contain control characters")

    return trimmed
