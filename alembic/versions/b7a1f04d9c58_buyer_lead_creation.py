"""buyer_lead_creation

Revision ID: b7a1f04d9c58
Revises: d4e8f2a71b93
Create Date: 2026-09-29 09:00:00.000000

SLICE-0070. Adds the minimum durable persistence for buyer contact / Lead
creation:

    buyer_leads -- one durable row per created Lead, keyed by a
                    server-minted `lead_id`, with the caller-supplied
                    `submission_operation_id` enforced UNIQUE for retry-safe
                    idempotent creation (`ON CONFLICT (submission_operation_id)
                    DO NOTHING`). `account_id` is nullable optional
                    attribution only (contract §3). `received_at` carries a
                    server-side `NOW()` default so a caller can never
                    backdate/future-date a Lead. `envelope_content_hash`
                    fingerprints exactly the caller-controlled immutable
                    envelope (NativeListingId + publishing
                    MarketplaceOrganizationId + optional AccountId + buyer
                    name/email/message) -- never `received_at` -- so an exact
                    retry of the same `submission_operation_id` can be
                    distinguished from a conflicting reuse without a second
                    query (mirrors the SLICE-0043/SLICE-0052 fingerprint
                    discipline).

`contact_email_verification_state` is always `'UNVERIFIED'` in v0.1
(contract §7); this migration adds no token/delivery/verification-evidence
table -- that remains a mandatory later capability.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7a1f04d9c58"
down_revision: str | None = "d4e8f2a71b93"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "buyer_leads",
        sa.Column("lead_id", sa.Text(), primary_key=True),
        sa.Column("submission_operation_id", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            nullable=False,
        ),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=True),
        sa.Column("buyer_name", sa.Text(), nullable=False),
        sa.Column("buyer_email", sa.Text(), nullable=False),
        sa.Column("contact_email_verification_state", sa.Text(), nullable=False),
        sa.Column("buyer_message", sa.Text(), nullable=False),
        sa.Column("source_channel", sa.Text(), nullable=False),
        sa.Column("envelope_content_hash", sa.Text(), nullable=False),
        sa.Column(
            "received_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_buyer_leads_native_listing_id", "buyer_leads", ["native_listing_id"])


def downgrade() -> None:
    op.drop_index("ix_buyer_leads_native_listing_id", table_name="buyer_leads")
    op.drop_table("buyer_leads")
