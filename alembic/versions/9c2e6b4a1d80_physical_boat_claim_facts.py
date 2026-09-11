"""physical_boat_claim_facts

Revision ID: 9c2e6b4a1d80
Revises: 8b6d3f0a2c17
Create Date: 2026-09-10 09:00:00.000000

SLICE-0050. Adds the smallest durable persistence for the seven accepted
SLICE-0050 `PHYSICAL_BOAT` fields (`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`)
as an immutable revision history plus an explicit current/head pointer,
directly on top of the SLICE-0046 `physical_boats` table -- mirroring the
SLICE-0045 `native_listing_offer_facts` migration's shape, with the head
keyed per `(physical_boat_id, claiming_organization_id)` pair instead of per
NativeListing (SLICE-0050 §7): claim authority belongs to the claiming
Organization, and a different Organization's own current claim head for the
same PhysicalBoat remains fully independent (no cross-Organization
supersession, SLICE-0050 §9).

Two tables only:

- ``physical_boat_claim_revisions`` -- one immutable row per successful
  claim write. Never updated or deleted by application code; a revision is
  superseded only by a new row plus a head-pointer change.
- ``physical_boat_claim_heads`` -- the explicit current-revision pointer per
  `(physical_boat_id, claiming_organization_id)` pair, so "current" is never
  inferred from ``MAX(recorded_at)`` or row order.

``content_hash`` is internal persistence evidence for idempotency/conflict
detection only, not a broker-facing field (mirrors
``native_listing_offer_revisions.content_hash``). ``loa_length``/``draft``
are stored as unconstrained ``NUMERIC`` (arbitrary precision, never binary
floating point); a CHECK constraint rejects the PostgreSQL 14+ NUMERIC
``NaN``/``Infinity``/``-Infinity`` special values and requires a positive
value, mirroring the domain-layer finite/positive check in
``hullq.domain.physical_boat_claims``.

``previous_claim_revision_id`` records the exact predecessor revision that
was current for this same `(physical_boat_id, claiming_organization_id)`
pair immediately before this row was inserted (``NULL`` for that pair's
first revision), fixed permanently at insertion time and never recomputed
from ``recorded_at``/row order. A ``UNIQUE (physical_boat_id,
claiming_organization_id, claim_revision_id)`` constraint on this table lets
both ``physical_boat_claim_heads.current_claim_revision_id`` and this
table's own ``previous_claim_revision_id`` be enforced through a *composite*
foreign key back to ``(physical_boat_id, claiming_organization_id,
claim_revision_id)`` here, so PostgreSQL itself makes it impossible for a
head or predecessor pointer to reference a revision that belongs to a
*different* PhysicalBoat or a *different* claiming Organization.

Every non-blank text CHECK (``marketed_brand_claim``,
``model_designation_claim``) matches the domain layer's Python
``str.strip()`` whitespace semantics exactly, via the same explicit
enumeration of the 29 Unicode code points ``str.isspace()`` recognizes used
by the SLICE-0045 migration -- see that migration's docstring for the full
PostgreSQL-locale rationale.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c2e6b4a1d80"
down_revision: str | None = "8b6d3f0a2c17"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Identical to the set used by 4d8e1a72c9f0_native_listing_offer_facts.py --
# see that migration for the full rationale.
_PYTHON_WHITESPACE_CODEPOINTS_INT = (
    0x0009,
    0x000A,
    0x000B,
    0x000C,
    0x000D,
    0x001C,
    0x001D,
    0x001E,
    0x001F,
    0x0020,
    0x0085,
    0x00A0,
    0x1680,
    0x2000,
    0x2001,
    0x2002,
    0x2003,
    0x2004,
    0x2005,
    0x2006,
    0x2007,
    0x2008,
    0x2009,
    0x200A,
    0x2028,
    0x2029,
    0x202F,
    0x205F,
    0x3000,
)
assert len(_PYTHON_WHITESPACE_CODEPOINTS_INT) == 29
_BACKSLASH = chr(0x5C)
_PYTHON_WHITESPACE_REGEX_CLASS = "".join(
    f"{_BACKSLASH}u{cp:04x}" for cp in _PYTHON_WHITESPACE_CODEPOINTS_INT
)


def _non_blank_predicate(column: str) -> str:
    """SQL predicate: *column* contains at least one character outside the
    exact Python str.isspace() whitespace set -- i.e. is not blank under
    the same rule the domain layer's str.strip()-based check applies."""
    return f"{column} ~ '[^{_PYTHON_WHITESPACE_REGEX_CLASS}]'"


