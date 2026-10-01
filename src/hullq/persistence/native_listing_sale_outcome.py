"""Durable NativeListing SaleOutcome persistence — SLICE-0074.

Implements `specs/BROKER_SALE_OUTCOME_CONTRACT.v0.1.md`: given an already-
persisted, authorized `NativeListing`, durably record an explicit SOLD
outcome as an immutable, append-only revision plus an explicit current/head
pointer (contract §7) -- exactly mirroring the already-accepted
`hullq.persistence.native_listing_offer` revision/head/content-hash
idempotency discipline, never a second, independently designed concurrency
model.

Recording SOLD on an ACTIVE listing atomically appends the outcome revision
*and* transitions lifecycle `ACTIVE -> WITHDRAWN` in the same database
transaction (contract §9: "No commit-and-compensate sequence is allowed").
This module never reinterprets lifecycle semantics itself: the transition is
applied via `hullq.persistence.native_listing_lifecycle
.apply_lifecycle_transition_row`, the exact accepted SLICE-0049 row
primitive, composed here under the identical `native_listings` row lock this
module already holds for the outcome write -- mirrors
`hullq.persistence.professional_listing_promotion`'s identical composition-
over-reimplementation discipline (contract §19 "no second lifecycle
authority").

Recording SOLD on an already-WITHDRAWN listing appends only the outcome
revision; lifecycle is left untouched. Recording SOLD on a DRAFT listing is
rejected (contract §9: "DRAFT SOLD recording is rejected in v0.1").

The real accepted SLICE-0041 publishing-eligibility evaluator is always
called; a caller-supplied authorization boolean is never accepted. The
candidate Organization must also equal the target NativeListing's persisted
`publishing_organization_id` -- eligibility inside one Organization never
authorizes closing another Organization's listing.

An optional `originating_lead_id` is validated, under the same lock, against
the real accepted SLICE-0070 `buyer_leads` record: it must exist, belong to
the identical Organization and reference the identical NativeListing
(contract §13); a missing/foreign/mismatched Lead fails the whole write
closed with zero mutation. No Lead is ever invented or inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.domain.buyer_lead import LeadId
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_lifecycle import (
    NativeListingLifecycleState,
    PublicationTransitionId,
)
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.domain.sale_outcome import SaleOutcomeKind, SaleOutcomeRevisionId, SaleOutcomeSnapshot
from hullq.persistence.buyer_lead import fetch_buyer_lead
from hullq.persistence.fingerprint import fingerprint_dict
from hullq.persistence.native_listing_lifecycle import apply_lifecycle_transition_row

__all__ = [
    "SaleOutcomeRevisionRecord",
    "SaleOutcomeTransactionOwnershipError",
    "SaleOutcomeWriteResult",
    "SaleOutcomeWriteStatus",
    "close_native_listing_as_sold",
    "fetch_current_sale_outcome",
    "fetch_sale_outcome_revision",
    "list_sale_outcome_revisions",
]


class SaleOutcomeTransactionOwnershipError(RuntimeError):
    """`close_native_listing_as_sold` cannot safely own a top-level
    transaction on *conn*.

    Mirrors `hullq.persistence.native_listing_offer.NativeListingOfferTransactionOwnershipError`:
    a CREATED/REVISED result must always mean the new current outcome
    revision -- and, for SOLD-on-ACTIVE, the ACTIVE -> WITHDRAWN transition
    -- are already durably committed together, independent of later caller
    action. That guarantee only holds when *conn* is IDLE (no transaction
    already open), since psycopg's ``conn.transaction()`` otherwise silently
    degrades to a nested SAVEPOINT. Call ``conn.commit()``/``conn.rollback()``
    first, or pass a freshly opened connection.
    """


class SaleOutcomeWriteStatus(StrEnum):
    """Mechanically distinct write outcomes. Never a bare boolean."""

    CREATED = "created"
    REVISED = "revised"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    DENIED = "denied"
    CROSS_ORGANIZATION_DENIED = "cross_organization_denied"
    NATIVE_LISTING_NOT_FOUND = "native_listing_not_found"
    DRAFT_NOT_ELIGIBLE = "draft_not_eligible"
    INVALID_LEAD = "invalid_lead"


_STATUSES_REQUIRING_CURRENT_REVISION = frozenset(
    {
        SaleOutcomeWriteStatus.CREATED,
        SaleOutcomeWriteStatus.REVISED,
        SaleOutcomeWriteStatus.ALREADY_EXISTS,
    }
)
_STATUSES_FORBIDDING_CURRENT_REVISION = frozenset(
    {
        SaleOutcomeWriteStatus.DENIED,
        SaleOutcomeWriteStatus.CROSS_ORGANIZATION_DENIED,
        SaleOutcomeWriteStatus.NATIVE_LISTING_NOT_FOUND,
        SaleOutcomeWriteStatus.DRAFT_NOT_ELIGIBLE,
        SaleOutcomeWriteStatus.INVALID_LEAD,
    }
)
_STATUSES_CARRYING_LIFECYCLE = _STATUSES_REQUIRING_CURRENT_REVISION


@dataclass(frozen=True)
class SaleOutcomeWriteResult:
    """Deterministic result of one `close_native_listing_as_sold` attempt.

    `DENIED` always carries the real SLICE-0041 denial reason.
    `current_revision_id` reflects the real durable current head of *this*
    NativeListing's SaleOutcome after this call (the new revision for
    CREATED/REVISED, the pre-existing current revision for ALREADY_EXISTS)
    and is never populated for a case that wrote nothing. `resulting_state`
    carries the lifecycle state immediately after this call (ACTIVE is
    never a possible value here -- SOLD is only ever recorded against ACTIVE
    or WITHDRAWN, and ACTIVE always transitions to WITHDRAWN in the same
    call). `transitioned_to_withdrawn` is `True` only when *this exact call*
    performed the ACTIVE -> WITHDRAWN transition (never on an idempotent
    retry of an already-applied transition, and never for a correction
    recorded against an already-WITHDRAWN listing).
    """

    status: SaleOutcomeWriteStatus
    denial_reason: PublishingEligibilityReason | None = None
    current_revision_id: SaleOutcomeRevisionId | None = None
    resulting_state: NativeListingLifecycleState | None = None
    transitioned_to_withdrawn: bool = False
    transition_id: PublicationTransitionId | None = None

    def __post_init__(self) -> None:
        if self.status is SaleOutcomeWriteStatus.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED write result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED write result may carry a denial reason")

        if self.status in _STATUSES_REQUIRING_CURRENT_REVISION:
            if self.current_revision_id is None:
                raise ValueError(
                    f"A {self.status.value.upper()} write result must carry current_revision_id"
                )
        elif (
            self.status in _STATUSES_FORBIDDING_CURRENT_REVISION
            and self.current_revision_id is not None
        ):
            raise ValueError(
                f"A {self.status.value.upper()} write result must not carry current_revision_id"
            )

        if self.status in _STATUSES_CARRYING_LIFECYCLE:
            if self.resulting_state is None:
                raise ValueError(
                    f"A {self.status.value.upper()} write result must carry resulting_state"
                )
        elif self.resulting_state is not None:
            raise ValueError("resulting_state may only be carried by a successful write result")

        if self.transitioned_to_withdrawn and self.transition_id is None:
            raise ValueError("transitioned_to_withdrawn=True must carry a transition_id")
        if not self.transitioned_to_withdrawn and self.transition_id is not None:
            raise ValueError(
                "transition_id may only be carried when transitioned_to_withdrawn=True"
            )


@dataclass(frozen=True)
class SaleOutcomeRevisionRecord:
    """Exact typed readback of one persisted NativeListing SaleOutcome revision."""

    revision_id: SaleOutcomeRevisionId
    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    recorded_by_account_id: AccountId
    outcome: SaleOutcomeSnapshot
    previous_revision_id: SaleOutcomeRevisionId | None
    recorded_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SELECT_LISTING_FOR_UPDATE = (
    "SELECT publishing_organization_id, lifecycle_state FROM native_listings "
    "WHERE native_listing_id = %s FOR UPDATE"
)

_SELECT_HEAD = (
    "SELECT current_sale_outcome_revision_id FROM native_listing_sale_outcome_heads "
    "WHERE native_listing_id = %s"
)

_SELECT_REVISION_BY_ID = (
    "SELECT native_listing_id, content_hash FROM native_listing_sale_outcome_revisions "
    "WHERE sale_outcome_revision_id = %s"
)

_INSERT_REVISION = """
INSERT INTO native_listing_sale_outcome_revisions (
    sale_outcome_revision_id, native_listing_id, publishing_organization_id,
    recorded_by_account_id, outcome_kind, sold_date, achieved_amount, achieved_currency,
    originating_lead_id, previous_sale_outcome_revision_id, content_hash
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (sale_outcome_revision_id) DO NOTHING
"""

_UPSERT_HEAD = """
INSERT INTO native_listing_sale_outcome_heads (native_listing_id, current_sale_outcome_revision_id)
VALUES (%s, %s)
ON CONFLICT (native_listing_id)
DO UPDATE SET current_sale_outcome_revision_id = EXCLUDED.current_sale_outcome_revision_id,
              updated_at = NOW()
"""

_REVISION_COLUMNS = """
    r.sale_outcome_revision_id, r.native_listing_id, r.publishing_organization_id,
    r.recorded_by_account_id, r.outcome_kind, r.sold_date, r.achieved_amount,
    r.achieved_currency, r.originating_lead_id, r.previous_sale_outcome_revision_id,
    r.recorded_at
"""

_SELECT_CURRENT_OUTCOME = f"""
SELECT {_REVISION_COLUMNS}
FROM native_listing_sale_outcome_heads h
JOIN native_listing_sale_outcome_revisions r ON r.sale_outcome_revision_id = h.current_sale_outcome_revision_id
WHERE h.native_listing_id = %s
"""

_SELECT_REVISION_RECORD = f"""
SELECT {_REVISION_COLUMNS}
FROM native_listing_sale_outcome_revisions r
WHERE r.sale_outcome_revision_id = %s
"""

_SELECT_HISTORY = f"""
SELECT {_REVISION_COLUMNS}
FROM native_listing_sale_outcome_revisions r
WHERE r.native_listing_id = %s
ORDER BY r.recorded_at ASC, r.sale_outcome_revision_id ASC
"""


# ---------------------------------------------------------------------------
# Fingerprint envelope
# ---------------------------------------------------------------------------


def _canonical_decimal_str(value: Decimal) -> str:
    """Stable string form for a finite Decimal, independent of the active
    Decimal context. Mirrors
    `hullq.persistence.native_listing_offer._canonical_decimal_str` exactly
    -- see that function's docstring for why `Decimal.normalize()` alone is
    unsafe for fingerprinting.
    """
    sign, digits_tuple, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError(f"achieved_amount must be finite, got {value!r}")
    digits = list(digits_tuple)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    if digits == [0]:
        exponent = 0
    coefficient = "".join(str(d) for d in digits)
    sign_str = "-" if sign else ""
    return f"{sign_str}{coefficient}E{exponent}"


def _outcome_envelope_dict(
    native_listing_id: str, recorded_by_account_id: str, outcome: SaleOutcomeSnapshot
) -> dict[str, Any]:
    return {
        "native_listing_id": native_listing_id,
        "recorded_by_account_id": recorded_by_account_id,
        "kind": outcome.kind.value,
        "sold_date": outcome.sold_date.isoformat() if outcome.sold_date is not None else None,
        "achieved_amount": _canonical_decimal_str(outcome.achieved_amount)
        if outcome.achieved_amount is not None
        else None,
        "achieved_currency": outcome.achieved_currency,
        "originating_lead_id": outcome.originating_lead_id.value
        if outcome.originating_lead_id is not None
        else None,
    }


# ---------------------------------------------------------------------------
# Row <-> domain conversion
# ---------------------------------------------------------------------------


def _row_to_revision_record(row: tuple[Any, ...]) -> SaleOutcomeRevisionRecord:
    (
        revision_id,
        native_listing_id,
        publishing_organization_id,
        recorded_by_account_id,
        outcome_kind,
        sold_date,
        achieved_amount,
        achieved_currency,
        originating_lead_id,
        previous_revision_id,
        recorded_at,
    ) = row

    outcome = SaleOutcomeSnapshot(
        kind=SaleOutcomeKind(outcome_kind),
        sold_date=sold_date,
        achieved_amount=Decimal(achieved_amount) if achieved_amount is not None else None,
        achieved_currency=achieved_currency,
        originating_lead_id=LeadId(originating_lead_id)
        if originating_lead_id is not None
        else None,
    )

    return SaleOutcomeRevisionRecord(
        revision_id=SaleOutcomeRevisionId(revision_id),
        native_listing_id=NativeListingId(native_listing_id),
        publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id),
        recorded_by_account_id=AccountId(recorded_by_account_id),
        outcome=outcome,
        previous_revision_id=(
            SaleOutcomeRevisionId(previous_revision_id)
            if previous_revision_id is not None
            else None
        ),
        recorded_at=recorded_at,
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def close_native_listing_as_sold(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
    revision_id: SaleOutcomeRevisionId,
    expected_current_revision_id: SaleOutcomeRevisionId | None,
    outcome: SaleOutcomeSnapshot,
) -> SaleOutcomeWriteResult:
    """Evaluate real SLICE-0041 eligibility + listing-Organization match, then
    durably record *outcome* as a new immutable SaleOutcome revision,
    atomically transitioning ACTIVE -> WITHDRAWN when the listing is
    currently ACTIVE (contract §9).

    Raises SaleOutcomeTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    if not isinstance(revision_id, SaleOutcomeRevisionId):
        raise TypeError(
            f"revision_id must be a SaleOutcomeRevisionId, got {type(revision_id).__name__}"
        )
    if expected_current_revision_id is not None and not isinstance(
        expected_current_revision_id, SaleOutcomeRevisionId
    ):
        raise TypeError(
            "expected_current_revision_id must be a SaleOutcomeRevisionId or None, got "
            f"{type(expected_current_revision_id).__name__}"
        )
    if not isinstance(outcome, SaleOutcomeSnapshot):
        raise TypeError(f"outcome must be a SaleOutcomeSnapshot, got {type(outcome).__name__}")

    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return SaleOutcomeWriteResult(
            status=SaleOutcomeWriteStatus.DENIED, denial_reason=decision.reason
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise SaleOutcomeTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); close_native_listing_as_sold() requires an IDLE "
            "connection so it can safely own and commit its own top-level transaction. Call "
            "conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    content_hash = fingerprint_dict(
        _outcome_envelope_dict(native_listing_id.value, account_id.value, outcome)
    )

    with conn.transaction(), conn.cursor() as cur:
        # Locks the native_listings row for the duration of this
        # transaction, serializing every concurrent outcome write/lifecycle
        # transition for this NativeListingId -- mirrors the FOR UPDATE
        # pattern already accepted for offer-revision/lifecycle writes.
        cur.execute(_SELECT_LISTING_FOR_UPDATE, [native_listing_id.value])
        listing_row = cur.fetchone()
        if listing_row is None:
            return SaleOutcomeWriteResult(status=SaleOutcomeWriteStatus.NATIVE_LISTING_NOT_FOUND)

        listing_organization_id, lifecycle_state_text = listing_row
        if listing_organization_id != candidate_organization.id.value:
            return SaleOutcomeWriteResult(status=SaleOutcomeWriteStatus.CROSS_ORGANIZATION_DENIED)

        lifecycle_state = NativeListingLifecycleState(lifecycle_state_text)
        if lifecycle_state is NativeListingLifecycleState.DRAFT:
            return SaleOutcomeWriteResult(status=SaleOutcomeWriteStatus.DRAFT_NOT_ELIGIBLE)

        cur.execute(_SELECT_HEAD, [native_listing_id.value])
        head_row = cur.fetchone()
        actual_current_id: str | None = head_row[0] if head_row is not None else None

        def _current_wrapped() -> SaleOutcomeRevisionId | None:
            return (
                SaleOutcomeRevisionId(actual_current_id) if actual_current_id is not None else None
            )

        cur.execute(_SELECT_REVISION_BY_ID, [revision_id.value])
        existing = cur.fetchone()
        if existing is not None:
            existing_listing_id, existing_hash = existing
            if existing_listing_id == native_listing_id.value and existing_hash == content_hash:
                # An exact retry never re-transitions lifecycle: the first
                # successful attempt already applied (or correctly skipped)
                # the ACTIVE -> WITHDRAWN transition atomically, so the
                # listing's current lifecycle_state read under this same
                # lock is already the authoritative post-write state.
                return SaleOutcomeWriteResult(
                    status=SaleOutcomeWriteStatus.ALREADY_EXISTS,
                    current_revision_id=_current_wrapped(),
                    resulting_state=lifecycle_state,
                )
            return SaleOutcomeWriteResult(
                status=SaleOutcomeWriteStatus.CONFLICT, current_revision_id=_current_wrapped()
            )

        expected_value = (
            expected_current_revision_id.value if expected_current_revision_id is not None else None
        )
        if expected_value != actual_current_id:
            return SaleOutcomeWriteResult(
                status=SaleOutcomeWriteStatus.CONFLICT, current_revision_id=_current_wrapped()
            )

        if outcome.originating_lead_id is not None:
            lead = fetch_buyer_lead(conn, outcome.originating_lead_id)
            if (
                lead is None
                or lead.native_listing_id != native_listing_id
                or lead.publishing_organization_id != candidate_organization.id
            ):
                return SaleOutcomeWriteResult(status=SaleOutcomeWriteStatus.INVALID_LEAD)

        cur.execute(
            _INSERT_REVISION,
            (
                revision_id.value,
                native_listing_id.value,
                candidate_organization.id.value,
                account_id.value,
                outcome.kind.value,
                outcome.sold_date,
                outcome.achieved_amount,
                outcome.achieved_currency,
                outcome.originating_lead_id.value
                if outcome.originating_lead_id is not None
                else None,
                actual_current_id,
                content_hash,
            ),
        )
        if cur.rowcount == 0:
            # Lost the race against a different NativeListing concurrently
            # claiming this exact (global-PK) revision id -- same-listing
            # writes are fully serialized by the row lock above, so this can
            # never be a match for *our* NativeListing.
            return SaleOutcomeWriteResult(
                status=SaleOutcomeWriteStatus.CONFLICT, current_revision_id=_current_wrapped()
            )

        cur.execute(_UPSERT_HEAD, (native_listing_id.value, revision_id.value))

        transition_id: PublicationTransitionId | None = None
        if lifecycle_state is NativeListingLifecycleState.ACTIVE:
            transition_id = apply_lifecycle_transition_row(
                cur,
                account_id=account_id,
                native_listing_id=native_listing_id,
                publishing_organization_id=candidate_organization.id,
                from_state=NativeListingLifecycleState.ACTIVE,
                to_state=NativeListingLifecycleState.WITHDRAWN,
            )
            resulting_state = NativeListingLifecycleState.WITHDRAWN
        else:
            assert lifecycle_state is NativeListingLifecycleState.WITHDRAWN
            resulting_state = NativeListingLifecycleState.WITHDRAWN

        status = (
            SaleOutcomeWriteStatus.CREATED
            if actual_current_id is None
            else SaleOutcomeWriteStatus.REVISED
        )
        return SaleOutcomeWriteResult(
            status=status,
            current_revision_id=revision_id,
            resulting_state=resulting_state,
            transitioned_to_withdrawn=transition_id is not None,
            transition_id=transition_id,
        )


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_current_sale_outcome(
    conn: Any, native_listing_id: NativeListingId
) -> SaleOutcomeRevisionRecord | None:
    """Exact typed readback of the current SaleOutcome revision for
    *native_listing_id*. Reads the explicit current/head pointer -- never
    `MAX(recorded_at)` or row order. A missing NativeListing/current outcome
    returns `None` rather than inventing a record."""
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_CURRENT_OUTCOME, [native_listing_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_revision_record(row)


def fetch_sale_outcome_revision(
    conn: Any, revision_id: SaleOutcomeRevisionId
) -> SaleOutcomeRevisionRecord | None:
    """Exact typed readback of one immutable SaleOutcome revision by its own
    id, regardless of whether it is still the current head."""
    if not isinstance(revision_id, SaleOutcomeRevisionId):
        raise TypeError(
            f"revision_id must be a SaleOutcomeRevisionId, got {type(revision_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_REVISION_RECORD, [revision_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_revision_record(row)


def list_sale_outcome_revisions(
    conn: Any, native_listing_id: NativeListingId
) -> list[SaleOutcomeRevisionRecord]:
    """Exact typed readback of the immutable SaleOutcome revision history for
    one NativeListing, ordered by `recorded_at` for display/audit
    convenience only."""
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_HISTORY, [native_listing_id.value])
        rows = cur.fetchall()
    return [_row_to_revision_record(row) for row in rows]
