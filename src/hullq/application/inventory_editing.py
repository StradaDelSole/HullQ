"""Broker-facing post-promotion inventory editor orchestration — SLICE-0072.

Implements `specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md`: thin
application orchestration exposing the already-accepted revisioned
NativeListing offer / Organization PhysicalBoat claim truth stores
(`hullq.persistence.inventory_editing`) through the authenticated Broker
Workspace, for an already-existing NativeListing owned by the selected,
currently authorized MarketplaceOrganization.

Authorization reuses the exact accepted SLICE-0053 Organization workspace/MFA
boundary (`hullq.application.broker_workspace_read.get_organization_workspace_result`)
-- mirrors `hullq.application.broker_inventory_lifecycle`'s identical
`_authorize_lifecycle_actor` pattern -- then re-fetches the current
`MarketplaceOrganization`/`OrganizationMembership` domain records so the real
accepted SLICE-0041 publishing-eligibility evaluator, invoked again inside
each persistence primitive, remains the sole authority over denial (contract
§2). This module never pre-decides eligibility itself.

`NATIVE_LISTING_NOT_FOUND`/`ORGANIZATION_MISMATCH`/`CROSS_ORGANIZATION_DENIED`
all collapse to the identical `LISTING_NOT_FOUND` outcome (contract §2: "must
remain non-enumerating") -- a foreign listing's existence is never
distinguishable from an unknown one once the Organization boundary itself has
already succeeded.

Every write re-opens a fresh top-level transaction on *conn* before invoking
the persistence primitive (mirrors `broker_inventory_lifecycle`'s identical
`conn.commit()` convention): the authorization reads issued by
`get_organization_workspace_result` and this module's own domain-record
re-fetch leave an implicit read transaction open under psycopg's default
`autocommit=False`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.application.current_public_eligibility import resolve_current_public_eligibility
from hullq.application.native_listing_freshness import resolve_current_freshness
from hullq.domain.current_public_eligibility import CurrentPublicSuppressionReason
from hullq.domain.inventory_edit_request import (
    InvalidInventoryEditRequestError,
    parse_native_listing_offer_edit_request,
    parse_physical_boat_claim_edit_request,
)
from hullq.domain.market_identity import MarketEpisodeId, NativeListingId, PhysicalBoatId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import PhysicalBoatClaimSnapshot
from hullq.domain.publishing_eligibility import (
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.broker_identity import (
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.persistence.inventory_editing import (
    ClaimEditResult,
    ClaimEditStatus,
    OfferEditResult,
    OfferEditStatus,
    edit_native_listing_offer,
    edit_physical_boat_claim,
)
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionRecord,
    fetch_current_native_listing_offer,
)
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimRevisionRecord,
    fetch_current_physical_boat_claim,
)
from hullq.persistence.publication_readiness import resolve_publication_readiness
from hullq.security.session_token import SessionClaims

__all__ = [
    "ClaimSaveOutcome",
    "ClaimSaveResult",
    "InventoryDetailOutcome",
    "InventoryDetailResult",
    "InventoryDetailView",
    "OfferSaveOutcome",
    "OfferSaveResult",
    "get_inventory_edit_detail",
    "save_organization_listing_claim",
    "save_organization_listing_offer",
]


# ---------------------------------------------------------------------------
# Shared actor authorization -- mirrors
# hullq.application.broker_inventory_lifecycle._authorize_lifecycle_actor
# ---------------------------------------------------------------------------


class _EditorActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


@dataclass(frozen=True)
class _AuthorizedActor:
    organization: MarketplaceOrganization
    membership: OrganizationMembership | None


def _authorize_editor_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> tuple[_EditorActorAuthorizationOutcome, _AuthorizedActor | None]:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _EditorActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _EditorActorAuthorizationOutcome.MFA_REQUIRED, None

    organization = fetch_marketplace_organization(conn, organization_id)
    if organization is None:
        return _EditorActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    return (
        _EditorActorAuthorizationOutcome.AUTHORIZED,
        _AuthorizedActor(organization=organization, membership=membership),
    )


def _fetch_owned_listing(
    conn: Any, native_listing_id: NativeListingId, organization_id: MarketplaceOrganizationId
) -> tuple[str | None, NativeListingLifecycleState] | None:
    """`(market_episode_id_value, lifecycle_state)` for *native_listing_id*
    iff it exists and is owned by *organization_id*; `None` otherwise
    (contract §2: unknown and foreign must be indistinguishable)."""
    listing_record = fetch_native_listing(conn, native_listing_id)
    if listing_record is None or listing_record.publishing_organization_id != organization_id:
        return None
    lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
    assert lifecycle_state is not None
    market_episode_id_value = (
        listing_record.listing.market_episode_id.value
        if listing_record.listing.market_episode_id is not None
        else None
    )
    return market_episode_id_value, lifecycle_state


# ---------------------------------------------------------------------------
# Offer / claim wire serialization (contract §8: minimum visible context)
# ---------------------------------------------------------------------------


def _claim_wrapper_wire(claim: Any) -> dict[str, Any] | None:
    if claim is None:
        return None
    value = claim.value
    if hasattr(value, "value") and not isinstance(value, str):
        value = value.value  # StrEnum member (KeelConfiguration/RudderConfiguration/VatTaxStatusValue)
    elif value is not None and not isinstance(value, (str, int)):
        value = str(value)  # Decimal -> plain string, never a binary float
    return {"assertion_kind": claim.assertion_kind.value, "value": value}


def _offer_to_wire_dict(offer: NativeListingOfferSnapshot) -> dict[str, Any]:
    body: dict[str, Any] = {
        "listing_offer.asking_price_mode": offer.asking_price_mode.value,
        "listing_offer.location_country": offer.location_country,
        "listing_offer.broker_description": offer.broker_description,
    }
    if offer.asking_price_amount is not None:
        body["listing_offer.asking_price_amount"] = str(offer.asking_price_amount)
    if offer.currency is not None:
        body["listing_offer.currency"] = offer.currency
    if offer.location_region is not None:
        body["listing_offer.location_region"] = _claim_wrapper_wire(offer.location_region)
    if offer.broker_summary is not None:
        body["listing_offer.broker_summary"] = _claim_wrapper_wire(offer.broker_summary)
    if offer.known_history_narrative is not None:
        body["listing_offer.known_history_narrative"] = _claim_wrapper_wire(
            offer.known_history_narrative
        )
    if offer.vat_tax_status_claim is not None:
        body["listing_offer.vat_tax_status_claim"] = _claim_wrapper_wire(offer.vat_tax_status_claim)
    return body


def _claims_to_wire_dict(claims: PhysicalBoatClaimSnapshot) -> dict[str, Any]:
    body: dict[str, Any] = {
        "physical_boat.marketed_brand_claim": claims.marketed_brand_claim,
        "physical_boat.model_designation_claim": claims.model_designation_claim,
        "physical_boat.build_year": _claim_wrapper_wire(claims.build_year),
    }
    if claims.loa_length is not None:
        body["physical_boat.loa_length"] = _claim_wrapper_wire(claims.loa_length)
    if claims.draft is not None:
        body["physical_boat.draft"] = _claim_wrapper_wire(claims.draft)
    if claims.keel_configuration is not None:
        body["physical_boat.keel_configuration"] = _claim_wrapper_wire(claims.keel_configuration)
    if claims.rudder_configuration is not None:
        body["physical_boat.rudder_configuration"] = _claim_wrapper_wire(claims.rudder_configuration)
    if claims.boat_name is not None:
        body["physical_boat.boat_name"] = _claim_wrapper_wire(claims.boat_name)
    return body


# ---------------------------------------------------------------------------
# Read: inventory edit detail (contract §8)
# ---------------------------------------------------------------------------


class InventoryDetailOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    OK = "OK"


@dataclass(frozen=True)
class InventoryDetailView:
    """Contract §8 minimum visible context. `claim`/`current_claim_revision_id`
    are `None` only in the defensive case of an incomplete NativeListing ->
    MarketEpisode -> PhysicalBoat chain (never expected for a listing that has
    completed SLICE-0067 promotion)."""

    native_listing_id: str
    organization_id: str
    lifecycle_state: str
    freshness_status: str
    last_confirmed_at: str | None
    current_offer_revision_id: str | None
    offer: dict[str, Any] | None
    current_claim_revision_id: str | None
    claim: dict[str, Any] | None
    publication_readiness: dict[str, Any] | None = None
    current_public_status: str | None = None
    suppression_reasons: tuple[str, ...] | None = None

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "native_listing_id": self.native_listing_id,
            "organization_id": self.organization_id,
            "lifecycle_state": self.lifecycle_state,
            "freshness_status": self.freshness_status,
            "last_confirmed_at": self.last_confirmed_at,
            "current_offer_revision_id": self.current_offer_revision_id,
            "offer": self.offer,
            "current_claim_revision_id": self.current_claim_revision_id,
            "claim": self.claim,
        }
        if self.publication_readiness is not None:
            body["publication_readiness"] = self.publication_readiness
        if self.current_public_status is not None:
            body["current_public_status"] = self.current_public_status
        if self.suppression_reasons is not None:
            body["suppression_reasons"] = list(self.suppression_reasons)
        return body


@dataclass(frozen=True)
class InventoryDetailResult:
    outcome: InventoryDetailOutcome
    view: InventoryDetailView | None = None

    def __post_init__(self) -> None:
        if self.outcome is InventoryDetailOutcome.OK:
            if self.view is None:
                raise ValueError("An OK inventory detail result must carry a view")
        elif self.view is not None:
            raise ValueError("Only an OK inventory detail result may carry a view")


def get_inventory_edit_detail(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    *,
    as_of: datetime,
) -> InventoryDetailResult:
    """Read the current authoritative offer/claim/lifecycle state for one own
    NativeListing (contract §8), reusing the identical D22/D29 evaluators the
    Broker Workspace inventory overview already reads
    (`hullq.application.broker_inventory_read._build_item_view`) -- never a
    second, independently maintained readiness/suppression rule.
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_editor_actor(conn, session, organization_id)
    if auth_outcome is _EditorActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return InventoryDetailResult(outcome=InventoryDetailOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _EditorActorAuthorizationOutcome.MFA_REQUIRED:
        return InventoryDetailResult(outcome=InventoryDetailOutcome.MFA_REQUIRED)
    assert actor is not None

    native_listing_id = NativeListingId(native_listing_id_value)
    owned = _fetch_owned_listing(conn, native_listing_id, organization_id)
    if owned is None:
        return InventoryDetailResult(outcome=InventoryDetailOutcome.LISTING_NOT_FOUND)
    market_episode_id_value, lifecycle_state = owned

    freshness = resolve_current_freshness(conn, native_listing_id, as_of=as_of)

    offer_record: NativeListingOfferRevisionRecord | None = fetch_current_native_listing_offer(
        conn, native_listing_id
    )

    claim_record: PhysicalBoatClaimRevisionRecord | None = None
    if market_episode_id_value is not None:
        market_episode_record = fetch_market_episode(conn, MarketEpisodeId(market_episode_id_value))
        if market_episode_record is not None:
            physical_boat_id: PhysicalBoatId = market_episode_record.market_episode.physical_boat_id
            if fetch_physical_boat(conn, physical_boat_id) is not None:
                claim_record = fetch_current_physical_boat_claim(
                    conn, physical_boat_id, organization_id
                )

    publication_readiness: dict[str, Any] | None = None
    current_public_status: str | None = None
    suppression_reasons: tuple[str, ...] | None = None
    if lifecycle_state is NativeListingLifecycleState.DRAFT:
        eligibility_decision = evaluate_native_listing_publishing_eligibility(
            session.account_id, actor.organization, actor.membership
        )
        readiness = resolve_publication_readiness(
            conn,
            native_listing_id=native_listing_id,
            publishing_organization_id=organization_id,
            publishing_eligibility=eligibility_decision,
            lifecycle_state=lifecycle_state,
            market_episode_id_value=market_episode_id_value,
        )
        publication_readiness = {
            "status": readiness.status.value,
            "blockers": sorted(blocker.value for blocker in readiness.blockers),
        }
    elif lifecycle_state is NativeListingLifecycleState.ACTIVE:
        eligibility = resolve_current_public_eligibility(conn, native_listing_id, as_of=as_of)
        if eligibility is not None:
            current_public_status = eligibility.status.value
            suppression_reasons = tuple(
                sorted(reason.value for reason in eligibility.suppression_reasons)
            )

    view = InventoryDetailView(
        native_listing_id=native_listing_id.value,
        organization_id=organization_id.value,
        lifecycle_state=lifecycle_state.value,
        freshness_status=freshness.status.value,
        last_confirmed_at=(
            freshness.last_confirmed_at.isoformat() if freshness.last_confirmed_at is not None else None
        ),
        current_offer_revision_id=(
            offer_record.revision_id.value if offer_record is not None else None
        ),
        offer=_offer_to_wire_dict(offer_record.offer) if offer_record is not None else None,
        current_claim_revision_id=(
            claim_record.revision_id.value if claim_record is not None else None
        ),
        claim=_claims_to_wire_dict(claim_record.claims) if claim_record is not None else None,
        publication_readiness=publication_readiness,
        current_public_status=current_public_status,
        suppression_reasons=suppression_reasons,
    )
    return InventoryDetailResult(outcome=InventoryDetailOutcome.OK, view=view)


# ---------------------------------------------------------------------------
# Write: offer save
# ---------------------------------------------------------------------------


class OfferSaveOutcome(StrEnum):
    """Mechanically distinct outcomes (mirrors contract §5/§7/§8's bounded
    saved/invalid/stale/unauthorized/blocking-invariant vocabulary)."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    DENIED = "DENIED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    STALE_VERSION = "STALE_VERSION"
    ACTIVE_INVARIANT_VIOLATION = "ACTIVE_INVARIANT_VIOLATION"
    SAVED = "SAVED"


@dataclass(frozen=True)
class OfferSaveResult:
    outcome: OfferSaveOutcome
    denial_reason: PublishingEligibilityReason | None = None
    current_offer_revision_id: str | None = None
    blockers: frozenset[CurrentPublicSuppressionReason] | None = None

    def __post_init__(self) -> None:
        if self.outcome is OfferSaveOutcome.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry a denial reason")

        carries_revision = self.outcome in (OfferSaveOutcome.SAVED, OfferSaveOutcome.STALE_VERSION)
        if self.outcome is OfferSaveOutcome.SAVED and self.current_offer_revision_id is None:
            raise ValueError("A SAVED result must carry current_offer_revision_id")
        if not carries_revision and self.current_offer_revision_id is not None:
            raise ValueError("Only SAVED/STALE_VERSION may carry current_offer_revision_id")

        if self.outcome is OfferSaveOutcome.ACTIVE_INVARIANT_VIOLATION:
            if not self.blockers:
                raise ValueError(
                    "An ACTIVE_INVARIANT_VIOLATION result must carry at least one blocker"
                )
        elif self.blockers is not None:
            raise ValueError("Only an ACTIVE_INVARIANT_VIOLATION result may carry blockers")

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"outcome": self.outcome.value}
        if self.denial_reason is not None:
            body["reason"] = self.denial_reason.value
        if self.current_offer_revision_id is not None:
            body["current_offer_revision_id"] = self.current_offer_revision_id
        if self.blockers is not None:
            body["blockers"] = sorted(blocker.value for blocker in self.blockers)
        return body


def _map_offer_edit_result(result: OfferEditResult) -> OfferSaveResult:
    if result.status is OfferEditStatus.DENIED:
        assert result.denial_reason is not None
        return OfferSaveResult(outcome=OfferSaveOutcome.DENIED, denial_reason=result.denial_reason)
    if result.status in (OfferEditStatus.CROSS_ORGANIZATION_DENIED, OfferEditStatus.NATIVE_LISTING_NOT_FOUND):
        return OfferSaveResult(outcome=OfferSaveOutcome.LISTING_NOT_FOUND)
    if result.status is OfferEditStatus.CONFLICT:
        return OfferSaveResult(
            outcome=OfferSaveOutcome.STALE_VERSION,
            current_offer_revision_id=(
                result.current_revision_id.value if result.current_revision_id is not None else None
            ),
        )
    if result.status is OfferEditStatus.ACTIVE_INVARIANT_VIOLATION:
        assert result.blockers is not None
        return OfferSaveResult(
            outcome=OfferSaveOutcome.ACTIVE_INVARIANT_VIOLATION, blockers=result.blockers
        )
    assert result.status in (OfferEditStatus.REVISED, OfferEditStatus.ALREADY_EXISTS)
    assert result.current_revision_id is not None
    return OfferSaveResult(
        outcome=OfferSaveOutcome.SAVED, current_offer_revision_id=result.current_revision_id.value
    )


def save_organization_listing_offer(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_body: Any,
) -> OfferSaveResult:
    """Apply one ordinary NativeListing offer edit for one own NativeListing
    (contract §3/§4/§5)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_editor_actor(conn, session, organization_id)
    if auth_outcome is _EditorActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return OfferSaveResult(outcome=OfferSaveOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _EditorActorAuthorizationOutcome.MFA_REQUIRED:
        return OfferSaveResult(outcome=OfferSaveOutcome.MFA_REQUIRED)
    assert actor is not None

    try:
        parsed = parse_native_listing_offer_edit_request(raw_body)
    except InvalidInventoryEditRequestError:
        return OfferSaveResult(outcome=OfferSaveOutcome.INVALID_PAYLOAD)

    conn.commit()
    result = edit_native_listing_offer(
        conn,
        account_id=session.account_id,
        candidate_organization=actor.organization,
        membership=actor.membership,
        native_listing_id=NativeListingId(native_listing_id_value),
        revision_id=parsed.revision_id,
        expected_current_revision_id=parsed.expected_current_revision_id,
        offer=parsed.offer,
    )
    return _map_offer_edit_result(result)


# ---------------------------------------------------------------------------
# Write: claim save
# ---------------------------------------------------------------------------


class ClaimSaveOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    DENIED = "DENIED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    CHAIN_INCOMPLETE = "CHAIN_INCOMPLETE"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    STALE_VERSION = "STALE_VERSION"
    ACTIVE_INVARIANT_VIOLATION = "ACTIVE_INVARIANT_VIOLATION"
    SAVED = "SAVED"


@dataclass(frozen=True)
class ClaimSaveResult:
    outcome: ClaimSaveOutcome
    denial_reason: PublishingEligibilityReason | None = None
    current_claim_revision_id: str | None = None
    blockers: frozenset[CurrentPublicSuppressionReason] | None = None

    def __post_init__(self) -> None:
        if self.outcome is ClaimSaveOutcome.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry a denial reason")

        carries_revision = self.outcome in (ClaimSaveOutcome.SAVED, ClaimSaveOutcome.STALE_VERSION)
        if self.outcome is ClaimSaveOutcome.SAVED and self.current_claim_revision_id is None:
            raise ValueError("A SAVED result must carry current_claim_revision_id")
        if not carries_revision and self.current_claim_revision_id is not None:
            raise ValueError("Only SAVED/STALE_VERSION may carry current_claim_revision_id")

        if self.outcome is ClaimSaveOutcome.ACTIVE_INVARIANT_VIOLATION:
            if not self.blockers:
                raise ValueError(
                    "An ACTIVE_INVARIANT_VIOLATION result must carry at least one blocker"
                )
        elif self.blockers is not None:
            raise ValueError("Only an ACTIVE_INVARIANT_VIOLATION result may carry blockers")

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"outcome": self.outcome.value}
        if self.denial_reason is not None:
            body["reason"] = self.denial_reason.value
        if self.current_claim_revision_id is not None:
            body["current_claim_revision_id"] = self.current_claim_revision_id
        if self.blockers is not None:
            body["blockers"] = sorted(blocker.value for blocker in self.blockers)
        return body


def _map_claim_edit_result(result: ClaimEditResult) -> ClaimSaveResult:
    if result.status is ClaimEditStatus.DENIED:
        assert result.denial_reason is not None
        return ClaimSaveResult(outcome=ClaimSaveOutcome.DENIED, denial_reason=result.denial_reason)
    if result.status in (
        ClaimEditStatus.CROSS_ORGANIZATION_DENIED,
        ClaimEditStatus.NATIVE_LISTING_NOT_FOUND,
    ):
        return ClaimSaveResult(outcome=ClaimSaveOutcome.LISTING_NOT_FOUND)
    if result.status is ClaimEditStatus.CHAIN_INCOMPLETE:
        return ClaimSaveResult(outcome=ClaimSaveOutcome.CHAIN_INCOMPLETE)
    if result.status is ClaimEditStatus.CONFLICT:
        return ClaimSaveResult(
            outcome=ClaimSaveOutcome.STALE_VERSION,
            current_claim_revision_id=(
                result.current_revision_id.value if result.current_revision_id is not None else None
            ),
        )
    if result.status is ClaimEditStatus.ACTIVE_INVARIANT_VIOLATION:
        assert result.blockers is not None
        return ClaimSaveResult(
            outcome=ClaimSaveOutcome.ACTIVE_INVARIANT_VIOLATION, blockers=result.blockers
        )
    assert result.status in (ClaimEditStatus.REVISED, ClaimEditStatus.ALREADY_EXISTS)
    assert result.current_revision_id is not None
    return ClaimSaveResult(
        outcome=ClaimSaveOutcome.SAVED, current_claim_revision_id=result.current_revision_id.value
    )


def save_organization_listing_claim(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_body: Any,
) -> ClaimSaveResult:
    """Apply one ordinary Organization PhysicalBoat claim edit for one own
    NativeListing (contract §3/§4/§5)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_editor_actor(conn, session, organization_id)
    if auth_outcome is _EditorActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return ClaimSaveResult(outcome=ClaimSaveOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _EditorActorAuthorizationOutcome.MFA_REQUIRED:
        return ClaimSaveResult(outcome=ClaimSaveOutcome.MFA_REQUIRED)
    assert actor is not None

    try:
        parsed = parse_physical_boat_claim_edit_request(raw_body)
    except InvalidInventoryEditRequestError:
        return ClaimSaveResult(outcome=ClaimSaveOutcome.INVALID_PAYLOAD)

    conn.commit()
    result = edit_physical_boat_claim(
        conn,
        account_id=session.account_id,
        candidate_organization=actor.organization,
        membership=actor.membership,
        native_listing_id=NativeListingId(native_listing_id_value),
        revision_id=parsed.revision_id,
        expected_current_revision_id=parsed.expected_current_revision_id,
        claims=parsed.claims,
    )
    return _map_claim_edit_result(result)
