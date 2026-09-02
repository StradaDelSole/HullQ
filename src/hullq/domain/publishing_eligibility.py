"""Marketplace professional publishing eligibility — SLICE-0041.

Implements the accepted MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1
decision boundary: given a HullQ Account, an explicit candidate publishing-
principal Organization and the relevant OrganizationMembership,
deterministically decide whether that Account may publish a public
NativeListing on behalf of that Organization.

This module answers only who may act as the professional publishing
principal. It does not create a listing, persist marketplace actors,
integrate Auth0, verify a broker externally, enforce MFA or expose an
API/UI. An ALLOWED result documents domain eligibility only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "AccountId",
    "MarketplaceOrganization",
    "MarketplaceOrganizationId",
    "MembershipRole",
    "MembershipState",
    "OrganizationMembership",
    "OrganizationMembershipId",
    "OrganizationPublishingEligibility",
    "ProfessionalCategory",
    "PublishingEligibilityDecision",
    "PublishingEligibilityReason",
    "PublishingEligibilityStatus",
    "evaluate_native_listing_publishing_eligibility",
]


def _require_kind(value: object, kind: type, field_label: str) -> None:
    """Fail closed when *value* is not an instance of the required *kind*.

    Equal raw text across different identity kinds must not be accepted as
    interchangeable; this check runs at construction time, not only under
    static type-checking.
    """
    if not isinstance(value, kind):
        raise TypeError(f"{field_label} must be a {kind.__name__}, got {type(value).__name__}")


# ---------------------------------------------------------------------------
# Identity kinds — runtime-distinct even when raw values collide
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccountId:
    """Identifies one HullQ Account.

    Represents HullQ Account identity only — not an Auth0 subject, email
    address or login token. Email must not be used as an identity key.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("AccountId.value must be non-empty")


@dataclass(frozen=True)
class MarketplaceOrganizationId:
    """Identifies one HullQ-owned marketplace Organization principal.

    Distinct from Account identity and from SLICE-0040 market identity
    kinds.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("MarketplaceOrganizationId.value must be non-empty")


@dataclass(frozen=True)
class OrganizationMembershipId:
    """Identifies one OrganizationMembership record."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("OrganizationMembershipId.value must be non-empty")


# ---------------------------------------------------------------------------
# Explicit domain vocabularies — never inferred from strings
# ---------------------------------------------------------------------------


class ProfessionalCategory(Enum):
    """Accepted public-supply professional Organization classes."""

    BROKER = "BROKER"
    DEALER = "DEALER"
    OTHER_PROFESSIONAL = "OTHER_PROFESSIONAL"


class OrganizationPublishingEligibility(Enum):
    """Adjudicated professional-supply eligibility state of an Organization.

    This slice does not define how the state is adjudicated. Only ELIGIBLE
    satisfies the Organization-side gate; UNVERIFIED is not equivalent to
    eligible.
    """

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNVERIFIED = "UNVERIFIED"