_KEEL_CONFIGURATION_VALUES = (
    "FIN",
    "FIN_WITH_BULB",
    "LONG_KEEL",
    "WING",
    "CENTERBOARD",
    "LIFTING_KEEL",
    "TWIN_KEEL",
    "OTHER",
)
_RUDDER_CONFIGURATION_VALUES = ("SPADE", "SKEG_HUNG", "TRANSOM_HUNG", "TWIN", "OTHER")


def upgrade() -> None:
    op.create_table(
        "physical_boat_claim_revisions",
        sa.Column("claim_revision_id", sa.Text(), primary_key=True),
        sa.Column(
            "physical_boat_id",
            sa.Text(),
            sa.ForeignKey("physical_boats.physical_boat_id"),
            nullable=False,
        ),
        sa.Column("claiming_organization_id", sa.Text(), nullable=False),
        sa.Column("recorded_by_account_id", sa.Text(), nullable=False),
        sa.Column("marketed_brand_claim", sa.Text(), nullable=False),
        sa.Column("model_designation_claim", sa.Text(), nullable=False),
        sa.Column("build_year_assertion_kind", sa.Text(), nullable=False),
        sa.Column("build_year_value", sa.Integer(), nullable=True),
        sa.Column("loa_length_assertion_kind", sa.Text(), nullable=True),
        sa.Column("loa_length_value", sa.Numeric(), nullable=True),
        sa.Column("draft_assertion_kind", sa.Text(), nullable=True),
        sa.Column("draft_value", sa.Numeric(), nullable=True),
        sa.Column("keel_configuration_assertion_kind", sa.Text(), nullable=True),
        sa.Column("keel_configuration_value", sa.Text(), nullable=True),
        sa.Column("rudder_configuration_assertion_kind", sa.Text(), nullable=True),
        sa.Column("rudder_configuration_value", sa.Text(), nullable=True),
        sa.Column("previous_claim_revision_id", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Lets both physical_boat_claim_heads.current_claim_revision_id and
        # this table's own previous_claim_revision_id be enforced via a
        # composite FK back to (physical_boat_id, claiming_organization_id,
        # claim_revision_id), so a head/predecessor pointer can never
        # reference a different PhysicalBoat's or Organization's revision.
        sa.UniqueConstraint(
            "physical_boat_id",
            "claiming_organization_id",
            "claim_revision_id",
            name="uq_pb_claim_rev_boat_org_revision",
        ),
        sa.ForeignKeyConstraint(
            ["physical_boat_id", "claiming_organization_id", "previous_claim_revision_id"],
            [
                "physical_boat_claim_revisions.physical_boat_id",
                "physical_boat_claim_revisions.claiming_organization_id",
                "physical_boat_claim_revisions.claim_revision_id",
            ],
            name="fk_pb_claim_rev_previous_same_boat_org",
        ),
        sa.CheckConstraint(
            _non_blank_predicate("marketed_brand_claim"),
            name="pb_claim_rev_marketed_brand_claim_non_blank",
        ),
        sa.CheckConstraint(
            _non_blank_predicate("model_designation_claim"),
            name="pb_claim_rev_model_designation_claim_non_blank",
        ),
        sa.CheckConstraint(
            "build_year_assertion_kind IN ('VALUE_ASSERTION', 'UNKNOWN')",
            name="pb_claim_rev_build_year_kind_valid",
        ),
        sa.CheckConstraint(
            "COALESCE(build_year_assertion_kind = 'VALUE_ASSERTION' AND build_year_value IS NOT NULL, FALSE) "
            "OR COALESCE(build_year_assertion_kind = 'UNKNOWN' AND build_year_value IS NULL, FALSE)",
            name="pb_claim_rev_build_year_state_valid",
        ),
        # Every optional/conditional assertion-kind/value column pair below
        # is constrained by one explicit enumeration of every valid (kind,
        # value) state, each branch wrapped in COALESCE(..., FALSE) --
        # mirrors the SLICE-0045 migration's rationale: an equality form
        # like `(kind = 'X') = (value IS NOT NULL)` is silently satisfied by
        # SQL's NULL-propagating three-valued logic whenever `kind IS NULL`,
        # so it would not reject `kind = NULL, value = 'hidden durable
        # value'`.
        sa.CheckConstraint(
            "COALESCE(loa_length_assertion_kind IS NULL AND loa_length_value IS NULL, FALSE) "
            "OR COALESCE(loa_length_assertion_kind = 'VALUE_ASSERTION' "
            "    AND loa_length_value IS NOT NULL AND loa_length_value::text !~ '[A-Za-z]' "
            "    AND loa_length_value > 0, FALSE) "
            "OR COALESCE(loa_length_assertion_kind = 'UNKNOWN' AND loa_length_value IS NULL, FALSE)",
            name="pb_claim_rev_loa_length_state_valid",
        ),
        sa.CheckConstraint(
            "COALESCE(draft_assertion_kind IS NULL AND draft_value IS NULL, FALSE) "
            "OR COALESCE(draft_assertion_kind = 'VALUE_ASSERTION' "
            "    AND draft_value IS NOT NULL AND draft_value::text !~ '[A-Za-z]' "
            "    AND draft_value > 0, FALSE) "
            "OR COALESCE(draft_assertion_kind = 'UNKNOWN' AND draft_value IS NULL, FALSE)",
            name="pb_claim_rev_draft_state_valid",
        ),
        sa.CheckConstraint(
            "COALESCE(keel_configuration_assertion_kind IS NULL AND keel_configuration_value IS NULL, FALSE) "
            "OR COALESCE(keel_configuration_assertion_kind = 'VALUE_ASSERTION' "
            f"    AND keel_configuration_value IN {_KEEL_CONFIGURATION_VALUES!r}, FALSE) "
            "OR COALESCE(keel_configuration_assertion_kind = 'UNKNOWN' AND keel_configuration_value IS NULL, FALSE)",
            name="pb_claim_rev_keel_configuration_state_valid",
        ),
        sa.CheckConstraint(
            "COALESCE(rudder_configuration_assertion_kind IS NULL AND rudder_configuration_value IS NULL, FALSE) "
            "OR COALESCE(rudder_configuration_assertion_kind = 'VALUE_ASSERTION' "
            f"    AND rudder_configuration_value IN {_RUDDER_CONFIGURATION_VALUES!r}, FALSE) "
            "OR COALESCE(rudder_configuration_assertion_kind = 'UNKNOWN' AND rudder_configuration_value IS NULL, FALSE)",
            name="pb_claim_rev_rudder_configuration_state_valid",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="pb_claim_rev_content_hash_sha256_length"
        ),
    )
    op.create_index(
        "ix_pb_claim_rev_boat_org",
        "physical_boat_claim_revisions",
        ["physical_boat_id", "claiming_organization_id"],
    )

    op.create_table(
        "physical_boat_claim_heads",
        sa.Column(
            "physical_boat_id",
            sa.Text(),
            sa.ForeignKey("physical_boats.physical_boat_id"),
            nullable=False,
        ),
        sa.Column("claiming_organization_id", sa.Text(), nullable=False),
        sa.Column("current_claim_revision_id", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint(
            "physical_boat_id", "claiming_organization_id", name="pk_pb_claim_heads"
        ),
        # Composite FK (not a plain FK on current_claim_revision_id alone):
        # forces the referenced revision's own (physical_boat_id,
        # claiming_organization_id) to equal this row's, so a head row for
        # (boat A, org X) pointing at a revision belonging to (boat B, org
        # X) or (boat A, org Y) is impossible in any DB-valid state.
        sa.ForeignKeyConstraint(
            ["physical_boat_id", "claiming_organization_id", "current_claim_revision_id"],
            [
                "physical_boat_claim_revisions.physical_boat_id",
                "physical_boat_claim_revisions.claiming_organization_id",
                "physical_boat_claim_revisions.claim_revision_id",
            ],
            name="fk_pb_claim_heads_current_same_boat_org",
        ),
    )


def downgrade() -> None:
    op.drop_table("physical_boat_claim_heads")
    op.drop_index("ix_pb_claim_rev_boat_org", table_name="physical_boat_claim_revisions")
    op.drop_table("physical_boat_claim_revisions")
