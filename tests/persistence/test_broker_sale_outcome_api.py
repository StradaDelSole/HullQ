"""FastAPI integration tests for SLICE-0074 broker sale/outcome close-out.

Uses a directly minted session token (`mint_session_token`) rather than a
full OIDC login round-trip -- mirrors `test_broker_inventory_lifecycle_api.py`'s
identical pattern: the login/session-minting path itself is already covered
end-to-end elsewhere; this file focuses on the new sale-outcome read/write
routes sitting on top of an already-valid session.

Covers `specs/BROKER_SALE_OUTCOME_CONTRACT.v0.1.md` §14's required retained
proof items: authorized ACTIVE close-as-SOLD, atomic WITHDRAWN transition,
readable current outcome, exact optional-field preservation, no asking-price
copying, SOLD-on-WITHDRAWN without lifecycle rewrite, non-enumerating
foreign-Organization access, stale expected-head conflict, idempotent retry,
operation-id payload collision, mismatched Lead rejection, cross-Organization
isolation for the same MarketEpisode, ordinary-lifecycle-only public
suppression and correction/superseding revision history.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from starlette.testclient import TestClient

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.buyer_lead import SubmissionOperationId
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.media_gallery import MediaSourceKind
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.persistence.buyer_lead import BuyerLeadCreationStatus, create_buyer_lead
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    fetch_lifecycle_state,
    list_publication_transitions,
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.native_listing_sale_outcome import list_sale_outcome_revisions
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.security.session_token import mint_session_token

_SECRET = b"7" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "broker-sale-outcome-v1"


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


@pytest.fixture()
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0074api_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def client(api_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _ensure_account(conn: Any, account_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )


def _session_cookie(account_id: str, *, mfa: bool = True) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=mfa,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=_SECRET)
    return minted.token


def _log_in(client: TestClient, account_id: str, *, mfa: bool = True) -> None:
    client.cookies.set("hullq_session", _session_cookie(account_id, mfa=mfa), domain="api.test")


def _seed_org_and_membership(
    api_url: str,
    *,
    org_id: str,
    account_id: str,
    membership_id: str,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
    state: MembershipState = MembershipState.ACTIVE,
    publishing_eligibility: OrganizationPublishingEligibility = (
        OrganizationPublishingEligibility.ELIGIBLE
    ),
) -> None:
    conn = psycopg.connect(api_url)
    try:
        _ensure_account(conn, account_id)
        seed_marketplace_organization(
            conn,
            MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_id),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=publishing_eligibility,
            ),
        )
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId(membership_id),
                account_id=AccountId(account_id),
                organization_id=MarketplaceOrganizationId(org_id),
                roles=roles,
                state=state,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _amount_offer(
    *, amount: str = "125000.00", currency: str = "EUR"
) -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal(amount),
        currency=currency,
    )


def _ready_physical_boat_claim() -> PhysicalBoatClaimSnapshot:
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, 2020),
    )


def _attach_ready_cover_image(conn: Any, *, listing_id: str, org_id: str, account_id: str) -> None:
    asset = insert_approved_media_asset(
        conn,
        owner_organization_id=MarketplaceOrganizationId(org_id),
        uploaded_by_account_id=AccountId(account_id),
        rights_declared=True,
        source_kind=MediaSourceKind.BROKER_UPLOAD,
        source_reference=None,
        original_object_key=f"original/{listing_id}",
        derivative_object_key=f"derivative/{listing_id}",
        content_hash=f"hash-{listing_id}",
        mime_type="image/jpeg",
        width=800,
        height=600,
        byte_size=12345,
    )
    placement_result = create_uploaded_image_placement(
        conn,
        native_listing_id=NativeListingId(listing_id),
        owner_organization_id=MarketplaceOrganizationId(org_id),
        media_asset=asset,
    )
    assert placement_result.media_placement_id is not None
    assert placement_result.gallery_version is not None
    cover_result = set_cover(
        conn,
        native_listing_id=NativeListingId(listing_id),
        owner_organization_id=MarketplaceOrganizationId(org_id),
        media_placement_id=placement_result.media_placement_id,
        expected_version=placement_result.gallery_version,
    )
    assert cover_result.outcome.value == "SET", cover_result


def _create_complete_draft_listing(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    offer: NativeListingOfferSnapshot | None = None,
) -> None:
    """Own, complete DRAFT NativeListing satisfying canonical D22
    PublicationReadiness (episode/boat/offer/claim/media/cover) -- mirrors
    `test_broker_inventory_lifecycle_api.py`'s identical helper."""
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(membership_id),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        # create_physical_boat/create_market_episode use
        # `INSERT ... ON CONFLICT (...) DO NOTHING` internally, so calling
        # them again for an already-shared physical_boat_id/market_episode_id
        # (the cross-Organization-same-episode test below) is a safe no-op.
        create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(market_episode_id),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
            ),
        )
        write_native_listing_offer_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=NativeListingOfferRevisionId(offer_revision_id),
            expected_current_revision_id=None,
            offer=offer if offer is not None else _amount_offer(),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
            expected_current_revision_id=None,
            claims=_ready_physical_boat_claim(),
        )
        _attach_ready_cover_image(conn, listing_id=listing_id, org_id=org_id, account_id=account_id)
        conn.commit()
    finally:
        conn.close()


