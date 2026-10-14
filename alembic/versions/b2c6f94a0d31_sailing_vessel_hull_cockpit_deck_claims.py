"""sailing_vessel_hull_cockpit_deck_claims

Revision ID: b2c6f94a0d31
Revises: a71d4f8c2e93
Create Date: 2026-10-14 09:00:00.000000

SLICE-0086. Extends the existing `physical_boat_claim_revisions` immutable
claim-revision table (9c2e6b4a1d80, extended c58f2a1d9e64 for `boat_name`) in
place with three new optional categorical claim fields, mirroring those two
migrations' exact per-field `assertion_kind`/`value` column-pair + CHECK
constraint shape:

    hull_configuration_assertion_kind / hull_configuration_value
    cockpit_position_assertion_kind / cockpit_position_value
    deck_saloon_assertion_kind / deck_saloon_value

Each new field allows only `VALUE_ASSERTION`/`UNKNOWN` (no `ABSENT` -- unlike
`boat_name`, the Owner-confirmed SLICE-0086 vocabulary never adds a separate
assertion_kind for "known absence"; `NONE`/`OTHER` are ordinary
VALUE_ASSERTION enum members of `deck_saloon`/`hull_configuration`/
`cockpit_position` themselves, exactly like `KeelConfiguration.OTHER`/
`RudderConfiguration.OTHER` already are for the existing two configuration
fields). Every CHECK mirrors 9c2e6b4a1d80's exact
`COALESCE(..., FALSE) OR COALESCE(..., FALSE) OR COALESCE(..., FALSE)` shape
(never a NULL-propagating equality form) for the identical reason recorded
there: a NULL `assertion_kind` must not vacuously satisfy an equality-shaped
constraint.

All six new columns are NULLable with no `server_default` other than NULL, so
every existing row reads back with the new fields cleanly omitted, never a
synthesized value -- mirrors c58f2a1d9e64. Because
`hullq.persistence.physical_boat_claims._claim_envelope_dict` only adds a
`"hull_configuration"`/`"cockpit_position"`/`"deck_saloon"` key to the
immutable-content fingerprint envelope when that claim is actually present,
an existing revision's stored `content_hash` (computed before this migration)
still matches the envelope recomputed for its own exact retry after this
migration -- this migration does not itself touch `content_hash`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c6f94a0d31"
down_revision: str | None = "a71d4f8c2e93"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_HULL_CONFIGURATION_VALUES = ("MONOHULL", "CATAMARAN", "TRIMARAN", "OTHER")
_COCKPIT_POSITION_VALUES = ("AFT", "CENTER", "FORWARD", "MULTIPLE", "OTHER")
_DECK_SALOON_VALUES = ("NONE", "DECK_SALOON", "PILOTHOUSE")


def _state_check(column_prefix: str, allowed_values: tuple[str, ...]) -> str:
    """The shared per-field CHECK shape (see this migration's docstring) --
    one explicit enumeration of every valid `(assertion_kind, value)` state,
    each branch wrapped in `COALESCE(..., FALSE)` so a NULL `assertion_kind`
    cannot vacuously satisfy any branch."""
    kind_col = f"{column_prefix}_assertion_kind"
    value_col = f"{column_prefix}_value"
    return (
        f"COALESCE({kind_col} IS NULL AND {value_col} IS NULL, FALSE) "
        f"OR COALESCE({kind_col} = 'VALUE_ASSERTION' "
        f"    AND {value_col} IN {allowed_values!r}, FALSE) "
        f"OR COALESCE({kind_col} = 'UNKNOWN' AND {value_col} IS NULL, FALSE)"
    )


def upgrade() -> None:
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("hull_configuration_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("hull_configuration_value", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_hull_configuration_state_valid",
        "physical_boat_claim_revisions",
        _state_check("hull_configuration", _HULL_CONFIGURATION_VALUES),
    )

    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("cockpit_position_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("cockpit_position_value", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_cockpit_position_state_valid",
        "physical_boat_claim_revisions",
        _state_check("cockpit_position", _COCKPIT_POSITION_VALUES),
    )

    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("deck_saloon_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("deck_saloon_value", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_deck_saloon_state_valid",
        "physical_boat_claim_revisions",
        _state_check("deck_saloon", _DECK_SALOON_VALUES),
    )


def downgrade() -> None:
    op.drop_constraint(
        "pb_claim_rev_deck_saloon_state_valid", "physical_boat_claim_revisions", type_="check"
    )
    op.drop_column("physical_boat_claim_revisions", "deck_saloon_value")
    op.drop_column("physical_boat_claim_revisions", "deck_saloon_assertion_kind")

    op.drop_constraint(
        "pb_claim_rev_cockpit_position_state_valid", "physical_boat_claim_revisions", type_="check"
    )
    op.drop_column("physical_boat_claim_revisions", "cockpit_position_value")
    op.drop_column("physical_boat_claim_revisions", "cockpit_position_assertion_kind")

    op.drop_constraint(
        "pb_claim_rev_hull_configuration_state_valid",
        "physical_boat_claim_revisions",
        type_="check",
    )
    op.drop_column("physical_boat_claim_revisions", "hull_configuration_value")
    op.drop_column("physical_boat_claim_revisions", "hull_configuration_assertion_kind")
