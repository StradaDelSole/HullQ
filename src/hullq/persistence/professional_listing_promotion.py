"""Professional draft -> atomic marketplace promotion — SLICE-0067.

Implements `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md` §7/§8/§9:
the one top-level PostgreSQL transaction that locks an exact,
Organization-owned `ProfessionalListingDraft`, re-validates authorization and
`PromotionReadiness`, mints fresh server-owned marketplace identities, and
creates the complete initial PhysicalBoat/MarketEpisode/NativeListing/claim/
offer chain plus the draft's own PROMOTED provenance -- all inside one
transaction, so any failure at any stage rolls back every write from that
attempt (contract §8: "No partial state ... is allowed").

Per contract §9, this module does not satisfy §8 by sequentially invoking
the existing standalone, independently-committing persistence writers
(`create_physical_boat`, `create_market_episode`, `create_native_listing`,
`write_native_listing_offer_revision`, `write_physical_boat_claim_revision`).
It instead composes each of those modules' factored-out, transaction-scoped
internal primitives (`insert_physical_boat_row`, `insert_market_episode_row`,
`insert_native_listing_row`, `write_native_listing_offer_revision_row`,
`write_physical_boat_claim_revision_row`) against one shared cursor inside
this function's own single `with conn.transaction():` block -- mechanically
preserving each primitive's existing validation/fingerprint/FK/head-pointer/
Organization-isolation semantics (contract §9) without a generic repository/
Unit-of-Work framework.

Publishing eligibility (the real accepted SLICE-0041 evaluator) and
`PromotionReadiness` (the real accepted SLICE-0067 evaluator) are each
invoked exactly once per attempt, against the exact locked draft row,
never pre-decided by a caller-supplied flag.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.domain.listing_draft_payload import AskingPriceMode as DraftAskingPriceMode
from hullq.domain.listing_draft_payload import ListingDraftPayload
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_offer import AskingPriceMode as OfferAskingPriceMode
from hullq.domain.native_listing_offer import (
    AssertionKind,
    LocationRegionClaim,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
)
from hullq.domain.physical_boat_claims import (
    BoatNameClaim,
    BuildYearClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.professional_listing_draft import (
    ProfessionalDraftPromotionState,
    ProfessionalListingDraftId,
)
from hullq.domain.promotion_readiness import PromotionReadinessReason, evaluate_promotion_readiness
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.market_episode import MarketEpisodeCreationStatus, insert_market_episode_row
from hullq.persistence.native_listing import NativeListingCreationStatus, insert_native_listing_row
from hullq.persistence.native_listing_offer import (
    NativeListingOfferWriteStatus,
    write_native_listing_offer_revision_row,
)
from hullq.persistence.physical_boat import PhysicalBoatCreationStatus, insert_physical_boat_row
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimWriteStatus,
    write_physical_boat_claim_revision_row,
)
from hullq.persistence.professional_listing_draft import (
    lock_professional_listing_draft_for_promotion,
    mark_professional_listing_draft_promoted,
)

__all__ = [
    "ProfessionalListingPromotionResult",
    "ProfessionalListingPromotionStatus",
    "ProfessionalListingPromotionTransactionOwnershipError",
    "promote_professional_listing_draft",
]

#: The exact SLICE-0067 D09 database uniqueness boundary (the migration's
#: partial unique index name, `107a989812e7_professional_draft_promotion`).
#: `DUPLICATE_EPISODE` is valid *only* for a `UniqueViolation` naming this
#: exact index/constraint -- independent exact-head review Finding C: any
#: other `UniqueViolation` escaping the promotion transaction (e.g. an
#: astronomically unlikely collision on a freshly-minted claim/offer
#: revision id, or on the draft's own promoted-NativeListingId uniqueness)
#: is a genuine internal invariant failure, never a business "this episode
#: is already listed" outcome, and must not be mislabeled as one.
_D09_ORG_EPISODE_UNIQUE_CONSTRAINT_NAME = "ux_native_listings_org_episode"


class ProfessionalListingPromotionTransactionOwnershipError(RuntimeError):
    """promote_professional_listing_draft cannot safely own a top-level
    transaction on *conn*.

    Mirrors every other module's identical guard (e.g.
    `hullq.persistence.native_listing.NativeListingTransactionOwnershipError`):
    a PROMOTED result must always mean the complete chain is already durably
    committed, independent of later caller action. That guarantee only holds
    when *conn* is IDLE. Call ``conn.commit()``/``conn.rollback()`` first, or
    pass a freshly opened connection.
    """


class ProfessionalListingPromotionStatus(StrEnum):
    """The bounded outcome vocabulary (contract §6). Never a bare boolean."""

    PROMOTED = "PROMOTED"
    ALREADY_PROMOTED = "ALREADY_PROMOTED"
    NOT_READY = "NOT_READY"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    DRAFT_NOT_FOUND = "DRAFT_NOT_FOUND"
    DENIED = "DENIED"
    DUPLICATE_EPISODE = "DUPLICATE_EPISODE"


_STATUSES_CARRYING_NATIVE_LISTING_ID = frozenset(
    {
        ProfessionalListingPromotionStatus.PROMOTED,
        ProfessionalListingPromotionStatus.ALREADY_PROMOTED,
    }
)


@dataclass(frozen=True)
class ProfessionalListingPromotionResult:
    """Deterministic result of one promotion attempt (contract §6).

    `PROMOTED`/`ALREADY_PROMOTED` always carry the resulting
    `NativeListingId`. `NOT_READY` always carries at least one
    `PromotionReadinessReason`. `DENIED` always carries the real SLICE-0041
    denial reason. No other status carries any of these.
    """

    status: ProfessionalListingPromotionStatus
    native_listing_id: NativeListingId | None = None
    reasons: tuple[PromotionReadinessReason, ...] | None = None
    denial_reason: PublishingEligibilityReason | None = None

    def __post_init__(self) -> None:
        if self.status in _STATUSES_CARRYING_NATIVE_LISTING_ID:
            if self.native_listing_id is None:
                raise ValueError(f"A {self.status.value} result must carry a native_listing_id")
        elif self.native_listing_id is not None:
            raise ValueError("Only PROMOTED/ALREADY_PROMOTED may carry a native_listing_id")

        if self.status is ProfessionalListingPromotionStatus.NOT_READY:
            if not self.reasons:
                raise ValueError("A NOT_READY result must carry at least one reason")
        elif self.reasons is not None:
            raise ValueError("Only a NOT_READY result may carry reasons")

        if self.status is ProfessionalListingPromotionStatus.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry a denial reason")


def _build_claim_snapshot(payload: ListingDraftPayload) -> PhysicalBoatClaimSnapshot:
    """Contract §10.4: exactly brand/model/build_year (+ optional boat_name),
    no BoatDesign baseline value copied, every other PhysicalBoat claim
    field omitted. Callers must only invoke this after PromotionReadiness
    has already confirmed brand/model/build_year are all present."""
    assert payload.marketed_brand_claim is not None
    assert payload.model_designation_claim is not None
    assert payload.build_year is not None

    build_year = BuildYearClaim(
        assertion_kind=AssertionKind(payload.build_year.assertion_kind.value),
        value=payload.build_year.value,
    )
    boat_name = (
        BoatNameClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=payload.boat_name)
        if payload.boat_name is not None
        else None
    )
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim=payload.marketed_brand_claim,
        model_designation_claim=payload.model_designation_claim,
        build_year=build_year,
        boat_name=boat_name,
    )


def _build_offer_snapshot(
    payload: ListingDraftPayload, broker_description: str
) -> NativeListingOfferSnapshot:
    """Contract §10.5: exactly mode/amount-iff-AMOUNT/currency-iff-AMOUNT/
    country/optional region/broker_description, every other offer field
    omitted. Callers must only invoke this after PromotionReadiness has
    already confirmed mode/country/broker_description (+ amount/currency
    when AMOUNT) are all present."""
    assert payload.asking_price_mode is not None
    assert payload.location_country is not None

    mode = OfferAskingPriceMode(payload.asking_price_mode.value)
    is_amount = payload.asking_price_mode is DraftAskingPriceMode.AMOUNT
    location_region = (
        LocationRegionClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=payload.location_region
        )
        if payload.location_region is not None
        else None
    )
    return NativeListingOfferSnapshot(
        asking_price_mode=mode,
        location_country=payload.location_country,
        broker_description=broker_description,
        asking_price_amount=payload.asking_price_amount if is_amount else None,
        currency=payload.currency if is_amount else None,
        location_region=location_region,
    )


def promote_professional_listing_draft(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    draft_id: ProfessionalListingDraftId,
    owner_organization_id: MarketplaceOrganizationId,
    expected_version: int,
) -> ProfessionalListingPromotionResult:
    """Run the complete D01-D09/§8 promotion transaction for one draft.

    *account_id*/*candidate_organization*/*membership* are the exact
    SLICE-0041 principal already authorized by the caller's Organization
    workspace boundary (contract §4) -- this function still re-evaluates
    real publishing eligibility itself before any marketplace write, exactly
    once, against the exact locked draft row.

    Raises ProfessionalListingPromotionTransactionOwnershipError, before any
    read/write is attempted, if *conn* already has an open transaction.
    """
    if not isinstance(expected_version, int) or isinstance(expected_version, bool):
        raise TypeError(f"expected_version must be an int, got {type(expected_version).__name__}")
    if expected_version <= 0:
        raise ValueError(f"expected_version must be positive, got {expected_version}")

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise ProfessionalListingPromotionTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); promote_professional_listing_draft() requires "
            "an IDLE connection so it can safely own and commit its own top-level transaction. "
            "Call conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    from psycopg.errors import UniqueViolation  # deferred: no module-level psycopg dependency

    try:
        with conn.transaction(), conn.cursor() as cur:
            locked = lock_professional_listing_draft_for_promotion(
                cur, draft_id=draft_id, owner_organization_id=owner_organization_id
            )
            if locked is None:
                return ProfessionalListingPromotionResult(
                    status=ProfessionalListingPromotionStatus.DRAFT_NOT_FOUND
                )

            if locked.promotion_state is ProfessionalDraftPromotionState.PROMOTED:
                # Contract §7.3: an exact-version retry against the frozen
                # promoted version is a read/idempotency result, not a
                # second marketplace creation attempt -- zero further writes.
                if locked.version == expected_version:
                    assert locked.promoted_native_listing_id is not None
                    return ProfessionalListingPromotionResult(
                        status=ProfessionalListingPromotionStatus.ALREADY_PROMOTED,
                        native_listing_id=locked.promoted_native_listing_id,
                    )
                return ProfessionalListingPromotionResult(
                    status=ProfessionalListingPromotionStatus.VERSION_CONFLICT
                )

            # EDITABLE.
            if locked.version != expected_version:
                return ProfessionalListingPromotionResult(
                    status=ProfessionalListingPromotionStatus.VERSION_CONFLICT
                )

            decision = evaluate_native_listing_publishing_eligibility(
                account_id, candidate_organization, membership
            )
            if decision.status is PublishingEligibilityStatus.DENIED:
                assert decision.reason is not None
                return ProfessionalListingPromotionResult(
                    status=ProfessionalListingPromotionStatus.DENIED, denial_reason=decision.reason
                )

            readiness = evaluate_promotion_readiness(locked.payload, locked.broker_description)
            if not readiness.is_ready:
                return ProfessionalListingPromotionResult(
                    status=ProfessionalListingPromotionStatus.NOT_READY, reasons=readiness.reasons
                )
            assert locked.broker_description is not None

            # Contract §C: mint every fresh server-owned identity for this
            # one promotion attempt. No BoatDesignRef is synthesized.
            physical_boat_id = PhysicalBoatId(str(uuid.uuid4()))
            market_episode_id = MarketEpisodeId(str(uuid.uuid4()))
            native_listing_id = NativeListingId(str(uuid.uuid4()))
            claim_revision_id = PhysicalBoatClaimRevisionId(str(uuid.uuid4()))
            offer_revision_id = NativeListingOfferRevisionId(str(uuid.uuid4()))

            # Both fresh mints are essentially guaranteed CREATED (server
            # random UUIDs); ALREADY_EXISTS is only reachable via an
            # astronomically unlikely UUID collision with a harmless-
            # identical envelope, tolerated defensively rather than
            # required. CONFLICT/DESIGN_NOT_FOUND/PHYSICAL_BOAT_NOT_FOUND
            # would indicate a genuine internal invariant violation.
            physical_boat_result = insert_physical_boat_row(
                cur, physical_boat=PhysicalBoat(id=physical_boat_id, boat_design_ref=None)
            )
            assert physical_boat_result.status in (
                PhysicalBoatCreationStatus.CREATED,
                PhysicalBoatCreationStatus.ALREADY_EXISTS,
            )
            market_episode_result = insert_market_episode_row(
                cur,
                market_episode=MarketEpisode(
                    id=market_episode_id, physical_boat_id=physical_boat_id
                ),
            )
            assert market_episode_result.status in (
                MarketEpisodeCreationStatus.CREATED,
                MarketEpisodeCreationStatus.ALREADY_EXISTS,
            )

            # A UniqueViolation here (SLICE-0067 D09,
            # ux_native_listings_org_episode) is allowed to propagate: the
            # freshly-minted market_episode_id above makes this practically
            # unreachable, but if it ever fired, the whole surrounding `with
            # conn.transaction():` must still roll back every write from this
            # attempt (contract §8) -- see the except UniqueViolation clause
            # below, which only runs once this whole block has already
            # unwound, and which classifies by exact constraint/index name
            # rather than assuming every UniqueViolation reaching it is D09.
            listing_result = insert_native_listing_row(
                cur,
                account_id=account_id,
                candidate_organization=candidate_organization,
                listing=NativeListing(id=native_listing_id, market_episode_id=market_episode_id),
                broker_listing_reference=locked.broker_listing_reference,
            )
            assert listing_result.status is NativeListingCreationStatus.CREATED

            claim_result = write_physical_boat_claim_revision_row(
                cur,
                account_id=account_id,
                candidate_organization=candidate_organization,
                native_listing_id=native_listing_id,
                revision_id=claim_revision_id,
                expected_current_revision_id=None,
                claims=_build_claim_snapshot(locked.payload),
            )
            assert claim_result.status is PhysicalBoatClaimWriteStatus.CREATED

            offer_result = write_native_listing_offer_revision_row(
                cur,
                account_id=account_id,
                candidate_organization=candidate_organization,
                native_listing_id=native_listing_id,
                revision_id=offer_revision_id,
                expected_current_revision_id=None,
                offer=_build_offer_snapshot(locked.payload, locked.broker_description),
            )
            assert offer_result.status is NativeListingOfferWriteStatus.CREATED

            promoted_at = mark_professional_listing_draft_promoted(
                cur,
                draft_id=draft_id,
                owner_organization_id=owner_organization_id,
                expected_version=expected_version,
                promoted_native_listing_id=native_listing_id,
            )
            assert promoted_at is not None

            return ProfessionalListingPromotionResult(
                status=ProfessionalListingPromotionStatus.PROMOTED,
                native_listing_id=native_listing_id,
            )
    except UniqueViolation as exc:
        # Independent exact-head review Finding C: classify by the exact
        # PostgreSQL constraint/index diagnostic, never by "any
        # UniqueViolation reached here". The surrounding `with
        # conn.transaction():` has already rolled back every write from
        # this attempt by the time this except clause runs (contract §8),
        # for either branch below.
        if exc.diag.constraint_name == _D09_ORG_EPISODE_UNIQUE_CONSTRAINT_NAME:
            return ProfessionalListingPromotionResult(
                status=ProfessionalListingPromotionStatus.DUPLICATE_EPISODE
            )
        # A UniqueViolation on any other constraint is a genuine internal
        # invariant failure (e.g. an astronomically unlikely fresh-UUID
        # collision on a claim/offer revision id or on the draft's own
        # promoted-NativeListingId uniqueness) -- never converted to a
        # business "duplicate episode" outcome.
        raise
