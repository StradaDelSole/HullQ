"""Broker-facing performance / funnel snapshot orchestration — SLICE-0075.

Implements `specs/BROKER_PERFORMANCE_FUNNEL_SNAPSHOT_CONTRACT.v0.1.md`:
thin application orchestration exposing the durable
`hullq.persistence.broker_performance.fetch_organization_performance_facts`
projection through the authenticated Broker Workspace, for the current
session's authorized MarketplaceOrganization and one explicit bounded time
window (contract §9).

Authorization reuses the exact accepted SLICE-0053 Organization workspace/MFA
boundary (`hullq.application.broker_workspace_read.get_organization_workspace_result`)
-- mirrors every other broker-read boundary's identical pattern
(`hullq.application.broker_inventory_read`,
`hullq.application.broker_sale_outcome`). This module never pre-decides
authorization itself, and never aggregates or leaks facts across a second
Organization (contract §10).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.broker_performance import (
    OrganizationPerformanceFacts,
    fetch_organization_performance_facts,
)
from hullq.security.session_token import SessionClaims

__all__ = [
    "DEFAULT_PERFORMANCE_WINDOW",
    "PerformanceReadOutcome",
    "PerformanceReadResult",
    "PerformanceWindow",
    "get_organization_performance_snapshot",
]

#: Contract §9: "the browser surface may support one bounded default window
#: plus a small bounded set of alternatives ... arbitrary unbounded
#: analytical queries are not required." An implementation-local, exhaustive,
#: bounded preset set -- never an arbitrary caller-supplied date range.
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class PerformanceWindow(StrEnum):
    LAST_7_DAYS = "LAST_7_DAYS"
    LAST_30_DAYS = "LAST_30_DAYS"
    LAST_90_DAYS = "LAST_90_DAYS"
    ALL_TIME = "ALL_TIME"


DEFAULT_PERFORMANCE_WINDOW = PerformanceWindow.LAST_30_DAYS

_WINDOW_DAYS = {
    PerformanceWindow.LAST_7_DAYS: 7,
    PerformanceWindow.LAST_30_DAYS: 30,
    PerformanceWindow.LAST_90_DAYS: 90,
}


def resolve_window_bounds(window: PerformanceWindow, *, as_of: datetime) -> tuple[datetime, datetime]:
    """Resolve *window* to an explicit, deterministic `[start, end)` pair
    anchored at *as_of* (contract §9: "All period boundaries must be
    explicit and deterministic"). `ALL_TIME`'s lower bound is a fixed epoch
    well before any HullQ data can exist -- never an unbounded `NULL`
    comparison."""
    if window is PerformanceWindow.ALL_TIME:
        return _EPOCH, as_of
    days = _WINDOW_DAYS[window]
    return as_of - timedelta(days=days), as_of


class PerformanceReadOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    INVALID_WINDOW = "INVALID_WINDOW"
    OK = "OK"


@dataclass(frozen=True)
class PerformanceReadResult:
    outcome: PerformanceReadOutcome
    window: PerformanceWindow | None = None
    facts: OrganizationPerformanceFacts | None = None

    def __post_init__(self) -> None:
        if self.outcome is PerformanceReadOutcome.OK:
            if self.window is None or self.facts is None:
                raise ValueError("An OK performance read result must carry window and facts")
        elif self.window is not None or self.facts is not None:
            raise ValueError("Only an OK performance read result may carry window/facts")

    def to_public_dict(self) -> dict[str, Any]:
        assert self.window is not None
        assert self.facts is not None
        body = self.facts.to_public_dict()
        body["window"] = self.window.value
        return body


def get_organization_performance_snapshot(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    *,
    raw_window: str | None,
    as_of: datetime,
) -> PerformanceReadResult:
    """Evaluate current Organization workspace authorization, then project
    the bounded performance snapshot for *raw_window* (or the accepted
    default when absent)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return PerformanceReadResult(outcome=PerformanceReadOutcome.ORG_NOT_FOUND_OR_DENIED)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return PerformanceReadResult(outcome=PerformanceReadOutcome.MFA_REQUIRED)

    if raw_window is None:
        window = DEFAULT_PERFORMANCE_WINDOW
    else:
        try:
            window = PerformanceWindow(raw_window)
        except ValueError:
            return PerformanceReadResult(outcome=PerformanceReadOutcome.INVALID_WINDOW)

    window_start, window_end = resolve_window_bounds(window, as_of=as_of)
    facts = fetch_organization_performance_facts(
        conn, organization_id, window_start=window_start, window_end=window_end
    )
    return PerformanceReadResult(outcome=PerformanceReadOutcome.OK, window=window, facts=facts)
