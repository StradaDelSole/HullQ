"""power_engine_count

Revision ID: b4f8e2a6c105
Revises: a3f7c1d2e4b9
Create Date: 2026-10-28 10:00:00.000000

SLICE-0094. Extends the existing `physical_boat_claim_revisions` immutable
claim-revision table (9c2e6b4a1d80, most recently extended a3f7c1d2e4b9 for
`power_drive_configuration`) in place with one new optional claim field:

    power_engine_count_assertion_kind / power_engine_count_value

Identical two-state shape to `power_drive_configuration`
(`VALUE_ASSERTION`/`UNKNOWN`, no `ABSENT`), but with a strictly typed
**integer** value bounded 1-32 rather than an enum vocabulary
(`hullq.domain.physical_boat_claims.PowerEngineCountClaim`) -- the first
bounded current-claim storage/authoring envelope
(`specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` "One field, one
meaning"). The narrower public Search filter whitelist (canonical tokens
1-8) is enforced at the Search/request layer, never here.

The new column pair is NULLable with no `server_default` other than NULL, so
every existing row reads back with the field cleanly omitted. Because
`hullq.persistence.physical_boat_claims._claim_envelope_dict` only adds a
`"power_engine_count"` key to the immutable-content fingerprint envelope
when that claim is actually present, an existing revision's stored
`content_hash` (computed before this migration) still matches the envelope
recomputed for its own exact retry after this migration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4f8e2a6c105"
down_revision: str | None = "a3f7c1d2e4b9"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("power_engine_count_assertion_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "physical_boat_claim_revisions",
        sa.Column("power_engine_count_value", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "pb_claim_rev_power_engine_count_state_valid",
        "physical_boat_claim_revisions",
        "COALESCE(power_engine_count_assertion_kind IS NULL "
        "    AND power_engine_count_value IS NULL, FALSE) "
        "OR COALESCE(power_engine_count_assertion_kind = 'VALUE_ASSERTION' "
        "    AND power_engine_count_value BETWEEN 1 AND 32, FALSE) "
        "OR COALESCE(power_engine_count_assertion_kind = 'UNKNOWN' "
        "    AND power_engine_count_value IS NULL, FALSE)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "pb_claim_rev_power_engine_count_state_valid",
        "physical_boat_claim_revisions",
        type_="check",
    )
    op.drop_column("physical_boat_claim_revisions", "power_engine_count_value")
    op.drop_column("physical_boat_claim_revisions", "power_engine_count_assertion_kind")
