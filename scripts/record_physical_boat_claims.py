"""SLICE-0050 operator-assisted PhysicalBoat claim recording CLI.

Reads one versioned JSON claim-recording request (schema:
``fixtures/slice_0050/physical_boat_claim_request.schema.v0.1.json``),
validates it structurally/typed, then drives
``hullq.persistence.physical_boat_claims.write_physical_boat_claim_revision``
against a real database connection. That single call resolves the
NativeListing -> MarketEpisode -> PhysicalBoat chain, evaluates the real
accepted SLICE-0041 authorization boundary and durably writes (or
idempotently confirms, or fails closed on) the bounded seven-field claim
revision. No Auth0 session, browser broker form or generic admin console is
required or provided by this script.

Requires ``HULLQ_DATABASE_URL`` in the environment; fails fast with an
actionable message if missing/invalid.

Run: uv run python scripts/record_physical_boat_claims.py <claim_request.json>
"""

from __future__ import annotations

import sys

from hullq.application.physical_boat_claim_loader import (
    PhysicalBoatClaimRequestValidationError,
    load_physical_boat_claim_request,
)
from hullq.persistence.connection import get_database_url, open_connection
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimWriteStatus,
    write_physical_boat_claim_revision,
)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: record_physical_boat_claims.py <claim_request.json>", file=sys.stderr)
        return 2
    request_path = args[0]

    try:
        request = load_physical_boat_claim_request(request_path)
    except PhysicalBoatClaimRequestValidationError as exc:
        print(f"CLAIM REQUEST INPUT INVALID -> {exc}", file=sys.stderr)
        return 1

    try:
        database_url = get_database_url()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    conn = open_connection(database_url)
    try:
        result = write_physical_boat_claim_revision(
            conn,
            account_id=request.account_id,
            candidate_organization=request.organization,
            membership=request.membership,
            native_listing_id=request.native_listing_id,
            revision_id=request.claim_revision_id,
            expected_current_revision_id=request.expected_current_claim_revision_id,
            claims=request.claims,
        )
    finally:
        conn.close()

    suffix = f" ({result.denial_reason.value})" if result.denial_reason is not None else ""
    print(f"physical_boat_claim -> {result.status.value.upper()}{suffix}")
    if result.current_revision_id is not None:
        print(f"current_revision_id -> {result.current_revision_id.value}")

    success_statuses = frozenset(
        {
            PhysicalBoatClaimWriteStatus.CREATED,
            PhysicalBoatClaimWriteStatus.REVISED,
            PhysicalBoatClaimWriteStatus.ALREADY_EXISTS,
        }
    )
    return 0 if result.status in success_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
