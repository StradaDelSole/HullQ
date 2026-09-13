"""native_listing_freshness

Revision ID: 7d4b1a9e3f26
Revises: 630ac7da649e
Create Date: 2026-09-13 09:00:00.000000

SLICE-0052. Adds the minimum durable persistence for NativeListing
freshness/reconfirmation evidence:

    native_listing_freshness_confirmations
                       -- one immutable, append-only row per successful
                          explicit reconfirmation event. Never updated or
                          deleted by application code. `occurred_at` carries
                          a server-side `NOW()` default so a caller can never
                          backdate or future-date a confirmation by supplying
                          an arbitrary timestamp (contract §4.2). The
                          `envelope_content_hash` column fingerprints exactly
                          the caller-controlled immutable envelope
                          (NativeListingId + actor AccountId + publishing
                          MarketplaceOrganizationId) -- never `occurred_at` --
                          so an exact retry of the same
                          `freshness_confirmation_id` can be distinguished
                          from a conflicting reuse without a second query.

This migration adds no lifecycle column/state and no scheduled job: freshness
is derived at read time from this table plus the existing SLICE-0049
`native_listing_publication_transitions` history (contract §4), never written
by time passing.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d4b1a9e3f26"
down_revision: str | None = "630ac7da649e"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_listing_freshness_confirmations",
        sa.Column("freshness_confirmation_id", sa.Text(), primary_key=True),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            nullable=False,
        ),
        sa.Column("actor_account_id", sa.Text(), nullable=False),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column("envelope_content_hash", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_nl_freshness_confirmations_native_listing_id",
        "native_listing_freshness_confirmations",
        ["native_listing_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nl_freshness_confirmations_native_listing_id",
        table_name="native_listing_freshness_confirmations",
    )
    op.drop_table("native_listing_freshness_confirmations")
