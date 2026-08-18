"""First-class Brand/Organization identity primitives and deterministic search-label generation.

Implements the accepted IDENTITY_MODEL.v0.2 / ADR-0011 Brand-Builder separation.
Contains only pure value objects and search-key generation — no persistence, ORM,
network resolution, or query/ranking semantics (OQ-009 remains unresolved).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "AliasClass",
    "Brand",
    "BrandModelRelationship",
    "BuilderRole",
    "IdentityAlias",
    "Organization",
    "OrganizationDesignRelationship",
    "generate_search_keys",
]


# ---------------------------------------------------------------------------
# Alias vocabulary — must exactly match IDENTITY_ALIAS_SCHEMA.v0.1.json enum
# ---------------------------------------------------------------------------


class AliasClass(StrEnum):
    """Normative alias class vocabulary.

    Values must exactly match the ``alias_class`` enum in
    ``IDENTITY_ALIAS_SCHEMA.v0.1.json``. Tests enforce this invariant.
    """

    COMMON_NAME = "common_name"
    TRADE_NAME = "trade_name"
    ABBREVIATION = "abbreviation"
    HISTORICAL_NAME = "historical_name"
    ALTERNATE_SPELLING = "alternate_spelling"
    TRANSLITERATION = "transliteration"
    SOURCE_SPELLING = "source_spelling"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Builder/manufacturer role vocabulary — matches BOAT_DESIGN_SCHEMA.v0.5.json
# and ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1.json
# ---------------------------------------------------------------------------


class BuilderRole(StrEnum):
    """Role of an Organization in a BoatDesign build relationship."""

    BUILDER = "builder"
    MANUFACTURER = "manufacturer"
    LICENSED_BUILDER = "licensed_builder"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Identity value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityAlias:
    """An entity-scoped alias record.

    Stable via ``id``; MUST NOT depend on array position for provenance.
    Aliases are scoped to the entity they name: Brand aliases must not appear
    on Organization records and vice versa.
    """

    id: str
    alias_class: AliasClass
    name: str
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("IdentityAlias.id must be non-empty")
        if not self.name:
            raise ValueError("IdentityAlias.name must be non-empty")


@dataclass(frozen=True)
class Organization:
    """A productive/legal organization (shipyard, builder, manufacturer).

    Separate first-class identity from Brand/Marque (ADR-0011).
    The same visible name does not collapse an Organization into a Brand.
    """

    id: str
    canonical_name: str
    aliases: tuple[IdentityAlias, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Organization.id must be non-empty")
        if not self.canonical_name:
            raise ValueError("Organization.canonical_name must be non-empty")


@dataclass(frozen=True)
class Brand:
    """A market-facing marque under which a BoatModel is marketed.

    Separate first-class identity from Organization/Builder (ADR-0011).
    The same visible name does not collapse a Brand into an Organization.
    """

    id: str
    canonical_name: str
    aliases: tuple[IdentityAlias, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Brand.id must be non-empty")
        if not self.canonical_name:
            raise ValueError("Brand.canonical_name must be non-empty")


@dataclass(frozen=True)
class BrandModelRelationship:
    """An independently identifiable relationship between a Brand and a BoatModel.

    Supports multiple historical associations and optional applicability bounds.
    """

    id: str
    brand_id: str
    boat_model_id: str
    first_year: int | None = None
    last_year: int | None = None
    hull_number_from: str | None = None
    hull_number_to: str | None = None
    market: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("BrandModelRelationship.id must be non-empty")
        if not self.brand_id:
            raise ValueError("BrandModelRelationship.brand_id must be non-empty")
        if not self.boat_model_id:
            raise ValueError("BrandModelRelationship.boat_model_id must be non-empty")


@dataclass(frozen=True)
class OrganizationDesignRelationship:
    """An independently identifiable builder/manufacturer relationship between
    an Organization and a BoatDesign.

    A builder change alone must not create a new BoatDesign (ADR-0004).
    Multiple time-bounded builder entries per BoatDesign are supported.
    """

    id: str
    organization_id: str
    boat_design_id: str
    role: BuilderRole
    first_year: int | None = None
    last_year: int | None = None
    hull_number_from: str | None = None
    hull_number_to: str | None = None
    market: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("OrganizationDesignRelationship.id must be non-empty")
        if not self.organization_id:
            raise ValueError("OrganizationDesignRelationship.organization_id must be non-empty")
        if not self.boat_design_id:
            raise ValueError("OrganizationDesignRelationship.boat_design_id must be non-empty")


# ---------------------------------------------------------------------------
# Deterministic search-label generation (REQ-SEARCH-008/009)
# ---------------------------------------------------------------------------

# Terminal corporate suffixes and country annotations to strip in search projections.
# Order matters for the combined pattern: longer/more-specific patterns first.
# Stripping is applied iteratively until no further suffix is removed.
# Canonical names are NEVER mutated; these are search-projection tokens only.
_SUFFIX_PATTERN = re.compile(
    r"""
    \s*                       # optional leading whitespace before suffix
    ,?                        # optional preceding comma (e.g. "Co., Ltd.")
    \s*
    (?:
        ltd\.?                # Ltd. or Ltd
        | limited
        | inc\.?              # Inc. or Inc
        | corp\.?             # Corp. or Corp
        | corporation
        | gmbh
        | co\.?               # Co. or Co
        | company
        | \([a-z]{2,4}\)      # country annotations: (usa), (uk), (fra), etc.
    )
    \s*$                      # end of string
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize(name: str) -> str:
    """Case-fold and collapse whitespace/punctuation for search projection."""
    folded = unicodedata.normalize("NFC", name).casefold()
    return " ".join(folded.split())


def _strip_suffixes(normalized: str) -> str:
    """Iteratively remove terminal corporate suffixes and country annotations.

    Applied to search projections only; never to canonical or source strings.
    """
    result = normalized
    while True:
        stripped = _SUFFIX_PATTERN.sub("", result).rstrip(" ,")
        if stripped == result:
            break
        result = stripped
    return result.strip()


def generate_search_keys(
    canonical_name: str,
    aliases: Sequence[IdentityAlias] = (),
) -> frozenset[str]:
    """Return a frozenset of deterministic search keys for an identity entity.

    The projection MAY:
    - case-fold and normalize whitespace/punctuation;
    - produce a shortened key by stripping accepted non-distinguishing terminal
      corporate suffixes and country annotations;
    - include normalized alias names as additional lookup terms for
      explicitly supplied aliases.

    The projection MUST NOT:
    - mutate canonical names or source strings;
    - merge distinct entity IDs;
    - perform fuzzy/typo matching or ranking (OQ-009 deferred);
    - infer Brand vs Organization from any string pattern.

    Two distinct entity IDs may produce the same normalized key; that is
    expected behavior and does not imply identity collapse.
    """
    keys: set[str] = set()

    base = _normalize(canonical_name)
    if base:
        keys.add(base)
        shortened = _strip_suffixes(base)
        if shortened and shortened != base:
            keys.add(shortened)

    for alias in aliases:
        alias_key = _normalize(alias.name)
        if alias_key:
            keys.add(alias_key)

    return frozenset(keys)
