"""Broker-facing SaleOutcome close-out orchestration — SLICE-0074.

Implements `specs/BROKER_SALE_OUTCOME_CONTRACT.v0.1.md`: thin application
orchestration exposing the already-accepted revisioned
`hullq.persistence.native_listing_sale_outcome` SaleOutcome truth store
through the authenticated Broker Workspace, for an already-existing
NativeListing owned by the selected, currently authorized
MarketplaceOrganization.

Authorization reuses the exact accepted SLICE-0053 Organization workspace/MFA
boundary (`hullq.application.broker_workspace_read.get_organization_workspace_result`)
-- mirrors `hullq.application.broker_inventory_lifecycle`'s and
`hullq.application.inventory_editing`'s identical actor-authorization
pattern -- then re-fetches the current `MarketplaceOrganization`/
`OrganizationMembership` domain records so the contract §8 SaleOutcome
mutation authorization (`hullq.persistence.native_listing_sale_outcome
._evaluate_sale_outcome_mutation_authorization`), invoked again inside the
persistence primitive, remains the sole authority over denial. This module
never pre-decides authorization itself. That authorization is deliberately
narrower than the SLICE-0041 publishing-eligibility evaluator used by the
lifecycle/offer/claim boundaries: it never depends on
`OrganizationPublishingEligibility`, since SaleOutcome is explicit
historical/commercial close-out truth that a current PUBLISHER must still be
able to record/correct for its own existing listing even after the
Organization can no longer publish new/updated public inventory
(independent review, amendment Finding A). A denied mutation therefore
collapses into the identical non-enumerating `ORG_NOT_FOUND_OR_DENIED`
outcome used for an unknown/unauthorized Organization -- there is no
SaleOutcome-specific "publishing denied" response shape.

`NATIVE_LISTING_NOT_FOUND`/`CROSS_ORGANIZATION_DENIED` collapse to the
identical `LISTING_NOT_FOUND` outcome (mirrors every other broker-write
boundary's non-enumeration discipline) -- a foreign listing's existence is
never distinguishable from an unknown one once the Organization boundary
itself has already succeeded.

Every write re-opens a fresh top-level transaction on *conn* before invoking
the persistence primitive (mirrors `broker_inventory_lifecycle`'s identical
`conn.commit()` convention).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.buyer_lead import LeadId
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import (
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
)
from hullq.domain.sale_outcome import SaleOutcomeKind, SaleOutcomeRevisionId, SaleOutcomeSnapshot
from hullq.persistence.broker_identity import (
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.native_listing_sale_outcome import (
    SaleOutcomeRevisionRecord,
    SaleOutcomeWriteResult,
    SaleOutcomeWriteStatus,
    close_native_listing_as_sold,
    fetch_current_sale_outcome,
)
from hullq.security.session_token import SessionClaims

__all__ = [
    "CloseAsSoldOutcome",
    "CloseAsSoldResult",
    "InvalidCloseAsSoldRequestError",
    "SaleOutcomeReadOutcome",
    "SaleOutcomeReadResult",
    "SaleOutcomeView",
    "close_organization_listing_as_sold",
    "get_sale_outcome_for_organization_listing",
]


# ---------------------------------------------------------------------------
# Shared actor authorization -- mirrors
# hullq.application.broker_inventory_lifecycle._authorize_lifecycle_actor
# ---------------------------------------------------------------------------


class _SaleOutcomeActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


@dataclass(frozen=True)
class _AuthorizedActor:
    organization: MarketplaceOrganization
    membership: OrganizationMembership | None


def _authorize_sale_outcome_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> tuple[_SaleOutcomeActorAuthorizationOutcome, _AuthorizedActor | None]:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _SaleOutcomeActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _SaleOutcomeActorAuthorizationOutcome.MFA_REQUIRED, None

    organization = fetch_marketplace_organization(conn, organization_id)
    if organization is None:
        return _SaleOutcomeActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    return (
        _SaleOutcomeActorAuthorizationOutcome.AUTHORIZED,
        _AuthorizedActor(organization=organization, membership=membership),
    )


# ---------------------------------------------------------------------------
# Read: current SaleOutcome (contract §10)
# ---------------------------------------------------------------------------


class SaleOutcomeReadOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    OK = "OK"


@dataclass(frozen=True)
class SaleOutcomeView:
    """Contract §10 minimum visible context. `outcome_kind`/`sold_date`/
    `achieved_amount`/`achieved_currency`/`originating_lead_id`/`recorded_at`
    are `None` together, exactly when no SaleOutcome has ever been recorded
    for this NativeListing -- never a fabricated zero/empty outcome."""

    native_listing_id: str
    organization_id: str
    lifecycle_state: str
    current_sale_outcome_revision_id: str | None
    outcome_kind: str | None
    sold_date: str | None
    achieved_amount: str | None
    achieved_currency: str | None
    originating_lead_id: str | None
    recorded_at: str | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "native_listing_id": self.native_listing_id,
            "organization_id": self.organization_id,
            "lifecycle_state": self.lifecycle_state,
            "current_sale_outcome_revision_id": self.current_sale_outcome_revision_id,
            "outcome_kind": self.outcome_kind,
            "sold_date": self.sold_date,
            "achieved_amount": self.achieved_amount,
            "achieved_currency": self.achieved_currency,
            "originating_lead_id": self.originating_lead_id,
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True)
class SaleOutcomeReadResult:
    outcome: SaleOutcomeReadOutcome
    view: SaleOutcomeView | None = None

    def __post_init__(self) -> None:
        if self.outcome is SaleOutcomeReadOutcome.OK:
            if self.view is None:
                raise ValueError("An OK SaleOutcome read result must carry a view")
        elif self.view is not None:
            raise ValueError("Only an OK SaleOutcome read result may carry a view")


def _outcome_record_to_view(
    native_listing_id: NativeListingId,
    organization_id: MarketplaceOrganizationId,
    lifecycle_state_value: str,
    record: SaleOutcomeRevisionRecord | None,
) -> SaleOutcomeView:
    if record is None:
        return SaleOutcomeView(
            native_listing_id=native_listing_id.value,
            organization_id=organization_id.value,
            lifecycle_state=lifecycle_state_value,
            current_sale_outcome_revision_id=None,
            outcome_kind=None,
            sold_date=None,
            achieved_amount=None,
            achieved_currency=None,
            originating_lead_id=None,
            recorded_at=None,
        )
    outcome = record.outcome
    return SaleOutcomeView(
        native_listing_id=native_listing_id.value,
        organization_id=organization_id.value,
        lifecycle_state=lifecycle_state_value,
        current_sale_outcome_revision_id=record.revision_id.value,
        outcome_kind=outcome.kind.value,
        sold_date=outcome.sold_date.isoformat() if outcome.sold_date is not None else None,
        achieved_amount=str(outcome.achieved_amount)
        if outcome.achieved_amount is not None
        else None,
        achieved_currency=outcome.achieved_currency,
        originating_lead_id=(
            outcome.originating_lead_id.value if outcome.originating_lead_id is not None else None
        ),
        recorded_at=record.recorded_at.isoformat(),
    )


def get_sale_outcome_for_organization_listing(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
) -> SaleOutcomeReadResult:
    """Read the current authoritative SaleOutcome (if any) plus lifecycle
    state for one own NativeListing (contract §10)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_sale_outcome_actor(conn, session, organization_id)
    if auth_outcome is _SaleOutcomeActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return SaleOutcomeReadResult(outcome=SaleOutcomeReadOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _SaleOutcomeActorAuthorizationOutcome.MFA_REQUIRED:
        return SaleOutcomeReadResult(outcome=SaleOutcomeReadOutcome.MFA_REQUIRED)
    assert actor is not None

    native_listing_id = NativeListingId(native_listing_id_value)
    listing_record = fetch_native_listing(conn, native_listing_id)
    if listing_record is None or listing_record.publishing_organization_id != organization_id:
        return SaleOutcomeReadResult(outcome=SaleOutcomeReadOutcome.LISTING_NOT_FOUND)
    lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
    assert lifecycle_state is not None

    record = fetch_current_sale_outcome(conn, native_listing_id)
    view = _outcome_record_to_view(
        native_listing_id, organization_id, lifecycle_state.value, record
    )
    return SaleOutcomeReadResult(outcome=SaleOutcomeReadOutcome.OK, view=view)


# ---------------------------------------------------------------------------
# Write: close as SOLD (contract §6/§9)
# ---------------------------------------------------------------------------

_REVISION_ID_KEY = "revision_id"
_EXPECTED_REVISION_KEY = "expected_current_revision_id"
_SOLD_DATE_KEY = "sold_date"
_ACHIEVED_AMOUNT_KEY = "achieved_amount"
_ACHIEVED_CURRENCY_KEY = "achieved_currency"
_ORIGINATING_LEAD_KEY = "originating_lead_id"

_KNOWN_REQUEST_KEYS = frozenset(
    {
        _REVISION_ID_KEY,
        _EXPECTED_REVISION_KEY,
        _SOLD_DATE_KEY,
        _ACHIEVED_AMOUNT_KEY,
        _ACHIEVED_CURRENCY_KEY,
        _ORIGINATING_LEAD_KEY,
    }
)

_DECIMAL_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")


class InvalidCloseAsSoldRequestError(ValueError):
    """Raised for an unknown key, an invalid value shape or a rejected
    `SaleOutcomeSnapshot` construction. Callers must fail the whole request
    closed (400) with zero mutation -- never a partial accept."""


@dataclass(frozen=True)
class _ParsedCloseAsSoldRequest:
    revision_id: SaleOutcomeRevisionId
    expected_current_revision_id: SaleOutcomeRevisionId | None
    outcome: SaleOutcomeSnapshot


def _parse_close_as_sold_request(raw: Any) -> _ParsedCloseAsSoldRequest:
    if not isinstance(raw, dict):
        raise InvalidCloseAsSoldRequestError(
            f"close-as-SOLD request must be a JSON object, got {type(raw).__name__}"
        )
    unknown = set(raw) - _KNOWN_REQUEST_KEYS
    if unknown:
        raise InvalidCloseAsSoldRequestError(f"unknown request key(s): {sorted(unknown)}")

    if _REVISION_ID_KEY not in raw:
        raise InvalidCloseAsSoldRequestError(f"{_REVISION_ID_KEY} is required")
    raw_revision_id = raw[_REVISION_ID_KEY]
    if not isinstance(raw_revision_id, str) or not raw_revision_id:
        raise InvalidCloseAsSoldRequestError(f"{_REVISION_ID_KEY} must be a non-empty string")
    revision_id = SaleOutcomeRevisionId(raw_revision_id)

    if _EXPECTED_REVISION_KEY not in raw:
        raise InvalidCloseAsSoldRequestError(f"{_EXPECTED_REVISION_KEY} is required")
    raw_expected = raw[_EXPECTED_REVISION_KEY]
    expected_current_revision_id: SaleOutcomeRevisionId | None
    if raw_expected is None:
        expected_current_revision_id = None
    elif isinstance(raw_expected, str) and raw_expected:
        expected_current_revision_id = SaleOutcomeRevisionId(raw_expected)
    else:
        raise InvalidCloseAsSoldRequestError(
            f"{_EXPECTED_REVISION_KEY} must be a non-empty string or null"
        )

    sold_date: date | None = None
    if raw.get(_SOLD_DATE_KEY) is not None:
        raw_sold_date = raw[_SOLD_DATE_KEY]
        if not isinstance(raw_sold_date, str):
            raise InvalidCloseAsSoldRequestError(f"{_SOLD_DATE_KEY} must be a string or null")
        try:
            sold_date = date.fromisoformat(raw_sold_date)
        except ValueError as exc:
            raise InvalidCloseAsSoldRequestError(
                f"{_SOLD_DATE_KEY} must be an ISO 8601 calendar date (YYYY-MM-DD)"
            ) from exc

    achieved_amount: Decimal | None = None
    if raw.get(_ACHIEVED_AMOUNT_KEY) is not None:
        raw_amount = raw[_ACHIEVED_AMOUNT_KEY]
        if not isinstance(raw_amount, str) or not _DECIMAL_PATTERN.fullmatch(raw_amount):
            raise InvalidCloseAsSoldRequestError(
                f"{_ACHIEVED_AMOUNT_KEY} must be a plain positive decimal string"
            )
        achieved_amount = Decimal(raw_amount)

    achieved_currency: str | None = None
    if raw.get(_ACHIEVED_CURRENCY_KEY) is not None:
        raw_currency = raw[_ACHIEVED_CURRENCY_KEY]
        if not isinstance(raw_currency, str):
            raise InvalidCloseAsSoldRequestError(
                f"{_ACHIEVED_CURRENCY_KEY} must be a string or null"
            )
        achieved_currency = raw_currency

    originating_lead_id: LeadId | None = None
    if raw.get(_ORIGINATING_LEAD_KEY) is not None:
        raw_lead_id = raw[_ORIGINATING_LEAD_KEY]
        if not isinstance(raw_lead_id, str) or not raw_lead_id:
            raise InvalidCloseAsSoldRequestError(
                f"{_ORIGINATING_LEAD_KEY} must be a non-empty string or null"
            )
        originating_lead_id = LeadId(raw_lead_id)

    try:
        outcome = SaleOutcomeSnapshot(
            kind=SaleOutcomeKind.SOLD,
            sold_date=sold_date,
            achieved_amount=achieved_amount,
            achieved_currency=achieved_currency,
            originating_lead_id=originating_lead_id,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidCloseAsSoldRequestError(str(exc)) from exc

    return _ParsedCloseAsSoldRequest(
        revision_id=revision_id,
        expected_current_revision_id=expected_current_revision_id,
        outcome=outcome,
    )


class CloseAsSoldOutcome(StrEnum):
    """Mechanically distinct outcomes -- never a bare boolean.

    There is no `DENIED`/"publishing denied" member here: contract §8
    authorization failures (missing/inactive membership, Account/
    Organization mismatch, missing PUBLISHER role) all collapse into the
    identical non-enumerating `ORG_NOT_FOUND_OR_DENIED` outcome already used
    for an unknown/unauthorized Organization -- never a SaleOutcome-specific
    reason-bearing denial shape (independent review, amendment Finding A).
    """

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    DRAFT_NOT_ELIGIBLE = "DRAFT_NOT_ELIGIBLE"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    INVALID_LEAD = "INVALID_LEAD"
    STALE_VERSION = "STALE_VERSION"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class CloseAsSoldResult:
    outcome: CloseAsSoldOutcome
    current_sale_outcome_revision_id: str | None = None
    lifecycle_state: str | None = None
    transitioned_to_withdrawn: bool = False

    def __post_init__(self) -> None:
        carries_revision = self.outcome in (
            CloseAsSoldOutcome.CLOSED,
            CloseAsSoldOutcome.STALE_VERSION,
        )
        if not carries_revision and self.current_sale_outcome_revision_id is not None:
            raise ValueError("Only CLOSED/STALE_VERSION may carry current_sale_outcome_revision_id")
        if (
            self.outcome is CloseAsSoldOutcome.CLOSED
            and self.current_sale_outcome_revision_id is None
        ):
            raise ValueError("A CLOSED result must carry current_sale_outcome_revision_id")

        if self.outcome is CloseAsSoldOutcome.CLOSED:
            if self.lifecycle_state is None:
                raise ValueError("A CLOSED result must carry lifecycle_state")
        elif self.lifecycle_state is not None:
            raise ValueError("Only a CLOSED result may carry lifecycle_state")

        if self.outcome is not CloseAsSoldOutcome.CLOSED and self.transitioned_to_withdrawn:
            raise ValueError("transitioned_to_withdrawn may only be True on a CLOSED result")

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"outcome": self.outcome.value}
        if self.current_sale_outcome_revision_id is not None:
            body["current_sale_outcome_revision_id"] = self.current_sale_outcome_revision_id
        if self.lifecycle_state is not None:
            body["lifecycle_state"] = self.lifecycle_state
        if self.outcome is CloseAsSoldOutcome.CLOSED:
            body["transitioned_to_withdrawn"] = self.transitioned_to_withdrawn
        return body


def _map_close_result(result: SaleOutcomeWriteResult) -> CloseAsSoldResult:
    if result.status is SaleOutcomeWriteStatus.DENIED:
        # Contract §8: a missing/inactive membership, Account/Organization
        # mismatch or missing PUBLISHER role all collapse into the identical
        # non-enumerating outcome already used for an unknown/unauthorized
        # Organization -- never a reason-bearing "publishing denied" shape
        # (independent review, amendment Finding A).
        return CloseAsSoldResult(outcome=CloseAsSoldOutcome.ORG_NOT_FOUND_OR_DENIED)
    if result.status in (
        SaleOutcomeWriteStatus.CROSS_ORGANIZATION_DENIED,
        SaleOutcomeWriteStatus.NATIVE_LISTING_NOT_FOUND,
    ):
        return CloseAsSoldResult(outcome=CloseAsSoldOutcome.LISTING_NOT_FOUND)
    if result.status is SaleOutcomeWriteStatus.DRAFT_NOT_ELIGIBLE:
        return CloseAsSoldResult(outcome=CloseAsSoldOutcome.DRAFT_NOT_ELIGIBLE)
    if result.status is SaleOutcomeWriteStatus.INVALID_LEAD:
        return CloseAsSoldResult(outcome=CloseAsSoldOutcome.INVALID_LEAD)
    if result.status is SaleOutcomeWriteStatus.CONFLICT:
        return CloseAsSoldResult(
            outcome=CloseAsSoldOutcome.STALE_VERSION,
            current_sale_outcome_revision_id=(
                result.current_revision_id.value if result.current_revision_id is not None else None
            ),
        )
    assert result.status in (
        SaleOutcomeWriteStatus.CREATED,
        SaleOutcomeWriteStatus.REVISED,
        SaleOutcomeWriteStatus.ALREADY_EXISTS,
    )
    assert result.current_revision_id is not None
    assert result.resulting_state is not None
    return CloseAsSoldResult(
        outcome=CloseAsSoldOutcome.CLOSED,
        current_sale_outcome_revision_id=result.current_revision_id.value,
        lifecycle_state=result.resulting_state.value,
        transitioned_to_withdrawn=result.transitioned_to_withdrawn,
    )


def close_organization_listing_as_sold(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_body: Any,
) -> CloseAsSoldResult:
    """Record one SOLD outcome for one own NativeListing, atomically
    withdrawing it when currently ACTIVE (contract §6/§9)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_sale_outcome_actor(conn, session, organization_id)
    if auth_outcome is _SaleOutcomeActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return CloseAsSoldResult(outcome=CloseAsSoldOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _SaleOutcomeActorAuthorizationOutcome.MFA_REQUIRED:
        return CloseAsSoldResult(outcome=CloseAsSoldOutcome.MFA_REQUIRED)
    assert actor is not None

    try:
        parsed = _parse_close_as_sold_request(raw_body)
    except InvalidCloseAsSoldRequestError:
        return CloseAsSoldResult(outcome=CloseAsSoldOutcome.INVALID_PAYLOAD)

    conn.commit()
    result = close_native_listing_as_sold(
        conn,
        account_id=session.account_id,
        candidate_organization=actor.organization,
        membership=actor.membership,
        native_listing_id=NativeListingId(native_listing_id_value),
        revision_id=parsed.revision_id,
        expected_current_revision_id=parsed.expected_current_revision_id,
        outcome=parsed.outcome,
    )
    return _map_close_result(result)