def _publish_directly(api_url: str, *, listing_id: str, org_id: str, account_id: str) -> None:
    """Fast-forward a complete DRAFT listing straight to ACTIVE -- used only
    to set up preconditions; the publish route itself is covered by
    `test_broker_inventory_lifecycle_api.py`."""
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-PUBLISH-{listing_id}"),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert result.status.value == "transitioned", result
        conn.commit()
    finally:
        conn.close()


def _withdraw_directly(api_url: str, *, listing_id: str, org_id: str, account_id: str) -> None:
    """Fast-forward an ACTIVE listing straight to an ordinary (non-SOLD)
    WITHDRAWN -- used only to set up the SOLD-on-already-WITHDRAWN
    precondition."""
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-WITHDRAW-{listing_id}"),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        result = withdraw_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert result.status.value == "transitioned", result
        conn.commit()
    finally:
        conn.close()


def _create_lead(
    api_url: str, *, listing_id: str, org_id: str, submission_operation_id: str
) -> str:
    """Create one real Lead for *listing_id* (which must currently be ACTIVE
    and current-public-eligible) via the accepted SLICE-0070 primitive."""
    conn = psycopg.connect(api_url)
    try:
        result = create_buyer_lead(
            conn,
            submission_operation_id=SubmissionOperationId(submission_operation_id),
            native_listing_id=NativeListingId(listing_id),
            account_id=None,
            buyer_name="Jamie Buyer",
            buyer_email="jamie@example.com",
            buyer_message="Interested in this boat, please call me.",
            as_of=datetime.now(UTC),
        )
        assert result.status is BuyerLeadCreationStatus.CREATED, result
        conn.commit()
        assert result.lead_id is not None
        return result.lead_id.value
    finally:
        conn.close()


def _lifecycle_state(api_url: str, listing_id: str) -> NativeListingLifecycleState | None:
    conn = psycopg.connect(api_url)
    try:
        return fetch_lifecycle_state(conn, NativeListingId(listing_id))
    finally:
        conn.close()


def _transition_count(api_url: str, listing_id: str) -> int:
    conn = psycopg.connect(api_url)
    try:
        return len(list_publication_transitions(conn, NativeListingId(listing_id)))
    finally:
        conn.close()


def _sale_outcome_revision_count(api_url: str, listing_id: str) -> int:
    conn = psycopg.connect(api_url)
    try:
        return len(list_sale_outcome_revisions(conn, NativeListingId(listing_id)))
    finally:
        conn.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _sale_outcome_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/sale-outcome"


def _close_as_sold(
    client: TestClient,
    org_id: str,
    listing_id: str,
    *,
    revision_id: str,
    expected_current_revision_id: str | None = None,
    sold_date: str | None = None,
    achieved_amount: str | None = None,
    achieved_currency: str | None = None,
    originating_lead_id: str | None = None,
) -> Any:
    return client.post(
        _sale_outcome_path(org_id, listing_id),
        json={
            "revision_id": revision_id,
            "expected_current_revision_id": expected_current_revision_id,
            "sold_date": sold_date,
            "achieved_amount": achieved_amount,
            "achieved_currency": achieved_currency,
            "originating_lead_id": originating_lead_id,
        },
        headers=_csrf_headers(),
    )


