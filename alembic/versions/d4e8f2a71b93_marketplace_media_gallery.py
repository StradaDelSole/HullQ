"""marketplace_media_gallery

Revision ID: d4e8f2a71b93
Revises: 107a989812e7
Create Date: 2026-09-27 09:00:00.000000

SLICE-0068. Implements `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md`
§2/§6/§7/§8/§9/§10/§12: the durable MediaAsset/MediaPlacement truth for an
Organization-controlled mixed-media (IMAGE + YOUTUBE) NativeListing gallery.

    media_assets                 -- one Organization-controlled uploaded
                                     IMAGE, already in a terminal processing
                                     state (see module docstring of
                                     `hullq.domain.media_gallery`: this
                                     implementation processes uploads
                                     synchronously, so a row is only ever
                                     durably created APPROVED or REJECTED --
                                     never a persisted intermediate state)
    media_placements              -- one listing-specific placement of a
                                      MediaAsset (IMAGE) or a normalized
                                      YouTube reference (YOUTUBE), with
                                      explicit per-listing ordering
    native_listing_media_state    -- one gallery "head" row per NativeListing:
                                      the optimistic-concurrency version used
                                      by reorder/cover/removal mutations
                                      (contract §8/§16) and the single
                                      explicit cover pointer (contract §8:
                                      "exactly zero or one placement is the
                                      explicit cover at any instant" -- a
                                      single nullable FK column makes that
                                      invariant true by construction rather
                                      than requiring a partial-unique-index
                                      workaround)

Every table adds NO column/FK to `professional_listing_drafts`: media
attaches only to an already-existing `native_listings` row (contract §2:
"Media attaches only to an existing marketplace NativeListing, never to
ProfessionalListingDraft").

`media_assets.processing_state`/`rights_state` and `media_placements.kind`
follow the existing plain-TEXT-plus-CHECK-constraint convention used
throughout this schema (e.g. `professional_listing_drafts.promotion_state`)
rather than a native Postgres ENUM type. The `ck_media_assets_state_shape`
constraint mechanically ties every nullable derivative-metadata column
(`derivative_object_key`, `content_hash`, `mime_type`, `width`, `height`,
`byte_size`) to `processing_state = 'APPROVED'` and `rejection_reason` to
`'REJECTED'` alone -- contract §7's "no intermediate/failure state can be
mistaken for APPROVED" is therefore enforced by PostgreSQL itself, not only
by application code. `ck_media_placements_kind_shape` gives the equivalent
guarantee for `media_asset_id` XOR `youtube_video_id`/`youtube_source_url`
(contract §4).

Independent review amendment (Finding A): `original_object_key` and
`derivative_object_key` are two distinct, independently-purgeable object-
storage keys, not one key doing double duty. `original_object_key` is
`NOT NULL` on every row -- both APPROVED and REJECTED -- because contract
§6 frames "begins non-public in private/quarantined object storage" as the
very first step of ingestion, before an accept/reject decision exists; a
row is only ever durably inserted at all after that private original is
already durably stored (contract §16: a storage failure at that point
leaves zero database trace to roll back). `derivative_object_key` remains
nullable, tied to `processing_state = 'APPROVED'` exactly like the other
derivative-metadata columns: a REJECTED asset's original stays quarantined
forever and is never promoted to a public derivative. Neither this
migration nor any route ever serves `original_object_key`'s bytes -- only
`hullq.persistence.media_gallery`/`hullq.application.media_gallery`
reference the column at all, and only for future D24 independent-lifecycle
bookkeeping.

Independent review amendment (Finding B): `source_kind` +
`source_reference` are the accepted D14 bounded provenance model.
`source_kind` is a finite CHECK-constrained classification (`'BROKER_UPLOAD'`
is the only v0.1 value: an authorized publisher uploaded this directly
through HullQ) -- not a broad rights-management system. `source_reference`
is an optional bounded broker-supplied free-text note (length-bounded at
the application layer, `hullq.domain.media_gallery.MAX_SOURCE_REFERENCE_
LENGTH`), kept a clearly separate column from `source_kind` so a note can
never be mistaken for the authoritative structured classification. Both
live on `media_assets`, never `media_placements`, so they survive contract
§9 same-Organization reuse onto another listing exactly like
`uploaded_by_account_id`/`rights_state` already do.

`uq_media_placements_listing_position` is `DEFERRABLE INITIALLY DEFERRED`:
a reorder mutation writes every affected placement's new `position` inside
one transaction, and a straight per-row `UPDATE` sequence can transiently
collide on position values mid-transaction even though the final state is a
valid permutation -- deferring the uniqueness check to `COMMIT` avoids
needing a separate temporary-offset dance while still ultimately enforcing
"deterministic explicit ordering" (contract §8) as a real database
invariant, not merely an application-level convention.

`native_listing_media_state.cover_placement_id` is `ON DELETE SET NULL`:
hard-deleting a `media_placements` row (contract §12: "placement removal !=
asset deletion") that happens to be the current cover automatically clears
the head row's cover pointer rather than leaving a dangling reference --
contract §8's "must not leave a phantom cover reference" is therefore also a
real foreign-key-driven guarantee, not only an application-level discipline.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8f2a71b93"
down_revision: str | None = "107a989812e7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("media_asset_id", sa.Text(), primary_key=True),
        sa.Column(
            "owner_organization_id",
            sa.Text(),
            sa.ForeignKey(
                "marketplace_organizations.organization_id",
                name="fk_media_assets_owner_organization_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_account_id",
            sa.Text(),
            sa.ForeignKey("accounts.account_id", name="fk_media_assets_uploaded_by_account_id"),
            nullable=False,
        ),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("processing_state", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("rights_state", sa.Text(), nullable=False),
        sa.Column("original_object_key", sa.Text(), nullable=False),
        sa.Column("derivative_object_key", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("retired_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "source_kind IN ('BROKER_UPLOAD')", name="ck_media_assets_source_kind_valid"
        ),
        sa.CheckConstraint(
            "processing_state IN ('APPROVED', 'REJECTED')",
            name="ck_media_assets_processing_state_valid",
        ),
        sa.CheckConstraint(
            "rights_state IN ('UNKNOWN', 'DECLARED')", name="ck_media_assets_rights_state_valid"
        ),
        sa.CheckConstraint(
            "(processing_state = 'APPROVED' AND derivative_object_key IS NOT NULL "
            " AND content_hash IS NOT NULL AND mime_type IS NOT NULL "
            " AND width IS NOT NULL AND height IS NOT NULL AND byte_size IS NOT NULL "
            " AND rejection_reason IS NULL)"
            " OR "
            "(processing_state = 'REJECTED' AND derivative_object_key IS NULL "
            " AND content_hash IS NULL AND mime_type IS NULL AND width IS NULL "
            " AND height IS NULL AND byte_size IS NULL AND rejection_reason IS NOT NULL)",
            name="ck_media_assets_state_shape",
        ),
    )
    op.create_index(
        "ix_media_assets_org_state", "media_assets", ["owner_organization_id", "processing_state"]
    )

    op.create_table(
        "media_placements",
        sa.Column("media_placement_id", sa.Text(), primary_key=True),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey(
                "native_listings.native_listing_id", name="fk_media_placements_native_listing_id"
            ),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "media_asset_id",
            sa.Text(),
            sa.ForeignKey("media_assets.media_asset_id", name="fk_media_placements_media_asset_id"),
            nullable=True,
        ),
        sa.Column("youtube_video_id", sa.Text(), nullable=True),
        sa.Column("youtube_source_url", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_by_account_id",
            sa.Text(),
            sa.ForeignKey("accounts.account_id", name="fk_media_placements_created_by_account_id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("kind IN ('IMAGE', 'YOUTUBE')", name="ck_media_placements_kind_valid"),
        sa.CheckConstraint(
            "(kind = 'IMAGE' AND media_asset_id IS NOT NULL AND youtube_video_id IS NULL "
            " AND youtube_source_url IS NULL)"
            " OR "
            "(kind = 'YOUTUBE' AND youtube_video_id IS NOT NULL AND media_asset_id IS NULL)",
            name="ck_media_placements_kind_shape",
        ),
        sa.UniqueConstraint(
            "native_listing_id",
            "position",
            name="uq_media_placements_listing_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_media_placements_asset", "media_placements", ["media_asset_id"])

    op.create_table(
        "native_listing_media_state",
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey(
                "native_listings.native_listing_id",
                name="fk_native_listing_media_state_native_listing_id",
            ),
            primary_key=True,
        ),
        sa.Column("gallery_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "cover_placement_id",
            sa.Text(),
            sa.ForeignKey(
                "media_placements.media_placement_id",
                name="fk_native_listing_media_state_cover_placement_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "gallery_version >= 0", name="ck_native_listing_media_state_version_nonnegative"
        ),
    )


def downgrade() -> None:
    op.drop_table("native_listing_media_state")
    op.drop_index("ix_media_placements_asset", table_name="media_placements")
    op.drop_table("media_placements")
    op.drop_index("ix_media_assets_org_state", table_name="media_assets")
    op.drop_table("media_assets")
