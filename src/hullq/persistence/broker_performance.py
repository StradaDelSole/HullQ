"""Broker performance / funnel snapshot aggregate read persistence — SLICE-0075.

Implements `specs/BROKER_PERFORMANCE_FUNNEL_SNAPSHOT_CONTRACT.v0.1.md`
§6/§7/§8: given one authorized Organization and one explicit bounded
`[window_start, window_end)` period, project the accepted funnel

    listing exposure/views -> Leads -> broker handling/contact attempt
    -> explicit SaleOutcome

as durable, reproducible facts (contract §2 truth rule 10) -- never a
re-derivation that could diverge from the underlying SLICE-0070/0071/0074
tables.

This module performs no tenancy/role authorization itself -- the caller
(`hullq.application.broker_performance_read`) must have already established
current authorized access to the exact Organization before calling anything
here. Every query here is scoped by an explicit `organization_id`; nothing
here ever aggregates or leaks across Organizations (contract §10).

Read-only: creates or mutates nothing.
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.lead_provenance import AcquisitionChannel
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.native_listing_view_event import fetch_organization_listing_view_counts

__all__ = [
    "ListingPerformanceFacts",
    "OrganizationPerformanceFacts",
    "fetch_organization_performance_facts",
]


@dataclass(frozen=True)
class ListingPerformanceFacts:
    """One listing's bounded factual snapshot within the requested window
    (contract §6). `sold_outcome_recorded_at`/`sold_outcome_source_known`
    reflect the listing's *current* SaleOutcome head regardless of window --
    an explicit close-out is lifetime truth, not a windowed event -- while
    every other field is scoped to `[window_start, window_end)`."""

    native_listing_id: str
    public_listing_views: int
    leads_received: int
    leads_contacted: int
    leads_closed: int
    first_contact_latency_known_count: int
    first_contact_latency_unknown_count: int
    sold_outcome_recorded_at: str | None
    sold_outcome_source_known: bool | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "native_listing_id": self.native_listing_id,
            "public_listing_views": self.public_listing_views,
            "leads_received": self.leads_received,
            "leads_contacted": self.leads_contacted,
            "leads_closed": self.leads_closed,
            "first_contact_latency_known_count": self.first_contact_latency_known_count,
            "first_contact_latency_unknown_count": self.first_contact_latency_unknown_count,
            "sold_outcome_recorded_at": self.sold_outcome_recorded_at,
            "sold_outcome_source_known": self.sold_outcome_source_known,
        }


@dataclass(frozen=True)
class OrganizationPerformanceFacts:
    """The bounded Organization-scoped summary over `[window_start,
    window_end)` (contract §6) plus the per-listing breakdown for every
    listing with at least one observed view, Lead or current SaleOutcome.

    `median_first_contact_latency_seconds` is `None` exactly when
    `first_contact_latency_known_count == 0` -- a derived statistic, always
    reported alongside its own supporting population count (contract §6:
    "Do not label derived ratios as facts without exposing numerator/
    denominator population"), never silently defaulted to zero.
    """

    window_start: datetime
    window_end: datetime
    public_listing_views: int
    leads_received: int
    leads_contacted: int
    leads_closed: int
    sold_outcomes: int
    sold_outcomes_with_known_source: int
    sold_outcomes_with_unknown_source: int
    acquisition_source_breakdown: dict[str, int]
    first_contact_latency_known_count: int
    first_contact_latency_unknown_count: int
    median_first_contact_latency_seconds: float | None
    listings: tuple[ListingPerformanceFacts, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "public_listing_views": self.public_listing_views,
            "leads_received": self.leads_received,
            "leads_contacted": self.leads_contacted,
            "leads_closed": self.leads_closed,
            "sold_outcomes": self.sold_outcomes,
            "sold_outcomes_with_known_source": self.sold_outcomes_with_known_source,
            "sold_outcomes_with_unknown_source": self.sold_outcomes_with_unknown_source,
            "acquisition_source_breakdown": dict(self.acquisition_source_breakdown),
            "first_contact_latency_known_count": self.first_contact_latency_known_count,
            "first_contact_latency_unknown_count": self.first_contact_latency_unknown_count,
            "median_first_contact_latency_seconds": self.median_first_contact_latency_seconds,
            "listings": [listing.to_public_dict() for listing in self.listings],
        }


_SELECT_ORG_LEADS_IN_WINDOW = """
SELECT bl.lead_id, bl.native_listing_id, bl.received_at,
       COALESCE(los.operational_status, 'NEW') AS operational_status,
       fc.first_contact_attempt_at,
       COALESCE(lap.acquisition_channel, 'UNKNOWN') AS acquisition_channel
FROM buyer_leads bl
LEFT JOIN lead_operational_state los ON los.lead_id = bl.lead_id
LEFT JOIN lead_acquisition_provenance lap ON lap.lead_id = bl.lead_id
LEFT JOIN (
    SELECT lead_id, MIN(occurred_at) AS first_contact_attempt_at
    FROM lead_timeline_events
    WHERE event_type = 'CONTACT_ATTEMPT'
    GROUP BY lead_id
) fc ON fc.lead_id = bl.lead_id
WHERE bl.publishing_organization_id = %(organization_id)s
  AND bl.received_at >= %(window_start)s AND bl.received_at < %(window_end)s
"""

_SELECT_ORG_CURRENT_SALE_OUTCOMES = """
SELECT h.native_listing_id, r.originating_lead_id, r.recorded_at
FROM native_listing_sale_outcome_heads h
JOIN native_listing_sale_outcome_revisions r
    ON r.sale_outcome_revision_id = h.current_sale_outcome_revision_id
WHERE r.publishing_organization_id = %(organization_id)s AND r.outcome_kind = 'SOLD'
"""


@dataclass(frozen=True)
class _LeadRow:
    lead_id: str
    native_listing_id: str
    received_at: datetime
    operational_status: str
    first_contact_attempt_at: datetime | None
    acquisition_channel: str


@dataclass(frozen=True)
class _SoldOutcomeRow:
    native_listing_id: str
    originating_lead_id: str | None
    recorded_at: datetime


def _fetch_org_leads_in_window(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    window_start: datetime,
    window_end: datetime,
) -> list[_LeadRow]:
    with conn.cursor() as cur:
        cur.execute(
            _SELECT_ORG_LEADS_IN_WINDOW,
            {
                "organization_id": organization_id.value,
                "window_start": window_start,
                "window_end": window_end,
            },
        )
        rows = cur.fetchall()
    return [
        _LeadRow(
            lead_id=row[0],
            native_listing_id=row[1],
            received_at=row[2],
            operational_status=row[3],
            first_contact_attempt_at=row[4],
            acquisition_channel=row[5],
        )
        for row in rows
    ]


def _fetch_org_current_sold_outcomes(
    conn: Any, organization_id: MarketplaceOrganizationId
) -> list[_SoldOutcomeRow]:
    with conn.cursor() as cur:
        cur.execute(_SELECT_ORG_CURRENT_SALE_OUTCOMES, {"organization_id": organization_id.value})
        rows = cur.fetchall()
    return [
        _SoldOutcomeRow(native_listing_id=row[0], originating_lead_id=row[1], recorded_at=row[2])
        for row in rows
    ]


def _latency_seconds(lead: _LeadRow) -> float | None:
    if lead.first_contact_attempt_at is None:
        return None
    return (lead.first_contact_attempt_at - lead.received_at).total_seconds()


def fetch_organization_performance_facts(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    window_start: datetime,
    window_end: datetime,
) -> OrganizationPerformanceFacts:
    """Compute the bounded Organization-scoped performance snapshot (contract
    §6) over `[window_start, window_end)`.

    The caller must already have verified current authorized access to
    *organization_id* -- this function never checks tenancy/role itself and
    never aggregates across a second Organization."""
    leads = _fetch_org_leads_in_window(
        conn, organization_id, window_start=window_start, window_end=window_end
    )
    sold_outcomes = _fetch_org_current_sold_outcomes(conn, organization_id)
    view_counts = fetch_organization_listing_view_counts(
        conn, organization_id, window_start=window_start, window_end=window_end
    )

    leads_by_listing: dict[str, list[_LeadRow]] = {}
    for lead in leads:
        leads_by_listing.setdefault(lead.native_listing_id, []).append(lead)

    sold_by_listing: dict[str, _SoldOutcomeRow] = {
        row.native_listing_id: row for row in sold_outcomes
    }

    all_listing_ids = set(view_counts) | set(leads_by_listing) | set(sold_by_listing)

    listings: list[ListingPerformanceFacts] = []
    for native_listing_id in sorted(all_listing_ids):
        listing_leads = leads_by_listing.get(native_listing_id, [])
        latencies = [
            latency
            for lead in listing_leads
            if (latency := _latency_seconds(lead)) is not None
        ]
        sold_row = sold_by_listing.get(native_listing_id)
        listings.append(
            ListingPerformanceFacts(
                native_listing_id=native_listing_id,
                public_listing_views=view_counts.get(native_listing_id, 0),
                leads_received=len(listing_leads),
                leads_contacted=sum(
                    1 for lead in listing_leads if lead.first_contact_attempt_at is not None
                ),
                leads_closed=sum(
                    1 for lead in listing_leads if lead.operational_status == "CLOSED"
                ),
                first_contact_latency_known_count=len(latencies),
                first_contact_latency_unknown_count=len(listing_leads) - len(latencies),
                sold_outcome_recorded_at=(
                    sold_row.recorded_at.isoformat() if sold_row is not None else None
                ),
                sold_outcome_source_known=(
                    sold_row.originating_lead_id is not None if sold_row is not None else None
                ),
            )
        )

    all_latencies = [
        latency for lead in leads if (latency := _latency_seconds(lead)) is not None
    ]
    source_breakdown = Counter(lead.acquisition_channel for lead in leads)
    for channel in AcquisitionChannel:
        source_breakdown.setdefault(channel.value, 0)

    windowed_sold = [row for row in sold_outcomes if window_start <= row.recorded_at < window_end]

    return OrganizationPerformanceFacts(
        window_start=window_start,
        window_end=window_end,
        public_listing_views=sum(view_counts.values()),
        leads_received=len(leads),
        leads_contacted=sum(1 for lead in leads if lead.first_contact_attempt_at is not None),
        leads_closed=sum(1 for lead in leads if lead.operational_status == "CLOSED"),
        sold_outcomes=len(windowed_sold),
        sold_outcomes_with_known_source=sum(
            1 for row in windowed_sold if row.originating_lead_id is not None
        ),
        sold_outcomes_with_unknown_source=sum(
            1 for row in windowed_sold if row.originating_lead_id is None
        ),
        acquisition_source_breakdown=dict(source_breakdown),
        first_contact_latency_known_count=len(all_latencies),
        first_contact_latency_unknown_count=len(leads) - len(all_latencies),
        median_first_contact_latency_seconds=(
            statistics.median(all_latencies) if all_latencies else None
        ),
        listings=tuple(listings),
    )
