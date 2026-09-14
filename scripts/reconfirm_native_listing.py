"""SLICE-0052 operator-assisted NativeListing reconfirmation CLI.

Reads the same small JSON principal file shape as
``scripts/lifecycle_listing.py`` describing the explicit AccountId, candidate
MarketplaceOrganization and OrganizationMembership required by the real
accepted SLICE-0041 eligibility evaluator, plus an explicit caller-supplied
``FreshnessConfirmationId``, then drives exactly one reconfirmation attempt
against a real database connection via
``hullq.persistence.native_listing_freshness.reconfirm_native_listing``.
Reports a deterministic, mechanically distinct outcome; a denied,
cross-Organization, non-ACTIVE or conflicting-ID request changes no state
and appends no confirmation row -- this CLI never repairs or bypasses that.

This entry point never accepts ``authorized=true``, a raw Organization-ID-
only bypass, or an arbitrary confirmation timestamp (contract §9):
``occurred_at`` is always system/database-recorded, never a CLI argument.

Requires ``HULLQ_DATABASE_URL`` in the environment; fails fast with an
actionable message if missing/invalid.

Run:
  uv run python scripts/reconfirm_native_listing.py <principal.json> <native_listing_id> <confirmation_id>

Example principal JSON shape (identical to lifecycle_listing.py's):
{
  "account_id": "ACC-1",
  "organization": {
    "id": "ORG-1",
    "professional_category": "BROKER",
    "publishing_eligibility": "ELIGIBLE"
  },
  "membership": {
    "id": "OM-1",
    "account_id": "ACC-1",
    "organization_id": "ORG-1",
    "roles": ["PUBLISHER"],
    "state": "ACTIVE"
  }
}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
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
from hullq.persistence.connection import get_database_url, open_connection
from hullq.persistence.native_listing_freshness import (
    ReconfirmationStatus,
    reconfirm_native_listing,
)


class PrincipalInputError(ValueError):
    """*path* could not be read/parsed, or its contents were domain-invalid."""


def _load_principal(
    path: str,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise PrincipalInputError(f"could not read principal file {path!r}: {exc}") from exc

    try:
        data: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise PrincipalInputError(f"principal file {path!r} is not valid JSON: {exc}") from exc

    try:
        org_data = data["organization"]
        membership_data = data["membership"]
        account_id = AccountId(data["account_id"])
        organization = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_data["id"]),
            professional_category=ProfessionalCategory(org_data["professional_category"]),
            publishing_eligibility=OrganizationPublishingEligibility(
                org_data["publishing_eligibility"]
            ),
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(membership_data["id"]),
            account_id=AccountId(membership_data["account_id"]),
            organization_id=MarketplaceOrganizationId(membership_data["organization_id"]),
            roles=frozenset(MembershipRole(role) for role in membership_data["roles"]),
            state=MembershipState(membership_data["state"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PrincipalInputError(f"principal file {path!r} is domain-invalid: {exc}") from exc

    return account_id, organization, membership


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        print(
            "usage: reconfirm_native_listing.py <principal.json> <native_listing_id> "
            "<confirmation_id>",
            file=sys.stderr,
        )
        return 2
    principal_path, native_listing_id_value, confirmation_id_value = args

    try:
        account_id, organization, membership = _load_principal(principal_path)
    except PrincipalInputError as exc:
        print(f"PRINCIPAL INPUT INVALID -> {exc}", file=sys.stderr)
        return 1

    try:
        database_url = get_database_url()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    conn = open_connection(database_url)
    try:
        result = reconfirm_native_listing(
            conn,
            confirmation_id=FreshnessConfirmationId(confirmation_id_value),
            account_id=account_id,
            candidate_organization=organization,
            membership=membership,
            native_listing_id=NativeListingId(native_listing_id_value),
        )
    finally:
        conn.close()

    suffix = f" ({result.denial_reason.value})" if result.denial_reason is not None else ""
    print(f"RECONFIRM -> {result.status.value.upper()}{suffix}")

    if result.status not in (ReconfirmationStatus.RECONFIRMED, ReconfirmationStatus.ALREADY_EXISTS):
        return 1

    assert result.occurred_at is not None
    print(f"occurred_at -> {result.occurred_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
