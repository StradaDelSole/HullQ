"""owner_direct_listing_draft

Revision ID: e2f9a6d15c40
Revises: b3e7f1a94c02
Create Date: 2026-09-15 09:00:00.000000

SLICE-0054. Adds the single dedicated durable aggregate required by
`specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md` §5: one private,
mutable, pre-market owner-direct listing draft workspace per HullQ Account.

    owner_direct_listing_drafts   -- draft_id, owner_account_id, payload,
                                      version, created_at, updated_at

Per contract §5, `draft_id` is TEXT (matching the existing `AccountId`/
`MarketplaceOrganizationId`/`NativeListingId` wrapper convention: exact UUID
version is an implementation detail, not a schema-level choice) and
`owner_account_id` is a real foreign key into the SLICE-0053
`accounts` directory -- but deliberately the *only* foreign key this table
carries. Per contract §5/§2, this migration adds NO foreign key and NO
column at all referencing `native_listings`, `physical_boats` or
`market_episodes`: a draft is pre-market workspace state, not marketplace
inventory, and must remain structurally incapable of being joined into
those tables as if it already were.

`payload` is JSONB (contract §5: acceptable here only because the API/
domain validator in `hullq.domain.owner_direct_draft` enforces the finite
v0.1 key set and value shapes -- this is not a schemaless-blob license).
`version` is a plain positive integer, compared-and-incremented by one
atomic `UPDATE ... WHERE version = expected_version` statement in
`hullq.persistence.owner_direct_draft` (contract §7) -- no separate
locking/versioning table is needed for that.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f9a6d15c40"
down_revision: str | None = "b3e7f1a94c02"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owner_direct_listing_drafts",
        sa.Column("draft_id", sa.Text(), primary_key=True),
        sa.Column(
            "owner_account_id",
            sa.Text(),
            sa.ForeignKey(
                "accounts.account_id", name="fk_owner_direct_listing_drafts_owner_account_id"
            ),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
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
        sa.CheckConstraint("version > 0", name="ck_owner_direct_listing_drafts_version_positive"),
    )
    op.create_index(
        "ix_owner_direct_listing_drafts_owner_account_id",
        "owner_direct_listing_drafts",
        ["owner_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_owner_direct_listing_drafts_owner_account_id",
        table_name="owner_direct_listing_drafts",
    )
    op.drop_table("owner_direct_listing_drafts")
