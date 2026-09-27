"""Professional draft promotion application orchestration — SLICE-0067.

Implements `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md` §4/§6:
thin orchestration over the accepted Organization workspace/MFA boundary
(`hullq.application.broker_workspace_read.get_organization_workspace_result`)
plus the one atomic promotion transaction
(`hullq.persistence.professional_listing_promotion.promote_professional_listing_draft`),
translating a signed `SessionClaims`, an explicit Organization selection and
a raw JSON-decoded request body into one deterministic outcome FastAPI can
render.

Contract §4 requires, for *every* promotion request -- including a read-only
exact-version retry of an already-PROMOTED draft -- that the current
Organization/MFA/ACTIVE-membership boundary AND current `PUBLISHER`
membership all hold before any draft/result disclosure. This module
therefore gates current `PUBLISHER` membership itself, at the same actor-
authorization layer as the professional draft-authoring gate
(`hullq.application.professional_listing_draft._authorize_draft_actor`) --
before the target draft is ever locked/read, so a non-PUBLISHER current
member cannot distinguish an unknown draft id from a known EDITABLE/PROMOTED
one, cannot see `NativeListingId` provenance, and causes zero mutation.

This module still never pre-decides *publishing eligibility* itself (mirrors
`hullq.application.broker_inventory_lifecycle`'s identical rationale): once
current PUBLISHER membership is confirmed, it re-fetches the current
`MarketplaceOrganization`/`OrganizationMembership` domain records and lets
the real accepted SLICE-0041 evaluator -- invoked once, inside the
persistence transaction, only for a new EDITABLE -> PROMOTED materialization
-- be the sole authority over Organization-eligibility denial. Contract §4's
last paragraph is preserved exactly: an already-PROMOTED exact-version retry
never re-requires current Organization publishing eligibility, only current
workspace/MFA/PUBLISHER authorization (checked here, uniformly, before the
persistence call either way).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.professional_listing_draft import ProfessionalListingDraftId
from hullq.domain.promotion_readiness import PromotionReadinessReason
from hullq.domain.publishing_eligibility import (
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
)
from hullq.persistence.broker_identity import (
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.persistence.professional_listing_promotion import (
    ProfessionalListingPromotionStatus,
    promote_professional_listing_draft,
)
from hullq.security.session_token import SessionClaims

__all__ = [
    "PromoteProfessionalDraftOutcome",
    "PromoteProfessionalDraftResult",
    "promote_professional_draft_for_organization",
]


class _PromotionActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


@dataclass(frozen=True)
class _AuthorizedActor:
    organization: MarketplaceOrganization
    membership: OrganizationMembership | None


def _authorize_promotion_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> tuple[_PromotionActorAuthorizationOutcome, _AuthorizedActor | None]:
    """Contract §4 items 1-5: authenticated session, current Organization
    access, MFA where required, exact current ACTIVE membership and current
    `PUBLISHER` membership -- required uniformly for *every* promotion
    request, including a read-only exact-version retry of an already-
    PROMOTED draft, and resolved entirely before the target draft is ever
    locked/read (mirrors `hullq.application.professional_listing_draft
    ._authorize_draft_actor`'s identical PUBLISHER-role gate).
    """
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _PromotionActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _PromotionActorAuthorizationOutcome.MFA_REQUIRED, None
    assert workspace_result.context is not None
    if "PUBLISHER" not in workspace_result.context.roles:
        return _PromotionActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED, None

    organization = fetch_marketplace_organization(conn, organization_id)
    if organization is None:
        return _PromotionActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    return (
        _PromotionActorAuthorizationOutcome.AUTHORIZED,
        _AuthorizedActor(organization=organization, membership=membership),
    )


def _parse_expected_version(raw_body: Any) -> int | None:
    """Contract §6: exactly one key, a positive JSON integer, booleans
    rejected. Missing/extra keys, `null`, strings, floats and non-positive
    values are all malformed."""
    if not isinstance(raw_body, dict):
        return None
    if set(raw_body) != {"expected_version"}:
        return None
    value = raw_body["expected_version"]
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value <= 0:
        return None
    return value


class PromoteProfessionalDraftOutcome(StrEnum):
    """Mechanically distinct outcomes for one promotion request."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    INVALID_REQUEST = "INVALID_REQUEST"
    DRAFT_NOT_FOUND = "DRAFT_NOT_FOUND"
    DENIED = "DENIED"
    NOT_READY = "NOT_READY"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    DUPLICATE_EPISODE = "DUPLICATE_EPISODE"
    PROMOTED = "PROMOTED"
    ALREADY_PROMOTED = "ALREADY_PROMOTED"


_STATUSES_CARRYING_NATIVE_LISTING_ID = frozenset(
    {PromoteProfessionalDraftOutcome.PROMOTED, PromoteProfessionalDraftOutcome.ALREADY_PROMOTED}
)

_PROMOTION_STATUS_TO_OUTCOME = {
    ProfessionalListingPromotionStatus.PROMOTED: PromoteProfessionalDraftOutcome.PROMOTED,
    ProfessionalListingPromotionStatus.ALREADY_PROMOTED: (
        PromoteProfessionalDraftOutcome.ALREADY_PROMOTED
    ),
    ProfessionalListingPromotionStatus.NOT_READY: PromoteProfessionalDraftOutcome.NOT_READY,
    ProfessionalListingPromotionStatus.VERSION_CONFLICT: (
        PromoteProfessionalDraftOutcome.VERSION_CONFLICT
    ),
    ProfessionalListingPromotionStatus.DRAFT_NOT_FOUND: (
        PromoteProfessionalDraftOutcome.DRAFT_NOT_FOUND
    ),
    ProfessionalListingPromotionStatus.DENIED: PromoteProfessionalDraftOutcome.DENIED,
    ProfessionalListingPromotionStatus.DUPLICATE_EPISODE: (
        PromoteProfessionalDraftOutcome.DUPLICATE_EPISODE
    ),
}


@dataclass(frozen=True)
class PromoteProfessionalDraftResult:
    outcome: PromoteProfessionalDraftOutcome
    native_listing_id: str | None = None
    reasons: tuple[PromotionReadinessReason, ...] | None = None
    denial_reason: PublishingEligibilityReason | None = None

    def __post_init__(self) -> None:
        if self.outcome in _STATUSES_CARRYING_NATIVE_LISTING_ID:
            if self.native_listing_id is None:
                raise ValueError(f"A {self.outcome.value} result must carry a native_listing_id")
        elif self.native_listing_id is not None:
            raise ValueError("Only PROMOTED/ALREADY_PROMOTED may carry a native_listing_id")

        if self.outcome is PromoteProfessionalDraftOutcome.NOT_READY:
            if not self.reasons:
                raise ValueError("A NOT_READY result must carry at least one reason")
        elif self.reasons is not None:
            raise ValueError("Only a NOT_READY result may carry reasons")

        if self.outcome is PromoteProfessionalDraftOutcome.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry a denial reason")

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"outcome": self.outcome.value}
        if self.native_listing_id is not None:
            body["native_listing_id"] = self.native_listing_id
        if self.reasons is not None:
            body["reasons"] = [reason.value for reason in self.reasons]
        if self.denial_reason is not None:
            body["reason"] = self.denial_reason.value
        return body


