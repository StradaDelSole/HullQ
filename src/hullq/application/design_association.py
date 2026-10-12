"""Broker-facing post-promotion NativeListing PhysicalBoat -> canonical
BoatDesign first-association orchestration -- SLICE-0082.

Thin application orchestration exposing the bounded candidate projection
and the atomic first-association write
(`hullq.persistence.boat_design_association`) through the authenticated
Broker Workspace, for an already-existing NativeListing owned by the
selected, currently authorized MarketplaceOrganization.

Authorization reuses the exact accepted SLICE-0053 Organization workspace/
MFA boundary (`hullq.application.broker_workspace_read.
get_organization_workspace_result`) -- mirrors
`hullq.application.inventory_editing`'s identical `_authorize_editor_actor`
pattern -- then re-fetches the current `MarketplaceOrganization`/
`OrganizationMembership` domain records so the real accepted SLICE-0041
publishing-eligibility evaluator remains the sole authority over write
denial. Reads (the selector search and the current-link readback) do not
evaluate publishing eligibility at all, mirroring
`hullq.application.inventory_editing.get_inventory_edit_detail`'s identical
read/write authorization split: only the mutating association endpoint
requires the PUBLISHER role / Organization eligibility gate.

`NATIVE_LISTING_NOT_FOUND`/`ORGANIZATION_MISMATCH` collapse to the identical
`LISTING_NOT_FOUND` outcome everywhere in this module -- a foreign listing's
existence is never distinguishable from an unknown one once the
Organization boundary itself has already succeeded.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.boat_design_association import (
    DesignCandidate,
    InvalidDesignAssociationRequestError,
    InvalidDesignSelectorQueryError,
    parse_design_association_request,
    parse_design_selector_query,
)
from hullq.domain.market_identity import NativeListingId, PhysicalBoatId
from hullq.domain.publishing_eligibility import (
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.boat_design_association import (
    DesignAssociationStatus,
    DesignAssociationWriteResult,
    associate_physical_boat_design,
    fetch_boat_design_candidate,
    search_boat_design_candidates,
)
from hullq.persistence.broker_identity import (
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.security.session_token import SessionClaims

__all__ = [
    "DesignAssociationOutcome",
    "DesignAssociationWriteApplicationResult",
    "DesignLinkStatus",
    "DesignReadOutcome",
    "DesignReadResult",
    "DesignReadView",
    "DesignSelectorOutcome",
    "DesignSelectorResult",
    "associate_organization_listing_design",
    "get_organization_listing_design_association",
    "search_organization_listing_design_candidates",
]


# ---------------------------------------------------------------------------
# Shared actor authorization -- mirrors
# hullq.application.inventory_editing._authorize_editor_actor
# ---------------------------------------------------------------------------


class _ActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


@dataclass(frozen=True)
class _AuthorizedActor:
    organization: MarketplaceOrganization
    membership: OrganizationMembership | None


def _authorize_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> tuple[_ActorAuthorizationOutcome, _AuthorizedActor | None]:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _ActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _ActorAuthorizationOutcome.MFA_REQUIRED, None

    organization = fetch_marketplace_organization(conn, organization_id)
    if organization is None:
        return _ActorAuthorizationOutcome.NOT_FOUND_OR_DENIED, None
    membership = fetch_membership_for_account_and_organization(
        conn, session.account_id, organization_id
    )
    return (
        _ActorAuthorizationOutcome.AUTHORIZED,
        _AuthorizedActor(organization=organization, membership=membership),
    )


def _fetch_owned_listing_physical_boat_id(
    conn: Any, native_listing_id: NativeListingId, organization_id: MarketplaceOrganizationId
) -> tuple[bool, PhysicalBoatId | None]:
    """`(found, physical_boat_id)` for *native_listing_id* iff it exists,
    is owned by *organization_id*, and its MarketEpisode -> PhysicalBoat
    chain fully resolves. `(True, None)` means the listing itself was found
    and owned but the chain is incomplete (CHAIN_INCOMPLETE territory);
    `(False, None)` means unknown/foreign (non-enumerating LISTING_NOT_FOUND
    territory)."""
    listing_record = fetch_native_listing(conn, native_listing_id)
    if listing_record is None or listing_record.publishing_organization_id != organization_id:
        return False, None
    if listing_record.listing.market_episode_id is None:
        return True, None
    market_episode_record = fetch_market_episode(conn, listing_record.listing.market_episode_id)
    if market_episode_record is None:
        return True, None
    physical_boat_id = market_episode_record.market_episode.physical_boat_id
    if fetch_physical_boat(conn, physical_boat_id) is None:
        return True, None
    return True, physical_boat_id


# ---------------------------------------------------------------------------
# Read: bounded candidate selector search
# ---------------------------------------------------------------------------


class DesignSelectorOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_QUERY = "INVALID_QUERY"
    OK = "OK"


@dataclass(frozen=True)
class DesignSelectorResult:
    outcome: DesignSelectorOutcome
    candidates: tuple[DesignCandidate, ...] | None = None

    def __post_init__(self) -> None:
        if self.outcome is DesignSelectorOutcome.OK:
            if self.candidates is None:
                raise ValueError("An OK selector result must carry candidates")
        elif self.candidates is not None:
            raise ValueError("Only an OK selector result may carry candidates")


def search_organization_listing_design_candidates(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_query: Any,
) -> DesignSelectorResult:
    """Bounded exact-source candidate search, scoped to one owned listing's
    authorized Organization context (Required Behavior #1/#3)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, _actor = _authorize_actor(conn, session, organization_id)
    if auth_outcome is _ActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return DesignSelectorResult(outcome=DesignSelectorOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _ActorAuthorizationOutcome.MFA_REQUIRED:
        return DesignSelectorResult(outcome=DesignSelectorOutcome.MFA_REQUIRED)

    native_listing_id = NativeListingId(native_listing_id_value)
    found, _physical_boat_id = _fetch_owned_listing_physical_boat_id(
        conn, native_listing_id, organization_id
    )
    if not found:
        return DesignSelectorResult(outcome=DesignSelectorOutcome.LISTING_NOT_FOUND)

    try:
        query = parse_design_selector_query(raw_query)
    except InvalidDesignSelectorQueryError:
        return DesignSelectorResult(outcome=DesignSelectorOutcome.INVALID_QUERY)

    candidates = tuple(search_boat_design_candidates(conn, query))
    return DesignSelectorResult(outcome=DesignSelectorOutcome.OK, candidates=candidates)


# ---------------------------------------------------------------------------
# Read: current link status
# ---------------------------------------------------------------------------


class DesignLinkStatus(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    LINKED = "LINKED"


class DesignReadOutcome(StrEnum):
    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    CHAIN_INCOMPLETE = "CHAIN_INCOMPLETE"
    OK = "OK"


@dataclass(frozen=True)
class DesignReadView:
    native_listing_id: str
    link_status: DesignLinkStatus
    boat_design_ref: str | None
    candidate: DesignCandidate | None

    def __post_init__(self) -> None:
        if self.link_status is DesignLinkStatus.LINKED:
            if self.boat_design_ref is None:
                raise ValueError("A LINKED view must carry boat_design_ref")
        elif self.boat_design_ref is not None:
            raise ValueError("An UNRESOLVED view must not carry boat_design_ref")

    def to_public_dict(self) -> dict[str, Any]:
        candidate_dict: dict[str, Any] | None = None
        if self.candidate is not None:
            candidate_dict = {
                "boat_design_ref": self.candidate.boat_design_ref.value,
                "boat_model_id": self.candidate.boat_model_id,
                "canonical_model_name": self.candidate.canonical_model_name,
                "generation": self.candidate.generation,
                "brand_names": list(self.candidate.brand_names),
                "first_built": self.candidate.first_built,
                "last_built": self.candidate.last_built,
            }
        return {
            "native_listing_id": self.native_listing_id,
            "link_status": self.link_status.value,
            "boat_design_ref": self.boat_design_ref,
            "candidate": candidate_dict,
        }


@dataclass(frozen=True)
class DesignReadResult:
    outcome: DesignReadOutcome
    view: DesignReadView | None = None

    def __post_init__(self) -> None:
        if self.outcome is DesignReadOutcome.OK:
            if self.view is None:
                raise ValueError("An OK read result must carry a view")
        elif self.view is not None:
            raise ValueError("Only an OK read result may carry a view")


def get_organization_listing_design_association(
    conn: Any, session: SessionClaims, organization_id_value: str, native_listing_id_value: str
) -> DesignReadResult:
    """Current authoritative link status for one own NativeListing."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, _actor = _authorize_actor(conn, session, organization_id)
    if auth_outcome is _ActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return DesignReadResult(outcome=DesignReadOutcome.ORG_NOT_FOUND_OR_DENIED)
    if auth_outcome is _ActorAuthorizationOutcome.MFA_REQUIRED:
        return DesignReadResult(outcome=DesignReadOutcome.MFA_REQUIRED)

    native_listing_id = NativeListingId(native_listing_id_value)
    found, physical_boat_id = _fetch_owned_listing_physical_boat_id(
        conn, native_listing_id, organization_id
    )
    if not found:
        return DesignReadResult(outcome=DesignReadOutcome.LISTING_NOT_FOUND)
    if physical_boat_id is None:
        return DesignReadResult(outcome=DesignReadOutcome.CHAIN_INCOMPLETE)

    physical_boat_record = fetch_physical_boat(conn, physical_boat_id)
    assert physical_boat_record is not None  # just confirmed above
    stored_ref = physical_boat_record.physical_boat.boat_design_ref
    if stored_ref is None:
        view = DesignReadView(
            native_listing_id=native_listing_id.value,
            link_status=DesignLinkStatus.UNRESOLVED,
            boat_design_ref=None,
            candidate=None,
        )
        return DesignReadResult(outcome=DesignReadOutcome.OK, view=view)

    candidate = fetch_boat_design_candidate(conn, stored_ref)
    view = DesignReadView(
        native_listing_id=native_listing_id.value,
        link_status=DesignLinkStatus.LINKED,
        boat_design_ref=stored_ref.value,
        candidate=candidate,
    )
    return DesignReadResult(outcome=DesignReadOutcome.OK, view=view)


# ---------------------------------------------------------------------------
# Write: explicit confirmed first-time association
# ---------------------------------------------------------------------------


class DesignAssociationOutcome(StrEnum):
    """Mechanically distinct outcomes (mirrors Required Behavior #5's
    bounded vocabulary)."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    DENIED = "DENIED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    CHAIN_INCOMPLETE = "CHAIN_INCOMPLETE"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    DESIGN_NOT_FOUND = "DESIGN_NOT_FOUND"
    SHARED_BOAT_CONFLICT = "SHARED_BOAT_CONFLICT"
    CONFLICT = "CONFLICT"
    ALREADY_LINKED = "ALREADY_LINKED"
    LINKED = "LINKED"


_OUTCOMES_CARRYING_STORED_REF = frozenset(
    {
        DesignAssociationOutcome.LINKED,
        DesignAssociationOutcome.ALREADY_LINKED,
        DesignAssociationOutcome.CONFLICT,
    }
)


@dataclass(frozen=True)
class DesignAssociationWriteApplicationResult:
    outcome: DesignAssociationOutcome
    denial_reason: PublishingEligibilityReason | None = None
    stored_boat_design_ref: str | None = None

    def __post_init__(self) -> None:
        if self.outcome is DesignAssociationOutcome.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry a denial reason")

        if self.outcome in _OUTCOMES_CARRYING_STORED_REF:
            if self.stored_boat_design_ref is None:
                raise ValueError(f"A {self.outcome.value} result must carry stored_boat_design_ref")
        elif self.stored_boat_design_ref is not None:
            raise ValueError(f"A {self.outcome.value} result must not carry stored_boat_design_ref")

    def to_public_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"outcome": self.outcome.value}
        if self.denial_reason is not None:
            body["reason"] = self.denial_reason.value
        if self.stored_boat_design_ref is not None:
            body["boat_design_ref"] = self.stored_boat_design_ref
        return body


def _map_write_result(
    result: DesignAssociationWriteResult,
) -> DesignAssociationWriteApplicationResult:
    if result.status is DesignAssociationStatus.PHYSICAL_BOAT_NOT_FOUND:
        # Defensive only: the caller already confirmed the chain resolves
        # before invoking the write, so this is CHAIN_INCOMPLETE territory
        # if it is ever reached (the PhysicalBoat vanished between the two
        # reads, which no existing mutation path can actually do).
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.CHAIN_INCOMPLETE
        )
    if result.status is DesignAssociationStatus.SHARED_BOAT_CONFLICT:
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.SHARED_BOAT_CONFLICT
        )
    if result.status is DesignAssociationStatus.DESIGN_NOT_FOUND:
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.DESIGN_NOT_FOUND
        )
    if result.status is DesignAssociationStatus.CONFLICT:
        assert result.stored_boat_design_ref is not None
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.CONFLICT,
            stored_boat_design_ref=result.stored_boat_design_ref.value,
        )
    if result.status is DesignAssociationStatus.ALREADY_LINKED:
        assert result.stored_boat_design_ref is not None
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.ALREADY_LINKED,
            stored_boat_design_ref=result.stored_boat_design_ref.value,
        )
    assert result.status is DesignAssociationStatus.LINKED
    assert result.stored_boat_design_ref is not None
    return DesignAssociationWriteApplicationResult(
        outcome=DesignAssociationOutcome.LINKED,
        stored_boat_design_ref=result.stored_boat_design_ref.value,
    )


