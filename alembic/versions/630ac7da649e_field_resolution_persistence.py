"""field_resolution_persistence

Revision ID: 630ac7da649e
Revises: 9c2e6b4a1d80
Create Date: 2026-09-12 09:00:00.000000

SLICE-0051 amendment (FieldResolution blocker resolution,
docs/SLICE_0051_FIELD_RESOLUTION_BLOCKER_RECONCILIATION_2026-09-12.md).

Adds the minimum durable PostgreSQL persistence for the already-accepted
OQ-004 / ADR-0006 versioned `FieldResolution` domain model
(`hullq.domain.provenance.FieldResolution`, `specs/PROVENANCE_MODEL.v0.1.md`,
`specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`). No new resolution/quality model
is introduced -- this migration only gives the existing domain type a
durable, race-safe home.

Two tables, mirroring the `physical_boat_claim_revisions` /
`physical_boat_claim_heads` shape from `9c2e6b4a1d80`:

- ``field_resolutions`` -- one immutable row per successful resolution
  write. Never updated or deleted by application code; a resolution is
  superseded only by a new row plus a head-pointer change.
- ``field_resolution_heads`` -- the explicit current-resolution pointer per
  `(subject_kind, subject_id, field_pointer)`, so "current" is never
  inferred from insertion order or a timestamp (`PROVENANCE_MODEL.v0.1.md`
  §5: "at most one current/active resolution per (subject_kind, subject_id,
  field_pointer)").

Unlike `physical_boat_claim_revisions` (which always has a pre-existing
`physical_boats` parent row to lock for concurrency control),
`field_resolutions` has no such fixed parent: `subject_kind`/`subject_id`
range over BoatModel/BoatDesign/NamedVariant/DesignOption, several of which
are not separate durable tables in this schema (NamedVariant/DesignOption
are opaque JSONB inside `canonical_boat_designs`, per the 002 migration's
own docstring). `hullq.persistence.field_resolution` therefore serializes
concurrent writers for the same logical `(subject_kind, subject_id,
field_pointer)` via a PostgreSQL advisory transaction lock
(`pg_advisory_xact_lock`) instead of a row lock -- see that module's
docstring for the full rationale.

``canonical_value_snapshot`` is stored as JSONB, kept schema-generic exactly
as `FIELD_RESOLUTION_SCHEMA.v0.1.json` requires (`{}` = any JSON type).
SLICE-0051's own bounded numeric `draft_max_m` usage always stores this as a
JSON *string* holding the canonical exact-decimal text (never a JSON
number), so PostgreSQL/JSONB's own float-oriented number decoding can never
introduce binary-float drift for that field -- see
`hullq.persistence.field_resolution`'s docstring.

``supporting_evidence_ids`` / ``contradicting_evidence_ids`` /
``considered_evidence_ids`` are stored as JSONB arrays of evidence ids;
CHECK constraints enforce the FIELD_RESOLUTION_SCHEMA.v0.1 structural rules
(VAL-PROV-005/007/008) directly, while cross-referential rules that need
the actual referenced evidence rows (existence, subject/field compatibility,
supporting/contradicting subset-of-considered, source-rights admission --
VAL-PROV-002/004) are enforced by `hullq.persistence.field_resolution`,
reusing `hullq.domain.provenance.validate_resolution_invariants` and
`hullq.sources.rights.check_source_use` rather than being reimplemented as
SQL.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "630ac7da649e"
down_revision: str | None = "9c2e6b4a1d80"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_SUBJECT_KIND_VALUES = ("boat_model", "boat_design", "named_variant", "design_option")
_STATE_VALUES = ("resolved", "resolved_with_conflict", "unknown", "needs_review", "conflict")
_RESOLVER_KIND_VALUES = ("human", "deterministic_tool", "llm")


def upgrade() -> None:
    op.create_table(
        "field_resolutions",
        sa.Column("resolution_id", sa.Text(), primary_key=True),
        sa.Column("subject_kind", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("field_pointer", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("canonical_value_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column(
            "supporting_evidence_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "contradicting_evidence_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "considered_evidence_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("resolution_method", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("resolver_kind", sa.Text(), nullable=False),
        sa.Column("resolver_identifier", sa.Text(), nullable=False),
        sa.Column("resolver_version", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("supersedes_resolution_id", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Lets both field_resolution_heads.current_resolution_id and this
        # table's own supersedes_resolution_id be enforced via a composite
        # FK back to (subject_kind, subject_id, field_pointer,
        # resolution_id), so a head/supersession pointer can never
        # reference a different subject's or field's resolution.
        sa.UniqueConstraint(
            "subject_kind",
            "subject_id",
            "field_pointer",
            "resolution_id",
            name="uq_field_res_subject_field_resolution",
        ),
        sa.ForeignKeyConstraint(
            ["subject_kind", "subject_id", "field_pointer", "supersedes_resolution_id"],
            [
                "field_resolutions.subject_kind",
                "field_resolutions.subject_id",
                "field_resolutions.field_pointer",
                "field_resolutions.resolution_id",
            ],
            name="fk_field_res_supersedes_same_subject_field",
        ),
        sa.CheckConstraint(
            f"subject_kind IN {_SUBJECT_KIND_VALUES!r}", name="field_res_subject_kind_valid"
        ),
        sa.CheckConstraint("field_pointer ~ '^/'", name="field_res_field_pointer_valid"),
        sa.CheckConstraint(f"state IN {_STATE_VALUES!r}", name="field_res_state_valid"),
        # VAL-PROV-007: unknown/needs_review/conflict MUST have a null
        # snapshot. VAL-PROV-005 (paired with the domain-layer resolved ->
        # non-null requirement): resolved/resolved_with_conflict MUST have a
        # non-null snapshot. COALESCE(..., FALSE) per branch mirrors the
        # 9c2e6b4a1d80 migration's rationale: SQL's NULL-propagating
        # three-valued logic would otherwise silently accept an
        # out-of-enum state value.
        sa.CheckConstraint(
            "COALESCE(state IN ('unknown', 'needs_review', 'conflict') "
            "    AND canonical_value_snapshot IS NULL, FALSE) "
            "OR COALESCE(state IN ('resolved', 'resolved_with_conflict') "
            "    AND canonical_value_snapshot IS NOT NULL, FALSE)",
            name="field_res_snapshot_state_valid",
        ),
        # VAL-PROV-005 (support requirement): a resolved value must be
        # backed by at least one supporting evidence id.
        sa.CheckConstraint(
            "state NOT IN ('resolved', 'resolved_with_conflict') "
            "OR jsonb_array_length(supporting_evidence_ids) >= 1",
            name="field_res_resolved_requires_supporting_evidence",
        ),
        # VAL-PROV-008 / PROVENANCE_MODEL.v0.1.md §5: resolved_with_conflict
        # and conflict MUST retain at least one contradicting evidence id.
        sa.CheckConstraint(
            "state NOT IN ('resolved_with_conflict', 'conflict') "
            "OR jsonb_array_length(contradicting_evidence_ids) >= 1",
            name="field_res_conflict_requires_contradicting_evidence",
        ),
        sa.CheckConstraint(
            f"resolver_kind IN {_RESOLVER_KIND_VALUES!r}", name="field_res_resolver_kind_valid"
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="field_res_content_hash_sha256_length"
        ),
    )
    op.create_index(
        "ix_field_res_subject_field",
        "field_resolutions",
        ["subject_kind", "subject_id", "field_pointer"],
    )

    op.create_table(
        "field_resolution_heads",
        sa.Column("subject_kind", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("field_pointer", sa.Text(), nullable=False),
        sa.Column("current_resolution_id", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint(
            "subject_kind", "subject_id", "field_pointer", name="pk_field_res_heads"
        ),
        # Composite FK (not a plain FK on current_resolution_id alone):
        # forces the referenced resolution's own (subject_kind, subject_id,
        # field_pointer) to equal this row's, so a head row for one subject
        # field pointing at a resolution belonging to a different subject or
        # field is impossible in any DB-valid state.
        sa.ForeignKeyConstraint(
            ["subject_kind", "subject_id", "field_pointer", "current_resolution_id"],
            [
                "field_resolutions.subject_kind",
                "field_resolutions.subject_id",
                "field_resolutions.field_pointer",
                "field_resolutions.resolution_id",
            ],
            name="fk_field_res_heads_current_same_subject_field",
        ),
    )


def downgrade() -> None:
    op.drop_table("field_resolution_heads")
    op.drop_index("ix_field_res_subject_field", table_name="field_resolutions")
    op.drop_table("field_resolutions")
