"""FastAPI integration tests for SLICE-0061 professional listing drafts.

Uses a directly minted session token (`mint_session_token`) rather than a
full OIDC login round-trip -- mirrors `test_broker_inventory_read_api.py`'s
identical pattern: the login/session-minting path itself is already covered
end-to-end by `test_broker_workspace_access_api.py` and
`scripts/inspect_broker_workspace_access.py`; this file focuses on the
professional-draft routes sitting on top of an already-valid session.

Covers contract §3 (Organization authorization + PUBLISHER role gate,
tenant isolation), §7 (create/list/read/update + optimistic concurrency),
§8 (CSRF) and §10 (privacy headers). Contract §11's non-promotion proof and
§4/§4.1's shared-validator-parity proof live in
`tests/persistence/test_professional_listing_draft_persistence.py` and
`tests/unit/test_professional_listing_draft_domain.py` respectively.
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
from hullq.security.session_token import mint_session_token

_SECRET = b"9" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "professional-listing-draft-v1"


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
    schema_name = f"hullq_s0061api_{uuid.uuid4().hex[:16]}"
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


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _drafts_path(org_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/drafts"


class TestProfessionalDraftAuthorizationBoundary:
    def test_unauthenticated_list_is_denied(self, client: TestClient) -> None:
        response = client.get(_drafts_path("ORG-PD-UNAUTH"))
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-PD-1")
        response = client.get(_drafts_path("ORG-PD-NEVER-CREATED"))
        assert response.status_code == 404

    def test_privileged_membership_without_mfa_is_blocked(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PD-MFA", account_id="ACC-PD-MFA", membership_id="OM-PD-MFA"
        )
        _log_in(client, "ACC-PD-MFA", mfa=False)
        response = client.get(_drafts_path("ORG-PD-MFA"))
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}

    def test_active_membership_without_publisher_role_is_blocked(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-NOPUB",
            account_id="ACC-PD-NOPUB",
            membership_id="OM-PD-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _log_in(client, "ACC-PD-NOPUB")
        response = client.get(_drafts_path("ORG-PD-NOPUB"))
        assert response.status_code == 403
        assert response.json() == {"error": "publisher_role_required"}

    def test_unverified_publishing_eligibility_does_not_block_draft_authoring(
        self, client: TestClient, api_url: str
    ) -> None:
        """Contract §3.2 item 5: OrganizationPublishingEligibility is never
        consulted for private pre-market draft authoring."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-UNVERIFIED",
            account_id="ACC-PD-UNVERIFIED",
            membership_id="OM-PD-UNVERIFIED",
            publishing_eligibility=OrganizationPublishingEligibility.UNVERIFIED,
        )
        _log_in(client, "ACC-PD-UNVERIFIED")
        response = client.post(_drafts_path("ORG-PD-UNVERIFIED"), json={}, headers=_csrf_headers())
        assert response.status_code == 201

    def test_ineligible_publishing_eligibility_does_not_block_draft_authoring(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-INELIGIBLE",
            account_id="ACC-PD-INELIGIBLE",
            membership_id="OM-PD-INELIGIBLE",
            publishing_eligibility=OrganizationPublishingEligibility.INELIGIBLE,
        )
        _log_in(client, "ACC-PD-INELIGIBLE")
        response = client.post(_drafts_path("ORG-PD-INELIGIBLE"), json={}, headers=_csrf_headers())
        assert response.status_code == 201

    def test_cross_organization_membership_is_not_found(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CROSS-OTHER",
            account_id="ACC-PD-CROSS-OTHER",
            membership_id="OM-PD-CROSS-OTHER",
        )
        _log_in(client, "ACC-PD-CROSS-SELF")
        response = client.get(_drafts_path("ORG-PD-CROSS-OTHER"))
        assert response.status_code == 404

    def test_revoked_membership_after_login_fails_closed_on_next_request(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-REVOKE",
            account_id="ACC-PD-REVOKE",
            membership_id="OM-PD-REVOKE",
        )
        _log_in(client, "ACC-PD-REVOKE")
        first = client.get(_drafts_path("ORG-PD-REVOKE"))
        assert first.status_code == 200

        conn = psycopg.connect(api_url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-PD-REVOKE"), MembershipState.INACTIVE
            )
            conn.commit()
        finally:
            conn.close()

        second = client.get(_drafts_path("ORG-PD-REVOKE"))
        assert second.status_code == 404


