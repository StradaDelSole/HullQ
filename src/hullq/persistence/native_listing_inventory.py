"""Durable Organization-scoped NativeListing inventory read — SLICE-0060.

Implements `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md` §3/§9:
a bounded, deterministically ordered, keyset-paginated projection over the
existing `native_listings` table, filtered to the exact caller-supplied
`publishing_organization_id`.

This module performs no authorization: the caller (the application layer)
must have already established that the requesting Account is currently
authorized for *organization_id* before calling here. `organization_id` is
always the exact equality filter on every query -- independent of any
caller-supplied cursor -- so a listing belonging to another Organization can
never be observed through this read regardless of cursor content.

Ordering is fixed: `created_at DESC, native_listing_id ASC` (contract §9).
Because the primary key sorts descending while the tie-break sorts
ascending, continuation cannot use a simple tuple comparison and instead
uses the explicit two-branch predicate in `_SELECT_NEXT_PAGE` below.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId

__all__ = [
    "InventoryListingRow",
    "InventorySortKey",
    "fetch_organization_inventory_page",
]


@dataclass(frozen=True)
class InventorySortKey:
    """The exact deterministic keyset continuation position (contract §9)."""

    created_at: datetime
    native_listing_id: NativeListingId


@dataclass(frozen=True)
class InventoryListingRow:
    """One exact, factual `native_listings` row -- no offer/freshness/public
    fact is resolved here; those remain the application layer's job so this
    module never duplicates another accepted truth model."""

    native_listing_id: NativeListingId
    lifecycle_state: NativeListingLifecycleState
    broker_listing_reference: str | None
    created_at: datetime


_SELECT_FIRST_PAGE = """
SELECT native_listing_id, lifecycle_state, broker_listing_reference, created_at
FROM native_listings
WHERE publishing_organization_id = %s
ORDER BY created_at DESC, native_listing_id ASC
LIMIT %s
"""

# created_at sorts DESC while native_listing_id tie-breaks ASC, so a plain
# tuple comparison cannot express "strictly after the last accepted sort
# key" -- this explicit two-branch predicate does: either a strictly
# earlier created_at, or the identical created_at with a strictly greater
# native_listing_id.
_SELECT_NEXT_PAGE = """
SELECT native_listing_id, lifecycle_state, broker_listing_reference, created_at
FROM native_listings
WHERE publishing_organization_id = %s
  AND (created_at < %s OR (created_at = %s AND native_listing_id > %s))
ORDER BY created_at DESC, native_listing_id ASC
LIMIT %s
"""


def fetch_organization_inventory_page(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    limit: int,
    after: InventorySortKey | None,
) -> list[InventoryListingRow]:
    """Fetch up to *limit* rows owned by *organization_id*, deterministically
    ordered `created_at DESC, native_listing_id ASC`, continuing strictly
    after *after* when supplied.

    Never loads unbounded Organization inventory: *limit* always bounds this
    single query, and no total-count query is issued (contract §9).
    """
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            f"organization_id must be a MarketplaceOrganizationId, got {type(organization_id).__name__}"
        )
    if after is not None and not isinstance(after, InventorySortKey):
        raise TypeError(f"after must be an InventorySortKey or None, got {type(after).__name__}")
    if limit <= 0:
        raise ValueError("limit must be positive")

    with conn.cursor() as cur:
        if after is None:
            cur.execute(_SELECT_FIRST_PAGE, [organization_id.value, limit])
        else:
            cur.execute(
                _SELECT_NEXT_PAGE,
                [
                    organization_id.value,
                    after.created_at,
                    after.created_at,
                    after.native_listing_id.value,
                    limit,
                ],
            )
        rows = cur.fetchall()

    return [
        InventoryListingRow(
            native_listing_id=NativeListingId(row[0]),
            lifecycle_state=NativeListingLifecycleState(row[1]),
            broker_listing_reference=row[2],
            created_at=row[3],
        )
        for row in rows
    ]
