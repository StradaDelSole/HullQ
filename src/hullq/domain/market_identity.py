"""Marketplace identity / truth boundary — SLICE-0040.

Implements the accepted MARKET_IDENTITY_CONTRACT.v0.1 representation of
BoatDesignRef, PhysicalBoat, MarketEpisode, NativeListing and
ExternalMarketObservation as runtime-distinct identity kinds.

This module proves representation, not resolution: no HIN/CIN/name matching,
dedup, episode-continuity inference or automatic MarketEpisode-link
resolution is implemented here. It contains only pure, frozen value objects —
no persistence, ORM or network access.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BoatDesignRef",
    "ExternalMarketObservation",
    "ExternalMarketObservationId",
    "MarketEpisode",
    "MarketEpisodeId",
    "NativeListing",
    "NativeListingId",
    "PhysicalBoat",
    "PhysicalBoatId",
]


def _require_kind(value: object, kind: type, field_label: str) -> None:
    """Fail closed when *value* is not an instance of the required *kind*.

    Equal raw text across different identity kinds must not be accepted as
    interchangeable; this check runs at construction time, not only under
    static type-checking.
    """
    if not isinstance(value, kind):
        raise TypeError(f"{field_label} must be a {kind.__name__}, got {type(value).__name__}")


# ---------------------------------------------------------------------------
# Identity kinds — runtime-distinct even when raw values collide
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoatDesignRef:
    """Marketplace-side pointer to an existing canonical BoatDesign.

    Does not mint, merge, redefine or mutate the referenced BoatDesign and
    carries no technical facts of its own.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("BoatDesignRef.value must be non-empty")


@dataclass(frozen=True)
class PhysicalBoatId:
    """Identifies one specific vessel (PhysicalBoat / MarketVessel)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("PhysicalBoatId.value must be non-empty")


@dataclass(frozen=True)
class MarketEpisodeId:
    """Identifies one sale/market episode for exactly one PhysicalBoat."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("MarketEpisodeId.value must be non-empty")


@dataclass(frozen=True)
class NativeListingId:
    """Identifies one HullQ-hosted market appearance."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("NativeListingId.value must be non-empty")


@dataclass(frozen=True)
class ExternalMarketObservationId:
    """Identifies one source-specific external market appearance."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ExternalMarketObservationId.value must be non-empty")


# ---------------------------------------------------------------------------
# Relationship-bearing records — identity links only, no truth projection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhysicalBoat:
    """One specific vessel identity.

    Not a BoatDesign, listing, market episode or observation. May reference a
    BoatDesign or remain design-unresolved. No HIN/CIN/name/registration
    matching or ownership proof is implemented here.
    """

    id: PhysicalBoatId
    boat_design_ref: BoatDesignRef | None = None

    def __post_init__(self) -> None:
        _require_kind(self.id, PhysicalBoatId, "PhysicalBoat.id")
        if self.boat_design_ref is not None:
            _require_kind(self.boat_design_ref, BoatDesignRef, "PhysicalBoat.boat_design_ref")


@dataclass(frozen=True)
class MarketEpisode:
    """One sale/market episode for exactly one PhysicalBoat.

    Episode continuity (SAME/NEW/UNRESOLVED) is a later resolution
    capability and is not represented here.
    """

    id: MarketEpisodeId
    physical_boat_id: PhysicalBoatId

    def __post_init__(self) -> None:
        _require_kind(self.id, MarketEpisodeId, "MarketEpisode.id")
        _require_kind(self.physical_boat_id, PhysicalBoatId, "MarketEpisode.physical_boat_id")


@dataclass(frozen=True)
class NativeListing:
    """A HullQ-hosted market appearance with its own identity.

    An identity link only — not listing lifecycle/status. May remain
    MarketEpisode-unresolved.
    """

    id: NativeListingId
    market_episode_id: MarketEpisodeId | None = None

    def __post_init__(self) -> None:
        _require_kind(self.id, NativeListingId, "NativeListing.id")
        if self.market_episode_id is not None:
            _require_kind(
                self.market_episode_id, MarketEpisodeId, "NativeListing.market_episode_id"
            )

    @property
    def is_resolved(self) -> bool:
        return self.market_episode_id is not None


@dataclass(frozen=True)
class ExternalMarketObservation:
    """One source-specific external market appearance with its own identity.

    Requires a non-empty source identity and source-side record key. May
    remain MarketEpisode-unresolved. No live source access, rights decision,
    adapter, dedup or automated resolution is authorized here.
    """

    id: ExternalMarketObservationId
    source_id: str
    source_record_key: str
    market_episode_id: MarketEpisodeId | None = None

    def __post_init__(self) -> None:
        _require_kind(self.id, ExternalMarketObservationId, "ExternalMarketObservation.id")
        if not self.source_id:
            raise ValueError("ExternalMarketObservation.source_id must be non-empty")
        if not self.source_record_key:
            raise ValueError("ExternalMarketObservation.source_record_key must be non-empty")
        if self.market_episode_id is not None:
            _require_kind(
                self.market_episode_id,
                MarketEpisodeId,
                "ExternalMarketObservation.market_episode_id",
            )

    @property
    def is_resolved(self) -> bool:
        return self.market_episode_id is not None
