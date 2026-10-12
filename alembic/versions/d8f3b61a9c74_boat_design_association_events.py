"""boat_design_association_events

Revision ID: d8f3b61a9c74
Revises: b6f3d9a0c452
Create Date: 2026-10-12 09:00:00.000000

SLICE-0082. Adds the smallest durable persistence for one broker-confirmed
first-time PhysicalBoat -> canonical BoatDesign association:

    physical_boats.boat_design_ref   -- already exists (SLICE-0046); this
                                         migration adds no column to it and
                                         no UPDATE path at the schema level
    boat_design_association_events   -- new immutable audit table, one row
                                         per confirmed association, ever

`UNIQUE (physical_boat_id)` on the new table is the schema-level expression
of the accepted "one confirmed association, ever" invariant: it is not a
revision history like `physical_boat_claim_revisions` (there is deliberately
no reassign/detach/replace path in SLICE-0082), so there is exactly one row
per linked PhysicalBoat, never superseded. The actual NULL -> non-NULL
transition on `physical_boats.boat_design_ref` itself remains the sole
current-truth column (`specs` Mechanical invariants: "physical_boats.
boat_design_ref ... remains sole current association truth"); this table is
evidence/provenance alongside it, inserted in the same transaction as that
transition, never instead of it.

`native_listing_id` records the exact NativeListing through which the
confirmation was performed -- immutable creation provenance, not a claim
that the NativeListing itself was mutated. `confirmation_method` is
constrained to the single SLICE-0082 value; a future second confirmation
method is an explicit schema change, not a silent widening.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8f3b61a9c74"
down_revision: str | None = "b6f3d9a0c452"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "boat_design_association_events",
        sa.Column("association_event_id", sa.Text(), primary_key=True),
        sa.Column(
            "physical_boat_id",
            sa.Text(),
            sa.ForeignKey("physical_boats.physical_boat_id"),
            nullable=False,
        ),
        sa.Column(
            "boat_design_ref",
            sa.Text(),
            sa.ForeignKey("canonical_boat_designs.id"),
            nullable=False,
        ),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            nullable=False,
        ),
        sa.Column("confirming_organization_id", sa.Text(), nullable=False),
        sa.Column(
            "recorded_by_account_id",
            sa.Text(),
            sa.ForeignKey("accounts.account_id"),
            nullable=False,
        ),
        sa.Column("confirmation_method", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "physical_boat_id", name="uq_boat_design_association_events_physical_boat_id"
        ),
        sa.CheckConstraint(
            "confirmation_method IN ('MANUAL_SELECTOR_CONFIRMATION')",
            name="ck_boat_design_association_events_confirmation_method",
        ),
    )


def downgrade() -> None:
    op.drop_table("boat_design_association_events")
