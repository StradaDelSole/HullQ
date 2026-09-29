"""Durable buyer contact / Lead creation persistence — SLICE-0070.

Implements `specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md` §5/§6/§12:
given an explicit target NativeListingId and already-validated bounded
buyer-supplied fields, atomically re-evaluate the canonical D29
CurrentPublicEligibility authority
(`hullq.application.current_public_eligibility.resolve_current_public_eligibility`
-- contract §12: "Do not introduce a second listing eligibility definition")
and, only when currently ELIGIBLE, durably create one immutable Lead
creation envelope in PostgreSQL.

Concurrency safety reuses the identical `SELECT ... FOR UPDATE` row-lock
pattern already accepted for lifecycle transitions/reconfirmation
(`hullq.persistence.native_listing_lifecycle`,
`hullq.persistence.native_listing_freshness`): locking the target
`native_listings` row for the duration of this transaction serializes a Lead
creation attempt against any concurrent lifecycle/freshness transition for
the same NativeListingId, so a stale browser page can never durably create a
Lead after current-public eligibility was already lost (contract §5's "A
stale browser page ... never grants a capability to create a Lead after
current-public eligibility is lost").

Idempotency/conflict resolution for the caller-supplied
`SubmissionOperationId` itself is handled race-safely via
`INSERT ... ON CONFLICT DO NOTHING` plus an exact envelope-fingerprint
comparison -- the same pattern already accepted for SLICE-0043 NativeListing
creation and SLICE-0052 reconfirmation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.current_public_eligibility import resolve_current_public_eligibility
from hullq.domain.buyer_lead import (
    ContactEmailVerificationState,
    LeadId,
    LeadSourceChannel,
    SubmissionOperationId,
)
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.persistence.fingerprint import fingerprint_dict

__all__ = [
    "BuyerLeadCreationResult",
    "BuyerLeadCreationStatus",
    "BuyerLeadRecord",
    "BuyerLeadTransactionOwnershipError",
    "create_buyer_lead",
    "fetch_buyer_lead",
]


class BuyerLeadTransactionOwnershipError(RuntimeError):
    """create_buyer_lead cannot safely own a top-level transaction on *conn*.

    Mirrors `hullq.persistence.native_listing.NativeListingTransactionOwnershipError`:
    a CREATED result must always mean the new immutable Lead row is already
    durably committed, independent of later caller action. That guarantee
    only holds when *conn* is IDLE (no transaction already open). Call
    ``conn.commit()``/``conn.rollback()`` first, or pass a freshly opened
    connection.
    """


class BuyerLeadCreationStatus(StrEnum):
    """Mechanically distinct creation outcomes. Never a bare boolean."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    #: Contract §5: missing, DRAFT, WITHDRAWN and ACTIVE-but-suppressed
    #: targets all collapse to this identical non-enumerating outcome.
    LISTING_NOT_AVAILABLE = "listing_not_available"


@dataclass(frozen=True)
class BuyerLeadCreationResult:
    """Deterministic result of one create_buyer_lead call.

    Only `CREATED`/`ALREADY_EXISTS` carry `lead_id`/`received_at`.
    """

    status: BuyerLeadCreationStatus
    lead_id: LeadId | None = None
    received_at: datetime | None = None

    def __post_init__(self) -> None:
        carries_identity = self.status in (
            BuyerLeadCreationStatus.CREATED,
            BuyerLeadCreationStatus.ALREADY_EXISTS,
        )
        if carries_identity:
            if self.lead_id is None or self.received_at is None:
                raise ValueError(
                    f"A {self.status.value} creation result must carry lead_id and received_at"
                )
        elif self.lead_id is not None or self.received_at is not None:
            raise ValueError(
                "Only a created/already_exists creation result may carry lead_id/received_at"
            )


