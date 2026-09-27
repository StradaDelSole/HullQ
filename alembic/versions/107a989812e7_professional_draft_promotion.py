"""professional_draft_promotion

Revision ID: 107a989812e7
Revises: c58f2a1d9e64
Create Date: 2026-09-27 09:00:00.000000

SLICE-0067. Adds the two durable schema gaps required by
`specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md` §5/§11:

1. ``professional_listing_drafts`` gains the promotion state/provenance
   triple: ``promotion_state`` (``EDITABLE`` | ``PROMOTED``, NOT NULL,
   server default ``'EDITABLE'`` so every existing row migrates to
   EDITABLE), ``promoted_native_listing_id`` (nullable FK into
   ``native_listings.native_listing_id``) and ``promoted_at`` (nullable
   TIMESTAMPTZ). A CHECK constraint enumerates exactly the two valid
   nullability pairings (contract §5): EDITABLE always pairs with both
   provenance columns NULL, PROMOTED always pairs with both non-NULL --
   mirrors the existing ``pb_claim_rev_boat_name_state_valid``
   COALESCE(...,FALSE)-per-branch pattern (see
   ``c58f2a1d9e64``'s docstring) so SQL's NULL-propagating three-valued
   logic can never silently accept a mismatched pairing. A partial unique
   index on ``promoted_native_listing_id`` (``WHERE ... IS NOT NULL``)
   enforces "one promoted NativeListingId may be linked from at most one
   ProfessionalListingDraft" without constraining the many rows that are
   still EDITABLE (NULL).

2. ``native_listings`` gains the accepted D09 resolved-episode uniqueness
   boundary: ``UNIQUE (publishing_organization_id, market_episode_id) WHERE
   market_episode_id IS NOT NULL``. Different Organizations may still
   reference the same resolved MarketEpisode; only the same Organization
   holding two NativeListings for the same resolved MarketEpisode is
   rejected. Because this is a plain ``CREATE UNIQUE INDEX`` (not
   ``CONCURRENTLY``), PostgreSQL validates every existing row as part of
   creating the index and the migration itself fails closed if any
   historical duplicate already violates it -- this migration never
   deletes, relinks or merges a pre-existing row to make the index buildable.
   Multiple NativeListings with a NULL ``market_episode_id`` remain
   unaffected (the partial predicate excludes them entirely).
   ``broker_listing_reference`` does not participate in this index at all.

Both promotion-state columns are added without a ``server_default`` other
than the fixed ``'EDITABLE'`` state (and NULL for the two provenance
columns), so no existing row is backfilled with a synthesized promotion
result.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "107a989812e7"
down_revision: str | None = "c58f2a1d9e64"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "professional_listing_drafts",
        sa.Column(
            "promotion_state",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'EDITABLE'"),
        ),
    )
    op.add_column(
        "professional_listing_drafts",
        sa.Column(
            "promoted_native_listing_id",
            sa.Text(),
            sa.ForeignKey(
                "native_listings.native_listing_id",
                name="fk_professional_listing_drafts_promoted_native_listing_id",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "professional_listing_drafts",
        sa.Column("promoted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_professional_listing_drafts_promotion_state_valid",
        "professional_listing_drafts",
        "promotion_state IN ('EDITABLE', 'PROMOTED')",
    )
    op.create_check_constraint(
        "ck_professional_listing_drafts_promotion_pairing",
        "professional_listing_drafts",
        "COALESCE(promotion_state = 'EDITABLE' "
        "    AND promoted_native_listing_id IS NULL AND promoted_at IS NULL, FALSE) "
        "OR COALESCE(promotion_state = 'PROMOTED' "
        "    AND promoted_native_listing_id IS NOT NULL AND promoted_at IS NOT NULL, FALSE)",
    )
    op.create_index(
        "ux_professional_listing_drafts_promoted_native_listing_id",
        "professional_listing_drafts",
        ["promoted_native_listing_id"],
        unique=True,
        postgresql_where=sa.text("promoted_native_listing_id IS NOT NULL"),
    )

    # SLICE-0067 D09: validates all existing rows as part of index creation
    # (no NOT VALID / CONCURRENTLY clause) -- a pre-existing historical
    # duplicate fails this statement, and the migration, closed.
    op.create_index(
        "ux_native_listings_org_episode",
        "native_listings",
        ["publishing_organization_id", "market_episode_id"],
        unique=True,
        postgresql_where=sa.text("market_episode_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_native_listings_org_episode", table_name="native_listings")
    op.drop_index(
        "ux_professional_listing_drafts_promoted_native_listing_id",
        table_name="professional_listing_drafts",
    )
    op.drop_constraint(
        "ck_professional_listing_drafts_promotion_pairing",
        "professional_listing_drafts",
        type_="check",
    )
    op.drop_constraint(
        "ck_professional_listing_drafts_promotion_state_valid",
        "professional_listing_drafts",
        type_="check",
    )
    op.drop_column("professional_listing_drafts", "promoted_at")
    op.drop_column("professional_listing_drafts", "promoted_native_listing_id")
    op.drop_column("professional_listing_drafts", "promotion_state")
