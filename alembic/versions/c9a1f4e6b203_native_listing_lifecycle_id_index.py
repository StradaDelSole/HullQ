"""native_listing_lifecycle_id_index

Revision ID: c9a1f4e6b203
Revises: b4f8e2a6c105
Create Date: 2026-10-29 09:00:00.000000

SLICE-0096. Adds the one supporting B-tree index the new bounded public
Search candidate page read (`hullq.persistence.inventory_search
.list_active_native_listing_candidates_page`) requires:

    (lifecycle_state, native_listing_id)

The existing SLICE-0049 `lifecycle_state` column (8b6d3f0a2c17) has no index
of its own; the only existing index touching `native_listing_id` ordering is
SLICE-0060's `(publishing_organization_id, created_at DESC, native_listing_id)`
(f1a9c02d5e83), which cannot serve a global
`WHERE lifecycle_state = 'ACTIVE' AND native_listing_id > :cursor
ORDER BY native_listing_id LIMIT :n` keyset scan across every publishing
Organization. Without this index that bounded query would still need to
walk the primary-key order filtering `lifecycle_state` row by row (or a full
sequential scan), reintroducing exactly the unbounded-cost risk the new
bounded page path exists to remove. This index is performance/access-path
infrastructure only: it adds no column, no constraint and changes no
listing truth, lifecycle or identity semantics -- the existing unbounded
`list_active_design_linked_listings`/`list_active_design_unresolved_listings`
queries (SLICE-0051/0092) are read-compatible with it unchanged and are not
otherwise modified by this migration.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a1f4e6b203"
down_revision: str | None = "b4f8e2a6c105"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_native_listings_lifecycle_state_id",
        "native_listings",
        ["lifecycle_state", "native_listing_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_native_listings_lifecycle_state_id", table_name="native_listings")
