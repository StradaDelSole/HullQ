"""FastAPI integration tests for the SLICE-0060 Organization inventory route.

Uses a directly minted session token (`mint_session_token`) rather than a
full OIDC login round-trip: `test_broker_workspace_access_api.py` and
`scripts/inspect_broker_workspace_access.py` already cover the login/
session-minting path end-to-end; this file focuses on the inventory route
itself sitting on top of an already-valid session, exactly mirroring what
`_require_session` accepts from a real login.
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
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
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
    update_membership_state,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_freshness import reconfirm_native_listing
from hullq.persistence.native_listing_lifecycle import (
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.security.session_token import mint_session_token

_SECRET = b"7" * 32


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
    schema_name = f"hullq_s0060api_{uuid.uuid4().hex[:16]}"
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
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _ensure_account(conn: Any, account_id: str) -> None:
    """`organization_memberships.account_id` carries a real foreign key onto
    `accounts` (SLICE-0053's broker actor directory) -- a membership seeded
    for an account_id that was never inserted there fails closed with a
    `ForeignKeyViolation`, exactly as it would for a real, never-logged-in
    identity. This directly inserts the durable `accounts` row a real JIT
    login (`get_or_create_account_for_identity`) would have produced, using
    the exact literal id this test file already names -- the row shape is
    the only thing that matters to the FK, not how it was minted."""
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
    state: MembershipState = MembershipState.ACTIVE,
) -> None:
    conn = psycopg.connect(api_url)
    try:
        _ensure_account(conn, account_id)
        seed_marketplace_organization(
            conn,
            MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_id),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            ),
        )
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId(membership_id),
                account_id=AccountId(account_id),
                organization_id=MarketplaceOrganizationId(org_id),
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=state,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _org_domain(org_id: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership_domain(membership_id: str, account_id: str, org_id: str) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=AccountId(account_id),
        organization_id=MarketplaceOrganizationId(org_id),
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _amount_offer() -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal("125000.00"),
        currency="EUR",
    )


def _poa_offer() -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.POA,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
    )


def _make_active_listing_with_public_read(
    conn: Any,
    *,
    listing_id: str,
    account_id: str,
    org_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    confirmation_id: str,
) -> None:
    """A complete, ACTIVE, freshly reconfirmed listing -- eligible for the
    accepted current public read (contract §8), so it must show a public
    link in the inventory."""
    account = AccountId(account_id)
    org = _org_domain(org_id)
    membership = _membership_domain(membership_id, account_id, org_id)

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    result = create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
        ),
        broker_listing_reference="REF-ACTIVE",
    )
    assert result.status.value in ("created", "already_exists"), result
    offer_result = write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=NativeListingOfferRevisionId(offer_revision_id),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    assert offer_result.status.value in ("created", "already_exists"), offer_result
    conn.commit()

    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result

    reconfirm_result = reconfirm_native_listing(
        conn,
        confirmation_id=FreshnessConfirmationId(confirmation_id),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert reconfirm_result.status.value == "reconfirmed", reconfirm_result


class TestInventoryAuthorizationBoundary:
    def test_unauthenticated_request_is_denied(self, client: TestClient) -> None:
        response = client.get("/api/broker/organizations/ORG-INV-UNAUTH/inventory")
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-INV-API-1")
        response = client.get("/api/broker/organizations/ORG-INV-NEVER-CREATED/inventory")
        assert response.status_code == 404

    def test_privileged_membership_without_mfa_is_blocked(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-INV-MFA", account_id="ACC-INV-MFA", membership_id="OM-INV-MFA"
        )
        _log_in(client, "ACC-INV-MFA", mfa=False)
        response = client.get("/api/broker/organizations/ORG-INV-MFA/inventory")
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}

    def test_cross_organization_membership_is_not_found(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-INV-CROSS-OTHER",
            account_id="ACC-INV-CROSS-OTHER",
            membership_id="OM-INV-CROSS-OTHER",
        )
        _log_in(client, "ACC-INV-CROSS-SELF")
        response = client.get("/api/broker/organizations/ORG-INV-CROSS-OTHER/inventory")
        assert response.status_code == 404

    def test_revoked_membership_after_login_fails_closed(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-INV-REVOKE",
            account_id="ACC-INV-REVOKE",
            membership_id="OM-INV-REVOKE",
        )
        _log_in(client, "ACC-INV-REVOKE")
        first = client.get("/api/broker/organizations/ORG-INV-REVOKE/inventory")
        assert first.status_code == 200

        conn = psycopg.connect(api_url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-INV-REVOKE"), MembershipState.INACTIVE
            )
            conn.commit()
        finally:
            conn.close()

        second = client.get("/api/broker/organizations/ORG-INV-REVOKE/inventory")
        assert second.status_code == 404


class TestInventoryTruth:
    def test_authorized_zero_listing_organization_is_ordinary_empty(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-INV-EMPTY-API",
            account_id="ACC-INV-EMPTY",
            membership_id="OM-INV-EMPTY",
        )
        _log_in(client, "ACC-INV-EMPTY")
        response = client.get("/api/broker/organizations/ORG-INV-EMPTY-API/inventory")
        assert response.status_code == 200
        assert response.json() == {"items": []}

    def test_mixed_lifecycle_offer_freshness_and_public_link_facts(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id = "ORG-INV-MIXED"
        account_id = "ACC-INV-MIXED"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id="OM-INV-MIXED"
        )
        org = _org_domain(org_id)
        membership = _membership_domain("OM-INV-MIXED", account_id, org_id)
        account = AccountId(account_id)

        conn = psycopg.connect(api_url)
        try:
            # ACTIVE, fresh, publicly readable, AMOUNT offer.
            _make_active_listing_with_public_read(
                conn,
                listing_id="NL-INV-MIXED-ACTIVE",
                account_id=account_id,
                org_id=org_id,
                membership_id="OM-INV-MIXED",
                physical_boat_id="PB-INV-MIXED-ACTIVE",
                market_episode_id="ME-INV-MIXED-ACTIVE",
                offer_revision_id="REV-INV-MIXED-ACTIVE",
                confirmation_id="CONF-INV-MIXED-ACTIVE",
            )

            # DRAFT: no offer, never published -> not publicly readable,
            # freshness UNKNOWN (never confirmed).
            draft_result = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(id=NativeListingId("NL-INV-MIXED-DRAFT")),
            )
            assert draft_result.status.value in ("created", "already_exists")
            conn.commit()

            # WITHDRAWN: complete chain, POA offer, published then withdrawn
            # -> lifecycle WITHDRAWN, never SOLD, no public link.
            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-INV-MIXED-WD"))
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-INV-MIXED-WD"),
                    physical_boat_id=PhysicalBoatId("PB-INV-MIXED-WD"),
                ),
            )
            wd_create = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId("NL-INV-MIXED-WD"),
                    market_episode_id=MarketEpisodeId("ME-INV-MIXED-WD"),
                ),
            )
            assert wd_create.status.value in ("created", "already_exists")
            wd_offer = write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-INV-MIXED-WD"),
                revision_id=NativeListingOfferRevisionId("REV-INV-MIXED-WD"),
                expected_current_revision_id=None,
                offer=_poa_offer(),
            )
            assert wd_offer.status.value in ("created", "already_exists")
            conn.commit()
            publish_wd = publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-INV-MIXED-WD"),
            )
            assert publish_wd.status.value == "transitioned"
            withdraw_wd = withdraw_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-INV-MIXED-WD"),
            )
            assert withdraw_wd.status.value == "transitioned"
        finally:
            conn.close()

        _log_in(client, account_id)
        response = client.get(f"/api/broker/organizations/{org_id}/inventory")
        assert response.status_code == 200
        body = response.json()
        by_id = {item["native_listing_id"]: item for item in body["items"]}
        assert set(by_id) == {"NL-INV-MIXED-ACTIVE", "NL-INV-MIXED-DRAFT", "NL-INV-MIXED-WD"}

        active = by_id["NL-INV-MIXED-ACTIVE"]
        assert active["lifecycle_state"] == "ACTIVE"
        assert active["offer"] == {"kind": "AMOUNT", "amount": "125000.00", "currency": "EUR"}
        assert active["freshness_status"] == "CONFIRMED"
        assert active["last_confirmed_at"] is not None
        assert active["is_publicly_listed"] is True

        draft = by_id["NL-INV-MIXED-DRAFT"]
        assert draft["lifecycle_state"] == "DRAFT"
        assert draft["offer"] == {"kind": "NO_CURRENT_OFFER", "amount": None, "currency": None}
        assert draft["freshness_status"] == "UNKNOWN"
        assert draft["last_confirmed_at"] is None
        assert draft["is_publicly_listed"] is False

        withdrawn = by_id["NL-INV-MIXED-WD"]
        assert withdrawn["lifecycle_state"] == "WITHDRAWN"
        assert withdrawn["lifecycle_state"] != "SOLD"
        assert withdrawn["offer"] == {"kind": "POA", "amount": None, "currency": None}
        assert withdrawn["is_publicly_listed"] is False

        # Deterministic created_at DESC ordering: the most recently created
        # listing (WITHDRAWN, created last in this test) appears first.
        ordered_ids = [item["native_listing_id"] for item in body["items"]]
        assert ordered_ids[0] == "NL-INV-MIXED-WD"

    def test_other_organization_listing_never_appears(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-INV-SELF",
            account_id="ACC-INV-SELF",
            membership_id="OM-INV-SELF",
        )
        other_org = _org_domain("ORG-INV-OTHER")
        other_account = AccountId("ACC-INV-OTHER-OWNER")
        other_membership = OrganizationMembership(
            id=OrganizationMembershipId("OM-INV-OTHER-OWNER"),
            account_id=other_account,
            organization_id=other_org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        conn = psycopg.connect(api_url)
        try:
            _ensure_account(conn, other_account.value)
            seed_marketplace_organization(conn, other_org)
            seed_organization_membership(conn, other_membership)
            conn.commit()
            result = create_native_listing(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                listing=NativeListing(id=NativeListingId("NL-INV-OTHER-ONLY")),
            )
            assert result.status.value in ("created", "already_exists")
            conn.commit()
        finally:
            conn.close()

        _log_in(client, "ACC-INV-SELF")
        response = client.get("/api/broker/organizations/ORG-INV-SELF/inventory")
        assert response.status_code == 200
        assert response.json() == {"items": []}


class TestInventoryPagination:
    def test_invalid_page_size_is_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-INV-PGSIZE",
            account_id="ACC-INV-PGSIZE",
            membership_id="OM-INV-PGSIZE",
        )
        _log_in(client, "ACC-INV-PGSIZE")
        too_big = client.get("/api/broker/organizations/ORG-INV-PGSIZE/inventory?page_size=101")
        zero = client.get("/api/broker/organizations/ORG-INV-PGSIZE/inventory?page_size=0")
        assert too_big.status_code == 400
        assert zero.status_code == 400

    def test_malformed_cursor_fails_closed_as_bounded_client_error(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-INV-BADCURSOR",
            account_id="ACC-INV-BADCURSOR",
            membership_id="OM-INV-BADCURSOR",
        )
        _log_in(client, "ACC-INV-BADCURSOR")
        response = client.get(
            "/api/broker/organizations/ORG-INV-BADCURSOR/inventory?cursor=not-a-valid-cursor!!"
        )
        assert response.status_code == 400

    def test_keyset_continuation_across_pages_has_no_duplicate_or_cross_organization_row(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id = "ORG-INV-PAGES"
        account_id = "ACC-INV-PAGES"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id="OM-INV-PAGES"
        )
        org = _org_domain(org_id)
        membership = _membership_domain("OM-INV-PAGES", account_id, org_id)
        account = AccountId(account_id)

        # A foreign listing in a different Organization: must never surface
        # on any page of this Organization's paginated read.
        other_org = _org_domain("ORG-INV-PAGES-OTHER")
        other_account = AccountId("ACC-INV-PAGES-OTHER")
        other_membership = OrganizationMembership(
            id=OrganizationMembershipId("OM-INV-PAGES-OTHER"),
            account_id=other_account,
            organization_id=other_org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )

        conn = psycopg.connect(api_url)
        try:
            _ensure_account(conn, other_account.value)
            seed_marketplace_organization(conn, other_org)
            seed_organization_membership(conn, other_membership)
            conn.commit()
            other_result = create_native_listing(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                listing=NativeListing(id=NativeListingId("NL-INV-PAGES-FOREIGN")),
            )
            assert other_result.status.value in ("created", "already_exists")

            listing_ids = [f"NL-INV-PAGES-{i:02d}" for i in range(5)]
            for listing_id in listing_ids:
                result = create_native_listing(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    listing=NativeListing(id=NativeListingId(listing_id)),
                )
                assert result.status.value in ("created", "already_exists")
            conn.commit()
        finally:
            conn.close()

        _log_in(client, account_id)
        first = client.get(f"/api/broker/organizations/{org_id}/inventory?page_size=2")
        assert first.status_code == 200
        first_body = first.json()
        assert len(first_body["items"]) == 2
        assert "next_cursor" in first_body

        second = client.get(
            f"/api/broker/organizations/{org_id}/inventory?page_size=2&cursor={first_body['next_cursor']}"
        )
        assert second.status_code == 200
        second_body = second.json()
        assert len(second_body["items"]) == 2
        assert "next_cursor" in second_body

        third = client.get(
            f"/api/broker/organizations/{org_id}/inventory?page_size=2&cursor={second_body['next_cursor']}"
        )
        assert third.status_code == 200
        third_body = third.json()
        assert len(third_body["items"]) == 1
        assert "next_cursor" not in third_body

        all_ids = [
            item["native_listing_id"]
            for page in (first_body, second_body, third_body)
            for item in page["items"]
        ]
        assert set(all_ids) == set(listing_ids)
        assert len(all_ids) == len(set(all_ids))
        assert "NL-INV-PAGES-FOREIGN" not in all_ids