def _setup_active_listing(
    api_url: str,
    *,
    suffix: str,
    org_id: str | None = None,
    account_id: str | None = None,
    offer: NativeListingOfferSnapshot | None = None,
) -> tuple[str, str, str]:
    """Create one own, complete, ACTIVE NativeListing. Returns
    (org_id, account_id, listing_id)."""
    org_id = org_id or f"ORG-SO-{suffix}"
    account_id = account_id or f"ACC-SO-{suffix}"
    membership_id = f"OM-SO-{suffix}"
    listing_id = f"NL-SO-{suffix}"
    _seed_org_and_membership(
        api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
    )
    _create_complete_draft_listing(
        api_url,
        listing_id=listing_id,
        org_id=org_id,
        account_id=account_id,
        membership_id=membership_id,
        physical_boat_id=f"PB-SO-{suffix}",
        market_episode_id=f"ME-SO-{suffix}",
        offer_revision_id=f"REV-OFFER-SO-{suffix}",
        offer=offer,
    )
    _publish_directly(api_url, listing_id=listing_id, org_id=org_id, account_id=account_id)
    return org_id, account_id, listing_id


# ---------------------------------------------------------------------------
# Authorization / tenancy / basic eligibility
# ---------------------------------------------------------------------------


class TestAuthorizationAndTenancy:
    def test_unauthenticated_post_is_blocked(self, client: TestClient) -> None:
        response = client.post(_sale_outcome_path("ORG-X", "NL-X"), headers=_csrf_headers())
        assert response.status_code == 401

    def test_unauthenticated_get_is_blocked(self, client: TestClient) -> None:
        response = client.get(_sale_outcome_path("ORG-X", "NL-X"))
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-SO-NEVER")
        response = _close_as_sold(
            client, "ORG-SO-NEVER-CREATED", "NL-X", revision_id=str(uuid.uuid4())
        )
        assert response.status_code == 404

    def test_mfa_required_session_writes_nothing(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="MFA")
        _log_in(client, account_id, mfa=False)
        response = _close_as_sold(client, org_id, listing_id, revision_id=str(uuid.uuid4()))
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.ACTIVE
        assert _sale_outcome_revision_count(api_url, listing_id) == 0

    def test_missing_publisher_role_writes_nothing(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, membership_id = "ORG-SO-NOPUB", "ACC-SO-NOPUB", "OM-SO-NOPUB"
        listing_id = "NL-SO-NOPUB"
        _seed_org_and_membership(
            api_url,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _create_complete_draft_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-SO-NOPUB",
            market_episode_id="ME-SO-NOPUB",
            offer_revision_id="REV-SO-NOPUB",
        )
        _publish_directly(api_url, listing_id=listing_id, org_id=org_id, account_id=account_id)
        _log_in(client, account_id, mfa=False)
        response = _close_as_sold(client, org_id, listing_id, revision_id=str(uuid.uuid4()))
        assert response.status_code == 403
        assert response.json() == {
            "error": "publishing_denied",
            "reason": "PUBLISHER_ROLE_REQUIRED",
        }
        assert _sale_outcome_revision_count(api_url, listing_id) == 0

    def test_foreign_and_unknown_listing_share_identical_not_found_shape(
        self, client: TestClient, api_url: str
    ) -> None:
        _, _, victim_listing_id = _setup_active_listing(api_url, suffix="VICTIM")
        _seed_org_and_membership(
            api_url, org_id="ORG-SO-ATTACKER", account_id="ACC-SO-ATTACKER", membership_id="OM-SO-A"
        )
        _log_in(client, "ACC-SO-ATTACKER")
        foreign = _close_as_sold(
            client, "ORG-SO-ATTACKER", victim_listing_id, revision_id=str(uuid.uuid4())
        )
        unknown = _close_as_sold(
            client, "ORG-SO-ATTACKER", "NL-NEVER-CREATED-SO", revision_id=str(uuid.uuid4())
        )
        assert foreign.status_code == unknown.status_code == 404
        assert foreign.content == unknown.content
        assert _lifecycle_state(api_url, victim_listing_id) is NativeListingLifecycleState.ACTIVE
        assert _sale_outcome_revision_count(api_url, victim_listing_id) == 0

        foreign_get = client.get(_sale_outcome_path("ORG-SO-ATTACKER", victim_listing_id))
        unknown_get = client.get(_sale_outcome_path("ORG-SO-ATTACKER", "NL-NEVER-CREATED-SO"))
        assert foreign_get.status_code == unknown_get.status_code == 404
        assert foreign_get.content == unknown_get.content

    def test_draft_listing_is_rejected_and_writes_nothing(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, membership_id = "ORG-SO-DRAFT", "ACC-SO-DRAFT", "OM-SO-DRAFT"
        listing_id = "NL-SO-DRAFT"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        conn = psycopg.connect(api_url)
        try:
            account = AccountId(account_id)
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_id),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId(membership_id),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(id=NativeListingId(listing_id)),
            )
            conn.commit()
        finally:
            conn.close()
        _log_in(client, account_id)
        response = _close_as_sold(client, org_id, listing_id, revision_id=str(uuid.uuid4()))
        assert response.status_code == 409
        assert response.json() == {"error": "draft_not_eligible"}
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.DRAFT
        assert _sale_outcome_revision_count(api_url, listing_id) == 0


