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
``NUMERIC`` (arbitrary precision, never binary floating point). Country/
currency CHECK constraints enforce normalized code *shape*
(ISO 3166-1 alpha-2 / ISO 4217, uppercase) as belt-and-suspenders alongside
the domain-layer validation in ``hullq.domain.native_listing_offer`` — they
do not by themselves prove membership in the real ISO code lists.
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
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
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
        sa.CheckConstraint(
            "location_region_assertion_kind IS NULL "
            "OR location_region_assertion_kind IN ('VALUE_ASSERTION', 'UNKNOWN')",
            name="nl_offer_rev_location_region_kind_valid",
        ),
        sa.CheckConstraint(
            "(location_region_assertion_kind = 'VALUE_ASSERTION') = (location_region_value IS NOT NULL)",
            name="nl_offer_rev_location_region_value_matches_kind",
        ),
        sa.CheckConstraint(
            "broker_summary_assertion_kind IS NULL "
            "OR broker_summary_assertion_kind IN ('VALUE_ASSERTION', 'NOT_APPLICABLE')",
            name="nl_offer_rev_broker_summary_kind_valid",
        ),
        sa.CheckConstraint(
            "(broker_summary_assertion_kind = 'VALUE_ASSERTION') = (broker_summary_value IS NOT NULL)",
            name="nl_offer_rev_broker_summary_value_matches_kind",
        ),
        sa.CheckConstraint(
            "known_history_narrative_assertion_kind IS NULL "
            "OR known_history_narrative_assertion_kind IN "
            "   ('VALUE_ASSERTION', 'NO_KNOWN_HISTORY_DECLARED', 'UNKNOWN')",
            name="nl_offer_rev_known_history_kind_valid",
        ),
        sa.CheckConstraint(
            "(known_history_narrative_assertion_kind = 'VALUE_ASSERTION') "
            "= (known_history_narrative_value IS NOT NULL)",
            name="nl_offer_rev_known_history_value_matches_kind",
        ),
        sa.CheckConstraint(
            "vat_tax_status_assertion_kind IS NULL "
            "OR vat_tax_status_assertion_kind IN ('VALUE_ASSERTION', 'UNKNOWN')",
            name="nl_offer_rev_vat_tax_status_kind_valid",
        ),
        sa.CheckConstraint(
            "(vat_tax_status_assertion_kind = 'VALUE_ASSERTION') = (vat_tax_status_value IS NOT NULL)",
            name="nl_offer_rev_vat_tax_status_value_matches_kind",
        ),
        sa.CheckConstraint(
            "vat_tax_status_value IS NULL "
            "OR vat_tax_status_value IN ('VAT_PAID', 'VAT_NOT_PAID', 'VAT_MARGIN_SCHEME', 'OTHER')",
            name="nl_offer_rev_vat_tax_status_value_valid",
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
        sa.Column(
            "current_offer_revision_id",
            sa.Text(),
            sa.ForeignKey("native_listing_offer_revisions.offer_revision_id"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("native_listing_offer_heads")
    op.drop_index("ix_nl_offer_rev_native_listing_id", table_name="native_listing_offer_revisions")
    op.drop_table("native_listing_offer_revisions")
