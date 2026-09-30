"""FastAPI integration tests for SLICE-0072 post-promotion inventory offer/
PhysicalBoat claim editing.

Mirrors `test_broker_inventory_lifecycle_api.py`'s fixture/session-minting
pattern: a directly minted session token rather than a full OIDC round-trip
(that path is covered by `test_broker_workspace_access_api.py`).

Covers `specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md` §2 (tenancy/
non-enumeration), §5 (optimistic concurrency/idempotency), §7 (ACTIVE hard-
invariant atomicity), §8 (read model), §14 (CSRF) and §15's required
concurrency proofs.
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
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    fetch_current_native_listing_offer,
    list_native_listing_offer_revisions,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    list_physical_boat_claim_revisions,
    write_physical_boat_claim_revision,
)
from hullq.security.session_token import mint_session_token

_SECRET = b"9" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"


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
    schema_name = f"hullq_s0072api_{uuid.uuid4().hex[:16]}"
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
                roles=roles,
                state=state,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _amount_offer(*, price: str = "125000.00") -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal(price),
        currency="EUR",
    )


def _ready_claim(*, build_year: int = 2020) -> PhysicalBoatClaimSnapshot:
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, build_year),
    )


def _create_promoted_listing(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    claim_revision_id: str,
    activate: bool = False,
) -> None:
    """A complete post-promotion NativeListing: episode/boat/offer/claim all
    present -- the identical shape a SLICE-0067 promotion produces. Optionally
    fast-forwarded straight to ACTIVE (bypassing publish's own D22 gate, which
    is exercised elsewhere) to set up ACTIVE-edit preconditions.
    """
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
            offer=_amount_offer(),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(claim_revision_id),
            expected_current_revision_id=None,
            claims=_ready_claim(),
        )
        if activate:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE native_listings SET lifecycle_state = 'ACTIVE' "
                    "WHERE native_listing_id = %s",
                    [listing_id],
                )
        conn.commit()
    finally:
        conn.close()


def _current_offer_revision_id(api_url: str, listing_id: str) -> str | None:
    conn = psycopg.connect(api_url)
    try:
        record = fetch_current_native_listing_offer(conn, NativeListingId(listing_id))
        return record.revision_id.value if record is not None else None
    finally:
        conn.close()


def _current_claim_revision_id(api_url: str, physical_boat_id: str, org_id: str) -> str | None:
    conn = psycopg.connect(api_url)
    try:
        record = fetch_current_physical_boat_claim(
            conn, PhysicalBoatId(physical_boat_id), MarketplaceOrganizationId(org_id)
        )
        return record.revision_id.value if record is not None else None
    finally:
        conn.close()


def _offer_revision_count(api_url: str, listing_id: str) -> int:
    conn = psycopg.connect(api_url)
    try:
        return len(list_native_listing_offer_revisions(conn, NativeListingId(listing_id)))
    finally:
        conn.close()


def _claim_revision_count(api_url: str, physical_boat_id: str, org_id: str) -> int:
    conn = psycopg.connect(api_url)
    try:
        return len(
            list_physical_boat_claim_revisions(
                conn, PhysicalBoatId(physical_boat_id), MarketplaceOrganizationId(org_id)
            )
        )
    finally:
        conn.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _edit_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/edit"


def _offer_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/offer"


def _claim_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/claim"


def _offer_body(
    expected_revision_id: str | None,
    *,
    price: str = "129000.00",
    revision_id: str | None = None,
) -> dict[str, Any]:
    return {
        "revision_id": revision_id if revision_id is not None else str(uuid.uuid4()),
        "expected_current_revision_id": expected_revision_id,
        "listing_offer.asking_price_mode": "AMOUNT",
        "listing_offer.asking_price_amount": price,
        "listing_offer.currency": "EUR",
        "listing_offer.location_country": "FR",
        "listing_offer.broker_description": "Updated broker description.",
    }


def _claim_body(
    expected_revision_id: str | None,
    *,
    build_year: int = 2021,
    revision_id: str | None = None,
) -> dict[str, Any]:
    return {
        "revision_id": revision_id if revision_id is not None else str(uuid.uuid4()),
        "expected_current_revision_id": expected_revision_id,
        "physical_boat.marketed_brand_claim": "Beneteau",
        "physical_boat.model_designation_claim": "Oceanis 30.1",
        "physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": build_year},
    }


# ---------------------------------------------------------------------------
# Read: GET .../edit
# ---------------------------------------------------------------------------


class TestEditDetailRead:
    def test_unauthenticated_read_is_blocked(self, client: TestClient) -> None:
        response = client.get(_edit_path("ORG-X", "NL-X"))
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-READ-1")
        response = client.get(_edit_path("ORG-READ-NEVER", "NL-X"))
        assert response.status_code == 404

    def test_foreign_organization_listing_is_not_found(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-READ-A", account_id="ACC-READ-A", membership_id="OM-READ-A"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-READ-B", account_id="ACC-READ-B", membership_id="OM-READ-B"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-READ-FOREIGN",
            org_id="ORG-READ-B",
            account_id="ACC-READ-B",
            membership_id="OM-READ-B",
            physical_boat_id="PB-READ-FOREIGN",
            market_episode_id="ME-READ-FOREIGN",
            offer_revision_id="REV-READ-FOREIGN",
            claim_revision_id="CLAIM-READ-FOREIGN",
        )
        _log_in(client, "ACC-READ-A")
        response = client.get(_edit_path("ORG-READ-A", "NL-READ-FOREIGN"))
        assert response.status_code == 404

    def test_ok_read_carries_current_offer_and_claim(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-READ-OK", account_id="ACC-READ-OK", membership_id="OM-READ-OK"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-READ-OK",
            org_id="ORG-READ-OK",
            account_id="ACC-READ-OK",
            membership_id="OM-READ-OK",
            physical_boat_id="PB-READ-OK",
            market_episode_id="ME-READ-OK",
            offer_revision_id="REV-READ-OK",
            claim_revision_id="CLAIM-READ-OK",
        )
        _log_in(client, "ACC-READ-OK")
        response = client.get(_edit_path("ORG-READ-OK", "NL-READ-OK"))
        assert response.status_code == 200
        body = response.json()
        assert body["lifecycle_state"] == "DRAFT"
        assert body["current_offer_revision_id"] == "REV-READ-OK"
        assert body["offer"]["listing_offer.asking_price_amount"] == "125000.00"
        assert body["current_claim_revision_id"] == "CLAIM-READ-OK"
        assert body["claim"]["physical_boat.marketed_brand_claim"] == "Beneteau"

    def test_mfa_required_read_is_blocked(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-READ-MFA", account_id="ACC-READ-MFA", membership_id="OM-READ-MFA"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-READ-MFA",
            org_id="ORG-READ-MFA",
            account_id="ACC-READ-MFA",
            membership_id="OM-READ-MFA",
            physical_boat_id="PB-READ-MFA",
            market_episode_id="ME-READ-MFA",
            offer_revision_id="REV-READ-MFA",
            claim_revision_id="CLAIM-READ-MFA",
        )
        _log_in(client, "ACC-READ-MFA", mfa=False)
        response = client.get(_edit_path("ORG-READ-MFA", "NL-READ-MFA"))
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}

    def test_ok_read_on_active_listing_carries_fully_populated_offer_and_claim(
        self, client: TestClient, api_url: str
    ) -> None:
        """Exercises every optional offer/claim wire field (contract §8) and
        the ACTIVE-only current_public_status/suppression_reasons branch --
        the DRAFT-only `test_ok_read_carries_current_offer_and_claim` above
        never populates these."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-READ-FULL",
            account_id="ACC-READ-FULL",
            membership_id="OM-READ-FULL",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-READ-FULL",
            org_id="ORG-READ-FULL",
            account_id="ACC-READ-FULL",
            membership_id="OM-READ-FULL",
            physical_boat_id="PB-READ-FULL",
            market_episode_id="ME-READ-FULL",
            offer_revision_id="REV-READ-FULL",
            claim_revision_id="CLAIM-READ-FULL",
            activate=True,
        )
        _log_in(client, "ACC-READ-FULL")

        full_offer_body = _offer_body("REV-READ-FULL")
        full_offer_body["listing_offer.location_region"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "Brittany",
        }
        full_offer_body["listing_offer.broker_summary"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "Well maintained, single owner.",
        }
        full_offer_body["listing_offer.known_history_narrative"] = {
            "assertion_kind": "NO_KNOWN_HISTORY_DECLARED"
        }
        full_offer_body["listing_offer.vat_tax_status_claim"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "VAT_PAID",
        }
        offer_response = client.post(
            _offer_path("ORG-READ-FULL", "NL-READ-FULL"),
            json=full_offer_body,
            headers=_csrf_headers(),
        )
        assert offer_response.status_code == 200, offer_response.json()

        full_claim_body = _claim_body("CLAIM-READ-FULL")
        full_claim_body["physical_boat.loa_length"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "9.14",
        }
        full_claim_body["physical_boat.draft"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "1.45",
        }
        full_claim_body["physical_boat.keel_configuration"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "FIN",
        }
        full_claim_body["physical_boat.rudder_configuration"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "SPADE",
        }
        full_claim_body["physical_boat.boat_name"] = {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "Serenity",
        }
        claim_response = client.post(
            _claim_path("ORG-READ-FULL", "NL-READ-FULL"),
            json=full_claim_body,
            headers=_csrf_headers(),
        )
        assert claim_response.status_code == 200, claim_response.json()

        response = client.get(_edit_path("ORG-READ-FULL", "NL-READ-FULL"))
        assert response.status_code == 200
        body = response.json()
        assert body["lifecycle_state"] == "ACTIVE"
        assert body["current_public_status"] in ("ELIGIBLE", "SUPPRESSED")
        assert body["suppression_reasons"] is not None
        offer = body["offer"]
        assert offer["listing_offer.location_region"] == {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "Brittany",
        }
        assert offer["listing_offer.broker_summary"]["value"] == "Well maintained, single owner."
        assert offer["listing_offer.known_history_narrative"] == {
            "assertion_kind": "NO_KNOWN_HISTORY_DECLARED",
            "value": None,
        }
        assert offer["listing_offer.vat_tax_status_claim"] == {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "VAT_PAID",
        }
        claim = body["claim"]
        assert claim["physical_boat.loa_length"] == {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "9.14",
        }
        assert claim["physical_boat.draft"] == {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "1.45",
        }
        assert claim["physical_boat.keel_configuration"] == {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "FIN",
        }
        assert claim["physical_boat.rudder_configuration"] == {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "SPADE",
        }
        assert claim["physical_boat.boat_name"] == {
            "assertion_kind": "VALUE_ASSERTION",
            "value": "Serenity",
        }