# ---------------------------------------------------------------------------
# Contract §14 proof items 1-6: close-as-SOLD core semantics
# ---------------------------------------------------------------------------


class TestCloseAsSoldCoreSemantics:
    def test_close_active_listing_transitions_atomically_and_records_full_outcome(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(
            api_url, suffix="FULL", offer=_amount_offer(amount="125000.00", currency="EUR")
        )
        _log_in(client, account_id)
        lead_id = _create_lead(
            api_url, listing_id=listing_id, org_id=org_id, submission_operation_id="SUB-FULL-1"
        )

        response = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=str(uuid.uuid4()),
            sold_date="2026-09-30",
            achieved_amount="118500.00",
            achieved_currency="EUR",
            originating_lead_id=lead_id,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "CLOSED"
        assert body["lifecycle_state"] == "WITHDRAWN"
        assert body["transitioned_to_withdrawn"] is True
        assert body["current_sale_outcome_revision_id"]

        # proof #2: lifecycle becomes WITHDRAWN atomically.
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.WITHDRAWN
        assert _transition_count(api_url, listing_id) == 2  # DRAFT->ACTIVE, ACTIVE->WITHDRAWN

        # proof #3/#4: current outcome is readable with exact optional fields.
        read = client.get(_sale_outcome_path(org_id, listing_id))
        assert read.status_code == 200
        read_body = read.json()
        assert read_body["lifecycle_state"] == "WITHDRAWN"
        assert read_body["outcome_kind"] == "SOLD"
        assert read_body["sold_date"] == "2026-09-30"
        assert read_body["achieved_amount"] == "118500.00"
        assert read_body["achieved_currency"] == "EUR"
        assert read_body["originating_lead_id"] == lead_id
        assert read_body["recorded_at"]
        # proof #5: achieved price is never the copied 125000.00 asking price.
        assert read_body["achieved_amount"] != "125000.00"

    def test_close_without_optional_fields_does_not_copy_asking_price(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(
            api_url, suffix="NOCOPY", offer=_amount_offer(amount="125000.00", currency="EUR")
        )
        _log_in(client, account_id)
        response = _close_as_sold(client, org_id, listing_id, revision_id=str(uuid.uuid4()))
        assert response.status_code == 200
        assert response.json()["lifecycle_state"] == "WITHDRAWN"

        read = client.get(_sale_outcome_path(org_id, listing_id))
        assert read.status_code == 200
        body = read.json()
        assert body["outcome_kind"] == "SOLD"
        assert body["sold_date"] is None
        assert body["achieved_amount"] is None
        assert body["achieved_currency"] is None
        assert body["originating_lead_id"] is None

    def test_sold_on_already_withdrawn_succeeds_without_lifecycle_rewrite(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="WD")
        _withdraw_directly(api_url, listing_id=listing_id, org_id=org_id, account_id=account_id)
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.WITHDRAWN
        assert _transition_count(api_url, listing_id) == 2

        _log_in(client, account_id)
        response = _close_as_sold(
            client, org_id, listing_id, revision_id=str(uuid.uuid4()), achieved_amount=None
        )
        assert response.status_code == 200
        body = response.json()
        assert body["lifecycle_state"] == "WITHDRAWN"
        assert body["transitioned_to_withdrawn"] is False
        # No new lifecycle transition row was appended.
        assert _transition_count(api_url, listing_id) == 2
        assert _sale_outcome_revision_count(api_url, listing_id) == 1


# ---------------------------------------------------------------------------
# Contract §14 proof items 8-10: concurrency / idempotency
# ---------------------------------------------------------------------------


class TestConcurrencyAndIdempotency:
    def test_stale_expected_head_conflict(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="STALE")
        _log_in(client, account_id)
        first_revision_id = str(uuid.uuid4())
        first = _close_as_sold(
            client, org_id, listing_id, revision_id=first_revision_id, achieved_amount=None
        )
        assert first.status_code == 200
        current_revision_id = first.json()["current_sale_outcome_revision_id"]

        second = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=str(uuid.uuid4()),
            expected_current_revision_id=None,  # stale: real current is first_revision_id
            achieved_amount="90000.00",
            achieved_currency="EUR",
        )
        assert second.status_code == 409
        body = second.json()
        assert body["outcome"] == "STALE_VERSION"
        assert body["current_sale_outcome_revision_id"] == current_revision_id
        assert _sale_outcome_revision_count(api_url, listing_id) == 1

    def test_idempotent_retry_with_identical_revision_id_and_payload(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="RETRY")
        _log_in(client, account_id)
        revision_id = str(uuid.uuid4())

        first = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=revision_id,
            achieved_amount="99000.00",
            achieved_currency="USD",
        )
        second = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=revision_id,
            achieved_amount="99000.00",
            achieved_currency="USD",
        )
        assert first.status_code == second.status_code == 200
        assert first.json()["outcome"] == second.json()["outcome"] == "CLOSED"
        assert (
            first.json()["current_sale_outcome_revision_id"]
            == second.json()["current_sale_outcome_revision_id"]
        )
        assert first.json()["lifecycle_state"] == second.json()["lifecycle_state"] == "WITHDRAWN"
        # Only the first call actually performed the ACTIVE -> WITHDRAWN
        # transition; the exact retry never re-transitions.
        assert first.json()["transitioned_to_withdrawn"] is True
        assert second.json()["transitioned_to_withdrawn"] is False
        assert _sale_outcome_revision_count(api_url, listing_id) == 1
        assert _transition_count(api_url, listing_id) == 2

    def test_operation_id_reused_with_different_payload_is_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id = "ORG-SO-OPCONFLICT"
        account_id = "ACC-SO-OPCONFLICT"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id="OM-SO-OPCONFLICT"
        )
        listing_a, listing_b = "NL-SO-OPCONFLICT-A", "NL-SO-OPCONFLICT-B"
        for listing_id, suffix in ((listing_a, "A"), (listing_b, "B")):
            _create_complete_draft_listing(
                api_url,
                listing_id=listing_id,
                org_id=org_id,
                account_id=account_id,
                membership_id="OM-SO-OPCONFLICT",
                physical_boat_id=f"PB-SO-OPCONFLICT-{suffix}",
                market_episode_id=f"ME-SO-OPCONFLICT-{suffix}",
                offer_revision_id=f"REV-SO-OPCONFLICT-{suffix}",
            )
            _publish_directly(api_url, listing_id=listing_id, org_id=org_id, account_id=account_id)

        _log_in(client, account_id)
        shared_revision_id = str(uuid.uuid4())
        first = _close_as_sold(client, org_id, listing_a, revision_id=shared_revision_id)
        assert first.status_code == 200

        second = _close_as_sold(client, org_id, listing_b, revision_id=shared_revision_id)
        assert second.status_code == 409
        assert second.json()["outcome"] == "STALE_VERSION"
        # listing_b has no current outcome at all -- the collision is against
        # a different NativeListing entirely, never ALREADY_EXISTS for B. No
        # current_sale_outcome_revision_id is carried at all in that case.
        assert "current_sale_outcome_revision_id" not in second.json()
        assert _sale_outcome_revision_count(api_url, listing_b) == 0
        assert _lifecycle_state(api_url, listing_b) is NativeListingLifecycleState.ACTIVE


