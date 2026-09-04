"""NativeListing offer-facts value representation — SLICE-0045.

Typed runtime representation for exactly the nine `LISTING_OFFER` fields
accepted by `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` /
`specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`:

    listing_offer.asking_price_mode
    listing_offer.asking_price_amount
    listing_offer.currency
    listing_offer.location_country
    listing_offer.location_region
    listing_offer.broker_summary
    listing_offer.broker_description
    listing_offer.known_history_narrative
    listing_offer.vat_tax_status_claim

This module contains only pure, frozen value objects — no persistence, ORM or
network access. It does not represent any `PHYSICAL_BOAT` field and does not
implement generic marketplace-fact/claim-resolution machinery: each optional/
conditional field gets its own small, statically-typed assertion wrapper
covering exactly the assertion kinds the accepted registry allows for that
field, so an omitted field (Python ``None``) remains mechanically distinct
from an explicit ``UNKNOWN``/``NOT_APPLICABLE``/``NO_KNOWN_HISTORY_DECLARED``
assertion, and an invalid assertion-kind/value pairing is rejected at
construction time — before any durable write is attempted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

__all__ = [
    "AskingPriceMode",
    "AssertionKind",
    "BrokerSummaryClaim",
    "KnownHistoryNarrativeClaim",
    "LocationRegionClaim",
    "NativeListingOfferRevisionId",
    "NativeListingOfferSnapshot",
    "VatTaxStatusClaim",
    "VatTaxStatusValue",
]

_CURRENCY_CODE_RE = re.compile(r"^[A-Z]{3}$")
_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")


def _require_kind(value: object, kind: type, field_label: str) -> None:
    """Fail closed when *value* is not an instance of the required *kind*.

    Mirrors the equivalent helper in `hullq.domain.publishing_eligibility`
    and `hullq.domain.market_identity`: equal raw text/values across
    different identity/claim kinds must not be accepted as interchangeable,
    and this check runs at construction time, not only under static
    type-checking.
    """
    if not isinstance(value, kind):
        raise TypeError(f"{field_label} must be a {kind.__name__}, got {type(value).__name__}")


def _require_non_blank(value: str, field_label: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_label} must be a non-empty, non-whitespace-only string")


# ---------------------------------------------------------------------------
# Identity kind — runtime-distinct even when raw values collide
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NativeListingOfferRevisionId:
    """Identifies one immutable NativeListing offer revision.

    Not interchangeable with NativeListingId, MarketEpisodeId, PhysicalBoatId
    or any other accepted marketplace identity kind.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("NativeListingOfferRevisionId.value must be non-empty")


# ---------------------------------------------------------------------------
# Explicit domain vocabularies — never inferred from strings
# ---------------------------------------------------------------------------


class AskingPriceMode(StrEnum):
    """`listing_offer.asking_price_mode` — the only two accepted v0.1 values."""

    AMOUNT = "AMOUNT"
    POA = "POA"


class VatTaxStatusValue(StrEnum):
    """`listing_offer.vat_tax_status_claim` categorical values.

    A stored value here is always a broker claim, never a HullQ legal
    verification (`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` §
    `listing_offer.vat_tax_status_claim`).
    """

    VAT_PAID = "VAT_PAID"
    VAT_NOT_PAID = "VAT_NOT_PAID"
    VAT_MARGIN_SCHEME = "VAT_MARGIN_SCHEME"
    OTHER = "OTHER"


class AssertionKind(StrEnum):
    """Assertion kinds used by the four optional/conditional offer fields.

    `PRESENT`/`ABSENT` are not used by any v0.1 `LISTING_OFFER` field and are
    therefore intentionally not represented here (this module has no
    generic assertion-kind list shared across the full 38-field registry;
    that generic representation is explicitly out of scope for this slice).
    """

    VALUE_ASSERTION = "VALUE_ASSERTION"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_KNOWN_HISTORY_DECLARED = "NO_KNOWN_HISTORY_DECLARED"


