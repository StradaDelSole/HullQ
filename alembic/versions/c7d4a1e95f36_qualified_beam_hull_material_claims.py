"""qualified_beam_hull_material_claims

Revision ID: c7d4a1e95f36
Revises: b2c6f94a0d31
Create Date: 2026-10-15 09:00:00.000000

SLICE-0087. Extends the existing `physical_boat_claim_revisions` immutable
claim-revision table (9c2e6b4a1d80, extended c58f2a1d9e64 for `boat_name`,
extended b2c6f94a0d31 for `hull_configuration`/`cockpit_position`/
`deck_saloon`) in place with two new optional claim fields:

    beam_assertion_kind / beam_value
    hull_material_assertion_kind / hull_material_value

`beam` mirrors `loa_length`/`draft`'s exact unconstrained ``NUMERIC``
(arbitrary precision, never binary floating point) shape and CHECK rule --
``VALUE_ASSERTION`` requires a non-NaN/non-Infinity positive value,
``UNKNOWN`` requires a NULL value, and the whole column pair may be NULL
(field omitted entirely). `hull_material` mirrors `hull_configuration`/
`cockpit_position`/`deck_saloon`'s categorical shape, but with the existing
marketplace registry's full seven-value actual-boat claim vocabulary
(``GRP_FIBERGLASS``/``STEEL``/``ALUMINUM``/``WOOD``/``FERROCEMENT``/
``CARBON_COMPOSITE``/``OTHER``) -- broader than the four public Search
filter tokens this slice authorizes, since a broker may truthfully assert a
material this slice's bounded public filter does not expose.

Both new fields allow only `VALUE_ASSERTION`/`UNKNOWN` (no `ABSENT`) --
identical two-state shape to every other optional claim field added since
9c2e6b4a1d80.

Both new columns are NULLable with no `server_default` other than NULL, so
every existing row reads back with the new fields cleanly omitted, never a
synthesized value -- mirrors b2c6f94a0d31. Because
`hullq.persistence.physical_boat_claims._claim_envelope_dict` only adds a
`"beam"`/`"hull_material"` key to the immutable-content fingerprint envelope
when that claim is actually present, an existing revision's stored
`content_hash` (computed before this migration) still matches the envelope
recomputed for its own exact retry after this migration -- this migration
does not itself touch `content_hash`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d4a1e95f36"
down_revision: str | None = "b2c6f94a0d31"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_HULL_MATERIAL_VALUES = (
    "GRP_FIBERGLASS",
    "STEEL",
    "ALUMINUM",
    "WOOD",
    "FERROCEMENT",
    "CARBON_COMPOSITE",
    "OTHER",
)


def upgrade() -> None:
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("beam_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("beam_value", sa.Numeric(), nullable=True),
    )
    # Mirrors 9c2e6b4a1d80's loa_length/draft CHECK shape exactly: a
    # VALUE_ASSERTION value must be non-NULL, contain no letters (rejecting
    # PostgreSQL 14+ NUMERIC's NaN/Infinity/-Infinity textual forms) and be
    # strictly positive.
    op.create_check_constraint(
        "pb_claim_rev_beam_state_valid",
        "physical_boat_claim_revisions",
        "COALESCE(beam_assertion_kind IS NULL AND beam_value IS NULL, FALSE) "
        "OR COALESCE(beam_assertion_kind = 'VALUE_ASSERTION' "
        "    AND beam_value IS NOT NULL AND beam_value::text !~ '[A-Za-z]' "
        "    AND beam_value > 0, FALSE) "
        "OR COALESCE(beam_assertion_kind = 'UNKNOWN' AND beam_value IS NULL, FALSE)",
    )

    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("hull_material_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("hull_material_value", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_hull_material_state_valid",
        "physical_boat_claim_revisions",
        "COALESCE(hull_material_assertion_kind IS NULL AND hull_material_value IS NULL, FALSE) "
        "OR COALESCE(hull_material_assertion_kind = 'VALUE_ASSERTION' "
        f"    AND hull_material_value IN {_HULL_MATERIAL_VALUES!r}, FALSE) "
        "OR COALESCE(hull_material_assertion_kind = 'UNKNOWN' "
        "    AND hull_material_value IS NULL, FALSE)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "pb_claim_rev_hull_material_state_valid", "physical_boat_claim_revisions", type_="check"
    )
    op.drop_column("physical_boat_claim_revisions", "hull_material_value")
    op.drop_column("physical_boat_claim_revisions", "hull_material_assertion_kind")

    op.drop_constraint(
        "pb_claim_rev_beam_state_valid", "physical_boat_claim_revisions", type_="check"
    )
    op.drop_column("physical_boat_claim_revisions", "beam_value")
    op.drop_column("physical_boat_claim_revisions", "beam_assertion_kind")
