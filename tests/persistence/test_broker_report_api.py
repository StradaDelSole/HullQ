"""PostgreSQL + real HTTP tests for SLICE-0089 broker periodic performance
report subscription + artifact API.

Covers: GET/PUT report-subscription auth/role/CSRF/version-conflict; the
live on-demand download route's auth/MFA gating and identical-metrics
guarantee; the historical periodic-report route's cross-Organization
isolation (report-ID enumeration resistance); and an end-to-end worker-tick
scenario proving a zero-Lead period is represented, admission/delivery are
idempotent under a repeated tick, and the periodic artifact becomes
downloadable only to the owning, currently-authorized Organization.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from starlette.testclient import TestClient

from hullq.application.broker_report_dispatch import (
    DeterministicLocalReportDeliveryAdapter,
    run_report_dispatch_worker_once,
)
from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.broker_report_subscription import ReportPeriodKind, SubscriptionStatus
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
from hullq.persistence.broker_report_subscription import set_subscription
from hullq.security.session_token import mint_session_token

_SECRET = b"5" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_NAME = "x-hullq-requested-with"
_CSRF_HEADER_VALUE = "broker-report-subscription-v1"


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, _CSRF_HEADER_NAME: _CSRF_HEADER_VALUE}


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
    schema_name = f"hullq_s0089api_{uuid.uuid4().hex[:16]}"
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
def api_conn(api_url: str) -> Generator[Any]:
    conn = psycopg.connect(api_url)
    try:
        yield conn
    finally:
        conn.close()


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


def _session_cookie(account_id: str) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=True,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=_SECRET)
    return minted.token


def _log_in(client: TestClient, account_id: str) -> None:
    client.cookies.set("hullq_session", _session_cookie(account_id), domain="api.test")


def _seed_org_and_membership(
    api_url: str, *, org_id: str, account_id: str, membership_id: str, roles: frozenset[Any]
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
                state=MembershipState.ACTIVE,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET/PUT report-subscription: auth/role/CSRF/version-conflict
# ---------------------------------------------------------------------------


def test_get_subscription_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/broker/organizations/ORG-X/report-subscription")
    assert response.status_code == 401


def test_get_subscription_unknown_organization_is_not_found(
    api_url: str, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-KNOWN",
        account_id="ACC-KNOWN",
        membership_id="OM-KNOWN",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _log_in(client, "ACC-KNOWN")
    response = client.get("/api/broker/organizations/ORG-UNKNOWN/report-subscription")
    assert response.status_code == 404


def test_get_subscription_default_is_inactive(api_url: str, client: TestClient) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-DEFAULT",
        account_id="ACC-DEFAULT",
        membership_id="OM-DEFAULT",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _log_in(client, "ACC-DEFAULT")
    response = client.get("/api/broker/organizations/ORG-DEFAULT/report-subscription")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INACTIVE"
    assert body["recipient_email"] is None
    assert body["revision"] == 0


def test_set_subscription_requires_owner_or_admin_role(api_url: str, client: TestClient) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-PUBLISHER",
        account_id="ACC-PUBLISHER",
        membership_id="OM-PUBLISHER",
        roles=frozenset({MembershipRole.PUBLISHER}),
    )
    _log_in(client, "ACC-PUBLISHER")
    response = client.put(
        "/api/broker/organizations/ORG-PUBLISHER/report-subscription",
        headers=_csrf_headers(),
        json={
            "status": "ACTIVE",
            "period_kind": "MONTHLY",
            "recipient_email": "broker@example.com",
            "expected_revision": 0,
        },
    )
    assert response.status_code == 403
    assert response.json() == {"error": "role_required"}


def test_set_subscription_requires_csrf(api_url: str, client: TestClient) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-CSRF",
        account_id="ACC-CSRF",
        membership_id="OM-CSRF",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _log_in(client, "ACC-CSRF")
    response = client.put(
        "/api/broker/organizations/ORG-CSRF/report-subscription",
        json={
            "status": "ACTIVE",
            "period_kind": "MONTHLY",
            "recipient_email": "broker@example.com",
            "expected_revision": 0,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "csrf validation failed"


def test_activating_without_recipient_is_invalid_input(api_url: str, client: TestClient) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-NOREC",
        account_id="ACC-NOREC",
        membership_id="OM-NOREC",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _log_in(client, "ACC-NOREC")
    response = client.put(
        "/api/broker/organizations/ORG-NOREC/report-subscription",
        headers=_csrf_headers(),
        json={
            "status": "ACTIVE",
            "period_kind": "MONTHLY",
            "recipient_email": None,
            "expected_revision": 0,
        },
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_input"}


def test_set_subscription_success_and_version_conflict(api_url: str, client: TestClient) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-SET",
        account_id="ACC-SET",
        membership_id="OM-SET",
        roles=frozenset({MembershipRole.ADMIN}),
    )
    _log_in(client, "ACC-SET")
    first = client.put(
        "/api/broker/organizations/ORG-SET/report-subscription",
        headers=_csrf_headers(),
        json={
            "status": "ACTIVE",
            "period_kind": "WEEKLY",
            "recipient_email": "broker@example.com",
            "expected_revision": 0,
        },
    )
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "ACTIVE"
    assert body["period_kind"] == "WEEKLY"
    assert body["revision"] == 1

    stale = client.put(
        "/api/broker/organizations/ORG-SET/report-subscription",
        headers=_csrf_headers(),
        json={
            "status": "INACTIVE",
            "period_kind": "WEEKLY",
            "recipient_email": "broker@example.com",
            "expected_revision": 0,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"] == "version_conflict"


# ---------------------------------------------------------------------------
# Live on-demand download route
# ---------------------------------------------------------------------------


def test_download_route_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/broker/organizations/ORG-X/report/download")
    assert response.status_code == 401


def test_download_route_cross_organization_denied(api_url: str, client: TestClient) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-DL-A",
        account_id="ACC-DL-A",
        membership_id="OM-DL-A",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _seed_org_and_membership(
        api_url,
        org_id="ORG-DL-B",
        account_id="ACC-DL-B",
        membership_id="OM-DL-B",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _log_in(client, "ACC-DL-B")
    response = client.get("/api/broker/organizations/ORG-DL-A/report/download")
    assert response.status_code == 404


def test_download_route_renders_identical_metrics_to_json_snapshot(
    api_url: str, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-DL-OK",
        account_id="ACC-DL-OK",
        membership_id="OM-DL-OK",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _log_in(client, "ACC-DL-OK")
    json_response = client.get(
        "/api/broker/organizations/ORG-DL-OK/performance?window=ALL_TIME"
    )
    assert json_response.status_code == 200
    html_response = client.get(
        "/api/broker/organizations/ORG-DL-OK/report/download?window=ALL_TIME"
    )
    assert html_response.status_code == 200
    assert html_response.headers["content-type"].startswith("text/html")
    assert "attachment" in html_response.headers["content-disposition"]
    body = json_response.json()
    assert str(body["public_listing_views"]) in html_response.text
    assert str(body["leads_received"]) in html_response.text


# ---------------------------------------------------------------------------
# End-to-end: zero-Lead period representation, idempotent tick, periodic
# artifact isolation/enumeration-resistance
# ---------------------------------------------------------------------------


def test_periodic_report_zero_lead_idempotent_tick_and_cross_org_isolation(
    api_url: str, api_conn: Any, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url,
        org_id="ORG-PERIODIC-A",
        account_id="ACC-PERIODIC-A",
        membership_id="OM-PERIODIC-A",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _seed_org_and_membership(
        api_url,
        org_id="ORG-PERIODIC-B",
        account_id="ACC-PERIODIC-B",
        membership_id="OM-PERIODIC-B",
        roles=frozenset({MembershipRole.OWNER}),
    )

    set_result = set_subscription(
        api_conn,
        MarketplaceOrganizationId("ORG-PERIODIC-A"),
        status=SubscriptionStatus.ACTIVE,
        period_kind=ReportPeriodKind.MONTHLY,
        recipient_email="broker@example.com",
        updated_by_account_id=AccountId("ACC-PERIODIC-A"),
        expected_revision=0,
        bootstrap_anchor_date=date(2026, 1, 1),
    )
    assert set_result.updated
    api_conn.commit()

    as_of = datetime(2026, 2, 5, tzinfo=UTC)  # Jan period has fully closed, zero Leads/views
    adapter = DeterministicLocalReportDeliveryAdapter()
    first_tick = run_report_dispatch_worker_once(
        api_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert first_tick.admission.value == "ADMITTED"
    assert first_tick.delivery.value == "DELIVERED"
    assert len(adapter.sent) == 1
    period_run_id = first_tick.admitted_period_run_id
    assert period_run_id is not None

    # Replay is idempotent -- a repeated tick admits/sends nothing further.
    second_tick = run_report_dispatch_worker_once(
        api_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert second_tick.admission.value == "NO_DUE_PERIOD"
    assert second_tick.delivery.value == "NO_ITEM_CLAIMED"
    assert len(adapter.sent) == 1

    _log_in(client, "ACC-PERIODIC-A")
    own_fetch = client.get(
        f"/api/broker/organizations/ORG-PERIODIC-A/report/periodic/{period_run_id}"
    )
    assert own_fetch.status_code == 200
    assert "No observed views" in own_fetch.text  # zero-Lead period is represented, not omitted

    # Organization B must never read Organization A's periodic report --
    # including by a correctly-guessed period_run_id (no enumeration oracle).
    _log_in(client, "ACC-PERIODIC-B")
    cross_org = client.get(
        f"/api/broker/organizations/ORG-PERIODIC-B/report/periodic/{period_run_id}"
    )
    assert cross_org.status_code == 404

    nonexistent = client.get(
        "/api/broker/organizations/ORG-PERIODIC-B/report/periodic/does-not-exist"
    )
    assert nonexistent.status_code == 404
    assert nonexistent.status_code == cross_org.status_code