# ---------------------------------------------------------------------------
# Contract §14 proof item 11: Lead linkage safety
# ---------------------------------------------------------------------------


class TestLeadLinkage:
    def test_mismatched_lead_is_rejected_without_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_a = _setup_active_listing(api_url, suffix="LEADA")
        _, _, listing_b = _setup_active_listing(
            api_url, suffix="LEADB", org_id=org_id, account_id=account_id
        )
        foreign_lead_id = _create_lead(
            api_url, listing_id=listing_b, org_id=org_id, submission_operation_id="SUB-LEADB-1"
        )

        _log_in(client, account_id)
        response = _close_as_sold(
            client,
            org_id,
            listing_a,
            revision_id=str(uuid.uuid4()),
            originating_lead_id=foreign_lead_id,
        )
        assert response.status_code == 422
        assert response.json() == {"error": "invalid_lead"}
        assert _lifecycle_state(api_url, listing_a) is NativeListingLifecycleState.ACTIVE
        assert _sale_outcome_revision_count(api_url, listing_a) == 0

    def test_nonexistent_lead_is_rejected(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="LEADGHOST")
        _log_in(client, account_id)
        response = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=str(uuid.uuid4()),
            originating_lead_id="LEAD-NEVER-CREATED",
        )
        assert response.status_code == 422
        assert response.json() == {"error": "invalid_lead"}
        assert _sale_outcome_revision_count(api_url, listing_id) == 0

    def test_cross_organization_lead_is_rejected(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="LEADXORG")
        other_org_id, _, other_listing_id = _setup_active_listing(api_url, suffix="LEADXORG-OTHER")
        foreign_lead_id = _create_lead(
            api_url,
            listing_id=other_listing_id,
            org_id=other_org_id,
            submission_operation_id="SUB-LEADXORG-1",
        )
        _log_in(client, account_id)
        response = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=str(uuid.uuid4()),
            originating_lead_id=foreign_lead_id,
        )
        assert response.status_code == 422
        assert response.json() == {"error": "invalid_lead"}

    def test_own_matching_lead_is_accepted(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="LEADOK")
        lead_id = _create_lead(
            api_url, listing_id=listing_id, org_id=org_id, submission_operation_id="SUB-LEADOK-1"
        )
        _log_in(client, account_id)
        response = _close_as_sold(
            client, org_id, listing_id, revision_id=str(uuid.uuid4()), originating_lead_id=lead_id
        )
        assert response.status_code == 200
        read = client.get(_sale_outcome_path(org_id, listing_id))
        assert read.json()["originating_lead_id"] == lead_id