@dataclass(frozen=True)
class BuyerLeadRecord:
    """Exact typed readback of one persisted Lead creation envelope.

    Contract §14: this readback exists for automated tests/retained proof
    only -- it does not authorize a public lookup endpoint or the Broker
    Workspace Lead inbox.
    """

    lead_id: LeadId
    submission_operation_id: SubmissionOperationId
    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    account_id: AccountId | None
    buyer_name: str
    buyer_email: str
    contact_email_verification_state: ContactEmailVerificationState
    buyer_message: str
    source_channel: LeadSourceChannel
    received_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SELECT_LISTING_FOR_UPDATE = (
    "SELECT publishing_organization_id FROM native_listings WHERE native_listing_id = %s FOR UPDATE"
)

_INSERT_LEAD = """
INSERT INTO buyer_leads (
    lead_id, submission_operation_id, native_listing_id, publishing_organization_id,
    account_id, buyer_name, buyer_email, contact_email_verification_state,
    buyer_message, source_channel, envelope_content_hash
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (submission_operation_id) DO NOTHING
RETURNING lead_id, received_at
"""

_SELECT_EXISTING_LEAD_BY_OPERATION_ID = (
    "SELECT lead_id, envelope_content_hash, received_at FROM buyer_leads "
    "WHERE submission_operation_id = %s"
)

_SELECT_LEAD = """
SELECT lead_id, submission_operation_id, native_listing_id, publishing_organization_id,
       account_id, buyer_name, buyer_email, contact_email_verification_state,
       buyer_message, source_channel, received_at
FROM buyer_leads WHERE lead_id = %s
"""


def _envelope_fingerprint(
    native_listing_id: str,
    publishing_organization_id: str,
    account_id: str | None,
    buyer_name: str,
    buyer_email: str,
    buyer_message: str,
) -> str:
    """Fingerprint exactly the caller-controlled immutable envelope.

    `received_at`/`lead_id` are deliberately excluded: both are
    system-generated, never caller-controlled, and must not participate in
    idempotency/conflict comparison (mirrors the SLICE-0043/SLICE-0052
    fingerprint discipline).
    """
    return fingerprint_dict(
        {
            "native_listing_id": native_listing_id,
            "publishing_organization_id": publishing_organization_id,
            "account_id": account_id,
            "buyer_name": buyer_name,
            "buyer_email": buyer_email,
            "buyer_message": buyer_message,
        }
    )


