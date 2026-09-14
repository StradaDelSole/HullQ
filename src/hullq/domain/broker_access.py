"""Authenticated Broker Workspace access boundary — SLICE-0053.

Implements the pure decision core of
`specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md` §2/§9/§10: the hard
conceptual separation between provider *authentication*, HullQ *identity*,
HullQ *membership* and HullQ *authorization*.

`AuthenticatedIdentity` is the provider-neutral evidence produced by a
validated Auth0 (or, in tests, a deterministic local) OIDC authentication --
never a HullQ authorization grant by itself. `evaluate_organization_workspace
_authorization` is the single deterministic authorization decision: given
current HullQ membership truth for one explicit Organization and the
validated MFA evidence carried by the authenticated identity, decide whether
that Organization's workspace context may be entered. It never searches
across unrelated memberships and never treats a provider role/claim as
HullQ authorization truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, StrEnum

from hullq.domain.publishing_eligibility import (
    MembershipRole,
    MembershipState,
    OrganizationMembership,
)

__all__ = [
    "PRIVILEGED_MFA_ROLES",
    "AuthenticatedIdentity",
    "OrganizationAuthorizationDecision",
    "OrganizationAuthorizationReason",
    "OrganizationAuthorizationStatus",
    "Provider",
    "evaluate_organization_workspace_authorization",
]


class Provider(StrEnum):
    """Accepted external identity providers.

    Only `AUTH0` is admitted (contract §4.1): a raw string provider label
    from client input is never trusted as a member of this vocabulary.
    """

    AUTH0 = "auth0"


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Provider-neutral, validated authentication evidence.

    This is authentication evidence only -- it proves the configured
    provider authenticated this exact `(provider, issuer, subject)` at
    `auth_time` with (or without) MFA. It carries no HullQ Account,
    Organization, membership or role. Email is deliberately absent: this
    boundary must never be capable of using email as an identity key.
    """

    provider: Provider
    issuer: str
    subject: str
    auth_time: datetime | None
    mfa_satisfied: bool

    def __post_init__(self) -> None:
        if not isinstance(self.provider, Provider):
            raise TypeError(
                f"AuthenticatedIdentity.provider must be a Provider, got {type(self.provider).__name__}"
            )
        if not self.issuer:
            raise ValueError("AuthenticatedIdentity.issuer must be non-empty")
        if not self.subject:
            raise ValueError("AuthenticatedIdentity.subject must be non-empty")
        if not isinstance(self.mfa_satisfied, bool):
            raise TypeError("AuthenticatedIdentity.mfa_satisfied must be a bool")


#: Contract §10: any membership carrying one or more of these roles requires
#: validated MFA evidence before the Organization workspace may be entered.
PRIVILEGED_MFA_ROLES: frozenset[MembershipRole] = frozenset(
    {MembershipRole.PUBLISHER, MembershipRole.OWNER, MembershipRole.ADMIN}
)


class OrganizationAuthorizationStatus(Enum):
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"


class OrganizationAuthorizationReason(Enum):
    """Deterministic, mechanically distinct denial reasons.

    Callers must collapse every one of these into one non-enumerating
    external failure shape (contract §9/§13); the fine-grained reason is for
    internal/test use only and must never be echoed to an unauthorized
    caller.
    """

    NO_MEMBERSHIP = "NO_MEMBERSHIP"
    MEMBERSHIP_INACTIVE = "MEMBERSHIP_INACTIVE"
    MFA_REQUIRED = "MFA_REQUIRED"


@dataclass(frozen=True)
class OrganizationAuthorizationDecision:
    """AUTHORIZED, or DENIED with an explicit deterministic reason."""

    status: OrganizationAuthorizationStatus
    reason: OrganizationAuthorizationReason | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, OrganizationAuthorizationStatus):
            raise TypeError(
                "OrganizationAuthorizationDecision.status must be an OrganizationAuthorizationStatus"
            )
        if self.status is OrganizationAuthorizationStatus.AUTHORIZED and self.reason is not None:
            raise ValueError("An AUTHORIZED decision must not carry a denial reason")
        if self.status is OrganizationAuthorizationStatus.DENIED and self.reason is None:
            raise ValueError("A DENIED decision must carry an explicit reason")

    @property
    def is_authorized(self) -> bool:
        return self.status is OrganizationAuthorizationStatus.AUTHORIZED


def evaluate_organization_workspace_authorization(
    *,
    membership: OrganizationMembership | None,
    mfa_satisfied: bool,
) -> OrganizationAuthorizationDecision:
    """Deterministically decide Organization workspace access.

    Evaluated only against the explicit *membership* supplied by the caller
    (current HullQ state for the exact requested Organization) and the
    explicit *mfa_satisfied* evidence carried by the current authenticated
    session -- never against a stale provider claim or any other
    Organization's membership. A missing/inactive membership always denies,
    independent of MFA. A privileged (`PRIVILEGED_MFA_ROLES`) ACTIVE
    membership additionally requires `mfa_satisfied`.
    """
    if membership is not None and not isinstance(membership, OrganizationMembership):
        raise TypeError(
            f"membership must be an OrganizationMembership or None, got {type(membership).__name__}"
        )
    if not isinstance(mfa_satisfied, bool):
        raise TypeError("mfa_satisfied must be a bool")

    if membership is None:
        return OrganizationAuthorizationDecision(
            status=OrganizationAuthorizationStatus.DENIED,
            reason=OrganizationAuthorizationReason.NO_MEMBERSHIP,
        )

    if membership.state is not MembershipState.ACTIVE:
        return OrganizationAuthorizationDecision(
            status=OrganizationAuthorizationStatus.DENIED,
            reason=OrganizationAuthorizationReason.MEMBERSHIP_INACTIVE,
        )

    if membership.roles & PRIVILEGED_MFA_ROLES and not mfa_satisfied:
        return OrganizationAuthorizationDecision(
            status=OrganizationAuthorizationStatus.DENIED,
            reason=OrganizationAuthorizationReason.MFA_REQUIRED,
        )

    return OrganizationAuthorizationDecision(status=OrganizationAuthorizationStatus.AUTHORIZED)
