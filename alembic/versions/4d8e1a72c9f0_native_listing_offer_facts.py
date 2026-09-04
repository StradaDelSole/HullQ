"""native_listing_offer_facts

Revision ID: 4d8e1a72c9f0
Revises: 1bb00df4a018
Create Date: 2026-09-04 12:00:00.000000

SLICE-0045. Adds the smallest durable persistence for the nine accepted
`LISTING_OFFER` fields (`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`) as an
immutable revision history plus an explicit current/head pointer, directly
on top of the SLICE-0043 `native_listings` table.

Two tables only:

- ``native_listing_offer_revisions`` — one immutable row per successful
  offer write. Never updated or deleted by application code; a revision is
  superseded only by a new row plus a head-pointer change.
- ``native_listing_offer_heads`` — the explicit current-revision pointer per
  NativeListing, so "current" is never inferred from ``MAX(recorded_at)`` or
  row order.

``content_hash`` is internal persistence evidence for idempotency/conflict
detection only (mirrors ``native_listings.content_hash`` from SLICE-0043),
not a broker-facing listing field. Money is stored as unconstrained
``NUMERIC`` (arbitrary precision, never binary floating point); a CHECK
constraint rejects the PostgreSQL 14+ NUMERIC ``NaN``/``Infinity``/
``-Infinity`` special values, mirroring the domain-layer finite check.
Country/currency CHECK constraints enforce normalized code *shape*
(ISO 3166-1 alpha-2 / ISO 4217, uppercase) as belt-and-suspenders alongside
the domain-layer validation in ``hullq.domain.native_listing_offer`` — they
do not by themselves prove membership in the real ISO code lists.

``previous_offer_revision_id`` records the exact predecessor revision that
was current immediately before this row was inserted (``NULL`` for a
NativeListing's first revision), fixed permanently at insertion time and
never recomputed from ``recorded_at``/row order. A ``UNIQUE
(native_listing_id, offer_revision_id)`` constraint on this table lets both
``native_listing_offer_heads.current_offer_revision_id`` and this table's
own ``previous_offer_revision_id`` be enforced through a *composite*
foreign key back to ``(native_listing_id, offer_revision_id)`` here, so
PostgreSQL itself makes it impossible for a head or predecessor pointer to
reference a revision that belongs to a *different* NativeListing.

Every optional/conditional assertion-kind/value column pair (location
region, broker summary, known-history narrative, VAT/tax status) is
constrained by one explicit three-way CHECK per field enumerating exactly
the valid states (omitted / a specific non-NULL assertion kind with its
required value shape) — never `(kind = 'X') = (value IS NOT NULL)`, which
is silently satisfied by SQL's NULL-propagation three-valued logic when
`kind IS NULL` regardless of what `value` holds.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d8e1a72c9f0"
down_revision: str | None = "1bb00df4a018"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_listing_offer_revisions",
        sa.Column("offer_revision_id", sa.Text(), primary_key=True),
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            nullable=False,
        ),
        sa.Column("publishing_organization_id", sa.Text(), nullable=False),
        sa.Column("recorded_by_account_id", sa.Text(), nullable=False),
        sa.Column("asking_price_mode", sa.Text(), nullable=False),
        sa.Column("asking_price_amount", sa.Numeric(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("location_country", sa.Text(), nullable=False),
        sa.Column("location_region_assertion_kind", sa.Text(), nullable=True),
        sa.Column("location_region_value", sa.Text(), nullable=True),
        sa.Column("broker_summary_assertion_kind", sa.Text(), nullable=True),
        sa.Column("broker_summary_value", sa.Text(), nullable=True),
        sa.Column("broker_description", sa.Text(), nullable=False),
        sa.Column("known_history_narrative_assertion_kind", sa.Text(), nullable=True),
        sa.Column("known_history_narrative_value", sa.Text(), nullable=True),
        sa.Column("vat_tax_status_assertion_kind", sa.Text(), nullable=True),
        sa.Column("vat_tax_status_value", sa.Text(), nullable=True),
        sa.Column("previous_offer_revision_id", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Lets both native_listing_offer_heads.current_offer_revision_id and
        # this table's own previous_offer_revision_id be enforced via a
        # composite FK back to (native_listing_id, offer_revision_id), so a
        # head/predecessor pointer can never reference another
        # NativeListing's revision.
        sa.UniqueConstraint(
            "native_listing_id", "offer_revision_id", name="uq_nl_offer_rev_listing_revision"
        ),
        sa.ForeignKeyConstraint(
            ["native_listing_id", "previous_offer_revision_id"],
            [
                "native_listing_offer_revisions.native_listing_id",
                "native_listing_offer_revisions.offer_revision_id",
            ],
            name="fk_nl_offer_rev_previous_same_listing",
        ),
        sa.CheckConstraint(
            "asking_price_mode IN ('AMOUNT', 'POA')",
            name="nl_offer_rev_asking_price_mode_valid",
        ),
        sa.CheckConstraint(
            "(asking_price_mode = 'AMOUNT' AND asking_price_amount IS NOT NULL "
            "  AND asking_price_amount > 0 AND currency IS NOT NULL) "
            "OR "
            "(asking_price_mode = 'POA' AND asking_price_amount IS NULL AND currency IS NULL)",
            name="nl_offer_rev_price_conditionality",
        ),
        sa.CheckConstraint(
            # PostgreSQL 14+ NUMERIC accepts 'NaN'/'Infinity'/'-Infinity'; a
            # valid finite decimal's text form never contains a letter, so
            # this rejects all three without needing version-specific
            # isnan()/isinf() functions.
            "asking_price_amount IS NULL OR asking_price_amount::text !~ '[A-Za-z]'",
            name="nl_offer_rev_asking_price_amount_finite",
        ),
        sa.CheckConstraint(
            "currency IS NULL OR currency ~ '^[A-Z]{3}$'",
            name="nl_offer_rev_currency_code_shape",
        ),
        sa.CheckConstraint(
            "location_country ~ '^[A-Z]{2}$'",
            name="nl_offer_rev_location_country_code_shape",
        ),
        sa.CheckConstraint(
            "length(btrim(broker_description)) > 0",
            name="nl_offer_rev_broker_description_non_blank",
        ),
        # Each of the four optional/conditional assertion-kind/value column
        # pairs below is constrained by one explicit enumeration of every
        # valid (kind, value) state rather than an equality like
        # `(kind = 'X') = (value IS NOT NULL)`. That equality form is
        # silently satisfied whenever kind IS NULL, regardless of what value
        # holds (SQL's NULL-propagating three-valued logic makes both sides
        # of the `=` evaluate to NULL, and CHECK treats NULL as passing) --
        # so `kind = NULL, value = 'hidden durable value'` would otherwise
        # pass validation and readback would silently discard that value by
        # treating a NULL kind as omission.
        #
        # Each OR-ed branch is wrapped in COALESCE(..., FALSE). Without it,
        # a branch like `kind = 'VALUE_ASSERTION' AND value IS NOT NULL`
        # still evaluates to NULL (not FALSE) whenever kind IS NULL, because
        # `NULL = 'VALUE_ASSERTION'` is NULL and `NULL AND TRUE` is NULL --
        # and `FALSE OR NULL OR FALSE` is NULL, not FALSE, so the whole
        # CHECK would again silently pass (CHECK only rejects a definite
        # FALSE) for exactly the `kind IS NULL, value IS NOT NULL` case this
        # constraint exists to reject. COALESCE forces every branch to a
        # definite boolean before the OR, so the overall expression is only
        # ever TRUE (a genuinely valid state) or FALSE (rejected).
        sa.CheckConstraint(
            "COALESCE(location_region_assertion_kind IS NULL AND location_region_value IS NULL, FALSE) "
            "OR COALESCE(location_region_assertion_kind = 'VALUE_ASSERTION' "
            "    AND location_region_value IS NOT NULL AND length(btrim(location_region_value)) > 0, FALSE) "
            "OR COALESCE(location_region_assertion_kind = 'UNKNOWN' AND location_region_value IS NULL, FALSE)",
            name="nl_offer_rev_location_region_state_valid",
        ),
        sa.CheckConstraint(
            "COALESCE(broker_summary_assertion_kind IS NULL AND broker_summary_value IS NULL, FALSE) "
            "OR COALESCE(broker_summary_assertion_kind = 'VALUE_ASSERTION' "
            "    AND broker_summary_value IS NOT NULL AND length(btrim(broker_summary_value)) > 0, FALSE) "
            "OR COALESCE(broker_summary_assertion_kind = 'NOT_APPLICABLE' AND broker_summary_value IS NULL, FALSE)",
            name="nl_offer_rev_broker_summary_state_valid",
        ),
        sa.CheckConstraint(
            "COALESCE(known_history_narrative_assertion_kind IS NULL "
            "    AND known_history_narrative_value IS NULL, FALSE) "
            "OR COALESCE(known_history_narrative_assertion_kind = 'VALUE_ASSERTION' "
            "    AND known_history_narrative_value IS NOT NULL "
            "    AND length(btrim(known_history_narrative_value)) > 0, FALSE) "
            "OR COALESCE(known_history_narrative_assertion_kind = 'NO_KNOWN_HISTORY_DECLARED' "
            "    AND known_history_narrative_value IS NULL, FALSE) "
            "OR COALESCE(known_history_narrative_assertion_kind = 'UNKNOWN' "
            "    AND known_history_narrative_value IS NULL, FALSE)",
            name="nl_offer_rev_known_history_state_valid",
        ),
        sa.CheckConstraint(
            "COALESCE(vat_tax_status_assertion_kind IS NULL AND vat_tax_status_value IS NULL, FALSE) "
            "OR COALESCE(vat_tax_status_assertion_kind = 'VALUE_ASSERTION' "
            "    AND vat_tax_status_value IN ('VAT_PAID', 'VAT_NOT_PAID', 'VAT_MARGIN_SCHEME', 'OTHER'), FALSE) "
            "OR COALESCE(vat_tax_status_assertion_kind = 'UNKNOWN' AND vat_tax_status_value IS NULL, FALSE)",
            name="nl_offer_rev_vat_tax_status_state_valid",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="nl_offer_rev_content_hash_sha256_length"
        ),
    )
    op.create_index(
        "ix_nl_offer_rev_native_listing_id",
        "native_listing_offer_revisions",
        ["native_listing_id"],
    )

    op.create_table(
        "native_listing_offer_heads",
        sa.Column(
            "native_listing_id",
            sa.Text(),
            sa.ForeignKey("native_listings.native_listing_id"),
            primary_key=True,
        ),
        sa.Column("current_offer_revision_id", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Composite FK (not a plain FK on current_offer_revision_id alone):
        # forces the referenced revision's own native_listing_id to equal
        # this row's native_listing_id, so heads.native_listing_id = A while
        # heads.current_offer_revision_id points at a revision belonging to
        # listing B is impossible in any DB-valid state.
        sa.ForeignKeyConstraint(
            ["native_listing_id", "current_offer_revision_id"],
            [
                "native_listing_offer_revisions.native_listing_id",
                "native_listing_offer_revisions.offer_revision_id",
            ],
            name="fk_nl_offer_heads_current_same_listing",
        ),
    )


def downgrade() -> None:
    op.drop_table("native_listing_offer_heads")
    op.drop_index("ix_nl_offer_rev_native_listing_id", table_name="native_listing_offer_revisions")
    op.drop_table("native_listing_offer_revisions")