def create_buyer_lead(
    conn: Any,
    *,
    submission_operation_id: SubmissionOperationId,
    native_listing_id: NativeListingId,
    account_id: AccountId | None,
    buyer_name: str,
    buyer_email: str,
    buyer_message: str,
    as_of: datetime,
) -> BuyerLeadCreationResult:
    """Re-evaluate D29 CurrentPublicEligibility, then durably create the Lead
    iff currently ELIGIBLE.

    *buyer_name*/*buyer_email*/*buyer_message* must already be validated/
    normalized by the caller (`hullq.application.buyer_lead_creation`) --
    this function performs no input-shape validation of its own, only
    identity-type checks.

    Race-safe: locks the target `native_listings` row for the duration of
    this transaction (contract §12), then uses
    INSERT ... ON CONFLICT DO NOTHING plus an exact content-hash comparison
    for the caller-supplied *submission_operation_id*, rather than a
    check-then-insert race. Same operation id + identical immutable envelope
    -> ALREADY_EXISTS with the original row untouched. Same operation id + a
    different immutable envelope -> CONFLICT, and the original row is never
    overwritten.

    Raises BuyerLeadTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(submission_operation_id, SubmissionOperationId):
        raise TypeError(
            "submission_operation_id must be a SubmissionOperationId, got "
            f"{type(submission_operation_id).__name__}"
        )
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    if account_id is not None and not isinstance(account_id, AccountId):
        raise TypeError(f"account_id must be an AccountId or None, got {type(account_id).__name__}")

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise BuyerLeadTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); create_buyer_lead() requires an IDLE "
            "connection so it can safely own and commit its own top-level transaction. "
            "Call conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    with conn.transaction(), conn.cursor() as cur:
        # Locks the target native_listings row for the duration of this
        # transaction, serializing this Lead creation attempt against any
        # concurrent lifecycle/freshness transition for the same
        # NativeListingId (contract §12) -- mirrors the FOR UPDATE pattern
        # already accepted for publish/withdraw/reconfirm.
        cur.execute(_SELECT_LISTING_FOR_UPDATE, [native_listing_id.value])
        row = cur.fetchone()
        if row is None:
            return BuyerLeadCreationResult(status=BuyerLeadCreationStatus.LISTING_NOT_AVAILABLE)
        publishing_organization_id_value = row[0]

        # The one canonical D29 authority (contract §12: "Do not introduce a
        # second listing eligibility definition"), re-evaluated fresh inside
        # this same locked transaction so its reads observe a consistent
        # snapshot no concurrent lifecycle/freshness/offer/claim/media
        # transition can race past.
        eligibility = resolve_current_public_eligibility(conn, native_listing_id, as_of=as_of)
        if eligibility is None or eligibility.status is not CurrentPublicEligibilityStatus.ELIGIBLE:
            return BuyerLeadCreationResult(status=BuyerLeadCreationStatus.LISTING_NOT_AVAILABLE)

        lead_id = LeadId(str(uuid.uuid4()))
        envelope_hash = _envelope_fingerprint(
            native_listing_id.value,
            publishing_organization_id_value,
            account_id.value if account_id is not None else None,
            buyer_name,
            buyer_email,
            buyer_message,
        )
        cur.execute(
            _INSERT_LEAD,
            (
                lead_id.value,
                submission_operation_id.value,
                native_listing_id.value,
                publishing_organization_id_value,
                account_id.value if account_id is not None else None,
                buyer_name,
                buyer_email,
                ContactEmailVerificationState.UNVERIFIED.value,
                buyer_message,
                LeadSourceChannel.HULLQ_PUBLIC_LISTING_CONTACT.value,
                envelope_hash,
            ),
        )
        inserted = cur.fetchone()
        if inserted is not None:
            return BuyerLeadCreationResult(
                status=BuyerLeadCreationStatus.CREATED, lead_id=lead_id, received_at=inserted[1]
            )

        # submission_operation_id already exists (exact retry or a
        # conflicting reuse): compare the caller-controlled immutable
        # envelope only, and never touch/rewrite the original row. The
        # freshly minted *lead_id* above is discarded unused.
        cur.execute(_SELECT_EXISTING_LEAD_BY_OPERATION_ID, [submission_operation_id.value])
        existing = cur.fetchone()
        assert existing is not None, "ON CONFLICT target row must exist"
        existing_lead_id_value, existing_envelope_hash, existing_received_at = existing
        if existing_envelope_hash == envelope_hash:
            return BuyerLeadCreationResult(
                status=BuyerLeadCreationStatus.ALREADY_EXISTS,
                lead_id=LeadId(existing_lead_id_value),
                received_at=existing_received_at,
            )
        return BuyerLeadCreationResult(status=BuyerLeadCreationStatus.CONFLICT)


def fetch_buyer_lead(conn: Any, lead_id: LeadId) -> BuyerLeadRecord | None:
    """Exact typed readback by LeadId, or None if not found.

    Contract §14: private/internal readback for automated tests and
    retained proof only -- no public Lead lookup endpoint is built on this.
    """
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.cursor() as cur:
        cur.execute(_SELECT_LEAD, [lead_id.value])
        row = cur.fetchone()
    if row is None:
        return None

    (
        lead_id_value,
        submission_operation_id_value,
        native_listing_id_value,
        publishing_organization_id_value,
        account_id_value,
        buyer_name,
        buyer_email,
        verification_state_value,
        buyer_message,
        source_channel_value,
        received_at,
    ) = row
    return BuyerLeadRecord(
        lead_id=LeadId(lead_id_value),
        submission_operation_id=SubmissionOperationId(submission_operation_id_value),
        native_listing_id=NativeListingId(native_listing_id_value),
        publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id_value),
        account_id=AccountId(account_id_value) if account_id_value is not None else None,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        contact_email_verification_state=ContactEmailVerificationState(verification_state_value),
        buyer_message=buyer_message,
        source_channel=LeadSourceChannel(source_channel_value),
        received_at=received_at,
    )
