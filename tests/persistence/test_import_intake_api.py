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

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from starlette.testclient import TestClient

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
from hullq.security.session_token import mint_session_token

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
            f"{_imports_path('ORG-IMP-RT')}/{batch_id}/confirm", json={}, headers=_csrf_headers()
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
                json={},
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
            f"{_imports_path('ORG-IMP-SNAP')}/{batch1_id}/confirm", json={}, headers=_csrf_headers()
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
            f"{_imports_path('ORG-IMP-SNAP')}/{batch2_id}/confirm", json={}, headers=_csrf_headers()
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
            f"{_imports_path('ORG-IMP-SNAP')}/{batch3_id}/confirm", json={}, headers=_csrf_headers()
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
            f"{_imports_path('ORG-IMP-NX')}/{batch_id}/confirm", json={}, headers=_csrf_headers()
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