def associate_organization_listing_design(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    raw_body: Any,
) -> DesignAssociationWriteApplicationResult:
    """Apply one explicit confirmed first-time design association for one
    own NativeListing (Required Behavior #2/#3/#4)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth_outcome, actor = _authorize_actor(conn, session, organization_id)
    if auth_outcome is _ActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.ORG_NOT_FOUND_OR_DENIED
        )
    if auth_outcome is _ActorAuthorizationOutcome.MFA_REQUIRED:
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.MFA_REQUIRED
        )
    assert actor is not None

    try:
        boat_design_ref = parse_design_association_request(raw_body)
    except InvalidDesignAssociationRequestError:
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.INVALID_PAYLOAD
        )

    decision = evaluate_native_listing_publishing_eligibility(
        session.account_id, actor.organization, actor.membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.DENIED, denial_reason=decision.reason
        )

    native_listing_id = NativeListingId(native_listing_id_value)
    found, physical_boat_id = _fetch_owned_listing_physical_boat_id(
        conn, native_listing_id, organization_id
    )
    if not found:
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.LISTING_NOT_FOUND
        )
    if physical_boat_id is None:
        return DesignAssociationWriteApplicationResult(
            outcome=DesignAssociationOutcome.CHAIN_INCOMPLETE
        )

    conn.commit()
    write_result = associate_physical_boat_design(
        conn,
        physical_boat_id=physical_boat_id,
        boat_design_ref=boat_design_ref,
        native_listing_id=native_listing_id,
        confirming_organization_id=organization_id,
        recorded_by_account_id=session.account_id,
    )
    return _map_write_result(write_result)
