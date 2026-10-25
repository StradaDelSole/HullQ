"""PostgreSQL-backed SLICE-0089 broker periodic report persistence/worker
tests.

Covers: subscription config optimistic concurrency; deterministic idempotent
period admission (repeated/concurrent ticks never double-admit); a
zero-Lead/zero-view period is still admitted and generated; the delivery
claim never lets two concurrent workers claim the same PeriodRun; bounded
retry -> eventual success; terminal failure after the attempt cap;
suppression when the subscription revision changes between generation and
dispatch (opt-out/recipient-change/deactivation); bounded purge; and the
independent-review round-1 amendment findings: bounded-lease claim recovery
with fencing (Finding A), cursor-based period continuity across a schedule
switch and across a full purge (Finding B), honest per-listing truncation
disclosure (Finding C), and dispatch-time recipient-authorization
revocation/offboarding (Finding D).
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
from hullq.domain.broker_report_subscription import (
    ReportDeliveryAttemptOutcome,
    ReportPeriodKind,
    SubscriptionStatus,
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
    update_membership_state,
)
from hullq.persistence.broker_report_subscription import (
    claim_next_deliverable_period_run,
    fetch_last_admitted_period_index,
    fetch_subscription,
    purge_expired_period_runs,
    record_delivery_attempt,
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


_DEFAULT_OWNER_ACCOUNT_ID = "ACC-SUB"


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


def _seed_owner_membership(
    conn: Any, organization_id: MarketplaceOrganizationId, *, account_id: str
) -> OrganizationMembershipId:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )
    conn.commit()
    membership_id = OrganizationMembershipId(f"OM-{account_id}-{organization_id.value}")
    seed_organization_membership(
        conn,
        OrganizationMembership(
            id=membership_id,
            account_id=AccountId(account_id),
            organization_id=organization_id,
            roles=frozenset({MembershipRole.OWNER}),
            state=MembershipState.ACTIVE,
        ),
    )
    conn.commit()
    return membership_id


def _activate_subscription(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    recipient_email: str,
    anchor_date: date,
    period_kind: ReportPeriodKind = ReportPeriodKind.MONTHLY,
    updated_by_account_id: str = _DEFAULT_OWNER_ACCOUNT_ID,
    seed_owner: bool = True,
) -> None:
    """Activates a subscription. By default also seeds an ACTIVE OWNER
    membership for *updated_by_account_id* (Finding D: dispatch re-checks
    this account's current authorization, so every happy-path test must
    give it a real, currently valid membership -- tests that specifically
    exercise revocation pass `seed_owner=False` and seed/mutate membership
    themselves)."""
    if seed_owner:
        _seed_owner_membership(conn, organization_id, account_id=updated_by_account_id)
    result = set_subscription(
        conn,
        organization_id,
        status=SubscriptionStatus.ACTIVE,
        period_kind=period_kind,
        recipient_email=recipient_email,
        updated_by_account_id=AccountId(updated_by_account_id),
        expected_revision=0,
        bootstrap_anchor_date=anchor_date,
        bootstrap_initial_period_kind=period_kind,
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
    assert default.next_period_start is None

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
        bootstrap_initial_period_kind=ReportPeriodKind.MONTHLY,
    )
    assert first.updated
    assert first.current.revision == 1
    assert first.current.next_period_start == datetime(2026, 1, 1, tzinfo=UTC)

    stale = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.INACTIVE,
        period_kind=ReportPeriodKind.MONTHLY,
        recipient_email="broker@example.com",
        updated_by_account_id=AccountId("ACC-1"),
        expected_revision=0,  # stale -- current revision is now 1
        bootstrap_anchor_date=date(2026, 1, 1),
        bootstrap_initial_period_kind=ReportPeriodKind.MONTHLY,
    )
    assert not stale.updated
    assert stale.current.revision == 1

    # Anchor date and the admission cursor never change across later
    # mutations, even a period_kind change.
    changed = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.ACTIVE,
        period_kind=ReportPeriodKind.WEEKLY,
        recipient_email="broker2@example.com",
        updated_by_account_id=AccountId("ACC-1"),
        expected_revision=1,
        bootstrap_anchor_date=date(2099, 1, 1),  # ignored -- row already exists
        bootstrap_initial_period_kind=ReportPeriodKind.WEEKLY,
    )
    assert changed.updated
    assert changed.current.anchor_date == date(2026, 1, 1)
    assert changed.current.next_period_start == datetime(2026, 1, 1, tzinfo=UTC)


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
    assert adapter.sent[0].idempotency_key  # Finding A: a durable provider dedup key

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

    first = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
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
    # strictly before dispatch. The same already-authorized account makes
    # this change, so the ONLY thing under test here is the stale-revision
    # suppression -- not Finding D's separate authorization re-check.
    current = fetch_subscription(report_conn, organization_id)
    deactivated = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.INACTIVE,
        period_kind=current.period_kind,
        recipient_email=current.recipient_email,
        updated_by_account_id=AccountId(_DEFAULT_OWNER_ACCOUNT_ID),
        expected_revision=current.revision,
        bootstrap_anchor_date=current.anchor_date or date(2026, 1, 1),
        bootstrap_initial_period_kind=current.period_kind,
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
# Amendment, Finding A: bounded-lease claim recovery + fencing
# ---------------------------------------------------------------------------


def test_stale_claim_is_reclaimed_after_lease_expiry_with_audit_entry(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-LEASE")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    admitted_id = _admit_next_due_period(report_conn, as_of=as_of)
    assert admitted_id is not None

    # Simulate a worker crash: claim directly (bypassing the full tick)
    # with a short lease, and never call record_delivery_attempt.
    first_claim = claim_next_deliverable_period_run(
        report_conn, worker_id="crashed-worker", as_of=as_of, lease_seconds=60
    )
    assert first_claim is not None
    assert first_claim.was_reclaimed is False
    assert first_claim.claim_generation == 1

    # Before the lease expires, nobody else can claim it.
    too_soon = claim_next_deliverable_period_run(
        report_conn, worker_id="w2", as_of=as_of + timedelta(seconds=30), lease_seconds=60
    )
    assert too_soon is None

    # After lease expiry, a later tick recovers the row (reclaim).
    later = as_of + timedelta(seconds=61)
    adapter = DeterministicLocalReportDeliveryAdapter()
    recovered = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w2", as_of=later
    )
    assert recovered.was_reclaimed is True
    assert recovered.delivery is DeliveryOutcome.DELIVERED
    assert len(adapter.sent) == 1

    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT outcome FROM organization_report_delivery_attempts "
            "WHERE period_run_id = %s ORDER BY attempted_at ASC",
            [admitted_id],
        )
        outcomes = [row[0] for row in cur.fetchall()]
    assert outcomes == ["RECLAIMED_AFTER_LEASE_EXPIRY", "DELIVERED"]


def test_superseded_claim_fence_rejects_a_late_stale_write(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-FENCE")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    admitted_id = _admit_next_due_period(report_conn, as_of=as_of)
    assert admitted_id is not None

    stale_claim = claim_next_deliverable_period_run(
        report_conn, worker_id="w1", as_of=as_of, lease_seconds=60
    )
    assert stale_claim is not None
    stale_generation = stale_claim.claim_generation

    later = as_of + timedelta(seconds=61)
    fresh_claim = claim_next_deliverable_period_run(
        report_conn, worker_id="w2", as_of=later, lease_seconds=60
    )
    assert fresh_claim is not None
    assert fresh_claim.claim_generation != stale_generation

    record_delivery_attempt(
        report_conn,
        admitted_id,
        outcome=ReportDeliveryAttemptOutcome.DELIVERED,
        expected_claim_generation=fresh_claim.claim_generation,
        provider_message_id="msg-fresh",
        as_of=later,
    )

    # The original (now-superseded) claimer's late write must never apply.
    with pytest.raises(RuntimeError):
        record_delivery_attempt(
            report_conn,
            admitted_id,
            outcome=ReportDeliveryAttemptOutcome.DELIVERED,
            expected_claim_generation=stale_generation,
            provider_message_id="msg-stale",
            as_of=later,
        )

    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT provider_message_id FROM organization_report_period_run WHERE period_run_id = %s",
            [admitted_id],
        )
        (stored_message_id,) = cur.fetchone()
    assert stored_message_id == "msg-fresh"


# ---------------------------------------------------------------------------
# Amendment, Finding B: cursor-based continuity across schedule switch/purge
# ---------------------------------------------------------------------------


def test_schedule_switch_continues_from_cursor_not_a_stale_window(report_conn: Any) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-SWITCH")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
        period_kind=ReportPeriodKind.MONTHLY,
    )

    first_as_of = datetime(2026, 2, 2, tzinfo=UTC)
    first_id = _admit_next_due_period(report_conn, as_of=first_as_of)
    assert first_id is not None
    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT period_start, period_end FROM organization_report_period_run WHERE period_run_id = %s",
            [first_id],
        )
        first_start, first_end = cur.fetchone()
    assert first_start == datetime(2026, 1, 1, tzinfo=UTC)
    assert first_end == datetime(2026, 2, 1, tzinfo=UTC)

    # Switch WEEKLY <- MONTHLY (same already-authorized account; this test
    # is about period continuity, not Finding D's authorization check).
    current = fetch_subscription(report_conn, organization_id)
    switched = set_subscription(
        report_conn,
        organization_id,
        status=SubscriptionStatus.ACTIVE,
        period_kind=ReportPeriodKind.WEEKLY,
        recipient_email=current.recipient_email,
        updated_by_account_id=AccountId(_DEFAULT_OWNER_ACCOUNT_ID),
        expected_revision=current.revision,
        bootstrap_anchor_date=current.anchor_date,
        bootstrap_initial_period_kind=current.period_kind,
    )
    assert switched.updated
    report_conn.commit()

    second_as_of = datetime(2026, 2, 9, tzinfo=UTC)
    second_id = _admit_next_due_period(report_conn, as_of=second_as_of)
    assert second_id is not None
    assert second_id != first_id
    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT period_start, period_end FROM organization_report_period_run WHERE period_run_id = %s",
            [second_id],
        )
        second_start, second_end = cur.fetchone()
    # The next period starts exactly where the MONTHLY period ended --
    # never a stale WEEKLY window re-derived from the original anchor.
    assert second_start == first_end == datetime(2026, 2, 1, tzinfo=UTC)
    assert second_end == datetime(2026, 2, 8, tzinfo=UTC)


def test_full_purge_then_resumed_tick_continues_from_cursor_not_index_zero(
    report_conn: Any,
) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-PURGE-RESUME")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
    )
    as_of = datetime(2026, 2, 2, tzinfo=UTC)
    first_id = _admit_next_due_period(report_conn, as_of=as_of)
    assert first_id is not None

    # Purge every retained row for this Organization -- MAX(period_index)
    # over period_run history is now unavailable.
    deleted = purge_expired_period_runs(
        report_conn, older_than=timedelta(seconds=0), as_of=datetime.now(UTC) + timedelta(seconds=1)
    )
    assert deleted == 1
    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM organization_report_period_run WHERE organization_id = %s",
            [organization_id.value],
        )
        (remaining,) = cur.fetchone()
    assert remaining == 0

    later_as_of = datetime(2026, 3, 3, tzinfo=UTC)
    resumed_id = _admit_next_due_period(report_conn, as_of=later_as_of)
    assert resumed_id is not None
    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT period_start, period_end FROM organization_report_period_run WHERE period_run_id = %s",
            [resumed_id],
        )
        resumed_start, resumed_end = cur.fetchone()
    # Must be the *second* MONTHLY period (Feb), never a re-admission of
    # the already-delivered/purged first period (Jan) and never any
    # unbounded catch-up skip -- the cursor alone, not retained history,
    # governs where the worker resumes.
    assert resumed_start == datetime(2026, 2, 1, tzinfo=UTC)
    assert resumed_end == datetime(2026, 3, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Amendment, Finding C: honest per-listing truncation disclosure
# ---------------------------------------------------------------------------


def test_admission_honestly_discloses_listing_truncation_in_stored_snapshot(
    report_conn: Any,
) -> None:
    import json as _json

    from hullq.application.broker_report_rendering import render_report_html
    from hullq.domain.broker_report_subscription import MAX_REPORT_LISTING_ROWS
    from hullq.domain.listing_telemetry import ListingViewOperationId
    from hullq.domain.market_identity import (
        MarketEpisode,
        MarketEpisodeId,
        NativeListing,
        NativeListingId,
        PhysicalBoat,
        PhysicalBoatId,
    )
    from hullq.persistence.market_episode import create_market_episode
    from hullq.persistence.native_listing import create_native_listing
    from hullq.persistence.native_listing_view_event import record_public_listing_view
    from hullq.persistence.physical_boat import create_physical_boat

    organization_id = _seed_org(report_conn, org_id="ORG-TRUNC")
    _seed_owner_membership(report_conn, organization_id, account_id=_DEFAULT_OWNER_ACCOUNT_ID)
    org = MarketplaceOrganization(
        id=organization_id,
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-{_DEFAULT_OWNER_ACCOUNT_ID}-{organization_id.value}"),
        account_id=AccountId(_DEFAULT_OWNER_ACCOUNT_ID),
        organization_id=organization_id,
        # PUBLISHER is required by `create_native_listing`'s own SLICE-0041
        # eligibility check -- OWNER alone (sufficient for the report
        # subscription's own OWNER/ADMIN gate) is not.
        roles=frozenset({MembershipRole.OWNER, MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    account = AccountId(_DEFAULT_OWNER_ACCOUNT_ID)

    # A real view event (not a full publish/offer/claim fixture -- cheaper,
    # and `fetch_organization_performance_facts` already only ever
    # populates the per-listing breakdown from observed activity) on
    # MAX_REPORT_LISTING_ROWS + 1 distinct listings, directly proving the
    # real bound end-to-end.
    listing_count = MAX_REPORT_LISTING_ROWS + 1
    view_at = datetime(2026, 1, 15, tzinfo=UTC)
    for i in range(listing_count):
        listing_id = f"NL-TRUNC-{i}"
        physical_boat_id = f"PB-TRUNC-{i}"
        market_episode_id = f"ME-TRUNC-{i}"
        create_physical_boat(
            report_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id))
        )
        create_market_episode(
            report_conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(market_episode_id),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
            ),
        )
        create_native_listing(
            report_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
            ),
        )
        record_public_listing_view(
            report_conn,
            operation_id=ListingViewOperationId(f"OP-TRUNC-{i}"),
            native_listing_id=NativeListingId(listing_id),
            publishing_organization_id=organization_id,
            occurred_at=view_at,
        )
        report_conn.commit()

    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
        seed_owner=False,  # already seeded above
    )

    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    admitted_id = _admit_next_due_period(report_conn, as_of=as_of)
    assert admitted_id is not None

    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT facts_json, listings_truncated FROM organization_report_period_run "
            "WHERE period_run_id = %s",
            [admitted_id],
        )
        facts_json, column_flag = cur.fetchone()

    facts = _json.loads(facts_json)
    assert column_flag is True
    # Finding C's exact bug: the flag must be embedded *inside* the stored
    # snapshot itself, not only in a sibling column the renderer never
    # looks at.
    assert facts["listings_truncated"] is True
    assert len(facts["listings"]) == MAX_REPORT_LISTING_ROWS
    # Aggregate totals are never truncated -- the full observed population
    # is still factually counted even though the per-listing rows are
    # bounded.
    assert facts["public_listing_views"] == listing_count
    assert len(facts["listings"]) < listing_count

    html = render_report_html(
        organization_display_name="Acme Yachts", generated_at_iso=as_of.isoformat(), facts=facts
    )
    assert "truncated" in html.lower()


# ---------------------------------------------------------------------------
# Amendment, Finding D: recipient authorization revocation/offboarding
# ---------------------------------------------------------------------------


def test_delivery_suppressed_when_configuring_account_membership_is_revoked(
    report_conn: Any,
) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-REVOKED")
    membership_id = _seed_owner_membership(report_conn, organization_id, account_id="ACC-LEAVING")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
        updated_by_account_id="ACC-LEAVING",
        seed_owner=False,
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    admitted_id = _admit_next_due_period(report_conn, as_of=as_of)
    assert admitted_id is not None

    # The configuring account leaves the Organization strictly after
    # generation, strictly before dispatch -- the subscription's own
    # revision never changes, only the account's membership.
    update_membership_state(report_conn, membership_id, MembershipState.INACTIVE)
    report_conn.commit()

    adapter = DeterministicLocalReportDeliveryAdapter()
    result = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert result.delivery is DeliveryOutcome.RECIPIENT_UNAUTHORIZED
    assert len(adapter.sent) == 0

    with report_conn.cursor() as cur:
        cur.execute(
            "SELECT outcome FROM organization_report_delivery_attempts WHERE period_run_id = %s",
            [admitted_id],
        )
        (outcome,) = cur.fetchone()
    assert outcome == "RECIPIENT_UNAUTHORIZED"


def test_delivery_suppressed_when_configuring_account_loses_owner_admin_role(
    report_conn: Any,
) -> None:
    organization_id = _seed_org(report_conn, org_id="ORG-DEMOTED")
    membership_id = _seed_owner_membership(report_conn, organization_id, account_id="ACC-DEMOTED")
    _activate_subscription(
        report_conn,
        organization_id,
        recipient_email="broker@example.com",
        anchor_date=date(2026, 1, 1),
        updated_by_account_id="ACC-DEMOTED",
        seed_owner=False,
    )
    as_of = datetime(2026, 2, 5, tzinfo=UTC)
    admitted_id = _admit_next_due_period(report_conn, as_of=as_of)
    assert admitted_id is not None

    # Demote to a non-OWNER/ADMIN role (membership stays ACTIVE).
    seed_organization_membership(
        report_conn,
        OrganizationMembership(
            id=membership_id,
            account_id=AccountId("ACC-DEMOTED"),
            organization_id=organization_id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        ),
    )
    report_conn.commit()

    adapter = DeterministicLocalReportDeliveryAdapter()
    result = run_report_dispatch_worker_once(
        report_conn, adapter=adapter, worker_id="w1", as_of=as_of
    )
    assert result.delivery is DeliveryOutcome.RECIPIENT_UNAUTHORIZED
    assert len(adapter.sent) == 0


def test_recipient_authorization_denied_for_a_nonexistent_organization(report_conn: Any) -> None:
    """A live PeriodRun can never actually reference a since-hard-deleted
    Organization under this schema's own FK constraints (no delete-
    Organization operation exists in this codebase at all), so this
    directly unit-tests the authorization helper's own "Organization no
    longer exists" branch rather than fighting an unreachable end-to-end
    scenario."""
    from hullq.application.broker_report_dispatch import _recipient_authorization_ok

    assert (
        _recipient_authorization_ok(
            report_conn,
            MarketplaceOrganizationId("ORG-NEVER-EXISTED"),
            AccountId("ACC-X"),
        )
        is False
    )


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
