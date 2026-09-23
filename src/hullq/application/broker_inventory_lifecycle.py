"""Broker-facing inventory lifecycle/freshness orchestration — SLICE-0064.

Implements `specs/PROFESSIONAL_INVENTORY_LIFECYCLE_CONTROLS_CONTRACT.v0.1.md`:
thin application orchestration exposing the already-accepted SLICE-0049
lifecycle transitions (`hullq.persistence.native_listing_lifecycle
.publish_native_listing` / `.withdraw_native_listing`) and the already-
accepted SLICE-0052 reconfirmation primitive
(`hullq.persistence.native_listing_freshness.reconfirm_native_listing`)
through the authenticated Broker Workspace, for an already-existing
NativeListing owned by the selected, currently authorized
MarketplaceOrganization.

This module never reinterprets lifecycle, freshness or authorization
semantics (contract §2): it reuses the exact accepted SLICE-0053
Organization workspace/MFA boundary
(`hullq.application.broker_workspace_read.get_organization_workspace_result`)
for the org-existence/membership/MFA gate, then re-fetches the current
`MarketplaceOrganization`/`OrganizationMembership` domain records so the
accepted SLICE-0041 publishing-eligibility evaluator -- invoked again,
unconditionally, *inside* each persistence primitive -- remains the sole
authority over PUBLISHER-role/Organization-eligibility denial (contract §5):
this module never pre-decides eligibility itself.

`NATIVE_LISTING_NOT_FOUND` and `ORGANIZATION_MISMATCH` (an existing listing
owned by a different Organization) collapse to the identical
`LISTING_NOT_FOUND` outcome (contract §4): a foreign listing's existence is
never distinguishable from an unknown one once the Organization boundary
itself has already succeeded.

Every write re-opens a fresh top-level transaction on *conn* before invoking
the persistence primitive (contract §8): the authorization reads issued by
`get_organization_workspace_result` and this module's own
Organization/Membership re-fetch leave an implicit read transaction open
under psycopg's default `autocommit=False`, so `conn.commit()` ends it
first -- otherwise the persistence primitive's own `with conn.transaction():`
would silently degrade to a nested SAVEPOINT (mirrors
`hullq.application.professional_listing_draft`'s identical comment).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
from hullq.domain.native_listing_lifecycle import PublicationTransitionId
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
from hullq.persistence.native_listing_freshness import (
    ReconfirmationResult,
    ReconfirmationStatus,
    reconfirm_native_listing,
)
from hullq.persistence.native_listing_lifecycle import (
    LifecycleTransitionResult,
    LifecycleTransitionStatus,
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.security.session_token import SessionClaims

#: A literal parenthesized `except (A, B, C):` tuple is reformatted by the
#: installed `ruff format` into invalid Python 3 `except A, B, C:` syntax
#: (mirrors `scripts/inspect_owner_direct_draft.py`'s identical named-tuple
#: workaround); referencing a named tuple constant instead sidesteps that.
_CONFIRMATION_ID_PARSE_ERRORS = (ValueError, AttributeError, TypeError)

__all__ = [
    "InventoryLifecycleOutcome",
    "LifecycleActionResult",
    "ReconfirmInventoryOutcome",
    "ReconfirmResult",
    "publish_organization_listing",
    "reconfirm_organization_listing",
    "withdraw_organization_listing",
]


# ---------------------------------------------------------------------------
# Shared actor authorization -- reuses the accepted Organization workspace
# boundary, then re-fetches the domain records the persistence primitives
# require (contract §4).
# ---------------------------------------------------------------------------


class _LifecycleActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


@dataclass(frozen=True)
class _AuthorizedActor:
    organization: MarketplaceOrganization
    membership: OrganizationMembership | None


def _authorize_lifecycle_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> tuple[_LifecycleActorAuthorizationOutcome, _AuthorizedActor | None]:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _LifecycleActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _LifecycleActorAuthorizationOutcome.MFA_REQUIRED, None

    organization = fetch_marketplace_organization(conn, organization_id)
    if organization is None:
        # The Organization vanished between the workspace check above and
        # this re-fetch -- collapse to the identical non-enumerating outcome
        # rather than crash.
        return _LifecycleActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    return (
        _LifecycleActorAuthorizationOutcome.AUTHORIZED,
        _AuthorizedActor(organization=organization, membership=membership),
    )


# ---------------------------------------------------------------------------
# Publish / Withdraw
# ---------------------------------------------------------------------------


class InventoryLifecycleOutcome(StrEnum):
    """Mechanically distinct publish/withdraw outcomes (contract §14)."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    DENIED = "DENIED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INCOMPLETE_LISTING = "INCOMPLETE_LISTING"
    STATE_CONFLICT = "STATE_CONFLICT"
    PUBLISHED = "PUBLISHED"
    WITHDRAWN = "WITHDRAWN"


