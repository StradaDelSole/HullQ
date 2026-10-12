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
    "InvalidDesignAssociationRequestError",
    "InvalidDesignSelectorQueryError",
    "parse_design_association_request",
    "parse_design_selector_query",
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


@dataclass(frozen=True, slots=True)
class DesignCandidate:
    """One exact-canonical-identity candidate shown by the bounded selector.

    Every field is read verbatim from durable canonical identity storage
    (`hullq.persistence.identity_readback`'s own `canonical_boat_designs`/
    `canonical_boat_models`/`canonical_brands` authority) -- this type
    carries no derived/guessed/fuzzy-matched value. `generation` is the raw
    recorded JSON shape (or `None`); `brand_names`/`first_built`/
    `last_built` are `()`/`None` when genuinely unrecorded, which the
    broker-facing selector must label as unknown, never silently omit as if
    it meant "no brand".
    """

    boat_design_ref: BoatDesignRef
    boat_model_id: str
    canonical_model_name: str
    generation: Any
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
