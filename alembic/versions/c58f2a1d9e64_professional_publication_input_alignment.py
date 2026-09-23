"""professional_publication_input_alignment

Revision ID: c58f2a1d9e64
Revises: 1a6de411f835
Create Date: 2026-09-23 09:00:00.000000

SLICE-0065. Closes the two repository-proven data-shape gaps that block a
later lossless professional-draft-to-marketplace promotion
(`specs/PROFESSIONAL_PUBLICATION_INPUT_ALIGNMENT_CONTRACT.v0.1.md`):

1. ``professional_listing_drafts`` gains a nullable ``broker_description``
   TEXT column -- professional-only pre-market input for the wire key
   ``listing_offer.broker_description``, mirroring the existing
   ``broker_listing_reference`` column's shape exactly (a dedicated nullable
   TEXT column outside the JSONB ``payload``, no non-blank CHECK at the DB
   layer -- trim/non-empty-when-present is enforced by
   `hullq.domain.professional_listing_draft` before this column is ever
   written, exactly like ``broker_listing_reference`` today). This migration
   adds no column/FK referencing ``native_listings``/``physical_boats``/
   ``market_episodes``: a professional draft remains pre-market workspace
   state, never marketplace inventory (contract §2).

2. ``physical_boat_claim_revisions`` gains an optional
   ``boat_name_assertion_kind``/``boat_name_value`` column pair, extending
   the existing SLICE-0050 immutable claim-revision model in place -- no new
   boat-name table (contract §7). The CHECK constraint mirrors this table's
   existing per-field enumeration-of-every-valid-state pattern (see
   9c2e6b4a1d80's docstring for the COALESCE(...,FALSE) rationale), except
   ``boat_name`` additionally allows the SLICE-0065 ``ABSENT`` assertion kind
   (contract §6): a concrete boat may genuinely carry no name, distinct from
   ``UNKNOWN`` (not asked/not known) and from the column pair simply being
   NULL (never asked at all).

Both new columns are NULLable and added without a ``server_default`` other
than NULL, so every existing row -- every current professional draft and
every pre-0065 claim revision -- reads back with the new field cleanly
omitted, never a synthesized value. Because
`hullq.persistence.physical_boat_claims._claim_envelope_dict` only adds a
``"boat_name"`` key to the immutable-content fingerprint envelope when a
boat-name claim is actually present, an existing revision's stored
``content_hash`` (computed before this migration, over an envelope that
never had a ``boat_name`` key at all) still matches the envelope recomputed
for its own exact retry after this migration -- this migration does not
itself touch ``content_hash``; it only makes the column pair available for
the application layer to read/write.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c58f2a1d9e64"
down_revision: str | None = "1a6de411f835"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Identical to the set used by 4d8e1a72c9f0_native_listing_offer_facts.py and
# 9c2e6b4a1d80_physical_boat_claim_facts.py -- see those migrations for the
# full PostgreSQL-locale rationale for enumerating Python's exact
# str.isspace() codepoints rather than relying on PostgreSQL's own,
# locale-dependent whitespace notion.
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
    exact Python str.isspace() whitespace set -- i.e. is not blank under the
    same rule the domain layer's str.strip()-based check applies."""
    return f"{column} ~ '[^{_PYTHON_WHITESPACE_REGEX_CLASS}]'"


def upgrade() -> None:
    op.add_column(
        "professional_listing_drafts",
        sa.Column("broker_description", sa.Text(), nullable=True),
    )

    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("boat_name_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("boat_name_value", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_boat_name_state_valid",
        "physical_boat_claim_revisions",
        "COALESCE(boat_name_assertion_kind IS NULL AND boat_name_value IS NULL, FALSE) "
        "OR COALESCE(boat_name_assertion_kind = 'VALUE_ASSERTION' "
        f"    AND boat_name_value IS NOT NULL AND {_non_blank_predicate('boat_name_value')}, FALSE) "
        "OR COALESCE(boat_name_assertion_kind IN ('ABSENT', 'UNKNOWN') "
        "    AND boat_name_value IS NULL, FALSE)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "pb_claim_rev_boat_name_state_valid",
        "physical_boat_claim_revisions",
        type_="check",
    )
    op.drop_column("physical_boat_claim_revisions", "boat_name_value")
    op.drop_column("physical_boat_claim_revisions", "boat_name_assertion_kind")
    op.drop_column("professional_listing_drafts", "broker_description")