# ---------------------------------------------------------------------------
# Contract §14 proof item 12: cross-Organization isolation for the same
# MarketEpisode
# ---------------------------------------------------------------------------


class TestCrossOrganizationMarketEpisodeIsolation:
    def test_second_organization_listing_for_same_market_episode_is_untouched(
        self, client: TestClient, api_url: str
    ) -> None:
        physical_boat_id, market_episode_id = "PB-SO-SHARED", "ME-SO-SHARED"
        conn = psycopg.connect(api_url)
        try:
            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id))
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId(market_episode_id),
                    physical_boat_id=PhysicalBoatId(physical_boat_id),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        org_a, account_a, listing_a = (
            "ORG-SO-SHARED-A",
            "ACC-SO-SHARED-A",
            "NL-SO-SHARED-A",
        )
        _seed_org_and_membership(
            api_url, org_id=org_a, account_id=account_a, membership_id="OM-SHARED-A"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id=listing_a,
            org_id=org_a,
            account_id=account_a,
            membership_id="OM-SHARED-A",
            physical_boat_id=physical_boat_id,
            market_episode_id=market_episode_id,
            offer_revision_id="REV-SHARED-A",
        )
        _publish_directly(api_url, listing_id=listing_a, org_id=org_a, account_id=account_a)

        org_b, account_b, listing_b = (
            "ORG-SO-SHARED-B",
            "ACC-SO-SHARED-B",
            "NL-SO-SHARED-B",
        )
        _seed_org_and_membership(
            api_url, org_id=org_b, account_id=account_b, membership_id="OM-SHARED-B"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id=listing_b,
            org_id=org_b,
            account_id=account_b,
            membership_id="OM-SHARED-B",
            physical_boat_id=physical_boat_id,
            market_episode_id=market_episode_id,
            offer_revision_id="REV-SHARED-B",
        )
        _publish_directly(api_url, listing_id=listing_b, org_id=org_b, account_id=account_b)

        _log_in(client, account_a)
        response = _close_as_sold(client, org_a, listing_a, revision_id=str(uuid.uuid4()))
        assert response.status_code == 200

        assert _lifecycle_state(api_url, listing_a) is NativeListingLifecycleState.WITHDRAWN
        assert _lifecycle_state(api_url, listing_b) is NativeListingLifecycleState.ACTIVE
        assert _sale_outcome_revision_count(api_url, listing_b) == 0


# ---------------------------------------------------------------------------
# Contract §14 proof item 13: public visibility only through ordinary
# lifecycle/current-public semantics
# ---------------------------------------------------------------------------


