"""PostgreSQL integration tests for hullq.persistence.broker_identity — SLICE-0053.

Covers JIT `(provider, issuer, subject) -> Account` mapping (atomicity,
idempotency, concurrency-safety, no orphan Account rows) and the
Organization/Membership directory read/seed surface, each against its own
disposable schema (mirroring the SLICE-0048 integration test pattern).
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.broker_access import Provider
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
    fetch_active_memberships_for_account,
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
    get_or_create_account_for_identity,
    seed_marketplace_organization,
    seed_organization_membership,
    update_membership_state,
)


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
def broker_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0053_{uuid.uuid4().hex[:16]}"
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
def conn(broker_url: str) -> Generator[Any]:
    connection = psycopg.connect(broker_url)
    try:
        yield connection
    finally:
        connection.close()


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


class TestJitAccountMapping:
    def test_first_login_creates_account(self, conn: Any) -> None:
        result = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        )
        conn.commit()
        assert result.created is True
        assert isinstance(result.account_id, AccountId)

    def test_retry_same_identity_returns_same_account(self, conn: Any) -> None:
        first = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        )
        conn.commit()
        second = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        )
        conn.commit()
        assert second.created is False
        assert second.account_id == first.account_id

    def test_different_subject_gets_different_account(self, conn: Any) -> None:
        first = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        )
        conn.commit()
        second = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-2"
        )
        conn.commit()
        assert first.account_id != second.account_id

    def test_email_is_never_a_parameter(self) -> None:
        import inspect

        sig = inspect.signature(get_or_create_account_for_identity)
        assert "email" not in sig.parameters

    def test_concurrent_first_login_converges_on_one_account(self, broker_url: str) -> None:
        """Two connections racing on the identical identity must never
        create two Accounts (contract §4/§8 concurrency-safety)."""
        results: list[AccountId] = []
        errors: list[BaseException] = []
        barrier = threading.Barrier(2)

        def _attempt() -> None:
            try:
                own_conn = psycopg.connect(broker_url)
                try:
                    barrier.wait(timeout=5)
                    result = get_or_create_account_for_identity(
                        own_conn,
                        provider=Provider.AUTH0,
                        issuer="https://iss/",
                        subject="race-subject",
                    )
                    own_conn.commit()
                    results.append(result.account_id)
                finally:
                    own_conn.close()
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert not errors, errors
        assert len(results) == 2
        assert results[0] == results[1]

        with conn_for(broker_url) as verify_conn, verify_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM accounts")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM auth_identities")
            assert cur.fetchone()[0] == 1


class _ConnCtx:
    def __init__(self, url: str) -> None:
        self._conn = psycopg.connect(url)

    def __enter__(self) -> Any:
        return self._conn

    def __exit__(self, *exc_info: object) -> None:
        self._conn.close()


def conn_for(url: str) -> _ConnCtx:
    return _ConnCtx(url)


class TestOrganizationMembershipDirectory:
    def test_seed_and_fetch_organization(self, conn: Any) -> None:
        seed_marketplace_organization(conn, _org("ORG-1"))
        conn.commit()
        fetched = fetch_marketplace_organization(conn, MarketplaceOrganizationId("ORG-1"))
        assert fetched is not None
        assert fetched.professional_category is ProfessionalCategory.BROKER
        assert fetched.publishing_eligibility is OrganizationPublishingEligibility.ELIGIBLE

    def test_fetch_unknown_organization_returns_none(self, conn: Any) -> None:
        assert (
            fetch_marketplace_organization(conn, MarketplaceOrganizationId("NEVER-CREATED")) is None
        )

    def test_active_membership_visible_in_context(self, conn: Any) -> None:
        account = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        ).account_id
        seed_marketplace_organization(conn, _org("ORG-1"))
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-1"),
                account_id=account,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            ),
        )
        conn.commit()

        active = fetch_active_memberships_for_account(conn, account)
        assert len(active) == 1
        assert active[0].organization_id == MarketplaceOrganizationId("ORG-1")
        assert active[0].roles == frozenset({MembershipRole.PUBLISHER})

    def test_zero_memberships_is_empty_list_not_error(self, conn: Any) -> None:
        account = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-lonely"
        ).account_id
        conn.commit()
        assert fetch_active_memberships_for_account(conn, account) == []

    def test_inactive_membership_excluded_from_active_list(self, conn: Any) -> None:
        account = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        ).account_id
        seed_marketplace_organization(conn, _org("ORG-1"))
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-1"),
                account_id=account,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.MEMBER}),
                state=MembershipState.INACTIVE,
            ),
        )
        conn.commit()
        assert fetch_active_memberships_for_account(conn, account) == []

    def test_membership_present_but_inactive_is_returned_by_direct_fetch(self, conn: Any) -> None:
        """Distinct from the ACTIVE-only list: direct fetch must still
        surface an INACTIVE row so callers can distinguish NO_MEMBERSHIP
        from MEMBERSHIP_INACTIVE internally."""
        account = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        ).account_id
        seed_marketplace_organization(conn, _org("ORG-1"))
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-1"),
                account_id=account,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.MEMBER}),
                state=MembershipState.INACTIVE,
            ),
        )
        conn.commit()
        membership = fetch_membership_for_account_and_organization(
            conn, account, MarketplaceOrganizationId("ORG-1")
        )
        assert membership is not None
        assert membership.state is MembershipState.INACTIVE

    def test_no_membership_row_returns_none(self, conn: Any) -> None:
        account = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        ).account_id
        conn.commit()
        assert (
            fetch_membership_for_account_and_organization(
                conn, account, MarketplaceOrganizationId("NEVER-EXISTED")
            )
            is None
        )

    def test_update_membership_state_takes_effect(self, conn: Any) -> None:
        account = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        ).account_id
        seed_marketplace_organization(conn, _org("ORG-1"))
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-1"),
                account_id=account,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            ),
        )
        conn.commit()
        assert len(fetch_active_memberships_for_account(conn, account)) == 1

        update_membership_state(conn, OrganizationMembershipId("OM-1"), MembershipState.INACTIVE)
        conn.commit()
        assert fetch_active_memberships_for_account(conn, account) == []

    def test_reseed_replaces_role_set(self, conn: Any) -> None:
        account = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-1"
        ).account_id
        seed_marketplace_organization(conn, _org("ORG-1"))
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-1"),
                account_id=account,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.MEMBER}),
                state=MembershipState.ACTIVE,
            ),
        )
        conn.commit()
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-1"),
                account_id=account,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.OWNER, MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            ),
        )
        conn.commit()
        membership = fetch_membership_for_account_and_organization(
            conn, account, MarketplaceOrganizationId("ORG-1")
        )
        assert membership is not None
        assert membership.roles == frozenset({MembershipRole.OWNER, MembershipRole.PUBLISHER})

    def test_many_to_many_accounts_and_organizations(self, conn: Any) -> None:
        account_a = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-a"
        ).account_id
        account_b = get_or_create_account_for_identity(
            conn, provider=Provider.AUTH0, issuer="https://iss/", subject="sub-b"
        ).account_id
        seed_marketplace_organization(conn, _org("ORG-1"))
        seed_marketplace_organization(conn, _org("ORG-2"))
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-A1"),
                account_id=account_a,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.MEMBER}),
                state=MembershipState.ACTIVE,
            ),
        )
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-A2"),
                account_id=account_a,
                organization_id=MarketplaceOrganizationId("ORG-2"),
                roles=frozenset({MembershipRole.MEMBER}),
                state=MembershipState.ACTIVE,
            ),
        )
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId("OM-B1"),
                account_id=account_b,
                organization_id=MarketplaceOrganizationId("ORG-1"),
                roles=frozenset({MembershipRole.OWNER}),
                state=MembershipState.ACTIVE,
            ),
        )
        conn.commit()

        assert {
            m.organization_id.value for m in fetch_active_memberships_for_account(conn, account_a)
        } == {
            "ORG-1",
            "ORG-2",
        }
        assert {
            m.organization_id.value for m in fetch_active_memberships_for_account(conn, account_b)
        } == {"ORG-1"}
