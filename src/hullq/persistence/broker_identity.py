"""Durable marketplace actor directory persistence — SLICE-0053.

Implements the durable-state half of
`specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`: JIT `(provider, issuer,
subject) -> HullQ AccountId` mapping (§4/§8), and read/seed access to the
Organization/Membership/role directory (§5) that
`hullq.domain.broker_access.evaluate_organization_workspace_authorization`
decides against.

Organization/membership *creation* here is an internal/test seeding
surface only (SLICE-0053 explicitly excludes self-service Organization
creation and membership administration from any HullQ-facing API); the only
externally reachable write path in this module is the JIT account mapping
performed once, atomically, on first successful authentication.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from hullq.domain.broker_access import Provider
from hullq.domain.organization_display_name import normalize_public_display_name
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
)

__all__ = [
    "JitAccountMappingResult",
    "fetch_active_memberships_for_account",
    "fetch_marketplace_organization",
    "fetch_membership_for_account_and_organization",
    "get_or_create_account_for_identity",
    "seed_marketplace_organization",
    "seed_organization_membership",
    "update_marketplace_organization_display_name",
    "update_membership_state",
]


@dataclass(frozen=True)
class JitAccountMappingResult:
    """Outcome of one `get_or_create_account_for_identity` call."""

    account_id: AccountId
    created: bool


_SELECT_ACCOUNT_FOR_IDENTITY = (
    "SELECT account_id FROM auth_identities WHERE provider = %s AND issuer = %s AND subject = %s"
)
_INSERT_ACCOUNT = "INSERT INTO accounts (account_id) VALUES (%s)"
_INSERT_AUTH_IDENTITY = (
    "INSERT INTO auth_identities (auth_identity_id, account_id, provider, issuer, subject) "
    "VALUES (%s, %s, %s, %s, %s)"
)
_ADVISORY_LOCK = "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))"


def get_or_create_account_for_identity(
    conn: Any, *, provider: Provider, issuer: str, subject: str
) -> JitAccountMappingResult:
    """Atomically resolve `(provider, issuer, subject)` to one HullQ Account.

    First admissible unknown identity creates exactly one Account +
    AuthIdentity row (contract §8). Concurrent/retried first logins for the
    identical identity converge on the same Account: this function takes a
    transaction-scoped PostgreSQL advisory lock keyed on the exact
    `(provider, issuer, subject)` tuple before checking for an existing
    mapping, so a losing concurrent caller blocks until the winner commits
    and then observes the winner's row -- no orphan Account row is ever
    created on the losing path, and no duplicate mapping is possible.

    Email is never consulted or used to link identities: this function has
    no email parameter at all.

    The caller owns the transaction: this function does not commit or
    rollback *conn*.
    """
    if not isinstance(provider, Provider):
        raise TypeError(f"provider must be a Provider, got {type(provider).__name__}")
    if not issuer:
        raise ValueError("issuer must be non-empty")
    if not subject:
        raise ValueError("subject must be non-empty")

    lock_key = f"{provider.value}|{issuer}|{subject}"
    with conn.cursor() as cur:
        cur.execute(_ADVISORY_LOCK, [lock_key])

        cur.execute(_SELECT_ACCOUNT_FOR_IDENTITY, [provider.value, issuer, subject])
        row = cur.fetchone()
        if row is not None:
            return JitAccountMappingResult(account_id=AccountId(row[0]), created=False)

        new_account_id = str(uuid.uuid4())
        new_auth_identity_id = str(uuid.uuid4())
        cur.execute(_INSERT_ACCOUNT, [new_account_id])
        cur.execute(
            _INSERT_AUTH_IDENTITY,
            [new_auth_identity_id, new_account_id, provider.value, issuer, subject],
        )
        return JitAccountMappingResult(account_id=AccountId(new_account_id), created=True)


# ---------------------------------------------------------------------------
# Organization / membership directory -- internal seeding + read access
# ---------------------------------------------------------------------------

_UPSERT_ORGANIZATION = """
INSERT INTO marketplace_organizations
    (organization_id, professional_category, publishing_eligibility, public_display_name)
