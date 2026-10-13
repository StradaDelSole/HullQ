"""import_snapshot_lineage

Revision ID: a71d4f8c2e93
Revises: f3a7c9e21b58
Create Date: 2026-10-12 15:00:00.000000

SLICE-0083 independent review amendment, Finding B. Replaces the racy
"check only previously CONFIRMED batches" snapshot-lineage read with one
atomic, uniquely-constrained claim:

    import_snapshot_lineages   -- owner_organization_id, import_source,
                                   file_sha256, established_by_batch_id,
                                   established_at

The composite primary key `(owner_organization_id, import_source)` is the
actual concurrency-safety mechanism (mirrors `import_source_mappings`'s
identical discipline from the primary implementation, and
`boat_design_association_events`' insert-once pattern): two concurrent
first-time snapshot confirms for the same Organization/ImportSource both
attempt `INSERT ... ON CONFLICT DO NOTHING`; the database allows exactly
one to durably "establish" the lineage (whichever digest wins), and the
loser's `SELECT ... FOR UPDATE` against the now-committed row -- blocked
behind the winner's insert lock until it commits -- reads the real
winning digest and compares, never racing a separate unlocked read of
`import_batches.status = 'CONFIRMED'` the way the original implementation
did.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a71d4f8c2e93"
down_revision: str | None = "f3a7c9e21b58"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_snapshot_lineages",
        sa.Column("owner_organization_id", sa.Text(), nullable=False),
        sa.Column("import_source", sa.Text(), nullable=False),
        sa.Column("file_sha256", sa.Text(), nullable=False),
        sa.Column(
            "established_by_batch_id",
            sa.Text(),
            sa.ForeignKey(
                "import_batches.import_batch_id",
                name="fk_import_snapshot_lineages_established_by_batch_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "established_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint(
            "owner_organization_id", "import_source", name="pk_import_snapshot_lineages"
        ),
    )


def downgrade() -> None:
    op.drop_table("import_snapshot_lineages")
