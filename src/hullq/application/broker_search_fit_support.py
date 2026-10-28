"""Shared support for every broker-facing authorized single-target
hypothetical DRAFT Search-fit preview (Sail: SLICE-0084+'s
`hullq.application.broker_search_fit`; Power: SLICE-0095's
`hullq.application.power_broker_search_fit`).

Extracted so the Organization/MFA/PUBLISHER authorization boundary and the
"exactly-once, canonical-or-fail-closed" scenario-parameter rule are each
decided in exactly one place and reused unchanged by every domain-specific
preview -- never re-implemented per domain (SLICE-0095 Required Behavior
§2: "If a helper is currently private, extract/reuse narrowly ... rather
than copying its business logic"). Neither helper encodes any Sail- or
Power-specific truth; each domain module maps the generic outcome onto its
own typed result/exception shape.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId, MembershipRole
from hullq.security.session_token import SessionClaims

__all__ = [
    "BrokerActorAuthorizationOutcome",
    "evaluate_broker_actor_authorization",
    "parse_single_valued_scenario_param",
]


class BrokerActorAuthorizationOutcome(StrEnum):
    """The generic, domain-neutral Organization/MFA/PUBLISHER authorization
    decision every broker Search-fit preview needs before touching its own
    listing/lifecycle/scenario logic."""

    AUTHORIZED = "AUTHORIZED"
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"


def evaluate_broker_actor_authorization(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> BrokerActorAuthorizationOutcome:
    """Evaluate the current workspace + PUBLISHER-role authorization
    boundary (mirrors the original `hullq.application.broker_search_fit
    ._authorize_actor`'s identical rationale, generalized away from that
    module's own Sail-specific `SearchFitResult` return shape).

    Callers must call this function twice -- once from inside the bounded
    `REPEATABLE READ` snapshot the rest of the evaluation reads from, and
    once more immediately after that snapshot closes, from a deliberately
    fresh statement against the now-current committed state (independent
    review Finding A, PR #342): an Organization membership revoked, or its
    PUBLISHER role removed, while the first evaluation was in flight is
    caught by the second call rather than silently legitimizing a stale
    authorization decision.
    """
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return BrokerActorAuthorizationOutcome.ORG_NOT_FOUND_OR_DENIED
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return BrokerActorAuthorizationOutcome.MFA_REQUIRED
    assert workspace_result.context is not None

    # `evaluate_organization_workspace_authorization` already guarantees an
    # AUTHORIZED outcome's membership is current and ACTIVE -- only the
    # PUBLISHER-role requirement a Search-fit preview's own contract adds
    # still needs checking, from the same authorized read.
    if MembershipRole.PUBLISHER.value not in workspace_result.context.roles:
        return BrokerActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED
    return BrokerActorAuthorizationOutcome.AUTHORIZED


def parse_single_valued_scenario_param(
    label: str,
    raw_values: Sequence[str],
    parsed: tuple[Any, bool] | None,
    *,
    error_type: type[ValueError],
) -> Any:
    """Shared "exactly-once, canonical-or-fail-closed" rule every private
    Search-fit scenario criterion follows (mirrors the original
    `hullq.application.broker_search_fit._parse_single_valued`'s identical
    rationale, driven by `hullq.search.criteria_registry
    .parse_numeric_param`/`parse_categorical_param`'s shared
    `(value, is_single_canonical) | None` convention). Unlike the public
    canonical-URL surface, a private preview has no redirect identity --
    ANY non-single-canonical input (duplicate, even of an identical value,
    or a non-canonical spelling) fails closed directly, never silently
    normalized. *error_type* lets each domain module raise its own typed
    `InvalidSearchFitScenarioError`/`InvalidPowerSearchFitScenarioError`
    rather than a shared one, so callers can still distinguish by `except`
    clause and the exception message/type a test asserts on never changes.
    """
    if parsed is None:
        raise error_type(f"{label} is not a supported/valid value")
    value, is_single_canonical = parsed
    if value is None:
        return None
    if len(raw_values) > 1:
        raise error_type(f"{label} must be supplied exactly once")
    if not is_single_canonical:
        raise error_type(f"{label} {raw_values[0]!r} is not in canonical form")
    return value
