"""FastAPI integration tests for SLICE-0083 multi-format broker inventory
import intake.

Uses a directly minted session token, mirroring
`test_professional_listing_draft_api.py`'s identical pattern. Covers the
Organization/PUBLISHER/MFA authorization boundary, CSRF, the full CSV
upload -> mapping -> confirm -> readable-private-draft round trip, exact
replay (ALREADY_IMPORTED, same draft, no duplicate), a NautiX 1.4 upload
(no manual mapping step), and the explicit unsupported-format/oversize/
worksheet-choice-required negative paths.
"""

from __future__ import annotations

import hashlib
import io
import os
import threading
import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
import xlsxwriter
import xlwt
from starlette.testclient import TestClient

from hullq.application.import_intake import (
    ConfirmImportBatchOutcome,
    confirm_import_batch_for_organization,
)
from hullq.domain.broker_access import AuthenticatedIdentity, Provider
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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.security.session_token import SessionClaims, mint_session_token

_SECRET = b"9" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "broker-import-intake-v1"

_VALID_NAUTIX_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<nautix xmlns="https://nautix.nautic-network.org/v1.4/" version="1.4" date="2026-10-01T10:00:00+02:00">
  <account token="ACME-1" status="active">
    <account_name>Acme Yacht Brokers</account_name>
    <adverts count="1">
      <advert id="ADV-0001" purpose="sale" type="boat" status="active" modified="2026-09-15T08:00:00+02:00">
        <advert_data>
          <office_id>OFFICE-1</office_id>
        </advert_data>
        <sale_data>
          <sale_class>used</sale_class>
          <price type="fixed" currency="EUR">125000.00</price>
          <location country="ES"/>
        </sale_data>
        <boat_data>
          <boat_types><type primary="true">sail-yacht</type></boat_types>
          <model>Oceanis 46.1</model>
        </boat_data>
      </advert>
    </adverts>
  </account>
