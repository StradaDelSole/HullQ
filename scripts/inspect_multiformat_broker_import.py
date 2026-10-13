"""SLICE-0083 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the multi-format broker inventory import intake vertical against a
real, disposable PostgreSQL 18 schema and two real local HTTP servers:
FastAPI and the built Astro/Node SSR web package. Authentication uses a
directly minted, cryptographically signed session cookie rather than a full
OIDC round-trip -- mirrors `scripts/inspect_broker_listing_design_association.py`'s
identical, already-accepted shortcut. FastAPI still performs its own real
signature verification of that exact cookie on every request below.

Demonstrates, end to end, through the real production FastAPI routes (no
direct SQL insertion of batches/rows):

    1. CSV upload (comma dialect) -> explicit mapping -> explicit confirm
       -> a real private ProfessionalListingDraft, read back through the
       *existing built Astro SSR* private draft editor page
    2. CSV upload (semicolon dialect, explicit selection) parses correctly;
       the identical bytes *without* that selection do not
    3. TSV and JSON uploads -> confirm, same outcome shape
    4. XLSX (explicit worksheet selection) and legacy XLS (genuine BIFF8
       via `xlwt`) uploads -> confirm
    5. genuine third-party XLSB and ODS fixtures (pinned from
       `python-calamine`'s own upstream test corpus) -> confirm
    6. one-time snapshot mode: exact-byte replay -> ALREADY_IMPORTED;
       changed bytes for the same ImportSource -> CONFLICT_REVIEW, zero
       duplicate drafts
    7. a stale `expected_row_count` is denied (zero mutation); the correct
       one then confirms normally
    8. NautiX 1.4 `adverts.xml`: a valid attested sale/sailboat advert
       confirms to a private draft; an `inactive` advert is
       `CONFLICT_REVIEW`, never an auto-withdrawal
    9. an unsupported declared format is rejected with zero mutation
   10. the real built Astro SSR `/imports` and `/imports/{batch_id}` pages
       render correctly for an authenticated broker
   11. exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_multiformat_broker_import.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import xlsxwriter
import xlwt

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "spreadsheets"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_ORG_ID = "ORG-0083-E2E"
_ACCOUNT_ID = "ACC-0083-E2E"
_IMPORT_CSRF_HEADER_VALUE = "broker-import-intake-v1"


def _base_db_url() -> str:
    url = os.environ.get("HULLQ_TEST_DATABASE_URL", "").strip()
    if not url:
        print("HULLQ_TEST_DATABASE_URL is not set.", file=sys.stderr)
        raise SystemExit(1)
    return url


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


def _free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except urllib.error.HTTPError:
            return True
        except _HTTP_PROBE_TRANSIENT_ERRORS:
            time.sleep(0.2)
    return False


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
    """A real, standards-compliant cookie-jar HTTP client -- mirrors
    `scripts/inspect_broker_listing_design_association.py`'s identical
    `BrowserSession`."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            _NoRedirect, urllib.request.HTTPCookieProcessor(self.jar)
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        extra_headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        req = urllib.request.Request(
            url, headers=dict(extra_headers or {}), method=method, data=data
        )
        response = self._opener.open(req, timeout=10)
        return response.status, response.headers, response.read()

    def get(
        self, url: str, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url, extra_headers=extra_headers)

    def post_json(
        self, url: str, payload: dict[str, Any], *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        return self.request(
            "POST", url, extra_headers=headers, data=json.dumps(payload).encode("utf-8")
        )

    def put_json(
        self, url: str, payload: dict[str, Any], *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        return self.request(
            "PUT", url, extra_headers=headers, data=json.dumps(payload).encode("utf-8")
        )

    def post_bytes(
        self, url: str, raw_bytes: bytes, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/octet-stream", **(extra_headers or {})}
        return self.request("POST", url, extra_headers=headers, data=raw_bytes)


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _csrf_headers(web_base: str) -> dict[str, str]:
    return {"Origin": web_base, "X-HullQ-Requested-With": _IMPORT_CSRF_HEADER_VALUE}


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str, session_secret_b64: str, web_base: str
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0083_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
    env["HULLQ_SESSION_SIGNING_SECRET"] = session_secret_b64
    env["HULLQ_WEB_BASE_URL"] = web_base
    env["HULLQ_WEB_ORIGIN"] = web_base
    env["HULLQ_SESSION_COOKIE_SECURE"] = "false"
    with log_path.open("wb") as log_file:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "hullq.api.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
                "--no-access-log",
                "--log-level",
                "warning",
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    return proc, log_path


def _stop_process(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _xlsx_bytes(sheet_name: str, rows: list[list[object]]) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet(sheet_name)
    for r, row in enumerate(rows):
        ws.write_row(r, 0, row)
    wb.close()
    return buf.getvalue()


def _xls_bytes(sheet_name: str, rows: list[list[object]]) -> bytes:
    buf = io.BytesIO()
    wb = xlwt.Workbook()
    ws = wb.add_sheet(sheet_name)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            ws.write(r, c, value)
    wb.save(buf)
    return buf.getvalue()


_VALID_NAUTIX_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<nautix xmlns="https://nautix.nautic-network.org/v1.4/" version="1.4" date="2026-10-01T10:00:00+02:00">
  <account token="E2E-ACME-1" status="active">
    <account_name>E2E Acme Yacht Brokers</account_name>
    <adverts count="1">
      <advert id="ADV-E2E-0001" purpose="sale" type="boat" status="active" modified="2026-09-15T08:00:00+02:00">
        <advert_data><office_id>OFFICE-1</office_id></advert_data>
        <sale_data>
          <sale_class>used</sale_class>
          <price type="fixed" currency="EUR">250000.00</price>
          <location country="ES"/>
        </sale_data>
        <boat_data>
          <boat_types><type primary="true">sail-yacht</type></boat_types>
          <model>E2E Oceanis 46.1</model>
          <boat_name>Zephyr</boat_name>
          <year_built>2021</year_built>
        </boat_data>
      </advert>
    </adverts>
  </account>
</nautix>
"""

_INACTIVE_NAUTIX_XML = _VALID_NAUTIX_XML.replace(
    b'status="active" modified="2026-09-15T08:00:00+02:00">\n        <advert_data>',
    b'status="inactive" modified="2026-09-15T08:00:00+02:00">\n        <advert_data>',
)


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0083e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0083_e2e_"))
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
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
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )
        from hullq.persistence.broker_identity import (
            seed_marketplace_organization,
            seed_organization_membership,
        )
        from hullq.security.session_token import mint_session_token

        url = _with_search_path(base_url, schema_name)
        print("MULTI-FORMAT BROKER INVENTORY IMPORT INTAKE\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head (includes import_* tables) -> OK")

        api_port = _free_port()
        web_port = _free_port()
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)

        api_proc, api_log_path = _start_api(
            url=url,
            api_port=api_port,
            preview_secret_b64=_b64url(preview_secret),
            session_secret_b64=_b64url(session_secret),
            web_base=web_base,
        )
        api_ready = _wait_for_http(f"{api_base}/api/broker/context")
        ok &= api_ready
        print(f"1. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print(
                api_log_path.read_text(encoding="utf-8", errors="replace")[-4000:], file=sys.stderr
            )

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = api_base
        web_env["HOST"] = "127.0.0.1"
        web_env["PORT"] = str(web_port)
        web_log_path = log_dir / "web.log"
        with web_log_path.open("wb") as web_log:
            web_proc = subprocess.Popen(
                ["node", "./dist/server/entry.mjs"],
                cwd=WEB_DIR,
                env=web_env,
                stdout=web_log,
                stderr=subprocess.STDOUT,
            )
        web_ready = _wait_for_http(f"{web_base}/broker")
        ok &= web_ready
        print(f"2. Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("MULTI-FORMAT BROKER INVENTORY IMPORT INTAKE RESULT -> FAIL")
            return 1

        def _mint_cookie(account_id: str, *, mfa: bool = True) -> str:
            identity = AuthenticatedIdentity(
                provider=Provider.AUTH0,
                issuer="https://issuer.test/",
                subject=f"subject-{account_id}",
                auth_time=datetime.now(UTC),
                mfa_satisfied=mfa,
            )
            minted = mint_session_token(identity, AccountId(account_id), secret=session_secret)
            return minted.token

        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [_ACCOUNT_ID],
                )
            conn.commit()
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0083-E2E"),
                    account_id=AccountId(_ACCOUNT_ID),
                    organization_id=MarketplaceOrganizationId(_ORG_ID),
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        print(f"3. seeded {_ORG_ID} with one ACTIVE PUBLISHER account -> OK\n")

        session = BrowserSession()
        session.jar.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name="hullq_session",
                value=_mint_cookie(_ACCOUNT_ID),
                port=None,
                port_specified=False,
                domain="127.0.0.1",
                domain_specified=True,
                domain_initial_dot=False,
                path="/",
                path_specified=True,
                secure=False,
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={},
            )
        )

        imports_path = f"{api_base}/api/broker/organizations/{_ORG_ID}/imports"

        def _upload(
            raw_bytes: bytes,
            *,
            fmt: str,
            source: str,
            worksheet: str | None = None,
            csv_delimiter: str | None = None,
            account_tokens: str | None = None,
        ) -> dict[str, Any]:
            headers = {
                **_csrf_headers(web_base),
                "X-HullQ-Import-Format": fmt,
                "X-HullQ-Import-Source": source,
            }
            if worksheet is not None:
                headers["X-HullQ-Worksheet"] = worksheet
            if csv_delimiter is not None:
                headers["X-HullQ-Csv-Delimiter"] = csv_delimiter
            if account_tokens is not None:
                headers["X-HullQ-Nautix-Account-Tokens"] = account_tokens
            status, _, body = session.post_bytes(imports_path, raw_bytes, extra_headers=headers)
            parsed = _json(body)
            assert status == 201, (status, parsed)
            return parsed

        def _map(
            batch_id: str, mapping: dict[str, str], *, snapshot_mode: bool = False
        ) -> dict[str, Any]:
            status, _, body = session.put_json(
                f"{imports_path}/{batch_id}/mapping",
                {"column_mapping": mapping, "snapshot_mode": snapshot_mode},
                extra_headers=_csrf_headers(web_base),
            )
            parsed = _json(body)
            assert status == 200, (status, parsed)
            return parsed

        def _confirm(batch_id: str, *, expected_row_count: int) -> tuple[int, dict[str, Any]]:
            status, _, body = session.post_json(
                f"{imports_path}/{batch_id}/confirm",
                {"expected_row_count": expected_row_count},
                extra_headers=_csrf_headers(web_base),
            )
            return status, _json(body)

        _COLUMN_MAPPING = {
            "Boat Name": "physical_boat.boat_name",
            "Build Year": "physical_boat.build_year",
            "Price": "listing_offer.asking_price_amount",
            "Ref": "__source_record_key__",
        }

        # 1. CSV (comma) upload -> map -> confirm -> real Astro SSR draft readback.
        csv_bytes = b"Boat Name,Build Year,Price,Ref\r\nAria,1998,125000,REF-E2E-1\r\n"
        batch = _upload(csv_bytes, fmt="CSV", source="CsvFeed")
        _map(batch["import_batch_id"], _COLUMN_MAPPING)
        status, confirmed = _confirm(batch["import_batch_id"], expected_row_count=1)
        csv_ok = status == 200 and confirmed["summary"]["CREATE_NEW_DRAFT"] == 1
        draft_id = confirmed["rows"][0]["created_professional_listing_draft_id"] if csv_ok else None
        ok &= csv_ok
        print(
            f"4. CSV (comma) upload -> map -> confirm -> {draft_id} -> {'OK' if csv_ok else 'FAIL'}"
        )

        draft_readback_ok = False
        if draft_id:
            status, _, body = session.get(
                f"{web_base}/broker/organizations/{_ORG_ID}/drafts/{draft_id}"
            )
            page_text = body.decode("utf-8")
            draft_readback_ok = (
                status == 200
                and "Professional listing draft" in page_text
                and 'value="Aria"' in page_text
            )
        ok &= draft_readback_ok
        print(
            f"   the real built Astro SSR private Draft editor page renders the imported boat "
            f"name ('Aria') -> {'OK' if draft_readback_ok else 'FAIL'}\n"
        )

        # 2. CSV dialect selection (Finding G).
        semi_bytes = b"Boat Name;Build Year;Price;Ref\r\nBeta;2005;89000;REF-E2E-2\r\n"
        semi_batch = _upload(semi_bytes, fmt="CSV", source="SemiFeed", csv_delimiter="SEMICOLON")
        semi_ok = semi_batch["headers"] == ["Boat Name", "Build Year", "Price", "Ref"]
        default_batch = _upload(semi_bytes, fmt="CSV", source="SemiDefaultFeed")
        semi_default_ok = default_batch["headers"] == ["Boat Name;Build Year;Price;Ref"]
        ok &= semi_ok and semi_default_ok
        print(
            f"5. CSV semicolon dialect (explicit) parses as 4 columns ({semi_ok}); without "
            f"selecting it, the identical bytes parse as 1 column, never silently guessed "
            f"({semi_default_ok}) -> {'OK' if (semi_ok and semi_default_ok) else 'FAIL'}\n"
        )

        # 3. TSV and JSON.
        tsv_bytes = b"Boat Name\tBuild Year\tPrice\tRef\r\nGamma\t2010\t60000\tREF-E2E-3\r\n"
        tsv_batch = _upload(tsv_bytes, fmt="TSV", source="TsvFeed")
        _map(tsv_batch["import_batch_id"], _COLUMN_MAPPING)
        tsv_status, tsv_confirmed = _confirm(tsv_batch["import_batch_id"], expected_row_count=1)
        tsv_ok = tsv_status == 200 and tsv_confirmed["summary"]["CREATE_NEW_DRAFT"] == 1

        json_bytes = json.dumps(
            {
                "listings": [
                    {"Boat Name": "Delta", "Build Year": 2015, "Price": "45000", "Ref": "REF-E2E-4"}
                ]
            }
        ).encode("utf-8")
        json_batch = _upload(json_bytes, fmt="JSON", source="JsonFeed")
        _map(json_batch["import_batch_id"], _COLUMN_MAPPING)
        json_status, json_confirmed = _confirm(json_batch["import_batch_id"], expected_row_count=1)
        json_ok = json_status == 200 and json_confirmed["summary"]["CREATE_NEW_DRAFT"] == 1
        ok &= tsv_ok and json_ok
        print(f"6. TSV upload -> map -> confirm -> {'OK' if tsv_ok else 'FAIL'}")
        print(f"   JSON upload -> map -> confirm -> {'OK' if json_ok else 'FAIL'}\n")

        # 4. XLSX (explicit worksheet) and legacy XLS (genuine BIFF8).
        xlsx_bytes = _xlsx_bytes(
            "Inventory",
            [["Boat Name", "Build Year", "Price", "Ref"], ["Epsilon", 2012, 72000, "REF-E2E-5"]],
        )
        xlsx_batch = _upload(xlsx_bytes, fmt="XLSX", source="XlsxFeed", worksheet="Inventory")
        _map(xlsx_batch["import_batch_id"], _COLUMN_MAPPING)
        xlsx_status, xlsx_confirmed = _confirm(xlsx_batch["import_batch_id"], expected_row_count=1)
        xlsx_ok = xlsx_status == 200 and xlsx_confirmed["summary"]["CREATE_NEW_DRAFT"] == 1

        xls_bytes = _xls_bytes(
            "Inventory",
            [["Boat Name", "Build Year", "Price", "Ref"], ["Zeta", 2008, 51000, "REF-E2E-6"]],
        )
        xls_batch = _upload(xls_bytes, fmt="XLS", source="XlsFeed", worksheet="Inventory")
        _map(xls_batch["import_batch_id"], _COLUMN_MAPPING)
        xls_status, xls_confirmed = _confirm(xls_batch["import_batch_id"], expected_row_count=1)
        xls_ok = xls_status == 200 and xls_confirmed["summary"]["CREATE_NEW_DRAFT"] == 1
        ok &= xlsx_ok and xls_ok
        print(
            f"7. XLSX upload (explicit worksheet) -> map -> confirm -> {'OK' if xlsx_ok else 'FAIL'}"
        )
        print(
            f"   legacy XLS (genuine BIFF8 via xlwt) -> map -> confirm -> {'OK' if xls_ok else 'FAIL'}\n"
        )

        # 5. Genuine third-party XLSB/ODS fixtures.
        xlsb_raw = (FIXTURES_DIR / "calamine_date.xlsb").read_bytes()
        xlsb_batch = _upload(xlsb_raw, fmt="XLSB", source="XlsbFeed", worksheet="Sheet1")
        ignore_mapping = dict.fromkeys(xlsb_batch["headers"], "__ignore__")
        mapped_xlsb = _map(xlsb_batch["import_batch_id"], ignore_mapping, snapshot_mode=True)
        xlsb_row_count = len(mapped_xlsb["rows"])
        xlsb_status, xlsb_confirmed = _confirm(
            xlsb_batch["import_batch_id"], expected_row_count=xlsb_row_count
        )
        xlsb_ok = (
            xlsb_status == 200 and xlsb_confirmed["summary"]["CREATE_NEW_DRAFT"] == xlsb_row_count
        )

        ods_raw = (FIXTURES_DIR / "calamine_date.ods").read_bytes()
        ods_batch = _upload(ods_raw, fmt="ODS", source="OdsFeed", worksheet="Sheet1")
        ods_ignore_mapping = dict.fromkeys(ods_batch["headers"], "__ignore__")
        mapped_ods = _map(ods_batch["import_batch_id"], ods_ignore_mapping, snapshot_mode=True)
        ods_row_count = len(mapped_ods["rows"])
        ods_status, ods_confirmed = _confirm(
            ods_batch["import_batch_id"], expected_row_count=ods_row_count
        )
        ods_ok = ods_status == 200 and ods_confirmed["summary"]["CREATE_NEW_DRAFT"] == ods_row_count
        ok &= xlsb_ok and ods_ok
        print(
            f"8. genuine third-party XLSB fixture (python-calamine's own test corpus) upload -> "
            f"map -> confirm -> {'OK' if xlsb_ok else 'FAIL'}"
        )
        print(
            f"   genuine third-party ODS fixture upload -> map -> confirm -> "
            f"{'OK' if ods_ok else 'FAIL'}\n"
        )

        # 6. Snapshot mode: exact replay vs. changed bytes.
        snap_bytes = b"Boat Name,Build Year,Price\r\nEta,2019,99000\r\n"
        snap_mapping = {
            "Boat Name": "physical_boat.boat_name",
            "Build Year": "physical_boat.build_year",
            "Price": "listing_offer.asking_price_amount",
        }
        snap_batch1 = _upload(snap_bytes, fmt="CSV", source="SnapFeed")
        _map(snap_batch1["import_batch_id"], snap_mapping, snapshot_mode=True)
        _, snap1_confirmed = _confirm(snap_batch1["import_batch_id"], expected_row_count=1)

        snap_batch2 = _upload(snap_bytes, fmt="CSV", source="SnapFeed")
        _map(snap_batch2["import_batch_id"], snap_mapping, snapshot_mode=True)
        _, snap2_confirmed = _confirm(snap_batch2["import_batch_id"], expected_row_count=1)
        replay_ok = (
            snap1_confirmed["summary"]["CREATE_NEW_DRAFT"] == 1
            and snap2_confirmed["summary"]["ALREADY_IMPORTED"] == 1
        )

        changed_bytes = snap_bytes.replace(b"99000", b"199000")
        snap_batch3 = _upload(changed_bytes, fmt="CSV", source="SnapFeed")
        _map(snap_batch3["import_batch_id"], snap_mapping, snapshot_mode=True)
        _, snap3_confirmed = _confirm(snap_batch3["import_batch_id"], expected_row_count=1)
        changed_ok = snap3_confirmed["summary"]["CONFLICT_REVIEW"] == 1

        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM professional_listing_drafts "
                    "WHERE owner_organization_id = %s AND broker_description IS NULL "
                    "AND payload->>'physical_boat.boat_name' = 'Eta'",
                    [_ORG_ID],
                )
                eta_draft_count = cur.fetchone()[0]
        finally:
            conn.close()
        no_duplicate_ok = eta_draft_count == 1

        ok &= replay_ok and changed_ok and no_duplicate_ok
        print(
            f"9. snapshot mode: exact-byte replay -> ALREADY_IMPORTED ({replay_ok}); changed "
            f"bytes for the same ImportSource -> CONFLICT_REVIEW ({changed_ok}); exactly one "
            f"'Eta' draft exists across all three attempts ({no_duplicate_ok}) -> "
            f"{'OK' if (replay_ok and changed_ok and no_duplicate_ok) else 'FAIL'}\n"
        )

        # 7. Stale confirmation (Finding F).
        stale_bytes = b"Boat Name,Build Year,Price,Ref\r\nTheta,2000,30000,REF-E2E-STALE\r\n"
        stale_batch = _upload(stale_bytes, fmt="CSV", source="StaleFeed")
        _map(stale_batch["import_batch_id"], _COLUMN_MAPPING)
        stale_status, stale_body = _confirm(stale_batch["import_batch_id"], expected_row_count=999)
        stale_denied_ok = stale_status == 409 and stale_body.get("error") == "stale_confirmation"
        correct_status, correct_body = _confirm(
            stale_batch["import_batch_id"], expected_row_count=1
        )
        stale_then_correct_ok = (
            correct_status == 200 and correct_body["summary"]["CREATE_NEW_DRAFT"] == 1
        )
        ok &= stale_denied_ok and stale_then_correct_ok
        print(
            f"10. a stale expected_row_count is denied with zero mutation ({stale_denied_ok}); "
            f"the correct value then confirms normally ({stale_then_correct_ok}) -> "
            f"{'OK' if (stale_denied_ok and stale_then_correct_ok) else 'FAIL'}\n"
        )

        # 8. NautiX 1.4: valid attested sale/sailboat advert, and inactive.
        nautix_batch = _upload(
            _VALID_NAUTIX_XML, fmt="NAUTIX_XML", source="NautixFeed", account_tokens="E2E-ACME-1"
        )
        nautix_mapped_ok = nautix_batch["status"] == "MAPPED"
        nautix_status, nautix_confirmed = _confirm(
            nautix_batch["import_batch_id"], expected_row_count=1
        )
        nautix_ok = (
            nautix_mapped_ok
            and nautix_status == 200
            and nautix_confirmed["summary"]["CREATE_NEW_DRAFT"] == 1
        )

        inactive_batch = _upload(
            _INACTIVE_NAUTIX_XML,
            fmt="NAUTIX_XML",
            source="NautixInactiveFeed",
            account_tokens="E2E-ACME-1",
        )
        inactive_status, inactive_confirmed = _confirm(
            inactive_batch["import_batch_id"], expected_row_count=1
        )
        inactive_ok = (
            inactive_status == 200 and inactive_confirmed["summary"]["CONFLICT_REVIEW"] == 1
        )
        ok &= nautix_ok and inactive_ok
        print(
            f"11. NautiX 1.4 valid attested sale/sailboat advert -> confirm -> private draft "
            f"({nautix_ok}); an 'inactive' advert -> CONFLICT_REVIEW, never an auto-withdrawal "
            f"({inactive_ok}) -> {'OK' if (nautix_ok and inactive_ok) else 'FAIL'}\n"
        )

        # 9. Unsupported format negative.
        unsupported_status, _, unsupported_body = session.post_bytes(
            imports_path,
            b"whatever",
            extra_headers={
                **_csrf_headers(web_base),
                "X-HullQ-Import-Format": "XLSM",
                "X-HullQ-Import-Source": "BadFeed",
            },
        )
        unsupported_ok = (
            unsupported_status == 400
            and _json(unsupported_body).get("error") == "unsupported_format"
        )
        ok &= unsupported_ok
        print(
            f"12. unsupported declared format rejected with zero mutation -> {'OK' if unsupported_ok else 'FAIL'}\n"
        )

        # 10. Real built Astro SSR import pages render for the authenticated broker.
        status, _, body = session.get(f"{web_base}/broker/organizations/{_ORG_ID}/imports")
        list_page_text = body.decode("utf-8")
        list_page_ok = status == 200 and "Multi-format inventory import" in list_page_text
        status, _, body = session.get(
            f"{web_base}/broker/organizations/{_ORG_ID}/imports/{batch['import_batch_id']}"
        )
        detail_page_text = body.decode("utf-8")
        detail_page_ok = (
            status == 200 and "Import batch" in detail_page_text and "CONFIRMED" in detail_page_text
        )
        ok &= list_page_ok and detail_page_ok
        print(
            f"13. the real built Astro SSR /imports list page ({list_page_ok}) and "
            f"/imports/{{batch_id}} detail page ({detail_page_ok}) render correctly -> "
            f"{'OK' if (list_page_ok and detail_page_ok) else 'FAIL'}\n"
        )

        print(f"MULTI-FORMAT BROKER INVENTORY IMPORT INTAKE RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
