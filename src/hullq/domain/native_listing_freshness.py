"""NativeListing freshness / reconfirmation vocabulary — SLICE-0052.

Implements `specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md` §§2-3: a
freshness state dimension that is runtime-distinct from the accepted
SLICE-0049 lifecycle vocabulary (`hullq.domain.native_listing_lifecycle`).

Hard invariants preserved by this module and its consumers:

    LifecycleState != FreshnessStatus
    STALE does not mutate lifecycle to WITHDRAWN
    STALE does not imply SOLD
    UNKNOWN does not imply withdrawn, sold or unavailable
    reconfirmation does not create a lifecycle transition

This module contains only pure, frozen value objects/policy evaluation — no
persistence, ORM or network access, and no wall-clock read: every evaluation
takes an explicit timezone-aware UTC `as_of` boundary (contract §8) so the
same persisted evidence can be evaluated deterministically at any instant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

__all__ = [
    "MANUAL_NATIVE_V1",
    "FreshnessConfirmationId",
    "FreshnessPolicy",
    "FreshnessStatus",
    "evaluate_freshness_status",
]


class FreshnessStatus(StrEnum):
    """The exactly four freshness states introduced by SLICE-0052.

    Never a lifecycle state, and never mapped to one: a STALE or UNKNOWN
    NativeListing remains lifecycle ACTIVE in durable state/history.
    """

    CONFIRMED = "CONFIRMED"
    DUE_FOR_CONFIRMATION = "DUE_FOR_CONFIRMATION"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FreshnessConfirmationId:
    """Identifies one immutable reconfirmation event.

    Not interchangeable with `PublicationTransitionId`, `NativeListingId` or
    any other accepted marketplace identity kind, even when the underlying
    raw text collides.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("FreshnessConfirmationId.value must be non-empty")


@dataclass(frozen=True)
class FreshnessPolicy:
    """One named, versioned freshness policy (contract §3).

    A later policy change is a versioned product-policy change: this
    dataclass is immutable, and existing named policy constants (such as
    `MANUAL_NATIVE_V1`) must never be mutated in place to silently change
    historical semantics — a policy change introduces a new named constant.
    """

    policy_id: str
    confirmation_ttl: timedelta
    grace_period: timedelta

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("FreshnessPolicy.policy_id must be non-empty")
        if self.confirmation_ttl <= timedelta(0):
            raise ValueError("FreshnessPolicy.confirmation_ttl must be positive")
        if self.grace_period <= timedelta(0):
            raise ValueError("FreshnessPolicy.grace_period must be positive")

    @property
    def stale_boundary(self) -> timedelta:
        """Total age at which a listing becomes STALE (TTL + grace)."""
        return self.confirmation_ttl + self.grace_period


#: The one production policy introduced by this contract (§3): exact 30-day
#: confirmation TTL plus a 7-day grace period, so the stale boundary is
#: exactly 37 days after the effective confirmation timestamp.
MANUAL_NATIVE_V1 = FreshnessPolicy(
    policy_id="MANUAL_NATIVE_V1",
    confirmation_ttl=timedelta(days=30),
    grace_period=timedelta(days=7),
)


def _require_timezone_aware(value: datetime, field_label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_label} must be a timezone-aware datetime, got {value!r}")


def evaluate_freshness_status(
    *,
    confirmed_at: datetime | None,
    as_of: datetime,
    policy: FreshnessPolicy = MANUAL_NATIVE_V1,
) -> FreshnessStatus:
    """Deterministically classify freshness from evidence + policy (contract §3).

    ```text
    confirmed_at <= as_of < confirmed_at + TTL           -> CONFIRMED
    confirmed_at + TTL <= as_of < confirmed_at + TTL+grace -> DUE_FOR_CONFIRMATION
    as_of >= confirmed_at + TTL+grace                     -> STALE
    confirmed_at is None                                  -> UNKNOWN
    confirmed_at > as_of                                  -> UNKNOWN (fail closed)
    ```

    *confirmed_at* is `None` when there is no admissible confirmation
    evidence at all — never manufactured or defaulted to "now" by a caller.
    A stored/effective confirmation timestamp later than *as_of* fails
    closed to UNKNOWN rather than manufacturing a negative age or treating
    future evidence as current confirmation (contract §3).

    Both *confirmed_at* (when not `None`) and *as_of* must be timezone-aware
    UTC datetimes; a naive datetime is a caller programming error, not a
    domain UNKNOWN, and raises `ValueError`.
    """
    _require_timezone_aware(as_of, "as_of")
    if confirmed_at is None:
        return FreshnessStatus.UNKNOWN
    _require_timezone_aware(confirmed_at, "confirmed_at")

    if confirmed_at > as_of:
        return FreshnessStatus.UNKNOWN

    age = as_of - confirmed_at
    if age < policy.confirmation_ttl:
        return FreshnessStatus.CONFIRMED
    if age < policy.stale_boundary:
        return FreshnessStatus.DUE_FOR_CONFIRMATION
    return FreshnessStatus.STALE
