"""SLICE-0093 owner-visible end-to-end proof — real PostgreSQL 18 + real
FastAPI + real built Astro SSR, review amendment Finding C.

Independent review on PR #390, Finding C: the READY deliverable explicitly
requires a retained inspector exercising real PostgreSQL18 + FastAPI +
**built Astro SSR**, five buyer locales, the genuine broker editor form
save/readback/unrelated edit preserving drive, invalid/stale/unauthorized
saves, and source-labeled buyer result. This script drives the real built
`/{locale}/power/search` buyer pages and the real built broker
`.../inventory/[native_listing_id]/edit` page through authenticated,
same-origin HTTP requests (`urllib` plus a standards-compliant cookie jar
for the real OIDC/session login, mirroring
`scripts/inspect_slice_0091_vessel_category_editor.py`'s identical
discipline) against a real local OIDC test issuer, a real FastAPI backend
and a real built Astro/Node SSR server, over a real disposable PostgreSQL 18
schema -- this is HTTP-level request/form-POST evidence, not a genuine
automated browser (no JS execution, no DOM rendering, no Playwright/
Selenium-style page automation).

Phase A (buyer, five locales): proves the separate `/api/search/{locale}
/power` route and the five `/{locale}/power/search` built SSR pages render
real evidence for three seeded candidates:

    1. NL-0093-INSP-CLAIM: a design-UNRESOLVED PhysicalBoat with an explicit
       current publisher POWER category + POD drive claim -- matches
       `power_drive=POD`, `source_basis=PUBLISHER_CLAIM`.
    2. NL-0093-INSP-SAIL: a design-UNRESOLVED explicit SAIL PhysicalBoat --
       never a Power positive for any token.
    3. NL-0093-INSP-LINKED: a design-LINKED PhysicalBoat (BoatDesign v0.6
       `propulsion.drive_type=shaft`, real admitted FieldResolution) with a
       matching concrete SHAFT claim -- matches `power_drive=SHAFT` on the
       design-linked surface, distinct from the claim-only surface above.

Phase B (broker editor, authenticated): proves the real
`physical_boat.power_drive_configuration` field round-trips through the
actual broker editor page:

    4. the real editor's PhysicalBoat claim form offers the drive field and
       starts unset
    5. an authenticated HTTP form POST sets it to POD; the authoritative
       current claim head reflects it
    6. a second, *unrelated* authenticated HTTP form POST (changing only
       `boat_name`, repeating every other current field exactly as the real
       form renders it) leaves the drive field untouched
    7. a stale `expected_current_revision_id` is rejected, zero mutation
    8. an invalid drive value is rejected, zero mutation
    9. an unauthorized Account (no membership in the owning Organization) is
       rejected, zero mutation

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``npm ci --prefix web && npm run build --prefix web``).

Run: uv run python scripts/inspect_slice_0093_power_drive_search.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
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
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_ORG_A_ID = "ORG-0093-EDITOR-A"
_LOCALES = ("en", "de", "fr", "pt", "es")

#: Review amendment Finding I (HIGH): the exact
#: `t.publisherClaimDisclaimer` string per locale
#: (`web/src/lib/powerSearchText.ts`) -- verified by real substring
#: presence in each built Astro SSR locale's rendered HTML, never only in
#: `en`.
#: Astro's built SSR text-node escaping renders `'` as the `&#39;` HTML
#: entity (confirmed against the real built output) -- the `en` string is
#: the only one of the five with an apostrophe, so it is the only one
#: spelled with the escaped entity here; matching the raw `'` character
#: against escaped HTML output would always miss.
_PUBLISHER_CLAIM_DISCLAIMER_BY_LOCALE = {
    "en": (
        "These listings are shown on the publishing broker&#39;s own current statement, "
        "not independently verified."
    ),
    "de": (
        "Diese Angebote beruhen auf der aktuellen Angabe des anbietenden Maklers, "
        "nicht auf unabhängiger Prüfung."
    ),
    "fr": (
        "Ces annonces reposent sur la déclaration actuelle du courtier vendeur, "
        "non vérifiée indépendamment."
    ),
    "pt": (
        "Estes anúncios baseiam-se na declaração atual do corretor "
        "anunciante, não verificada de forma independente."
    ),
    "es": (
        "Estos anuncios se basan en la declaración actual del corredor anunciante, "
        "no verificada de forma independiente."
    ),
}


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


def _http_get(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
    """A real, standards-compliant cookie-jar HTTP client with form-POST
    support -- HTTP-level request/form-POST evidence only, never a genuine
    automated browser (no JS execution, no DOM rendering, no Playwright/
    Selenium-style page automation)."""

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

    def post_form(
        self, url: str, fields: dict[str, str], *, origin: str
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": origin}
        return self.request(
            "POST", url, extra_headers=headers, data=urlencode(fields).encode("utf-8")
        )

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


def _edit_page_path(org_id: str, listing_id: str) -> str:
    return f"/broker/organizations/{org_id}/inventory/{listing_id}/edit"


def _form_block(page_text: str, heading: str) -> str:
    idx = page_text.index(heading)
    start = page_text.index("<form", idx)
    end = page_text.index("</form>", start) + len("</form>")
    return page_text[start:end]


def _hidden_field_value(form_html: str, field_name: str) -> str:
    pattern = re.compile(r'name="' + re.escape(field_name) + r'"[\s\S]*?value="([^"]*)"')
    match = pattern.search(form_html)
    assert match is not None, f"hidden field {field_name!r} not found in form block"
    return match.group(1)


def _select_block(form_html: str, select_name: str) -> str:
    """Review amendment Finding I (HIGH): the exact `<select name=...>
    ... </select>` element, scoped to *select_name* -- never the whole
    form block. The form has several `<select>` elements whose *other*
    options also render the bare word "selected" (e.g. assertion-kind
    dropdowns) -- checking for the substring "selected" anywhere in the
    whole form block proves nothing about this specific field."""
    pattern = re.compile(r'<select\b[^>]*\bname="' + re.escape(select_name) + r'"[\s\S]*?</select>')
    match = pattern.search(form_html)
    assert match is not None, f"<select name={select_name!r}> not found in form block"
    return match.group(0)


def _option_is_selected(select_html: str, value: str) -> bool:
    """Whether `<option value={value} ...>` inside *select_html* carries the
    `selected` boolean attribute -- Astro omits the attribute entirely for
    a falsy boolean, so its bare presence on the one matching `<option>`
    tag (not merely anywhere in the surrounding `<select>`) is the correct,
    specific proof this exact value is the one currently selected."""
    pattern = re.compile(r'<option\b[^>]*\bvalue="' + re.escape(value) + r'"([^>]*)>')
    match = pattern.search(select_html)
    assert match is not None, f'<option value="{value}"> not found in select block'
    return "selected" in match.group(1)


def _seed(conn: Any) -> None:
    from hullq.domain.market_identity import (
        BoatDesignRef,
        MarketEpisode,
        MarketEpisodeId,
        NativeListing,
        NativeListingId,
        PhysicalBoat,
        PhysicalBoatId,
    )
    from hullq.domain.media_gallery import MediaSourceKind
    from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
    from hullq.domain.physical_boat_claims import (
        AssertionKind,
        BuildYearClaim,
        PhysicalBoatClaimRevisionId,
        PhysicalBoatClaimSnapshot,
        PowerDriveConfiguration,
        PowerDriveConfigurationClaim,
        VesselCategory,
        VesselCategoryClaim,
    )
    from hullq.domain.provenance import SubjectKind
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
    from hullq.persistence.broker_identity import seed_marketplace_organization
    from hullq.persistence.market_episode import create_market_episode
    from hullq.persistence.media_gallery import (
        create_uploaded_image_placement,
        insert_approved_media_asset,
        set_cover,
    )
    from hullq.persistence.native_listing import create_native_listing
    from hullq.persistence.native_listing_lifecycle import publish_native_listing
    from hullq.persistence.native_listing_offer import (
        NativeListingOfferRevisionId,
        write_native_listing_offer_revision,
    )
    from hullq.persistence.physical_boat import create_physical_boat
    from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
    from hullq.search.power_drive_design_bridge import lookup_power_drive_canonical_value

    sys.path.insert(0, str(REPO_ROOT / "tests" / "persistence"))
    from _field_resolution_support import (
        admit_resolved_categorical_field,  # type: ignore[import-not-found]
    )

    VA = AssertionKind.VALUE_ASSERTION

    def _org(value: str) -> MarketplaceOrganization:
        return MarketplaceOrganization(
            id=MarketplaceOrganizationId(value),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )

    def _membership(
        org: MarketplaceOrganization, account: Any, membership_id: str
    ) -> OrganizationMembership:
        return OrganizationMembership(
            id=OrganizationMembershipId(membership_id),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )

    def _attach_cover(listing_id: str, org: MarketplaceOrganization, account: Any) -> None:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [account.value],
                )
            seed_marketplace_organization(conn, org)
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key=f"original/{listing_id}",
                derivative_object_key=f"derivative/{listing_id}",
                content_hash=f"hash-{listing_id}",
                mime_type="image/jpeg",
                width=800,
                height=600,
                byte_size=12345,
            )
            placement = create_uploaded_image_placement(
                conn,
                native_listing_id=NativeListingId(listing_id),
                owner_organization_id=org.id,
                media_asset=asset,
            )
            set_cover(
                conn,
                native_listing_id=NativeListingId(listing_id),
                owner_organization_id=org.id,
                media_placement_id=placement.media_placement_id,
                expected_version=placement.gallery_version,
            )

    def _publish(
        listing_id: str,
        physical_boat_id: str,
        market_episode_id: str,
        org_id: str,
        boat_design_id: str | None,
        vessel_category: VesselCategoryClaim | None,
        power_drive_configuration: PowerDriveConfigurationClaim | None,
    ) -> None:
        account = AccountId(f"ACC-{listing_id}")
        org = _org(org_id)
        membership = _membership(org, account, f"OM-{listing_id}")
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(physical_boat_id),
                boat_design_ref=BoatDesignRef(boat_design_id) if boat_design_id else None,
            ),
        )
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(market_episode_id),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
            ),
        )
        write_native_listing_offer_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
            expected_current_revision_id=None,
            offer=NativeListingOfferSnapshot(
                asking_price_mode=AskingPriceMode.AMOUNT,
                location_country="FR",
                broker_description="A well-maintained motor yacht.",
                asking_price_amount=Decimal("250000.00"),
                currency="EUR",
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Swift Trawler 35",
                build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                vessel_category=vessel_category,
                power_drive_configuration=power_drive_configuration,
            ),
        )
        _attach_cover(listing_id, org, account)
        publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )

    # 1. design-unresolved, publisher-owned POWER + POD claim.
    _publish(
        "NL-0093-INSP-CLAIM",
        "PB-0093-INSP-CLAIM",
        "ME-0093-INSP-CLAIM",
        "ORG-0093-INSP-CLAIM",
        None,
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        PowerDriveConfigurationClaim(assertion_kind=VA, value=PowerDriveConfiguration.POD),
    )

    # 2. design-unresolved, explicit SAIL -- never a Power positive.
    _publish(
        "NL-0093-INSP-SAIL",
        "PB-0093-INSP-SAIL",
        "ME-0093-INSP-SAIL",
        "ORG-0093-INSP-SAIL",
        None,
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        None,
    )

    # 3. design-linked, v0.6 shaft FieldResolution + matching concrete claim.
    design_id = "BD-0093-INSP-LINKED"
    model_id = "BM-0093-INSP-LINKED"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"propulsion": {"drive_type": "shaft"}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    conn.commit()
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/drive_type",
        value="shaft",
        resolution_id=f"FR-PWRDRV-{design_id}",
        fetch_canonical_value=lookup_power_drive_canonical_value,
    )
    _publish(
        "NL-0093-INSP-LINKED",
        "PB-0093-INSP-LINKED",
        "ME-0093-INSP-LINKED",
        "ORG-0093-INSP-LINKED",
        design_id,
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        PowerDriveConfigurationClaim(assertion_kind=VA, value=PowerDriveConfiguration.SHAFT),
    )
    conn.commit()


def _start_api(
    *,
    url: str,
    api_port: int,
    preview_secret_b64: str,
    session_secret_b64: str,
    issuer_base: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    web_base: str,
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0093_insp_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
    env["HULLQ_SESSION_SIGNING_SECRET"] = session_secret_b64
    env["HULLQ_AUTH_ISSUER"] = issuer_base
    env["HULLQ_AUTH_AUTHORIZE_URL"] = f"{issuer_base}authorize"
    env["HULLQ_AUTH_TOKEN_URL"] = f"{issuer_base}token"
    env["HULLQ_AUTH_JWKS_URL"] = f"{issuer_base}.well-known/jwks.json"
    env["HULLQ_AUTH_CLIENT_ID"] = client_id
    env["HULLQ_AUTH_CLIENT_SECRET"] = client_secret
    env["HULLQ_AUTH_REDIRECT_URI"] = redirect_uri
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


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  npm ci --prefix web && npm run build --prefix web",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0093insp_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)
    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0093_insp_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.domain.market_identity import PhysicalBoatId
        from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )
        from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0093 POWER DRIVE CONFIGURATION SEARCH + EDITOR PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic migrated to current head -> OK\n")

        conn = psycopg.connect(url)
        try:
            _seed(conn)
            print(
                "1. seeded NL-0093-INSP-CLAIM (design-unresolved POWER+POD publisher claim), "
                "NL-0093-INSP-SAIL (design-unresolved SAIL), "
                "NL-0093-INSP-LINKED (design-linked v0.6 shaft + matching concrete SHAFT) -> OK\n"
            )
        finally:
            conn.close()

        # Also prove the application-level funnel directly against real
        # PostgreSQL before ever touching HTTP.
        conn2 = psycopg.connect(url)
        try:
            from hullq.application.power_inventory_query import evaluate_power_drive_requirement

            pod_outcome = evaluate_power_drive_requirement(
                conn2, power_drive="POD", as_of=datetime.now(UTC)
            )
            claim_ids = {m.native_listing_id.value for m in pod_outcome.claim_only_matches}
            shaft_outcome = evaluate_power_drive_requirement(
                conn2, power_drive="SHAFT", as_of=datetime.now(UTC)
            )
            design_ids = {m.native_listing_id.value for m in shaft_outcome.design_linked_matches}
            step2_ok = claim_ids == {"NL-0093-INSP-CLAIM"} and design_ids == {"NL-0093-INSP-LINKED"}
            ok &= step2_ok
            print(
                "2. application funnel (evaluate_power_drive_requirement): "
                f"power_drive=POD claim_only_matches={sorted(claim_ids)}, "
                f"power_drive=SHAFT design_linked_matches={sorted(design_ids)} -> "
                f"{'OK' if step2_ok else 'FAIL'}\n"
            )
        finally:
            conn2.close()

        issuer_host = "127.0.0.1"
        issuer_port = _free_port(issuer_host)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{issuer_host}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-power-drive-editor-e2e-client"
        client_secret = secrets.token_urlsafe(24)
        preview_secret_b64 = _b64url(os.urandom(32))
        session_secret_b64 = _b64url(os.urandom(32))

        issuer_code = (
            "import uvicorn\n"
            "from hullq.testing.oidc_test_issuer import create_test_issuer_app\n"
            f"app = create_test_issuer_app(issuer={issuer_base!r}, client_id={client_id!r}, "
            f"client_secret={client_secret!r}, redirect_uri={redirect_uri!r})\n"
            f"uvicorn.run(app, host={issuer_host!r}, port={issuer_port}, log_level='warning')\n"
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
            f"3. deterministic local OIDC/JWKS test issuer serving -> {'OK' if issuer_ready else 'FAIL'}"
        )

        api_proc, api_log_path = _start_api(
            url=url,
            api_port=api_port,
            preview_secret_b64=preview_secret_b64,
            session_secret_b64=session_secret_b64,
            issuer_base=issuer_base,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            web_base=web_base,
        )
        api_ready = _wait_for_http(f"{api_base}/api/search/en/power")
        ok &= api_ready
        print(f"4. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print("---- api.log ----", file=sys.stderr)
            print(api_log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)

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
        web_ready = _wait_for_http(f"{web_base}/en/power/search")
        ok &= web_ready
        print(f"5. Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("SLICE-0093 PROOF RESULT -> FAIL")
            return 1

        # --- Phase A: buyer, five locales ---------------------------------

        for locale in _LOCALES:
            page_status, _, page_body = _http_get(
                f"{web_base}/{locale}/power/search?power_drive=POD"
            )
            page_text = page_body.decode("utf-8")
            noindex_ok = 'name="robots" content="noindex"' in page_text
            disclaimer_ok = _PUBLISHER_CLAIM_DISCLAIMER_BY_LOCALE[locale] in page_text
            locale_ok = (
                page_status == 200
                and "NL-0093-INSP-CLAIM" in page_text
                and "NL-0093-INSP-SAIL" not in page_text
                and "NL-0093-INSP-LINKED" not in page_text
                and noindex_ok
                and disclaimer_ok
            )
            ok &= locale_ok
            print(
                f"6.[{locale}] GET /{locale}/power/search?power_drive=POD (built Astro SSR): "
                f"claim-only match renders, SAIL/other-token listings absent, noindex="
                f"{'OK' if noindex_ok else 'FAIL'}, publisher-claim disclaimer="
                f"{'OK' if disclaimer_ok else 'FAIL'} -> {'OK' if locale_ok else 'FAIL'}"
            )
        print()

        api_status, _, api_body = _http_get(f"{api_base}/api/search/en/power?power_drive=POD")
        api_json = _json(api_body)
        claim_matches = api_json.get("publisher_claim_matches", [])
        claim_ids = {m["native_listing_id"] for m in claim_matches}
        claim_entry = next(
            (m for m in claim_matches if m["native_listing_id"] == "NL-0093-INSP-CLAIM"), None
        )
        step7_ok = (
            api_status == 200
            and claim_ids == {"NL-0093-INSP-CLAIM"}
            and claim_entry is not None
            and claim_entry.get("source_basis") == "PUBLISHER_CLAIM"
            and api_json.get("design_linked_match_count") == 0
        )
        ok &= step7_ok
        print(
            "7. GET /api/search/en/power?power_drive=POD: publisher_claim_matches="
            f"{sorted(claim_ids)}, source_basis={claim_entry.get('source_basis') if claim_entry else None}, "
            f"design_linked_match_count=0 -> {'OK' if step7_ok else 'FAIL'}"
        )

        api_status8, _, api_body8 = _http_get(f"{api_base}/api/search/en/power?power_drive=SHAFT")
        api_json8 = _json(api_body8)
        design_ids8 = {m["native_listing_id"] for m in api_json8.get("design_linked_matches", [])}
        step8_ok = api_status8 == 200 and design_ids8 == {"NL-0093-INSP-LINKED"}
        ok &= step8_ok
        print(
            "8. GET /api/search/en/power?power_drive=SHAFT: design_linked_matches="
            f"{sorted(design_ids8)} -> {'OK' if step8_ok else 'FAIL'}\n"
        )

        # --- Phase B: broker editor, authenticated -------------------------

        inventory_path_a = f"/broker/organizations/{_ORG_A_ID}/inventory"
        session_a = BrowserSession()
        login_url_a = (
            f"{api_base}/api/auth/login?next={quote(inventory_path_a, safe='')}"
            f"&login_hint=power-drive-0093-subject-a"
            f"&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        status, headers, _ = session_a.follow_full_login(login_url_a)
        login_ok = status == 302 and headers.get("Location") == f"{web_base}{inventory_path_a}"
        ok &= login_ok
        print(f"9. Account A real OIDC login (MFA-satisfied) -> {'OK' if login_ok else 'FAIL'}")

        status, _, body = session_a.get(f"{api_base}/api/broker/context")
        account_a_id = _json(body)["account_id"]

        from hullq.domain.market_identity import (
            MarketEpisode,
            MarketEpisodeId,
            NativeListing,
            NativeListingId,
            PhysicalBoat,
        )
        from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
        from hullq.domain.physical_boat_claims import (
            AssertionKind,
            BuildYearClaim,
            PhysicalBoatClaimRevisionId,
            PhysicalBoatClaimSnapshot,
        )
        from hullq.domain.publishing_eligibility import (
            AccountId,
            MarketplaceOrganization,
            MembershipRole,
            MembershipState,
            OrganizationMembership,
            OrganizationMembershipId,
            OrganizationPublishingEligibility,
            ProfessionalCategory,
        )
        from hullq.persistence.broker_identity import (
            seed_marketplace_organization,
            seed_organization_membership,
        )
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.native_listing_offer import (
            NativeListingOfferRevisionId,
            write_native_listing_offer_revision,
        )
        from hullq.persistence.physical_boat import create_physical_boat
        from hullq.persistence.physical_boat_claims import (
            fetch_current_physical_boat_claim,
            list_physical_boat_claim_revisions,
            write_physical_boat_claim_revision,
        )

        conn = psycopg.connect(url)
        try:
            org_a = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_A_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org_a)
            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-0093-EDITOR-A"),
                account_id=AccountId(account_a_id),
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            seed_organization_membership(conn, membership_a)
            conn.commit()

            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0093-EDITOR"))
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0093-EDITOR"),
                    physical_boat_id=PhysicalBoatId("PB-0093-EDITOR"),
                ),
            )
            create_native_listing(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(
                    id=NativeListingId("NL-0093-EDITOR"),
                    market_episode_id=MarketEpisodeId("ME-0093-EDITOR"),
                ),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0093-EDITOR"),
                revision_id=NativeListingOfferRevisionId("REV-0093-EDITOR"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained motor yacht.",
                    asking_price_amount=Decimal("225000.00"),
                    currency="EUR",
                ),
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0093-EDITOR"),
                revision_id=PhysicalBoatClaimRevisionId("CLAIM-0093-EDITOR-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Jeanneau",
                    model_designation_claim="Merry Fisher 895",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                ),
            )
            conn.commit()
            db_claim_before = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
        finally:
            conn.close()
        assert db_claim_before is not None
        no_drive_yet_ok = db_claim_before.claims.power_drive_configuration is None
        ok &= no_drive_yet_ok
        print(
            "10. seeded ORG_A/NL-0093-EDITOR with a claim that has no power_drive_configuration "
            f"yet -> {'OK' if no_drive_yet_ok else 'FAIL'}\n"
        )

        status, _, body = session_a.get(f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0093-EDITOR')}")
        page_text = body.decode("utf-8")
        claim_form = _form_block(page_text, '<h2 id="claim-editor">PhysicalBoat claim</h2>')
        has_field_ok = (
            status == 200
            and 'name="power_drive_configuration_kind"' in claim_form
            and 'name="power_drive_configuration_value"' in claim_form
        )
        ok &= has_field_ok
        print(
            "11. the real editor's PhysicalBoat claim form offers a power_drive_configuration "
            f"field -> {'OK' if has_field_ok else 'FAIL'}"
        )
        revision_id_1 = _hidden_field_value(claim_form, "revision_id")
        expected_1 = _hidden_field_value(claim_form, "expected_current_revision_id")
        assert expected_1 == db_claim_before.revision_id.value

        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0093-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": revision_id_1,
                "expected_current_revision_id": expected_1,
                "marketed_brand_claim": "Jeanneau",
                "model_designation_claim": "Merry Fisher 895",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2021",
                "power_drive_configuration_kind": "VALUE_ASSERTION",
                "power_drive_configuration_value": "POD",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        set_saved_ok = status == 200 and "Saved." in page_text

        conn = psycopg.connect(url)
        try:
            claim_after_set = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
        finally:
            conn.close()
        assert claim_after_set is not None
        set_ok = (
            claim_after_set.claims.power_drive_configuration is not None
            and claim_after_set.claims.power_drive_configuration.value.value == "POD"
        )
        ok &= set_saved_ok and set_ok
        print(
            "12. an authenticated HTTP form POST sets power_drive_configuration to POD; the "
            f"authoritative current claim head reflects it -> {'OK' if (set_saved_ok and set_ok) else 'FAIL'}\n"
        )

        status, _, body = session_a.get(f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0093-EDITOR')}")
        page_text = body.decode("utf-8")
        claim_form = _form_block(page_text, '<h2 id="claim-editor">PhysicalBoat claim</h2>')
        drive_select = _select_block(claim_form, "power_drive_configuration_value")
        prefilled_ok = _option_is_selected(drive_select, "POD") and not any(
            _option_is_selected(drive_select, other)
            for other in ("SHAFT", "STERNDRIVE", "WATERJET", "OUTBOARD", "MIXED", "OTHER")
        )
        revision_id_2 = _hidden_field_value(claim_form, "revision_id")
        expected_2 = _hidden_field_value(claim_form, "expected_current_revision_id")
        assert expected_2 == claim_after_set.revision_id.value

        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0093-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": revision_id_2,
                "expected_current_revision_id": expected_2,
                "marketed_brand_claim": "Jeanneau",
                "model_designation_claim": "Merry Fisher 895",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2021",
                "power_drive_configuration_kind": "VALUE_ASSERTION",
                "power_drive_configuration_value": "POD",
                "boat_name_kind": "VALUE_ASSERTION",
                "boat_name_value": "Sea Fox",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        unrelated_saved_ok = status == 200 and "Saved." in page_text and "Sea Fox" in page_text

        conn = psycopg.connect(url)
        try:
            claim_after_unrelated = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
        finally:
            conn.close()
        assert claim_after_unrelated is not None
        preserved_ok = (
            claim_after_unrelated.claims.power_drive_configuration is not None
            and claim_after_unrelated.claims.power_drive_configuration.value.value == "POD"
            and claim_after_unrelated.claims.boat_name is not None
            and claim_after_unrelated.claims.boat_name.value == "Sea Fox"
        )
        ok &= unrelated_saved_ok and preserved_ok and prefilled_ok
        print(
            "13. the real editor pre-fills the power_drive_configuration_value select's POD "
            f"option specifically as selected (never another option) -> "
            f"{'OK' if prefilled_ok else 'FAIL'}"
        )
        print(
            "14. an unrelated authenticated HTTP form POST (boat_name only) leaves "
            f"power_drive_configuration untouched (still POD) -> "
            f"{'OK' if (unrelated_saved_ok and preserved_ok) else 'FAIL'}\n"
        )

        # Stale revision.
        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0093-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": expected_1,
                "marketed_brand_claim": "Jeanneau",
                "model_designation_claim": "Merry Fisher 895",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2021",
                "power_drive_configuration_kind": "VALUE_ASSERTION",
                "power_drive_configuration_value": "SHAFT",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        stale_rendered_ok = status == 200 and "changed since you loaded the page" in page_text

        conn = psycopg.connect(url)
        try:
            claim_after_stale = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            revision_count_stale = len(
                list_physical_boat_claim_revisions(
                    conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
                )
            )
        finally:
            conn.close()
        assert claim_after_stale is not None
        stale_no_mutation_ok = (
            claim_after_stale.revision_id.value == claim_after_unrelated.revision_id.value
            and revision_count_stale == 3
            and claim_after_stale.claims.power_drive_configuration is not None
            and claim_after_stale.claims.power_drive_configuration.value.value == "POD"
        )
        ok &= stale_rendered_ok and stale_no_mutation_ok
        print(
            "15. a stale expected_current_revision_id is rejected (re-rendered, zero mutation; "
            f"still POD, 3 revisions on record) -> "
            f"{'OK' if (stale_rendered_ok and stale_no_mutation_ok) else 'FAIL'}"
        )

        # Invalid drive value.
        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0093-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": claim_after_unrelated.revision_id.value,
                "marketed_brand_claim": "Jeanneau",
                "model_designation_claim": "Merry Fisher 895",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2021",
                "power_drive_configuration_kind": "VALUE_ASSERTION",
                "power_drive_configuration_value": "DIESEL_ELECTRIC",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        invalid_rendered_ok = status == 200 and "couldn&#39;t be saved" in page_text

        conn = psycopg.connect(url)
        try:
            claim_after_invalid = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            revision_count_invalid = len(
                list_physical_boat_claim_revisions(
                    conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
                )
            )
        finally:
            conn.close()
        assert claim_after_invalid is not None
        invalid_no_mutation_ok = (
            claim_after_invalid.revision_id.value == claim_after_unrelated.revision_id.value
            and revision_count_invalid == 3
            and claim_after_invalid.claims.power_drive_configuration is not None
            and claim_after_invalid.claims.power_drive_configuration.value.value == "POD"
        )
        ok &= invalid_rendered_ok and invalid_no_mutation_ok
        print(
            '16. an invalid drive value ("DIESEL_ELECTRIC") is rejected (re-rendered, zero '
            f"mutation; still POD, 3 revisions on record) -> "
            f"{'OK' if (invalid_rendered_ok and invalid_no_mutation_ok) else 'FAIL'}"
        )

        # Unauthorized Account: a different, freshly-logged-in Account with
        # no membership in ORG_A attempts the same save.
        session_b = BrowserSession()
        login_url_b = (
            f"{api_base}/api/auth/login?next={quote(inventory_path_a, safe='')}"
            f"&login_hint=power-drive-0093-subject-b"
            f"&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        session_b.follow_full_login(login_url_b)
        status, _, body = session_b.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0093-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": claim_after_unrelated.revision_id.value,
                "marketed_brand_claim": "Jeanneau",
                "model_designation_claim": "Merry Fisher 895",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2021",
                "power_drive_configuration_kind": "VALUE_ASSERTION",
                "power_drive_configuration_value": "OUTBOARD",
            },
            origin=web_base,
        )
        unauthorized_page_text = body.decode("utf-8")
        unauthorized_not_saved_ok = not (status == 200 and "Saved." in unauthorized_page_text)

        conn = psycopg.connect(url)
        try:
            claim_after_unauthorized = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            revision_count_unauthorized = len(
                list_physical_boat_claim_revisions(
                    conn, PhysicalBoatId("PB-0093-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
                )
            )
        finally:
            conn.close()
        assert claim_after_unauthorized is not None
        unauthorized_no_mutation_ok = (
            claim_after_unauthorized.revision_id.value == claim_after_unrelated.revision_id.value
            and revision_count_unauthorized == 3
            and claim_after_unauthorized.claims.power_drive_configuration is not None
            and claim_after_unauthorized.claims.power_drive_configuration.value.value == "POD"
        )
        ok &= unauthorized_not_saved_ok and unauthorized_no_mutation_ok
        print(
            "17. an unauthorized Account (no membership in ORG_A) attempting the same save "
            f"never saves and never mutates the durable claim (still POD, 3 revisions on "
            f"record) -> {'OK' if (unauthorized_not_saved_ok and unauthorized_no_mutation_ok) else 'FAIL'}\n"
        )

        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secrets_clean = all(
            client_secret not in text and session_secret_b64 not in text
            for text in (api_log_text, web_log_text)
        )
        ok &= secrets_clean
        print(
            f"    ordinary API/web logs contain no client/session secret -> {'OK' if secrets_clean else 'FAIL'}\n"
        )

        print(
            f"SLICE-0093 POWER DRIVE CONFIGURATION SEARCH + EDITOR PROOF RESULT -> {'PASS' if ok else 'FAIL'}"
        )
        return 0 if ok else 1
    finally:
        for proc in (issuer_proc, api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
