"""Public listing telemetry vocabulary — SLICE-0075.

Implements `specs/BROKER_PERFORMANCE_FUNNEL_SNAPSHOT_CONTRACT.v0.1.md` §3/§5:
the one accepted v0.1 listing telemetry event kind (`PUBLIC_LISTING_VIEW`)
and its durable operation identity. A `PUBLIC_LISTING_VIEW` means HullQ
successfully served/read the current public listing surface for a concrete
NativeListing under the accepted public-eligibility boundary (contract §3) --
never a broker/private preview read, an authenticated broker edit read, a
suppressed/not-public read, a failed/404 read or an asset/image request.

Pure value objects only -- no persistence/network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["ListingTelemetryEventKind", "ListingViewOperationId"]


class ListingTelemetryEventKind(StrEnum):
    """Bounded listing telemetry vocabulary (contract §3 v0.1 minimum set).

    v0.1 supports exactly one event kind. If a later slice adds a separate
    exposure/impression fact, its semantics must be mechanically distinct
    from `PUBLIC_LISTING_VIEW` (contract §3) -- never silently merged into
    this same vocabulary member.
    """

    PUBLIC_LISTING_VIEW = "PUBLIC_LISTING_VIEW"


@dataclass(frozen=True)
class ListingViewOperationId:
    """Identifies one durable public-listing-view telemetry operation
    (contract §5). Server-minted per request -- never client-supplied --
    distinct from every other accepted marketplace identity kind, even when
    the underlying raw text collides."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ListingViewOperationId.value must be non-empty")
