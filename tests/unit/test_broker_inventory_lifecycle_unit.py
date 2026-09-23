"""Pure unit tests for SLICE-0064 broker inventory lifecycle orchestration.

No PostgreSQL/FastAPI dependency: exercises only
`hullq.application.broker_inventory_lifecycle`'s pure helpers -- the
strict-canonical-UUID reconfirm operation-identity parser (contract §11) and
the result dataclasses' invariants (never a bare boolean, never a field
attached to the wrong outcome).
"""

from __future__ import annotations

import uuid

import pytest

from hullq.application.broker_inventory_lifecycle import (
    InventoryLifecycleOutcome,
    LifecycleActionResult,
    ReconfirmInventoryOutcome,
    ReconfirmResult,
    _parse_confirmation_id,
)
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
from hullq.domain.native_listing_lifecycle import PublicationTransitionId
from hullq.domain.publishing_eligibility import PublishingEligibilityReason


class TestParseConfirmationId:
    def test_canonical_uuid_string_is_accepted(self) -> None:
        raw = str(uuid.uuid4())
        result = _parse_confirmation_id(raw)
        assert result == FreshnessConfirmationId(raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "not-a-uuid",
            "  ",
            "12345678-1234-1234-1234-1234567890ZZ",
        ],
    )
    def test_non_uuid_string_is_rejected(self, raw: str) -> None:
        assert _parse_confirmation_id(raw) is None

    def test_non_canonical_uppercase_uuid_is_rejected(self) -> None:
        """A different spelling of the identical UUID must not be silently
        canonicalized -- reject it so exactly one stable string is ever
        accepted as one operation identity."""
        canonical = str(uuid.uuid4())
        uppercased = canonical.upper()
        assert _parse_confirmation_id(uppercased) is None

    def test_uuid_without_hyphens_is_rejected(self) -> None:
        canonical = str(uuid.uuid4())
        no_hyphens = canonical.replace("-", "")
        assert _parse_confirmation_id(no_hyphens) is None

    @pytest.mark.parametrize("raw", [None, 123, 1.5, True, [], {}])
    def test_non_string_input_is_rejected(self, raw: object) -> None:
        assert _parse_confirmation_id(raw) is None


class TestLifecycleActionResultInvariants:
    def test_denied_without_reason_raises(self) -> None:
        with pytest.raises(ValueError):
            LifecycleActionResult(outcome=InventoryLifecycleOutcome.DENIED)

    def test_non_denied_with_reason_raises(self) -> None:
        with pytest.raises(ValueError):
            LifecycleActionResult(
                outcome=InventoryLifecycleOutcome.STATE_CONFLICT,
                denial_reason=PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
            )

    def test_published_without_transition_id_raises(self) -> None:
        with pytest.raises(ValueError):
            LifecycleActionResult(outcome=InventoryLifecycleOutcome.PUBLISHED)

    def test_non_transition_outcome_with_transition_id_raises(self) -> None:
        with pytest.raises(ValueError):
            LifecycleActionResult(
                outcome=InventoryLifecycleOutcome.LISTING_NOT_FOUND,
                transition_id=PublicationTransitionId("PT-1"),
            )

    def test_published_to_public_dict_carries_transition_id(self) -> None:
        result = LifecycleActionResult(
            outcome=InventoryLifecycleOutcome.PUBLISHED,
            transition_id=PublicationTransitionId("PT-1"),
        )
        assert result.to_public_dict() == {"outcome": "PUBLISHED", "transition_id": "PT-1"}

    def test_denied_to_public_dict_carries_reason(self) -> None:
        result = LifecycleActionResult(
            outcome=InventoryLifecycleOutcome.DENIED,
            denial_reason=PublishingEligibilityReason.ORGANIZATION_UNVERIFIED,
        )
        assert result.to_public_dict() == {
            "outcome": "DENIED",
            "reason": "ORGANIZATION_UNVERIFIED",
        }


class TestReconfirmResultInvariants:
    def test_denied_without_reason_raises(self) -> None:
        with pytest.raises(ValueError):
            ReconfirmResult(outcome=ReconfirmInventoryOutcome.DENIED)

    def test_reconfirmed_without_occurred_at_raises(self) -> None:
        with pytest.raises(ValueError):
            ReconfirmResult(outcome=ReconfirmInventoryOutcome.RECONFIRMED)

    def test_non_reconfirmed_with_occurred_at_raises(self) -> None:
        from datetime import UTC, datetime

        with pytest.raises(ValueError):
            ReconfirmResult(
                outcome=ReconfirmInventoryOutcome.STATE_CONFLICT,
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_reconfirmed_to_public_dict_carries_occurred_at(self) -> None:
        from datetime import UTC, datetime

        occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
        result = ReconfirmResult(
            outcome=ReconfirmInventoryOutcome.RECONFIRMED, occurred_at=occurred_at
        )
        assert result.to_public_dict() == {
            "outcome": "RECONFIRMED",
            "occurred_at": occurred_at.isoformat(),
        }
