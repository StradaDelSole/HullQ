"""Broker Workspace context read models — SLICE-0053.

Implements contract §9/§11/§12: the minimum protected read model FastAPI
serves to Astro. Every membership/role fact here is read fresh from current
HullQ persistence on every call -- never derived from the session token's
identity/MFA evidence alone -- so a revoked/changed membership takes effect
on the very next read (contract §D).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.domain.broker_access import (
    PRIVILEGED_MFA_ROLES,
    OrganizationAuthorizationReason,
    OrganizationAuthorizationStatus,
    evaluate_organization_workspace_authorization,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.persistence.broker_identity import (
    fetch_active_memberships_for_account,
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.security.session_token import SessionClaims

__all__ = [
    "BrokerContextReadModel",
    "OrganizationContextView",
    "OrganizationWorkspaceOutcome",
    "OrganizationWorkspaceResult",
    "get_broker_context_read_model",
    "get_organization_workspace_result",
]


@dataclass(frozen=True)
class OrganizationContextView:
    """One authorized Organization workspace context (contract §9/§11).

    `public_display_name` (SLICE-0063 contract §9) is current bounded
    presentation metadata only -- `organization_id` remains the exclusive
    authorization selector; a client's `public_display_name` is never
    accepted back as one.
    """

    organization_id: str
    professional_category: str
    publishing_eligibility: str
    public_display_name: str
    roles: tuple[str, ...]
    mfa_required: bool
    mfa_satisfied: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "professional_category": self.professional_category,
            "publishing_eligibility": self.publishing_eligibility,
            "public_display_name": self.public_display_name,
            "roles": list(self.roles),
            "mfa_required": self.mfa_required,
            "mfa_satisfied": self.mfa_satisfied,
        }


@dataclass(frozen=True)
class BrokerContextReadModel:
    account_id: str
    organizations: tuple[OrganizationContextView, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "organizations": [org.to_public_dict() for org in self.organizations],
        }


def get_broker_context_read_model(conn: Any, session: SessionClaims) -> BrokerContextReadModel:
    """List every ACTIVE Organization membership context for the current Account.

    An Account with zero ACTIVE memberships gets an empty list -- contract
    §11's "safe no-Organization-access state" -- never an error.
    """
    memberships = fetch_active_memberships_for_account(conn, session.account_id)
    views = []
    for membership in memberships:
        org = fetch_marketplace_organization(conn, membership.organization_id)
        if org is None:
            # A membership row referencing a since-deleted Organization is
            # not this read model's problem to repair; it is simply not
            # shown as an accessible context.
            continue
        privileged = bool(membership.roles & PRIVILEGED_MFA_ROLES)
        views.append(
            OrganizationContextView(
                organization_id=org.id.value,
                professional_category=org.professional_category.value,
                publishing_eligibility=org.publishing_eligibility.value,
                public_display_name=org.resolved_public_display_name,
                roles=tuple(sorted(role.value for role in membership.roles)),
                mfa_required=privileged,
                mfa_satisfied=session.identity.mfa_satisfied,
            )
        )
    return BrokerContextReadModel(account_id=session.account_id.value, organizations=tuple(views))


class OrganizationWorkspaceOutcome(StrEnum):
    """Mechanically distinct outcomes for one Organization workspace request.

    `NOT_FOUND_OR_DENIED` deliberately collapses "Organization does not
    exist" and "Organization exists but you have no/inactive membership"
    into one identical, non-enumerating outcome (contract §9/§E).
    """

    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


@dataclass(frozen=True)
class OrganizationWorkspaceResult:
    outcome: OrganizationWorkspaceOutcome
    context: OrganizationContextView | None = None

    def __post_init__(self) -> None:
        if self.outcome is OrganizationWorkspaceOutcome.AUTHORIZED and self.context is None:
            raise ValueError("An AUTHORIZED result must carry an OrganizationContextView")
        if self.outcome is not OrganizationWorkspaceOutcome.AUTHORIZED and self.context is not None:
            raise ValueError("Only an AUTHORIZED result may carry an OrganizationContextView")


def get_organization_workspace_result(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> OrganizationWorkspaceResult:
    """Evaluate one explicit Organization workspace request against current state.

    Reads current membership truth fresh (never trusts the session token's
    identity/MFA evidence to imply any Organization access on its own), then
    applies the pure `evaluate_organization_workspace_authorization` policy.
    """
    account_id: AccountId = session.account_id
    membership = fetch_membership_for_account_and_organization(conn, account_id, organization_id)
    decision = evaluate_organization_workspace_authorization(
        membership=membership, mfa_satisfied=session.identity.mfa_satisfied
    )

    if decision.status is OrganizationAuthorizationStatus.DENIED:
        if decision.reason is OrganizationAuthorizationReason.MFA_REQUIRED:
            return OrganizationWorkspaceResult(outcome=OrganizationWorkspaceOutcome.MFA_REQUIRED)
        return OrganizationWorkspaceResult(outcome=OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED)

    org = fetch_marketplace_organization(conn, organization_id)
    if org is None or membership is None:
        # Membership referenced an Organization that no longer exists --
        # collapse to the same non-enumerating outcome as no membership.
        return OrganizationWorkspaceResult(outcome=OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED)

    privileged = bool(membership.roles & PRIVILEGED_MFA_ROLES)
    context = OrganizationContextView(
        organization_id=org.id.value,
        professional_category=org.professional_category.value,
        publishing_eligibility=org.publishing_eligibility.value,
        public_display_name=org.resolved_public_display_name,
        roles=tuple(sorted(role.value for role in membership.roles)),
        mfa_required=privileged,
        mfa_satisfied=session.identity.mfa_satisfied,
    )
    return OrganizationWorkspaceResult(
        outcome=OrganizationWorkspaceOutcome.AUTHORIZED, context=context
    )
