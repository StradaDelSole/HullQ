"""power_drive_configuration

Revision ID: a3f7c1d2e4b9
Revises: e91a4c7d0f3b
Create Date: 2026-10-28 09:00:00.000000

SLICE-0093. Extends the existing `physical_boat_claim_revisions` immutable
claim-revision table (9c2e6b4a1d80, most recently extended e91a4c7d0f3b for
`vessel_category`) in place with one new optional claim field:

    power_drive_configuration_assertion_kind / power_drive_configuration_value

Identical two-state shape to `hull_material`/`vessel_category`
(`VALUE_ASSERTION`/`UNKNOWN`, no `ABSENT`), with the bounded seven-value
broker claim vocabulary `SHAFT`/`STERNDRIVE`/`POD`/`WATERJET`/`OUTBOARD`/
`MIXED`/`OTHER` (`hullq.domain.physical_boat_claims.PowerDriveConfiguration`)
-- broader than the five public Search filter tokens the companion
`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md` authorizes.

The new column pair is NULLable with no `server_default` other than NULL, so
every existing row reads back with the field cleanly omitted. Because
`hullq.persistence.physical_boat_claims._claim_envelope_dict` only adds a
`"power_drive_configuration"` key to the immutable-content fingerprint
envelope when that claim is actually present, an existing revision's stored
`content_hash` (computed before this migration) still matches the envelope
recomputed for its own exact retry after this migration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7c1d2e4b9"
down_revision: str | None = "e91a4c7d0f3b"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_POWER_DRIVE_CONFIGURATION_VALUES = (
    "SHAFT",
    "STERNDRIVE",
    "POD",
    "WATERJET",
    "OUTBOARD",
    "MIXED",
    "OTHER",
)
_ASSERTION_KIND_VALUES = ("VALUE_ASSERTION", "UNKNOWN")


def upgrade() -> None:
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("power_drive_configuration_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("power_drive_configuration_value", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_power_drive_configuration_state_valid",
        "physical_boat_claim_revisions",
        "COALESCE(power_drive_configuration_assertion_kind IS NULL "
        "    AND power_drive_configuration_value IS NULL, FALSE) "
        "OR COALESCE(power_drive_configuration_assertion_kind = 'VALUE_ASSERTION' "
        f"    AND power_drive_configuration_value IN {_POWER_DRIVE_CONFIGURATION_VALUES!r}, FALSE) "
        "OR COALESCE(power_drive_configuration_assertion_kind = 'UNKNOWN' "
        "    AND power_drive_configuration_value IS NULL, FALSE)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "pb_claim_rev_power_drive_configuration_state_valid",
        "physical_boat_claim_revisions",
        type_="check",
    )
    op.drop_column("physical_boat_claim_revisions", "power_drive_configuration_value")
    op.drop_column("physical_boat_claim_revisions", "power_drive_configuration_assertion_kind")
