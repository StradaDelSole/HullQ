"""native_listing_inventory_index

Revision ID: f1a9c02d5e83
Revises: e2f9a6d15c40
Create Date: 2026-09-20 09:00:00.000000

SLICE-0060. Adds the one supporting B-tree index the accepted Organization
inventory overview read (contract §13) requires:

    (publishing_organization_id, created_at DESC, native_listing_id ASC)

The existing SLICE-0043 `native_listings` table has no index on
`publishing_organization_id` at all, so an Organization-scoped, deterministic
`created_at DESC, native_listing_id ASC` keyset read would otherwise require
a full-table scan + sort. This index is performance/access-path
infrastructure only: it adds no column, no constraint and changes no listing
truth, lifecycle, ownership or identity semantics.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a9c02d5e83"
down_revision: str | None = "e2f9a6d15c40"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_native_listings_org_created_id",
        "native_listings",
        ["publishing_organization_id", sa.text("created_at DESC"), "native_listing_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_native_listings_org_created_id", table_name="native_listings")
