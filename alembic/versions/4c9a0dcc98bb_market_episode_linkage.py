"""market_episode_linkage

Revision ID: 4c9a0dcc98bb
Revises: 7a3f0e5c1b6d
Create Date: 2026-09-05 12:30:00.000000

SLICE-0047. Adds the smallest durable persistence for the missing identity/
linkage segment between an accepted durable `PhysicalBoat` and an accepted
durable `NativeListing`:

    market_episode_id   -- caller-supplied, durable primary identity
    physical_boat_id     -- required FK into the existing physical_boats(physical_boat_id)
                            authority; a MarketEpisode always identifies one
                            sale/market episode for exactly one PhysicalBoat
    created_at           -- server-generated

There is deliberately no uniqueness constraint on `physical_boat_id`: many
distinct MarketEpisodeIds may reference one PhysicalBoatId (a later sale
episode for the same yacht is not an identity conflict). This migration adds
no lifecycle/status/freshness/seller/price/observation/continuity/dedup
column -- those remain out of scope for this slice.

This migration also completes the previously-nullable, previously-unenforced
`native_listings.market_episode_id` creation-envelope column with a real
foreign key into `market_episodes(market_episode_id)`. NULL remains valid
(unresolved linkage). No cascade-delete behavior is introduced on either FK.

A pre-0047 database may contain a non-null `native_listings.market_episode_id`
value that was written by SLICE-0043 before any durable MarketEpisode
authority existed. There is no truthful PhysicalBoat mapping from which this
migration could reconstruct such an episode, so it deliberately does not
attempt to. PostgreSQL's `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY`
validates all existing rows by default (this migration never uses `NOT
VALID`): if any such pre-existing non-null value would be orphaned by the
new FK, the ADD CONSTRAINT statement itself raises `ForeignKeyViolation` and
the whole migration transaction rolls back -- upgrade fails closed rather
than fabricating a MarketEpisode, silently nulling the value, or rewriting
the immutable NativeListing envelope.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c9a0dcc98bb"
down_revision: str | None = "7a3f0e5c1b6d"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_episodes",
        sa.Column("market_episode_id", sa.Text(), primary_key=True),
        sa.Column(
            "physical_boat_id",
            sa.Text(),
            sa.ForeignKey(
                "physical_boats.physical_boat_id", name="fk_market_episodes_physical_boat_id"
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Validates existing native_listings.market_episode_id data by default
    # (no NOT VALID clause): an orphaned pre-existing non-null value fails
    # this statement, and the migration, closed.
    op.create_foreign_key(
        "fk_native_listings_market_episode_id",
        "native_listings",
        "market_episodes",
        ["market_episode_id"],
        ["market_episode_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_native_listings_market_episode_id", "native_listings", type_="foreignkey"
    )
    op.drop_table("market_episodes")
