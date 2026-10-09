"""media_asset_backup_redundancy

Revision ID: b6f3d9a0c452
Revises: a2e7c0f5b931
Create Date: 2026-10-09 09:00:00.000000

SLICE-0080. Implements `specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md`
§3/§4/§11: durable PostgreSQL truth distinguishing legacy/pre-SLICE-0080
`media_assets` rows (independent original copy not established/known) from
post-SLICE-0080 rows whose independent Backblaze B2 original copy was
confirmed established before this row's database truth committed.

Three new nullable columns, added with no data backfill:

    backup_provider        -- operational recovery metadata only (contract
                               §3: "MUST NOT participate in MediaAsset
                               identity"); the only v0.1 value is
                               'BACKBLAZE_B2' (`hullq.domain.media_gallery.
                               MediaBackupProviderKind`)
    backup_object_key      -- the opaque key locating the established
                               independent copy; never a provider URL
    backup_established_at  -- set only at the exact moment this row's
                               database truth committed with both the
                               primary R2 original write and the
                               independent B2 original write already
                               confirmed successful (contract §5's
                               synchronous establishment invariant)

Every pre-existing row's three new columns default to `NULL` on this
migration -- contract §3: "Existing rows MUST migrate without fabricating
backup success. They remain explicitly unverified/not-established". No
`UPDATE` statement ever runs against a pre-existing row here; `NULL` *is*
the honest "not established/unknown" state, not a sentinel requiring a
separate flag.

`ck_media_assets_backup_shape` makes contract §3's "mechanically impossible
for a row to claim an established B2 copy while lacking the durable backup
object reference/provider role required to locate it" a real database
invariant, not only an application-level convention: all three columns are
`NULL` together (not established) or all three are `NOT NULL` together
(established with a locator) -- no partial/impossible shape is representable
at all, in either direction. `ck_media_assets_backup_provider_valid` bounds
`backup_provider` to the finite v0.1 token vocabulary, mirroring this
table's existing `source_kind`/`processing_state`/`rights_state` TEXT-plus-
CHECK-constraint convention (see the owning `d4e8f2a71b93` migration's
docstring) rather than a native Postgres ENUM type.

These columns apply uniformly to both `APPROVED` and `REJECTED` rows
(contract §5: "This applies to both APPROVED and retained REJECTED
MediaAssets because both retain the broker's original/quarantine bytes") --
deliberately orthogonal to `ck_media_assets_state_shape`'s existing
APPROVED/REJECTED derivative-metadata shape constraint, never merged into it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6f3d9a0c452"
down_revision: str | None = "a2e7c0f5b931"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("media_assets", sa.Column("backup_provider", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("backup_object_key", sa.Text(), nullable=True))
    op.add_column(
        "media_assets",
        sa.Column("backup_established_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_media_assets_backup_provider_valid",
        "media_assets",
        "backup_provider IS NULL OR backup_provider IN ('BACKBLAZE_B2')",
    )
    op.create_check_constraint(
        "ck_media_assets_backup_shape",
        "media_assets",
        "(backup_provider IS NULL AND backup_object_key IS NULL "
        " AND backup_established_at IS NULL)"
        " OR "
        "(backup_provider IS NOT NULL AND backup_object_key IS NOT NULL "
        " AND backup_established_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_media_assets_backup_shape", "media_assets", type_="check")
    op.drop_constraint("ck_media_assets_backup_provider_valid", "media_assets", type_="check")
    op.drop_column("media_assets", "backup_established_at")
    op.drop_column("media_assets", "backup_object_key")
    op.drop_column("media_assets", "backup_provider")
