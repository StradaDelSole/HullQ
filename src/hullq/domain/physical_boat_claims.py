"""PhysicalBoat buyer-critical claim value representation — SLICE-0050.

Typed runtime representation for exactly the seven `PHYSICAL_BOAT` registry
fields accepted by SLICE-0050 §4/§5
(`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` /
`specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`):

    physical_boat.marketed_brand_claim
    physical_boat.model_designation_claim
    physical_boat.build_year
    physical_boat.loa_length
    physical_boat.draft
    physical_boat.keel_configuration
    physical_boat.rudder_configuration

This module contains only pure, frozen value objects -- no persistence, ORM
or network access. It does not represent any other `PHYSICAL_BOAT` field and
does not implement a generic 38-field marketplace-fact framework: each
optional/conditional field gets its own small, statically-typed assertion
wrapper covering exactly the assertion kinds the accepted registry allows for
that field, so an omitted field (Python ``None``) remains mechanically
distinct from an explicit ``UNKNOWN`` assertion, and an invalid assertion-
kind/value pairing is rejected at construction time -- before any durable
write is attempted.

These claims are always broker-declared statements about the *concrete*
PhysicalBoat -- never a resolved BoatDesign/reference baseline value
(SLICE-0050 §12). This module has no knowledge of BoatDesign at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from hullq.domain.native_listing_offer import AssertionKind

__all__ = [
    "AssertionKind",
    "BuildYearClaim",
    "DraftClaim",
    "KeelConfiguration",
    "KeelConfigurationClaim",
    "LoaLengthClaim",
    "PhysicalBoatClaimRevisionId",
    "PhysicalBoatClaimSnapshot",
    "RudderConfiguration",
    "RudderConfigurationClaim",
]


def _require_kind(value: object, kind: type, field_label: str) -> None:
    """Fail closed when *value* is not an instance of the required *kind*.

    Mirrors the equivalent helper in `hullq.domain.market_identity`,
    `hullq.domain.publishing_eligibility` and
    `hullq.domain.native_listing_offer`: equal raw text/values across
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
# Identity kind -- runtime-distinct even when raw values collide
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhysicalBoatClaimRevisionId:
    """Identifies one immutable PhysicalBoat claim revision.

    Not interchangeable with PhysicalBoatId, NativeListingOfferRevisionId or
    any other accepted marketplace identity kind.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("PhysicalBoatClaimRevisionId.value must be non-empty")


# ---------------------------------------------------------------------------
# Explicit domain vocabularies -- never inferred from strings
# ---------------------------------------------------------------------------


class KeelConfiguration(StrEnum):
    """`physical_boat.keel_configuration` categorical values (registry v0.1)."""

    FIN = "FIN"
    FIN_WITH_BULB = "FIN_WITH_BULB"
    LONG_KEEL = "LONG_KEEL"
    WING = "WING"
    CENTERBOARD = "CENTERBOARD"
    LIFTING_KEEL = "LIFTING_KEEL"
    TWIN_KEEL = "TWIN_KEEL"
    OTHER = "OTHER"


class RudderConfiguration(StrEnum):
    """`physical_boat.rudder_configuration` categorical values (registry v0.1)."""

    SPADE = "SPADE"
    SKEG_HUNG = "SKEG_HUNG"
    TRANSOM_HUNG = "TRANSOM_HUNG"
    TWIN = "TWIN"
    OTHER = "OTHER"


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


_BUILD_YEAR_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})
_LOA_LENGTH_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})
_DRAFT_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})
_KEEL_CONFIGURATION_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})
_RUDDER_CONFIGURATION_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})


def _require_positive_finite_meters(value: Decimal, field_label: str) -> None:
    _require_kind(value, Decimal, field_label)
    if not value.is_finite():
        raise ValueError(f"{field_label} must be finite, got {value!r}")
    if value <= 0:
        raise ValueError(f"{field_label} must be a positive length in meters")


@dataclass(frozen=True)
class BuildYearClaim:
    """`physical_boat.build_year`: VALUE_ASSERTION(integer) or explicit UNKNOWN.

    Always present on a valid `PhysicalBoatClaimSnapshot` -- `build_year` is
    `REQUIRED_RESPONSE` (the broker must answer), but the answer may be
    explicit `UNKNOWN` rather than a guessed value.
    """

    assertion_kind: AssertionKind
    value: int | None = None

    def __post_init__(self) -> None:
        _validate_claim(self.assertion_kind, self.value, _BUILD_YEAR_ALLOWED, "BuildYearClaim")
        # bool is a subclass of int in Python; reject it explicitly so a
        # stray True/False can never masquerade as a calendar year.
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION and (
            isinstance(self.value, bool) or not isinstance(self.value, int)
        ):
            raise TypeError(f"BuildYearClaim.value must be an int, got {type(self.value).__name__}")


@dataclass(frozen=True)
class LoaLengthClaim:
    """`physical_boat.loa_length`: VALUE_ASSERTION(decimal SI meters) or explicit UNKNOWN.

    A `None` `PhysicalBoatClaimSnapshot.loa_length` (this whole wrapper
    omitted) is mechanically distinct from an explicit `UNKNOWN` assertion.
    """

    assertion_kind: AssertionKind
    value: Decimal | None = None

    def __post_init__(self) -> None:
        _validate_claim(self.assertion_kind, self.value, _LOA_LENGTH_ALLOWED, "LoaLengthClaim")
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            assert self.value is not None
            _require_positive_finite_meters(self.value, "LoaLengthClaim.value")


@dataclass(frozen=True)
class DraftClaim:
    """`physical_boat.draft`: VALUE_ASSERTION(decimal SI meters) or explicit UNKNOWN.

    A `None` `PhysicalBoatClaimSnapshot.draft` (this whole wrapper omitted)
    is mechanically distinct from an explicit `UNKNOWN` assertion.
    """

    assertion_kind: AssertionKind
    value: Decimal | None = None

    def __post_init__(self) -> None:
        _validate_claim(self.assertion_kind, self.value, _DRAFT_ALLOWED, "DraftClaim")
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            assert self.value is not None
            _require_positive_finite_meters(self.value, "DraftClaim.value")


@dataclass(frozen=True)
class KeelConfigurationClaim:
    """`physical_boat.keel_configuration`: VALUE_ASSERTION(KeelConfiguration) or explicit UNKNOWN."""

    assertion_kind: AssertionKind
    value: KeelConfiguration | None = None

    def __post_init__(self) -> None:
        _validate_claim(
            self.assertion_kind, self.value, _KEEL_CONFIGURATION_ALLOWED, "KeelConfigurationClaim"
        )
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            _require_kind(self.value, KeelConfiguration, "KeelConfigurationClaim.value")


@dataclass(frozen=True)
class RudderConfigurationClaim:
    """`physical_boat.rudder_configuration`: VALUE_ASSERTION(RudderConfiguration) or explicit UNKNOWN."""

    assertion_kind: AssertionKind
    value: RudderConfiguration | None = None

    def __post_init__(self) -> None:
        _validate_claim(
            self.assertion_kind,
            self.value,
            _RUDDER_CONFIGURATION_ALLOWED,
            "RudderConfigurationClaim",
        )
        if self.assertion_kind is AssertionKind.VALUE_ASSERTION:
            _require_kind(self.value, RudderConfiguration, "RudderConfigurationClaim.value")


# ---------------------------------------------------------------------------
# The bounded seven-field claim snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhysicalBoatClaimSnapshot:
    """One complete, internally-consistent PhysicalBoat claim snapshot.

    Bounded to exactly the seven accepted SLICE-0050 `PHYSICAL_BOAT` fields
    -- no builder, boat name, HIN/CIN, beam, displacement, hull material,
    rig, engine, cabin/berth/head or history/refit/survey field. Numeric
    values use `decimal.Decimal`, never a binary-floating-point type.
    """

    marketed_brand_claim: str
    model_designation_claim: str
    build_year: BuildYearClaim
    loa_length: LoaLengthClaim | None = None
    draft: DraftClaim | None = None
    keel_configuration: KeelConfigurationClaim | None = None
    rudder_configuration: RudderConfigurationClaim | None = None

    def __post_init__(self) -> None:
        _require_kind(
            self.marketed_brand_claim, str, "PhysicalBoatClaimSnapshot.marketed_brand_claim"
        )
        _require_non_blank(
            self.marketed_brand_claim, "PhysicalBoatClaimSnapshot.marketed_brand_claim"
        )
        _require_kind(
            self.model_designation_claim, str, "PhysicalBoatClaimSnapshot.model_designation_claim"
        )
        _require_non_blank(
            self.model_designation_claim, "PhysicalBoatClaimSnapshot.model_designation_claim"
        )
        _require_kind(self.build_year, BuildYearClaim, "PhysicalBoatClaimSnapshot.build_year")

        if self.loa_length is not None:
            _require_kind(self.loa_length, LoaLengthClaim, "PhysicalBoatClaimSnapshot.loa_length")
        if self.draft is not None:
            _require_kind(self.draft, DraftClaim, "PhysicalBoatClaimSnapshot.draft")
        if self.keel_configuration is not None:
            _require_kind(
                self.keel_configuration,
                KeelConfigurationClaim,
                "PhysicalBoatClaimSnapshot.keel_configuration",
            )
        if self.rudder_configuration is not None:
            _require_kind(
                self.rudder_configuration,
                RudderConfigurationClaim,
                "PhysicalBoatClaimSnapshot.rudder_configuration",
            )
