"""vessel_category_foundation

Revision ID: e91a4c7d0f3b
Revises: f1a9c3d7b802
Create Date: 2026-10-26 09:00:00.000000

SLICE-0091. Adds the explicit, source-qualified Sail/Power/Motorsailer
vessel category foundation (`docs/slices/SLICE-0091-vessel-category-
foundation.md` §A/§B):

1. Extends the existing `physical_boat_claim_revisions` immutable
   claim-revision table (9c2e6b4a1d80, most recently extended c7d4a1e95f36
   for `beam`/`hull_material`) in place with one new optional claim field:

       vessel_category_assertion_kind / vessel_category_value

   Identical two-state shape to `hull_material` (`VALUE_ASSERTION`/
   `UNKNOWN`, no `ABSENT`), but with the bounded three-value positive
   vocabulary `SAIL`/`POWER`/`MOTORSAILER` -- `CONFLICT` and `UNKNOWN` are
   resolution-time outcomes only
   (`hullq.domain.vessel_category.VesselCategoryResolution`), never a
   legal column value here.

   The new column pair is NULLable with no `server_default` other than
   NULL, so every existing row reads back with the field cleanly omitted.
   Because `hullq.persistence.physical_boat_claims._claim_envelope_dict`
   only adds a `"vessel_category"` key to the immutable-content fingerprint
   envelope when that claim is actually present, an existing revision's
   stored `content_hash` (computed before this migration) still matches the
   envelope recomputed for its own exact retry after this migration.

2. Two new tables giving the independent design-side plane
   (`hullq.domain.vessel_category.DesignVesselCategoryAssertion`) its own
   small, single-purpose immutable-revision + explicit-current-head home
   (`hullq.persistence.boat_design_category`) -- mirroring the
   `physical_boat_claim_revisions`/`physical_boat_claim_heads` shape, but
   scoped to exactly one field and locking the real pre-existing
   `canonical_boat_designs` parent row for concurrency (never a PostgreSQL
   advisory lock, since -- unlike `field_resolutions` -- this table's
   subject is always exactly one BoatDesign, a real durable parent row):

   - ``boat_design_category_assertions`` -- one immutable row per
     successful assertion write. Never updated or deleted by application
     code; an assertion is superseded only by a new row plus a
     head-pointer change (a retraction back to `UNKNOWN` is itself such a
     new row, never an UPDATE of the prior one).
   - ``boat_design_category_assertion_heads`` -- the explicit current
     assertion pointer per `boat_design_id`, so "current" is never inferred
     from insertion order or a timestamp.

   Deliberately NOT a reuse of the generalized `field_resolutions`/
   `field_resolution_heads` tables (630ac7da649e): that kernel's job is
   source-rights-gated admission of physical/technical BoatDesign facts
   sourced from external research evidence and requires the asserted value
   to already durably exist elsewhere for its write-time canonical-
   consistency check -- entangling a type/admission foundation with that
   machinery would be a second truth kernel wearing the first one's
   clothes. See `hullq.persistence.boat_design_category`'s module docstring
   for the full rationale.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e91a4c7d0f3b"
down_revision: str | None = "f1a9c3d7b802"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_VESSEL_CATEGORY_VALUES = ("SAIL", "POWER", "MOTORSAILER")
_ASSERTION_KIND_VALUES = ("VALUE_ASSERTION", "UNKNOWN")
_ISSUER_KIND_VALUES = ("human", "deterministic_tool", "llm")


def upgrade() -> None:
    # --- 1. concrete PhysicalBoat claim: vessel_category -------------------
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("vessel_category_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("vessel_category_value", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_vessel_category_state_valid",
        "physical_boat_claim_revisions",
        "COALESCE(vessel_category_assertion_kind IS NULL AND vessel_category_value IS NULL, "
        "    FALSE) "
        "OR COALESCE(vessel_category_assertion_kind = 'VALUE_ASSERTION' "
        f"    AND vessel_category_value IN {_VESSEL_CATEGORY_VALUES!r}, FALSE) "
        "OR COALESCE(vessel_category_assertion_kind = 'UNKNOWN' "
        "    AND vessel_category_value IS NULL, FALSE)",
    )

    # --- 2. design-side plane: boat_design_category_assertions -------------
    op.create_table(
        "boat_design_category_assertions",
        sa.Column("assertion_id", sa.Text(), primary_key=True),
        sa.Column("boat_design_id", sa.Text(), nullable=False),
        sa.Column("assertion_kind", sa.Text(), nullable=False),
        sa.Column("category_value", sa.Text(), nullable=True),
        sa.Column("issuer_kind", sa.Text(), nullable=False),
        sa.Column("issuer_identifier", sa.Text(), nullable=False),
        sa.Column("issuer_version", sa.Text(), nullable=True),
        sa.Column("previous_assertion_id", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["boat_design_id"],
            ["canonical_boat_designs.id"],
            name="fk_bd_cat_assertions_boat_design",
        ),
        # Lets both boat_design_category_assertion_heads.current_assertion_id
        # and this table's own previous_assertion_id be enforced via a
        # composite FK back to (boat_design_id, assertion_id), so a
        # head/predecessor pointer can never reference a different
        # BoatDesign's assertion.
        sa.UniqueConstraint(
            "boat_design_id", "assertion_id", name="uq_bd_cat_assertions_design_assertion"
        ),
        sa.ForeignKeyConstraint(
            ["boat_design_id", "previous_assertion_id"],
            ["boat_design_category_assertions.boat_design_id",
             "boat_design_category_assertions.assertion_id"],
            name="fk_bd_cat_assertions_previous_same_design",
        ),
        sa.CheckConstraint(
            f"assertion_kind IN {_ASSERTION_KIND_VALUES!r}", name="bd_cat_assertion_kind_valid"
        ),
        sa.CheckConstraint(
            "COALESCE(assertion_kind = 'VALUE_ASSERTION' "
            f"    AND category_value IN {_VESSEL_CATEGORY_VALUES!r}, FALSE) "
            "OR COALESCE(assertion_kind = 'UNKNOWN' AND category_value IS NULL, FALSE)",
            name="bd_cat_assertion_value_state_valid",
        ),
        sa.CheckConstraint(
            f"issuer_kind IN {_ISSUER_KIND_VALUES!r}", name="bd_cat_assertion_issuer_kind_valid"
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="bd_cat_assertion_content_hash_sha256_length"
        ),
    )
    op.create_index(
        "ix_bd_cat_assertions_boat_design",
        "boat_design_category_assertions",
        ["boat_design_id"],
    )

    # --- 3. design-side plane: boat_design_category_assertion_heads --------
    op.create_table(
        "boat_design_category_assertion_heads",
        sa.Column("boat_design_id", sa.Text(), primary_key=True),
        sa.Column("current_assertion_id", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["boat_design_id"],
            ["canonical_boat_designs.id"],
            name="fk_bd_cat_heads_boat_design",
        ),
        # Composite FK (not a plain FK on current_assertion_id alone):
        # forces the referenced assertion's own boat_design_id to equal this
        # row's, so a head row for one BoatDesign pointing at a different
        # BoatDesign's assertion is impossible in any DB-valid state.
        sa.ForeignKeyConstraint(
            ["boat_design_id", "current_assertion_id"],
            ["boat_design_category_assertions.boat_design_id",
             "boat_design_category_assertions.assertion_id"],
            name="fk_bd_cat_heads_current_same_design",
        ),
    )


def downgrade() -> None:
    op.drop_table("boat_design_category_assertion_heads")
    op.drop_index("ix_bd_cat_assertions_boat_design", table_name="boat_design_category_assertions")
    op.drop_table("boat_design_category_assertions")

    op.drop_constraint(
        "pb_claim_rev_vessel_category_state_valid",
        "physical_boat_claim_revisions",
        type_="check",
    )
    op.drop_column("physical_boat_claim_revisions", "vessel_category_value")
    op.drop_column("physical_boat_claim_revisions", "vessel_category_assertion_kind")
