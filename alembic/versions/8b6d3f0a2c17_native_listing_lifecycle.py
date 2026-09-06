"""native_listing_lifecycle

Revision ID: 8b6d3f0a2c17
Revises: 4c9a0dcc98bb
Create Date: 2026-09-06 09:00:00.000000

SLICE-0049. Adds the minimum durable persistence for the first production
public NativeListing lifecycle:

    lifecycle_state    -- added column on the existing SLICE-0043
                          ``native_listings`` table; NOT NULL with a
                          'DRAFT' server default. PostgreSQL applies this
                          default to every pre-existing row as part of
                          adding the NOT NULL column, so every listing that
                          existed before this migration becomes DRAFT, and
                          the same server default means every listing
                          created after this migration -- through the
                          unmodified SLICE-0043 ``create_native_listing``
                          INSERT, which never references this column --
                          also begins DRAFT. No row is or can be made
                          ACTIVE by this migration.

    native_listing_publication_transitions
                       -- one immutable, append-only row per successful
                          lifecycle transition. Never updated or deleted by
                          application code. A CHECK constraint enumerates
                          exactly the two authorized transitions
                          (DRAFT -> ACTIVE, ACTIVE -> WITHDRAWN); no other
                          (from_state, to_state) pair -- including
                          WITHDRAWN -> ACTIVE republish -- can ever be
                          inserted.

``lifecycle_state`` is deliberately outside the accepted SLICE-0043
immutable creation envelope: it is not part of ``native_listings.content_hash``
and is never referenced by ``create_native_listing``'s idempotency/collision
SQL, so an exact retry of the original immutable creation request remains
ALREADY_EXISTS regardless of how lifecycle later changes.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b6d3f0a2c17"
down_revision: str | None = "4c9a0dcc98bb"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "native_listings",
        sa.Column(
            "lifecycle_state",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
    )
    op.create_check_constraint(
        "native_listings_lifecycle_state_valid",
        "native_listings",
        "lifecycle_state IN ('DRAFT', 'ACTIVE', 'WITHDRAWN')",
    )

    op.create_table(
        "native_listing_publication_transitions",
        sa.Column("publication_transition_id", sa.Text(), primary_key=True),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            nullable=False,
        ),
        sa.Column("from_state", sa.Text(), nullable=False),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("actor_account_id", sa.Text(), nullable=False),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "(from_state = 'DRAFT' AND to_state = 'ACTIVE') "
            "OR (from_state = 'ACTIVE' AND to_state = 'WITHDRAWN')",
            name="nl_publication_transitions_transition_valid",
        ),
    )
    op.create_index(
        "ix_nl_publication_transitions_native_listing_id",
        "native_listing_publication_transitions",
        ["native_listing_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nl_publication_transitions_native_listing_id",
        table_name="native_listing_publication_transitions",
    )
    op.drop_table("native_listing_publication_transitions")
    op.drop_constraint("native_listings_lifecycle_state_valid", "native_listings", type_="check")
    op.drop_column("native_listings", "lifecycle_state")
