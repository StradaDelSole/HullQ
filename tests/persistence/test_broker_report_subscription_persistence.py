"""PostgreSQL-backed SLICE-0089 broker periodic report persistence/worker
tests.

Covers: subscription config optimistic concurrency; deterministic idempotent
period admission (repeated/concurrent ticks never double-admit); a
zero-Lead/zero-view period is still admitted and generated; the delivery
claim never lets two concurrent workers claim the same PeriodRun; bounded
retry -> eventual success; terminal failure after the attempt cap;
suppression when the subscription revision changes between generation and
dispatch (opt-out/recipient-change/deactivation); and bounded purge.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.broker_report_dispatch import (
    AdmissionOutcome,
    DeliveryOutcome,
    DeliverySendOutcome,
    DeliverySendResult,
    DeterministicLocalReportDeliveryAdapter,
    _admit_next_due_period,
    run_report_dispatch_worker_once,
)
from hullq.domain.broker_report_subscription import ReportPeriodKind, SubscriptionStatus
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.broker_report_subscription import (
    fetch_last_admitted_period_index,
    fetch_subscription,
    purge_expired_period_runs,
    set_subscription,
)

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors test_lead_notification_persistence.py)
# ---------------------------------------------------------------------------


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
def report_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0089r_{uuid.uuid4().hex[:16]}"
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
def report_conn(report_url: str) -> Generator[Any]:
    conn = psycopg.connect(report_url)
    try:
        yield conn
    finally:
        conn.close()


def _seed_org(conn: Any, *, org_id: str) -> MarketplaceOrganizationId:
    organization_id = MarketplaceOrganizationId(org_id)
    seed_marketplace_organization(
        conn,
        MarketplaceOrganization(
            id=organization_id,
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        ),
    )
    conn.commit()
    return organization_id


def _activate_subscription(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    recipient_email: str,
    anchor_date: date,
    period_kind: ReportPeriodKind = ReportPeriodKind.MONTHLY,
) -> None:
    result = set_subscription(
        conn,
        organization_id,
        status=SubscriptionStatus.ACTIVE,
        period_kind=period_kind,
        recipient_email=recipient_email,
        updated_by_account_id=AccountId("ACC-SUB"),
        expected_revision=0,
        bootstrap_anchor_date=anchor_date,
    )
    assert result.updated, result
    conn.commit()


# ---------------------------------------------------------------------------
# Subscription config optimistic concurrency
# ---------------------------------------------------------------------------


def test_subscription_default_and_optimistic_concurrency(report_conn: Any) -> None:
    organization_id = MarketplaceOrganizationId("ORG-SUB-DEFAULT")
    default = fetch_subscription(report_conn, organization_id)
    assert default.status is SubscriptionStatus.INACTIVE
    assert default.revision == 0
    assert default.anchor_date is None

    seed_marketplace_organization(
        report_conn,
        MarketplaceOrganization(
            id=organization_id,
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        ),
    )
    report_conn.commit()

    first = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.ACTIVE,
        period_kind=ReportPeriodKind.MONTHLY,
        recipient_email="broker@example.com",
        updated_by_account_id=AccountId("ACC-1"),
        expected_revision=0,
        bootstrap_anchor_date=date(2026, 1, 1),
    )
    assert first.updated
    assert first.current.revision == 1

    stale = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.INACTIVE,
        period_kind=ReportPeriodKind.MONTHLY,
        recipient_email="broker@example.com",
        updated_by_account_id=AccountId("ACC-1"),
        expected_revision=0,  # stale -- current revision is now 1
        bootstrap_anchor_date=date(2026, 1, 1),
    )
    assert not stale.updated
    assert stale.current.revision == 1

    # Anchor date never changes across later mutations, even period_kind.
    changed = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.ACTIVE,
        period_kind=ReportPeriodKind.WEEKLY,
        recipient_email="broker2@example.com",
        updated_by_account_id=AccountId("ACC-1"),
        expected_revision=1,
        bootstrap_anchor_date=date(2099, 1, 1),  # ignored -- row already exists
    )
    assert changed.updated
    assert changed.current.anchor_date == date(2026, 1, 1)


# ---------------------------------------------------------------------------
# Deterministic idempotent admission + zero-Lead representation
# ---------------------------------------------------------------------------


def test_worker_tick_admits_one_closed_zero_lead_period_and_delivers(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-ZERO")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )

    as_of = datetime(2026, 2, 5, tzinfo=UTC)  # the Jan period has fully closed
    adapter = DeterministicLocalReportDeliveryAdapter()
    result = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert result.admission is AdmissionOutcome.ADMITTED
    assert result.delivery is DeliveryOutcome.DELIVERED
    assert len(adapter.sent) == 1
    # The zero-Lead period is genuinely represented in the delivered body,
    # never silently omitted.
    assert "Acme" not in adapter.sent[0].body  # sanity: no fabricated brand text
    assert "Report" in adapter.sent[0].body

    assert fetch_last_admitted_period_index(report_conn, organization_id) == 0


def test_repeated_worker_ticks_never_double_admit_or_double_send(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-REPEAT")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    adapter = DeterministicLocalReportDeliveryAdapter()

    first = run_report_dispatch_worker_once(report_conn, adapter=adapter, worker_id="w1", as_of=as_of)
    assert first.admission is AdmissionOutcome.ADMITTED
    assert first.delivery is DeliveryOutcome.DELIVERED

    second = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert second.admission is AdmissionOutcome.NO_DUE_PERIOD
    assert second.delivery is DeliveryOutcome.NO_ITEM_CLAIMED
    assert len(adapter.sent) == 1


def test_concurrent_admission_never_admits_the_same_period_twice(report_url: str) -> None:
    conn = psycopg.connect(report_url)
    try:
        organization_id = _seed_org(conn, org_id="ORG-RACE")
        _activate_subscription(
            conn,
            organization_id,
            recipient_email="broker@example.com",
            anchor_date=date(2026, 1, 1),
        )
    finally:
        conn.close()

    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _run(worker_id: str) -> None:
        thread_conn = psycopg.connect(report_url)
        try:
            adapter = DeterministicLocalReportDeliveryAdapter()
            barrier.wait()
            result = run_report_dispatch_worker_once(
                thread_conn, adapter=adapter, worker_id=worker_id, as_of=as_of
            )
            with lock:
                outcomes.append(result.admission.value)
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=_run, args=(f"w{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["ADMITTED", "NO_DUE_PERIOD"]

    verify_conn = psycopg.connect(report_url)
    try:
        with verify_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM organization_report_period_run WHERE organization_id = %s",
                [organization_id.value],
            )
            (count,) = cur.fetchone()
    finally:
        verify_conn.close()
    assert count == 1


def test_concurrent_delivery_claims_never_claim_the_same_period_run(report_url: str) -> None:
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    conn = psycopg.connect(report_url)
    try:
        organization_id = _seed_org(conn, org_id="ORG-CLAIM-RACE")
        _activate_subscription(
            conn,
            organization_id,
            recipient_email="broker@example.com",
            anchor_date=date(2026, 1, 1),
        )
        # Admit the PeriodRun up front (own private step, not via the full
        # worker tick) so the concurrency race below exercises only the
        # delivery-claim step in isolation.
        admitted_id = _admit_next_due_period(conn, as_of=as_of)
        assert admitted_id is not None
    finally:
        conn.close()

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _run(worker_id: str) -> None:
        thread_conn = psycopg.connect(report_url)
        try:
            adapter = DeterministicLocalReportDeliveryAdapter()
            barrier.wait()
            result = run_report_dispatch_worker_once(
                thread_conn, adapter=adapter, worker_id=worker_id, as_of=as_of
            )
            with lock:
                outcomes.append(result.delivery.value)
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=_run, args=(f"w{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["DELIVERED", "NO_ITEM_CLAIMED"]


# ---------------------------------------------------------------------------
# Retry / terminal failure / suppression
# ---------------------------------------------------------------------------


def test_retryable_failure_then_later_success(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-RETRY")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    adapter = DeterministicLocalReportDeliveryAdapter()
    adapter.queue_outcome(
        DeliverySendResult(outcome=DeliverySendOutcome.RETRYABLE_ERROR, error_text="smtp timeout")
    )

    failing = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert failing.delivery is DeliveryOutcome.RETRYABLE_FAILURE

    later = as_of + timedelta(seconds=1000)
    retried = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=later
    )
    assert retried.delivery is DeliveryOutcome.DELIVERED
    assert len(adapter.sent) == 2


def test_terminal_failure_after_attempt_cap(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-TERMINAL")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    adapter = DeterministicLocalReportDeliveryAdapter()
    for _ in range(10):
        adapter.queue_outcome(
            DeliverySendResult(outcome=DeliverySendOutcome.RETRYABLE_ERROR, error_text="down")
        )

    last_outcome = None
    current_as_of = as_of
    for _ in range(6):
        result = run_report_dispatch_worker_once(
            report_conn, adapter=adapter, worker_id="w1", as_of=current_as_of
        )
        last_outcome = result.delivery
        current_as_of = current_as_of + timedelta(seconds=1000)
        if last_outcome in (DeliveryOutcome.TERMINAL_FAILURE, DeliveryOutcome.NO_ITEM_CLAIMED):
            break
    assert last_outcome is DeliveryOutcome.TERMINAL_FAILURE

    # A terminal failure is never retried again.
    final = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=current_as_of + timedelta(days=1)
    )
    assert final.delivery is DeliveryOutcome.NO_ITEM_CLAIMED


def test_opt_out_between_generation_and_dispatch_suppresses_delivery(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-SUPPRESS")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    admitted_id = _admit_next_due_period(report_conn, as_of=as_of)
    assert admitted_id is not None

    # Opt out (bumps the subscription revision) strictly after generation,
    # strictly before dispatch.
    current = fetch_subscription(report_conn, organization_id)
    deactivated = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.INACTIVE,
        period_kind=current.period_kind,
        recipient_email=current.recipient_email,
        updated_by_account_id=AccountId("ACC-1"),
        expected_revision=current.revision,
        bootstrap_anchor_date=current.anchor_date or date(2026, 1, 1),
    )
    assert deactivated.updated
    report_conn.commit()

    adapter = DeterministicLocalReportDeliveryAdapter()
    result = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert result.delivery is DeliveryOutcome.SUPPRESSED
    assert len(adapter.sent) == 0  # never sent to a stale/deactivated target


# ---------------------------------------------------------------------------
# Bounded purge
# ---------------------------------------------------------------------------


def test_purge_expired_period_runs_is_bounded(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-PURGE")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    run_report_dispatch_worker_once(
        report_conn, adapter=DeterministicLocalReportDeliveryAdapter(), worker_id="w1", as_of=as_of
    )

    # `created_at` is the row's real wall-clock insertion time (retention is
    # about real elapsed time, independent of the synthetic `as_of` used
    # above for period-window math) -- purge bounds must be evaluated
    # against real "now", not the synthetic period `as_of`.
    real_now = datetime.now(UTC)

    not_yet_expired = purge_expired_period_runs(
        report_conn, older_than=timedelta(days=400), as_of=real_now
    )
    assert not_yet_expired == 0

    deleted = purge_expired_period_runs(
        report_conn, older_than=timedelta(seconds=0), as_of=real_now + timedelta(seconds=1)
    )
    assert deleted == 1
