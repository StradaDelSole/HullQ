"""Unit tests for the SLICE-0049 lifecycle vocabulary (pure, no DB).

Covers the exactly-three-state enum and the PublicationTransitionId identity
kind's fail-closed construction/non-interchangeability.
"""

from __future__ import annotations

import pytest

from hullq.domain.native_listing_lifecycle import (
    NativeListingLifecycleState,
    PublicationTransitionId,
)


def test_lifecycle_state_has_exactly_three_members() -> None:
    assert {member.value for member in NativeListingLifecycleState} == {
        "DRAFT",
        "ACTIVE",
        "WITHDRAWN",
    }


def test_publication_transition_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        PublicationTransitionId("")


def test_publication_transition_id_equality_is_by_value() -> None:
    assert PublicationTransitionId("PTR-1") == PublicationTransitionId("PTR-1")
    assert PublicationTransitionId("PTR-1") != PublicationTransitionId("PTR-2")


def test_publication_transition_id_is_not_interchangeable_with_plain_str() -> None:
    """Equal raw text across identity kinds must not collapse to equality --
    mirrors the same invariant already enforced for every other accepted
    marketplace identity kind."""
    assert PublicationTransitionId("X") != "X"
