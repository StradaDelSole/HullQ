"""NativeListing freshness resolution / current-market predicate — SLICE-0052.

The one production application entry point combining immutable persisted
evidence (`hullq.persistence.native_listing_freshness`) with the pure
`MANUAL_NATIVE_V1` policy (`hullq.domain.native_listing_freshness`) into one
deterministic current-freshness read, plus the shared current-market
eligibility predicate (contract §7) consumed identically by the public
listing read model and the native-inventory Search candidate path so the two
surfaces can never silently diverge on what counts as "current".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import (
    MANUAL_NATIVE_V1,
    FreshnessStatus,
    evaluate_freshness_status,
)
from hullq.persistence.native_listing_freshness import fetch_effective_confirmed_at

__all__ = ["CurrentFreshness", "is_current_market_eligible", "resolve_current_freshness"]

#: Contract §7: buyer surfaces admit exactly these two freshness statuses as
#: current-market eligible. STALE/UNKNOWN are always suppressed.
_CURRENT_MARKET_ELIGIBLE_STATUSES = frozenset(
    {FreshnessStatus.CONFIRMED, FreshnessStatus.DUE_FOR_CONFIRMATION}
)


@dataclass(frozen=True, slots=True)
class CurrentFreshness:
    """One deterministic freshness read: the classified status plus its evidence."""

    status: FreshnessStatus
    last_confirmed_at: datetime | None


def resolve_current_freshness(
    conn: Any, native_listing_id: NativeListingId, *, as_of: datetime
) -> CurrentFreshness:
    """Resolve *native_listing_id*'s current freshness at the explicit *as_of* boundary.

    Always evaluated under `MANUAL_NATIVE_V1` (contract §3): a later policy
    would be a versioned product-policy change, not a parameter of this call.
    """
    confirmed_at = fetch_effective_confirmed_at(conn, native_listing_id)
    status = evaluate_freshness_status(
        confirmed_at=confirmed_at, as_of=as_of, policy=MANUAL_NATIVE_V1
    )
    return CurrentFreshness(status=status, last_confirmed_at=confirmed_at)


def is_current_market_eligible(status: FreshnessStatus) -> bool:
    """Contract §7: only CONFIRMED/DUE_FOR_CONFIRMATION may remain on current buyer surfaces."""
    return status in _CURRENT_MARKET_ELIGIBLE_STATUSES
