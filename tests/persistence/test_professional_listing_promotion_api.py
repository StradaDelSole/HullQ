"""FastAPI integration tests for SLICE-0067 professional draft promotion.

Mirrors `test_professional_listing_draft_api.py`'s directly-minted-session
pattern: the login/session-minting path is already covered end-to-end
elsewhere, so this file focuses on the promote route sitting on top of an
already-valid session.

Covers contract §4 (authorization reuse), §6 (bounded outcome/HTTP mapping),
§12 (browser-visible readiness/result) and §13 (CSRF).
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
)
from hullq.security.session_token import mint_session_token

_SECRET = b"9" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "professional-listing-draft-v1"

_READY_PAYLOAD = {
    "physical_boat.marketed_brand_claim": "Beneteau",
    "physical_boat.model_designation_claim": "Oceanis 30.1",
    "physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 2021},
    "listing_offer.asking_price_mode": "AMOUNT",
    "listing_offer.asking_price_amount": "125000",
    "listing_offer.currency": "EUR",
    "listing_offer.location_country": "FR",
    "listing_offer.broker_description": "A lovely, well-maintained cruising sloop.",
}


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
    schema_name = f"hullq_s0067api_{uuid.uuid4().hex[:16]}"
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


def _promote_path(org_id: str, draft_id: str) -> str:
    return f"{_drafts_path(org_id)}/{draft_id}/promote"


def _create_ready_draft(client: TestClient, org_id: str) -> str:
    created = client.post(_drafts_path(org_id), json=_READY_PAYLOAD, headers=_csrf_headers())
    assert created.status_code == 201
    return str(created.json()["draft_id"])


_MARKETPLACE_TABLES = (
    "physical_boats",
    "market_episodes",
    "native_listings",
    "native_listing_offer_revisions",
    "native_listing_offer_heads",
    "physical_boat_claim_revisions",
    "physical_boat_claim_heads",
)


def _marketplace_row_counts(api_url: str) -> dict[str, int]:
    conn = psycopg.connect(api_url)
    try:
        counts: dict[str, int] = {}
        with conn.cursor() as cur:
            for table in _MARKETPLACE_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                row = cur.fetchone()
                assert row is not None
                counts[table] = row[0]
        return counts
    finally:
        conn.close()


def _draft_state_direct(api_url: str, draft_id: str) -> tuple[str, int]:
    """Reads promotion_state/version directly from PostgreSQL -- used only
    where the test scenario itself has just removed the API's own PUBLISHER
    authorization, so the ordinary authorized GET route cannot be used to
    verify zero mutation without reintroducing the very role this test is
    proving is now denied."""
    conn = psycopg.connect(api_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT promotion_state, version FROM professional_listing_drafts "
                "WHERE professional_listing_draft_id = %s",
                [draft_id],
            )
            row = cur.fetchone()
            assert row is not None
            return row[0], row[1]
    finally:
        conn.close()


class TestPromotionAuthorizationBoundary:
    def test_unauthenticated_is_401(self, client: TestClient) -> None:
        response = client.post(
            _promote_path("ORG-PROMO-API-UNAUTH", "unknown"),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert response.status_code == 401

    def test_unknown_organization_is_404(self, client: TestClient) -> None:
        _log_in(client, "ACC-PROMO-API-1")
        response = client.post(
            _promote_path("ORG-PROMO-API-NEVER-CREATED", "unknown"),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert response.status_code == 404

    def test_missing_csrf_header_fails_before_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-CSRF",
            account_id="ACC-PROMO-API-CSRF",
            membership_id="OM-PROMO-API-CSRF",
        )
        _log_in(client, "ACC-PROMO-API-CSRF")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-CSRF")

        response = client.post(
            _promote_path("ORG-PROMO-API-CSRF", draft_id),
            json={"expected_version": 1},
            headers={"Origin": _WEB_ORIGIN},
        )
        assert response.status_code == 403

        reread = client.get(f"{_drafts_path('ORG-PROMO-API-CSRF')}/{draft_id}")
        assert reread.json()["promotion_state"] == "EDITABLE"

    def test_foreign_draft_id_is_404(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-FOREIGN",
            account_id="ACC-PROMO-API-FOREIGN",
            membership_id="OM-PROMO-API-FOREIGN",
        )
        _log_in(client, "ACC-PROMO-API-FOREIGN")
        response = client.post(
            _promote_path("ORG-PROMO-API-FOREIGN", str(uuid.uuid4())),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert response.status_code == 404


class TestPromotionRequiresCurrentPublisherRole:
    """Independent exact-head review Finding A: contract §4 requires current
    `PUBLISHER` membership before *every* promotion request may disclose
    draft/result state -- including a read-only exact-version retry of an
    already-PROMOTED draft -- not merely for a new EDITABLE -> PROMOTED
    materialization."""

    def _denied_publisher_role_required(self, response: Any) -> None:
        assert response.status_code == 403
        assert response.json() == {
            "error": "publishing_denied",
            "reason": "PUBLISHER_ROLE_REQUIRED",
        }

    def test_non_publisher_member_against_known_editable_draft_is_denied(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-NOPUB-1",
            account_id="ACC-PROMO-API-NOPUB-1",
            membership_id="OM-PROMO-API-NOPUB-1",
        )
        _log_in(client, "ACC-PROMO-API-NOPUB-1")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-NOPUB-1")

        # Downgrade the exact same membership to no longer include PUBLISHER.
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-NOPUB-1",
            account_id="ACC-PROMO-API-NOPUB-1",
            membership_id="OM-PROMO-API-NOPUB-1",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        before = _marketplace_row_counts(api_url)

        response = client.post(
            _promote_path("ORG-PROMO-API-NOPUB-1", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        self._denied_publisher_role_required(response)
        assert _marketplace_row_counts(api_url) == before
        state, version = _draft_state_direct(api_url, draft_id)
        assert state == "EDITABLE"
        assert version == 1

    def test_non_publisher_member_against_unknown_draft_is_identically_denied(
        self, client: TestClient, api_url: str
    ) -> None:
        """Non-enumeration: an unknown draft id must return the exact same
        403 shape as a known EDITABLE/PROMOTED one once PUBLISHER is
        missing -- the caller must never be able to use this boundary as a
        draft-existence oracle."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-NOPUB-2",
            account_id="ACC-PROMO-API-NOPUB-2",
            membership_id="OM-PROMO-API-NOPUB-2",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _log_in(client, "ACC-PROMO-API-NOPUB-2")

        response = client.post(
            _promote_path("ORG-PROMO-API-NOPUB-2", str(uuid.uuid4())),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        self._denied_publisher_role_required(response)

    def test_publisher_role_revoked_after_promotion_blocks_exact_retry_disclosure(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-NOPUB-3",
            account_id="ACC-PROMO-API-NOPUB-3",
            membership_id="OM-PROMO-API-NOPUB-3",
        )
        _log_in(client, "ACC-PROMO-API-NOPUB-3")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-NOPUB-3")

        promoted = client.post(
            _promote_path("ORG-PROMO-API-NOPUB-3", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert promoted.status_code == 201
        native_listing_id = promoted.json()["native_listing_id"]

        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-NOPUB-3",
            account_id="ACC-PROMO-API-NOPUB-3",
            membership_id="OM-PROMO-API-NOPUB-3",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        before = _marketplace_row_counts(api_url)

        retry = client.post(
            _promote_path("ORG-PROMO-API-NOPUB-3", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        self._denied_publisher_role_required(retry)
        assert "native_listing_id" not in retry.json()
        assert native_listing_id not in retry.text
        assert _marketplace_row_counts(api_url) == before

    def test_authorized_publisher_exact_retry_still_returns_already_promoted(
        self, client: TestClient, api_url: str
    ) -> None:
        """Confirms the fix does not regress the accepted historical-
        idempotency behavior for a still-authorized current PUBLISHER."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-PUB-OK",
            account_id="ACC-PROMO-API-PUB-OK",
            membership_id="OM-PROMO-API-PUB-OK",
        )
        _log_in(client, "ACC-PROMO-API-PUB-OK")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-PUB-OK")

        first = client.post(
            _promote_path("ORG-PROMO-API-PUB-OK", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert first.status_code == 201
        native_listing_id = first.json()["native_listing_id"]
        before = _marketplace_row_counts(api_url)

        retry = client.post(
            _promote_path("ORG-PROMO-API-PUB-OK", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert retry.status_code == 200
        assert retry.json()["outcome"] == "ALREADY_PROMOTED"
        assert retry.json()["native_listing_id"] == native_listing_id
        assert _marketplace_row_counts(api_url) == before

    def test_authorized_publisher_exact_retry_survives_organization_becoming_ineligible(
        self, client: TestClient, api_url: str
    ) -> None:
        """Contract §4 last paragraph: an already-PROMOTED exact-version
        retry never re-requires current Organization publishing
        eligibility -- only current workspace/MFA/PUBLISHER authorization,
        which this scenario still satisfies."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-ELIG",
            account_id="ACC-PROMO-API-ELIG",
            membership_id="OM-PROMO-API-ELIG",
        )
        _log_in(client, "ACC-PROMO-API-ELIG")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-ELIG")

        first = client.post(
            _promote_path("ORG-PROMO-API-ELIG", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert first.status_code == 201
        native_listing_id = first.json()["native_listing_id"]

        conn = psycopg.connect(api_url)
        try:
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId("ORG-PROMO-API-ELIG"),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.UNVERIFIED,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        retry = client.post(
            _promote_path("ORG-PROMO-API-ELIG", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert retry.status_code == 200
        assert retry.json()["outcome"] == "ALREADY_PROMOTED"
        assert retry.json()["native_listing_id"] == native_listing_id


class TestPromotionRequestValidation:
    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"expected_version": 1, "extra": "nope"},
            {"expected_version": None},
            {"expected_version": "1"},
            {"expected_version": 1.5},
            {"expected_version": True},
            {"expected_version": 0},
            {"expected_version": -1},
        ],
    )
    def test_malformed_request_is_400_without_mutation(
        self, client: TestClient, api_url: str, body: dict[str, Any]
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-MALFORMED",
            account_id="ACC-PROMO-API-MALFORMED",
            membership_id="OM-PROMO-API-MALFORMED",
        )
        _log_in(client, "ACC-PROMO-API-MALFORMED")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-MALFORMED")

        response = client.post(
            _promote_path("ORG-PROMO-API-MALFORMED", draft_id), json=body, headers=_csrf_headers()
        )
        assert response.status_code == 400

        reread = client.get(f"{_drafts_path('ORG-PROMO-API-MALFORMED')}/{draft_id}")
        assert reread.json()["version"] == 1
        assert reread.json()["promotion_state"] == "EDITABLE"


class TestPromotionOutcomes:
    def test_promotes_ready_draft_and_shows_in_inventory(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-OK",
            account_id="ACC-PROMO-API-OK",
            membership_id="OM-PROMO-API-OK",
        )
        _log_in(client, "ACC-PROMO-API-OK")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-OK")

        response = client.post(
            _promote_path("ORG-PROMO-API-OK", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert response.status_code == 201
        body = response.json()
        assert body["outcome"] == "PROMOTED"
        native_listing_id = body["native_listing_id"]
        assert native_listing_id

        reread = client.get(f"{_drafts_path('ORG-PROMO-API-OK')}/{draft_id}")
        assert reread.json()["promotion_state"] == "PROMOTED"
        assert reread.json()["promoted_native_listing_id"] == native_listing_id
        assert reread.json()["version"] == 1

        inventory = client.get("/api/broker/organizations/ORG-PROMO-API-OK/inventory")
        assert inventory.status_code == 200
        listing_ids = [item["native_listing_id"] for item in inventory.json()["items"]]
        assert native_listing_id in listing_ids
        promoted_item = next(
            item
            for item in inventory.json()["items"]
            if item["native_listing_id"] == native_listing_id
        )
        assert promoted_item["lifecycle_state"] == "DRAFT"

        public_read = client.get(f"/api/listings/{native_listing_id}")
        assert public_read.status_code == 404

    def test_exact_retry_returns_already_promoted(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-RETRY",
            account_id="ACC-PROMO-API-RETRY",
            membership_id="OM-PROMO-API-RETRY",
        )
        _log_in(client, "ACC-PROMO-API-RETRY")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-RETRY")

        first = client.post(
            _promote_path("ORG-PROMO-API-RETRY", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert first.status_code == 201
        native_listing_id = first.json()["native_listing_id"]

        retry = client.post(
            _promote_path("ORG-PROMO-API-RETRY", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert retry.status_code == 200
        assert retry.json()["outcome"] == "ALREADY_PROMOTED"
        assert retry.json()["native_listing_id"] == native_listing_id

    def test_not_ready_incomplete_draft_returns_409_with_reasons(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-NOTREADY",
            account_id="ACC-PROMO-API-NOTREADY",
            membership_id="OM-PROMO-API-NOTREADY",
        )
        _log_in(client, "ACC-PROMO-API-NOTREADY")
        created = client.post(
            _drafts_path("ORG-PROMO-API-NOTREADY"), json={}, headers=_csrf_headers()
        )
        draft_id = created.json()["draft_id"]

        response = client.post(
            _promote_path("ORG-PROMO-API-NOTREADY", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "not_ready"
        assert "MISSING_MARKETED_BRAND" in body["reasons"]

    def test_stale_version_returns_409(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-STALE",
            account_id="ACC-PROMO-API-STALE",
            membership_id="OM-PROMO-API-STALE",
        )
        _log_in(client, "ACC-PROMO-API-STALE")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-STALE")

        response = client.post(
            _promote_path("ORG-PROMO-API-STALE", draft_id),
            json={"expected_version": 999},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json()["error"] == "version_conflict"

    def test_promoted_draft_rejects_further_update(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-IMMUTABLE",
            account_id="ACC-PROMO-API-IMMUTABLE",
            membership_id="OM-PROMO-API-IMMUTABLE",
        )
        _log_in(client, "ACC-PROMO-API-IMMUTABLE")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-IMMUTABLE")
        promoted = client.post(
            _promote_path("ORG-PROMO-API-IMMUTABLE", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert promoted.status_code == 201

        update = client.put(
            f"{_drafts_path('ORG-PROMO-API-IMMUTABLE')}/{draft_id}",
            json={"expected_version": 1, "physical_boat.boat_name": "Sea Breeze"},
            headers=_csrf_headers(),
        )
        assert update.status_code == 409
        assert update.json()["error"] == "promoted_immutable"

    def test_promoted_draft_excluded_from_active_list(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-LIST",
            account_id="ACC-PROMO-API-LIST",
            membership_id="OM-PROMO-API-LIST",
        )
        _log_in(client, "ACC-PROMO-API-LIST")
        promoted_draft_id = _create_ready_draft(client, "ORG-PROMO-API-LIST")
        client.post(
            _promote_path("ORG-PROMO-API-LIST", promoted_draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        other_draft_id = _create_ready_draft(client, "ORG-PROMO-API-LIST")

        listed = client.get(_drafts_path("ORG-PROMO-API-LIST"))
        draft_ids = [d["draft_id"] for d in listed.json()["drafts"]]
        assert promoted_draft_id not in draft_ids
        assert other_draft_id in draft_ids

    def test_direct_read_of_promoted_draft_shows_immutable_provenance(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PROMO-API-READ",
            account_id="ACC-PROMO-API-READ",
            membership_id="OM-PROMO-API-READ",
        )
        _log_in(client, "ACC-PROMO-API-READ")
        draft_id = _create_ready_draft(client, "ORG-PROMO-API-READ")
        promoted = client.post(
            _promote_path("ORG-PROMO-API-READ", draft_id),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        native_listing_id = promoted.json()["native_listing_id"]

        reread = client.get(f"{_drafts_path('ORG-PROMO-API-READ')}/{draft_id}")
        assert reread.status_code == 200
        body = reread.json()
        assert body["promotion_state"] == "PROMOTED"
        assert body["promoted_native_listing_id"] == native_listing_id
        assert body["promoted_at"]