@dataclass(frozen=True)
class LifecycleActionResult:
    """Deterministic result of one publish/withdraw attempt.

    `DENIED` always carries the real SLICE-0041 denial reason. `PUBLISHED`/
    `WITHDRAWN` always carry the newly appended immutable `transition_id`.
    No other outcome carries either field.
    """

    outcome: InventoryLifecycleOutcome
    denial_reason: PublishingEligibilityReason | None = None
    transition_id: PublicationTransitionId | None = None

    def __post_init__(self) -> None:
        if self.outcome is InventoryLifecycleOutcome.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry a denial reason")

        carries_transition = self.outcome in (
            InventoryLifecycleOutcome.PUBLISHED,
            InventoryLifecycleOutcome.WITHDRAWN,
        )
        if carries_transition:
            if self.transition_id is None:
                raise ValueError(f"A {self.outcome.value} result must carry a transition_id")
        elif self.transition_id is not None:
            raise ValueError("Only a PUBLISHED/WITHDRAWN result may carry a transition_id")

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"outcome": self.outcome.value}
        if self.denial_reason is not None:
            body["reason"] = self.denial_reason.value
        if self.transition_id is not None:
            body["transition_id"] = self.transition_id.value
        return body


def _map_transition_result(
    result: LifecycleTransitionResult, *, published: bool
) -> LifecycleActionResult:
    if result.status is LifecycleTransitionStatus.DENIED:
        assert result.denial_reason is not None
        return LifecycleActionResult(
            outcome=InventoryLifecycleOutcome.DENIED, denial_reason=result.denial_reason
        )
    if result.status in (
        LifecycleTransitionStatus.NATIVE_LISTING_NOT_FOUND,
        LifecycleTransitionStatus.ORGANIZATION_MISMATCH,
    ):
        return LifecycleActionResult(outcome=InventoryLifecycleOutcome.LISTING_NOT_FOUND)
    if result.status is LifecycleTransitionStatus.INCOMPLETE_LISTING:
        return LifecycleActionResult(outcome=InventoryLifecycleOutcome.INCOMPLETE_LISTING)
    if result.status is LifecycleTransitionStatus.CURRENT_STATE_CONFLICT:
        return LifecycleActionResult(outcome=InventoryLifecycleOutcome.STATE_CONFLICT)
    assert result.status is LifecycleTransitionStatus.TRANSITIONED
    assert result.transition_id is not None
    outcome = (
        InventoryLifecycleOutcome.PUBLISHED if published else InventoryLifecycleOutcome.WITHDRAWN
    )
    return LifecycleActionResult(outcome=outcome, transition_id=result.transition_id)


