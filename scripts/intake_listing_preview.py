"""SLICE-0048 operator-assisted listing intake CLI.

Reads one versioned JSON intake file (schema:
``fixtures/slice_0048/listing_intake_request.schema.v0.1.json``), validates
it structurally/typed, then drives the fixed four-stage orchestration in
``hullq.application.listing_intake`` against a real database connection.
Reports stage-by-stage status; a failure at any stage stops the run and
mints no preview token. Retrying with the exact same input is safe and
continues from whatever durable partial progress already committed.

Requires ``HULLQ_DATABASE_URL`` and ``HULLQ_PREVIEW_SIGNING_SECRET`` in the
environment; both fail fast with an actionable message if missing/invalid.
``HULLQ_PREVIEW_BASE_URL`` is optional and only used to compose a full
shareable preview URL in the printed report.

Run: uv run python scripts/intake_listing_preview.py <intake.json>
"""

from __future__ import annotations

import os
import sys

from hullq.application.listing_intake import ListingIntakeOutcome, run_listing_intake
from hullq.application.listing_intake_loader import (
    ListingIntakeRequestValidationError,
    load_listing_intake_request,
)
from hullq.persistence.connection import get_database_url, open_connection
from hullq.security.preview_signing import PreviewSigningSecretError, get_preview_signing_secret


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: intake_listing_preview.py <intake.json>", file=sys.stderr)
        return 2
    intake_path = args[0]

    try:
        request = load_listing_intake_request(intake_path)
    except ListingIntakeRequestValidationError as exc:
        print(f"INTAKE INPUT INVALID -> {exc}", file=sys.stderr)
        return 1

    try:
        database_url = get_database_url()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        secret = get_preview_signing_secret()
    except PreviewSigningSecretError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    conn = open_connection(database_url)
    try:
        result = run_listing_intake(conn, request=request, preview_signing_secret=secret)
    finally:
        conn.close()

    print(f"physical_boat  -> {result.physical_boat.status.value.upper()}")
    if result.market_episode is not None:
        print(f"market_episode -> {result.market_episode.status.value.upper()}")
    if result.native_listing is not None:
        suffix = (
            f" ({result.native_listing.denial_reason.value})"
            if result.native_listing.denial_reason is not None
            else ""
        )
        print(f"native_listing -> {result.native_listing.status.value.upper()}{suffix}")
    if result.offer is not None:
        suffix = (
            f" ({result.offer.denial_reason.value})"
            if result.offer.denial_reason is not None
            else ""
        )
        print(f"offer_revision -> {result.offer.status.value.upper()}{suffix}")

    if result.outcome is not ListingIntakeOutcome.SUCCEEDED:
        print(
            f"\nINTAKE OUTCOME -> {result.outcome.value.upper()} "
            "(stopped fail-closed; no preview token minted; no all-or-nothing rollback "
            "is claimed -- any earlier CREATED stage above is already durably committed)",
            file=sys.stderr,
        )
        return 1

    assert result.preview_token is not None
    assert result.preview_token_expires_at is not None
    base_url = os.environ.get("HULLQ_PREVIEW_BASE_URL", "").strip()
    preview_path = f"/_preview/listings/{result.preview_token}"
    preview_url = f"{base_url.rstrip('/')}{preview_path}" if base_url else preview_path

    print("\nINTAKE OUTCOME -> SUCCEEDED")
    print(f"preview token expires at -> {result.preview_token_expires_at.isoformat()}")
    print(f"preview URL -> {preview_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