class TestProfessionalDraftCrud:
    def test_create_list_read_roundtrip(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CRUD-1",
            account_id="ACC-PD-CRUD-1",
            membership_id="OM-PD-CRUD-1",
        )
        _log_in(client, "ACC-PD-CRUD-1")

        created = client.post(_drafts_path("ORG-PD-CRUD-1"), json={}, headers=_csrf_headers())
        assert created.status_code == 201
        body = created.json()
        assert body["version"] == 1
        assert body["owner_organization_id"] == "ORG-PD-CRUD-1"
        assert body["broker_listing_reference"] is None
        draft_id = body["draft_id"]

        listed = client.get(_drafts_path("ORG-PD-CRUD-1"))
        assert listed.status_code == 200
        assert [d["draft_id"] for d in listed.json()["drafts"]] == [draft_id]

        fetched = client.get(f"{_drafts_path('ORG-PD-CRUD-1')}/{draft_id}")
        assert fetched.status_code == 200
        assert fetched.json()["draft_id"] == draft_id
        assert fetched.json()["version"] == 1

    def test_save_partial_payload_and_broker_reference_and_reopen_exact_values(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CRUD-2",
            account_id="ACC-PD-CRUD-2",
            membership_id="OM-PD-CRUD-2",
        )
        _log_in(client, "ACC-PD-CRUD-2")
        created = client.post(_drafts_path("ORG-PD-CRUD-2"), json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        updated = client.put(
            f"{_drafts_path('ORG-PD-CRUD-2')}/{draft_id}",
            json={
                "expected_version": 1,
                "broker_listing_reference": "REF-CRUD-2",
                "physical_boat.boat_name": "Sea Breeze",
                "listing_offer.asking_price_mode": "POA",
            },
            headers=_csrf_headers(),
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        assert updated.json()["broker_listing_reference"] == "REF-CRUD-2"

        reopened = client.get(f"{_drafts_path('ORG-PD-CRUD-2')}/{draft_id}")
        assert reopened.status_code == 200
        assert reopened.json()["physical_boat.boat_name"] == "Sea Breeze"
        assert reopened.json()["listing_offer.asking_price_mode"] == "POA"
        assert reopened.json()["broker_listing_reference"] == "REF-CRUD-2"
        assert reopened.json()["version"] == 2

    def test_save_broker_description_and_reopen_exact_value(
        self, client: TestClient, api_url: str
    ) -> None:
        """SLICE-0065 Publication Input Alignment contract §4.2: professional
        create/read/update round-trips `listing_offer.broker_description`
        under its exact wire key."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-DESC-1",
            account_id="ACC-PD-DESC-1",
            membership_id="OM-PD-DESC-1",
        )
        _log_in(client, "ACC-PD-DESC-1")
        created = client.post(_drafts_path("ORG-PD-DESC-1"), json={}, headers=_csrf_headers())
        assert created.json()["listing_offer.broker_description"] is None
        draft_id = created.json()["draft_id"]

        updated = client.put(
            f"{_drafts_path('ORG-PD-DESC-1')}/{draft_id}",
            json={
                "expected_version": 1,
                "listing_offer.broker_description": "  A lovely, well-maintained sloop.  ",
            },
            headers=_csrf_headers(),
        )
        assert updated.status_code == 200
        assert (
            updated.json()["listing_offer.broker_description"] == "A lovely, well-maintained sloop."
        )

        reopened = client.get(f"{_drafts_path('ORG-PD-DESC-1')}/{draft_id}")
        assert reopened.status_code == 200
        assert (
            reopened.json()["listing_offer.broker_description"]
            == "A lovely, well-maintained sloop."
        )

    def test_whitespace_only_broker_description_is_rejected_without_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-DESC-2",
            account_id="ACC-PD-DESC-2",
            membership_id="OM-PD-DESC-2",
        )
        _log_in(client, "ACC-PD-DESC-2")
        created = client.post(_drafts_path("ORG-PD-DESC-2"), json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        response = client.put(
            f"{_drafts_path('ORG-PD-DESC-2')}/{draft_id}",
            json={"expected_version": 1, "listing_offer.broker_description": "   "},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400

        current = client.get(f"{_drafts_path('ORG-PD-DESC-2')}/{draft_id}")
        assert current.json()["version"] == 1
        assert current.json()["listing_offer.broker_description"] is None

    def test_stale_expected_version_returns_409_without_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PD-STALE", account_id="ACC-PD-STALE", membership_id="OM-PD-STALE"
        )
        _log_in(client, "ACC-PD-STALE")
        created = client.post(_drafts_path("ORG-PD-STALE"), json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        first_update = client.put(
            f"{_drafts_path('ORG-PD-STALE')}/{draft_id}",
            json={"expected_version": 1, "physical_boat.boat_name": "First"},
            headers=_csrf_headers(),
        )
        assert first_update.status_code == 200

        stale_update = client.put(
            f"{_drafts_path('ORG-PD-STALE')}/{draft_id}",
            json={"expected_version": 1, "physical_boat.boat_name": "Stale"},
            headers=_csrf_headers(),
        )
        assert stale_update.status_code == 409

        current = client.get(f"{_drafts_path('ORG-PD-STALE')}/{draft_id}")
        assert current.json()["physical_boat.boat_name"] == "First"
        assert current.json()["version"] == 2

    def test_invalid_payload_key_returns_400_without_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-INVALID",
            account_id="ACC-PD-INVALID",
            membership_id="OM-PD-INVALID",
        )
        _log_in(client, "ACC-PD-INVALID")
        created = client.post(_drafts_path("ORG-PD-INVALID"), json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        response = client.put(
            f"{_drafts_path('ORG-PD-INVALID')}/{draft_id}",
            json={"expected_version": 1, "physical_boat.hull_material": "GRP"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400

        current = client.get(f"{_drafts_path('ORG-PD-INVALID')}/{draft_id}")
        assert current.json()["version"] == 1

    def test_foreign_organization_cannot_read_or_write_another_organizations_draft(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-VICTIM",
            account_id="ACC-PD-VICTIM",
            membership_id="OM-PD-VICTIM",
        )
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-ATTACKER",
            account_id="ACC-PD-ATTACKER",
            membership_id="OM-PD-ATTACKER",
        )
        _log_in(client, "ACC-PD-VICTIM")
        created = client.post(_drafts_path("ORG-PD-VICTIM"), json={}, headers=_csrf_headers())
        draft_id = created.json()["draft_id"]

        _log_in(client, "ACC-PD-ATTACKER")
        foreign_read = client.get(f"{_drafts_path('ORG-PD-ATTACKER')}/{draft_id}")
        unknown_read = client.get(f"{_drafts_path('ORG-PD-ATTACKER')}/{uuid.uuid4()}")
        assert foreign_read.status_code == 404
        assert unknown_read.status_code == 404
        assert foreign_read.content == unknown_read.content

        foreign_write = client.put(
            f"{_drafts_path('ORG-PD-ATTACKER')}/{draft_id}",
            json={"expected_version": 1, "physical_boat.boat_name": "Hijacked"},
            headers=_csrf_headers(),
        )
        assert foreign_write.status_code == 404

        _log_in(client, "ACC-PD-VICTIM")
        still_original = client.get(f"{_drafts_path('ORG-PD-VICTIM')}/{draft_id}")
        assert "physical_boat.boat_name" not in still_original.json()

    def test_empty_organization_draft_list_is_deterministic_and_bounded(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PD-EMPTY", account_id="ACC-PD-EMPTY", membership_id="OM-PD-EMPTY"
        )
        _log_in(client, "ACC-PD-EMPTY")
        response = client.get(_drafts_path("ORG-PD-EMPTY"))
        assert response.status_code == 200
        assert response.json() == {"drafts": []}

    def test_invalid_page_size_is_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-PGSIZE",
            account_id="ACC-PD-PGSIZE",
            membership_id="OM-PD-PGSIZE",
        )
        _log_in(client, "ACC-PD-PGSIZE")
        too_big = client.get(f"{_drafts_path('ORG-PD-PGSIZE')}?page_size=101")
        zero = client.get(f"{_drafts_path('ORG-PD-PGSIZE')}?page_size=0")
        assert too_big.status_code == 400
        assert zero.status_code == 400

    def test_malformed_cursor_fails_closed(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-BADCURSOR",
            account_id="ACC-PD-BADCURSOR",
            membership_id="OM-PD-BADCURSOR",
        )
        _log_in(client, "ACC-PD-BADCURSOR")
        response = client.get(f"{_drafts_path('ORG-PD-BADCURSOR')}?cursor=not-a-valid-cursor!!")
        assert response.status_code == 400

    def test_keyset_continuation_across_pages_has_no_duplicate(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PD-PAGES", account_id="ACC-PD-PAGES", membership_id="OM-PD-PAGES"
        )
        _log_in(client, "ACC-PD-PAGES")
        for _ in range(3):
            resp = client.post(_drafts_path("ORG-PD-PAGES"), json={}, headers=_csrf_headers())
            assert resp.status_code == 201

        first = client.get(f"{_drafts_path('ORG-PD-PAGES')}?page_size=2")
        assert first.status_code == 200
        first_body = first.json()
        assert len(first_body["drafts"]) == 2
        assert "next_cursor" in first_body

        second = client.get(
            f"{_drafts_path('ORG-PD-PAGES')}?page_size=2&cursor={first_body['next_cursor']}"
        )
        assert second.status_code == 200
        second_body = second.json()
        assert len(second_body["drafts"]) == 1
        assert "next_cursor" not in second_body

        all_ids = [d["draft_id"] for d in first_body["drafts"] + second_body["drafts"]]
        assert len(all_ids) == len(set(all_ids)) == 3


class TestProfessionalDraftCsrf:
    def test_create_without_csrf_headers_fails_closed(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CSRF-1",
            account_id="ACC-PD-CSRF-1",
            membership_id="OM-PD-CSRF-1",
        )
        _log_in(client, "ACC-PD-CSRF-1")
        response = client.post(_drafts_path("ORG-PD-CSRF-1"), json={})
        assert response.status_code == 403

    def test_create_with_wrong_origin_fails_closed(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CSRF-2",
            account_id="ACC-PD-CSRF-2",
            membership_id="OM-PD-CSRF-2",
        )
        _log_in(client, "ACC-PD-CSRF-2")
        response = client.post(
            _drafts_path("ORG-PD-CSRF-2"),
            json={},
            headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": _CSRF_HEADER_VALUE,
            },
        )
        assert response.status_code == 403

    def test_create_with_correct_origin_missing_requested_header_fails_closed(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CSRF-3",
            account_id="ACC-PD-CSRF-3",
            membership_id="OM-PD-CSRF-3",
        )
        _log_in(client, "ACC-PD-CSRF-3")
        response = client.post(
            _drafts_path("ORG-PD-CSRF-3"), json={}, headers={"Origin": _WEB_ORIGIN}
        )
        assert response.status_code == 403

    def test_owner_direct_csrf_header_value_is_rejected_here(
        self, client: TestClient, api_url: str
    ) -> None:
        """The two draft channels' fixed CSRF header values are distinct
        (contract §8): a valid owner-direct-draft-v1 header must not be
        accepted on this boundary."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CSRF-4",
            account_id="ACC-PD-CSRF-4",
            membership_id="OM-PD-CSRF-4",
        )
        _log_in(client, "ACC-PD-CSRF-4")
        response = client.post(
            _drafts_path("ORG-PD-CSRF-4"),
            json={},
            headers={"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": "owner-direct-draft-v1"},
        )
        assert response.status_code == 403

    def test_valid_same_origin_mutation_succeeds(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CSRF-5",
            account_id="ACC-PD-CSRF-5",
            membership_id="OM-PD-CSRF-5",
        )
        _log_in(client, "ACC-PD-CSRF-5")
        response = client.post(_drafts_path("ORG-PD-CSRF-5"), json={}, headers=_csrf_headers())
        assert response.status_code == 201

    def test_no_mutation_from_failed_csrf_attempts(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-CSRF-6",
            account_id="ACC-PD-CSRF-6",
            membership_id="OM-PD-CSRF-6",
        )
        _log_in(client, "ACC-PD-CSRF-6")
        client.post(_drafts_path("ORG-PD-CSRF-6"), json={})
        client.post(
            _drafts_path("ORG-PD-CSRF-6"),
            json={},
            headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": _CSRF_HEADER_VALUE,
            },
        )
        listed = client.get(_drafts_path("ORG-PD-CSRF-6"))
        assert listed.json() == {"drafts": []}