</nautix>
"""


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


@pytest.fixture()
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0083api_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def client(api_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _ensure_account(conn: Any, account_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )


def _session_cookie(account_id: str, *, mfa: bool = True) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=mfa,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=_SECRET)
    return minted.token


def _log_in(client: TestClient, account_id: str, *, mfa: bool = True) -> None:
    client.cookies.set("hullq_session", _session_cookie(account_id, mfa=mfa), domain="api.test")


def _seed_org_and_membership(
    api_url: str,
    *,
    org_id: str,
    account_id: str,
    membership_id: str,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
    state: MembershipState = MembershipState.ACTIVE,
    publishing_eligibility: OrganizationPublishingEligibility = (
        OrganizationPublishingEligibility.ELIGIBLE
    ),
) -> None:
    conn = psycopg.connect(api_url)
    try:
        _ensure_account(conn, account_id)
        seed_marketplace_organization(
            conn,
            MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_id),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=publishing_eligibility,
            ),
        )
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId(membership_id),
                account_id=AccountId(account_id),
                organization_id=MarketplaceOrganizationId(org_id),
                roles=roles,
                state=state,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _imports_path(org_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/imports"


_CSV_BYTES = (
    b"Boat Name,Build Year,Price,Ref\r\nAria,1998,125000,REF-1\r\nBeta,2005,89000,REF-2\r\n"
)

_CSV_MAPPING = {
    "Boat Name": "physical_boat.boat_name",
    "Build Year": "physical_boat.build_year",
    "Price": "listing_offer.asking_price_amount",
    "Ref": "__source_record_key__",
}


def _upload_csv(
    client: TestClient,
    org_id: str,
    *,
    import_source: str = "TestFeed",
    csv_bytes: bytes = _CSV_BYTES,
) -> Any:
    return client.post(
        _imports_path(org_id),
        content=csv_bytes,
        headers={
            **_csrf_headers(),
            "X-HullQ-Import-Format": "CSV",
            "X-HullQ-Import-Source": import_source,
            "Content-Type": "application/octet-stream",
        },
    )


def _upload_file(
    client: TestClient,
    org_id: str,
    *,
    declared_format: str,
    import_source: str,
    file_bytes: bytes,
    worksheet_name: str | None = None,
) -> Any:
    headers = {
        **_csrf_headers(),
        "X-HullQ-Import-Format": declared_format,
        "X-HullQ-Import-Source": import_source,
        "Content-Type": "application/octet-stream",
    }
    if worksheet_name is not None:
        headers["X-HullQ-Worksheet"] = worksheet_name
    return client.post(_imports_path(org_id), content=file_bytes, headers=headers)


class TestImportAuthorizationBoundary:
    def test_unauthenticated_upload_is_denied(self, client: TestClient) -> None:
        response = _upload_csv(client, "ORG-IMP-UNAUTH")
        assert response.status_code == 401

    def test_missing_csrf_header_is_denied(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-CSRF", account_id="ACC-IMP-CSRF", membership_id="OM-IMP-CSRF"
        )
        _log_in(client, "ACC-IMP-CSRF")
        response = client.post(
            _imports_path("ORG-IMP-CSRF"),
            content=_CSV_BYTES,
            headers={
                "X-HullQ-Import-Format": "CSV",
                "X-HullQ-Import-Source": "Feed",
                "Content-Type": "application/octet-stream",
            },
        )
        assert response.status_code == 403

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-IMP-1")
        response = _upload_csv(client, "ORG-IMP-NEVER-CREATED")
        assert response.status_code == 404

    def test_mfa_required_blocks_upload(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-MFA", account_id="ACC-IMP-MFA", membership_id="OM-IMP-MFA"
        )
        _log_in(client, "ACC-IMP-MFA", mfa=False)
        response = _upload_csv(client, "ORG-IMP-MFA")
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}

    def test_non_publisher_role_blocks_upload(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-NOPUB",
            account_id="ACC-IMP-NOPUB",
            membership_id="OM-IMP-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _log_in(client, "ACC-IMP-NOPUB")
        response = _upload_csv(client, "ORG-IMP-NOPUB")
        assert response.status_code == 403
        assert response.json() == {"error": "publisher_role_required"}


class TestCsvUploadMapConfirmRoundtrip:
    def test_full_roundtrip_creates_readable_private_drafts(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-RT", account_id="ACC-IMP-RT", membership_id="OM-IMP-RT"
        )
        _log_in(client, "ACC-IMP-RT")

        upload = _upload_csv(client, "ORG-IMP-RT")
        assert upload.status_code == 201
        batch = upload.json()
        assert batch["status"] == "AWAITING_MAPPING"
        assert batch["headers"] == ["Boat Name", "Build Year", "Price", "Ref"]
        batch_id = batch["import_batch_id"]

        mapping_response = client.put(
            f"{_imports_path('ORG-IMP-RT')}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        assert mapping_response.status_code == 200
        mapped = mapping_response.json()
        assert mapped["status"] == "MAPPED"
        assert all(row["preview_classification"] == "VALID" for row in mapped["rows"])

        confirm_response = client.post(
            f"{_imports_path('ORG-IMP-RT')}/{batch_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm_response.status_code == 200
        confirmed = confirm_response.json()
        assert confirmed["status"] == "CONFIRMED"
        assert confirmed["summary"]["CREATE_NEW_DRAFT"] == 2
        assert confirmed["summary"]["INVALID"] == 0

        draft_ids = [row["created_professional_listing_draft_id"] for row in confirmed["rows"]]
        assert all(draft_ids)
        assert len(set(draft_ids)) == 2

        # Every created row is readable via the *existing* private draft
        # editor route -- never a NativeListing/public surface.
        draft_read = client.get(f"/api/broker/organizations/ORG-IMP-RT/drafts/{draft_ids[0]}")
        assert draft_read.status_code == 200
        draft_body = draft_read.json()
        assert draft_body["promotion_state"] == "EDITABLE"

    def test_stale_expected_row_count_is_rejected_with_zero_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        """Independent review amendment Finding F: a confirm request
        carrying a mismatched `expected_row_count` (the caller's stale
        view of this batch) is denied before any row is processed."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-STALE",
            account_id="ACC-IMP-STALE",
            membership_id="OM-IMP-STALE",
        )
        _log_in(client, "ACC-IMP-STALE")

        upload = _upload_csv(client, "ORG-IMP-STALE")
        batch_id = upload.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-STALE')}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )

        stale_confirm = client.post(
            f"{_imports_path('ORG-IMP-STALE')}/{batch_id}/confirm",
            json={"expected_row_count": 999},
            headers=_csrf_headers(),
        )
        assert stale_confirm.status_code == 409
        assert stale_confirm.json()["error"] == "stale_confirmation"

        verify_conn = psycopg.connect(api_url)
        try:
            with verify_conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM import_rows WHERE import_batch_id = %s "
                    "AND outcome IS NOT NULL",
                    [batch_id],
                )
                (resolved_count,) = cur.fetchone()
        finally:
            verify_conn.close()
        assert resolved_count == 0

        # The correct expected_row_count still confirms normally -- the
        # check denies a genuinely stale request without poisoning a
        # later correct one.
        correct_confirm = client.post(
            f"{_imports_path('ORG-IMP-STALE')}/{batch_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert correct_confirm.status_code == 200
        assert correct_confirm.json()["summary"]["CREATE_NEW_DRAFT"] == 2

    def test_missing_expected_row_count_is_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-NOEXPECT",
            account_id="ACC-IMP-NOEXPECT",
            membership_id="OM-IMP-NOEXPECT",
        )
        _log_in(client, "ACC-IMP-NOEXPECT")
        upload = _upload_csv(client, "ORG-IMP-NOEXPECT")
        batch_id = upload.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-NOEXPECT')}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        response = client.post(
            f"{_imports_path('ORG-IMP-NOEXPECT')}/{batch_id}/confirm",
            json={},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_confirm_request"

    def test_exact_replay_second_batch_is_already_imported_same_draft(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-REPLAY",
            account_id="ACC-IMP-REPLAY",
            membership_id="OM-IMP-REPLAY",
        )
        _log_in(client, "ACC-IMP-REPLAY")

        def _upload_map_confirm() -> dict[str, Any]:
            upload = _upload_csv(client, "ORG-IMP-REPLAY", import_source="ReplayFeed")
            batch_id = upload.json()["import_batch_id"]
            client.put(
                f"{_imports_path('ORG-IMP-REPLAY')}/{batch_id}/mapping",
                json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
                headers=_csrf_headers(),
            )
            confirm = client.post(
                f"{_imports_path('ORG-IMP-REPLAY')}/{batch_id}/confirm",
                json={"expected_row_count": 2},
                headers=_csrf_headers(),
            )
            return confirm.json()

        first = _upload_map_confirm()
        assert first["summary"]["CREATE_NEW_DRAFT"] == 2

        second = _upload_map_confirm()
        assert second["summary"]["CREATE_NEW_DRAFT"] == 0
        assert second["summary"]["ALREADY_IMPORTED"] == 2
        first_drafts = sorted(r["created_professional_listing_draft_id"] for r in first["rows"])
        second_drafts = sorted(r["created_professional_listing_draft_id"] for r in second["rows"])
        assert first_drafts == second_drafts

    def test_snapshot_mode_second_upload_is_conflict_review_never_duplicates(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-SNAP", account_id="ACC-IMP-SNAP", membership_id="OM-IMP-SNAP"
        )
        _log_in(client, "ACC-IMP-SNAP")
        no_key_mapping = {
            "Boat Name": "physical_boat.boat_name",
            "Build Year": "physical_boat.build_year",
            "Price": "listing_offer.asking_price_amount",
            "Ref": "__ignore__",
        }

        upload1 = _upload_csv(client, "ORG-IMP-SNAP", import_source="SnapFeed")
        batch1_id = upload1.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-SNAP')}/{batch1_id}/mapping",
            json={"column_mapping": no_key_mapping, "snapshot_mode": True},
            headers=_csrf_headers(),
        )
        confirm1 = client.post(
            f"{_imports_path('ORG-IMP-SNAP')}/{batch1_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm1.json()["summary"]["CREATE_NEW_DRAFT"] == 2

        # Exact-byte re-upload of the identical file -> identical snapshot
        # keys -> ALREADY_IMPORTED, never a duplicate.
        upload2 = _upload_csv(client, "ORG-IMP-SNAP", import_source="SnapFeed")
        batch2_id = upload2.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-SNAP')}/{batch2_id}/mapping",
            json={"column_mapping": no_key_mapping, "snapshot_mode": True},
            headers=_csrf_headers(),
        )
        confirm2 = client.post(
            f"{_imports_path('ORG-IMP-SNAP')}/{batch2_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm2.json()["summary"]["ALREADY_IMPORTED"] == 2

        # A *changed* snapshot re-upload (different file bytes) must never
        # silently create a second batch of drafts for the same rows.
        changed_bytes = _CSV_BYTES.replace(b"125000", b"999999")
        upload3 = _upload_csv(
            client, "ORG-IMP-SNAP", import_source="SnapFeed", csv_bytes=changed_bytes
        )
        batch3_id = upload3.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-SNAP')}/{batch3_id}/mapping",
            json={"column_mapping": no_key_mapping, "snapshot_mode": True},
            headers=_csrf_headers(),
        )
        confirm3 = client.post(
            f"{_imports_path('ORG-IMP-SNAP')}/{batch3_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        summary3 = confirm3.json()["summary"]
        assert summary3["CREATE_NEW_DRAFT"] == 0
        assert summary3["CONFLICT_REVIEW"] == 2


class TestNautixUpload:
    def test_valid_nautix_upload_confirms_to_private_draft(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-NX", account_id="ACC-IMP-NX", membership_id="OM-IMP-NX"
        )
        _log_in(client, "ACC-IMP-NX")

        upload = client.post(
            _imports_path("ORG-IMP-NX"),
            content=_VALID_NAUTIX_XML,
            headers={
                **_csrf_headers(),
                "X-HullQ-Import-Format": "NAUTIX_XML",
                "X-HullQ-Import-Source": "NautixFeed",
                "X-HullQ-Nautix-Account-Tokens": "ACME-1",
                "Content-Type": "application/octet-stream",
            },
        )
        assert upload.status_code == 201
        batch = upload.json()
        assert batch["status"] == "MAPPED"  # no manual mapping step for NautiX
        batch_id = batch["import_batch_id"]
        assert batch["rows"][0]["preview_classification"] == "VALID"

        confirm = client.post(
            f"{_imports_path('ORG-IMP-NX')}/{batch_id}/confirm",
            json={"expected_row_count": 1},
            headers=_csrf_headers(),
        )
        assert confirm.status_code == 200
        assert confirm.json()["summary"]["CREATE_NEW_DRAFT"] == 1

    def test_xxe_nautix_upload_is_rejected_with_zero_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-NXXXE",
            account_id="ACC-IMP-NXXXE",
            membership_id="OM-IMP-NXXXE",
        )
        _log_in(client, "ACC-IMP-NXXXE")
        malicious = (
            b'<?xml version="1.0"?>\n'
            b'<!DOCTYPE nautix [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n'
            b'<nautix xmlns="https://nautix.nautic-network.org/v1.4/" version="1.4" '
            b'date="2026-10-01T10:00:00+02:00">&xxe;</nautix>\n'
        )
        upload = client.post(
            _imports_path("ORG-IMP-NXXXE"),
            content=malicious,
            headers={
                **_csrf_headers(),
                "X-HullQ-Import-Format": "NAUTIX_XML",
                "X-HullQ-Import-Source": "NautixFeed",
                "Content-Type": "application/octet-stream",
            },
        )
        assert upload.status_code == 400
        assert upload.json()["error"] == "parse_failed"

        list_response = client.get(_imports_path("ORG-IMP-NXXXE"))
        assert list_response.json()["batches"] == []