class MembershipState(Enum):
    """Active/inactive state of an OrganizationMembership."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MembershipRole(Enum):
    """Composable membership roles. Roles may coexist on one membership."""

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    PUBLISHER = "PUBLISHER"
    MEMBER = "MEMBER"


# ---------------------------------------------------------------------------
# Domain records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketplaceOrganization:
    """A candidate professional publishing-principal Organization.

    The professional category does not imply eligibility; eligibility is a
    separate adjudicated state.
    """

    id: MarketplaceOrganizationId
    professional_category: ProfessionalCategory
    publishing_eligibility: OrganizationPublishingEligibility

    def __post_init__(self) -> None:
        _require_kind(self.id, MarketplaceOrganizationId, "MarketplaceOrganization.id")
        _require_kind(
            self.professional_category,
            ProfessionalCategory,
            "MarketplaceOrganization.professional_category",
        )
        _require_kind(
            self.publishing_eligibility,
            OrganizationPublishingEligibility,
            "MarketplaceOrganization.publishing_eligibility",
        )


@dataclass(frozen=True)
class OrganizationMembership:
    """Binds AccountId -> MarketplaceOrganizationId -> roles -> state."""

    id: OrganizationMembershipId
    account_id: AccountId
    organization_id: MarketplaceOrganizationId
    roles: frozenset[MembershipRole]
    state: MembershipState

    def __post_init__(self) -> None:
        _require_kind(self.id, OrganizationMembershipId, "OrganizationMembership.id")
        _require_kind(self.account_id, AccountId, "OrganizationMembership.account_id")
        _require_kind(
            self.organization_id,
            MarketplaceOrganizationId,
            "OrganizationMembership.organization_id",
        )
        _require_kind(self.state, MembershipState, "OrganizationMembership.state")
        if not isinstance(self.roles, frozenset):
            raise TypeError(
                f"OrganizationMembership.roles must be a frozenset, got {type(self.roles).__name__}"
            )
        for role in self.roles:
            _require_kind(role, MembershipRole, "OrganizationMembership.roles member")


# ---------------------------------------------------------------------------
# Decision result — never a bare boolean
# ---------------------------------------------------------------------------


class PublishingEligibilityStatus(Enum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"


class PublishingEligibilityReason(Enum):
    """Deterministic, mechanically distinct denial reasons."""

    NO_MEMBERSHIP = "NO_MEMBERSHIP"
    ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH"
    ORGANIZATION_MISMATCH = "ORGANIZATION_MISMATCH"
    MEMBERSHIP_INACTIVE = "MEMBERSHIP_INACTIVE"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    ORGANIZATION_INELIGIBLE = "ORGANIZATION_INELIGIBLE"
    ORGANIZATION_UNVERIFIED = "ORGANIZATION_UNVERIFIED"


@dataclass(frozen=True)
class PublishingEligibilityDecision:
    """ALLOWED, or DENIED with an explicit deterministic reason.

    An ALLOWED decision documents domain eligibility only: it does not
    assert that MFA, authentication or actual publication has occurred.
    """

    status: PublishingEligibilityStatus
    reason: PublishingEligibilityReason | None = None

    def __post_init__(self) -> None:
        _require_kind(
            self.status, PublishingEligibilityStatus, "PublishingEligibilityDecision.status"
        )
        if self.status is PublishingEligibilityStatus.ALLOWED and self.reason is not None:
            raise ValueError("An ALLOWED decision must not carry a denial reason")
        if self.status is PublishingEligibilityStatus.DENIED and self.reason is None:
            raise ValueError("A DENIED decision must carry an explicit reason")
        if self.reason is not None:
            _require_kind(
                self.reason, PublishingEligibilityReason, "PublishingEligibilityDecision.reason"
            )

    @property
    def is_allowed(self) -> bool:
        return self.status is PublishingEligibilityStatus.ALLOWED


def _allowed() -> PublishingEligibilityDecision:
    return PublishingEligibilityDecision(status=PublishingEligibilityStatus.ALLOWED)


def _denied(reason: PublishingEligibilityReason) -> PublishingEligibilityDecision:
    return PublishingEligibilityDecision(status=PublishingEligibilityStatus.DENIED, reason=reason)


# ---------------------------------------------------------------------------
# Deterministic decision — pure, explicit principal, no ambiguity search
# ---------------------------------------------------------------------------


def evaluate_native_listing_publishing_eligibility(
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
) -> PublishingEligibilityDecision:
    """Deterministically decide NativeListing publishing eligibility.

    Evaluated only against the explicit *candidate_organization* principal
    and the explicit *membership* supplied by the caller. Does not search
    across unrelated memberships to find one that would permit the action.
    """
    _require_kind(account_id, AccountId, "account_id")
    _require_kind(candidate_organization, MarketplaceOrganization, "candidate_organization")
    if membership is not None:
        _require_kind(membership, OrganizationMembership, "membership")

    if membership is None:
        return _denied(PublishingEligibilityReason.NO_MEMBERSHIP)

    if membership.account_id != account_id:
        return _denied(PublishingEligibilityReason.ACCOUNT_MISMATCH)

    if membership.organization_id != candidate_organization.id:
        return _denied(PublishingEligibilityReason.ORGANIZATION_MISMATCH)

    if membership.state is not MembershipState.ACTIVE:
        return _denied(PublishingEligibilityReason.MEMBERSHIP_INACTIVE)

    if MembershipRole.PUBLISHER not in membership.roles:
        return _denied(PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED)

    if (
        candidate_organization.publishing_eligibility
        is not OrganizationPublishingEligibility.ELIGIBLE
    ):
        if (
            candidate_organization.publishing_eligibility
            is OrganizationPublishingEligibility.UNVERIFIED
        ):
            return _denied(PublishingEligibilityReason.ORGANIZATION_UNVERIFIED)
        return _denied(PublishingEligibilityReason.ORGANIZATION_INELIGIBLE)

    return _allowed()
