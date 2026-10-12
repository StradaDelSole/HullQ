"""Broker-facing NativeListing PhysicalBoat -> canonical BoatDesign first
association -- SLICE-0082.

Pure, persistence-neutral domain surface for
`specs/MARKET_IDENTITY_CONTRACT.v0.1.md`-governed confirmation: bounded
candidate selector request parsing, the exact-canonical-identity candidate
projection shape, and the association write request shape. No database, no
FastAPI, no Account/Organization/session lookup and no fuzzy matching --
every candidate is an existing durable `canonical_boat_designs` row read
verbatim, never minted/guessed here.

A `DesignConfirmationMethod` is deliberately a single fixed value in this
slice: the only accepted evidence is an authenticated broker's own explicit
selector confirmation (Required Behavior #2 -- "this does not verify the
boat's actual keel, rudder, draft, year or configuration"). Introducing a
second confirmation method later is an explicit decision, not a silent
extension of this enum.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import BoatDesignRef

__all__ = [
    "DESIGN_SELECTOR_MAX_RESULTS",
    "MAX_DESIGN_SELECTOR_QUERY_LENGTH",
    "DesignCandidate",
    "DesignConfirmationMethod",
    "GenerationIdentity",
    "InvalidDesignAssociationRequestError",
    "InvalidDesignSelectorQueryError",
    "parse_design_association_request",
    "parse_design_selector_query",
    "parse_generation_identity",
]

#: Required Behavior #1: "server-defined max 20 results per query" -- a hard
#: ceiling, not a default a caller can raise.
DESIGN_SELECTOR_MAX_RESULTS = 20

#: Generous enough for any real brand/model search phrase, far below any
#: plausible legitimate query -- bounds parsing cost before a single SQL
#: parameter is ever built, independent of the persistence-layer LIMIT.
MAX_DESIGN_SELECTOR_QUERY_LENGTH = 200


class DesignConfirmationMethod(StrEnum):
    """The exact evidence kind recorded for one association event.

    A single fixed value: an authenticated broker's own explicit selector
    confirmation. Never inferred, never a fuzzy/automatic match.
    """

    MANUAL_SELECTOR_CONFIRMATION = "MANUAL_SELECTOR_CONFIRMATION"


#: `BOAT_DESIGN_SCHEMA.v0.5` §`generation.boundary_confidence`'s exact closed
#: vocabulary. A value outside this set is treated as genuinely unrecorded
#: (`None`) rather than guessed -- see `parse_generation_identity`.
_GENERATION_BOUNDARY_CONFIDENCE_VALUES = frozenset({"high", "medium", "low", "unknown"})


@dataclass(frozen=True, slots=True)
class GenerationIdentity:
    """The recorded `BOAT_DESIGN_SCHEMA.v0.5` §`generation` identity block,
    projected safely and verbatim (independent review Finding B, 2026-10-12).

    This is what actually distinguishes two canonical designs that share an
    identical brand, model name and even identical BoatModel-level
    first/last-built years but are genuinely different designs (a different
    generation/hull revision): `label`/`sequence` are the recorded
    generation identity itself; `first_built`/`last_built`/
    `hull_number_from`/`hull_number_to` are *this generation's own*
    recorded production boundary -- independent of, and potentially
    narrower than, the parent BoatModel's overall first/last-built years
    already shown elsewhere. `boundary_confidence` is the schema's own
    explicit confidence in that boundary, shown so a broker never reads an
    uncertain boundary as a certain one.

    Every field is `None`/`()` only when genuinely unrecorded or when the
    underlying stored value could not be safely interpreted as its declared
    type -- never a guessed/inferred value standing in for an absent one.
    """

    label: str | None
    sequence: int | None
    aliases: tuple[str, ...]
    first_built: int | None
    last_built: int | None
    hull_number_from: str | None
    hull_number_to: str | None
    boundary_confidence: str | None


def _safe_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _safe_int(value: Any) -> int | None:
    # bool is an int subclass in Python; a boundary year/sequence number
    # stored as a boolean is not a value this projection will ever trust.
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_generation_identity(raw: Any) -> GenerationIdentity:
    """Safely project a raw `canonical_boat_designs.generation` JSONB value
    into a typed `GenerationIdentity`.

    This is a defensive *read* projection, not a second admission validator:
    canonical admission already enforces `BOAT_DESIGN_SCHEMA.v0.5`'s exact
    `generation` shape, so a non-conforming stored value is not expected to
    be reachable here -- but if one is ever encountered (a future schema
    migration, a direct-SQL seeding error), every field independently
    degrades to `None`/`()` rather than raising or guessing, so a
    display-layer caller always receives a safely renderable value and
    never silently fabricates one.
    """
    if not isinstance(raw, dict):
        return GenerationIdentity(
            label=None,
            sequence=None,
            aliases=(),
            first_built=None,
            last_built=None,
            hull_number_from=None,
            hull_number_to=None,
            boundary_confidence=None,
        )
    aliases_raw = raw.get("aliases")
    aliases = (
        tuple(a for a in aliases_raw if isinstance(a, str) and a)
        if isinstance(aliases_raw, list)
        else ()
    )
    boundary_confidence = raw.get("boundary_confidence")
    return GenerationIdentity(
        label=_safe_str(raw.get("label")),
        sequence=_safe_int(raw.get("sequence")),
        aliases=aliases,
        first_built=_safe_int(raw.get("first_built")),
        last_built=_safe_int(raw.get("last_built")),
        hull_number_from=_safe_str(raw.get("hull_number_from")),
        hull_number_to=_safe_str(raw.get("hull_number_to")),
        boundary_confidence=(
            boundary_confidence
            if boundary_confidence in _GENERATION_BOUNDARY_CONFIDENCE_VALUES
            else None
        ),
    )


@dataclass(frozen=True, slots=True)
class DesignCandidate:
    """One exact-canonical-identity candidate shown by the bounded selector.

    Every field is read verbatim from durable canonical identity storage
    (`hullq.persistence.identity_readback`'s own `canonical_boat_designs`/
    `canonical_boat_models`/`canonical_brands` authority) -- this type
    carries no derived/guessed/fuzzy-matched value. `generation` is the
    safely-typed `GenerationIdentity` projection (independent review
    Finding B) -- never the raw opaque JSON a display layer would have to
    interpret itself; `brand_names`/`first_built`/`last_built` are
    `()`/`None` when genuinely unrecorded, which the broker-facing selector
    must label as unknown, never silently omit as if it meant "no brand".
    """

    boat_design_ref: BoatDesignRef
    boat_model_id: str
    canonical_model_name: str
    generation: GenerationIdentity
    brand_names: tuple[str, ...]
    first_built: int | None
    last_built: int | None


class InvalidDesignSelectorQueryError(ValueError):
    """Raised for a malformed selector query. Callers must fail the whole
    request closed (400) -- never a best-effort partial parse."""


def parse_design_selector_query(raw: Any) -> str:
    """Parse the optional free-text selector search term.

    Missing/`None`/empty is valid and means "no filter" (bounded first-N
    candidates, never an unbounded/unfiltered catalog dump since the
    persistence layer still applies its own hard result limit). Must be a
    string within `MAX_DESIGN_SELECTOR_QUERY_LENGTH`; the returned value is
    stripped of leading/trailing whitespace only -- never silently truncated.
    """
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise InvalidDesignSelectorQueryError(f"query must be a string, got {type(raw).__name__}")
    stripped = raw.strip()
    if len(stripped) > MAX_DESIGN_SELECTOR_QUERY_LENGTH:
        raise InvalidDesignSelectorQueryError(
            f"query must be at most {MAX_DESIGN_SELECTOR_QUERY_LENGTH} characters"
        )
    return stripped


class InvalidDesignAssociationRequestError(ValueError):
    """Raised for an unknown key or an invalid `boat_design_ref` shape.
    Callers must fail the whole request closed (400) with zero mutation --
    never a partial accept."""


_BOAT_DESIGN_REF_KEY = "boat_design_ref"
_ASSOCIATION_REQUEST_KEYS = frozenset({_BOAT_DESIGN_REF_KEY})


def parse_design_association_request(raw: Any) -> BoatDesignRef:
    """Parse the exactly-one-key POST body `{"boat_design_ref": "<id>"}`.

    Rejects missing/extra keys, `None`, non-string and empty-string values.
    Never accepts a PhysicalBoatId/NativeListingId/MarketEpisodeId or any
    other identity kind in this field -- only a `BoatDesignRef`-shaped
    string is ever constructed here (SLICE-0040 contract: identity kinds
    must never be interchangeable).
    """
    if not isinstance(raw, dict):
        raise InvalidDesignAssociationRequestError("request body must be a JSON object")
    extra_keys = set(raw) - _ASSOCIATION_REQUEST_KEYS
    if extra_keys:
        raise InvalidDesignAssociationRequestError(f"unknown key(s): {sorted(extra_keys)}")
    if _BOAT_DESIGN_REF_KEY not in raw:
        raise InvalidDesignAssociationRequestError(f"{_BOAT_DESIGN_REF_KEY} is required")
    value = raw[_BOAT_DESIGN_REF_KEY]
    if not isinstance(value, str) or not value:
        raise InvalidDesignAssociationRequestError(
            f"{_BOAT_DESIGN_REF_KEY} must be a non-empty string"
        )
    return BoatDesignRef(value)
