"""broker_actor_directory

Revision ID: b3e7f1a94c02
Revises: 7d4b1a9e3f26
Create Date: 2026-09-14 12:00:00.000000

SLICE-0053. Adds the durable marketplace actor directory required by
`specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md` §5/§15:

    accounts                     -- immutable HullQ Account identity
    auth_identities               -- (provider, issuer, subject) -> account_id
    marketplace_organizations     -- durable Organization principal, SLICE-0041
                                      ProfessionalCategory/OrganizationPublishingEligibility
    organization_memberships      -- account_id <-> organization_id, ACTIVE/INACTIVE
    organization_membership_roles -- composable MembershipRole set per membership

All ID columns are `TEXT`, matching the existing `AccountId`/
`MarketplaceOrganizationId` wrapper convention (see
`native_listings.created_by_account_id` /
`native_listings.publishing_organization_id`) -- exact UUID version is an
implementation detail, not a schema-level choice.

Per contract §5.1, this migration deliberately adds NO foreign key from the
pre-existing `native_listings.created_by_account_id` /
`native_listings.publishing_organization_id` columns into this new actor
directory: those columns predate the directory and carry accepted
historical/synthetic identifiers that must not be forced to resolve into it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e7f1a94c02"
down_revision: str | None = "7d4b1a9e3f26"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.Text(), primary_key=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "auth_identities",
        sa.Column("auth_identity_id", sa.Text(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Text(),
            sa.ForeignKey("accounts.account_id", name="fk_auth_identities_account_id"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "provider", "issuer", "subject", name="uq_auth_identities_provider_issuer_subject"
        ),
    )
    op.create_index(
        "ix_auth_identities_account_id", "auth_identities", ["account_id"], unique=False
    )

    op.create_table(
        "marketplace_organizations",
        sa.Column("organization_id", sa.Text(), primary_key=True),
        sa.Column("professional_category", sa.Text(), nullable=False),
        sa.Column("publishing_eligibility", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "organization_memberships",
        sa.Column("membership_id", sa.Text(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Text(),
            sa.ForeignKey("accounts.account_id", name="fk_org_memberships_account_id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Text(),
            sa.ForeignKey(
                "marketplace_organizations.organization_id",
                name="fk_org_memberships_organization_id",
            ),
            nullable=False,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "account_id", "organization_id", name="uq_org_memberships_account_organization"
        ),
    )
    op.create_index(
        "ix_org_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "organization_membership_roles",
        sa.Column(
            "membership_id",
            sa.Text(),
            sa.ForeignKey(
                "organization_memberships.membership_id",
                name="fk_org_membership_roles_membership_id",
            ),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "membership_id", "role", name="uq_org_membership_roles_membership_role"
        ),
    )


def downgrade() -> None:
    op.drop_table("organization_membership_roles")
    op.drop_index("ix_org_memberships_organization_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_table("marketplace_organizations")
    op.drop_index("ix_auth_identities_account_id", table_name="auth_identities")
    op.drop_table("auth_identities")
    op.drop_table("accounts")