def _validate_claim(
    assertion_kind: AssertionKind,
    value: object,
    allowed_kinds: frozenset[AssertionKind],
    label: str,
) -> None:
    _require_kind(assertion_kind, AssertionKind, f"{label}.assertion_kind")
    if assertion_kind not in allowed_kinds:
        allowed = sorted(k.value for k in allowed_kinds)
        raise ValueError(
            f"{label}.assertion_kind must be one of {allowed}, got {assertion_kind.value!r}"
        )
    if assertion_kind is AssertionKind.VALUE_ASSERTION:
        if value is None:
            raise ValueError(f"{label}.value is required when assertion_kind is VALUE_ASSERTION")
    elif value is not None:
        raise ValueError(
            f"{label}.value must be None when assertion_kind is {assertion_kind.value}"
        )


# ---------------------------------------------------------------------------
# Per-field assertion wrappers — omission (Python None) stays distinct from
# an explicit UNKNOWN/NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED assertion.
# ---------------------------------------------------------------------------

_LOCATION_REGION_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})
_BROKER_SUMMARY_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.NOT_APPLICABLE})
_KNOWN_HISTORY_NARRATIVE_ALLOWED = frozenset(
    {
        AssertionKind.VALUE_ASSERTION,
        AssertionKind.NO_KNOWN_HISTORY_DECLARED,
        AssertionKind.UNKNOWN,
    }
)
_VAT_TAX_STATUS_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})


@dataclass(frozen=True)
class LocationRegionClaim:
    """`listing_offer.location_region`: VALUE_ASSERTION(text) or explicit UNKNOWN."""

    assertion_kind: AssertionKind
    value: str | None = None

    def __post_init__(self) -> None:
        _validate_claim(
            self.assertion_kind, self.value, _LOCATION_REGION_ALLOWED, "LocationRegionClaim"
        )
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            assert self.value is not None
            _require_non_blank(self.value, "LocationRegionClaim.value")


@dataclass(frozen=True)
class BrokerSummaryClaim:
    """`listing_offer.broker_summary`: VALUE_ASSERTION(text) or explicit NOT_APPLICABLE."""

    assertion_kind: AssertionKind
    value: str | None = None

    def __post_init__(self) -> None:
        _validate_claim(
            self.assertion_kind, self.value, _BROKER_SUMMARY_ALLOWED, "BrokerSummaryClaim"
        )
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            assert self.value is not None
            _require_non_blank(self.value, "BrokerSummaryClaim.value")


@dataclass(frozen=True)
class KnownHistoryNarrativeClaim:
    """`listing_offer.known_history_narrative`: VALUE_ASSERTION(text),
    NO_KNOWN_HISTORY_DECLARED or explicit UNKNOWN.

    `NO_KNOWN_HISTORY_DECLARED` means the claimant declares no relevant
    history known to them; it is never proof no such history exists
    (`specs/MARKETPLACE_FACT_CONTRACT.v0.1.md` §3.2).
    """

    assertion_kind: AssertionKind
    value: str | None = None

    def __post_init__(self) -> None:
        _validate_claim(
            self.assertion_kind,
            self.value,
            _KNOWN_HISTORY_NARRATIVE_ALLOWED,
            "KnownHistoryNarrativeClaim",
        )
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            assert self.value is not None
            _require_non_blank(self.value, "KnownHistoryNarrativeClaim.value")


