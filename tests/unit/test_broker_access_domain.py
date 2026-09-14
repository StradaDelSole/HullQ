"""Unit tests for hullq.domain.broker_access — SLICE-0053.

Covers the pure Organization-workspace-authorization decision boundary
(contract §9/§10) independent of any persistence/network concern.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hullq.domain.broker_access import (
    AuthenticatedIdentity,
    OrganizationAuthorizationReason,
    OrganizationAuthorizationStatus,
    Provider,
    evaluate_organization_workspace_authorization,
)
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
)

DEFAULT_ACCOUNT_ID = AccountId("ACC-X")
DEFAULT_ORGANIZATION_ID = MarketplaceOrganizationId("ORG-A")


def _membership(
    *,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.MEMBER}),
    state: MembershipState = MembershipState.ACTIVE,
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId("OM-1"),
        account_id=DEFAULT_ACCOUNT_ID,
        organization_id=DEFAULT_ORGANIZATION_ID,
        roles=roles,
        state=state,
    )


class TestAuthenticatedIdentity:
    def test_valid_identity_constructs(self) -> None:
        identity = AuthenticatedIdentity(
            provider=Provider.AUTH0,
            issuer="https://hullq-dev.eu.auth0.com/",
            subject="auth0|abc123",
            auth_time=datetime.now(UTC),
            mfa_satisfied=True,
        )
        assert identity.subject == "auth0|abc123"

    def test_empty_issuer_rejected(self) -> None:
        with pytest.raises(ValueError, match="issuer"):
            AuthenticatedIdentity(
                provider=Provider.AUTH0, issuer="", subject="s", auth_time=None, mfa_satisfied=False
            )

    def test_empty_subject_rejected(self) -> None:
        with pytest.raises(ValueError, match="subject"):
            AuthenticatedIdentity(
                provider=Provider.AUTH0,
                issuer="iss",
                subject="",
                auth_time=None,
                mfa_satisfied=False,
            )

    def test_wrong_provider_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            AuthenticatedIdentity(
                provider="auth0",  # type: ignore[arg-type]
                issuer="iss",
                subject="s",
                auth_time=None,
                mfa_satisfied=False,
            )


class TestEvaluateOrganizationWorkspaceAuthorization:
    def test_no_membership_denied(self) -> None:
        decision = evaluate_organization_workspace_authorization(
            membership=None, mfa_satisfied=False
        )
        assert decision.status is OrganizationAuthorizationStatus.DENIED
        assert decision.reason is OrganizationAuthorizationReason.NO_MEMBERSHIP

    def test_inactive_membership_denied_even_with_mfa(self) -> None:
        decision = evaluate_organization_workspace_authorization(
            membership=_membership(state=MembershipState.INACTIVE), mfa_satisfied=True
        )
        assert decision.status is OrganizationAuthorizationStatus.DENIED
        assert decision.reason is OrganizationAuthorizationReason.MEMBERSHIP_INACTIVE

    def test_non_privileged_active_membership_authorized_without_mfa(self) -> None:
        decision = evaluate_organization_workspace_authorization(
            membership=_membership(roles=frozenset({MembershipRole.MEMBER})), mfa_satisfied=False
        )
        assert decision.is_authorized

    @pytest.mark.parametrize(
        "role", [MembershipRole.PUBLISHER, MembershipRole.OWNER, MembershipRole.ADMIN]
    )
    def test_privileged_role_without_mfa_denied(self, role: MembershipRole) -> None:
        decision = evaluate_organization_workspace_authorization(
            membership=_membership(roles=frozenset({role})), mfa_satisfied=False
        )
        assert decision.status is OrganizationAuthorizationStatus.DENIED
        assert decision.reason is OrganizationAuthorizationReason.MFA_REQUIRED

    @pytest.mark.parametrize(
        "role", [MembershipRole.PUBLISHER, MembershipRole.OWNER, MembershipRole.ADMIN]
    )
    def test_privileged_role_with_mfa_authorized(self, role: MembershipRole) -> None:
        decision = evaluate_organization_workspace_authorization(
            membership=_membership(roles=frozenset({role})), mfa_satisfied=True
        )
        assert decision.is_authorized

    def test_mixed_roles_one_privileged_still_requires_mfa(self) -> None:
        decision = evaluate_organization_workspace_authorization(
            membership=_membership(roles=frozenset({MembershipRole.MEMBER, MembershipRole.OWNER})),
            mfa_satisfied=False,
        )
        assert decision.status is OrganizationAuthorizationStatus.DENIED
        assert decision.reason is OrganizationAuthorizationReason.MFA_REQUIRED

    def test_wrong_membership_type_rejected(self) -> None:
        with pytest.raises(TypeError):
            evaluate_organization_workspace_authorization(
                membership="not-a-membership", mfa_satisfied=False
            )  # type: ignore[arg-type]

    def test_non_bool_mfa_rejected(self) -> None:
        with pytest.raises(TypeError):
            evaluate_organization_workspace_authorization(membership=None, mfa_satisfied=1)  # type: ignore[arg-type]

    def test_decision_never_authorized_with_reason(self) -> None:
        from hullq.domain.broker_access import OrganizationAuthorizationDecision

        with pytest.raises(ValueError, match="AUTHORIZED"):
            OrganizationAuthorizationDecision(
                status=OrganizationAuthorizationStatus.AUTHORIZED,
                reason=OrganizationAuthorizationReason.NO_MEMBERSHIP,
            )

    def test_decision_denied_requires_reason(self) -> None:
        from hullq.domain.broker_access import OrganizationAuthorizationDecision

        with pytest.raises(ValueError, match="DENIED"):
            OrganizationAuthorizationDecision(status=OrganizationAuthorizationStatus.DENIED)
