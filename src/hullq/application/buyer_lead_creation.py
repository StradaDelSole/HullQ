"""Durable buyer contact / Lead creation orchestration — SLICE-0070.

The one production application entry point for
`specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md`: validates/
normalizes the bounded buyer-supplied request shape (contract §8) at this
boundary -- before `hullq.persistence.buyer_lead.create_buyer_lead` is ever
asked to touch the database -- then delegates the authoritative current-
public recheck + atomic creation to that persistence function.

Never trusts client-supplied Organization identity (contract §2/§5): only a
target NativeListingId is accepted from the request; the publishing
Organization is always derived server-side from authoritative NativeListing
truth inside the persistence layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.buyer_lead import (
    LeadId,
    SubmissionOperationId,
    normalize_buyer_email,
    normalize_buyer_message,
    normalize_buyer_name,
    normalize_submission_operation_id,
)
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import AccountId
from hullq.persistence.buyer_lead import BuyerLeadCreationStatus, create_buyer_lead

__all__ = ["CreateBuyerLeadOutcome", "CreateBuyerLeadResult", "create_buyer_lead_for_listing"]


class CreateBuyerLeadOutcome(StrEnum):
    """The bounded public creation-result vocabulary (contract §10)."""

    CREATED = "CREATED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    LISTING_NOT_AVAILABLE = "LISTING_NOT_AVAILABLE"
    INVALID_INPUT = "INVALID_INPUT"
    SUBMISSION_CONFLICT = "SUBMISSION_CONFLICT"


@dataclass(frozen=True)
class CreateBuyerLeadResult:
    """Deterministic result of one buyer contact submission.

    Only `CREATED`/`ALREADY_EXISTS` carry `lead_id`/`received_at`.
    """

    outcome: CreateBuyerLeadOutcome
    lead_id: LeadId | None = None
    received_at: datetime | None = None

    def __post_init__(self) -> None:
        carries_identity = self.outcome in (
            CreateBuyerLeadOutcome.CREATED,
            CreateBuyerLeadOutcome.ALREADY_EXISTS,
        )
        if carries_identity:
            if self.lead_id is None or self.received_at is None:
                raise ValueError(
                    f"A {self.outcome.value} result must carry lead_id and received_at"
                )
        elif self.lead_id is not None or self.received_at is not None:
            raise ValueError("Only a CREATED/ALREADY_EXISTS result may carry lead_id/received_at")


def create_buyer_lead_for_listing(
    conn: Any,
    *,
    native_listing_id_value: str,
    account_id: AccountId | None,
    raw_submission_operation_id: Any,
    raw_name: Any,
    raw_email: Any,
    raw_message: Any,
    as_of: datetime,
) -> CreateBuyerLeadResult:
    """Validate the bounded request shape, then delegate to
    `hullq.persistence.buyer_lead.create_buyer_lead`.

    *account_id* is optional attribution only (contract §3): the caller
    (the FastAPI route) resolves it from an already-verified HullQ session,
    never from a client-supplied field. A malformed *native_listing_id_value*
    (contract §5's missing/unknown targets) and any invalid/missing bounded
    field (contract §8) both fail closed before the database is touched --
    the former as LISTING_NOT_AVAILABLE (never a distinguishable identity
    error), the latter as INVALID_INPUT.
    """
    try:
        native_listing_id = NativeListingId(native_listing_id_value)
    except (TypeError, ValueError):
        return CreateBuyerLeadResult(outcome=CreateBuyerLeadOutcome.LISTING_NOT_AVAILABLE)

    try:
        submission_operation_id = SubmissionOperationId(
            normalize_submission_operation_id(raw_submission_operation_id)
        )
        buyer_name = normalize_buyer_name(raw_name)
        buyer_email = normalize_buyer_email(raw_email)
        buyer_message = normalize_buyer_message(raw_message)
    except (TypeError, ValueError):
        return CreateBuyerLeadResult(outcome=CreateBuyerLeadOutcome.INVALID_INPUT)

    result = create_buyer_lead(
        conn,
        submission_operation_id=submission_operation_id,
        native_listing_id=native_listing_id,
        account_id=account_id,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_message=buyer_message,
        as_of=as_of,
    )

    if result.status is BuyerLeadCreationStatus.LISTING_NOT_AVAILABLE:
        return CreateBuyerLeadResult(outcome=CreateBuyerLeadOutcome.LISTING_NOT_AVAILABLE)
    if result.status is BuyerLeadCreationStatus.CONFLICT:
        return CreateBuyerLeadResult(outcome=CreateBuyerLeadOutcome.SUBMISSION_CONFLICT)
    if result.status is BuyerLeadCreationStatus.CREATED:
        assert result.lead_id is not None
        assert result.received_at is not None
        return CreateBuyerLeadResult(
            outcome=CreateBuyerLeadOutcome.CREATED,
            lead_id=result.lead_id,
            received_at=result.received_at,
        )
    assert result.status is BuyerLeadCreationStatus.ALREADY_EXISTS
    assert result.lead_id is not None
    assert result.received_at is not None
    return CreateBuyerLeadResult(
        outcome=CreateBuyerLeadOutcome.ALREADY_EXISTS,
        lead_id=result.lead_id,
        received_at=result.received_at,
    )
