"""professional_listing_draft

Revision ID: a05c7e9b1f34
Revises: f1a9c02d5e83
Create Date: 2026-09-20 09:00:00.000000

SLICE-0061. Adds the single dedicated durable aggregate required by
`specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md` §6: one private,
mutable, pre-market professional listing draft workspace owned by one
`marketplace_organizations` Organization (SLICE-0053 actor directory).

    professional_listing_drafts   -- professional_listing_draft_id,
                                      owner_organization_id,
                                      created_by_account_id,
                                      broker_listing_reference, payload,
                                      version, created_at, updated_at

Per contract §6, `professional_listing_draft_id` is TEXT (matching the
existing `AccountId`/`MarketplaceOrganizationId`/`OwnerDirectListingDraftId`
wrapper convention: exact UUID version is an implementation detail, not a
schema-level choice). `owner_organization_id` is a real foreign key into
`marketplace_organizations` -- the authoritative ownership boundary (contract
§3.1) -- and `created_by_account_id` is a real foreign key into `accounts`,
audit metadata only, never the ownership boundary. Per contract §6/§11, this
migration adds NO foreign key and NO column at all referencing
`native_listings`, `physical_boats` or `market_episodes`: a professional
draft is pre-market workspace state, not marketplace inventory, and must
remain structurally incapable of being joined into those tables as if it
already were.

`payload` is JSONB (acceptable here only because the API/domain validator in
`hullq.domain.listing_draft_payload` enforces the finite v0.1 key set and
value shapes -- this is not a schemaless-blob license, mirroring the
accepted `owner_direct_listing_drafts` design). `broker_listing_reference` is
a nullable plain TEXT column, professional-only metadata (contract §5) --
deliberately not part of the JSONB payload, so it can be read/indexed
without depending on the payload's internal shape. `version` is a plain
positive integer, compared-and-incremented by one atomic
`UPDATE ... WHERE version = expected_version` statement in
`hullq.persistence.professional_listing_draft` (contract §7) -- no separate
locking/versioning table is needed for that.

The composite index below supports the contract §7/§9 bounded, deterministic
`updated_at DESC, professional_listing_draft_id ASC` keyset list, scoped to
one `owner_organization_id` -- mirroring
`f1a9c02d5e83_native_listing_inventory_index`'s identical rationale for the
Organization inventory read.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a05c7e9b1f34"
down_revision: str | None = "f1a9c02d5e83"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "professional_listing_drafts",
        sa.Column("professional_listing_draft_id", sa.Text(), primary_key=True),
        sa.Column(
            "owner_organization_id",
            sa.Text(),
            sa.ForeignKey(
                "marketplace_organizations.organization_id",
                name="fk_professional_listing_drafts_owner_organization_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_by_account_id",
            sa.Text(),
            sa.ForeignKey(
                "accounts.account_id", name="fk_professional_listing_drafts_created_by_account_id"
            ),
            nullable=False,
        ),
        sa.Column("broker_listing_reference", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("version > 0", name="ck_professional_listing_drafts_version_positive"),
    )
    op.create_index(
        "ix_professional_listing_drafts_org_updated_id",
        "professional_listing_drafts",
        ["owner_organization_id", sa.text("updated_at DESC"), "professional_listing_draft_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_professional_listing_drafts_org_updated_id",
        table_name="professional_listing_drafts",
    )
    op.drop_table("professional_listing_drafts")
