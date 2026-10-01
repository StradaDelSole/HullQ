"""native_listing_view_event

Revision ID: a2e7c0f5b931
Revises: f3a8c71d9e02
Create Date: 2026-10-01 10:00:00.000000

SLICE-0075. Adds the smallest durable persistence for one accepted public
listing telemetry fact (`specs/BROKER_PERFORMANCE_FUNNEL_SNAPSHOT_CONTRACT.v0.1.md`
§5):

    native_listing_view_events -- one durable row per recorded
        `PUBLIC_LISTING_VIEW` operation, keyed by a server-minted
        `operation_id` enforced UNIQUE for retry-safe idempotent recording
        (`ON CONFLICT (operation_id) DO NOTHING`). `payload_fingerprint`
        fingerprints exactly the caller-controlled
        `(native_listing_id, publishing_organization_id)` payload -- never
        `occurred_at` -- so an exact retry of the same `operation_id` can be
        distinguished from a conflicting reuse (mirrors the SLICE-0070
        `buyer_leads.envelope_content_hash` discipline). `occurred_at`
        carries a server-side `NOW()` default so a caller can never backdate/
        future-date a view. No raw IP, browser fingerprint, referrer URL or
        query-string field is ever persisted here (contract §4).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2e7c0f5b931"
down_revision: str | None = "f3a8c71d9e02"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_listing_view_events",
        sa.Column("operation_id", sa.Text(), primary_key=True),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            nullable=False,
        ),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column("event_kind", sa.Text(), nullable=False),
        sa.Column("payload_fingerprint", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "event_kind IN ('PUBLIC_LISTING_VIEW')",
            name="nl_view_event_kind_valid",
        ),
    )
    op.create_index(
        "ix_nl_view_events_native_listing_id_occurred_at",
        "native_listing_view_events",
        ["native_listing_id", "occurred_at"],
    )
    op.create_index(
        "ix_nl_view_events_org_id_occurred_at",
        "native_listing_view_events",
        ["publishing_organization_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_nl_view_events_org_id_occurred_at", table_name="native_listing_view_events")
    op.drop_index(
        "ix_nl_view_events_native_listing_id_occurred_at",
        table_name="native_listing_view_events",
    )
    op.drop_table("native_listing_view_events")
