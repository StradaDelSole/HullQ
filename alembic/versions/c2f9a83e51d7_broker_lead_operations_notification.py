"""broker_lead_operations_notification

Revision ID: c2f9a83e51d7
Revises: b7a1f04d9c58
Create Date: 2026-09-29 12:00:00.000000

SLICE-0071. Adds the durable persistence for the broker Lead operating loop
layered on top of the SLICE-0070 immutable `buyer_leads` envelope:

    lead_operational_state -- one mutable row per Lead (created lazily on
        first mutation, never at Lead-creation time): current operational
        status, unread/read state, current assignment, current follow-up due
        date and close reason, plus an integer `version` for optimistic
        concurrency. Absence of a row is equivalent to the default
        NEW/unread/unassigned state (contract §5/§6).

    lead_timeline_events -- append-only broker-workflow history: notes,
        status/assignment/read/follow-up mutations, contact attempts and
        closure (contract §8/§8A). Never edits/removes a prior event.

    organization_lead_notification_config -- at most one primary
        Lead-notification email per Organization (contract §9), mutable only
        by current ACTIVE OWNER/ADMIN at the application layer.

    lead_notification_outbox -- one durable notification intent per Lead,
        created atomically with Lead creation (contract §10); `lead_id` is
        UNIQUE so retrying an already-resolved submission_operation_id can
        never create a second intent. Delivery-state/attempt/claim columns
        support the retry/claim worker (contract §12).

    lead_notification_delivery_attempts -- append-only delivery-attempt
        history per outbox row, preserving the
        "Lead -> notification intent -> delivery attempt(s) -> optional
        provider message identifier" correlation (contract §12A) without
        committing to any production-provider schema.

    lead_acquisition_provenance -- one immutable creation-time evidence row
        per Lead (contract §8B): bounded acquisition/discovery evidence,
        defaulting to UNKNOWN when no evidence was supplied. Never mutated
        after creation; never affects Lead eligibility/quality, buyer email
        verification or Search/listing/public truth.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2f9a83e51d7"
down_revision: str | None = "b7a1f04d9c58"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_operational_state",
        sa.Column(
            "lead_id",
            sa.Text(),
            sa.ForeignKey("buyer_leads.lead_id"),
            primary_key=True,
        ),
        sa.Column("operational_status", sa.Text(), nullable=False, server_default="NEW"),
        sa.Column("is_unread", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("assigned_account_id", sa.Text(), nullable=True),
        sa.Column("follow_up_due_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "lead_timeline_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column(
            "lead_id",
            sa.Text(),
            sa.ForeignKey("buyer_leads.lead_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_account_id", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("note_text", sa.Text(), nullable=True),
        sa.Column("contact_channel", sa.Text(), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_lead_timeline_events_lead_id_occurred_at",
        "lead_timeline_events",
        ["lead_id", "occurred_at"],
    )

    op.create_table(
        "organization_lead_notification_config",
        sa.Column(
            "organization_id",
            sa.Text(),
            sa.ForeignKey("marketplace_organizations.organization_id"),
            primary_key=True,
        ),
        sa.Column("notification_email", sa.Text(), nullable=True),
        sa.Column("updated_by_account_id", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "lead_notification_outbox",
        sa.Column("outbox_id", sa.Text(), primary_key=True),
        sa.Column(
            "lead_id",
            sa.Text(),
            sa.ForeignKey("buyer_leads.lead_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("native_listing_id", sa.Text(), nullable=False),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column("buyer_name", sa.Text(), nullable=False),
        sa.Column("buyer_email", sa.Text(), nullable=False),
        sa.Column("contact_email_verification_state", sa.Text(), nullable=False),
        sa.Column("buyer_message_excerpt", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
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
    )
    op.create_index(
        "ix_lead_notification_outbox_status_next_attempt",
        "lead_notification_outbox",
        ["status", "next_attempt_at"],
    )

    op.create_table(
        "lead_notification_delivery_attempts",
        sa.Column("attempt_id", sa.Text(), primary_key=True),
        sa.Column(
            "outbox_id",
            sa.Text(),
            sa.ForeignKey("lead_notification_outbox.outbox_id"),
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
        "ix_lead_notification_delivery_attempts_outbox_id",
        "lead_notification_delivery_attempts",
        ["outbox_id"],
    )

    op.create_table(
        "lead_acquisition_provenance",
        sa.Column(
            "lead_id",
            sa.Text(),
            sa.ForeignKey("buyer_leads.lead_id"),
            primary_key=True,
        ),
        sa.Column("acquisition_channel", sa.Text(), nullable=False, server_default="UNKNOWN"),
        sa.Column("utm_source", sa.Text(), nullable=True),
        sa.Column("utm_medium", sa.Text(), nullable=True),
        sa.Column("utm_campaign", sa.Text(), nullable=True),
        sa.Column("utm_term", sa.Text(), nullable=True),
        sa.Column("utm_content", sa.Text(), nullable=True),
        sa.Column("discovery_surface", sa.Text(), nullable=False, server_default="UNKNOWN"),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("lead_acquisition_provenance")
    op.drop_index(
        "ix_lead_notification_delivery_attempts_outbox_id",
        table_name="lead_notification_delivery_attempts",
    )
    op.drop_table("lead_notification_delivery_attempts")
    op.drop_index(
        "ix_lead_notification_outbox_status_next_attempt", table_name="lead_notification_outbox"
    )
    op.drop_table("lead_notification_outbox")
    op.drop_table("organization_lead_notification_config")
    op.drop_index(
        "ix_lead_timeline_events_lead_id_occurred_at", table_name="lead_timeline_events"
    )
    op.drop_table("lead_timeline_events")
    op.drop_table("lead_operational_state")
