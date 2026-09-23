"""FastAPI integration tests for SLICE-0064 professional inventory lifecycle
controls (publish/withdraw/reconfirm an already-existing NativeListing).

Uses a directly minted session token (`mint_session_token`) rather than a
full OIDC login round-trip -- mirrors `test_broker_inventory_read_api.py`'s
and `test_professional_listing_draft_api.py`'s identical pattern: the login/
session-minting path itself is already covered end-to-end by
`test_broker_workspace_access_api.py` and
`scripts/inspect_broker_workspace_access.py`; this file focuses on the three
new lifecycle mutation routes sitting on top of an already-valid session.

Covers contract §4 (Organization/tenant authorization, non-enumeration),
§5/§9/§10/§11 (publish/withdraw/reconfirm semantics), §7 (CSRF) and §14
(mechanically distinct outcomes).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
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
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
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
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    fetch_lifecycle_state,
    list_publication_transitions,
    publish_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.security.session_token import mint_session_token

_SECRET = b"8" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1"


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
    schema_name = f"hullq_s0064api_{uuid.uuid4().hex[:16]}"
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


def _make_client(api_url: str, monkeypatch: pytest.MonkeyPatch, *, as_of: datetime) -> TestClient:
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
        freshness_as_of_override=as_of,
    )
    return TestClient(app, base_url="http://api.test", follow_redirects=False)


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


def _amount_offer() -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal("125000.00"),
        currency="EUR",
    )


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
) -> None:
    """Own, complete DRAFT NativeListing satisfying the §7 completeness predicate."""
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
        conn.commit()
    finally:
        conn.close()


def _create_incomplete_draft_listing(
    api_url: str, *, listing_id: str, org_id: str, account_id: str, membership_id: str
) -> None:
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


def _publish_directly(api_url: str, *, listing_id: str, org_id: str, account_id: str) -> None:
    """Fast-forward a complete DRAFT listing straight to ACTIVE via the
    accepted persistence primitive -- used only to set up preconditions for
    withdraw/reconfirm tests; the publish route itself is exercised by
    `TestPublish` below."""
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


def _confirmation_count(api_url: str) -> int:
    conn = psycopg.connect(api_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM native_listing_freshness_confirmations")
            row = cur.fetchone()
            assert row is not None
            return int(row[0])
    finally:
        conn.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _publish_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/publish"


def _withdraw_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/withdraw"


def _reconfirm_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/reconfirm"


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


class TestPublish:
    def test_unauthenticated_publish_is_blocked(self, client: TestClient) -> None:
        response = client.post(_publish_path("ORG-PUB-UNAUTH", "NL-X"), headers=_csrf_headers())
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient, api_url: str) -> None:
        _log_in(client, "ACC-PUB-1")
        response = client.post(
            _publish_path("ORG-PUB-NEVER-CREATED", "NL-X"), headers=_csrf_headers()
        )
        assert response.status_code == 404

    def test_mfa_required_session_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PUB-MFA", account_id="ACC-PUB-MFA", membership_id="OM-PUB-MFA"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-PUB-MFA",
            org_id="ORG-PUB-MFA",
            account_id="ACC-PUB-MFA",
            membership_id="OM-PUB-MFA",
            physical_boat_id="PB-PUB-MFA",
            market_episode_id="ME-PUB-MFA",
            offer_revision_id="REV-PUB-MFA",
        )
        _log_in(client, "ACC-PUB-MFA", mfa=False)
        response = client.post(_publish_path("ORG-PUB-MFA", "NL-PUB-MFA"), headers=_csrf_headers())
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}
        assert _lifecycle_state(api_url, "NL-PUB-MFA") is NativeListingLifecycleState.DRAFT

    def test_missing_publisher_role_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PUB-NOPUB",
            account_id="ACC-PUB-NOPUB",
            membership_id="OM-PUB-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-PUB-NOPUB",
            org_id="ORG-PUB-NOPUB",
            account_id="ACC-PUB-NOPUB",
            membership_id="OM-PUB-NOPUB",
            physical_boat_id="PB-PUB-NOPUB",
            market_episode_id="ME-PUB-NOPUB",
            offer_revision_id="REV-PUB-NOPUB",
        )
        _log_in(client, "ACC-PUB-NOPUB", mfa=False)  # MEMBER-only: not a PRIVILEGED_MFA_ROLE
        response = client.post(
            _publish_path("ORG-PUB-NOPUB", "NL-PUB-NOPUB"), headers=_csrf_headers()
        )
        assert response.status_code == 403
        assert response.json() == {
            "error": "publishing_denied",
            "reason": "PUBLISHER_ROLE_REQUIRED",
        }
        assert _lifecycle_state(api_url, "NL-PUB-NOPUB") is NativeListingLifecycleState.DRAFT

    def test_inactive_membership_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PUB-INACTIVE",
            account_id="ACC-PUB-INACTIVE",
            membership_id="OM-PUB-INACTIVE",
            state=MembershipState.INACTIVE,
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-PUB-INACTIVE",
            org_id="ORG-PUB-INACTIVE",
            account_id="ACC-PUB-INACTIVE",
            membership_id="OM-PUB-INACTIVE",
            physical_boat_id="PB-PUB-INACTIVE",
            market_episode_id="ME-PUB-INACTIVE",
            offer_revision_id="REV-PUB-INACTIVE",
        )
        _log_in(client, "ACC-PUB-INACTIVE")
        response = client.post(
            _publish_path("ORG-PUB-INACTIVE", "NL-PUB-INACTIVE"), headers=_csrf_headers()
        )
        assert response.status_code == 404  # workspace-level non-enumeration
        assert _lifecycle_state(api_url, "NL-PUB-INACTIVE") is NativeListingLifecycleState.DRAFT

    @pytest.mark.parametrize(
        ("eligibility", "expected_reason"),
        [
            (OrganizationPublishingEligibility.UNVERIFIED, "ORGANIZATION_UNVERIFIED"),
            (OrganizationPublishingEligibility.INELIGIBLE, "ORGANIZATION_INELIGIBLE"),
        ],
    )
    def test_unverified_or_ineligible_organization_writes_nothing(
        self,
        client: TestClient,
        api_url: str,
        eligibility: OrganizationPublishingEligibility,
        expected_reason: str,
    ) -> None:
        org_id = f"ORG-PUB-{expected_reason}"
        account_id = f"ACC-PUB-{expected_reason}"
        membership_id = f"OM-PUB-{expected_reason}"
        listing_id = f"NL-PUB-{expected_reason}"
        _seed_org_and_membership(
            api_url,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            publishing_eligibility=eligibility,
        )
        _create_complete_draft_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id=f"PB-{expected_reason}",
            market_episode_id=f"ME-{expected_reason}",
            offer_revision_id=f"REV-{expected_reason}",
        )
        _log_in(client, account_id)
        response = client.post(_publish_path(org_id, listing_id), headers=_csrf_headers())
        assert response.status_code == 403
        assert response.json() == {"error": "publishing_denied", "reason": expected_reason}
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.DRAFT

    def test_foreign_and_unknown_listing_share_identical_not_found_shape(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PUB-VICTIM", account_id="ACC-PUB-VICTIM", membership_id="OM-PUB-V"
        )
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PUB-ATTACKER",
            account_id="ACC-PUB-ATTACKER",
            membership_id="OM-PUB-A",
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-PUB-VICTIM",
            org_id="ORG-PUB-VICTIM",
            account_id="ACC-PUB-VICTIM",
            membership_id="OM-PUB-V",
            physical_boat_id="PB-PUB-VICTIM",
            market_episode_id="ME-PUB-VICTIM",
            offer_revision_id="REV-PUB-VICTIM",
        )
        _log_in(client, "ACC-PUB-ATTACKER")
        foreign = client.post(
            _publish_path("ORG-PUB-ATTACKER", "NL-PUB-VICTIM"), headers=_csrf_headers()
        )
        unknown = client.post(
            _publish_path("ORG-PUB-ATTACKER", "NL-NEVER-CREATED"), headers=_csrf_headers()
        )
        assert foreign.status_code == unknown.status_code == 404
        assert foreign.content == unknown.content
        assert _lifecycle_state(api_url, "NL-PUB-VICTIM") is NativeListingLifecycleState.DRAFT

    def test_complete_draft_publish_transitions_exactly_once_to_active(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PUB-OK", account_id="ACC-PUB-OK", membership_id="OM-PUB-OK"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-PUB-OK",
            org_id="ORG-PUB-OK",
            account_id="ACC-PUB-OK",
            membership_id="OM-PUB-OK",
            physical_boat_id="PB-PUB-OK",
            market_episode_id="ME-PUB-OK",
            offer_revision_id="REV-PUB-OK",
        )
        _log_in(client, "ACC-PUB-OK")
        response = client.post(_publish_path("ORG-PUB-OK", "NL-PUB-OK"), headers=_csrf_headers())
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "PUBLISHED"
        assert body["transition_id"]
        assert _lifecycle_state(api_url, "NL-PUB-OK") is NativeListingLifecycleState.ACTIVE
        assert _transition_count(api_url, "NL-PUB-OK") == 1

    def test_incomplete_draft_publish_returns_bounded_failure_and_stays_draft(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PUB-INC", account_id="ACC-PUB-INC", membership_id="OM-PUB-INC"
        )
        _create_incomplete_draft_listing(
            api_url,
            listing_id="NL-PUB-INC",
            org_id="ORG-PUB-INC",
            account_id="ACC-PUB-INC",
            membership_id="OM-PUB-INC",
        )
        _log_in(client, "ACC-PUB-INC")
        response = client.post(_publish_path("ORG-PUB-INC", "NL-PUB-INC"), headers=_csrf_headers())
        assert response.status_code == 422
        assert response.json() == {"error": "incomplete_listing"}
        assert _lifecycle_state(api_url, "NL-PUB-INC") is NativeListingLifecycleState.DRAFT
        assert _transition_count(api_url, "NL-PUB-INC") == 0

    def test_publish_of_already_active_listing_is_state_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PUB-DBL", account_id="ACC-PUB-DBL", membership_id="OM-PUB-DBL"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-PUB-DBL",
            org_id="ORG-PUB-DBL",
            account_id="ACC-PUB-DBL",
            membership_id="OM-PUB-DBL",
            physical_boat_id="PB-PUB-DBL",
            market_episode_id="ME-PUB-DBL",
            offer_revision_id="REV-PUB-DBL",
        )
        _publish_directly(
            api_url, listing_id="NL-PUB-DBL", org_id="ORG-PUB-DBL", account_id="ACC-PUB-DBL"
        )
        _log_in(client, "ACC-PUB-DBL")
        response = client.post(_publish_path("ORG-PUB-DBL", "NL-PUB-DBL"), headers=_csrf_headers())
        assert response.status_code == 409
        assert response.json() == {"error": "state_conflict"}
        assert _transition_count(api_url, "NL-PUB-DBL") == 1

    def test_publish_creates_no_offer_physical_boat_or_market_episode_rows(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PUB-NOADJ",
            account_id="ACC-PUB-NOADJ",
            membership_id="OM-PUB-NOADJ",
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-PUB-NOADJ",
            org_id="ORG-PUB-NOADJ",
            account_id="ACC-PUB-NOADJ",
            membership_id="OM-PUB-NOADJ",
            physical_boat_id="PB-PUB-NOADJ",
            market_episode_id="ME-PUB-NOADJ",
            offer_revision_id="REV-PUB-NOADJ",
        )

        def _counts() -> dict[str, int]:
            conn = psycopg.connect(api_url)
            try:
                out: dict[str, int] = {}
                for table in (
                    "physical_boats",
                    "market_episodes",
                    "native_listing_offer_revisions",
                ):
                    with conn.cursor() as cur:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        row = cur.fetchone()
                        assert row is not None
                        out[table] = row[0]
                return out
            finally:
                conn.close()

        before = _counts()
        _log_in(client, "ACC-PUB-NOADJ")
        response = client.post(
            _publish_path("ORG-PUB-NOADJ", "NL-PUB-NOADJ"), headers=_csrf_headers()
        )
        assert response.status_code == 200
        assert _counts() == before


# ---------------------------------------------------------------------------
# Withdraw
# ---------------------------------------------------------------------------


class TestWithdraw:
    def test_unauthenticated_withdraw_is_blocked(self, client: TestClient) -> None:
        response = client.post(_withdraw_path("ORG-WD-UNAUTH", "NL-X"), headers=_csrf_headers())
        assert response.status_code == 401

    def test_own_active_withdraw_transitions_exactly_once(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-WD-OK", account_id="ACC-WD-OK", membership_id="OM-WD-OK"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-WD-OK",
            org_id="ORG-WD-OK",
            account_id="ACC-WD-OK",
            membership_id="OM-WD-OK",
            physical_boat_id="PB-WD-OK",
            market_episode_id="ME-WD-OK",
            offer_revision_id="REV-WD-OK",
        )
        _publish_directly(
            api_url, listing_id="NL-WD-OK", org_id="ORG-WD-OK", account_id="ACC-WD-OK"
        )
        _log_in(client, "ACC-WD-OK")
        response = client.post(_withdraw_path("ORG-WD-OK", "NL-WD-OK"), headers=_csrf_headers())
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "WITHDRAWN"
        assert body["transition_id"]
        assert _lifecycle_state(api_url, "NL-WD-OK") is NativeListingLifecycleState.WITHDRAWN
        assert _transition_count(api_url, "NL-WD-OK") == 2

    def test_withdraw_of_draft_listing_is_state_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-WD-DRAFT", account_id="ACC-WD-DRAFT", membership_id="OM-WD-DRAFT"
        )
        _create_incomplete_draft_listing(
            api_url,
            listing_id="NL-WD-DRAFT",
            org_id="ORG-WD-DRAFT",
            account_id="ACC-WD-DRAFT",
            membership_id="OM-WD-DRAFT",
        )
        _log_in(client, "ACC-WD-DRAFT")
        response = client.post(
            _withdraw_path("ORG-WD-DRAFT", "NL-WD-DRAFT"), headers=_csrf_headers()
        )
        assert response.status_code == 409
        assert response.json() == {"error": "state_conflict"}
        assert _lifecycle_state(api_url, "NL-WD-DRAFT") is NativeListingLifecycleState.DRAFT

    def test_withdraw_of_already_withdrawn_listing_is_state_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-WD-DBL", account_id="ACC-WD-DBL", membership_id="OM-WD-DBL"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-WD-DBL",
            org_id="ORG-WD-DBL",
            account_id="ACC-WD-DBL",
            membership_id="OM-WD-DBL",
            physical_boat_id="PB-WD-DBL",
            market_episode_id="ME-WD-DBL",
            offer_revision_id="REV-WD-DBL",
        )
        _publish_directly(
            api_url, listing_id="NL-WD-DBL", org_id="ORG-WD-DBL", account_id="ACC-WD-DBL"
        )
        _log_in(client, "ACC-WD-DBL")
        first = client.post(_withdraw_path("ORG-WD-DBL", "NL-WD-DBL"), headers=_csrf_headers())
        assert first.status_code == 200
        second = client.post(_withdraw_path("ORG-WD-DBL", "NL-WD-DBL"), headers=_csrf_headers())
        assert second.status_code == 409
        assert second.json() == {"error": "state_conflict"}
        assert _transition_count(api_url, "NL-WD-DBL") == 2

    def test_withdraw_never_creates_a_third_lifecycle_state(
        self, client: TestClient, api_url: str
    ) -> None:
        """No SOLD/ARCHIVED state exists to accidentally create; this proves
        the only durable value after withdraw is the accepted WITHDRAWN
        constant."""
        _seed_org_and_membership(
            api_url, org_id="ORG-WD-SOLD", account_id="ACC-WD-SOLD", membership_id="OM-WD-SOLD"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-WD-SOLD",
            org_id="ORG-WD-SOLD",
            account_id="ACC-WD-SOLD",
            membership_id="OM-WD-SOLD",
            physical_boat_id="PB-WD-SOLD",
            market_episode_id="ME-WD-SOLD",
            offer_revision_id="REV-WD-SOLD",
        )
        _publish_directly(
            api_url, listing_id="NL-WD-SOLD", org_id="ORG-WD-SOLD", account_id="ACC-WD-SOLD"
        )
        _log_in(client, "ACC-WD-SOLD")
        response = client.post(_withdraw_path("ORG-WD-SOLD", "NL-WD-SOLD"), headers=_csrf_headers())
        assert response.status_code == 200
        assert _lifecycle_state(api_url, "NL-WD-SOLD") is NativeListingLifecycleState.WITHDRAWN


# ---------------------------------------------------------------------------
# Reconfirm
# ---------------------------------------------------------------------------


class TestReconfirm:
    def test_unauthenticated_reconfirm_is_blocked(self, client: TestClient) -> None:
        response = client.post(
            _reconfirm_path("ORG-RC-UNAUTH", "NL-X"),
            json={"confirmation_id": str(uuid.uuid4())},
            headers=_csrf_headers(),
        )
        assert response.status_code == 401

    def test_own_active_reconfirm_succeeds_with_stable_operation_id(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-RC-OK", account_id="ACC-RC-OK", membership_id="OM-RC-OK"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-RC-OK",
            org_id="ORG-RC-OK",
            account_id="ACC-RC-OK",
            membership_id="OM-RC-OK",
            physical_boat_id="PB-RC-OK",
            market_episode_id="ME-RC-OK",
            offer_revision_id="REV-RC-OK",
        )
        _publish_directly(
            api_url, listing_id="NL-RC-OK", org_id="ORG-RC-OK", account_id="ACC-RC-OK"
        )
        _log_in(client, "ACC-RC-OK")
        confirmation_id = str(uuid.uuid4())
        response = client.post(
            _reconfirm_path("ORG-RC-OK", "NL-RC-OK"),
            json={"confirmation_id": confirmation_id},
            headers=_csrf_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "RECONFIRMED"
        assert body["occurred_at"]
        assert _lifecycle_state(api_url, "NL-RC-OK") is NativeListingLifecycleState.ACTIVE
        assert _confirmation_count(api_url) == 1

    def test_exact_retry_with_same_operation_id_is_idempotent(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-RC-RETRY", account_id="ACC-RC-RETRY", membership_id="OM-RC-RETRY"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-RC-RETRY",
            org_id="ORG-RC-RETRY",
            account_id="ACC-RC-RETRY",
            membership_id="OM-RC-RETRY",
            physical_boat_id="PB-RC-RETRY",
            market_episode_id="ME-RC-RETRY",
            offer_revision_id="REV-RC-RETRY",
        )
        _publish_directly(
            api_url, listing_id="NL-RC-RETRY", org_id="ORG-RC-RETRY", account_id="ACC-RC-RETRY"
        )
        _log_in(client, "ACC-RC-RETRY")
        confirmation_id = str(uuid.uuid4())
        first = client.post(
            _reconfirm_path("ORG-RC-RETRY", "NL-RC-RETRY"),
            json={"confirmation_id": confirmation_id},
            headers=_csrf_headers(),
        )
        second = client.post(
            _reconfirm_path("ORG-RC-RETRY", "NL-RC-RETRY"),
            json={"confirmation_id": confirmation_id},
            headers=_csrf_headers(),
        )
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert _confirmation_count(api_url) == 1

    def test_conflicting_operation_id_reuse_fails_closed(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-RC-CONFLICT", account_id="ACC-RC-CONFLICT", membership_id="OM-RC-C"
        )
        for suffix in ("A", "B"):
            _create_complete_draft_listing(
                api_url,
                listing_id=f"NL-RC-CONFLICT-{suffix}",
                org_id="ORG-RC-CONFLICT",
                account_id="ACC-RC-CONFLICT",
                membership_id="OM-RC-C",
                physical_boat_id=f"PB-RC-CONFLICT-{suffix}",
                market_episode_id=f"ME-RC-CONFLICT-{suffix}",
                offer_revision_id=f"REV-RC-CONFLICT-{suffix}",
            )
            _publish_directly(
                api_url,
                listing_id=f"NL-RC-CONFLICT-{suffix}",
                org_id="ORG-RC-CONFLICT",
                account_id="ACC-RC-CONFLICT",
            )
        _log_in(client, "ACC-RC-CONFLICT")
        confirmation_id = str(uuid.uuid4())
        first = client.post(
            _reconfirm_path("ORG-RC-CONFLICT", "NL-RC-CONFLICT-A"),
            json={"confirmation_id": confirmation_id},
            headers=_csrf_headers(),
        )
        assert first.status_code == 200
        second = client.post(
            _reconfirm_path("ORG-RC-CONFLICT", "NL-RC-CONFLICT-B"),
            json={"confirmation_id": confirmation_id},
            headers=_csrf_headers(),
        )
        assert second.status_code == 409
        assert second.json() == {"error": "operation_id_conflict"}
        assert _confirmation_count(api_url) == 1

    @pytest.mark.parametrize("draft_or_withdrawn", ["draft", "withdrawn"])
    def test_non_active_reconfirm_writes_no_confirmation(
        self, client: TestClient, api_url: str, draft_or_withdrawn: str
    ) -> None:
        listing_id = f"NL-RC-{draft_or_withdrawn.upper()}"
        org_id = f"ORG-RC-{draft_or_withdrawn.upper()}"
        account_id = f"ACC-RC-{draft_or_withdrawn.upper()}"
        membership_id = f"OM-RC-{draft_or_withdrawn.upper()}"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_complete_draft_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id=f"PB-{listing_id}",
            market_episode_id=f"ME-{listing_id}",
            offer_revision_id=f"REV-{listing_id}",
        )
        if draft_or_withdrawn == "withdrawn":
            _publish_directly(api_url, listing_id=listing_id, org_id=org_id, account_id=account_id)
            conn = psycopg.connect(api_url)
            try:
                org = MarketplaceOrganization(
                    id=MarketplaceOrganizationId(org_id),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                )
                membership = OrganizationMembership(
                    id=OrganizationMembershipId(f"OM-WD-{listing_id}"),
                    account_id=AccountId(account_id),
                    organization_id=org.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                )
                from hullq.persistence.native_listing_lifecycle import withdraw_native_listing

                withdraw_native_listing(
                    conn,
                    account_id=AccountId(account_id),
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(listing_id),
                )
                conn.commit()
            finally:
                conn.close()

        _log_in(client, account_id)
        response = client.post(
            _reconfirm_path(org_id, listing_id),
            json={"confirmation_id": str(uuid.uuid4())},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json() == {"error": "state_conflict"}
        assert _confirmation_count(api_url) == 0

    def test_reconfirm_does_not_change_lifecycle(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-RC-NOCHANGE",
            account_id="ACC-RC-NOCHANGE",
            membership_id="OM-RC-NC",
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-RC-NOCHANGE",
            org_id="ORG-RC-NOCHANGE",
            account_id="ACC-RC-NOCHANGE",
            membership_id="OM-RC-NC",
            physical_boat_id="PB-RC-NOCHANGE",
            market_episode_id="ME-RC-NOCHANGE",
            offer_revision_id="REV-RC-NOCHANGE",
        )
        _publish_directly(
            api_url,
            listing_id="NL-RC-NOCHANGE",
            org_id="ORG-RC-NOCHANGE",
            account_id="ACC-RC-NOCHANGE",
        )
        _log_in(client, "ACC-RC-NOCHANGE")
        response = client.post(
            _reconfirm_path("ORG-RC-NOCHANGE", "NL-RC-NOCHANGE"),
            json={"confirmation_id": str(uuid.uuid4())},
            headers=_csrf_headers(),
        )
        assert response.status_code == 200
        assert _lifecycle_state(api_url, "NL-RC-NOCHANGE") is NativeListingLifecycleState.ACTIVE
        assert _transition_count(api_url, "NL-RC-NOCHANGE") == 1

    def test_invalid_operation_id_is_rejected_without_writing(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-RC-BADID", account_id="ACC-RC-BADID", membership_id="OM-RC-BADID"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-RC-BADID",
            org_id="ORG-RC-BADID",
            account_id="ACC-RC-BADID",
            membership_id="OM-RC-BADID",
            physical_boat_id="PB-RC-BADID",
            market_episode_id="ME-RC-BADID",
            offer_revision_id="REV-RC-BADID",
        )
        _publish_directly(
            api_url, listing_id="NL-RC-BADID", org_id="ORG-RC-BADID", account_id="ACC-RC-BADID"
        )
        _log_in(client, "ACC-RC-BADID")
        response = client.post(
            _reconfirm_path("ORG-RC-BADID", "NL-RC-BADID"),
            json={"confirmation_id": "not-a-uuid"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_operation_id"}
        assert _confirmation_count(api_url) == 0

    def test_stale_active_reconfirm_restores_current_market_eligibility(
        self, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-RC-STALE", account_id="ACC-RC-STALE", membership_id="OM-RC-STALE"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-RC-STALE",
            org_id="ORG-RC-STALE",
            account_id="ACC-RC-STALE",
            membership_id="OM-RC-STALE",
            physical_boat_id="PB-RC-STALE",
            market_episode_id="ME-RC-STALE",
            offer_revision_id="REV-RC-STALE",
        )
        _publish_directly(
            api_url, listing_id="NL-RC-STALE", org_id="ORG-RC-STALE", account_id="ACC-RC-STALE"
        )

        now = datetime.now(UTC)
        # Two distinct fixed clocks: one far enough past the original
        # publish to observe STALE, and one a few minutes ahead of "now"
        # used both to perform the reconfirmation (so its real, DB-recorded
        # `occurred_at` -- necessarily at or after "now" -- still lands
        # at-or-before this clock) and to observe the freshly restored
        # eligibility. A single far-future clock cannot observe restoration:
        # reconfirming only ever records the real current instant, which
        # would still be far in that same clock's past.
        stale_client = _make_client(api_url, monkeypatch, as_of=now + timedelta(days=40))
        fresh_client = _make_client(api_url, monkeypatch, as_of=now + timedelta(minutes=5))
        try:
            _log_in(stale_client, "ACC-RC-STALE")
            stale_public = stale_client.get("/api/listings/NL-RC-STALE")
            assert stale_public.status_code == 404  # STALE: not current-market eligible

            _log_in(fresh_client, "ACC-RC-STALE")
            response = fresh_client.post(
                _reconfirm_path("ORG-RC-STALE", "NL-RC-STALE"),
                json={"confirmation_id": str(uuid.uuid4())},
                headers=_csrf_headers(),
            )
            assert response.status_code == 200
            assert response.json()["outcome"] == "RECONFIRMED"

            restored_public = fresh_client.get("/api/listings/NL-RC-STALE")
            assert restored_public.status_code == 200

            still_stale_public = stale_client.get("/api/listings/NL-RC-STALE")
            assert still_stale_public.status_code == 404
        finally:
            stale_client.close()
            fresh_client.close()


# ---------------------------------------------------------------------------
# Tenant isolation / non-enumeration (withdraw + reconfirm)
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    def test_withdraw_foreign_and_unknown_listing_share_identical_not_found_shape(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-WD-VICTIM", account_id="ACC-WD-VICTIM", membership_id="OM-WD-V"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-WD-ATTACKER", account_id="ACC-WD-ATTACKER", membership_id="OM-WD-A"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-WD-VICTIM",
            org_id="ORG-WD-VICTIM",
            account_id="ACC-WD-VICTIM",
            membership_id="OM-WD-V",
            physical_boat_id="PB-WD-VICTIM",
            market_episode_id="ME-WD-VICTIM",
            offer_revision_id="REV-WD-VICTIM",
        )
        _publish_directly(
            api_url, listing_id="NL-WD-VICTIM", org_id="ORG-WD-VICTIM", account_id="ACC-WD-VICTIM"
        )
        _log_in(client, "ACC-WD-ATTACKER")
        foreign = client.post(
            _withdraw_path("ORG-WD-ATTACKER", "NL-WD-VICTIM"), headers=_csrf_headers()
        )
        unknown = client.post(
            _withdraw_path("ORG-WD-ATTACKER", "NL-NEVER-CREATED-WD"), headers=_csrf_headers()
        )
        assert foreign.status_code == unknown.status_code == 404
        assert foreign.content == unknown.content
        assert _lifecycle_state(api_url, "NL-WD-VICTIM") is NativeListingLifecycleState.ACTIVE

    def test_reconfirm_foreign_and_unknown_listing_share_identical_not_found_shape(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-RC-VICTIM", account_id="ACC-RC-VICTIM", membership_id="OM-RC-V"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-RC-ATTACKER", account_id="ACC-RC-ATTACKER", membership_id="OM-RC-A"
        )
        _create_complete_draft_listing(
            api_url,
            listing_id="NL-RC-VICTIM",
            org_id="ORG-RC-VICTIM",
            account_id="ACC-RC-VICTIM",
            membership_id="OM-RC-V",
            physical_boat_id="PB-RC-VICTIM",
            market_episode_id="ME-RC-VICTIM",
            offer_revision_id="REV-RC-VICTIM",
        )
        _publish_directly(
            api_url, listing_id="NL-RC-VICTIM", org_id="ORG-RC-VICTIM", account_id="ACC-RC-VICTIM"
        )
        _log_in(client, "ACC-RC-ATTACKER")
        confirmation_id = str(uuid.uuid4())
        foreign = client.post(
            _reconfirm_path("ORG-RC-ATTACKER", "NL-RC-VICTIM"),
            json={"confirmation_id": confirmation_id},
            headers=_csrf_headers(),
        )
        unknown = client.post(
            _reconfirm_path("ORG-RC-ATTACKER", "NL-NEVER-CREATED-RC"),
            json={"confirmation_id": confirmation_id},
            headers=_csrf_headers(),
        )
        assert foreign.status_code == unknown.status_code == 404
        assert foreign.content == unknown.content
        assert _confirmation_count(api_url) == 0


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


class TestCsrf:
    def _setup_active_listing(self, api_url: str, *, suffix: str) -> tuple[str, str, str]:
        org_id, account_id, membership_id, listing_id = (
            f"ORG-CSRF-{suffix}",
            f"ACC-CSRF-{suffix}",
            f"OM-CSRF-{suffix}",
            f"NL-CSRF-{suffix}",
        )
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_complete_draft_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id=f"PB-{listing_id}",
            market_episode_id=f"ME-{listing_id}",
            offer_revision_id=f"REV-{listing_id}",
        )
        return org_id, account_id, listing_id

    def test_publish_without_csrf_headers_fails_closed(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = self._setup_active_listing(api_url, suffix="1")
        _log_in(client, account_id)
        response = client.post(_publish_path(org_id, listing_id))
        assert response.status_code == 403
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.DRAFT

    def test_publish_with_wrong_origin_fails_closed(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = self._setup_active_listing(api_url, suffix="2")
        _log_in(client, account_id)
        response = client.post(
            _publish_path(org_id, listing_id),
            headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": _CSRF_HEADER_VALUE,
            },
        )
        assert response.status_code == 403
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.DRAFT

    def test_publish_with_missing_fixed_header_fails_closed(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, listing_id = self._setup_active_listing(api_url, suffix="3")
        _log_in(client, account_id)
        response = client.post(_publish_path(org_id, listing_id), headers={"Origin": _WEB_ORIGIN})
        assert response.status_code == 403
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.DRAFT

    def test_draft_csrf_header_value_is_rejected_here(
        self, client: TestClient, api_url: str
    ) -> None:
        """The three broker-write channels' fixed CSRF header values are
        distinct: a valid professional-listing-draft-v1 header must not be
        accepted on this boundary."""
        org_id, account_id, listing_id = self._setup_active_listing(api_url, suffix="4")
        _log_in(client, account_id)
        response = client.post(
            _publish_path(org_id, listing_id),
            headers={
                "Origin": _WEB_ORIGIN,
                "X-HullQ-Requested-With": "professional-listing-draft-v1",
            },
        )
        assert response.status_code == 403
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.DRAFT

    def test_valid_same_origin_publish_succeeds(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = self._setup_active_listing(api_url, suffix="5")
        _log_in(client, account_id)
        response = client.post(_publish_path(org_id, listing_id), headers=_csrf_headers())
        assert response.status_code == 200

    def test_no_mutation_from_failed_csrf_attempts(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, listing_id = self._setup_active_listing(api_url, suffix="6")
        _log_in(client, account_id)
        client.post(_publish_path(org_id, listing_id))
        client.post(
            _publish_path(org_id, listing_id),
            headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": _CSRF_HEADER_VALUE,
            },
        )
        assert _lifecycle_state(api_url, listing_id) is NativeListingLifecycleState.DRAFT
        assert _transition_count(api_url, listing_id) == 0