class TestProfessionalDraftPrivacyHeaders:
    def test_draft_responses_are_private_no_store_and_noindex(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PD-HEADERS",
            account_id="ACC-PD-HEADERS",
            membership_id="OM-PD-HEADERS",
        )
        _log_in(client, "ACC-PD-HEADERS")
        response = client.get(_drafts_path("ORG-PD-HEADERS"))
        assert response.headers.get("cache-control") == "private, no-store"
        assert response.headers.get("x-robots-tag") == "noindex"


class TestProfessionalDraftSafeRendering:
    def test_html_like_broker_reference_is_stored_and_returned_as_plain_text(
        self, client: TestClient, api_url: str
    ) -> None:
        """The API layer must never interpret/execute this text -- it is
        stored and returned verbatim as JSON string data; safe rendering at
        the browser surface is proven by the retained proof script."""
        _seed_org_and_membership(
            api_url, org_id="ORG-PD-XSS", account_id="ACC-PD-XSS", membership_id="OM-PD-XSS"
        )
        _log_in(client, "ACC-PD-XSS")
        malicious = "<script>alert('xss')</script>"
        created = client.post(
            _drafts_path("ORG-PD-XSS"),
            json={"broker_listing_reference": malicious},
            headers=_csrf_headers(),
        )
        assert created.status_code == 201
        assert created.json()["broker_listing_reference"] == malicious
