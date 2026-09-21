"""publishing_organization_public_display_name

Revision ID: 1a6de411f835
Revises: a05c7e9b1f34
Create Date: 2026-09-21 09:00:00.000000

SLICE-0063. Adds the bounded current presentation identity required by
`specs/PUBLISHING_ORGANIZATION_PUBLIC_IDENTITY_CONTRACT.v0.1.md` §3/§3.1:

    marketplace_organizations.public_display_name  -- TEXT NOT NULL

No second publisher identity table is introduced (contract §3): this is one
new column on the existing SLICE-0053 `marketplace_organizations` row.

Existing rows predate this column and must receive a deterministic local
backfill without any network/external lookup (contract §3.1's accepted
compatibility backfill is `public_display_name = organization_id`). This is
done in three steps because the backfill value is per-row, not a constant
`server_default`: add the column nullable, `UPDATE` every existing row to
its own `organization_id`, then tighten the column to `NOT NULL`. New rows
inserted after this migration always supply an explicit value through
`hullq.persistence.broker_identity.seed_marketplace_organization` (which
itself falls back to the Organization ID when the domain object's
`public_display_name` is `None`), so no `server_default` is needed going
forward either.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a6de411f835"
down_revision: str | None = "a05c7e9b1f34"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "marketplace_organizations",
        sa.Column("public_display_name", sa.Text(), nullable=True),
    )
    op.execute(
        "UPDATE marketplace_organizations "
        "SET public_display_name = organization_id "
        "WHERE public_display_name IS NULL"
    )
    op.alter_column("marketplace_organizations", "public_display_name", nullable=False)


def downgrade() -> None:
    op.drop_column("marketplace_organizations", "public_display_name")