# ---------------------------------------------------------------------------
# Offer save
# ---------------------------------------------------------------------------


class TestOfferSave:
    def test_missing_csrf_header_is_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-OFF-CSRF", account_id="ACC-OFF-CSRF", membership_id="OM-OFF-CSRF"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-CSRF",
            org_id="ORG-OFF-CSRF",
            account_id="ACC-OFF-CSRF",
            membership_id="OM-OFF-CSRF",
            physical_boat_id="PB-OFF-CSRF",
            market_episode_id="ME-OFF-CSRF",
            offer_revision_id="REV-OFF-CSRF",
            claim_revision_id="CLAIM-OFF-CSRF",
        )
        _log_in(client, "ACC-OFF-CSRF")
        response = client.post(
            _offer_path("ORG-OFF-CSRF", "NL-OFF-CSRF"),
            json=_offer_body("REV-OFF-CSRF"),
            headers={"Origin": _WEB_ORIGIN},
        )
        assert response.status_code == 403
        assert _current_offer_revision_id(api_url, "NL-OFF-CSRF") == "REV-OFF-CSRF"

    def test_invalid_payload_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-OFF-BAD", account_id="ACC-OFF-BAD", membership_id="OM-OFF-BAD"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-BAD",
            org_id="ORG-OFF-BAD",
            account_id="ACC-OFF-BAD",
            membership_id="OM-OFF-BAD",
            physical_boat_id="PB-OFF-BAD",
            market_episode_id="ME-OFF-BAD",
            offer_revision_id="REV-OFF-BAD",
            claim_revision_id="CLAIM-OFF-BAD",
        )
        _log_in(client, "ACC-OFF-BAD")
        body = _offer_body("REV-OFF-BAD")
        body["listing_offer.asking_price_mode"] = "NOT_A_MODE"
        response = client.post(
            _offer_path("ORG-OFF-BAD", "NL-OFF-BAD"), json=body, headers=_csrf_headers()
        )
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_payload"}
        assert _current_offer_revision_id(api_url, "NL-OFF-BAD") == "REV-OFF-BAD"

    def test_successful_save_advances_current_head(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-OFF-OK", account_id="ACC-OFF-OK", membership_id="OM-OFF-OK"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-OK",
            org_id="ORG-OFF-OK",
            account_id="ACC-OFF-OK",
            membership_id="OM-OFF-OK",
            physical_boat_id="PB-OFF-OK",
            market_episode_id="ME-OFF-OK",
            offer_revision_id="REV-OFF-OK",
            claim_revision_id="CLAIM-OFF-OK",
        )
        _log_in(client, "ACC-OFF-OK")
        response = client.post(
            _offer_path("ORG-OFF-OK", "NL-OFF-OK"),
            json=_offer_body("REV-OFF-OK", price="139000.00"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "SAVED"
        new_revision_id = body["current_offer_revision_id"]
        assert new_revision_id != "REV-OFF-OK"
        assert _current_offer_revision_id(api_url, "NL-OFF-OK") == new_revision_id
        assert _offer_revision_count(api_url, "NL-OFF-OK") == 2

    def test_stale_expectation_conflicts_without_overwrite(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-STALE",
            account_id="ACC-OFF-STALE",
            membership_id="OM-OFF-STALE",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-STALE",
            org_id="ORG-OFF-STALE",
            account_id="ACC-OFF-STALE",
            membership_id="OM-OFF-STALE",
            physical_boat_id="PB-OFF-STALE",
            market_episode_id="ME-OFF-STALE",
            offer_revision_id="REV-OFF-STALE",
            claim_revision_id="CLAIM-OFF-STALE",
        )
        _log_in(client, "ACC-OFF-STALE")
        response = client.post(
            _offer_path("ORG-OFF-STALE", "NL-OFF-STALE"),
            json=_offer_body("REV-DOES-NOT-EXIST"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        body = response.json()
        assert body["outcome"] == "STALE_VERSION"
        assert body["current_offer_revision_id"] == "REV-OFF-STALE"
        assert _current_offer_revision_id(api_url, "NL-OFF-STALE") == "REV-OFF-STALE"
        assert _offer_revision_count(api_url, "NL-OFF-STALE") == 1

    def test_identical_retry_does_not_duplicate_current_revision(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-RETRY",
            account_id="ACC-OFF-RETRY",
            membership_id="OM-OFF-RETRY",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-RETRY",
            org_id="ORG-OFF-RETRY",
            account_id="ACC-OFF-RETRY",
            membership_id="OM-OFF-RETRY",
            physical_boat_id="PB-OFF-RETRY",
            market_episode_id="ME-OFF-RETRY",
            offer_revision_id="REV-OFF-RETRY",
            claim_revision_id="CLAIM-OFF-RETRY",
        )
        _log_in(client, "ACC-OFF-RETRY")
        body = _offer_body("REV-OFF-RETRY", price="145000.00")
        first = client.post(
            _offer_path("ORG-OFF-RETRY", "NL-OFF-RETRY"), json=body, headers=_csrf_headers()
        )
        assert first.status_code == 200
        first_new_revision_id = first.json()["current_offer_revision_id"]

        second = client.post(
            _offer_path("ORG-OFF-RETRY", "NL-OFF-RETRY"), json=body, headers=_csrf_headers()
        )
        assert second.status_code == 200
        assert second.json()["current_offer_revision_id"] == first_new_revision_id
        assert _offer_revision_count(api_url, "NL-OFF-RETRY") == 2

    def test_foreign_organization_cannot_edit(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-FOR-A",
            account_id="ACC-OFF-FOR-A",
            membership_id="OM-OFF-FOR-A",
        )
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-FOR-B",
            account_id="ACC-OFF-FOR-B",
            membership_id="OM-OFF-FOR-B",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-FOR",
            org_id="ORG-OFF-FOR-B",
            account_id="ACC-OFF-FOR-B",
            membership_id="OM-OFF-FOR-B",
            physical_boat_id="PB-OFF-FOR",
            market_episode_id="ME-OFF-FOR",
            offer_revision_id="REV-OFF-FOR",
            claim_revision_id="CLAIM-OFF-FOR",
        )
        _log_in(client, "ACC-OFF-FOR-A")
        response = client.post(
            _offer_path("ORG-OFF-FOR-A", "NL-OFF-FOR"),
            json=_offer_body("REV-OFF-FOR"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 404
        assert _current_offer_revision_id(api_url, "NL-OFF-FOR") == "REV-OFF-FOR"

    def test_inactive_membership_observed_fresh_writes_nothing(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-INACT",
            account_id="ACC-OFF-INACT",
            membership_id="OM-OFF-INACT",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-INACT",
            org_id="ORG-OFF-INACT",
            account_id="ACC-OFF-INACT",
            membership_id="OM-OFF-INACT",
            physical_boat_id="PB-OFF-INACT",
            market_episode_id="ME-OFF-INACT",
            offer_revision_id="REV-OFF-INACT",
            claim_revision_id="CLAIM-OFF-INACT",
        )
        # Revoke the membership *after* listing creation -- proves the
        # authorization gate is re-checked fresh on every write, not cached
        # from an earlier request.
        conn = psycopg.connect(api_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE organization_memberships SET state = 'INACTIVE' "
                    "WHERE membership_id = %s",
                    ["OM-OFF-INACT"],
                )
            conn.commit()
        finally:
            conn.close()

        _log_in(client, "ACC-OFF-INACT")
        response = client.post(
            _offer_path("ORG-OFF-INACT", "NL-OFF-INACT"),
            json=_offer_body("REV-OFF-INACT"),
            headers=_csrf_headers(),
        )
        # Non-enumerating workspace boundary (mirrors
        # test_broker_inventory_lifecycle_api.py's identical
        # test_inactive_membership_writes_nothing): an inactive membership
        # is denied at the same 404 boundary as an unknown Organization.
        assert response.status_code == 404
        assert _current_offer_revision_id(api_url, "NL-OFF-INACT") == "REV-OFF-INACT"

    def test_active_listing_ordinary_edit_succeeds(self, client: TestClient, api_url: str) -> None:
        """Confirms the D29-narrowed re-check does not itself block an
        ordinary edit of an already-complete ACTIVE listing -- the D22
        evaluator would incorrectly reject this via LIFECYCLE_NOT_DRAFT."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-ACTIVE",
            account_id="ACC-OFF-ACTIVE",
            membership_id="OM-OFF-ACTIVE",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-ACTIVE",
            org_id="ORG-OFF-ACTIVE",
            account_id="ACC-OFF-ACTIVE",
            membership_id="OM-OFF-ACTIVE",
            physical_boat_id="PB-OFF-ACTIVE",
            market_episode_id="ME-OFF-ACTIVE",
            offer_revision_id="REV-OFF-ACTIVE",
            claim_revision_id="CLAIM-OFF-ACTIVE",
            activate=True,
        )
        _log_in(client, "ACC-OFF-ACTIVE")
        response = client.post(
            _offer_path("ORG-OFF-ACTIVE", "NL-OFF-ACTIVE"),
            json=_offer_body("REV-OFF-ACTIVE", price="150000.00"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "SAVED"

    def test_active_invariant_violation_leaves_prior_head_unchanged(
        self, client: TestClient, api_url: str
    ) -> None:
        """Defensive proof of contract §7's atomic rollback: an ACTIVE
        listing whose MarketEpisode chain is (abnormally) unresolved must
        reject a candidate offer edit atomically, leaving the prior offer
        head untouched -- exercised by directly forcing an otherwise-
        unreachable chain-incomplete + ACTIVE combination."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-INVARIANT",
            account_id="ACC-OFF-INVARIANT",
            membership_id="OM-OFF-INVARIANT",
        )
        conn = psycopg.connect(api_url)
        try:
            account = AccountId("ACC-OFF-INVARIANT")
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-OFF-INVARIANT"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-OFF-INVARIANT"),
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
                listing=NativeListing(id=NativeListingId("NL-OFF-INVARIANT")),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-OFF-INVARIANT"),
                revision_id=NativeListingOfferRevisionId("REV-OFF-INVARIANT"),
                expected_current_revision_id=None,
                offer=_amount_offer(),
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE native_listings SET lifecycle_state = 'ACTIVE' "
                    "WHERE native_listing_id = %s",
                    ["NL-OFF-INVARIANT"],
                )
            conn.commit()
        finally:
            conn.close()

        _log_in(client, "ACC-OFF-INVARIANT")
        response = client.post(
            _offer_path("ORG-OFF-INVARIANT", "NL-OFF-INVARIANT"),
            json=_offer_body("REV-OFF-INVARIANT"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 422
        body = response.json()
        assert body["outcome"] == "ACTIVE_INVARIANT_VIOLATION"
        assert "MARKET_EPISODE_UNRESOLVED" in body["blockers"]
        assert _current_offer_revision_id(api_url, "NL-OFF-INVARIANT") == "REV-OFF-INVARIANT"
        assert _offer_revision_count(api_url, "NL-OFF-INVARIANT") == 1

    def test_mfa_required_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-OFF-MFA", account_id="ACC-OFF-MFA", membership_id="OM-OFF-MFA"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-MFA",
            org_id="ORG-OFF-MFA",
            account_id="ACC-OFF-MFA",
            membership_id="OM-OFF-MFA",
            physical_boat_id="PB-OFF-MFA",
            market_episode_id="ME-OFF-MFA",
            offer_revision_id="REV-OFF-MFA",
            claim_revision_id="CLAIM-OFF-MFA",
        )
        _log_in(client, "ACC-OFF-MFA", mfa=False)
        response = client.post(
            _offer_path("ORG-OFF-MFA", "NL-OFF-MFA"),
            json=_offer_body("REV-OFF-MFA"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}
        assert _current_offer_revision_id(api_url, "NL-OFF-MFA") == "REV-OFF-MFA"

    def test_missing_publisher_role_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-NOPUB",
            account_id="ACC-OFF-NOPUB",
            membership_id="OM-OFF-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-OFF-NOPUB",
            org_id="ORG-OFF-NOPUB",
            account_id="ACC-OFF-NOPUB",
            membership_id="OM-OFF-NOPUB",
            physical_boat_id="PB-OFF-NOPUB",
            market_episode_id="ME-OFF-NOPUB",
            offer_revision_id="REV-OFF-NOPUB",
            claim_revision_id="CLAIM-OFF-NOPUB",
        )
        _log_in(client, "ACC-OFF-NOPUB", mfa=False)  # MEMBER-only: not a PRIVILEGED_MFA_ROLE
        response = client.post(
            _offer_path("ORG-OFF-NOPUB", "NL-OFF-NOPUB"),
            json=_offer_body("REV-OFF-NOPUB"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 403
        assert response.json() == {
            "error": "publishing_denied",
            "reason": "PUBLISHER_ROLE_REQUIRED",
        }
        assert _current_offer_revision_id(api_url, "NL-OFF-NOPUB") == "REV-OFF-NOPUB"

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-OFF-UNKNOWN-ORG")
        response = client.post(
            _offer_path("ORG-OFF-NEVER-CREATED", "NL-X"),
            json=_offer_body(None),
            headers=_csrf_headers(),
        )
        assert response.status_code == 404

    def test_unknown_listing_id_is_not_found(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-OFF-UNKNOWN-NL",
            account_id="ACC-OFF-UNKNOWN-NL",
            membership_id="OM-OFF-UNKNOWN-NL",
        )
        _log_in(client, "ACC-OFF-UNKNOWN-NL")
        response = client.post(
            _offer_path("ORG-OFF-UNKNOWN-NL", "NL-OFF-NEVER-CREATED"),
            json=_offer_body(None),
            headers=_csrf_headers(),
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Claim save
# ---------------------------------------------------------------------------


class TestClaimSave:
    def test_successful_save_advances_current_head(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-CLM-OK", account_id="ACC-CLM-OK", membership_id="OM-CLM-OK"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-CLM-OK",
            org_id="ORG-CLM-OK",
            account_id="ACC-CLM-OK",
            membership_id="OM-CLM-OK",
            physical_boat_id="PB-CLM-OK",
            market_episode_id="ME-CLM-OK",
            offer_revision_id="REV-CLM-OK",
            claim_revision_id="CLAIM-CLM-OK",
        )
        _log_in(client, "ACC-CLM-OK")
        response = client.post(
            _claim_path("ORG-CLM-OK", "NL-CLM-OK"),
            json=_claim_body("CLAIM-CLM-OK", build_year=2022),
            headers=_csrf_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "SAVED"
        new_revision_id = body["current_claim_revision_id"]
        assert new_revision_id != "CLAIM-CLM-OK"
        assert _current_claim_revision_id(api_url, "PB-CLM-OK", "ORG-CLM-OK") == new_revision_id
        assert _claim_revision_count(api_url, "PB-CLM-OK", "ORG-CLM-OK") == 2

    def test_stale_expectation_conflicts_without_overwrite(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-CLM-STALE",
            account_id="ACC-CLM-STALE",
            membership_id="OM-CLM-STALE",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-CLM-STALE",
            org_id="ORG-CLM-STALE",
            account_id="ACC-CLM-STALE",
            membership_id="OM-CLM-STALE",
            physical_boat_id="PB-CLM-STALE",
            market_episode_id="ME-CLM-STALE",
            offer_revision_id="REV-CLM-STALE",
            claim_revision_id="CLAIM-CLM-STALE",
        )
        _log_in(client, "ACC-CLM-STALE")
        response = client.post(
            _claim_path("ORG-CLM-STALE", "NL-CLM-STALE"),
            json=_claim_body("CLAIM-DOES-NOT-EXIST"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        body = response.json()
        assert body["outcome"] == "STALE_VERSION"
        assert body["current_claim_revision_id"] == "CLAIM-CLM-STALE"
        assert (
            _current_claim_revision_id(api_url, "PB-CLM-STALE", "ORG-CLM-STALE")
            == "CLAIM-CLM-STALE"
        )
        assert _claim_revision_count(api_url, "PB-CLM-STALE", "ORG-CLM-STALE") == 1

    def test_reused_revision_id_with_different_content_conflicts(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-CLM-REUSE",
            account_id="ACC-CLM-REUSE",
            membership_id="OM-CLM-REUSE",
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-CLM-REUSE",
            org_id="ORG-CLM-REUSE",
            account_id="ACC-CLM-REUSE",
            membership_id="OM-CLM-REUSE",
            physical_boat_id="PB-CLM-REUSE",
            market_episode_id="ME-CLM-REUSE",
            offer_revision_id="REV-CLM-REUSE",
            claim_revision_id="CLAIM-CLM-REUSE",
        )
        # Directly write a second claim revision reusing a fixed id, then
        # attempt the same id again through the HTTP route with different
        # content -- proves a revision-id collision with divergent content
        # conflicts rather than silently overwriting.
        conn = psycopg.connect(api_url)
        try:
            account = AccountId("ACC-CLM-REUSE")
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-CLM-REUSE"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-CLM-REUSE"),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            result = write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-CLM-REUSE"),
                revision_id=PhysicalBoatClaimRevisionId("CLAIM-CLM-REUSE-2"),
                expected_current_revision_id=PhysicalBoatClaimRevisionId("CLAIM-CLM-REUSE"),
                claims=_ready_claim(build_year=2023),
            )
            assert result.status.value == "revised", result
            conn.commit()
        finally:
            conn.close()

        # Resend the *already-used* "CLAIM-CLM-REUSE-2" revision id, with its
        # real recorded predecessor but different content -- the exact
        # "reused identity with different immutable content" case (contract
        # §5), distinct from a plain stale-expectation conflict.
        _log_in(client, "ACC-CLM-REUSE")
        response = client.post(
            _claim_path("ORG-CLM-REUSE", "NL-CLM-REUSE"),
            json={
                "revision_id": "CLAIM-CLM-REUSE-2",
                "expected_current_revision_id": "CLAIM-CLM-REUSE",
                "physical_boat.marketed_brand_claim": "Beneteau",
                "physical_boat.model_designation_claim": "Oceanis 30.1",
                "physical_boat.build_year": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": 2024,
                },
            },
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json()["outcome"] == "STALE_VERSION"
        assert (
            _current_claim_revision_id(api_url, "PB-CLM-REUSE", "ORG-CLM-REUSE")
            == "CLAIM-CLM-REUSE-2"
        )

    def test_mfa_required_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-CLM-MFA", account_id="ACC-CLM-MFA", membership_id="OM-CLM-MFA"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-CLM-MFA",
            org_id="ORG-CLM-MFA",
            account_id="ACC-CLM-MFA",
            membership_id="OM-CLM-MFA",
            physical_boat_id="PB-CLM-MFA",
            market_episode_id="ME-CLM-MFA",
            offer_revision_id="REV-CLM-MFA",
            claim_revision_id="CLAIM-CLM-MFA",
        )
        _log_in(client, "ACC-CLM-MFA", mfa=False)
        response = client.post(
            _claim_path("ORG-CLM-MFA", "NL-CLM-MFA"),
            json=_claim_body("CLAIM-CLM-MFA"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}
        assert _current_claim_revision_id(api_url, "PB-CLM-MFA", "ORG-CLM-MFA") == "CLAIM-CLM-MFA"

    def test_missing_publisher_role_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-CLM-NOPUB",
            account_id="ACC-CLM-NOPUB",
            membership_id="OM-CLM-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-CLM-NOPUB",
            org_id="ORG-CLM-NOPUB",
            account_id="ACC-CLM-NOPUB",
            membership_id="OM-CLM-NOPUB",
            physical_boat_id="PB-CLM-NOPUB",
            market_episode_id="ME-CLM-NOPUB",
            offer_revision_id="REV-CLM-NOPUB",
            claim_revision_id="CLAIM-CLM-NOPUB",
        )
        _log_in(client, "ACC-CLM-NOPUB", mfa=False)  # MEMBER-only: not a PRIVILEGED_MFA_ROLE
        response = client.post(
            _claim_path("ORG-CLM-NOPUB", "NL-CLM-NOPUB"),
            json=_claim_body("CLAIM-CLM-NOPUB"),
            headers=_csrf_headers(),
        )
        assert response.status_code == 403
        assert response.json() == {
            "error": "publishing_denied",
            "reason": "PUBLISHER_ROLE_REQUIRED",
        }
        assert (
            _current_claim_revision_id(api_url, "PB-CLM-NOPUB", "ORG-CLM-NOPUB")
            == "CLAIM-CLM-NOPUB"
        )

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-CLM-UNKNOWN-ORG")
        response = client.post(
            _claim_path("ORG-CLM-NEVER-CREATED", "NL-X"),
            json=_claim_body(None),
            headers=_csrf_headers(),
        )
        assert response.status_code == 404

    def test_unknown_listing_id_is_not_found(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-CLM-UNKNOWN-NL",
            account_id="ACC-CLM-UNKNOWN-NL",
            membership_id="OM-CLM-UNKNOWN-NL",
        )
        _log_in(client, "ACC-CLM-UNKNOWN-NL")
        response = client.post(
            _claim_path("ORG-CLM-UNKNOWN-NL", "NL-CLM-NEVER-CREATED"),
            json=_claim_body(None),
            headers=_csrf_headers(),
        )
        assert response.status_code == 404

    def test_invalid_payload_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-CLM-BAD", account_id="ACC-CLM-BAD", membership_id="OM-CLM-BAD"
        )
        _create_promoted_listing(
            api_url,
            listing_id="NL-CLM-BAD",
            org_id="ORG-CLM-BAD",
            account_id="ACC-CLM-BAD",
            membership_id="OM-CLM-BAD",
            physical_boat_id="PB-CLM-BAD",
            market_episode_id="ME-CLM-BAD",
            offer_revision_id="REV-CLM-BAD",
            claim_revision_id="CLAIM-CLM-BAD",
        )
        _log_in(client, "ACC-CLM-BAD")
        body = _claim_body("CLAIM-CLM-BAD")
        del body["physical_boat.marketed_brand_claim"]
        response = client.post(
            _claim_path("ORG-CLM-BAD", "NL-CLM-BAD"), json=body, headers=_csrf_headers()
        )
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_payload"}
        assert _current_claim_revision_id(api_url, "PB-CLM-BAD", "ORG-CLM-BAD") == "CLAIM-CLM-BAD"

    def test_chain_incomplete_writes_nothing(self, client: TestClient, api_url: str) -> None:
        """A claim edit against a NativeListing with no MarketEpisode link at
        all fails closed as CHAIN_INCOMPLETE -- distinct from STALE_VERSION/
        NOT_FOUND (contract: the claim authority is about the concrete
        PhysicalBoat reached through the NativeListing -> MarketEpisode ->
        PhysicalBoat chain)."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-CLM-CHAIN",
            account_id="ACC-CLM-CHAIN",
            membership_id="OM-CLM-CHAIN",
        )
        conn = psycopg.connect(api_url)
        try:
            account = AccountId("ACC-CLM-CHAIN")
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-CLM-CHAIN"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-CLM-CHAIN"),
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
                listing=NativeListing(id=NativeListingId("NL-CLM-CHAIN")),
            )
            conn.commit()
        finally:
            conn.close()

        _log_in(client, "ACC-CLM-CHAIN")
        response = client.post(
            _claim_path("ORG-CLM-CHAIN", "NL-CLM-CHAIN"),
            json=_claim_body(None),
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json() == {"error": "chain_incomplete"}

    def test_active_invariant_violation_leaves_prior_head_unchanged(
        self, client: TestClient, api_url: str
    ) -> None:
        """A claim edit's own write always resolves the chain FIRST (contract
        §3: claim authority is about the concrete PhysicalBoat reached
        through NativeListing -> MarketEpisode -> PhysicalBoat) -- unlike the
        offer-edit proof, a *chain-incomplete* ACTIVE listing can never reach
        the ACTIVE-invariant re-check for a claim edit at all (it fails
        CHAIN_INCOMPLETE first, proven above). This listing instead has a
        COMPLETE chain (claim write succeeds) but no current offer at all,
        so the D29 re-check's OFFER_MISSING blocker fires after the claim
        write, and the whole attempt -- including the just-written claim
        revision -- rolls back atomically."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-CLM-INVARIANT",
            account_id="ACC-CLM-INVARIANT",
            membership_id="OM-CLM-INVARIANT",
        )
        conn = psycopg.connect(api_url)
        try:
            account = AccountId("ACC-CLM-INVARIANT")
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-CLM-INVARIANT"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-CLM-INVARIANT"),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-CLM-INVARIANT"))
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-CLM-INVARIANT"),
                    physical_boat_id=PhysicalBoatId("PB-CLM-INVARIANT"),
                ),
            )
            create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId("NL-CLM-INVARIANT"),
                    market_episode_id=MarketEpisodeId("ME-CLM-INVARIANT"),
                ),
            )
            claim_result = write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-CLM-INVARIANT"),
                revision_id=PhysicalBoatClaimRevisionId("CLAIM-CLM-INVARIANT"),
                expected_current_revision_id=None,
                claims=_ready_claim(),
            )
            assert claim_result.status.value == "created", claim_result
            # Deliberately no offer written at all: forces D29's
            # OFFER_MISSING blocker once this listing is ACTIVE.
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE native_listings SET lifecycle_state = 'ACTIVE' "
                    "WHERE native_listing_id = %s",
                    ["NL-CLM-INVARIANT"],
                )
            conn.commit()
        finally:
            conn.close()

        _log_in(client, "ACC-CLM-INVARIANT")
        response = client.post(
            _claim_path("ORG-CLM-INVARIANT", "NL-CLM-INVARIANT"),
            json=_claim_body("CLAIM-CLM-INVARIANT", build_year=2022),
            headers=_csrf_headers(),
        )
        assert response.status_code == 422
        body = response.json()
        assert body["outcome"] == "ACTIVE_INVARIANT_VIOLATION"
        assert "OFFER_MISSING" in body["blockers"]
        assert (
            _current_claim_revision_id(api_url, "PB-CLM-INVARIANT", "ORG-CLM-INVARIANT")
            == "CLAIM-CLM-INVARIANT"
        )
        assert _claim_revision_count(api_url, "PB-CLM-INVARIANT", "ORG-CLM-INVARIANT") == 1