class TestPublicVisibility:
    def test_public_listing_disappears_only_through_ordinary_lifecycle(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="PUBLIC")
        before = client.get(f"/api/listings/{listing_id}")
        assert before.status_code == 200

        _log_in(client, account_id)
        response = _close_as_sold(client, org_id, listing_id, revision_id=str(uuid.uuid4()))
        assert response.status_code == 200

        after = client.get(f"/api/listings/{listing_id}")
        assert after.status_code == 404


# ---------------------------------------------------------------------------
# Contract §14 proof item 14: correction/superseding revision history
# ---------------------------------------------------------------------------


class TestCorrectionHistory:
    def test_correction_revision_preserves_prior_outcome_history(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="CORRECT")
        _log_in(client, account_id)
        first = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=str(uuid.uuid4()),
            achieved_amount="100000.00",
            achieved_currency="EUR",
        )
        assert first.status_code == 200
        first_revision_id = first.json()["current_sale_outcome_revision_id"]

        second = _close_as_sold(
            client,
            org_id,
            listing_id,
            revision_id=str(uuid.uuid4()),
            expected_current_revision_id=first_revision_id,
            achieved_amount="105000.00",
            achieved_currency="EUR",
        )
        assert second.status_code == 200
        assert second.json()["transitioned_to_withdrawn"] is False  # already WITHDRAWN

        read = client.get(_sale_outcome_path(org_id, listing_id))
        assert read.json()["achieved_amount"] == "105000.00"

        revisions = sorted(
            (
                r.revision_id.value,
                r.outcome.achieved_amount,
                r.previous_revision_id.value if r.previous_revision_id is not None else None,
            )
            for r in _list_revisions(api_url, listing_id)
        )
        assert len(revisions) == 2
        amounts = {str(amount) for _, amount, _ in revisions}
        assert amounts == {"100000.00", "105000.00"}
        # The second revision's previous_revision_id links back to the first.
        second_row = next(r for r in revisions if str(r[1]) == "105000.00")
        assert second_row[2] == first_revision_id


def _list_revisions(api_url: str, listing_id: str) -> list[Any]:
    conn = psycopg.connect(api_url)
    try:
        return list_sale_outcome_revisions(conn, NativeListingId(listing_id))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


class TestCsrf:
    def test_missing_csrf_headers_fails_closed(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="CSRF1")
        _log_in(client, account_id)
        response = client.post(
            _sale_outcome_path(org_id, listing_id), json={"revision_id": str(uuid.uuid4())}
        )
        assert response.status_code == 403
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.ACTIVE

    def test_wrong_origin_fails_closed(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="CSRF2")
        _log_in(client, account_id)
        response = client.post(
            _sale_outcome_path(org_id, listing_id),
            json={"revision_id": str(uuid.uuid4())},
            headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": _CSRF_HEADER_VALUE,
            },
        )
        assert response.status_code == 403
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.ACTIVE

    def test_another_channels_csrf_header_value_is_rejected(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="CSRF3")
        _log_in(client, account_id)
        response = client.post(
            _sale_outcome_path(org_id, listing_id),
            json={"revision_id": str(uuid.uuid4())},
            headers={
                "Origin": _WEB_ORIGIN,
                "X-HullQ-Requested-With": "professional-inventory-lifecycle-v1",
            },
        )
        assert response.status_code == 403
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.ACTIVE

    def test_valid_same_origin_close_succeeds(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="CSRF4")
        _log_in(client, account_id)
        response = _close_as_sold(client, org_id, listing_id, revision_id=str(uuid.uuid4()))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------


class TestInvalidPayload:
    def test_missing_revision_id_is_invalid_payload(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="BADPAYLOAD1")
        _log_in(client, account_id)
        response = client.post(
            _sale_outcome_path(org_id, listing_id),
            json={"expected_current_revision_id": None},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_payload"}

    def test_achieved_amount_without_currency_is_invalid_payload(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="BADPAYLOAD2")
        _log_in(client, account_id)
        response = _close_as_sold(
            client, org_id, listing_id, revision_id=str(uuid.uuid4()), achieved_amount="1000.00"
        )
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_payload"}
        assert _sale_outcome_revision_count(api_url, listing_id) == 0

    def test_malformed_sold_date_is_invalid_payload(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = _setup_active_listing(api_url, suffix="BADPAYLOAD3")
        _log_in(client, account_id)
        response = _close_as_sold(
            client, org_id, listing_id, revision_id=str(uuid.uuid4()), sold_date="not-a-date"
        )
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_payload"}