def publish_organization_listing(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
) -> LifecycleActionResult:
    """Publish one existing, complete, own DRAFT NativeListing (contract §9)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_lifecycle_actor(conn, session, organization_id)
    if auth_outcome is _LifecycleActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return LifecycleActionResult(outcome=InventoryLifecycleOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _LifecycleActorAuthorizationOutcome.MFA_REQUIRED:
        return LifecycleActionResult(outcome=InventoryLifecycleOutcome.MFA_REQUIRED)
    assert actor is not None

    # Ends the authorization reads' implicit transaction so the mutation
    # below commits independently (see module docstring).
    conn.commit()
    result = publish_native_listing(
        conn,
        account_id=session.account_id,
        candidate_organization=actor.organization,
        membership=actor.membership,
        native_listing_id=NativeListingId(native_listing_id_value),
    )
    return _map_transition_result(result, published=True)


def withdraw_organization_listing(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
) -> LifecycleActionResult:
    """Withdraw one existing own ACTIVE NativeListing (contract §10)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_lifecycle_actor(conn, session, organization_id)
    if auth_outcome is _LifecycleActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return LifecycleActionResult(outcome=InventoryLifecycleOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _LifecycleActorAuthorizationOutcome.MFA_REQUIRED:
        return LifecycleActionResult(outcome=InventoryLifecycleOutcome.MFA_REQUIRED)
    assert actor is not None

    conn.commit()
    result = withdraw_native_listing(
        conn,
        account_id=session.account_id,
        candidate_organization=actor.organization,
        membership=actor.membership,
        native_listing_id=NativeListingId(native_listing_id_value),
    )
    return _map_transition_result(result, published=False)


# ---------------------------------------------------------------------------
# Reconfirm
# ---------------------------------------------------------------------------


class ReconfirmInventoryOutcome(StrEnum):
    """Mechanically distinct reconfirmation outcomes (contract §14)."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    DENIED = "DENIED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_OPERATION_ID = "INVALID_OPERATION_ID"
    STATE_CONFLICT = "STATE_CONFLICT"
    OPERATION_ID_CONFLICT = "OPERATION_ID_CONFLICT"
    RECONFIRMED = "RECONFIRMED"


@dataclass(frozen=True)
class ReconfirmResult:
    """Deterministic result of one reconfirmation attempt.

    `DENIED` always carries the real SLICE-0041 denial reason. `RECONFIRMED`
    always carries the immutable event's real `occurred_at` -- identical
    whether this call created the event or exactly retried an existing one
    (contract §11/§4.2: an exact retry never manufactures a new timestamp).
    No other outcome carries either field.
    """

    outcome: ReconfirmInventoryOutcome
    denial_reason: PublishingEligibilityReason | None = None
    occurred_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.outcome is ReconfirmInventoryOutcome.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry a denial reason")

        if self.outcome is ReconfirmInventoryOutcome.RECONFIRMED:
            if self.occurred_at is None:
                raise ValueError("A RECONFIRMED result must carry occurred_at")
        elif self.occurred_at is not None:
            raise ValueError("Only a RECONFIRMED result may carry occurred_at")

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"outcome": self.outcome.value}
        if self.denial_reason is not None:
            body["reason"] = self.denial_reason.value
        if self.occurred_at is not None:
            body["occurred_at"] = self.occurred_at.isoformat()
        return body


def _parse_confirmation_id(raw: Any) -> FreshnessConfirmationId | None:
    """Accept only a canonical (lowercase, hyphenated) UUID string.

    Contract §11 SHOULDs a canonical UUID; this module MUSTs it, rejecting
    any other spelling rather than silently canonicalizing it -- two
    differently-spelled strings for the identical UUID must never be treated
    as the same stable operation identity by one caller and a different one
    by another (mirrors the strict-canonical-cursor discipline already
    accepted elsewhere in this codebase, e.g.
    `hullq.application.broker_inventory_read._cursor_b64url_decode`).
    """
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = uuid.UUID(raw)
    except _CONFIRMATION_ID_PARSE_ERRORS:
        return None
    if str(parsed) != raw:
        return None
    return FreshnessConfirmationId(raw)


def _map_reconfirm_result(result: ReconfirmationResult) -> ReconfirmResult:
    if result.status is ReconfirmationStatus.DENIED:
        assert result.denial_reason is not None
        return ReconfirmResult(
            outcome=ReconfirmInventoryOutcome.DENIED, denial_reason=result.denial_reason
        )
    if result.status in (
        ReconfirmationStatus.NATIVE_LISTING_NOT_FOUND,
        ReconfirmationStatus.ORGANIZATION_MISMATCH,
    ):
        return ReconfirmResult(outcome=ReconfirmInventoryOutcome.LISTING_NOT_FOUND)
    if result.status is ReconfirmationStatus.NOT_ACTIVE:
        return ReconfirmResult(outcome=ReconfirmInventoryOutcome.STATE_CONFLICT)
    if result.status is ReconfirmationStatus.CONFLICT:
        return ReconfirmResult(outcome=ReconfirmInventoryOutcome.OPERATION_ID_CONFLICT)
    assert result.status in (ReconfirmationStatus.RECONFIRMED, ReconfirmationStatus.ALREADY_EXISTS)
    assert result.occurred_at is not None
    return ReconfirmResult(
        outcome=ReconfirmInventoryOutcome.RECONFIRMED, occurred_at=result.occurred_at
    )


def reconfirm_organization_listing(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_confirmation_id: Any,
) -> ReconfirmResult:
    """Reconfirm one existing own ACTIVE NativeListing (contract §11).

    *raw_confirmation_id* is the caller-supplied bounded operation identity
    (contract §12: "Reconfirm carries only the bounded operation/
    confirmation identity"); a malformed value is rejected before *conn* is
    ever asked to mutate anything.
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_lifecycle_actor(conn, session, organization_id)
    if auth_outcome is _LifecycleActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return ReconfirmResult(outcome=ReconfirmInventoryOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _LifecycleActorAuthorizationOutcome.MFA_REQUIRED:
        return ReconfirmResult(outcome=ReconfirmInventoryOutcome.MFA_REQUIRED)
    assert actor is not None

    confirmation_id = _parse_confirmation_id(raw_confirmation_id)
    if confirmation_id is None:
        return ReconfirmResult(outcome=ReconfirmInventoryOutcome.INVALID_OPERATION_ID)

    conn.commit()
    result = reconfirm_native_listing(
        conn,
        confirmation_id=confirmation_id,
        account_id=session.account_id,
        candidate_organization=actor.organization,
        membership=actor.membership,
        native_listing_id=NativeListingId(native_listing_id_value),
    )
    return _map_reconfirm_result(result)
