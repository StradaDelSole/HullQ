"""Broker Sale / Outcome close-out value representation — SLICE-0074.

Implements `specs/BROKER_SALE_OUTCOME_CONTRACT.v0.1.md` §4/§5/§6: the
initial, bounded outcome vocabulary (`SOLD` only) and the typed, internally
consistent snapshot of one SOLD report -- optional `sold_date`, optional
achieved amount+currency (currency required iff amount is present) and an
optional originating Lead reference.

`sold_date` is a calendar date, deliberately distinct from the persisted
`recorded_at` timestamp (contract §3 invariant 5: "`recorded_at` is distinct
from `sold_date`") -- this module never conflates the two. Achieved sale
price is represented as `decimal.Decimal`, never a binary-floating-point
type, and is never derived from an asking price (contract §3 invariant 4);
nothing in this module reads or references `NativeListingOfferSnapshot` at
all.

This module contains only pure, frozen value objects — no persistence, ORM
or network access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from hullq.domain.buyer_lead import LeadId

__all__ = [
    "SaleOutcomeKind",
    "SaleOutcomeRevisionId",
    "SaleOutcomeSnapshot",
]

_CURRENCY_CODE_RE = re.compile(r"^[A-Z]{3}$")


def _require_kind(value: object, kind: type, field_label: str) -> None:
    """Mirrors `hullq.domain.native_listing_offer._require_kind`: equal raw
    values across different identity/claim kinds must never be accepted as
    interchangeable, enforced at construction time."""
    if not isinstance(value, kind):
        raise TypeError(f"{field_label} must be a {kind.__name__}, got {type(value).__name__}")


class SaleOutcomeKind(StrEnum):
    """Bounded outcome vocabulary (contract §5). v0.1 supports exactly
    `SOLD` -- ordinary WITHDRAWN lifecycle is never duplicated here."""

    SOLD = "SOLD"


@dataclass(frozen=True)
class SaleOutcomeRevisionId:
    """Identifies one immutable NativeListing SaleOutcome revision.

    Not interchangeable with `NativeListingId`, `NativeListingOfferRevisionId`
    or any other accepted marketplace identity kind, even when the
    underlying raw text collides.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("SaleOutcomeRevisionId.value must be non-empty")


@dataclass(frozen=True)
class SaleOutcomeSnapshot:
    """One complete, internally-consistent SaleOutcome report (contract §6).

    Every field besides `kind` is optional -- unknown/unavailable values stay
    absent, never fabricated (contract §6: "the UI must not force fabricated
    values"). `achieved_currency` is required iff `achieved_amount` is
    present, mirroring `NativeListingOfferSnapshot`'s identical
    amount/currency conditionality.
    """

    kind: SaleOutcomeKind
    sold_date: date | None = None
    achieved_amount: Decimal | None = None
    achieved_currency: str | None = None
    originating_lead_id: LeadId | None = None

    def __post_init__(self) -> None:
        _require_kind(self.kind, SaleOutcomeKind, "SaleOutcomeSnapshot.kind")

        if self.sold_date is not None:
            _require_kind(self.sold_date, date, "SaleOutcomeSnapshot.sold_date")

        if self.achieved_amount is not None:
            _require_kind(self.achieved_amount, Decimal, "SaleOutcomeSnapshot.achieved_amount")
            if not self.achieved_amount.is_finite():
                raise ValueError(
                    f"achieved_amount must be a finite value, got {self.achieved_amount!r}"
                )
            if self.achieved_amount <= 0:
                raise ValueError("achieved_amount must be a positive amount")
            if self.achieved_currency is None:
                raise ValueError("achieved_currency is required when achieved_amount is present")
        elif self.achieved_currency is not None:
            raise ValueError("achieved_currency must not be populated without achieved_amount")

        if self.achieved_currency is not None and not _CURRENCY_CODE_RE.fullmatch(
            self.achieved_currency
        ):
            raise ValueError(
                "achieved_currency must be an uppercase 3-letter ISO 4217 code, got "
                f"{self.achieved_currency!r}"
            )

        if self.originating_lead_id is not None:
            _require_kind(
                self.originating_lead_id, LeadId, "SaleOutcomeSnapshot.originating_lead_id"
            )