VALUES (%s, %s, %s, %s)
ON CONFLICT (organization_id) DO UPDATE
    SET professional_category = EXCLUDED.professional_category,
        publishing_eligibility = EXCLUDED.publishing_eligibility,
        public_display_name = EXCLUDED.public_display_name
"""

_SELECT_ORGANIZATION = (
    "SELECT organization_id, professional_category, publishing_eligibility, public_display_name "
    "FROM marketplace_organizations WHERE organization_id = %s"
)

_UPDATE_ORGANIZATION_DISPLAY_NAME = (
    "UPDATE marketplace_organizations SET public_display_name = %s WHERE organization_id = %s"
)

_UPSERT_MEMBERSHIP = """
INSERT INTO organization_memberships (membership_id, account_id, organization_id, state)
VALUES (%s, %s, %s, %s)
ON CONFLICT (account_id, organization_id) DO UPDATE
    SET state = EXCLUDED.state
RETURNING membership_id
"""

_DELETE_MEMBERSHIP_ROLES = "DELETE FROM organization_membership_roles WHERE membership_id = %s"
_INSERT_MEMBERSHIP_ROLE = (
    "INSERT INTO organization_membership_roles (membership_id, role) VALUES (%s, %s)"
)
_UPDATE_MEMBERSHIP_STATE = "UPDATE organization_memberships SET state = %s WHERE membership_id = %s"

_SELECT_MEMBERSHIP_FOR_ACCOUNT_ORG = """
SELECT membership_id, state
FROM organization_memberships
WHERE account_id = %s AND organization_id = %s
"""

_SELECT_ROLES_FOR_MEMBERSHIP = (
    "SELECT role FROM organization_membership_roles WHERE membership_id = %s"
)

_SELECT_ACTIVE_MEMBERSHIPS_FOR_ACCOUNT = """
SELECT m.membership_id, m.organization_id, m.state
FROM organization_memberships m
WHERE m.account_id = %s AND m.state = 'ACTIVE'
"""


def seed_marketplace_organization(conn: Any, organization: MarketplaceOrganization) -> None:
    """Idempotently write/replace one Organization's durable directory row.

    Internal seeding helper only -- SLICE-0053 has no self-service
    Organization-creation API. The caller owns transaction commit.

    SLICE-0063: `organization.public_display_name` is written verbatim when
    explicit; when `None`, the persisted column falls back to the
    Organization ID (contract §3.1's accepted compatibility backfill), so
    the durable column is never null even for an internal/test-seeded
    Organization that never specified a display name.
    """
    if not isinstance(organization, MarketplaceOrganization):
        raise TypeError(
            f"organization must be a MarketplaceOrganization, got {type(organization).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(
            _UPSERT_ORGANIZATION,
            [
                organization.id.value,
                organization.professional_category.value,
                organization.publishing_eligibility.value,
                organization.resolved_public_display_name,
            ],
        )


def fetch_marketplace_organization(
    conn: Any, organization_id: MarketplaceOrganizationId
) -> MarketplaceOrganization | None:
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "organization_id must be a MarketplaceOrganizationId, "
            f"got {type(organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_ORGANIZATION, [organization_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    org_id_value, professional_category_value, publishing_eligibility_value, display_name_value = (
        row
    )
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id_value),
        professional_category=ProfessionalCategory(professional_category_value),
        publishing_eligibility=OrganizationPublishingEligibility(publishing_eligibility_value),
        public_display_name=display_name_value,
    )


def update_marketplace_organization_display_name(
    conn: Any, organization_id: MarketplaceOrganizationId, display_name: str
) -> None:
    """Change only the current presentation `public_display_name`.

    Contract §2/Required Behavior §G: this touches exactly one column on
    the existing `marketplace_organizations` row -- it never creates a
    second Organization identity and has no reachable path to any
    NativeListing identity/content/lifecycle/offer table. The caller owns
    transaction commit.
    """
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "organization_id must be a MarketplaceOrganizationId, "
            f"got {type(organization_id).__name__}"
        )
    normalized = normalize_public_display_name(display_name)
    with conn.cursor() as cur:
        cur.execute(_UPDATE_ORGANIZATION_DISPLAY_NAME, [normalized, organization_id.value])


def seed_organization_membership(conn: Any, membership: OrganizationMembership) -> None:
    """Idempotently write/replace one OrganizationMembership + its roles.

    Internal seeding helper only -- SLICE-0053 has no self-service
    membership-administration API. Replaces the exact `membership.id` for
    the `(account_id, organization_id)` pair and its full role set. The
    caller owns transaction commit.
    """
    if not isinstance(membership, OrganizationMembership):
        raise TypeError(
            f"membership must be an OrganizationMembership, got {type(membership).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(
            _UPSERT_MEMBERSHIP,
            [
                membership.id.value,
                membership.account_id.value,
                membership.organization_id.value,
                membership.state.value,
            ],
        )
        row = cur.fetchone()
        assert row is not None
        membership_id_value = row[0]
        cur.execute(_DELETE_MEMBERSHIP_ROLES, [membership_id_value])
        for role in membership.roles:
            cur.execute(_INSERT_MEMBERSHIP_ROLE, [membership_id_value, role.value])


def update_membership_state(
    conn: Any, membership_id: OrganizationMembershipId, state: MembershipState
) -> None:
    """Change one existing membership's ACTIVE/INACTIVE state.

    Used to demonstrate contract §9/§D: a membership/role change must alter
    the *next* authorization read without any provider-side action.
    """
    if not isinstance(membership_id, OrganizationMembershipId):
        raise TypeError(
            f"membership_id must be an OrganizationMembershipId, got {type(membership_id).__name__}"
        )
    if not isinstance(state, MembershipState):
        raise TypeError(f"state must be a MembershipState, got {type(state).__name__}")
    with conn.cursor() as cur:
        cur.execute(_UPDATE_MEMBERSHIP_STATE, [state.value, membership_id.value])


def _load_roles(conn: Any, membership_id: str) -> frozenset[MembershipRole]:
    with conn.cursor() as cur:
        cur.execute(_SELECT_ROLES_FOR_MEMBERSHIP, [membership_id])
        return frozenset(MembershipRole(row[0]) for row in cur.fetchall())


def fetch_membership_for_account_and_organization(
    conn: Any, account_id: AccountId, organization_id: MarketplaceOrganizationId
) -> OrganizationMembership | None:
    """Read current membership truth for one exact `(account, Organization)` pair.

    Returns `None` when no membership row exists at all (contract §9
    "missing membership"). An existing INACTIVE row is returned, not
    hidden, so callers can distinguish NO_MEMBERSHIP from
    MEMBERSHIP_INACTIVE internally while still collapsing both to the same
    external non-enumerating failure shape.
    """
    if not isinstance(account_id, AccountId):
        raise TypeError(f"account_id must be an AccountId, got {type(account_id).__name__}")
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "organization_id must be a MarketplaceOrganizationId, "
            f"got {type(organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_MEMBERSHIP_FOR_ACCOUNT_ORG, [account_id.value, organization_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    membership_id_value, state_value = row
    roles = _load_roles(conn, membership_id_value)
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id_value),
        account_id=account_id,
        organization_id=organization_id,
        roles=roles,
        state=MembershipState(state_value),
    )


def fetch_active_memberships_for_account(
    conn: Any, account_id: AccountId
) -> list[OrganizationMembership]:
    """Read every ACTIVE membership currently held by *account_id*.

    Used to build the SLICE-0053 "authorized Organization choices" list
    (contract §11): a caller with zero rows here has no Organization
    workspace context at all.
    """
    if not isinstance(account_id, AccountId):
        raise TypeError(f"account_id must be an AccountId, got {type(account_id).__name__}")
    with conn.cursor() as cur:
        cur.execute(_SELECT_ACTIVE_MEMBERSHIPS_FOR_ACCOUNT, [account_id.value])
        rows = cur.fetchall()
    memberships = []
    for membership_id_value, organization_id_value, state_value in rows:
        roles = _load_roles(conn, membership_id_value)
        memberships.append(
            OrganizationMembership(
                id=OrganizationMembershipId(membership_id_value),
                account_id=account_id,
                organization_id=MarketplaceOrganizationId(organization_id_value),
                roles=roles,
                state=MembershipState(state_value),
            )
        )
    return memberships