def promote_professional_draft_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    draft_id_value: str,
    raw_body: Any,
) -> PromoteProfessionalDraftResult:
    """Promote one exact, Organization-owned draft version (contract §4/§6)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_promotion_actor(conn, session, organization_id)
    if auth_outcome is _PromotionActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return PromoteProfessionalDraftResult(
            outcome=PromoteProfessionalDraftOutcome.ORG_NOT_FOUND_OR_DENIED
        )
    if auth_outcome is _PromotionActorAuthorizationOutcome.MFA_REQUIRED:
        return PromoteProfessionalDraftResult(outcome=PromoteProfessionalDraftOutcome.MFA_REQUIRED)
    if auth_outcome is _PromotionActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        # Contract §4: missing current PUBLISHER membership is resolved
        # before the target draft is ever touched -- reuses the existing
        # DENIED outcome + the real SLICE-0041 PUBLISHER_ROLE_REQUIRED
        # reason (never a new external outcome), so the response is
        # identical to any other publishing-denied 403 regardless of
        # whether draft_id_value names an unknown, EDITABLE or PROMOTED
        # draft, and regardless of expected_version.
        return PromoteProfessionalDraftResult(
            outcome=PromoteProfessionalDraftOutcome.DENIED,
            denial_reason=PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        )
    assert actor is not None

    expected_version = _parse_expected_version(raw_body)
    if expected_version is None:
        return PromoteProfessionalDraftResult(
            outcome=PromoteProfessionalDraftOutcome.INVALID_REQUEST
        )

    # Ends the authorization reads' implicit transaction so the promotion
    # transaction below commits independently rather than as an uncommitted
    # nested SAVEPOINT (mirrors `hullq.application.broker_inventory_lifecycle`'s
    # identical comment).
    conn.commit()
    result = promote_professional_listing_draft(
        conn,
        account_id=session.account_id,
        candidate_organization=actor.organization,
        membership=actor.membership,
        draft_id=ProfessionalListingDraftId(draft_id_value),
        owner_organization_id=organization_id,
        expected_version=expected_version,
    )

    outcome = _PROMOTION_STATUS_TO_OUTCOME[result.status]
    return PromoteProfessionalDraftResult(
        outcome=outcome,
        native_listing_id=(
            result.native_listing_id.value if result.native_listing_id is not None else None
        ),
        reasons=result.reasons,
        denial_reason=result.denial_reason,
    )
