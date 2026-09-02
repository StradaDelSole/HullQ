"""Unit tests for hullq.domain.market_identity — SLICE-0040.

Covers the required test scenarios from
docs/slices/SLICE-0040-marketplace-identity-truth-boundary.md and the
locked semantics in specs/MARKET_IDENTITY_CONTRACT.v0.1.md.
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

import pytest

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

ROOT = Path(__file__).resolve().parents[2]

IDENTITY_KINDS = [
    BoatDesignRef,
    PhysicalBoatId,
    MarketEpisodeId,
    NativeListingId,
    ExternalMarketObservationId,
]


# ---------------------------------------------------------------------------
# Every identity value object rejects empty identifiers
# ---------------------------------------------------------------------------


class TestEmptyIdentifiersRejected:
    @pytest.mark.parametrize("kind", IDENTITY_KINDS)
    def test_empty_value_raises(self, kind: type) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            kind("")


# ---------------------------------------------------------------------------
# Equal raw strings across identity kinds remain distinct
# ---------------------------------------------------------------------------


class TestCrossKindRawTokenCollision:
    def test_equal_raw_text_different_kinds_are_not_equal(self) -> None:
        token = "COLLIDING-TOKEN"
        physical_id = PhysicalBoatId(token)
        listing_id = NativeListingId(token)
        episode_id = MarketEpisodeId(token)
        observation_id = ExternalMarketObservationId(token)
        design_ref = BoatDesignRef(token)

        instances = [physical_id, listing_id, episode_id, observation_id, design_ref]
        for i, left in enumerate(instances):
            for j, right in enumerate(instances):
                if i == j:
                    continue
                assert left != right

    def test_same_kind_same_value_are_equal(self) -> None:
        assert PhysicalBoatId("PB-1") == PhysicalBoatId("PB-1")


# ---------------------------------------------------------------------------
# Wrong-kind relationship references fail at runtime
# ---------------------------------------------------------------------------


class TestWrongKindReferencesFailClosed:
    def test_market_episode_rejects_non_physical_boat_id(self) -> None:
        with pytest.raises(TypeError, match="PhysicalBoatId"):
            MarketEpisode(
                id=MarketEpisodeId("ME-1"),
                physical_boat_id=NativeListingId("NL-1"),  # type: ignore[arg-type]
            )

    def test_physical_boat_rejects_non_boat_design_ref(self) -> None:
        with pytest.raises(TypeError, match="BoatDesignRef"):
            PhysicalBoat(
                id=PhysicalBoatId("PB-1"),
                boat_design_ref=PhysicalBoatId("PB-2"),  # type: ignore[arg-type]
            )

    def test_physical_boat_rejects_wrong_kind_id(self) -> None:
        with pytest.raises(TypeError, match="PhysicalBoatId"):
            PhysicalBoat(id=NativeListingId("NL-1"))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PhysicalBoat / BoatDesignRef
# ---------------------------------------------------------------------------


class TestPhysicalBoatBoatDesignReference:
    def test_physical_boat_with_resolved_boat_design_ref(self) -> None:
        design_ref = BoatDesignRef("BD-OCEANIS-361")
        boat = PhysicalBoat(id=PhysicalBoatId("PB-1"), boat_design_ref=design_ref)
        assert boat.boat_design_ref == design_ref

    def test_physical_boat_may_remain_design_unresolved(self) -> None:
        boat = PhysicalBoat(id=PhysicalBoatId("PB-1"))
        assert boat.boat_design_ref is None


# ---------------------------------------------------------------------------
# One PhysicalBoat -> multiple MarketEpisodes
# ---------------------------------------------------------------------------


class TestPhysicalBoatMultipleEpisodes:
    def test_two_episodes_reference_same_physical_boat(self) -> None:
        boat_id = PhysicalBoatId("PB-1")
        episode_a = MarketEpisode(id=MarketEpisodeId("ME-A"), physical_boat_id=boat_id)
        episode_b = MarketEpisode(id=MarketEpisodeId("ME-B"), physical_boat_id=boat_id)
        assert episode_a.physical_boat_id == episode_b.physical_boat_id == boat_id
        assert episode_a.id != episode_b.id


# ---------------------------------------------------------------------------
# NativeListing resolution states
# ---------------------------------------------------------------------------


class TestNativeListingResolution:
    def test_native_listing_can_remain_unresolved(self) -> None:
        listing = NativeListing(id=NativeListingId("NL-1"))
        assert listing.market_episode_id is None
        assert listing.is_resolved is False

    def test_resolved_native_listing_holds_market_episode_id(self) -> None:
        episode_id = MarketEpisodeId("ME-1")
        listing = NativeListing(id=NativeListingId("NL-1"), market_episode_id=episode_id)
        assert listing.market_episode_id == episode_id
        assert listing.is_resolved is True

    def test_native_listing_rejects_non_market_episode_id_link(self) -> None:
        with pytest.raises(TypeError, match="MarketEpisodeId"):
            NativeListing(
                id=NativeListingId("NL-1"),
                market_episode_id=PhysicalBoatId("PB-1"),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# ExternalMarketObservation
# ---------------------------------------------------------------------------


class TestExternalMarketObservation:
    def test_requires_non_empty_source_id(self) -> None:
        with pytest.raises(ValueError, match="source_id"):
            ExternalMarketObservation(
                id=ExternalMarketObservationId("EMO-1"),
                source_id="",
                source_record_key="REC-1",
            )

    def test_requires_non_empty_source_record_key(self) -> None:
        with pytest.raises(ValueError, match="source_record_key"):
            ExternalMarketObservation(
                id=ExternalMarketObservationId("EMO-1"),
                source_id="yachtworld",
                source_record_key="",
            )

    def test_can_remain_unresolved(self) -> None:
        observation = ExternalMarketObservation(
            id=ExternalMarketObservationId("EMO-1"),
            source_id="yachtworld",
            source_record_key="REC-1",
        )
        assert observation.market_episode_id is None
        assert observation.is_resolved is False

    def test_resolved_observation_holds_market_episode_id(self) -> None:
        episode_id = MarketEpisodeId("ME-1")
        observation = ExternalMarketObservation(
            id=ExternalMarketObservationId("EMO-1"),
            source_id="yachtworld",
            source_record_key="REC-1",
            market_episode_id=episode_id,
        )
        assert observation.market_episode_id == episode_id
        assert observation.is_resolved is True

    def test_rejects_non_market_episode_id_link(self) -> None:
        with pytest.raises(TypeError, match="MarketEpisodeId"):
            ExternalMarketObservation(
                id=ExternalMarketObservationId("EMO-1"),
                source_id="yachtworld",
                source_record_key="REC-1",
                market_episode_id=NativeListingId("NL-1"),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# One MarketEpisode referenced by native + multiple external appearances
# ---------------------------------------------------------------------------


class TestSharedMarketEpisodeAcrossAppearances:
    def test_native_and_multiple_external_reference_same_episode_without_collapse(self) -> None:
        episode_id = MarketEpisodeId("ME-1")
        listing = NativeListing(id=NativeListingId("NL-1"), market_episode_id=episode_id)
        observation_1 = ExternalMarketObservation(
            id=ExternalMarketObservationId("EMO-1"),
            source_id="yachtworld",
            source_record_key="REC-1",
            market_episode_id=episode_id,
        )
        observation_2 = ExternalMarketObservation(
            id=ExternalMarketObservationId("EMO-2"),
            source_id="boat24",
            source_record_key="REC-2",
            market_episode_id=episode_id,
        )

        assert listing.market_episode_id == episode_id
        assert observation_1.market_episode_id == episode_id
        assert observation_2.market_episode_id == episode_id
        assert listing.id != observation_1.id != observation_2.id
        assert observation_1.id != observation_2.id


# ---------------------------------------------------------------------------
# No automatic BoatDesign -> physical/listing technical-fact projection
# ---------------------------------------------------------------------------


class TestNoTruthProjection:
    def test_physical_boat_carries_no_technical_fact_fields(self) -> None:
        field_names = {f.name for f in dataclasses.fields(PhysicalBoat)}
        assert field_names == {"id", "boat_design_ref"}

    def test_native_listing_carries_no_technical_fact_fields(self) -> None:
        field_names = {f.name for f in dataclasses.fields(NativeListing)}
        assert field_names == {"id", "market_episode_id"}

    def test_external_observation_carries_no_technical_fact_fields(self) -> None:
        field_names = {f.name for f in dataclasses.fields(ExternalMarketObservation)}
        assert field_names == {"id", "source_id", "source_record_key", "market_episode_id"}


# ---------------------------------------------------------------------------
# Owner-test output is deterministic/offline
# ---------------------------------------------------------------------------


class TestOwnerScriptDeterministicOffline:
    def test_owner_script_passes_and_is_deterministic(self) -> None:
        script = ROOT / "scripts" / "inspect_market_identity_boundary.py"
        first = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
            timeout=30,
        )
        second = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
            timeout=30,
        )

        assert first.returncode == 0, first.stderr
        assert second.returncode == 0, second.stderr
        assert first.stdout == second.stdout
        assert "BOUNDARY RESULT: PASS" in first.stdout
        assert "RAW TOKEN COLLISION ACROSS KINDS: PRESERVED DISTINCT" in first.stdout
        assert "DESIGN FACTS PROJECTED TO PHYSICAL/LISTING TRUTH: NO" in first.stdout
