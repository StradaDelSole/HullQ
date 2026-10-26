"""broker_periodic_performance_reporting

Revision ID: f1a9c3d7b802
Revises: c7d4a1e95f36
Create Date: 2026-10-25 00:00:00.000000

SLICE-0089. Adds durable persistence for the broker periodic performance
report capability, layered on top of the accepted SLICE-0075 funnel
snapshot read model. Never changes any SLICE-0075 table.

Amendment (independent review round 1, pre-merge -- this revision has not
yet reached canonical main, so it is amended in place rather than chained):

    organization_report_subscription -- at most one bounded recurrence
        config per Organization (explicit opt-in, WEEKLY/MONTHLY,
        recipient email, OWNER/ADMIN-gated at the application layer).
        `revision` increments on every mutation (status/period_kind/
        recipient change); each PeriodRun snapshots the revision that
        authorized its admission, so a later revision change suppresses
        delivery rather than silently redirecting it. `next_period_start`
        (Finding B) is the durable admission cursor: the exact start of
        the next period to admit, advanced only by the dispatch worker,
        never derived from (and therefore never corrupted by purging)
        retained PeriodRun history.

    organization_report_period_run -- one durable job row per admitted
        period: the deterministic, idempotent admission unit, now keyed
        by `(organization_id, period_start, period_end)` -- the actual
        calendar-window identity -- rather than a bare sequence number
        that meant different things under different `period_kind`s
        (Finding B). `facts_json`/`generated_at` are captured once at
        admission time inside one consistent read-only snapshot
        transaction (Finding C), making the artifact a true as-of
        snapshot even if underlying SOLD/Lead facts keep evolving
        afterwards. `lease_expires_at`/`claim_generation` (Finding A)
        bound how long a claimed-but-never-recorded row can block
        recovery, with a fencing token so a superseded claim's late write
        can never silently overwrite a later claim's own result.
        `provider_idempotency_key` is a durable per-run identity a later
        real production delivery provider can use for its own dedup --
        this migration/implementation never activates such a provider.

    organization_report_delivery_attempts -- append-only delivery-attempt
        history per PeriodRun, mirroring the accepted SLICE-0071
        `lead_notification_delivery_attempts` pattern but with its own
        independent identity/retention (never shared with Lead
        notification semantics).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a9c3d7b802"
down_revision: str | None = "c7d4a1e95f36"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_report_subscription",
        sa.Column(
            "organization_id",
            sa.Text(),
            sa.ForeignKey("marketplace_organizations.organization_id"),
            primary_key=True,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="INACTIVE"),
        sa.Column("period_kind", sa.Text(), nullable=False, server_default="MONTHLY"),
        sa.Column("recipient_email", sa.Text(), nullable=True),
        sa.Column("anchor_date", sa.Date(), nullable=False),
        sa.Column("next_period_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_by_account_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "organization_report_period_run",
        sa.Column("period_run_id", sa.Text(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Text(),
            sa.ForeignKey("marketplace_organizations.organization_id"),
            nullable=False,
        ),
        sa.Column("period_index", sa.Integer(), nullable=False),
        sa.Column("period_kind", sa.Text(), nullable=False),
        sa.Column("period_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("period_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("subscription_revision", sa.Integer(), nullable=False),
        sa.Column("recipient_email", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="GENERATED"),
        sa.Column("facts_json", sa.Text(), nullable=False),
        sa.Column("listings_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider_idempotency_key", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "next_attempt_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("claimed_by", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("claim_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "organization_id", "period_start", "period_end", name="uq_report_period_run_org_window"
        ),
    )
    op.create_index(
        "ix_report_period_run_status_next_attempt",
        "organization_report_period_run",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_report_period_run_claimed_lease",
        "organization_report_period_run",
        ["claimed_at", "lease_expires_at"],
    )

    op.create_table(
        "organization_report_delivery_attempts",
        sa.Column("attempt_id", sa.Text(), primary_key=True),
        sa.Column(
            "period_run_id",
            sa.Text(),
            sa.ForeignKey("organization_report_period_run.period_run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attempted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_report_delivery_attempts_period_run_id",
        "organization_report_delivery_attempts",
        ["period_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_delivery_attempts_period_run_id",
        table_name="organization_report_delivery_attempts",
    )
    op.drop_table("organization_report_delivery_attempts")
    op.drop_index("ix_report_period_run_claimed_lease", table_name="organization_report_period_run")
    op.drop_index(
        "ix_report_period_run_status_next_attempt", table_name="organization_report_period_run"
    )
    op.drop_table("organization_report_period_run")
    op.drop_table("organization_report_subscription")