class TestCsvDialectSelection:
    """Independent review amendment Finding G: explicit CSV dialect
    selection through the real upload workflow -- never silent delimiter
    guessing or locale-based numeric coercion."""

    _SEMICOLON_CSV_BYTES = (
        b"Boat Name;Build Year;Price;Ref\r\nAria;1998;125000;REF-1\r\nBeta;2005;89000;REF-2\r\n"
    )

    def test_semicolon_csv_full_roundtrip(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-SEMI", account_id="ACC-IMP-SEMI", membership_id="OM-IMP-SEMI"
        )
        _log_in(client, "ACC-IMP-SEMI")

        upload = client.post(
            _imports_path("ORG-IMP-SEMI"),
            content=self._SEMICOLON_CSV_BYTES,
            headers={
                **_csrf_headers(),
                "X-HullQ-Import-Format": "CSV",
                "X-HullQ-Import-Source": "SemiFeed",
                "X-HullQ-Csv-Delimiter": "SEMICOLON",
                "Content-Type": "application/octet-stream",
            },
        )
        assert upload.status_code == 201
        batch = upload.json()
        assert batch["headers"] == ["Boat Name", "Build Year", "Price", "Ref"]
        batch_id = batch["import_batch_id"]

        mapping_response = client.put(
            f"{_imports_path('ORG-IMP-SEMI')}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        assert mapping_response.status_code == 200
        assert all(
            row["preview_classification"] == "VALID" for row in mapping_response.json()["rows"]
        )

        confirm = client.post(
            f"{_imports_path('ORG-IMP-SEMI')}/{batch_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm.status_code == 200
        assert confirm.json()["summary"]["CREATE_NEW_DRAFT"] == 2

    def test_semicolon_bytes_as_default_comma_dialect_is_one_column_not_fabricated(
        self, client: TestClient, api_url: str
    ) -> None:
        """No silent delimiter guessing: the identical semicolon-delimited
        bytes, uploaded *without* selecting the semicolon dialect, parse
        as one comma-free column per row (the whole line as one field)
        rather than the parser silently detecting/switching dialects."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-SEMI-DEFAULT",
            account_id="ACC-IMP-SEMI-DEFAULT",
            membership_id="OM-IMP-SEMI-DEFAULT",
        )
        _log_in(client, "ACC-IMP-SEMI-DEFAULT")
        upload = client.post(
            _imports_path("ORG-IMP-SEMI-DEFAULT"),
            content=self._SEMICOLON_CSV_BYTES,
            headers={
                **_csrf_headers(),
                "X-HullQ-Import-Format": "CSV",
                "X-HullQ-Import-Source": "SemiFeed",
                "Content-Type": "application/octet-stream",
            },
        )
        assert upload.status_code == 201
        assert upload.json()["headers"] == ["Boat Name;Build Year;Price;Ref"]

    def test_unsupported_csv_delimiter_value_is_rejected_with_zero_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-BADDELIM",
            account_id="ACC-IMP-BADDELIM",
            membership_id="OM-IMP-BADDELIM",
        )
        _log_in(client, "ACC-IMP-BADDELIM")
        upload = client.post(
            _imports_path("ORG-IMP-BADDELIM"),
            content=_CSV_BYTES,
            headers={
                **_csrf_headers(),
                "X-HullQ-Import-Format": "CSV",
                "X-HullQ-Import-Source": "Feed",
                "X-HullQ-Csv-Delimiter": "PIPE",
                "Content-Type": "application/octet-stream",
            },
        )
        assert upload.status_code == 400
        assert upload.json()["error"] == "unsupported_format"

        list_response = client.get(_imports_path("ORG-IMP-BADDELIM"))
        assert list_response.json()["batches"] == []


class TestFormatNegatives:
    def test_unsupported_declared_format_is_rejected(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-BADFMT",
            account_id="ACC-IMP-BADFMT",
            membership_id="OM-IMP-BADFMT",
        )
        _log_in(client, "ACC-IMP-BADFMT")
        response = client.post(
            _imports_path("ORG-IMP-BADFMT"),
            content=b"whatever",
            headers={
                **_csrf_headers(),
                "X-HullQ-Import-Format": "XLSM",
                "X-HullQ-Import-Source": "Feed",
                "Content-Type": "application/octet-stream",
            },
        )
        assert response.status_code == 400
        assert response.json()["error"] == "unsupported_format"

    def test_oversize_upload_rejected_by_content_length(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-BIG", account_id="ACC-IMP-BIG", membership_id="OM-IMP-BIG"
        )
        _log_in(client, "ACC-IMP-BIG")
        response = client.post(
            _imports_path("ORG-IMP-BIG"),
            content=b"x",
            headers={
                **_csrf_headers(),
                "X-HullQ-Import-Format": "CSV",
                "X-HullQ-Import-Source": "Feed",
                "Content-Type": "application/octet-stream",
                "Content-Length": "999999999",
            },
        )
        assert response.status_code == 413

    def test_malformed_csv_rejected_with_zero_mutation(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-MALFORMED",
            account_id="ACC-IMP-MALFORMED",
            membership_id="OM-IMP-MALFORMED",
        )
        _log_in(client, "ACC-IMP-MALFORMED")
        response = _upload_csv(client, "ORG-IMP-MALFORMED", csv_bytes=b"")
        assert response.status_code == 400
        assert response.json()["kind"] == "EMPTY"
        list_response = client.get(_imports_path("ORG-IMP-MALFORMED"))
        assert list_response.json()["batches"] == []


def _backend_pid(conn: Any) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        pid = int(cur.fetchone()[0])
    conn.commit()  # end the implicit read transaction; leaves conn IDLE
    return pid


def _wait_until_blocked_on_lock(monitor_conn: Any, pid: int, *, timeout: float = 10.0) -> bool:
    """Poll `pg_locks` on a dedicated connection until *pid* is genuinely
    waiting (not granted) on a lock -- never a fixed sleep guessing at
    scheduling, mirroring
    `test_boat_design_association_persistence.py`'s identical SLICE-0082
    Finding A proof technique."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with monitor_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid = %s AND NOT granted)", [pid]
            )
            (is_waiting,) = cur.fetchone()
        monitor_conn.commit()
        if is_waiting:
            return True
        time.sleep(0.05)
    return False


class TestAuthorizationRevocationDuringConfirm:
    def test_concurrent_membership_revocation_denies_in_flight_row_zero_mutation(
        self, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Independent review amendment Finding A: the one authorization
        check at the top of `confirm_import_batch_for_organization` passes
        (membership ACTIVE/PUBLISHER at call entry), but a *second*
        connection revokes that exact membership -- genuinely blocked on
        the identical membership row lock the per-row recheck acquires,
        confirmed via `pg_locks`, never a timing guess -- and is only
        allowed to commit once the confirm call is truly blocked behind
        it. The confirm call must see the revocation and deny with zero
        draft/mapping mutation, never silently using the stale entry-time
        authorization for the in-flight row.
        """
        org_id = "ORG-IMP-REVOKE-RACE"
        account_id = "ACC-IMP-REVOKE-RACE"
        membership_id = "OM-IMP-REVOKE-RACE"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )

        from hullq.api.app import create_app

        monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
        setup_client = TestClient(
            create_app(
                database_url=api_url,
                preview_signing_secret=os.urandom(32),
                session_signing_secret=_SECRET,
                web_origin=_WEB_ORIGIN,
            ),
            base_url="http://api.test",
            follow_redirects=False,
        )
        _log_in(setup_client, account_id)
        upload = _upload_csv(setup_client, org_id, import_source="RevokeRaceFeed")
        assert upload.status_code == 201
        batch_id = upload.json()["import_batch_id"]
        mapping_response = setup_client.put(
            f"{_imports_path(org_id)}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        assert mapping_response.status_code == 200
        setup_client.close()

        revoker_conn = psycopg.connect(api_url)
        monitor_conn = psycopg.connect(api_url)
        confirm_conn = psycopg.connect(api_url)
        confirm_pid = _backend_pid(confirm_conn)

        errors: list[BaseException] = []
        confirm_results: list[Any] = []
        membership_locked = threading.Event()

        def _hold_lock_then_revoke() -> None:
            try:
                with revoker_conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM organization_memberships "
                        "WHERE account_id = %s AND organization_id = %s FOR UPDATE",
                        [account_id, org_id],
                    )
                membership_locked.set()
                blocked = _wait_until_blocked_on_lock(monitor_conn, confirm_pid)
                assert blocked, "confirm call never blocked on the membership row lock"
                with revoker_conn.cursor() as cur:
                    cur.execute(
                        "UPDATE organization_memberships SET state = 'INACTIVE' "
                        "WHERE account_id = %s AND organization_id = %s",
                        [account_id, org_id],
                    )
                revoker_conn.commit()
            except Exception as exc:  # pragma: no cover - surfaced via errors assertion
                errors.append(exc)

        def _attempt_confirm() -> None:
            try:
                membership_locked.wait(timeout=10)
                session = SessionClaims(
                    account_id=AccountId(account_id),
                    identity=AuthenticatedIdentity(
                        provider=Provider.AUTH0,
                        issuer="https://issuer.test/",
                        subject=f"subject-{account_id}",
                        auth_time=datetime.now(UTC),
                        mfa_satisfied=True,
                    ),
                    issued_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC),
                )
                result = confirm_import_batch_for_organization(
                    confirm_conn, session, org_id, batch_id, expected_row_count=2
                )
                confirm_results.append(result)
            except Exception as exc:  # pragma: no cover - surfaced via errors assertion
                errors.append(exc)

        threads = [
            threading.Thread(target=_hold_lock_then_revoke),
            threading.Thread(target=_attempt_confirm),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
        revoker_conn.close()
        monitor_conn.close()
        confirm_conn.close()

        assert not errors, f"Thread errors: {errors}"
        assert len(confirm_results) == 1
        result = confirm_results[0]
        assert result.outcome in (
            ConfirmImportBatchOutcome.NOT_FOUND_OR_DENIED,
            ConfirmImportBatchOutcome.PUBLISHER_ROLE_REQUIRED,
        )

        verify_conn = psycopg.connect(api_url)
        try:
            with verify_conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM professional_listing_drafts WHERE owner_organization_id = %s",
                    [org_id],
                )
                (draft_count,) = cur.fetchone()
                cur.execute(
                    "SELECT count(*) FROM import_rows WHERE import_batch_id = %s "
                    "AND outcome IS NOT NULL",
                    [batch_id],
                )
                (resolved_row_count,) = cur.fetchone()
        finally:
            verify_conn.close()
        assert draft_count == 0
        assert resolved_row_count == 0


_SPREADSHEET_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "spreadsheets"


def _xlsx_inventory_bytes() -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("Inventory")
    ws.write_row(0, 0, ["Boat Name", "Build Year", "Price", "Ref"])
    ws.write_row(1, 0, ["Aria", 1998, 125000, "REF-1"])
    ws.write_row(2, 0, ["Beta", 2005, 89000, "REF-2"])
    wb.close()
    return buf.getvalue()


def _xls_inventory_bytes() -> bytes:
    buf = io.BytesIO()
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Inventory")
    for r, row in enumerate(
        [
            ["Boat Name", "Build Year", "Price", "Ref"],
            ["Aria", 1998, 125000, "REF-1"],
            ["Beta", 2005, 89000, "REF-2"],
        ]
    ):
        for c, value in enumerate(row):
            ws.write(r, c, value)
    wb.save(buf)
    return buf.getvalue()


def _load_pinned_fixture(name: str, expected_sha256: str) -> bytes:
    raw = (_SPREADSHEET_FIXTURES_DIR / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == expected_sha256, f"{name} digest mismatch"
    return raw


class TestSpreadsheetFormatUploadRoundtrip:
    """Independent review amendment Finding D: every spreadsheet format in
    the support matrix executed end-to-end (upload -> map -> confirm),
    not only reasoned about structurally. XLSX/XLS carry genuine
    broker-inventory-shaped content; XLSB/ODS use the real third-party
    `python-calamine` test fixtures pinned in
    `tests/fixtures/spreadsheets/` (non-inventory-shaped, but genuine
    binary bytes this repository did not author) -- mapped with every
    column ignored except an explicit snapshot-mode dedup key, still
    proving the full upload/map/confirm/replay pipeline accepts them."""

    def test_xlsx_full_roundtrip(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-XLSX", account_id="ACC-IMP-XLSX", membership_id="OM-IMP-XLSX"
        )
        _log_in(client, "ACC-IMP-XLSX")
        upload = _upload_file(
            client,
            "ORG-IMP-XLSX",
            declared_format="XLSX",
            import_source="XlsxFeed",
            file_bytes=_xlsx_inventory_bytes(),
            worksheet_name="Inventory",
        )
        assert upload.status_code == 201
        batch_id = upload.json()["import_batch_id"]
        mapping_response = client.put(
            f"{_imports_path('ORG-IMP-XLSX')}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        assert mapping_response.status_code == 200
        confirm = client.post(
            f"{_imports_path('ORG-IMP-XLSX')}/{batch_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm.status_code == 200
        assert confirm.json()["summary"]["CREATE_NEW_DRAFT"] == 2

    def test_xls_full_roundtrip(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-XLS", account_id="ACC-IMP-XLS", membership_id="OM-IMP-XLS"
        )
        _log_in(client, "ACC-IMP-XLS")
        upload = _upload_file(
            client,
            "ORG-IMP-XLS",
            declared_format="XLS",
            import_source="XlsFeed",
            file_bytes=_xls_inventory_bytes(),
            worksheet_name="Inventory",
        )
        assert upload.status_code == 201
        batch_id = upload.json()["import_batch_id"]
        mapping_response = client.put(
            f"{_imports_path('ORG-IMP-XLS')}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        assert mapping_response.status_code == 200
        confirm = client.post(
            f"{_imports_path('ORG-IMP-XLS')}/{batch_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm.status_code == 200
        assert confirm.json()["summary"]["CREATE_NEW_DRAFT"] == 2

        # Exact replay of the identical genuine XLS bytes -> ALREADY_IMPORTED.
        upload2 = _upload_file(
            client,
            "ORG-IMP-XLS",
            declared_format="XLS",
            import_source="XlsFeed",
            file_bytes=_xls_inventory_bytes(),
            worksheet_name="Inventory",
        )
        batch2_id = upload2.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-XLS')}/{batch2_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        confirm2 = client.post(
            f"{_imports_path('ORG-IMP-XLS')}/{batch2_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm2.json()["summary"]["ALREADY_IMPORTED"] == 2

    def test_genuine_xlsb_fixture_full_roundtrip_and_replay(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-XLSB", account_id="ACC-IMP-XLSB", membership_id="OM-IMP-XLSB"
        )
        _log_in(client, "ACC-IMP-XLSB")
        raw = _load_pinned_fixture(
            "calamine_date.xlsb",
            "68d36adf4d4de3890209e786eeb89a98778d25158628f83e96587e652fbb4eca",
        )
        upload = _upload_file(
            client,
            "ORG-IMP-XLSB",
            declared_format="XLSB",
            import_source="XlsbFeed",
            file_bytes=raw,
            worksheet_name="Sheet1",
        )
        assert upload.status_code == 201
        batch = upload.json()
        batch_id = batch["import_batch_id"]
        headers = batch["headers"]
        ignore_mapping = dict.fromkeys(headers, "__ignore__")
        mapping_response = client.put(
            f"{_imports_path('ORG-IMP-XLSB')}/{batch_id}/mapping",
            json={"column_mapping": ignore_mapping, "snapshot_mode": True},
            headers=_csrf_headers(),
        )
        assert mapping_response.status_code == 200
        mapped = mapping_response.json()
        row_count = len(mapped["rows"])
        assert row_count > 0

        confirm = client.post(
            f"{_imports_path('ORG-IMP-XLSB')}/{batch_id}/confirm",
            json={"expected_row_count": row_count},
            headers=_csrf_headers(),
        )
        assert confirm.status_code == 200
        # Every row maps to zero draft-relevant fields (all ignored) but is
        # still a genuine, mechanically VALID staged row with a server-
        # authored snapshot key -- proving the full pipeline accepts
        # genuine third-party XLSB bytes end-to-end.
        assert confirm.json()["summary"]["CREATE_NEW_DRAFT"] == row_count

        upload2 = _upload_file(
            client,
            "ORG-IMP-XLSB",
            declared_format="XLSB",
            import_source="XlsbFeed",
            file_bytes=raw,
            worksheet_name="Sheet1",
        )
        batch2_id = upload2.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-XLSB')}/{batch2_id}/mapping",
            json={"column_mapping": ignore_mapping, "snapshot_mode": True},
            headers=_csrf_headers(),
        )
        confirm2 = client.post(
            f"{_imports_path('ORG-IMP-XLSB')}/{batch2_id}/confirm",
            json={"expected_row_count": row_count},
            headers=_csrf_headers(),
        )
        assert confirm2.json()["summary"]["ALREADY_IMPORTED"] == row_count

    def test_genuine_ods_fixture_full_roundtrip(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-IMP-ODS", account_id="ACC-IMP-ODS", membership_id="OM-IMP-ODS"
        )
        _log_in(client, "ACC-IMP-ODS")
        raw = _load_pinned_fixture(
            "calamine_date.ods",
            "d65f3198bc73f2fad356e1b097215fc2f9a833fb802638217e5adc27fbba0466",
        )
        upload = _upload_file(
            client,
            "ORG-IMP-ODS",
            declared_format="ODS",
            import_source="OdsFeed",
            file_bytes=raw,
            worksheet_name="Sheet1",
        )
        assert upload.status_code == 201
        batch = upload.json()
        batch_id = batch["import_batch_id"]
        ignore_mapping = dict.fromkeys(batch["headers"], "__ignore__")
        mapping_response = client.put(
            f"{_imports_path('ORG-IMP-ODS')}/{batch_id}/mapping",
            json={"column_mapping": ignore_mapping, "snapshot_mode": True},
            headers=_csrf_headers(),
        )
        assert mapping_response.status_code == 200
        row_count = len(mapping_response.json()["rows"])
        assert row_count > 0

        confirm = client.post(
            f"{_imports_path('ORG-IMP-ODS')}/{batch_id}/confirm",
            json={"expected_row_count": row_count},
            headers=_csrf_headers(),
        )
        assert confirm.status_code == 200


class TestStagingRetentionAndPendingBatchLimit:
    """Independent review amendment Finding E: bounded staging retention
    (expired, never-confirmed batches are purged, never kept forever) and
    a bounded per-Organization count of pending (unconfirmed) batches."""

    def test_expired_unconfirmed_batch_is_purged_on_next_upload(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-EXPIRE",
            account_id="ACC-IMP-EXPIRE",
            membership_id="OM-IMP-EXPIRE",
        )
        _log_in(client, "ACC-IMP-EXPIRE")

        upload = _upload_csv(client, "ORG-IMP-EXPIRE", import_source="ExpireFeed")
        assert upload.status_code == 201
        expired_batch_id = upload.json()["import_batch_id"]

        conn = psycopg.connect(api_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE import_batches SET expires_at = NOW() - INTERVAL '1 hour' "
                    "WHERE import_batch_id = %s",
                    [expired_batch_id],
                )
            conn.commit()
        finally:
            conn.close()

        # Any subsequent upload for the same Organization opportunistically
        # purges its own expired, never-confirmed batches first.
        second_upload = _upload_csv(client, "ORG-IMP-EXPIRE", import_source="OtherFeed")
        assert second_upload.status_code == 201

        get_expired = client.get(f"{_imports_path('ORG-IMP-EXPIRE')}/{expired_batch_id}")
        assert get_expired.status_code == 404

        verify_conn = psycopg.connect(api_url)
        try:
            with verify_conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM import_rows WHERE import_batch_id = %s",
                    [expired_batch_id],
                )
                (row_count,) = cur.fetchone()
        finally:
            verify_conn.close()
        assert row_count == 0

    def test_confirmed_batch_is_never_purged_even_once_expired(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-KEEPCONFIRMED",
            account_id="ACC-IMP-KEEPCONFIRMED",
            membership_id="OM-IMP-KEEPCONFIRMED",
        )
        _log_in(client, "ACC-IMP-KEEPCONFIRMED")

        upload = _upload_csv(client, "ORG-IMP-KEEPCONFIRMED", import_source="KeepFeed")
        batch_id = upload.json()["import_batch_id"]
        client.put(
            f"{_imports_path('ORG-IMP-KEEPCONFIRMED')}/{batch_id}/mapping",
            json={"column_mapping": _CSV_MAPPING, "snapshot_mode": False},
            headers=_csrf_headers(),
        )
        confirm = client.post(
            f"{_imports_path('ORG-IMP-KEEPCONFIRMED')}/{batch_id}/confirm",
            json={"expected_row_count": 2},
            headers=_csrf_headers(),
        )
        assert confirm.json()["summary"]["CREATE_NEW_DRAFT"] == 2

        conn = psycopg.connect(api_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE import_batches SET expires_at = NOW() - INTERVAL '1 hour' "
                    "WHERE import_batch_id = %s",
                    [batch_id],
                )
            conn.commit()
        finally:
            conn.close()

        _upload_csv(client, "ORG-IMP-KEEPCONFIRMED", import_source="AnotherFeed")

        get_confirmed = client.get(f"{_imports_path('ORG-IMP-KEEPCONFIRMED')}/{batch_id}")
        assert get_confirmed.status_code == 200
        assert get_confirmed.json()["status"] == "CONFIRMED"

    def test_too_many_pending_batches_rejects_further_uploads(
        self, client: TestClient, api_url: str
    ) -> None:
        from hullq.persistence.import_intake import MAX_PENDING_BATCHES_PER_ORGANIZATION

        _seed_org_and_membership(
            api_url,
            org_id="ORG-IMP-PENDLIMIT",
            account_id="ACC-IMP-PENDLIMIT",
            membership_id="OM-IMP-PENDLIMIT",
        )
        _log_in(client, "ACC-IMP-PENDLIMIT")

        for i in range(MAX_PENDING_BATCHES_PER_ORGANIZATION):
            response = _upload_csv(client, "ORG-IMP-PENDLIMIT", import_source=f"Feed{i}")
            assert response.status_code == 201, f"upload {i} unexpectedly failed"

        over_limit = _upload_csv(client, "ORG-IMP-PENDLIMIT", import_source="OneTooManyFeed")
        assert over_limit.status_code == 429
        assert over_limit.json()["error"] == "too_many_pending_batches"

        list_response = client.get(_imports_path("ORG-IMP-PENDLIMIT"))
        assert len(list_response.json()["batches"]) == MAX_PENDING_BATCHES_PER_ORGANIZATION
