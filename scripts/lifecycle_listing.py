"""SLICE-0049 operator-assisted NativeListing lifecycle CLI (publish / withdraw).

Reads one small JSON principal file describing the explicit AccountId,
candidate MarketplaceOrganization and OrganizationMembership required by the
real accepted SLICE-0041 eligibility evaluator, then drives exactly one
lifecycle transition (`DRAFT -> ACTIVE` or `ACTIVE -> WITHDRAWN`) against a
real database connection via `hullq.persistence.native_listing_lifecycle`.
Reports a deterministic, mechanically distinct outcome; a denied, mismatched,
unsupported or stale request changes no state and appends no audit record --
this CLI never repairs or bypasses that.

Requires `HULLQ_DATABASE_URL` in the environment; fails fast with an
actionable message if missing/invalid.

Run:
  uv run python scripts/lifecycle_listing.py publish <principal.json> <native_listing_id>
  uv run python scripts/lifecycle_listing.py withdraw <principal.json> <native_listing_id>

Example principal JSON shape:
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
from hullq.persistence.native_listing_lifecycle import (
    LifecycleTransitionStatus,
    publish_native_listing,
    withdraw_native_listing,
)

_COMMANDS = {"publish": publish_native_listing, "withdraw": withdraw_native_listing}


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
    if len(args) != 3 or args[0] not in _COMMANDS:
        print(
            "usage: lifecycle_listing.py <publish|withdraw> <principal.json> <native_listing_id>",
            file=sys.stderr,
        )
        return 2
    command, principal_path, native_listing_id_value = args

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
        result = _COMMANDS[command](
            conn,
            account_id=account_id,
            candidate_organization=organization,
            membership=membership,
            native_listing_id=NativeListingId(native_listing_id_value),
        )
    finally:
        conn.close()

    suffix = f" ({result.denial_reason.value})" if result.denial_reason is not None else ""
    print(f"{command.upper()} -> {result.status.value.upper()}{suffix}")

    if result.status is not LifecycleTransitionStatus.TRANSITIONED:
        return 1

    assert result.transition_id is not None
    print(f"transition_id -> {result.transition_id.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
