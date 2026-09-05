"""physical_boat_identity

Revision ID: 7a3f0e5c1b6d
Revises: 4d8e1a72c9f0
Create Date: 2026-09-05 12:00:00.000000

SLICE-0046. Adds the smallest durable persistence for one real-yacht
PhysicalBoat identity, distinct from BoatDesign/MarketEpisode/NativeListing
identity:

    physical_boat_id  -- caller-supplied, durable primary identity
    boat_design_ref    -- optional FK into the existing canonical_boat_designs(id)
                          authority; NULL means unresolved design identity,
                          not design absence
    created_at         -- server-generated

There is deliberately no uniqueness constraint on ``boat_design_ref``: many
PhysicalBoatIds may reference one BoatDesign (sister ships), and this table
must never deduplicate/merge real-yacht identities because they share a
design. There is also deliberately no UPDATE path for ``boat_design_ref`` in
this slice -- creation is immutable, and an existing PhysicalBoatId's stored
design reference is never silently mutated by later application code.

This migration adds no MarketEpisode/NativeListing attachment column, no
Organization/account ownership column and none of the 29 SLICE-0044
`PHYSICAL_BOAT` marketplace fact fields -- those remain out of scope for
this slice.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a3f0e5c1b6d"
down_revision: str | None = "4d8e1a72c9f0"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "physical_boats",
        sa.Column("physical_boat_id", sa.Text(), primary_key=True),
        sa.Column(
            "boat_design_ref",
            sa.Text(),
            sa.ForeignKey("canonical_boat_designs.id", name="fk_physical_boats_boat_design_ref"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("physical_boats")
