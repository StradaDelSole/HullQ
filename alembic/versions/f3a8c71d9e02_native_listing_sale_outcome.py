"""native_listing_sale_outcome

Revision ID: f3a8c71d9e02
Revises: c2f9a83e51d7
Create Date: 2026-10-01 09:00:00.000000

SLICE-0074. Adds the smallest durable persistence for an explicit broker
SaleOutcome close-out (`specs/BROKER_SALE_OUTCOME_CONTRACT.v0.1.md`) as an
immutable revision history plus an explicit current/head pointer, directly
on top of the SLICE-0043 ``native_listings`` table -- exactly mirroring the
SLICE-0045 ``native_listing_offer_revisions``/``native_listing_offer_heads``
shape (`4d8e1a72c9f0_native_listing_offer_facts.py`):

- ``native_listing_sale_outcome_revisions`` -- one immutable row per
  successful outcome write. Never updated or deleted by application code; a
  revision is superseded only by a new row plus a head-pointer change.
- ``native_listing_sale_outcome_heads`` -- the explicit current-revision
  pointer per NativeListing, so "current" is never inferred from
  ``MAX(recorded_at)`` or row order.

``content_hash`` is internal persistence evidence for idempotency/conflict
detection only, mirroring ``native_listing_offer_revisions.content_hash``.
Achieved sale price is stored as unconstrained ``NUMERIC`` (never binary
floating point); a CHECK constraint rejects the PostgreSQL 14+ NUMERIC
``NaN``/``Infinity``/``-Infinity`` special values. ``sold_date`` is a plain
``DATE`` -- deliberately distinct from ``recorded_at`` (contract §3
invariant 5).

``originating_lead_id`` is a plain (non-composite) foreign key to
``buyer_leads.lead_id``: the SLICE-0070 Lead table has no
``(native_listing_id, lead_id)`` composite key for this migration to join
against, so "the referenced Lead belongs to the same NativeListing/
Organization" (contract §13) is enforced by
``hullq.persistence.native_listing_sale_outcome.close_native_listing_as_sold``
at write time, not by the database schema alone -- mirroring how the
SLICE-0045 offer/claim tables also leave cross-entity *semantic* agreement
(e.g. Organization match) to application code atop their own FK existence
checks.

``previous_sale_outcome_revision_id`` records the exact predecessor revision
that was current immediately before this row was inserted (``NULL`` for a
NativeListing's first revision), fixed permanently at insertion time. A
``UNIQUE (native_listing_id, sale_outcome_revision_id)`` constraint lets both
``native_listing_sale_outcome_heads.current_sale_outcome_revision_id`` and
this table's own ``previous_sale_outcome_revision_id`` be enforced through a
composite foreign key back to ``(native_listing_id,
sale_outcome_revision_id)`` here, so PostgreSQL itself makes it impossible
for a head/predecessor pointer to reference a revision belonging to a
*different* NativeListing.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a8c71d9e02"
down_revision: str | None = "c2f9a83e51d7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_listing_sale_outcome_revisions",
        sa.Column("sale_outcome_revision_id", sa.Text(), primary_key=True),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            nullable=False,
        ),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column("recorded_by_account_id", sa.Text(), nullable=False),
        sa.Column("outcome_kind", sa.Text(), nullable=False),
        sa.Column("sold_date", sa.Date(), nullable=True),
        sa.Column("achieved_amount", sa.Numeric(), nullable=True),
        sa.Column("achieved_currency", sa.Text(), nullable=True),
        sa.Column(
            "originating_lead_id",
            sa.Text(),
            sa.ForeignKey("buyer_leads.lead_id"),
            nullable=True,
        ),
        sa.Column("previous_sale_outcome_revision_id", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Lets both native_listing_sale_outcome_heads.current_sale_outcome_revision_id
        # and this table's own previous_sale_outcome_revision_id be enforced
        # via a composite FK back to (native_listing_id,
        # sale_outcome_revision_id), so a head/predecessor pointer can never
        # reference another NativeListing's revision.
        sa.UniqueConstraint(
            "native_listing_id",
            "sale_outcome_revision_id",
            name="uq_nl_sale_outcome_rev_listing_revision",
        ),
        sa.ForeignKeyConstraint(
            ["native_listing_id", "previous_sale_outcome_revision_id"],
            [
                "native_listing_sale_outcome_revisions.native_listing_id",
                "native_listing_sale_outcome_revisions.sale_outcome_revision_id",
            ],
            name="fk_nl_sale_outcome_rev_previous_same_listing",
        ),
        sa.CheckConstraint(
            "outcome_kind IN ('SOLD')",
            name="nl_sale_outcome_rev_kind_valid",
        ),
        sa.CheckConstraint(
            "(achieved_amount IS NULL AND achieved_currency IS NULL) "
            "OR (achieved_amount IS NOT NULL AND achieved_amount > 0 AND achieved_currency IS NOT NULL)",
            name="nl_sale_outcome_rev_amount_currency_conditionality",
        ),
        sa.CheckConstraint(
            # PostgreSQL 14+ NUMERIC accepts 'NaN'/'Infinity'/'-Infinity'; a
            # valid finite decimal's text form never contains a letter, so
            # this rejects all three without needing version-specific
            # isnan()/isinf() functions (mirrors
            # nl_offer_rev_asking_price_amount_finite).
            "achieved_amount IS NULL OR achieved_amount::text !~ '[A-Za-z]'",
            name="nl_sale_outcome_rev_achieved_amount_finite",
        ),
        sa.CheckConstraint(
            "achieved_currency IS NULL OR achieved_currency ~ '^[A-Z]{3}$'",
            name="nl_sale_outcome_rev_achieved_currency_code_shape",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="nl_sale_outcome_rev_content_hash_sha256_length"
        ),
    )
    op.create_index(
        "ix_nl_sale_outcome_rev_native_listing_id",
        "native_listing_sale_outcome_revisions",
        ["native_listing_id"],
    )

    op.create_table(
        "native_listing_sale_outcome_heads",
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            primary_key=True,
        ),
        sa.Column("current_sale_outcome_revision_id", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Composite FK (not a plain FK on current_sale_outcome_revision_id
        # alone): forces the referenced revision's own native_listing_id to
        # equal this row's native_listing_id.
        sa.ForeignKeyConstraint(
            ["native_listing_id", "current_sale_outcome_revision_id"],
            [
                "native_listing_sale_outcome_revisions.native_listing_id",
                "native_listing_sale_outcome_revisions.sale_outcome_revision_id",
            ],
            name="fk_nl_sale_outcome_heads_current_same_listing",
        ),
    )


def downgrade() -> None:
    op.drop_table("native_listing_sale_outcome_heads")
    op.drop_index(
        "ix_nl_sale_outcome_rev_native_listing_id",
        table_name="native_listing_sale_outcome_revisions",
    )
    op.drop_table("native_listing_sale_outcome_revisions")
