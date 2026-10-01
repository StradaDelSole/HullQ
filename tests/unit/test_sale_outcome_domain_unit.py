"""Unit tests for the SLICE-0074 SaleOutcome value representation.

Pure domain tests, no database. Prove: achieved amount/currency
conditionality with no synthetic amount, finite/positive amount enforcement,
currency code shape, and that `recorded_at` never appears here at all --
`sold_date` is the only durable date this module represents, distinct from
`recorded_at` which is purely a persistence-layer concern (contract §3
invariant 5).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from hullq.domain.buyer_lead import LeadId
from hullq.domain.sale_outcome import SaleOutcomeKind, SaleOutcomeRevisionId, SaleOutcomeSnapshot


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {"kind": SaleOutcomeKind.SOLD}
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# SaleOutcomeRevisionId
# ---------------------------------------------------------------------------


def test_revision_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SaleOutcomeRevisionId("")


def test_revision_id_is_not_interchangeable_with_a_plain_string() -> None:
    assert SaleOutcomeRevisionId("REV-1") != "REV-1"


def test_revision_id_is_not_interchangeable_with_a_lead_id_of_equal_value() -> None:
    assert SaleOutcomeRevisionId("SAME-VALUE") != LeadId("SAME-VALUE")


# ---------------------------------------------------------------------------
# Minimal valid snapshot
# ---------------------------------------------------------------------------


def test_bare_sold_outcome_with_no_optional_fields_is_valid() -> None:
    outcome = SaleOutcomeSnapshot(**_base_kwargs())
    assert outcome.kind is SaleOutcomeKind.SOLD
    assert outcome.sold_date is None
    assert outcome.achieved_amount is None
    assert outcome.achieved_currency is None
    assert outcome.originating_lead_id is None


def test_kind_must_be_a_sale_outcome_kind() -> None:
    with pytest.raises(TypeError, match="SaleOutcomeKind"):
        SaleOutcomeSnapshot(**_base_kwargs(kind="SOLD"))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# sold_date -- distinct from recorded_at, which this module never represents
# ---------------------------------------------------------------------------


def test_sold_date_accepts_a_plain_calendar_date() -> None:
    outcome = SaleOutcomeSnapshot(**_base_kwargs(sold_date=date(2026, 9, 30)))
    assert outcome.sold_date == date(2026, 9, 30)


def test_sold_date_must_be_a_date() -> None:
    with pytest.raises(TypeError, match="sold_date"):
        SaleOutcomeSnapshot(**_base_kwargs(sold_date="2026-09-30"))  # type: ignore[arg-type]


def test_module_never_represents_recorded_at() -> None:
    assert not hasattr(SaleOutcomeSnapshot(**_base_kwargs()), "recorded_at")


# ---------------------------------------------------------------------------
# achieved_amount / achieved_currency conditionality
# ---------------------------------------------------------------------------


def test_achieved_amount_requires_achieved_currency() -> None:
    with pytest.raises(ValueError, match="achieved_currency is required"):
        SaleOutcomeSnapshot(**_base_kwargs(achieved_amount=Decimal("100000.00")))


def test_achieved_currency_requires_achieved_amount() -> None:
    with pytest.raises(ValueError, match="achieved_currency must not be populated"):
        SaleOutcomeSnapshot(**_base_kwargs(achieved_currency="EUR"))


def test_achieved_amount_and_currency_together_is_valid() -> None:
    outcome = SaleOutcomeSnapshot(
        **_base_kwargs(achieved_amount=Decimal("118500.00"), achieved_currency="EUR")
    )
    assert outcome.achieved_amount == Decimal("118500.00")
    assert outcome.achieved_currency == "EUR"


def test_achieved_amount_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        SaleOutcomeSnapshot(**_base_kwargs(achieved_amount=Decimal("0"), achieved_currency="EUR"))


def test_achieved_amount_must_be_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        SaleOutcomeSnapshot(
            **_base_kwargs(achieved_amount=Decimal("Infinity"), achieved_currency="EUR")
        )


def test_achieved_amount_is_never_inferred_from_an_asking_price() -> None:
    """This module never references NativeListingOfferSnapshot at all --
    there is no asking-price field here to accidentally copy from."""
    assert not hasattr(SaleOutcomeSnapshot, "asking_price_amount")


@pytest.mark.parametrize("currency", ["eur", "EU", "EURO", "123", ""])
def test_achieved_currency_rejects_malformed_codes(currency: str) -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        SaleOutcomeSnapshot(
            **_base_kwargs(achieved_amount=Decimal("100000.00"), achieved_currency=currency)
        )


# ---------------------------------------------------------------------------
# originating_lead_id
# ---------------------------------------------------------------------------


def test_originating_lead_id_accepts_a_lead_id() -> None:
    outcome = SaleOutcomeSnapshot(**_base_kwargs(originating_lead_id=LeadId("LEAD-1")))
    assert outcome.originating_lead_id == LeadId("LEAD-1")


def test_originating_lead_id_must_be_a_lead_id() -> None:
    with pytest.raises(TypeError, match="originating_lead_id"):
        SaleOutcomeSnapshot(**_base_kwargs(originating_lead_id="LEAD-1"))  # type: ignore[arg-type]


def test_no_lead_is_ever_invented_by_default() -> None:
    outcome = SaleOutcomeSnapshot(**_base_kwargs())
    assert outcome.originating_lead_id is None
