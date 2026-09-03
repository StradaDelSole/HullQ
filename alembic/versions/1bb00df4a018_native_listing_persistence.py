"""native_listing_persistence

Revision ID: 1bb00df4a018
Revises: 6f1c2a9d0001
Create Date: 2026-09-03 17:59:13.455760

SLICE-0043. Adds the smallest durable NativeListing creation-envelope table
required by the accepted NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1: HullQ's
first marketplace application table, added directly on top of the SLICE-0042
Alembic baseline.

This is an immutable creation envelope only — no lifecycle/status column, no
FK to an actor/MarketEpisode table (neither exists yet), and no full listing
field catalog. ``content_hash`` is internal persistence evidence used for
idempotency/conflict detection, not a broker-facing listing field; it is
always a lowercase SHA-256 hex digest (64 characters), matching
``hullq.persistence.fingerprint.fingerprint_dict``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1bb00df4a018"
down_revision: str | None = "6f1c2a9d0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_listings",
        sa.Column("native_listing_id", sa.Text(), primary_key=True),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column("created_by_account_id", sa.Text(), nullable=False),
        sa.Column("market_episode_id", sa.Text(), nullable=True),
        sa.Column("broker_listing_reference", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="native_listings_content_hash_sha256_length"
        ),
        sa.CheckConstraint(
            "broker_listing_reference IS NULL OR length(btrim(broker_listing_reference)) > 0",
            name="native_listings_broker_listing_reference_non_blank",
        ),
    )


def downgrade() -> None:
    op.drop_table("native_listings")
