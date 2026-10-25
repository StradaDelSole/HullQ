"""Broker periodic performance report subscription orchestration — SLICE-0089.

Thin application orchestration exposing
`hullq.persistence.broker_report_subscription` through the authenticated
Broker Workspace, reusing the exact accepted SLICE-0053 Organization
workspace/MFA boundary and the SLICE-0071 OWNER/ADMIN-only write-role
pattern (`hullq.application.lead_operations.set_notification_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.broker_report_subscription import ReportPeriodKind, SubscriptionStatus
from hullq.domain.lead_notification import normalize_notification_recipient_email
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId, MembershipRole
from hullq.persistence.broker_identity import fetch_membership_for_account_and_organization
from hullq.persistence.broker_report_subscription import (
    SubscriptionRecord,
    fetch_subscription,
    set_subscription,
)
from hullq.security.session_token import SessionClaims

__all__ = [
    "ReportSubscriptionOutcome",
    "ReportSubscriptionResultView",
    "get_report_subscription",
    "set_report_subscription",
]


class ReportSubscriptionOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    ROLE_REQUIRED = "ROLE_REQUIRED"
    INVALID_INPUT = "INVALID_INPUT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    OK = "OK"


@dataclass(frozen=True)
class ReportSubscriptionResultView:
    outcome: ReportSubscriptionOutcome
    config: SubscriptionRecord | None = None

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"status": self.outcome.value}
        if self.config is not None:
            body.update(self.config.to_public_dict())
        return body


def get_report_subscription(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> ReportSubscriptionResultView:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return ReportSubscriptionResultView(
            outcome=ReportSubscriptionOutcome.ORG_NOT_FOUND_OR_DENIED
        )
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.MFA_REQUIRED)
    config = fetch_subscription(conn, organization_id)
    return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.OK, config=config)


def set_report_subscription(
    conn: Any,
    session: SessionClaims,
    organization_id: MarketplaceOrganizationId,
    *,
    raw_status: Any,
    raw_period_kind: Any,
    raw_recipient_email: Any,
    expected_revision: int,
    as_of: datetime,
) -> ReportSubscriptionResultView:
    """Create/change the Organization's periodic report subscription.

    Only a current ACTIVE `OWNER` or `ADMIN` may call this (re-derived
    fresh from persistence, never from the session token). Activating
    (`status="ACTIVE"`) always requires a syntactically valid
    `recipient_email` -- "NO automatic opt-in or mass sending" together
    with a durable recipient is what makes a subscription deliverable at
    all; there is no `NO_RECIPIENT_CONFIGURED` dispatch state here (unlike
    SLICE-0071's Lead notifications) because this boundary simply refuses
    to activate without one.
    """
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return ReportSubscriptionResultView(
            outcome=ReportSubscriptionOutcome.ORG_NOT_FOUND_OR_DENIED
        )
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.MFA_REQUIRED)

    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    if membership is None or not (membership.roles & {MembershipRole.OWNER, MembershipRole.ADMIN}):
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.ROLE_REQUIRED)

    if not isinstance(raw_status, str):
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.INVALID_INPUT)
    try:
        status = SubscriptionStatus(raw_status)
    except ValueError:
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.INVALID_INPUT)

    if not isinstance(raw_period_kind, str):
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.INVALID_INPUT)
    try:
        period_kind = ReportPeriodKind(raw_period_kind)
    except ValueError:
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.INVALID_INPUT)

    if raw_recipient_email is None:
        recipient_email: str | None = None
    elif isinstance(raw_recipient_email, str):
        try:
            recipient_email = normalize_notification_recipient_email(raw_recipient_email)
        except TypeError, ValueError:
            return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.INVALID_INPUT)
    else:
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.INVALID_INPUT)

    if status is SubscriptionStatus.ACTIVE and recipient_email is None:
        return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.INVALID_INPUT)

    conn.commit()  # end the reads' implicit transaction before the write transaction below.
    result = set_subscription(
        conn,
        organization_id,
        status=status,
        period_kind=period_kind,
        recipient_email=recipient_email,
        updated_by_account_id=session.account_id,
        expected_revision=expected_revision,
        bootstrap_anchor_date=as_of.date(),
        bootstrap_initial_period_kind=period_kind,
    )
    if not result.updated:
        return ReportSubscriptionResultView(
            outcome=ReportSubscriptionOutcome.VERSION_CONFLICT, config=result.current
        )
    return ReportSubscriptionResultView(outcome=ReportSubscriptionOutcome.OK, config=result.current)
