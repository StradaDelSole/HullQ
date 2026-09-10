"""Durable PhysicalBoat buyer-critical claim persistence — SLICE-0050.

Given an already-persisted, authorized SLICE-0043/0046/0047 NativeListing ->
MarketEpisode -> PhysicalBoat chain, durably create and revise the bounded
seven-field `PhysicalBoat` claim snapshot
(`hullq.domain.physical_boat_claims.PhysicalBoatClaimSnapshot`), preserving
immutable revision history, exact broker-claim semantics and cross-
Organization isolation -- mirroring
`hullq.persistence.native_listing_offer.write_native_listing_offer_revision`
field-for-field in its authorization/idempotency/conflict/concurrency shape.

The write entry point is a `NativeListingId`, not a `PhysicalBoatId`
directly (SLICE-0050 §6): the claim authority is about the concrete
PhysicalBoat, but 0050 uses the existing NativeListing as the authorization/
context entry point. This module resolves NativeListing -> MarketEpisode ->
PhysicalBoat itself and fails closed as `CHAIN_INCOMPLETE` when any link is
missing, before ever touching claim history. The real accepted SLICE-0041
evaluator is always called; a caller-supplied authorization boolean is never
accepted. The candidate Organization must also equal the target
NativeListing's persisted `publishing_organization_id` -- eligibility inside
one Organization never authorizes writing another Organization's claims
about a PhysicalBoat merely because both reference it.

Current/head state is durable and explicit per `(PhysicalBoatId,
claiming MarketplaceOrganizationId)` (`physical_boat_claim_heads`), never
inferred from `MAX(recorded_at)` or row order. A revision write carries an
explicit `expected_current_revision_id` (`None` for the first revision for
that pair, the exact current revision id otherwise); a stale expectation
fails closed as `CONFLICT` with zero new current state. A client-supplied
revision id that already exists resolves deterministically against the
*complete* immutable envelope -- same PhysicalBoat, same claiming
Organization, same recorded predecessor (`previous_claim_revision_id`, fixed
at that revision's own insertion time -- not the pair's possibly-since-
advanced current head) and identical seven-field content is `ALREADY_EXISTS`;
any difference, including a different supplied predecessor for the same
revision id, is `CONFLICT` (SLICE-0050 §7/§7.3). Neither ever silently
overwrites or re-promotes a prior revision, and one Organization's claims
about a PhysicalBoat never supersede a different Organization's claims about
the same PhysicalBoat (SLICE-0050 §9).

Claim recording is not conditioned on NativeListing lifecycle state: an
authorized owning publisher may supply/correct claims while its listing is
DRAFT, ACTIVE or later non-public.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import NativeListingId, PhysicalBoatId
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    LoaLengthClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    RudderConfiguration,
    RudderConfigurationClaim,
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
    "PhysicalBoatClaimRevisionRecord",
    "PhysicalBoatClaimTransactionOwnershipError",
    "PhysicalBoatClaimWriteResult",
    "PhysicalBoatClaimWriteStatus",
    "fetch_current_physical_boat_claim",
    "fetch_physical_boat_claim_revision",
    "list_physical_boat_claim_revisions",
    "write_physical_boat_claim_revision",
]


class PhysicalBoatClaimTransactionOwnershipError(RuntimeError):
    """write_physical_boat_claim_revision cannot safely own a top-level transaction on *conn*.

    Mirrors `hullq.persistence.native_listing_offer.NativeListingOfferTransactionOwnershipError`:
    a CREATED/REVISED result must always mean the new current claim revision
    is already durably committed, independent of later caller action. That
    guarantee only holds when *conn* is IDLE (no transaction already open),
    since psycopg's ``conn.transaction()`` otherwise silently degrades to a
    nested SAVEPOINT. Call ``conn.commit()``/``conn.rollback()`` first, or
    pass a freshly opened connection.
    """


class PhysicalBoatClaimWriteStatus(StrEnum):
    """Mechanically distinct write outcomes. Never a bare boolean."""

    CREATED = "created"
    REVISED = "revised"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    DENIED = "denied"
    CROSS_ORGANIZATION_DENIED = "cross_organization_denied"
    NATIVE_LISTING_NOT_FOUND = "native_listing_not_found"
    CHAIN_INCOMPLETE = "chain_incomplete"


_STATUSES_REQUIRING_CURRENT_REVISION = frozenset(
    {
        PhysicalBoatClaimWriteStatus.CREATED,
        PhysicalBoatClaimWriteStatus.REVISED,
        PhysicalBoatClaimWriteStatus.ALREADY_EXISTS,
    }
)
_STATUSES_FORBIDDING_CURRENT_REVISION = frozenset(
    {
        PhysicalBoatClaimWriteStatus.DENIED,
        PhysicalBoatClaimWriteStatus.CROSS_ORGANIZATION_DENIED,
        PhysicalBoatClaimWriteStatus.NATIVE_LISTING_NOT_FOUND,
        PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE,
    }
)


@dataclass(frozen=True)
class PhysicalBoatClaimWriteResult:
    """Deterministic result of one write_physical_boat_claim_revision call.

    `DENIED` always carries the real SLICE-0041 denial reason.
    `CROSS_ORGANIZATION_DENIED` is separate and fail-closed: the caller is
    eligible within their own Organization, but that Organization does not
    match the target NativeListing's persisted publishing Organization.
    `current_revision_id` reflects the real durable current head of this
    `(PhysicalBoat, Organization)` pair after this call and is never
    populated for a case that wrote nothing / never reached the head.
    """

    status: PhysicalBoatClaimWriteStatus
    denial_reason: PublishingEligibilityReason | None = None
    current_revision_id: PhysicalBoatClaimRevisionId | None = None

    def __post_init__(self) -> None:
        if self.status is PhysicalBoatClaimWriteStatus.DENIED:
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
class PhysicalBoatClaimRevisionRecord:
    """Exact typed readback of one persisted PhysicalBoat claim revision.

    `previous_revision_id` is the exact durable current head (for this same
    `(PhysicalBoatId, claiming_organization_id)` pair) that was validated
    immediately before this revision was inserted -- `None` for that pair's
    first revision.
    """

    revision_id: PhysicalBoatClaimRevisionId
    physical_boat_id: PhysicalBoatId
    claiming_organization_id: MarketplaceOrganizationId
    recorded_by_account_id: AccountId
    claims: PhysicalBoatClaimSnapshot
    previous_revision_id: PhysicalBoatClaimRevisionId | None
    recorded_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SELECT_LISTING_FOR_UPDATE = (
    "SELECT publishing_organization_id, market_episode_id "
    "FROM native_listings WHERE native_listing_id = %s FOR UPDATE"
)

_SELECT_MARKET_EPISODE_PHYSICAL_BOAT = (
    "SELECT physical_boat_id FROM market_episodes WHERE market_episode_id = %s"
)

_SELECT_AND_LOCK_PHYSICAL_BOAT = (
    "SELECT physical_boat_id FROM physical_boats WHERE physical_boat_id = %s FOR UPDATE"
)

_SELECT_HEAD = (
    "SELECT current_claim_revision_id FROM physical_boat_claim_heads "
    "WHERE physical_boat_id = %s AND claiming_organization_id = %s"
)

_SELECT_REVISION_BY_ID = (
    "SELECT physical_boat_id, claiming_organization_id, previous_claim_revision_id, content_hash "
    "FROM physical_boat_claim_revisions WHERE claim_revision_id = %s"
)

_INSERT_REVISION = """
INSERT INTO physical_boat_claim_revisions (
    claim_revision_id, physical_boat_id, claiming_organization_id,
    recorded_by_account_id, marketed_brand_claim, model_designation_claim,
    build_year_assertion_kind, build_year_value,
    loa_length_assertion_kind, loa_length_value,
    draft_assertion_kind, draft_value,
    keel_configuration_assertion_kind, keel_configuration_value,
    rudder_configuration_assertion_kind, rudder_configuration_value,
    previous_claim_revision_id, content_hash
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (claim_revision_id) DO NOTHING
"""

_UPSERT_HEAD = """
INSERT INTO physical_boat_claim_heads (
    physical_boat_id, claiming_organization_id, current_claim_revision_id
) VALUES (%s, %s, %s)
ON CONFLICT (physical_boat_id, claiming_organization_id)
DO UPDATE SET current_claim_revision_id = EXCLUDED.current_claim_revision_id,
              updated_at = NOW()
"""

_REVISION_COLUMNS = """
    r.claim_revision_id, r.physical_boat_id, r.claiming_organization_id,
    r.recorded_by_account_id, r.marketed_brand_claim, r.model_designation_claim,
    r.build_year_assertion_kind, r.build_year_value,
    r.loa_length_assertion_kind, r.loa_length_value,
    r.draft_assertion_kind, r.draft_value,
    r.keel_configuration_assertion_kind, r.keel_configuration_value,
    r.rudder_configuration_assertion_kind, r.rudder_configuration_value,
    r.previous_claim_revision_id, r.recorded_at
"""

_SELECT_CURRENT_CLAIM = f"""
SELECT {_REVISION_COLUMNS}
FROM physical_boat_claim_heads h
JOIN physical_boat_claim_revisions r ON r.claim_revision_id = h.current_claim_revision_id
WHERE h.physical_boat_id = %s AND h.claiming_organization_id = %s
"""

_SELECT_REVISION_RECORD = f"""
SELECT {_REVISION_COLUMNS}
FROM physical_boat_claim_revisions r
WHERE r.claim_revision_id = %s
"""

_SELECT_HISTORY = f"""
SELECT {_REVISION_COLUMNS}
FROM physical_boat_claim_revisions r
WHERE r.physical_boat_id = %s AND r.claiming_organization_id = %s
ORDER BY r.recorded_at ASC, r.claim_revision_id ASC
"""


# ---------------------------------------------------------------------------
# Fingerprint envelope
# ---------------------------------------------------------------------------


def _canonical_decimal_str(value: Decimal) -> str:
    """Stable, context-precision-independent string form for a finite Decimal.

    Copied from `hullq.persistence.native_listing_offer._canonical_decimal_str`
    (see that function's docstring for the full rationale): `normalize()`
    implicitly rounds to the ambient Decimal context's precision before
    reducing the representation, which could misdetect two genuinely
    different high-precision values as the same fingerprint content. Using
    `as_tuple()` and stripping only trailing coefficient zeros is both
    lossless and context-independent.
    """
    sign, digits_tuple, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        # Non-finite (Infinity/-Infinity/NaN) values are rejected by
        # LoaLengthClaim/DraftClaim before persistence ever calls this;
        # this is an unreachable defensive guard, not a normal code path.
        raise ValueError(f"decimal value must be finite, got {value!r}")
    digits = list(digits_tuple)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    if digits == [0]:
        exponent = 0
    coefficient = "".join(str(d) for d in digits)
    sign_str = "-" if sign else ""
    return f"{sign_str}{coefficient}E{exponent}"


def _optional_claim_dict(
    claim: LoaLengthClaim
    | DraftClaim
    | KeelConfigurationClaim
    | RudderConfigurationClaim
    | BuildYearClaim
    | None,
) -> dict[str, Any] | None:
    if claim is None:
        return None
    raw_value = claim.value
    if isinstance(raw_value, Decimal):
        value: Any = _canonical_decimal_str(raw_value)
    elif isinstance(raw_value, (KeelConfiguration, RudderConfiguration)):
        value = raw_value.value
    else:
        value = raw_value
    return {"assertion_kind": claim.assertion_kind.value, "value": value}


def _claim_envelope_dict(
    physical_boat_id: str,
    claiming_organization_id: str,
    recorded_by_account_id: str,
    claims: PhysicalBoatClaimSnapshot,
) -> dict[str, Any]:
    return {
        "physical_boat_id": physical_boat_id,
        "claiming_organization_id": claiming_organization_id,
        "recorded_by_account_id": recorded_by_account_id,
        "marketed_brand_claim": claims.marketed_brand_claim,
        "model_designation_claim": claims.model_designation_claim,
        "build_year": _optional_claim_dict(claims.build_year),
        "loa_length": _optional_claim_dict(claims.loa_length),
        "draft": _optional_claim_dict(claims.draft),
        "keel_configuration": _optional_claim_dict(claims.keel_configuration),
        "rudder_configuration": _optional_claim_dict(claims.rudder_configuration),
    }


# ---------------------------------------------------------------------------
# Row <-> domain conversion
# ---------------------------------------------------------------------------


def _row_to_revision_record(row: tuple[Any, ...]) -> PhysicalBoatClaimRevisionRecord:
    (
        revision_id,
        physical_boat_id,
        claiming_organization_id,
        recorded_by_account_id,
        marketed_brand_claim,
        model_designation_claim,
        build_year_kind,
        build_year_value,
        loa_length_kind,
        loa_length_value,
        draft_kind,
        draft_value,
        keel_kind,
        keel_value,
        rudder_kind,
        rudder_value,
        previous_revision_id,
        recorded_at,
    ) = row

    loa_length: LoaLengthClaim | None = None
    if loa_length_kind is not None:
        loa_length = LoaLengthClaim(
            assertion_kind=AssertionKind(loa_length_kind),
            value=Decimal(loa_length_value) if loa_length_value is not None else None,
        )
    draft: DraftClaim | None = None
    if draft_kind is not None:
        draft = DraftClaim(
            assertion_kind=AssertionKind(draft_kind),
            value=Decimal(draft_value) if draft_value is not None else None,
        )
    keel_configuration: KeelConfigurationClaim | None = None
    if keel_kind is not None:
        keel_configuration = KeelConfigurationClaim(
            assertion_kind=AssertionKind(keel_kind),
            value=KeelConfiguration(keel_value) if keel_value is not None else None,
        )
    rudder_configuration: RudderConfigurationClaim | None = None
    if rudder_kind is not None:
        rudder_configuration = RudderConfigurationClaim(
            assertion_kind=AssertionKind(rudder_kind),
            value=RudderConfiguration(rudder_value) if rudder_value is not None else None,
        )

    claims = PhysicalBoatClaimSnapshot(
        marketed_brand_claim=marketed_brand_claim,
        model_designation_claim=model_designation_claim,
        build_year=BuildYearClaim(
            assertion_kind=AssertionKind(build_year_kind),
            value=build_year_value,
        ),
        loa_length=loa_length,
        draft=draft,
        keel_configuration=keel_configuration,
        rudder_configuration=rudder_configuration,
    )

    return PhysicalBoatClaimRevisionRecord(
        revision_id=PhysicalBoatClaimRevisionId(revision_id),
        physical_boat_id=PhysicalBoatId(physical_boat_id),
        claiming_organization_id=MarketplaceOrganizationId(claiming_organization_id),
        recorded_by_account_id=AccountId(recorded_by_account_id),
        claims=claims,
        previous_revision_id=(
            PhysicalBoatClaimRevisionId(previous_revision_id)
            if previous_revision_id is not None
            else None
        ),
        recorded_at=recorded_at,
    )


def _optional_claim_columns(
    claim: BuildYearClaim
    | LoaLengthClaim
    | DraftClaim
    | KeelConfigurationClaim
    | RudderConfigurationClaim
    | None,
) -> tuple[str | None, Any]:
    if claim is None:
        return None, None
    raw_value = claim.value
    if isinstance(raw_value, (KeelConfiguration, RudderConfiguration)):
        return claim.assertion_kind.value, raw_value.value
    return claim.assertion_kind.value, raw_value


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_physical_boat_claim_revision(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
    revision_id: PhysicalBoatClaimRevisionId,
    expected_current_revision_id: PhysicalBoatClaimRevisionId | None,
    claims: PhysicalBoatClaimSnapshot,
) -> PhysicalBoatClaimWriteResult:
    """Evaluate real SLICE-0041 eligibility + listing-Organization match, then
    resolve NativeListing -> MarketEpisode -> PhysicalBoat and durably write
    *claims* as a new immutable revision iff every step succeeds.

    Raises PhysicalBoatClaimTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    if not isinstance(revision_id, PhysicalBoatClaimRevisionId):
        raise TypeError(
            f"revision_id must be a PhysicalBoatClaimRevisionId, got {type(revision_id).__name__}"
        )
    if expected_current_revision_id is not None and not isinstance(
        expected_current_revision_id, PhysicalBoatClaimRevisionId
    ):
        raise TypeError(
            "expected_current_revision_id must be a PhysicalBoatClaimRevisionId or None, got "
            f"{type(expected_current_revision_id).__name__}"
        )
    if not isinstance(claims, PhysicalBoatClaimSnapshot):
        raise TypeError(f"claims must be a PhysicalBoatClaimSnapshot, got {type(claims).__name__}")

    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return PhysicalBoatClaimWriteResult(
            status=PhysicalBoatClaimWriteStatus.DENIED, denial_reason=decision.reason
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise PhysicalBoatClaimTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); write_physical_boat_claim_revision() requires "
            "an IDLE connection so it can safely own and commit its own top-level transaction. "
            "Call conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    with conn.transaction(), conn.cursor() as cur:
        # Locks the (already-existing) native_listings row, mirroring
        # write_native_listing_offer_revision's pattern.
        cur.execute(_SELECT_LISTING_FOR_UPDATE, [native_listing_id.value])
        listing_row = cur.fetchone()
        if listing_row is None:
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.NATIVE_LISTING_NOT_FOUND
            )

        listing_organization_id, market_episode_id_value = listing_row
        if listing_organization_id != candidate_organization.id.value:
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.CROSS_ORGANIZATION_DENIED
            )

        if market_episode_id_value is None:
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE
            )

        cur.execute(_SELECT_MARKET_EPISODE_PHYSICAL_BOAT, [market_episode_id_value])
        market_episode_row = cur.fetchone()
        if market_episode_row is None:
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE
            )
        physical_boat_id_value = market_episode_row[0]

        # Locks the target physical_boats row for the duration of this
        # transaction, serializing every concurrent claim write for this
        # PhysicalBoatId (across every claiming Organization) -- mirrors the
        # FOR UPDATE row-lock pattern already accepted for offer-revision
        # and lifecycle-transition writes. Also doubles as the PhysicalBoat
        # existence check required by the chain-completeness predicate.
        cur.execute(_SELECT_AND_LOCK_PHYSICAL_BOAT, [physical_boat_id_value])
        if cur.fetchone() is None:
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE
            )

        content_hash = fingerprint_dict(
            _claim_envelope_dict(
                physical_boat_id_value,
                candidate_organization.id.value,
                account_id.value,
                claims,
            )
        )

        cur.execute(_SELECT_HEAD, [physical_boat_id_value, candidate_organization.id.value])
        head_row = cur.fetchone()
        actual_current_id: str | None = head_row[0] if head_row is not None else None

        def _current_wrapped() -> PhysicalBoatClaimRevisionId | None:
            return (
                PhysicalBoatClaimRevisionId(actual_current_id)
                if actual_current_id is not None
                else None
            )

        expected_value = (
            expected_current_revision_id.value if expected_current_revision_id is not None else None
        )

        cur.execute(_SELECT_REVISION_BY_ID, [revision_id.value])
        existing = cur.fetchone()
        if existing is not None:
            (
                existing_physical_boat_id,
                existing_organization_id,
                existing_previous_revision_id,
                existing_hash,
            ) = existing
            # An exact retry must match on the full immutable envelope,
            # which includes the predecessor/supersession identity this
            # revision was recorded against (SLICE-0050 §7/§7.3) -- not
            # content_hash alone. Comparing against the *stored*
            # previous_claim_revision_id (fixed permanently at this
            # revision's own insertion time), rather than against
            # actual_current_id (the pair's *current* head, which may have
            # since advanced past this revision), is what lets a genuine
            # retry of an old, since-superseded revision still resolve
            # ALREADY_EXISTS: only a retry supplying a *different*
            # predecessor than what was originally recorded is a real
            # conflict.
            if (
                existing_physical_boat_id == physical_boat_id_value
                and existing_organization_id == candidate_organization.id.value
                and existing_previous_revision_id == expected_value
                and existing_hash == content_hash
            ):
                return PhysicalBoatClaimWriteResult(
                    status=PhysicalBoatClaimWriteStatus.ALREADY_EXISTS,
                    current_revision_id=_current_wrapped(),
                )
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.CONFLICT,
                current_revision_id=_current_wrapped(),
            )

        if expected_value != actual_current_id:
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.CONFLICT,
                current_revision_id=_current_wrapped(),
            )

        build_year_kind, build_year_value = _optional_claim_columns(claims.build_year)
        loa_length_kind, loa_length_value = _optional_claim_columns(claims.loa_length)
        draft_kind, draft_value = _optional_claim_columns(claims.draft)
        keel_kind, keel_value = _optional_claim_columns(claims.keel_configuration)
        rudder_kind, rudder_value = _optional_claim_columns(claims.rudder_configuration)

        # ON CONFLICT DO NOTHING on claim_revision_id (a global PRIMARY KEY,
        # not scoped to (physical_boat_id, claiming_organization_id)) closes
        # the race window against a *different* PhysicalBoat/Organization
        # pair concurrently claiming this exact revision id -- mirrors
        # write_native_listing_offer_revision's rationale.
        cur.execute(
            _INSERT_REVISION,
            (
                revision_id.value,
                physical_boat_id_value,
                candidate_organization.id.value,
                account_id.value,
                claims.marketed_brand_claim,
                claims.model_designation_claim,
                build_year_kind,
                build_year_value,
                loa_length_kind,
                loa_length_value,
                draft_kind,
                draft_value,
                keel_kind,
                keel_value,
                rudder_kind,
                rudder_value,
                actual_current_id,
                content_hash,
            ),
        )
        if cur.rowcount == 0:
            # Lost the race: a different (PhysicalBoat, Organization) pair
            # committed this exact claim_revision_id after our pre-check but
            # before our INSERT. Can never be a match for *our* pair (same-
            # pair writes are fully serialized by the physical_boats row
            # lock above), so it is always CONFLICT, never ALREADY_EXISTS --
            # and our own head is untouched.
            return PhysicalBoatClaimWriteResult(
                status=PhysicalBoatClaimWriteStatus.CONFLICT,
                current_revision_id=_current_wrapped(),
            )

        cur.execute(
            _UPSERT_HEAD,
            (physical_boat_id_value, candidate_organization.id.value, revision_id.value),
        )

        status = (
            PhysicalBoatClaimWriteStatus.CREATED
            if actual_current_id is None
            else PhysicalBoatClaimWriteStatus.REVISED
        )
        return PhysicalBoatClaimWriteResult(status=status, current_revision_id=revision_id)


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_current_physical_boat_claim(
    conn: Any, physical_boat_id: PhysicalBoatId, claiming_organization_id: MarketplaceOrganizationId
) -> PhysicalBoatClaimRevisionRecord | None:
    """Exact typed readback of the current claim revision for one
    `(PhysicalBoatId, claiming Organization)` pair.

    Reads the explicit current/head pointer -- never `MAX(recorded_at)` or
    row order. A missing PhysicalBoat/Organization pair or no current claim
    returns None rather than inventing a record.
    """
    if not isinstance(physical_boat_id, PhysicalBoatId):
        raise TypeError(
            f"physical_boat_id must be a PhysicalBoatId, got {type(physical_boat_id).__name__}"
        )
    if not isinstance(claiming_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "claiming_organization_id must be a MarketplaceOrganizationId, got "
            f"{type(claiming_organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_CURRENT_CLAIM, [physical_boat_id.value, claiming_organization_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_revision_record(row)


def fetch_physical_boat_claim_revision(
    conn: Any, revision_id: PhysicalBoatClaimRevisionId
) -> PhysicalBoatClaimRevisionRecord | None:
    """Exact typed readback of one immutable claim revision by its own id.

    Returns the revision regardless of whether it is still the current head
    -- used to prove prior revisions remain retained/unchanged after a later
    revision supersedes them.
    """
    if not isinstance(revision_id, PhysicalBoatClaimRevisionId):
        raise TypeError(
            f"revision_id must be a PhysicalBoatClaimRevisionId, got {type(revision_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_REVISION_RECORD, [revision_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_revision_record(row)


def list_physical_boat_claim_revisions(
    conn: Any, physical_boat_id: PhysicalBoatId, claiming_organization_id: MarketplaceOrganizationId
) -> list[PhysicalBoatClaimRevisionRecord]:
    """Exact typed readback of the immutable revision history for one
    `(PhysicalBoatId, claiming Organization)` pair.

    Ordered by recorded_at for display/audit convenience only; which
    revision is *current* is never inferred from this ordering -- use
    `fetch_current_physical_boat_claim` for that.
    """
    if not isinstance(physical_boat_id, PhysicalBoatId):
        raise TypeError(
            f"physical_boat_id must be a PhysicalBoatId, got {type(physical_boat_id).__name__}"
        )
    if not isinstance(claiming_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "claiming_organization_id must be a MarketplaceOrganizationId, got "
            f"{type(claiming_organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_HISTORY, [physical_boat_id.value, claiming_organization_id.value])
        rows = cur.fetchall()
    return [_row_to_revision_record(row) for row in rows]
