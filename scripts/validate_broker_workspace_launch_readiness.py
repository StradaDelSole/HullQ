"""SLICE-0076 Broker Workspace Launch Validation harness — real PostgreSQL +
real HTTP, following the exact three-real-service discipline already
accepted for this package's other vertical proofs (e.g.
`scripts/inspect_broker_workspace_access.py`,
`scripts/inspect_professional_listing_draft_workspace.py`): a deterministic
local OIDC/JWKS test issuer, real FastAPI, and the built Astro/Node SSR web
package, driven entirely through real HTTP requests against the exact same
page URLs and `<form method="POST">` actions a signed-in browser would use.

Per `specs/BROKER_WORKSPACE_LAUNCH_VALIDATION_PROTOCOL.v0.1.md` §§2-4, this
script is the one representative-broker "participant": during every timed
task it only ever calls `web_base` page/form/upload-proxy URLs -- the exact
browser-visible surfaces -- never a direct FastAPI (`api_base`) call, direct
SQL or operator/admin shortcut. Database/API access is used only for
untimed environment setup (creating the Organization/membership before
timing starts, per protocol §2) and for starting/stopping the three local
servers.

This script never asserts a PASS/FAIL launch-gate disposition itself -- it
only produces the timed, stepped, evidence-bearing run this slice's retained
markdown evidence documents transcribe. See
`docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md` for the
disposition.

SLICE-0077 extends TASK_5 with one deliberate direct-persistence mutation
mid-task (deactivating a second member's Organization membership). That
write represents a concurrent *external* actor (e.g. another admin), not the
timed broker-participant completing their own task through a DB shortcut --
the participant's own next action is still only ever a `web_base` form POST,
and the proof is exactly that it then fails closed rather than succeeding.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/validate_broker_workspace_launch_readiness.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import io
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import psycopg
from PIL import Image

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
    update_membership_state,
)
from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_ORG_ID = "ORG-0076-VALIDATION"
_SUBJECT = "broker-0076-subject"
#: SLICE-0077: a second current-ACTIVE member of the same Organization, used
#: to prove the assignment candidate picker offers more than just the signed
#: -in broker, and to exercise the "candidate deactivated between read and
#: submit fails closed" / "historical inactive assignee not rewritten" proof.
_SECOND_MEMBER_ACCOUNT_ID = "ACC-0077-SECOND-MEMBER"
_SECOND_MEMBER_MEMBERSHIP_ID = "OM-0077-SECOND-MEMBER"
#: An INACTIVE member of the same Organization -- must never be offered as a
#: candidate.
_INACTIVE_MEMBER_ACCOUNT_ID = "ACC-0077-INACTIVE-MEMBER"
_INACTIVE_MEMBER_MEMBERSHIP_ID = "OM-0077-INACTIVE-MEMBER"
#: An ACTIVE member of a different, foreign Organization -- must never be
#: offered as a candidate here.
_FOREIGN_ORG_ID = "ORG-0077-FOREIGN"
_FOREIGN_MEMBER_ACCOUNT_ID = "ACC-0077-FOREIGN-MEMBER"
_FOREIGN_MEMBER_MEMBERSHIP_ID = "OM-0077-FOREIGN-MEMBER"
_BUYER_LEAD_CSRF_HEADER_NAME = "X-HullQ-Requested-With"
_BUYER_LEAD_CSRF_HEADER_VALUE = "marketplace-buyer-lead-v1"

#: `except (A, B, C):` is reformatted by this repo's installed `ruff format`
#: into invalid Python 3 `except A, B, C:` syntax (see
#: `scripts/inspect_professional_listing_draft_workspace.py`'s identical
#: named-tuple workaround) -- referencing a named tuple sidesteps that.
_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)


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
    """Real, standards-compliant cookie-jar HTTP client with form-POST and
    raw-upload support -- mirrors this package's other real-HTTP proofs."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            _NoRedirect, urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.last_set_cookie_headers: list[str] = []

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
        status = response.status
        resp_headers = response.headers
        body = response.read()
        self.last_set_cookie_headers = resp_headers.get_all("Set-Cookie") or []
        return status, resp_headers, body

    def get(self, url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url)

    def post_form(
        self, url: str, fields: dict[str, str], *, origin: str
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": origin}
        return self.request(
            "POST", url, extra_headers=headers, data=urlencode(fields).encode("utf-8")
        )

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        origin: str,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/json", "Origin": origin, **(extra_headers or {})}
        return self.request(
            "POST", url, extra_headers=headers, data=json.dumps(payload).encode("utf-8")
        )

    def post_bytes(
        self, url: str, data: bytes, *, origin: str, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Origin": origin, **(extra_headers or {})}
        return self.request("POST", url, extra_headers=headers, data=data)

    def follow_full_login(self, login_url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        status, headers, body = self.get(login_url)
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, body = self.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}: {body!r}"
        callback_url = headers["Location"]
        return self.get(callback_url)


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _extract_assignee_candidate_values(html: str) -> list[str]:
    """Extract the current assignment-picker `<option value="...">` values
    from rendered Lead-detail HTML (SLICE-0077 contract §5/§7) -- the exact
    set of AccountIds the signed-in broker could discover and select
    through the visible `<select name="assignee_account_id">` control,
    excluding the empty placeholder option."""
    select_match = re.search(
        r'<select name="assignee_account_id"[^>]*>(.*?)</select>', html, re.DOTALL
    )
    if select_match is None:
        return []
    return [
        value for value in re.findall(r'<option value="([^"]*)"', select_match.group(1)) if value
    ]


def _ensure_account(conn: Any, account_id: str) -> None:
    """Insert one bare Account row for a seeded membership that is never
    logged in through the real OIDC flow (`organization_memberships.account_id`
    is a hard FK to `accounts.account_id`)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )


def _jpeg_bytes(color: tuple[int, int, int], size: tuple[int, int] = (640, 480)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


@dataclass
class TaskRecord:
    task_id: str
    title: str
    scenario: str
    steps: list[str] = field(default_factory=list)
    friction: list[str] = field(default_factory=list)
    errors_recovery: list[str] = field(default_factory=list)
    operator_assistance_required: bool = False
    outcome: str = "NOT_COMPLETED_ENVIRONMENT"
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "scenario": self.scenario,
            "steps": self.steps,
            "friction": self.friction,
            "errors_recovery": self.errors_recovery,
            "operator_assistance_required": self.operator_assistance_required,
            "outcome": self.outcome,
            "duration_seconds": round(self.duration_seconds, 3),
        }


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  npm ci --prefix web && npm run build --prefix web",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0076val_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0076_validation_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True
    records: list[TaskRecord] = []

    try:
        url = _with_search_path(base_url, schema_name)
        print("SLICE-0076 BROKER WORKSPACE LAUNCH VALIDATION HARNESS\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK\n")

        _ISSUER_HOST = "127.0.0.2"
        issuer_port = _free_port(_ISSUER_HOST)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{_ISSUER_HOST}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-s0076-client"
        client_secret = secrets.token_urlsafe(24)
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)

        issuer_code = (
            "import uvicorn\n"
            "from hullq.testing.oidc_test_issuer import create_test_issuer_app\n"
            f"app = create_test_issuer_app(issuer={issuer_base!r}, client_id={client_id!r}, "
            f"client_secret={client_secret!r}, redirect_uri={redirect_uri!r})\n"
            f"uvicorn.run(app, host={_ISSUER_HOST!r}, port={issuer_port}, log_level='warning')\n"
        )
        issuer_log_path = log_dir / "issuer.log"
        with issuer_log_path.open("wb") as issuer_log:
            issuer_proc = subprocess.Popen(
                [sys.executable, "-c", issuer_code],
                cwd=REPO_ROOT,
                stdout=issuer_log,
                stderr=subprocess.STDOUT,
            )
        issuer_ready = _wait_for_http(f"{issuer_base}.well-known/jwks.json")
        ok &= issuer_ready
        print(
            f"1. deterministic local OIDC/JWKS test issuer serving -> {'OK' if issuer_ready else 'FAIL'}"
        )

        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = _b64url(preview_secret)
        api_env["HULLQ_SESSION_SIGNING_SECRET"] = _b64url(session_secret)
        api_env["HULLQ_AUTH_ISSUER"] = issuer_base
        api_env["HULLQ_AUTH_AUTHORIZE_URL"] = f"{issuer_base}authorize"
        api_env["HULLQ_AUTH_TOKEN_URL"] = f"{issuer_base}token"
        api_env["HULLQ_AUTH_JWKS_URL"] = f"{issuer_base}.well-known/jwks.json"
        api_env["HULLQ_AUTH_CLIENT_ID"] = client_id
        api_env["HULLQ_AUTH_CLIENT_SECRET"] = client_secret
        api_env["HULLQ_AUTH_REDIRECT_URI"] = redirect_uri
        api_env["HULLQ_WEB_BASE_URL"] = web_base
        # The one exact accepted browser Origin for broker-write CSRF
        # validation (matches every other real-HTTP proof in this package,
        # e.g. `scripts/inspect_professional_listing_draft_workspace.py`).
        api_env["HULLQ_WEB_ORIGIN"] = web_base
        api_env["HULLQ_SESSION_COOKIE_SECURE"] = "false"

        api_log_path = log_dir / "api.log"
        with api_log_path.open("wb") as api_log:
            # Contract §17: a deterministic local/fake S3-compatible object
            # store is the accepted substitute for live Cloudflare R2
            # credentials outside production -- injected here via
            # `create_app(object_storage=...)` (constructor injection,
            # mirroring every media pytest fixture) rather than `--factory`,
            # since this validation run has no real R2 account.
            api_code = (
                "import uvicorn\n"
                "from hullq.api.app import create_app\n"
                "from hullq.storage.object_storage import InMemoryObjectStorage\n"
                "app = create_app(object_storage=InMemoryObjectStorage())\n"
                f"uvicorn.run(app, host='127.0.0.1', port={api_port}, log_level='warning')\n"
            )
            api_proc = subprocess.Popen(
                [sys.executable, "-c", api_code],
                cwd=REPO_ROOT,
                env=api_env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
            )
        api_ready = _wait_for_http(f"{api_base}/api/broker/context")
        ok &= api_ready
        print(f"2. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")

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
        print(f"3. Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("ENVIRONMENT SETUP RESULT -> FAIL")
            return 1

        # ------------------------------------------------------------------
        # UNTIMED SETUP: real login (JIT account), seed Organization/
        # membership, MFA step-up. Protocol §2 explicitly permits automated
        # setup/seeding before timing starts.
        # ------------------------------------------------------------------
        setup_t0 = time.monotonic()
        session = BrowserSession()
        login_url = f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT}"
        session.follow_full_login(login_url)
        status, _, body = session.get(f"{api_base}/api/broker/context")
        assert status == 200, f"expected 200 from /api/broker/context, got {status}"
        account_id = _json(body)["account_id"]

        conn = psycopg.connect(url)
        try:
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
                    id=OrganizationMembershipId("OM-0076-A"),
                    account_id=AccountId(account_id),
                    organization_id=MarketplaceOrganizationId(_ORG_ID),
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )

            # SLICE-0077: a second current-ACTIVE same-Organization member
            # (candidate picker must offer more than just the signed-in
            # broker), an INACTIVE same-Organization member, and an ACTIVE
            # member of a *different* Organization -- Task 5 proves neither
            # of the latter two is ever offered as an assignment candidate.
            _ensure_account(conn, _SECOND_MEMBER_ACCOUNT_ID)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId(_SECOND_MEMBER_MEMBERSHIP_ID),
                    account_id=AccountId(_SECOND_MEMBER_ACCOUNT_ID),
                    organization_id=MarketplaceOrganizationId(_ORG_ID),
                    roles=frozenset({MembershipRole.MEMBER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            _ensure_account(conn, _INACTIVE_MEMBER_ACCOUNT_ID)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId(_INACTIVE_MEMBER_MEMBERSHIP_ID),
                    account_id=AccountId(_INACTIVE_MEMBER_ACCOUNT_ID),
                    organization_id=MarketplaceOrganizationId(_ORG_ID),
                    roles=frozenset({MembershipRole.MEMBER}),
                    state=MembershipState.INACTIVE,
                ),
            )
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_FOREIGN_ORG_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            _ensure_account(conn, _FOREIGN_MEMBER_ACCOUNT_ID)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId(_FOREIGN_MEMBER_MEMBERSHIP_ID),
                    account_id=AccountId(_FOREIGN_MEMBER_ACCOUNT_ID),
                    organization_id=MarketplaceOrganizationId(_FOREIGN_ORG_ID),
                    roles=frozenset({MembershipRole.MEMBER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        stepup_login_url = (
            f"{api_base}/api/auth/login?next=/broker/organizations/{_ORG_ID}"
            f"&login_hint={_SUBJECT}&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        session.follow_full_login(stepup_login_url)
        setup_seconds = time.monotonic() - setup_t0
        print(
            f"4. untimed setup complete (real login, seeded Organization/PUBLISHER membership, "
            f"MFA step-up) in {setup_seconds:.2f}s (environment time, excluded from task timing)\n"
        )

        def org_url(path: str) -> str:
            return f"{web_base}/broker/organizations/{_ORG_ID}{path}"

        native_listing_id: str = ""
        lead_id: str = ""

        # ------------------------------------------------------------------
        # TASK 1 — create + publish listing
        # ------------------------------------------------------------------
        rec = TaskRecord(
            task_id="TASK_1",
            title="Create + publish listing",
            scenario=(
                "Representative broker, already authenticated in an authorized Organization "
                "workspace, already knows the vessel's brand/model/build year/asking price/"
                "location/description from their own paperwork and starts a new listing."
            ),
        )
        t0 = time.monotonic()
        try:
            status, _, body = session.get(org_url("/drafts"))
            rec.steps.append(f"GET drafts list -> {status}")
            assert status == 200

            status, headers, _post_body = session.post_form(org_url("/drafts"), {}, origin=web_base)
            rec.steps.append(f"POST start a draft -> {status}")
            assert status == 303, (
                f"expected 303, got {status}: {_post_body.decode('utf-8', 'replace')[:800]!r}"
            )
            draft_path = urlsplit(headers["Location"]).path
            draft_url = f"{web_base}{draft_path}"

            status, _, body = session.get(draft_url)
            rec.steps.append(f"GET fresh draft -> {status}")
            html = body.decode("utf-8")
            version = int(re.search(r"Version:\s*(\d+)", html).group(1))

            status, _, body = session.post_form(
                draft_url,
                {
                    "intent": "save",
                    "expected_version": str(version),
                    "broker_listing_reference": "VAL-2026-0076-1",
                    "physical_boat.marketed_brand_claim": "Beneteau",
                    "physical_boat.model_designation_claim": "Oceanis 30.1",
                    "physical_boat.build_year.assertion_kind": "VALUE_ASSERTION",
                    "physical_boat.build_year": "2019",
                    "physical_boat.boat_name": "Validation One",
                    "listing_offer.asking_price_mode": "AMOUNT",
                    "listing_offer.asking_price_amount": "89500.00",
                    "listing_offer.currency": "eur",
                    "listing_offer.location_country": "fr",
                    "listing_offer.location_region": "Brittany",
                    "listing_offer.broker_description": "Well-maintained, one owner, recent sails.",
                },
                origin=web_base,
            )
            rec.steps.append(f"POST save required fields -> {status}")
            html = body.decode("utf-8")
            assert "Saved." in html, "expected Saved. confirmation after save"
            assert "ready to promote" in html, (
                f"draft not reported ready to promote: {html[:400]!r}"
            )
            version = int(re.search(r"Version:\s*(\d+)", html).group(1))

            status, _, body = session.post_form(
                draft_url, {"intent": "promote", "expected_version": str(version)}, origin=web_base
            )
            rec.steps.append(f"POST promote draft -> {status}")
            html = body.decode("utf-8")
            assert "Promotion succeeded." in html or "Promoted." in html, (
                f"promotion did not succeed: {html[:400]!r}"
            )
            m = re.search(r"<code>([^<]+)</code>", html)
            assert m, "expected promoted NativeListingId in response"
            native_listing_id = m.group(1).strip()
            rec.steps.append(f"promoted -> NativeListingId {native_listing_id}")

            media_url = org_url(f"/inventory/{native_listing_id}/media")
            status, _, body = session.get(media_url)
            rec.steps.append(f"GET media gallery (empty) -> {status}")
            html = body.decode("utf-8")
            assert "No media yet" in html

            upload_url = f"{web_base}/broker/organizations/{_ORG_ID}/inventory/{native_listing_id}/media/upload"
            status, _, body = session.post_bytes(
                upload_url,
                _jpeg_bytes((40, 90, 160)),
                origin=web_base,
                extra_headers={
                    "Content-Type": "image/jpeg",
                    "X-HullQ-Rights-Confirmed": "true",
                    "X-HullQ-Source-Reference": "validation harness cover image",
                },
            )
            rec.steps.append(
                f"POST upload cover image (streamed, same contract as the browser's own upload script) -> {status}"
            )
            assert status == 201, f"expected 201 Uploaded, got {status}: {body!r}"

            status, _, body = session.get(media_url)
            rec.steps.append(f"GET media gallery (1 image) -> {status}")
            html = body.decode("utf-8")
            gallery_version = int(re.search(r"Current gallery \(version (\d+)\)", html).group(1))
            m = re.search(
                r'name="action" value="set_cover">\s*<input type="hidden" name="media_placement_id" value="([^"]+)"',
                html,
            )
            assert m, f"expected a 'Make cover' candidate placement: {html[:800]!r}"
            placement_id = m.group(1)

            status, _, body = session.post_form(
                media_url,
                {
                    "action": "set_cover",
                    "media_placement_id": placement_id,
                    "expected_version": str(gallery_version),
                },
                origin=web_base,
            )
            rec.steps.append(f"POST set cover -> {status}")
            html = body.decode("utf-8")
            assert "Cover updated." in html, f"cover was not updated: {html[:400]!r}"

            inventory_url = org_url("/inventory")
            status, _, body = session.get(inventory_url)
            rec.steps.append(f"GET inventory overview -> {status}")
            html = body.decode("utf-8")
            assert "Ready to publish" in html, (
                f"listing not reported ready to publish: {html[:800]!r}"
            )

            status, _, body = session.post_form(
                inventory_url,
                {"native_listing_id": native_listing_id, "action": "publish"},
                origin=web_base,
            )
            rec.steps.append(f"POST publish -> {status}")
            html = body.decode("utf-8")
            assert "Published." in html, f"publish did not succeed: {html[:400]!r}"
            assert ">ACTIVE<" in html or "ACTIVE" in html

            rec.outcome = "PASS"
        except Exception as exc:
            rec.outcome = "BLOCKING_DEFICIENCY"
            rec.errors_recovery.append(str(exc))
        rec.duration_seconds = time.monotonic() - t0
        records.append(rec)
        print(f"TASK 1 ({rec.outcome}) in {rec.duration_seconds:.2f}s")
        if rec.errors_recovery:
            print("   ERROR:", rec.errors_recovery[-1])

        # ------------------------------------------------------------------
        # TASK 2 — edit price / status / details
        # ------------------------------------------------------------------
        rec = TaskRecord(
            task_id="TASK_2",
            title="Edit price / status / details",
            scenario="Same broker revisits their just-published ACTIVE listing to correct the asking price and a PhysicalBoat fact, then reconfirms freshness.",
        )
        t0 = time.monotonic()
        try:
            edit_url = org_url(f"/inventory/{native_listing_id}/edit")
            status, _, body = session.get(edit_url)
            rec.steps.append(f"GET edit listing -> {status}")
            html = body.decode("utf-8")
            offer_block = html.split("<h2>Offer</h2>", 1)[1].split(
                "<h2>PhysicalBoat claim</h2>", 1
            )[0]
            offer_revision_id = re.search(
                r'name="expected_current_revision_id"\s+value="([^"]*)"', offer_block
            ).group(1)

            status, _, body = session.post_form(
                edit_url,
                {
                    "action": "save_offer",
                    "revision_id": str(uuid.uuid4()),
                    "expected_current_revision_id": offer_revision_id,
                    "asking_price_mode": "AMOUNT",
                    "asking_price_amount": "87900.00",
                    "currency": "EUR",
                    "location_country": "FR",
                    "broker_description": "Price reduced -- motivated seller.",
                    "location_region_kind": "",
                    "location_region_value": "",
                    "broker_summary_kind": "",
                    "broker_summary_value": "",
                    "known_history_narrative_kind": "",
                    "known_history_narrative_value": "",
                    "vat_tax_status_claim_kind": "",
                    "vat_tax_status_claim_value": "VAT_PAID",
                },
                origin=web_base,
            )
            rec.steps.append(f"POST save offer (edit price) -> {status}")
            html = body.decode("utf-8")
            assert "Saved." in html, f"offer save did not succeed: {html[:400]!r}"
            assert "87900.00" in html, "edited price not reflected on authoritative re-read"

            claim_block = html.split("<h2>PhysicalBoat claim</h2>", 1)[1].split(
                "<h2>Sale / outcome</h2>", 1
            )[0]
            claim_revision_id = re.search(
                r'name="expected_current_revision_id"\s+value="([^"]*)"', claim_block
            ).group(1)
            status, _, body = session.post_form(
                edit_url,
                {
                    "action": "save_claim",
                    "revision_id": str(uuid.uuid4()),
                    "expected_current_revision_id": claim_revision_id,
                    "marketed_brand_claim": "Beneteau",
                    "model_designation_claim": "Oceanis 30.1 (refit)",
                    "build_year_kind": "VALUE_ASSERTION",
                    "build_year_value": "2019",
                    "loa_length_kind": "",
                    "loa_length_value": "",
                    "draft_kind": "",
                    "draft_value": "",
                    "keel_configuration_kind": "",
                    "keel_configuration_value": "FIN",
                    "rudder_configuration_kind": "",
                    "rudder_configuration_value": "SPADE",
                    "boat_name_kind": "",
                    "boat_name_value": "",
                },
                origin=web_base,
            )
            rec.steps.append(f"POST save claim (edit PhysicalBoat fact) -> {status}")
            html = body.decode("utf-8")
            assert "Saved." in html, f"claim save did not succeed: {html[:400]!r}"
            assert "Oceanis 30.1 (refit)" in html, (
                "edited model designation not reflected on authoritative re-read"
            )

            status, _, body = session.get(inventory_url := org_url("/inventory"))
            rec.steps.append(f"GET inventory (locate Reconfirm action) -> {status}")
            html = body.decode("utf-8")
            m = re.search(r'name="confirmation_id" value="([^"]+)"', html)
            assert m, f"expected a Reconfirm control on the ACTIVE listing: {html[:800]!r}"

            status, _, body = session.post_form(
                inventory_url,
                {
                    "native_listing_id": native_listing_id,
                    "action": "reconfirm",
                    "confirmation_id": str(uuid.uuid4()),
                },
                origin=web_base,
            )
            rec.steps.append(f"POST reconfirm (freshness/lifecycle action) -> {status}")
            html = body.decode("utf-8")
            assert "Reconfirmed." in html, f"reconfirm did not succeed: {html[:400]!r}"
            assert "last confirmed" in html, (
                "freshness re-read did not show last-confirmed evidence"
            )

            rec.outcome = "PASS"
        except Exception as exc:
            rec.outcome = "BLOCKING_DEFICIENCY"
            rec.errors_recovery.append(str(exc))
        rec.duration_seconds = time.monotonic() - t0
        records.append(rec)
        print(f"TASK 2 ({rec.outcome}) in {rec.duration_seconds:.2f}s")
        if rec.errors_recovery:
            print("   ERROR:", rec.errors_recovery[-1])

        # ------------------------------------------------------------------
        # TASK 3 — media management
        # ------------------------------------------------------------------
        rec = TaskRecord(
            task_id="TASK_3",
            title="Media management",
            scenario="Same broker adds two more photos, reorders the gallery, changes the cover image, and tries an invalid YouTube link to see what happens.",
        )
        t0 = time.monotonic()
        try:
            media_url = org_url(f"/inventory/{native_listing_id}/media")
            upload_url = f"{web_base}/broker/organizations/{_ORG_ID}/inventory/{native_listing_id}/media/upload"
            for idx, color in enumerate(((200, 60, 60), (60, 200, 90)), start=1):
                status, _, body = session.post_bytes(
                    upload_url,
                    _jpeg_bytes(color),
                    origin=web_base,
                    extra_headers={
                        "Content-Type": "image/jpeg",
                        "X-HullQ-Rights-Confirmed": "true",
                        "X-HullQ-Source-Reference": f"validation harness image {idx}",
                    },
                )
                rec.steps.append(f"POST upload additional image {idx} -> {status}")
                assert status == 201, (
                    f"expected 201 Uploaded for image {idx}, got {status}: {body!r}"
                )

            status, _, body = session.get(media_url)
            rec.steps.append(f"GET media gallery (3 images) -> {status}")
            html = body.decode("utf-8")
            gallery_version = int(re.search(r"Current gallery \(version (\d+)\)", html).group(1))
            placement_ids = re.findall(
                r'name="action" value="remove">\s*<input type="hidden" name="media_placement_id" value="([^"]+)"',
                html,
            )
            assert len(placement_ids) == 3, f"expected 3 placements, found {len(placement_ids)}"
            positions = {
                pid: int(
                    re.search(rf'name="position_{re.escape(pid)}" value="(\d+)"', html).group(1)
                )
                for pid in placement_ids
            }

            first, second = placement_ids[0], placement_ids[1]
            reorder_fields = {
                "action": "reorder",
                "expected_version": str(gallery_version),
            }
            for pid, pos in positions.items():
                if pid == first:
                    reorder_fields[f"position_{pid}"] = str(positions[second])
                elif pid == second:
                    reorder_fields[f"position_{pid}"] = str(positions[first])
                else:
                    reorder_fields[f"position_{pid}"] = str(pos)
            status, _, body = session.post_form(media_url, reorder_fields, origin=web_base)
            rec.steps.append(f"POST reorder gallery (swap first two positions) -> {status}")
            html = body.decode("utf-8")
            assert "Order saved." in html, f"reorder did not succeed: {html[:400]!r}"

            gallery_version = int(re.search(r"Current gallery \(version (\d+)\)", html).group(1))
            m = re.search(
                r'name="action" value="set_cover">\s*<input type="hidden" name="media_placement_id" value="([^"]+)"',
                html,
            )
            assert m, f"expected another cover candidate to change to: {html[:800]!r}"
            new_cover_id = m.group(1)
            status, _, body = session.post_form(
                media_url,
                {
                    "action": "set_cover",
                    "media_placement_id": new_cover_id,
                    "expected_version": str(gallery_version),
                },
                origin=web_base,
            )
            rec.steps.append(f"POST change cover to a different image -> {status}")
            html = body.decode("utf-8")
            assert "Cover updated." in html, f"cover change did not succeed: {html[:400]!r}"

            status, _, body = session.post_form(
                media_url,
                {"action": "youtube_add", "youtube_url": "not-a-real-url"},
                origin=web_base,
            )
            rec.steps.append(
                f"POST add invalid YouTube URL (deliberate invalid-input path) -> {status}"
            )
            html = body.decode("utf-8")
            assert "That YouTube link isn" in html and "supported." in html, (
                f"invalid YouTube URL did not produce a recoverable, understandable message: {html[:400]!r}"
            )
            assert "<h2>Current gallery" in html, (
                "gallery state must still render after the rejected input"
            )
            rec.errors_recovery.append(
                "Invalid YouTube URL was rejected with an explicit, specific message "
                '("That YouTube link isn\'t supported.") and the existing gallery/cover state '
                "remained intact and visible -- a clear, recoverable error path."
            )

            rec.outcome = "PASS"
        except Exception as exc:
            rec.outcome = "BLOCKING_DEFICIENCY"
            rec.errors_recovery.append(str(exc))
        rec.duration_seconds = time.monotonic() - t0
        records.append(rec)
        print(f"TASK 3 ({rec.outcome}) in {rec.duration_seconds:.2f}s")
        if rec.errors_recovery:
            print("   ERROR:", rec.errors_recovery[-1])

        # ------------------------------------------------------------------
        # UNTIMED SETUP for tasks 4-6: an anonymous buyer contacts the
        # now-published listing through the ordinary public contact route
        # (buyer-side, not the broker-participant being timed).
        # ------------------------------------------------------------------
        buyer_session = BrowserSession()
        contact_url = f"{web_base}/listings/{native_listing_id}/contact"
        status, _, body = buyer_session.post_json(
            contact_url,
            {
                "submission_operation_id": str(uuid.uuid4()),
                "name": "Validation Buyer",
                "email": "validation-buyer@example.invalid",
                "message": "Is this boat still available? I'd like more photos.",
            },
            origin=web_base,
            extra_headers={_BUYER_LEAD_CSRF_HEADER_NAME: _BUYER_LEAD_CSRF_HEADER_VALUE},
        )
        assert status == 201, f"expected 201 from buyer contact, got {status}: {body!r}"
        lead_id = _json(body)["lead_id"]
        print(
            f"5. untimed setup: seeded one BuyerLead ({lead_id}) via the ordinary public contact route\n"
        )

        # ------------------------------------------------------------------
        # TASK 4 — Lead source identification
        # ------------------------------------------------------------------
        rec = TaskRecord(
            task_id="TASK_4",
            title="Lead source identification",
            scenario="Same broker opens the Lead inbox to see a new buyer inquiry and identify which listing it concerns and where it came from.",
        )
        t0 = time.monotonic()
        try:
            leads_url = org_url("/leads")
            status, _, body = session.get(leads_url)
            rec.steps.append(f"GET Lead inbox -> {status}")
            html = body.decode("utf-8")
            assert lead_id in html, "new Lead not visible in the inbox"

            lead_detail_url = org_url(f"/leads/{lead_id}")
            status, _, body = session.get(lead_detail_url)
            rec.steps.append(f"GET Lead detail -> {status}")
            html = body.decode("utf-8")
            assert native_listing_id in html, (
                "contacted listing not identified on the Lead detail page"
            )
            assert "Acquisition channel:" in html and "Discovery surface:" in html, (
                "acquisition/discovery evidence not rendered"
            )
            m_acq = re.search(r"Acquisition channel:\s*([A-Z_]+)", html)
            m_disc = re.search(r"Discovery surface:\s*([A-Z_]+)", html)
            rec.steps.append(
                f"acquisition_channel={m_acq.group(1) if m_acq else 'MISSING'}, "
                f"discovery_surface={m_disc.group(1) if m_disc else 'MISSING'} "
                "(explicit value shown, UNKNOWN is an accepted explicit outcome, not a failure)"
            )
            rec.outcome = "PASS"
        except Exception as exc:
            rec.outcome = "BLOCKING_DEFICIENCY"
            rec.errors_recovery.append(str(exc))
        rec.duration_seconds = time.monotonic() - t0
        records.append(rec)
        print(f"TASK 4 ({rec.outcome}) in {rec.duration_seconds:.2f}s")
        if rec.errors_recovery:
            print("   ERROR:", rec.errors_recovery[-1])

        # ------------------------------------------------------------------
        # TASK 5 — Lead handling
        # ------------------------------------------------------------------
        rec = TaskRecord(
            task_id="TASK_5",
            title="Lead handling",
            scenario="Same broker marks the Lead read, discovers a visible assignment candidate and assigns it, updates its status, sets a follow-up, adds a note, records a contact attempt, and re-finds it via the inbox filters.",
        )
        t0 = time.monotonic()
        try:
            lead_detail_url = org_url(f"/leads/{lead_id}")
            status, _, body = session.get(lead_detail_url)
            html = body.decode("utf-8")
            version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            if "Unread" in html:
                status, _, body = session.post_form(
                    lead_detail_url, {"action": "mark_read"}, origin=web_base
                )
                rec.steps.append(f"POST mark read -> {status}")
                html = body.decode("utf-8")
                assert "Done." in html and "Read" in html, "mark-read did not succeed"
                version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            # SLICE-0077: the Assign control is now a `<select>` populated
            # from the real assignment-candidate projection -- discover a
            # valid candidate from the rendered picker itself, never from
            # prior knowledge of an opaque AccountId.
            candidate_values = _extract_assignee_candidate_values(html)
            rec.steps.append(
                f"discovered {len(candidate_values)} assignment candidate(s) from the rendered picker"
            )
            assert candidate_values, "no assignment candidate rendered in the visible picker"
            assert _INACTIVE_MEMBER_ACCOUNT_ID not in candidate_values, (
                "an INACTIVE same-Organization member was offered as a candidate"
            )
            assert _FOREIGN_MEMBER_ACCOUNT_ID not in candidate_values, (
                "a foreign-Organization member was offered as a candidate"
            )
            assert account_id in candidate_values, (
                "the signed-in broker's own ACTIVE membership was not offered as a candidate"
            )
            assert _SECOND_MEMBER_ACCOUNT_ID in candidate_values, (
                "a second current-ACTIVE same-Organization member was not offered as a candidate"
            )

            status, _, body = session.post_form(
                lead_detail_url,
                {
                    "action": "assign",
                    "assignee_account_id": account_id,
                    "expected_version": str(version),
                },
                origin=web_base,
            )
            rec.steps.append(
                f"POST assign using a candidate discovered from the visible picker -> {status}"
            )
            html = body.decode("utf-8")
            assert "Done." in html and f"Assigned: {account_id}" in html, (
                f"discoverable-candidate assignment did not succeed: {html[:400]!r}"
            )
            version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            # Reassign to the second candidate, then simulate that member's
            # Organization membership being deactivated by someone else
            # between this read and a later (stale) resubmission -- contract
            # §5/§7: the mutation must still fail closed, and the Lead's
            # stored historical assignee must not be silently rewritten
            # merely because the candidate list no longer offers it
            # (contract §6).
            status, _, body = session.post_form(
                lead_detail_url,
                {
                    "action": "assign",
                    "assignee_account_id": _SECOND_MEMBER_ACCOUNT_ID,
                    "expected_version": str(version),
                },
                origin=web_base,
            )
            rec.steps.append(f"POST reassign to second active candidate -> {status}")
            html = body.decode("utf-8")
            assert "Done." in html and f"Assigned: {_SECOND_MEMBER_ACCOUNT_ID}" in html, (
                f"reassignment to second candidate did not succeed: {html[:400]!r}"
            )
            version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            conn = psycopg.connect(url)
            try:
                update_membership_state(
                    conn,
                    OrganizationMembershipId(_SECOND_MEMBER_MEMBERSHIP_ID),
                    MembershipState.INACTIVE,
                )
                conn.commit()
            finally:
                conn.close()
            rec.steps.append(
                "simulated out-of-band deactivation of the currently-assigned second candidate's membership"
            )

            status, _, body = session.get(lead_detail_url)
            rec.steps.append(f"GET Lead detail after deactivation -> {status}")
            html = body.decode("utf-8")
            assert f"Assigned: {_SECOND_MEMBER_ACCOUNT_ID}" in html, (
                "historical assignee was silently rewritten/dropped after the member went inactive"
            )
            candidate_values_after = _extract_assignee_candidate_values(html)
            assert _SECOND_MEMBER_ACCOUNT_ID not in candidate_values_after, (
                "a now-inactive member is still offered as a new assignment candidate"
            )
            version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            status, _, body = session.post_form(
                lead_detail_url,
                {
                    "action": "assign",
                    "assignee_account_id": _SECOND_MEMBER_ACCOUNT_ID,
                    "expected_version": str(version),
                },
                origin=web_base,
            )
            rec.steps.append(
                f"POST stale resubmission targeting the now-inactive member -> {status}"
            )
            html = body.decode("utf-8")
            assert "not a current active member" in html, (
                f"stale reassignment to a deactivated member was not rejected: {html[:400]!r}"
            )
            assert f"Assigned: {_SECOND_MEMBER_ACCOUNT_ID}" in html, (
                "rejected reassignment unexpectedly altered the stored historical assignee"
            )
            rec.steps.append(
                "confirmed: mutation fails closed on a stale/deactivated candidate, and the stored "
                "historical assignee is not silently rewritten"
            )

            # Restore a current-ACTIVE assignee before continuing the rest
            # of the task (status/follow-up/note/contact-attempt/re-find
            # below are independent of who the Lead is assigned to, but a
            # clean known state keeps this proof unambiguous).
            status, _, body = session.post_form(
                lead_detail_url,
                {
                    "action": "assign",
                    "assignee_account_id": account_id,
                    "expected_version": str(version),
                },
                origin=web_base,
            )
            html = body.decode("utf-8")
            assert "Done." in html and f"Assigned: {account_id}" in html, (
                f"final reassignment to the signed-in broker did not succeed: {html[:400]!r}"
            )
            version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            status, _, body = session.post_form(
                lead_detail_url,
                {"action": "set_status", "status": "IN_PROGRESS", "expected_version": str(version)},
                origin=web_base,
            )
            rec.steps.append(f"POST update status -> {status}")
            html = body.decode("utf-8")
            assert "Done." in html, f"status update did not succeed: {html[:400]!r}"
            assert "IN_PROGRESS" in html
            version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            status, _, body = session.post_form(
                lead_detail_url,
                {
                    "action": "set_follow_up",
                    # Deliberately overdue (past wall-clock time) so the
                    # inbox's own follow_up_due filter -- "due or overdue" --
                    # actually surfaces it, demonstrating a real re-find.
                    "due_at": (datetime.now(UTC) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M"),
                    "expected_version": str(version),
                },
                origin=web_base,
            )
            rec.steps.append(f"POST set follow-up -> {status}")
            html = body.decode("utf-8")
            assert "Done." in html, f"follow-up set did not succeed: {html[:400]!r}"
            assert (
                "Follow-up due:" in html and "None" not in html.split("Follow-up due:", 1)[1][:40]
            )
            version = int(re.search(r'name="expected_version" value="(\d+)"', html).group(1))

            status, _, body = session.post_form(
                lead_detail_url,
                {
                    "action": "add_note",
                    "text": "Called once, left voicemail; buyer wants more photos.",
                },
                origin=web_base,
            )
            rec.steps.append(f"POST add note -> {status}")
            html = body.decode("utf-8")
            assert "Done." in html and "left voicemail" in html, (
                "note did not appear in the timeline"
            )

            status, _, body = session.post_form(
                lead_detail_url,
                {"action": "add_contact_attempt", "channel": "PHONE", "note": "No answer"},
                origin=web_base,
            )
            rec.steps.append(f"POST record contact attempt -> {status}")
            html = body.decode("utf-8")
            assert "Done." in html and "PHONE" in html, (
                "contact attempt did not appear in the timeline"
            )

            status, _, body = session.get(org_url("/leads?follow_up_due=true"))
            rec.steps.append(f"GET inbox filtered to follow-up-due (re-find the Lead) -> {status}")
            html = body.decode("utf-8")
            assert lead_id in html, "re-finding the Lead via the follow-up-due filter failed"
            rec.steps.append(
                "Lead filters are limited to two boolean toggles (unread-only, follow-up-due) plus "
                "an undocumented 'status' query param; there is no free-text buyer-name/email/"
                "listing search box. Sufficient to re-find one Lead in this run; not demonstrated at "
                "realistic multi-Lead inbox volume."
            )

            rec.outcome = "PASS"
        except Exception as exc:
            rec.outcome = "BLOCKING_DEFICIENCY"
            rec.errors_recovery.append(str(exc))
        rec.duration_seconds = time.monotonic() - t0
        records.append(rec)
        print(f"TASK 5 ({rec.outcome}) in {rec.duration_seconds:.2f}s")
        if rec.errors_recovery:
            print("   ERROR:", rec.errors_recovery[-1])

        # ------------------------------------------------------------------
        # TASK 6 — commercial / sale outcome
        # ------------------------------------------------------------------
        rec = TaskRecord(
            task_id="TASK_6",
            title="Commercial / sale outcome",
            scenario="Same broker closes the listing as SOLD, explicitly linking the originating Lead but without yet knowing the achieved price.",
        )
        t0 = time.monotonic()
        try:
            edit_url = org_url(f"/inventory/{native_listing_id}/edit")
            status, _, body = session.get(edit_url)
            rec.steps.append(f"GET edit listing (locate sale/outcome section) -> {status}")
            html = body.decode("utf-8")
            sale_block = html.split("<h2>Sale / outcome</h2>", 1)[1]
            m = re.search(
                r'name="expected_current_sale_outcome_revision_id"\s+value="([^"]*)"', sale_block
            )
            expected_sale_revision = m.group(1) if m else ""

            status, _, body = session.post_form(
                edit_url,
                {
                    "action": "close_as_sold",
                    "revision_id": str(uuid.uuid4()),
                    "expected_current_sale_outcome_revision_id": expected_sale_revision,
                    "sold_date": "2026-10-10",
                    "achieved_amount": "",
                    "achieved_currency": "",
                    "originating_lead_id": lead_id,
                },
                origin=web_base,
            )
            rec.steps.append(
                f"POST close as SOLD (price unknown, Lead explicitly linked) -> {status}"
            )
            html = body.decode("utf-8")
            assert "Recorded." in html, f"close-as-sold did not succeed: {html[:400]!r}"
            assert "SOLD" in html
            assert f"Lead {lead_id}" in html, (
                "explicitly-selected originating Lead not linked on re-read"
            )
            sale_section = html.split("<h2>Sale / outcome</h2>", 1)[1]
            # Deterministic proof that leaving achieved price/currency absent
            # does not fabricate a price on the authoritative re-read: the
            # rendered "Current outcome: ..." line only ever includes an
            # em-dash-prefixed *numeric* fragment for the achieved-amount
            # clause (`edit.astro`'s "— {achieved_amount} {achieved_currency}"
            # conditional) -- the sold-date clause is "— sold <date>" and the
            # Lead-link clause is "— via Lead <id>", neither of which starts
            # with a digit. Independent review 2026-10-01 (reviewed HEAD
            # 28288ef, Finding C): the previous `... or True` assertion could
            # never fail and proved nothing.
            outcome_line_match = re.search(
                r"Current outcome:.*?\(recorded", sale_section, re.DOTALL
            )
            assert outcome_line_match, (
                f"could not locate the rendered current-outcome line: {sale_section[:400]!r}"
            )
            outcome_line = outcome_line_match.group(0)
            assert not re.search(r"—\s*\d", outcome_line), (
                "achieved price/currency appears to have been fabricated or defaulted "
                f"despite being left blank: {outcome_line!r}"
            )
            assert "sold 2026-10-10" in outcome_line, (
                f"the sold date actually supplied is not reflected on the re-read: {outcome_line!r}"
            )

            status, _, body = session.get(org_url("/inventory"))
            rec.steps.append(f"GET inventory overview (verify resulting lifecycle) -> {status}")
            html = body.decode("utf-8")
            assert "WITHDRAWN" in html, (
                "lifecycle did not reflect SOLD-driven withdrawal on authoritative re-read"
            )

            rec.outcome = "PASS"
        except Exception as exc:
            rec.outcome = "BLOCKING_DEFICIENCY"
            rec.errors_recovery.append(str(exc))
        rec.duration_seconds = time.monotonic() - t0
        records.append(rec)
        print(f"TASK 6 ({rec.outcome}) in {rec.duration_seconds:.2f}s")
        if rec.errors_recovery:
            print("   ERROR:", rec.errors_recovery[-1])

        # ------------------------------------------------------------------
        # UNTIMED OBSERVATION 7 — performance / funnel snapshot
        # ------------------------------------------------------------------
        obs = TaskRecord(
            task_id="OBSERVATION_7",
            title="Factual performance / funnel snapshot (untimed)",
            scenario="Same broker locates the Organization's performance snapshot and checks whether today's activity is understandable there.",
        )
        try:
            status, _, body = session.get(org_url("/performance?window=ALL_TIME"))
            obs.steps.append(f"GET performance snapshot -> {status}")
            html = body.decode("utf-8")
            assert "Performance &amp; funnel snapshot" in html or "Performance" in html
            assert "Leads received: 1" in html, f"leads_received not reflected: {html[:800]!r}"
            assert "Explicit SOLD outcomes recorded in window: 1" in html, (
                "SOLD outcome not reflected"
            )
            obs.outcome = "PASS"
        except Exception as exc:
            obs.outcome = "BLOCKING_DEFICIENCY"
            obs.errors_recovery.append(str(exc))
        records.append(obs)
        print(f"OBSERVATION 7 ({obs.outcome})\n")
        if obs.errors_recovery:
            print("   ERROR:", obs.errors_recovery[-1])

        # SLICE-0077 contract §7: explicitly state whether the accepted
        # SLICE-0076 TASK_5 blocking deficiency (undiscoverable opaque
        # AccountId assignment) is CLOSED or remains OPEN -- no more
        # excluding TASK_5 from the overall result.
        task_5_record = next(r for r in records if r.task_id == "TASK_5")
        slice_0076_blocker_status = "CLOSED" if task_5_record.outcome == "PASS" else "OPEN"
        overall_ok = all(r.outcome == "PASS" for r in records)
        print("=== EVIDENCE JSON BEGIN ===")
        print(
            json.dumps(
                {
                    "schema_name": schema_name,
                    "organization_id": _ORG_ID,
                    "native_listing_id": native_listing_id,
                    "lead_id": lead_id,
                    "setup_seconds": round(setup_seconds, 3),
                    "slice_0076_task_5_blocker_status": slice_0076_blocker_status,
                    "tasks": [r.to_dict() for r in records],
                },
                indent=2,
            )
        )
        print("=== EVIDENCE JSON END ===")

        print(f"\nSLICE-0076 TASK_5 blocking deficiency -> {slice_0076_blocker_status}")
        print(f"HARNESS RESULT -> {'PASS' if overall_ok else 'SEE TASK FINDINGS'}")
        return 0
    finally:
        for proc in (issuer_proc, api_proc, web_proc):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
