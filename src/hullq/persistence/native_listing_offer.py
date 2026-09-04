"""Durable NativeListing offer-facts persistence — SLICE-0045.

Given an already-persisted, authorized SLICE-0043 `NativeListing`, durably
create and revise the offer state defined by the nine `LISTING_OFFER`
fields in `MARKETPLACE_FIELD_REGISTRY.v0.1`
(`hullq.domain.native_listing_offer.NativeListingOfferSnapshot`), preserving
immutable revision history, exact broker-claim semantics and cross-
Organization isolation.

The real accepted SLICE-0041 evaluator is always called; a caller-supplied
authorization boolean is never accepted. The candidate Organization must
also equal the target NativeListing's persisted `publishing_organization_id`
(SLICE-0043) — eligibility inside one Organization never authorizes editing
another Organization's listing. A denied, cross-Organization or missing-
listing request writes zero revision/head rows.

Current/head state is an explicit database relationship
(`native_listing_offer_heads`), never inferred from `MAX(created_at)` or row
order. A revision write carries an explicit
`expected_current_revision_id` (`None` for the first revision, the exact
current revision id otherwise); a stale expectation fails closed as
`CONFLICT` with zero new current state. A client-supplied revision id that
already exists resolves deterministically: identical immutable content is
`ALREADY_EXISTS`; different content (or a different NativeListing) is
`CONFLICT`. Neither ever silently overwrites or re-promotes a prior
revision.

This module does not persist any `PHYSICAL_BOAT` fact, does not create a
generic marketplace EAV/JSON fact store, and does not implement public
publication, search or a broker workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    AssertionKind,
    BrokerSummaryClaim,
    KnownHistoryNarrativeClaim,
    LocationRegionClaim,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
    VatTaxStatusValue,
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
from hullq.persistence.fingerprint import fingerprint_dict

__all__ = [
    "NativeListingOfferRevisionRecord",
    "NativeListingOfferTransactionOwnershipError",
    "NativeListingOfferWriteResult",
    "NativeListingOfferWriteStatus",
    "fetch_current_native_listing_offer",
    "fetch_native_listing_offer_revision",
    "list_native_listing_offer_revisions",
    "write_native_listing_offer_revision",
]


class NativeListingOfferTransactionOwnershipError(RuntimeError):
    """write_native_listing_offer_revision cannot safely own a top-level transaction on *conn*.

    Mirrors `hullq.persistence.native_listing.NativeListingTransactionOwnershipError`:
    a CREATED/REVISED result must always mean the new current offer revision
    is already durably committed, independent of later caller action. That
    guarantee only holds when *conn* is IDLE (no transaction already open),
    since psycopg's ``conn.transaction()`` otherwise silently degrades to a
    nested SAVEPOINT. Call ``conn.commit()``/``conn.rollback()`` first, or
    pass a freshly opened connection.
    """


class NativeListingOfferWriteStatus(StrEnum):
    """Mechanically distinct write outcomes. Never a bare boolean."""

    CREATED = "created"
    REVISED = "revised"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    DENIED = "denied"
    CROSS_ORGANIZATION_DENIED = "cross_organization_denied"
    NATIVE_LISTING_NOT_FOUND = "native_listing_not_found"


_STATUSES_REQUIRING_CURRENT_REVISION = frozenset(
    {
        NativeListingOfferWriteStatus.CREATED,
        NativeListingOfferWriteStatus.REVISED,
        NativeListingOfferWriteStatus.ALREADY_EXISTS,
    }
)
_STATUSES_FORBIDDING_CURRENT_REVISION = frozenset(
    {
        NativeListingOfferWriteStatus.DENIED,
        NativeListingOfferWriteStatus.CROSS_ORGANIZATION_DENIED,
        NativeListingOfferWriteStatus.NATIVE_LISTING_NOT_FOUND,
    }
)


@dataclass(frozen=True)
class NativeListingOfferWriteResult:
    """Deterministic result of one write_native_listing_offer_revision call.

    `DENIED` always carries the real SLICE-0041 denial reason.
    `CROSS_ORGANIZATION_DENIED` is a distinct, separately fail-closed case:
    the caller is eligible within their own Organization, but that
    Organization does not match the target NativeListing's persisted
    publishing Organization. `current_revision_id` reflects the real durable
    current head of *this* NativeListing after this call (the new revision
    for CREATED/REVISED, the pre-existing current revision for
    ALREADY_EXISTS) and is never populated for a case that wrote nothing /
    never reached the head. `CONFLICT` may or may not carry one: a stale
    `expected_current_revision_id` or a revision-id collision are both
    reported as CONFLICT even when this NativeListing has no current
    revision at all yet (for example, a revision id collision against a
    completely different NativeListing that itself has never been written).
    """

    status: NativeListingOfferWriteStatus
    denial_reason: PublishingEligibilityReason | None = None
    current_revision_id: NativeListingOfferRevisionId | None = None

    def __post_init__(self) -> None:
        if self.status is NativeListingOfferWriteStatus.DENIED:
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


@dataclass(frozen=True)
class NativeListingOfferRevisionRecord:
    """Exact typed readback of one persisted NativeListing offer revision.

    `previous_revision_id` is the exact durable current head that was
    validated (against `expected_current_revision_id`) immediately before
    this revision was inserted — `None` for a NativeListing's first
    revision. It is set once at insertion time and never recomputed from
    timestamps or row order; PostgreSQL enforces that a non-null value
    always references a revision belonging to this same NativeListing
    (see the composite foreign key in the SLICE-0045 migration).
    """

    revision_id: NativeListingOfferRevisionId
    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    recorded_by_account_id: AccountId
    offer: NativeListingOfferSnapshot
    previous_revision_id: NativeListingOfferRevisionId | None
    recorded_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SELECT_LISTING_ORG_FOR_UPDATE = (
    "SELECT publishing_organization_id FROM native_listings WHERE native_listing_id = %s FOR UPDATE"
)

_SELECT_HEAD = (
    "SELECT current_offer_revision_id FROM native_listing_offer_heads WHERE native_listing_id = %s"
)

_SELECT_REVISION_BY_ID = (
    "SELECT native_listing_id, content_hash FROM native_listing_offer_revisions "
    "WHERE offer_revision_id = %s"
)

_INSERT_REVISION = """
INSERT INTO native_listing_offer_revisions (
    offer_revision_id, native_listing_id, publishing_organization_id,
    recorded_by_account_id, asking_price_mode, asking_price_amount, currency,
    location_country, location_region_assertion_kind, location_region_value,
    broker_summary_assertion_kind, broker_summary_value, broker_description,
    known_history_narrative_assertion_kind, known_history_narrative_value,
    vat_tax_status_assertion_kind, vat_tax_status_value, previous_offer_revision_id,
    content_hash
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (offer_revision_id) DO NOTHING
"""

_UPSERT_HEAD = """
INSERT INTO native_listing_offer_heads (native_listing_id, current_offer_revision_id)
VALUES (%s, %s)
ON CONFLICT (native_listing_id)
DO UPDATE SET current_offer_revision_id = EXCLUDED.current_offer_revision_id,
              updated_at = NOW()
"""

_REVISION_COLUMNS = """
    r.offer_revision_id, r.native_listing_id, r.publishing_organization_id,
    r.recorded_by_account_id, r.asking_price_mode, r.asking_price_amount, r.currency,
    r.location_country, r.location_region_assertion_kind, r.location_region_value,
    r.broker_summary_assertion_kind, r.broker_summary_value, r.broker_description,
    r.known_history_narrative_assertion_kind, r.known_history_narrative_value,
    r.vat_tax_status_assertion_kind, r.vat_tax_status_value, r.previous_offer_revision_id,
    r.recorded_at
"""

_SELECT_CURRENT_OFFER = f"""
SELECT {_REVISION_COLUMNS}
FROM native_listing_offer_heads h
JOIN native_listing_offer_revisions r ON r.offer_revision_id = h.current_offer_revision_id
WHERE h.native_listing_id = %s
"""

_SELECT_REVISION_RECORD = f"""
SELECT {_REVISION_COLUMNS}
FROM native_listing_offer_revisions r
WHERE r.offer_revision_id = %s
"""

_SELECT_HISTORY = f"""
SELECT {_REVISION_COLUMNS}
FROM native_listing_offer_revisions r
WHERE r.native_listing_id = %s
ORDER BY r.recorded_at ASC, r.offer_revision_id ASC
"""


# ---------------------------------------------------------------------------
# Fingerprint envelope
# ---------------------------------------------------------------------------


def _claim_dict(
    claim: LocationRegionClaim
    | BrokerSummaryClaim
    | KnownHistoryNarrativeClaim
    | VatTaxStatusClaim
    | None,
) -> dict[str, Any] | None:
    if claim is None:
        return None
    value = claim.value.value if isinstance(claim.value, VatTaxStatusValue) else claim.value
    return {"assertion_kind": claim.assertion_kind.value, "value": value}


def _canonical_decimal_str(value: Decimal) -> str:
    """Stable string form for a finite Decimal, independent of the active
    Decimal context and lossless for every accepted finite value.

    `Decimal('125000.00')`, `Decimal('125000')` and `Decimal('1.25E+5')`
    all represent the same monetary value and must fingerprint identically
    so an equivalent retry resolves as ALREADY_EXISTS rather than a false
    CONFLICT -- but `Decimal.normalize()` (used by an earlier version of
    this function) implicitly rounds to the *ambient* Decimal context's
    precision (28 significant digits by default) before reducing the
    representation. Two distinct finite values with more than 28
    significant digits differing only past that many digits would
    therefore normalize to the same rounded result and be misdetected as
    the same revision content -- silently accepting a genuinely different
    price as ALREADY_EXISTS instead of CONFLICT.

    `Decimal.as_tuple()` instead returns the exact (sign, digit, exponent)
    representation as originally parsed/constructed, with no context
    rounding applied. Stripping only trailing coefficient zeros (adjusting
    the exponent to compensate, exactly as `normalize()` does for that
    part) canonicalizes trailing-zero/exponent notation differences while
    never discarding a significant digit, so the result is both lossless
    and independent of `getcontext().prec`.
    """
    sign, digits_tuple, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        # Non-finite (Infinity/-Infinity/NaN) values are rejected by
        # NativeListingOfferSnapshot before persistence ever calls this;
        # this is an unreachable defensive guard, not a normal code path.
        raise ValueError(f"asking_price_amount must be finite, got {value!r}")
    digits = list(digits_tuple)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    if digits == [0]:
        exponent = 0
    coefficient = "".join(str(d) for d in digits)
    sign_str = "-" if sign else ""
    return f"{sign_str}{coefficient}E{exponent}"


def _offer_envelope_dict(
    native_listing_id: str, recorded_by_account_id: str, offer: NativeListingOfferSnapshot
) -> dict[str, Any]:
    return {
        "native_listing_id": native_listing_id,
        "recorded_by_account_id": recorded_by_account_id,
        "asking_price_mode": offer.asking_price_mode.value,
        "asking_price_amount": _canonical_decimal_str(offer.asking_price_amount)
        if offer.asking_price_amount is not None
        else None,
        "currency": offer.currency,
        "location_country": offer.location_country,
        "broker_description": offer.broker_description,
        "location_region": _claim_dict(offer.location_region),
        "broker_summary": _claim_dict(offer.broker_summary),
        "known_history_narrative": _claim_dict(offer.known_history_narrative),
        "vat_tax_status_claim": _claim_dict(offer.vat_tax_status_claim),
    }


# ---------------------------------------------------------------------------
# Row <-> domain conversion
# ---------------------------------------------------------------------------


def _optional_claim(
    kind_text: str | None,
    value_text: str | None,
    ctor: type[LocationRegionClaim] | type[BrokerSummaryClaim] | type[KnownHistoryNarrativeClaim],
) -> Any:
    if kind_text is None:
        return None
    return ctor(assertion_kind=AssertionKind(kind_text), value=value_text)


def _row_to_revision_record(row: tuple[Any, ...]) -> NativeListingOfferRevisionRecord:
    (
        revision_id,
        native_listing_id,
        publishing_organization_id,
        recorded_by_account_id,
        asking_price_mode,
        asking_price_amount,
        currency,
        location_country,
        location_region_kind,
        location_region_value,
        broker_summary_kind,
        broker_summary_value,
        broker_description,
        known_history_kind,
        known_history_value,
        vat_kind,
        vat_value,
        previous_offer_revision_id,
        recorded_at,
    ) = row

    vat_claim: VatTaxStatusClaim | None = None
    if vat_kind is not None:
        vat_claim = VatTaxStatusClaim(
            assertion_kind=AssertionKind(vat_kind),
            value=VatTaxStatusValue(vat_value) if vat_value is not None else None,
        )

    offer = NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode(asking_price_mode),
        location_country=location_country,
        broker_description=broker_description,
        asking_price_amount=Decimal(asking_price_amount)
        if asking_price_amount is not None
        else None,
        currency=currency,
        location_region=_optional_claim(
            location_region_kind, location_region_value, LocationRegionClaim
        ),
        broker_summary=_optional_claim(
            broker_summary_kind, broker_summary_value, BrokerSummaryClaim
        ),
        known_history_narrative=_optional_claim(
            known_history_kind, known_history_value, KnownHistoryNarrativeClaim
        ),
        vat_tax_status_claim=vat_claim,
    )

    return NativeListingOfferRevisionRecord(
        revision_id=NativeListingOfferRevisionId(revision_id),
        native_listing_id=NativeListingId(native_listing_id),
        publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id),
        recorded_by_account_id=AccountId(recorded_by_account_id),
        offer=offer,
        previous_revision_id=(
            NativeListingOfferRevisionId(previous_offer_revision_id)
            if previous_offer_revision_id is not None
            else None
        ),
        recorded_at=recorded_at,
    )


def _claim_columns(
    claim: LocationRegionClaim | BrokerSummaryClaim | KnownHistoryNarrativeClaim | None,
) -> tuple[str | None, str | None]:
    if claim is None:
        return None, None
    return claim.assertion_kind.value, claim.value


def _vat_columns(claim: VatTaxStatusClaim | None) -> tuple[str | None, str | None]:
    if claim is None:
        return None, None
    value = claim.value.value if claim.value is not None else None
    return claim.assertion_kind.value, value


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_native_listing_offer_revision(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
    revision_id: NativeListingOfferRevisionId,
    expected_current_revision_id: NativeListingOfferRevisionId | None,
    offer: NativeListingOfferSnapshot,
) -> NativeListingOfferWriteResult:
    """Evaluate real SLICE-0041 eligibility + listing-Organization match, then
    durably write *offer* as a new immutable revision iff ALLOWED.

    Raises NativeListingOfferTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    if not isinstance(revision_id, NativeListingOfferRevisionId):
        raise TypeError(
            f"revision_id must be a NativeListingOfferRevisionId, got {type(revision_id).__name__}"
        )
    if expected_current_revision_id is not None and not isinstance(
        expected_current_revision_id, NativeListingOfferRevisionId
    ):
        raise TypeError(
            "expected_current_revision_id must be a NativeListingOfferRevisionId or None, got "
            f"{type(expected_current_revision_id).__name__}"
        )
    if not isinstance(offer, NativeListingOfferSnapshot):
        raise TypeError(f"offer must be a NativeListingOfferSnapshot, got {type(offer).__name__}")

    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return NativeListingOfferWriteResult(
            status=NativeListingOfferWriteStatus.DENIED, denial_reason=decision.reason
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise NativeListingOfferTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); write_native_listing_offer_revision() requires "
            "an IDLE connection so it can safely own and commit its own top-level transaction. "
            "Call conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    content_hash = fingerprint_dict(
        _offer_envelope_dict(native_listing_id.value, account_id.value, offer)
    )

    with conn.transaction(), conn.cursor() as cur:
        # Locks the (already-existing) native_listings row for the duration
        # of this transaction, serializing all concurrent offer writes for
        # this NativeListingId. Without this, two concurrent first-time
        # writers could each observe "no head row yet" and both proceed to
        # INSERT a distinct first revision -- a lost-update race, since
        # native_listing_offer_heads has no row to lock via FOR UPDATE
        # before it exists.
        cur.execute(_SELECT_LISTING_ORG_FOR_UPDATE, [native_listing_id.value])
        listing_row = cur.fetchone()
        if listing_row is None:
            return NativeListingOfferWriteResult(
                status=NativeListingOfferWriteStatus.NATIVE_LISTING_NOT_FOUND
            )

        listing_organization_id = listing_row[0]
        if listing_organization_id != candidate_organization.id.value:
            return NativeListingOfferWriteResult(
                status=NativeListingOfferWriteStatus.CROSS_ORGANIZATION_DENIED
            )

        cur.execute(_SELECT_HEAD, [native_listing_id.value])
        head_row = cur.fetchone()
        actual_current_id: str | None = head_row[0] if head_row is not None else None

        def _current_wrapped() -> NativeListingOfferRevisionId | None:
            return (
                NativeListingOfferRevisionId(actual_current_id)
                if actual_current_id is not None
                else None
            )

        cur.execute(_SELECT_REVISION_BY_ID, [revision_id.value])
        existing = cur.fetchone()
        if existing is not None:
            existing_listing_id, existing_hash = existing
            if existing_listing_id == native_listing_id.value and existing_hash == content_hash:
                return NativeListingOfferWriteResult(
                    status=NativeListingOfferWriteStatus.ALREADY_EXISTS,
                    current_revision_id=_current_wrapped(),
                )
            return NativeListingOfferWriteResult(
                status=NativeListingOfferWriteStatus.CONFLICT,
                current_revision_id=_current_wrapped(),
            )

        expected_value = (
            expected_current_revision_id.value if expected_current_revision_id is not None else None
        )
        if expected_value != actual_current_id:
            return NativeListingOfferWriteResult(
                status=NativeListingOfferWriteStatus.CONFLICT,
                current_revision_id=_current_wrapped(),
            )

        location_region_kind, location_region_value = _claim_columns(offer.location_region)
        broker_summary_kind, broker_summary_value = _claim_columns(offer.broker_summary)
        known_history_kind, known_history_value = _claim_columns(offer.known_history_narrative)
        vat_kind, vat_value = _vat_columns(offer.vat_tax_status_claim)

        # ON CONFLICT DO NOTHING on offer_revision_id (a global PRIMARY KEY,
        # not scoped to native_listing_id) closes the race window against a
        # *different* NativeListing concurrently claiming this exact
        # revision id between the pre-check SELECT above and this INSERT --
        # the FOR UPDATE lock on native_listings only serializes writers for
        # *this* NativeListingId, so a same-listing collision is already
        # impossible, but a cross-listing one is not, without this guard.
        # previous_offer_revision_id is exactly the current head validated
        # above (None for a first revision), fixed permanently at insertion
        # time -- never recomputed from timestamps/row order.
        cur.execute(
            _INSERT_REVISION,
            (
                revision_id.value,
                native_listing_id.value,
                candidate_organization.id.value,
                account_id.value,
                offer.asking_price_mode.value,
                offer.asking_price_amount,
                offer.currency,
                offer.location_country,
                location_region_kind,
                location_region_value,
                broker_summary_kind,
                broker_summary_value,
                offer.broker_description,
                known_history_kind,
                known_history_value,
                vat_kind,
                vat_value,
                actual_current_id,
                content_hash,
            ),
        )
        if cur.rowcount == 0:
            # Lost the race: a different NativeListing committed this exact
            # offer_revision_id after our pre-check but before our INSERT.
            # This can never be a match for *our* NativeListing (same-listing
            # writes are fully serialized by the row lock above), so it is
            # always a CONFLICT, never ALREADY_EXISTS -- and our own head is
            # untouched.
            return NativeListingOfferWriteResult(
                status=NativeListingOfferWriteStatus.CONFLICT,
                current_revision_id=_current_wrapped(),
            )

        cur.execute(_UPSERT_HEAD, (native_listing_id.value, revision_id.value))

        status = (
            NativeListingOfferWriteStatus.CREATED
            if actual_current_id is None
            else NativeListingOfferWriteStatus.REVISED
        )
        return NativeListingOfferWriteResult(status=status, current_revision_id=revision_id)


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_current_native_listing_offer(
    conn: Any, native_listing_id: NativeListingId
) -> NativeListingOfferRevisionRecord | None:
    """Exact typed readback of the current offer revision for *native_listing_id*.

    Reads the explicit current/head pointer — never `MAX(recorded_at)` or row
    order. A missing NativeListing/current offer returns None rather than
    inventing a record.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_CURRENT_OFFER, [native_listing_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_revision_record(row)


def fetch_native_listing_offer_revision(
    conn: Any, revision_id: NativeListingOfferRevisionId
) -> NativeListingOfferRevisionRecord | None:
    """Exact typed readback of one immutable offer revision by its own id.

    Returns the revision regardless of whether it is still the current head —
    used to prove prior revisions remain retained/unchanged after a later
    revision supersedes them.
    """
    if not isinstance(revision_id, NativeListingOfferRevisionId):
        raise TypeError(
            f"revision_id must be a NativeListingOfferRevisionId, got {type(revision_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_REVISION_RECORD, [revision_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_revision_record(row)


def list_native_listing_offer_revisions(
    conn: Any, native_listing_id: NativeListingId
) -> list[NativeListingOfferRevisionRecord]:
    """Exact typed readback of the immutable revision history for one NativeListing.

    Ordered by recorded_at for display/audit convenience only; which
    revision is *current* is never inferred from this ordering — use
    `fetch_current_native_listing_offer` for that.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_HISTORY, [native_listing_id.value])
        rows = cur.fetchall()
    return [_row_to_revision_record(row) for row in rows]
