"""FastAPI integration tests for SLICE-0082 broker-confirmed PhysicalBoat ->
canonical BoatDesign first association.

Mirrors `test_broker_inventory_editing_api.py`'s fixture/session-minting
pattern: a directly minted session token rather than a full OIDC round-trip.

Covers the slice's Required Behavior §1-§5: bounded candidate search,
explicit confirmation, Organization/MFA/PUBLISHER authorization and
non-enumeration, atomic CAS write + idempotency/conflict, and the current-
link readback vocabulary.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
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
from hullq.persistence.physical_boat import create_physical_boat, fetch_physical_boat
from hullq.security.session_token import mint_session_token

_SECRET = b"9" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "broker-design-association-v1"


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
    schema_name = f"hullq_s0082api_{uuid.uuid4().hex[:16]}"
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


def _insert_canonical_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", "{}", "[]", "[]", "{}", "1" * 64],
        )
    conn.commit()


def _create_unlinked_listing(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
) -> None:
    """The exact shape SLICE-0067 promotion produces: a fresh, design-
    unresolved PhysicalBoat/MarketEpisode/NativeListing chain."""
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
        conn.commit()
    finally:
        conn.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _candidates_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/design-candidates"


def _association_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/design-association"


# ---------------------------------------------------------------------------
# GET candidates
# ---------------------------------------------------------------------------


class TestDesignCandidatesRead:
    def test_unauthenticated_is_blocked(self, client: TestClient) -> None:
        response = client.get(_candidates_path("ORG-X", "NL-X"))
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-CAND-1")
        response = client.get(_candidates_path("ORG-CAND-NEVER", "NL-X"))
        assert response.status_code == 404

    def test_foreign_listing_is_not_found(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-CAND-A", account_id="ACC-CAND-A", membership_id="OM-CAND-A"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-CAND-B", account_id="ACC-CAND-B", membership_id="OM-CAND-B"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-CAND-FOREIGN",
            org_id="ORG-CAND-B",
            account_id="ACC-CAND-B",
            membership_id="OM-CAND-B",
            physical_boat_id="PB-CAND-FOREIGN",
            market_episode_id="ME-CAND-FOREIGN",
        )
        _log_in(client, "ACC-CAND-A")
        response = client.get(_candidates_path("ORG-CAND-A", "NL-CAND-FOREIGN"))
        assert response.status_code == 404

    def test_mfa_required_blocks_read(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-CAND-MFA", account_id="ACC-CAND-MFA", membership_id="OM-CAND-MFA"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-CAND-MFA",
            org_id="ORG-CAND-MFA",
            account_id="ACC-CAND-MFA",
            membership_id="OM-CAND-MFA",
            physical_boat_id="PB-CAND-MFA",
            market_episode_id="ME-CAND-MFA",
        )
        _log_in(client, "ACC-CAND-MFA", mfa=False)
        response = client.get(_candidates_path("ORG-CAND-MFA", "NL-CAND-MFA"))
        assert response.status_code == 403
        assert response.json()["error"] == "mfa_required"

    def test_ok_read_returns_bounded_candidates(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-CAND-OK", account_id="ACC-CAND-OK", membership_id="OM-CAND-OK"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-CAND-OK",
            org_id="ORG-CAND-OK",
            account_id="ACC-CAND-OK",
            membership_id="OM-CAND-OK",
            physical_boat_id="PB-CAND-OK",
            market_episode_id="ME-CAND-OK",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_canonical_boat_design(conn, "BD-CAND-OK", "BM-CAND-OK")
        finally:
            conn.close()
        _log_in(client, "ACC-CAND-OK")
        response = client.get(_candidates_path("ORG-CAND-OK", "NL-CAND-OK"))
        assert response.status_code == 200
        candidates = response.json()["candidates"]
        assert any(c["boat_design_ref"] == "BD-CAND-OK" for c in candidates)

    def test_over_max_length_query_is_invalid(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-CAND-LONG",
            account_id="ACC-CAND-LONG",
            membership_id="OM-CAND-LONG",
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-CAND-LONG",
            org_id="ORG-CAND-LONG",
            account_id="ACC-CAND-LONG",
            membership_id="OM-CAND-LONG",
            physical_boat_id="PB-CAND-LONG",
            market_episode_id="ME-CAND-LONG",
        )
        _log_in(client, "ACC-CAND-LONG")
        response = client.get(
            _candidates_path("ORG-CAND-LONG", "NL-CAND-LONG"), params={"q": "x" * 500}
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET current link status
# ---------------------------------------------------------------------------


class TestDesignAssociationRead:
    def test_unresolved_before_any_write(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-READ-UNR", account_id="ACC-READ-UNR", membership_id="OM-READ-UNR"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-READ-UNR",
            org_id="ORG-READ-UNR",
            account_id="ACC-READ-UNR",
            membership_id="OM-READ-UNR",
            physical_boat_id="PB-READ-UNR",
            market_episode_id="ME-READ-UNR",
        )
        _log_in(client, "ACC-READ-UNR")
        response = client.get(_association_path("ORG-READ-UNR", "NL-READ-UNR"))
        assert response.status_code == 200
        assert response.json()["link_status"] == "UNRESOLVED"
        assert response.json()["boat_design_ref"] is None


# ---------------------------------------------------------------------------
# POST association write
# ---------------------------------------------------------------------------


class TestAssociateDesign:
    def test_unauthenticated_is_blocked(self, client: TestClient) -> None:
        response = client.post(_association_path("ORG-X", "NL-X"), json={"boat_design_ref": "BD-1"})
        assert response.status_code == 401

    def test_missing_csrf_header_is_blocked(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-CSRF", account_id="ACC-CSRF", membership_id="OM-CSRF"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-CSRF",
            org_id="ORG-CSRF",
            account_id="ACC-CSRF",
            membership_id="OM-CSRF",
            physical_boat_id="PB-CSRF",
            market_episode_id="ME-CSRF",
        )
        _log_in(client, "ACC-CSRF")
        response = client.post(
            _association_path("ORG-CSRF", "NL-CSRF"), json={"boat_design_ref": "BD-1"}
        )
        assert response.status_code == 403

    def test_mfa_required_blocks_write(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-WMFA", account_id="ACC-WMFA", membership_id="OM-WMFA"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-WMFA",
            org_id="ORG-WMFA",
            account_id="ACC-WMFA",
            membership_id="OM-WMFA",
            physical_boat_id="PB-WMFA",
            market_episode_id="ME-WMFA",
        )
        _log_in(client, "ACC-WMFA", mfa=False)
        response = client.post(
            _association_path("ORG-WMFA", "NL-WMFA"),
            json={"boat_design_ref": "BD-1"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 403
        assert response.json()["error"] == "mfa_required"

    def test_publisher_role_required(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-NOPUB",
            account_id="ACC-NOPUB",
            membership_id="OM-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-NOPUB",
            org_id="ORG-NOPUB",
            account_id="ACC-NOPUB",
            membership_id="OM-NOPUB",
            physical_boat_id="PB-NOPUB",
            market_episode_id="ME-NOPUB",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_canonical_boat_design(conn, "BD-NOPUB", "BM-NOPUB")
        finally:
            conn.close()
        _log_in(client, "ACC-NOPUB")
        response = client.post(
            _association_path("ORG-NOPUB", "NL-NOPUB"),
            json={"boat_design_ref": "BD-NOPUB"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 403
        assert response.json()["reason"] == "PUBLISHER_ROLE_REQUIRED"

    def test_foreign_listing_is_not_found(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-WFOR-A", account_id="ACC-WFOR-A", membership_id="OM-WFOR-A"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-WFOR-B", account_id="ACC-WFOR-B", membership_id="OM-WFOR-B"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-WFOR",
            org_id="ORG-WFOR-B",
            account_id="ACC-WFOR-B",
            membership_id="OM-WFOR-B",
            physical_boat_id="PB-WFOR",
            market_episode_id="ME-WFOR",
        )
        _log_in(client, "ACC-WFOR-A")
        response = client.post(
            _association_path("ORG-WFOR-A", "NL-WFOR"),
            json={"boat_design_ref": "BD-1"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 404

    def test_invalid_payload_shape(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-INV", account_id="ACC-INV", membership_id="OM-INV"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-INV",
            org_id="ORG-INV",
            account_id="ACC-INV",
            membership_id="OM-INV",
            physical_boat_id="PB-INV",
            market_episode_id="ME-INV",
        )
        _log_in(client, "ACC-INV")
        response = client.post(
            _association_path("ORG-INV", "NL-INV"), json={}, headers=_csrf_headers()
        )
        assert response.status_code == 400

    def test_unknown_design_ref_is_422(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UNK", account_id="ACC-UNK", membership_id="OM-UNK"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-UNK",
            org_id="ORG-UNK",
            account_id="ACC-UNK",
            membership_id="OM-UNK",
            physical_boat_id="PB-UNK",
            market_episode_id="ME-UNK",
        )
        _log_in(client, "ACC-UNK")
        response = client.post(
            _association_path("ORG-UNK", "NL-UNK"),
            json={"boat_design_ref": "BD-DOES-NOT-EXIST"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 422
        assert response.json()["error"] == "design_not_found"

    def test_full_happy_path_link_then_idempotent_retry_then_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-HP", account_id="ACC-HP", membership_id="OM-HP"
        )
        _create_unlinked_listing(
            api_url,
            listing_id="NL-HP",
            org_id="ORG-HP",
            account_id="ACC-HP",
            membership_id="OM-HP",
            physical_boat_id="PB-HP",
            market_episode_id="ME-HP",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_canonical_boat_design(conn, "BD-HP-X", "BM-HP-X")
            _insert_canonical_boat_design(conn, "BD-HP-Y", "BM-HP-Y")
        finally:
            conn.close()
        _log_in(client, "ACC-HP")

        first = client.post(
            _association_path("ORG-HP", "NL-HP"),
            json={"boat_design_ref": "BD-HP-X"},
            headers=_csrf_headers(),
        )
        assert first.status_code == 201
        assert first.json()["outcome"] == "LINKED"
        assert first.json()["boat_design_ref"] == "BD-HP-X"

        # Durable: a fresh readback (new connection via the API) sees it.
        read_after = client.get(_association_path("ORG-HP", "NL-HP"))
        assert read_after.json()["link_status"] == "LINKED"
        assert read_after.json()["boat_design_ref"] == "BD-HP-X"

        retry = client.post(
            _association_path("ORG-HP", "NL-HP"),
            json={"boat_design_ref": "BD-HP-X"},
            headers=_csrf_headers(),
        )
        assert retry.status_code == 200
        assert retry.json()["outcome"] == "ALREADY_LINKED"

        conflict = client.post(
            _association_path("ORG-HP", "NL-HP"),
            json={"boat_design_ref": "BD-HP-Y"},
            headers=_csrf_headers(),
        )
        assert conflict.status_code == 409
        assert conflict.json()["boat_design_ref"] == "BD-HP-X"

        # The physical boat chain truly carries the stored link.
        conn = psycopg.connect(api_url)
        try:
            record = fetch_physical_boat(conn, PhysicalBoatId("PB-HP"))
        finally:
            conn.close()
        assert record is not None
        assert record.physical_boat.boat_design_ref is not None
        assert record.physical_boat.boat_design_ref.value == "BD-HP-X"
