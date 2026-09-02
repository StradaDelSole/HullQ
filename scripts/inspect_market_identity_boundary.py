"""SLICE-0040 marketplace identity / truth boundary owner-inspection.

Deterministic, offline demonstration that BoatDesignRef, PhysicalBoat,
MarketEpisode, NativeListing and ExternalMarketObservation are runtime-
distinct identity kinds, that market appearances may remain MarketEpisode-
unresolved, and that a raw-token collision across identity kinds does not
collapse their identities. Uses synthetic identities only; no network,
credentials or persistence.

Run: uv run python scripts/inspect_market_identity_boundary.py
"""

from __future__ import annotations

import dataclasses
import sys

from hullq.domain.market_identity import (
    BoatDesignRef,
    ExternalMarketObservation,
    ExternalMarketObservationId,
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)

RAW_COLLISION_TOKEN = "RAW-TOKEN-0001"


def _check_raw_token_collision_preserved() -> bool:
    """Same raw text used across two identity kinds must not collapse identity."""
    physical_id = PhysicalBoatId(RAW_COLLISION_TOKEN)
    listing_id = NativeListingId(RAW_COLLISION_TOKEN)
    same_raw_text = physical_id.value == listing_id.value
    distinct_identity = physical_id != listing_id
    wrong_kind_rejected = False
    try:
        MarketEpisode(id=MarketEpisodeId("ME-BAD"), physical_boat_id=listing_id)  # type: ignore[arg-type]
    except TypeError:
        wrong_kind_rejected = True
    return same_raw_text and distinct_identity and wrong_kind_rejected


def _check_no_design_fact_projection() -> bool:
    """PhysicalBoat/NativeListing/ExternalMarketObservation carry identity
    links only — no BoatDesign/Configuration technical-fact fields.
    """
    physical_boat_fields = {f.name for f in dataclasses.fields(PhysicalBoat)}
    native_listing_fields = {f.name for f in dataclasses.fields(NativeListing)}
    external_observation_fields = {f.name for f in dataclasses.fields(ExternalMarketObservation)}
    return (
        physical_boat_fields == {"id", "boat_design_ref"}
        and native_listing_fields == {"id", "market_episode_id"}
        and external_observation_fields
        == {"id", "source_id", "source_record_key", "market_episode_id"}
    )


def main() -> int:
    boat_design_ref = BoatDesignRef("BD-OCEANIS-361-MK1")

    physical_boat = PhysicalBoat(
        id=PhysicalBoatId("PB-0001"),
        boat_design_ref=boat_design_ref,
    )

    episode_a = MarketEpisode(id=MarketEpisodeId("ME-0001"), physical_boat_id=physical_boat.id)
    episode_b = MarketEpisode(id=MarketEpisodeId("ME-0002"), physical_boat_id=physical_boat.id)

    native_listing_linked = NativeListing(
        id=NativeListingId("NL-0001"),
        market_episode_id=episode_a.id,
    )
    native_listing_unresolved = NativeListing(id=NativeListingId("NL-0002"))

    external_observation_linked = ExternalMarketObservation(
        id=ExternalMarketObservationId("EMO-0001"),
        source_id="yachtworld",
        source_record_key="YW-998877",
        market_episode_id=episode_a.id,
    )
    external_observation_unresolved = ExternalMarketObservation(
        id=ExternalMarketObservationId("EMO-0002"),
        source_id="boat24",
        source_record_key="B24-112233",
    )

    print("MARKETPLACE IDENTITY BOUNDARY\n")
    print(f"BoatDesignRef: {boat_design_ref.value}")
    print(f"PhysicalBoat: {physical_boat.id.value} -> BoatDesignRef {boat_design_ref.value}")
    print(f"MarketEpisode A: {episode_a.id.value} -> PhysicalBoat {physical_boat.id.value}")
    print(f"MarketEpisode B: {episode_b.id.value} -> PhysicalBoat {physical_boat.id.value}")
    print(
        f"NativeListing linked: {native_listing_linked.id.value} "
        f"-> MarketEpisode {episode_a.id.value}"
    )
    print(f"NativeListing unresolved: {native_listing_unresolved.id.value} -> UNRESOLVED")
    print(
        f"ExternalObservation linked: {external_observation_linked.id.value} "
        f"-> MarketEpisode {episode_a.id.value}"
    )
    print(
        f"ExternalObservation unresolved: {external_observation_unresolved.id.value} -> UNRESOLVED"
    )
    print()

    checks = {
        "two episodes reference one PhysicalBoat": (
            episode_a.physical_boat_id == episode_b.physical_boat_id == physical_boat.id
        ),
        "native listing resolution states": (
            native_listing_linked.is_resolved and not native_listing_unresolved.is_resolved
        ),
        "external observation resolution states": (
            external_observation_linked.is_resolved
            and not external_observation_unresolved.is_resolved
        ),
        "one episode referenced by native + external without collapse": (
            native_listing_linked.market_episode_id == external_observation_linked.market_episode_id
            and native_listing_linked.id != external_observation_linked.id
        ),
        "raw token collision preserved distinct": _check_raw_token_collision_preserved(),
        "no design-fact projection": _check_no_design_fact_projection(),
    }

    raw_token_ok = checks["raw token collision preserved distinct"]
    no_projection_ok = checks["no design-fact projection"]
    all_ok = all(checks.values())

    print(f"RAW TOKEN COLLISION ACROSS KINDS: {'PRESERVED DISTINCT' if raw_token_ok else 'FAIL'}")
    print(
        f"DESIGN FACTS PROJECTED TO PHYSICAL/LISTING TRUTH: {'NO' if no_projection_ok else 'FAIL'}"
    )
    print(f"BOUNDARY RESULT: {'PASS' if all_ok else 'FAIL'}")

    if not all_ok:
        failed = [name for name, ok in checks.items() if not ok]
        print(f"\nFailed checks: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
