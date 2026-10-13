"""multiformat_import_intake

Revision ID: f3a7c9e21b58
Revises: d8f3b61a9c74
Create Date: 2026-10-12 11:00:00.000000

SLICE-0083. Adds the D26 durable staged-import aggregate
(`docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D26):

    import_batches            -- one uploaded file's bounded staging state
    import_rows                -- one staged row per batch, 1:many
    import_source_mappings     -- the durable, unique (Organization,
                                   ImportSource, SourceRecordKey) ->
                                   ProfessionalListingDraftId identity map

`import_source_mappings`'s composite primary key IS the D26 "durable unique
Organization/source/sourcekey constraint" (mechanical invariants): once one
row exists for a given `(owner_organization_id, import_source,
source_record_key)`, no second row for that exact key can ever be
inserted -- a later confirm attempt for the same key can only read this row
back (ALREADY_IMPORTED, if its `row_digest` still matches) or refuse to
mutate it (CONFLICT_REVIEW, if the digest differs). This table has
deliberately no `UPDATE` path in the application layer: it is populated by
exactly one atomic insert per key, ever, mirroring the same
insert-once/no-reassign discipline `boat_design_association_events`
established for SLICE-0082.

Both new tables carry a real foreign key to `professional_listing_drafts`
only on `import_rows.created_professional_listing_draft_id` /
`import_source_mappings.professional_listing_draft_id` -- never to
`native_listings`/`physical_boats`/`market_episodes`: an import batch/row
is pre-draft staging state plus a pointer to the one private draft it
produced, structurally incapable of being joined as if it already were
published marketplace inventory (same discipline
`a05c7e9b1f34_professional_listing_draft` established for the draft table
itself).

`import_rows.raw_fields`/`draft_request_wire` are JSONB because they carry
per-format-variable staged content; `hullq.domain.import_intake` enforces
the finite, bounded key/value shapes before anything is written here --
this is not a schemaless-blob license, mirroring the accepted
`professional_listing_drafts.payload` design.

`import_batches.staged_table` holds the already-bounded (`MAX_IMPORT_ROWS`
x `MAX_IMPORT_COLUMNS` x `MAX_IMPORT_CELL_CHARS`) parsed `headers`/`rows`
for a column-mapped format (CSV/TSV/Excel/JSON) between upload and the
explicit mapping step -- never the original uploaded bytes themselves
(mechanical invariants: "do not persist arbitrary unbounded original
uploaded spreadsheets"). It is cleared back to `NULL` once mapping is
applied and `import_rows` becomes the authoritative per-row state; NautiX
(no separate mapping step) never populates it at all.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a7c9e21b58"
down_revision: str | None = "d8f3b61a9c74"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("import_batch_id", sa.Text(), primary_key=True),
        sa.Column(
            "owner_organization_id",
            sa.Text(),
            sa.ForeignKey(
                "marketplace_organizations.organization_id",
                name="fk_import_batches_owner_organization_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_by_account_id",
            sa.Text(),
            sa.ForeignKey("accounts.account_id", name="fk_import_batches_created_by_account_id"),
            nullable=False,
        ),
        sa.Column("import_format", sa.Text(), nullable=False),
        sa.Column("import_source", sa.Text(), nullable=False),
        sa.Column("worksheet_name", sa.Text(), nullable=True),
        sa.Column("snapshot_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("file_sha256", sa.Text(), nullable=False),
        sa.Column("file_byte_size", sa.Integer(), nullable=False),
        sa.Column("column_mapping", postgresql.JSONB(), nullable=True),
        sa.Column("staged_table", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("mapped_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            "import_format IN ('CSV','TSV','XLSX','XLS','XLSB','ODS','JSON','NAUTIX_XML')",
            name="ck_import_batches_import_format",
        ),
        sa.CheckConstraint(
            "status IN ('AWAITING_MAPPING','MAPPED','CONFIRMING','CONFIRMED','EXPIRED')",
            name="ck_import_batches_status",
        ),
        sa.CheckConstraint("file_byte_size >= 0", name="ck_import_batches_file_byte_size"),
        sa.CheckConstraint("row_count >= 0", name="ck_import_batches_row_count"),
    )
    op.create_index(
        "ix_import_batches_org_created",
        "import_batches",
        ["owner_organization_id", sa.text("created_at DESC"), "import_batch_id"],
    )

    op.create_table(
        "import_rows",
        sa.Column("import_row_id", sa.Text(), primary_key=True),
        sa.Column(
            "import_batch_id",
            sa.Text(),
            sa.ForeignKey("import_batches.import_batch_id", name="fk_import_rows_import_batch_id"),
            nullable=False,
        ),
        sa.Column("row_ordinal", sa.Integer(), nullable=False),
        sa.Column("raw_fields", postgresql.JSONB(), nullable=False),
        sa.Column(
            "unmapped_headers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("preview_classification", sa.Text(), nullable=False),
        sa.Column(
            "preview_reasons",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("source_record_key", sa.Text(), nullable=True),
        sa.Column("draft_request_wire", postgresql.JSONB(), nullable=True),
        sa.Column("row_digest", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column(
            "created_professional_listing_draft_id",
            sa.Text(),
            sa.ForeignKey(
                "professional_listing_drafts.professional_listing_draft_id",
                name="fk_import_rows_created_professional_listing_draft_id",
            ),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "preview_classification IN ('VALID','INVALID','CONFLICT_REVIEW')",
            name="ck_import_rows_preview_classification",
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN "
            "('CREATE_NEW_DRAFT','ALREADY_IMPORTED','CONFLICT_REVIEW','INVALID')",
            name="ck_import_rows_outcome",
        ),
        sa.UniqueConstraint("import_batch_id", "row_ordinal", name="uq_import_rows_batch_ordinal"),
    )
    op.create_index("ix_import_rows_batch_id", "import_rows", ["import_batch_id"])

    op.create_table(
        "import_source_mappings",
        sa.Column("owner_organization_id", sa.Text(), nullable=False),
        sa.Column("import_source", sa.Text(), nullable=False),
        sa.Column("source_record_key", sa.Text(), nullable=False),
        sa.Column("row_digest", sa.Text(), nullable=False),
        sa.Column(
            "professional_listing_draft_id",
            sa.Text(),
            sa.ForeignKey(
                "professional_listing_drafts.professional_listing_draft_id",
                name="fk_import_source_mappings_professional_listing_draft_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_by_import_batch_id",
            sa.Text(),
            sa.ForeignKey(
                "import_batches.import_batch_id",
                name="fk_import_source_mappings_created_by_import_batch_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint(
            "owner_organization_id",
            "import_source",
            "source_record_key",
            name="pk_import_source_mappings",
        ),
    )
    op.create_index(
        "ix_import_source_mappings_draft_id",
        "import_source_mappings",
        ["professional_listing_draft_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_import_source_mappings_draft_id", table_name="import_source_mappings")
    op.drop_table("import_source_mappings")
    op.drop_index("ix_import_rows_batch_id", table_name="import_rows")
    op.drop_table("import_rows")
    op.drop_index("ix_import_batches_org_created", table_name="import_batches")
    op.drop_table("import_batches")