@dataclass(frozen=True)
class VatTaxStatusClaim:
    """`listing_offer.vat_tax_status_claim`: VALUE_ASSERTION(VatTaxStatusValue) or UNKNOWN.

    `SENSITIVE` + `DISPLAY_ONLY` in v0.1: this remains an unverified broker
    claim. This slice does not introduce `verified=true`, tax certification
    or searchable VAT filtering; the writer Account / publishing Organization
    / recorded timestamp attribution required by
    `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md` §7 is carried by the containing
    persisted revision, not by this value object.
    """

    assertion_kind: AssertionKind
    value: VatTaxStatusValue | None = None

    def __post_init__(self) -> None:
        _validate_claim(
            self.assertion_kind, self.value, _VAT_TAX_STATUS_ALLOWED, "VatTaxStatusClaim"
        )
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            _require_kind(self.value, VatTaxStatusValue, "VatTaxStatusClaim.value")


# ---------------------------------------------------------------------------
# The bounded nine-field offer snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NativeListingOfferSnapshot:
    """One complete, internally-consistent NativeListing offer snapshot.

    Bounded to exactly the nine accepted `LISTING_OFFER` fields — no
    convenience yacht spec, lifecycle, freshness or contact data. Price
    AMOUNT/POA conditionality (`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
    § `listing_offer.asking_price_mode`) and normalized country/currency
    code shape are mechanically enforced here, before any durable write is
    attempted. Money is represented as `decimal.Decimal`, never a
    binary-floating-point type.
    """

    asking_price_mode: AskingPriceMode
    location_country: str
    broker_description: str
    asking_price_amount: Decimal | None = None
    currency: str | None = None
    location_region: LocationRegionClaim | None = None
    broker_summary: BrokerSummaryClaim | None = None
    known_history_narrative: KnownHistoryNarrativeClaim | None = None
    vat_tax_status_claim: VatTaxStatusClaim | None = None

    def __post_init__(self) -> None:
        _require_kind(
            self.asking_price_mode, AskingPriceMode, "NativeListingOfferSnapshot.asking_price_mode"
        )

        if self.asking_price_mode is AskingPriceMode.AMOUNT:
            if self.asking_price_amount is None:
                raise ValueError("asking_price_amount is required when asking_price_mode is AMOUNT")
            if self.currency is None:
                raise ValueError("currency is required when asking_price_mode is AMOUNT")
            _require_kind(
                self.asking_price_amount, Decimal, "NativeListingOfferSnapshot.asking_price_amount"
            )
            if self.asking_price_amount <= 0:
                raise ValueError("asking_price_amount must be a positive amount")
        else:  # POA
            if self.asking_price_amount is not None:
                raise ValueError(
                    "asking_price_amount must not be populated (no synthetic price) when "
                    "asking_price_mode is POA"
                )
            if self.currency is not None:
                raise ValueError("currency must not be populated when asking_price_mode is POA")

        if self.currency is not None and not _CURRENCY_CODE_RE.fullmatch(self.currency):
            raise ValueError(
                f"currency must be an uppercase 3-letter ISO 4217 code, got {self.currency!r}"
            )

        _require_kind(self.location_country, str, "NativeListingOfferSnapshot.location_country")
        if not _COUNTRY_CODE_RE.fullmatch(self.location_country):
            raise ValueError(
                "location_country must be an uppercase 2-letter ISO 3166-1 alpha-2 code, got "
                f"{self.location_country!r}"
            )

        _require_non_blank(self.broker_description, "NativeListingOfferSnapshot.broker_description")

        if self.location_region is not None:
            _require_kind(
                self.location_region,
                LocationRegionClaim,
                "NativeListingOfferSnapshot.location_region",
            )
        if self.broker_summary is not None:
            _require_kind(
                self.broker_summary, BrokerSummaryClaim, "NativeListingOfferSnapshot.broker_summary"
            )
        if self.known_history_narrative is not None:
            _require_kind(
                self.known_history_narrative,
                KnownHistoryNarrativeClaim,
                "NativeListingOfferSnapshot.known_history_narrative",
            )
        if self.vat_tax_status_claim is not None:
            _require_kind(
                self.vat_tax_status_claim,
                VatTaxStatusClaim,
                "NativeListingOfferSnapshot.vat_tax_status_claim",
            )
