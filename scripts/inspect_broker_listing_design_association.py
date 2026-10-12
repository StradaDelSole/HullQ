"""SLICE-0082 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the broker-confirmed NativeListing PhysicalBoat -> canonical
BoatDesign first-association vertical against a real, disposable PostgreSQL
18 schema and two real local HTTP servers: FastAPI and the built Astro/Node
SSR web package. Authentication uses a directly minted, cryptographically
signed session cookie rather than a full OIDC round-trip -- mirrors
`tests/persistence/test_broker_inventory_editing_api.py`'s identical,
already-accepted shortcut ("that path is covered by
test_broker_workspace_access_api.py"); FastAPI still performs its own real
signature verification of that exact cookie on every request below.

Demonstrates, end to end:

    1. an authorized broker creates + fills + promotes a professional draft
       through the real accepted FastAPI promotion transaction (no direct
       SQL insertion, no manual PhysicalBoat linking) -- the resulting
       NativeListing's PhysicalBoat starts design-UNRESOLVED
    2. the real built Astro broker inventory editor page's bounded design
       selector surfaces the one seeded canonical BoatDesign for a search
       term, and a real same-origin browser form POST explicitly confirms
       it -- durable LINKED state, one audit event
    3. the identical confirmation replayed is idempotent (ALREADY_LINKED,
       zero additional audit rows); a different target -- known or unknown
       to canonical_boat_designs -- conflicts (409, the existing link is
       read-only truth); a foreign Organization's attempt is non-
       enumerating (404); a missing-MFA session is denied (403,
       MFA_REQUIRED) -- zero mutation in every case
    4. the broker completes the concrete-yacht claim (adding
       keel_configuration), attaches the required cover image and publishes
       the listing through the existing accepted lifecycle gate
    5. a second, independently promoted/published listing is deliberately
       left design-UNRESOLVED -- it remains fully reachable through the
       existing public listing route (an unlinked listing is never
       penalized)
    6. ordinary public technical Search (`keel_configuration=FIN`) finds
       the linked listing as a CONFIRMED_MATCH and never surfaces the
       deliberately unresolved listing; the accepted technical Search
       criterion count remains exactly 2 (an unrecognized third parameter
       still 400s)
    7. exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_listing_design_association.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import json
import os
import re
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
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_ORG_A_ID = "ORG-0082-A"
_ORG_B_ID = "ORG-0082-B"
_ACCOUNT_A_ID = "ACC-0082-A"
_ACCOUNT_B_ID = "ACC-0082-B"
_DRAFT_CSRF_HEADER_VALUE = "professional-listing-draft-v1"
_LIFECYCLE_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1"
_EDITING_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"
_DESIGN_ASSOCIATION_CSRF_HEADER_VALUE = "broker-design-association-v1"

_DESIGN_ID = "BD-0082-E2E"
_MODEL_ID = "BM-0082-E2E"


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
    """A real, standards-compliant cookie-jar HTTP client with form-POST
    support -- mirrors `scripts/inspect_professional_inventory_editing.py`'s
    identical `BrowserSession`."""

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

    def post_form(
        self, url: str, fields: dict[str, str], *, origin: str
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": origin}
        return self.request(
            "POST", url, extra_headers=headers, data=urlencode(fields).encode("utf-8")
        )


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _csrf_headers(web_base: str, header_value: str) -> dict[str, str]:
    return {"Origin": web_base, "X-HullQ-Requested-With": header_value}


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


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str, session_secret_b64: str, web_base: str
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0082_api_", suffix=".log")[1])
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


def _insert_boat_design_with_keel_baseline(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            [model_id, "Oceanis 30.1", "0" * 64],
        )
        baseline = json.dumps({"appendages": {"keel_type": "fin"}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline, "1" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_brands (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            ["Beneteau", "Beneteau", "2" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_brand_model_relationships "
            "(id, brand_id, boat_model_id, content_hash) VALUES (%s, %s, %s, %s)",
            [f"rel-{design_id}", "Beneteau", model_id, "3" * 64],
        )
    conn.commit()


def _admit_keel_field_resolution(conn: Any, design_id: str) -> None:
    """Durably admit one `resolved` `appendages.keel_type` FieldResolution
    on *design_id*'s baseline, through the real accepted
    `write_field_resolution` path -- mirrors
    `scripts/inspect_first_native_inventory_search.py`'s identical recipe,
    trimmed to the single criterion this proof's Search step needs."""
    from hullq.domain.provenance import (
        ClaimSemantics,
        ConfidenceLevel,
        EvidenceType,
        FieldEvidenceV3,
        FieldResolution,
        JsonPointer,
        NormalizedCandidate,
        ObservationApplicability,
        ProducerKind,
        ProducerMetadata,
        ProvenanceSubject,
        RawObservation,
        RawObservationKind,
        ResearchContext,
        ResolutionMethod,
        ResolutionState,
        ResolverKind,
        ResolverMetadata,
        SourceLocator,
        SubjectKind,
    )
    from hullq.persistence.field_resolution import (
        FieldResolutionWriteStatus,
        write_field_resolution,
    )
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.research.jobs import ResearchTarget
    from hullq.research.observations import ResearchEvidenceBundle
    from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value

    wikidata_source: dict[str, Any] = json.loads(
        (REPO_ROOT / "fixtures" / "sources" / "wikidata_source.json").read_text(encoding="utf-8")
    )
    wikidata_source_id = wikidata_source["source_id"]

    evidence_id = "EV-0082-E2E-KEEL"
    evidence = FieldEvidenceV3(
        evidence_id=evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=design_id),
        field_pointer=JsonPointer(KEEL_TYPE_FIELD_POINTER),
        source_id=wikidata_source_id,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD, value="fin", unit=None, excerpt=None
        ),
        normalized_candidate=NormalizedCandidate(
            value="fin", unit=None, method_id="proof-normalize", method_version="1"
        ),
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="inspect_broker_listing_design_association",
            version="1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-10-12T00:00:00+00:00",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=True,
        ),
    )
    bundle = ResearchEvidenceBundle(
        bundle_id="BUNDLE-0082-E2E",
        bundle_version="1",
        research_target=ResearchTarget(
            manufacturer=None, model="design-association-e2e", first_built=None
        ),
        research_job_id=None,
        activity_id=None,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=(evidence,),
        reference_crosschecks=(),
    )
    import_result = import_research_evidence_bundle(conn, bundle)
    assert import_result.status.value in ("imported", "already_imported"), import_result
    conn.commit()

    resolution = FieldResolution(
        resolution_id="FR-0082-E2E-KEEL",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=design_id),
        field_pointer=JsonPointer(KEEL_TYPE_FIELD_POINTER),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot="fin",
        supporting_evidence_ids=frozenset({evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_broker_listing_design_association",
            version="1",
        ),
        resolved_at="2026-10-12T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    write_result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        fetch_canonical_value=lookup_keel_canonical_value,
        available_sources={wikidata_source_id: wikidata_source},
    )
    assert write_result.status is FieldResolutionWriteStatus.CREATED, write_result
    conn.commit()


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0082e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0082_e2e_"))
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from _publication_readiness_fixture import attach_d22_minimum_cover_image

        from hullq.domain.broker_access import AuthenticatedIdentity, Provider
        from hullq.domain.market_identity import NativeListingId, PhysicalBoatId
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
        from hullq.persistence.market_episode import fetch_market_episode
        from hullq.persistence.native_listing import fetch_native_listing
        from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
        from hullq.persistence.physical_boat import fetch_physical_boat
        from hullq.security.session_token import mint_session_token

        url = _with_search_path(base_url, schema_name)
        print("BROKER LISTING -> CANONICAL BOATDESIGN ASSOCIATION\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head (includes boat_design_association_events) -> OK")

        conn = psycopg.connect(url)
        try:
            _insert_boat_design_with_keel_baseline(conn, _DESIGN_ID, _MODEL_ID)
            _admit_keel_field_resolution(conn, _DESIGN_ID)
        finally:
            conn.close()
        print(
            f"0a. seeded one canonical BoatDesign ({_DESIGN_ID}, Beneteau Oceanis 30.1, FIN keel) "
            "with a real admitted FieldResolution -> OK\n"
        )

        api_port = _free_port()
        web_port = _free_port()
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)

        api_proc, _api_log_path = _start_api(
            url=url,
            api_port=api_port,
            preview_secret_b64=_b64url(preview_secret),
            session_secret_b64=_b64url(session_secret),
            web_base=web_base,
        )
        api_ready = _wait_for_http(f"{api_base}/api/broker/context")
        ok &= api_ready
        print(f"1. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")

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
            print("BROKER LISTING -> CANONICAL BOATDESIGN ASSOCIATION RESULT -> FAIL")
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
                    [_ACCOUNT_A_ID],
                )
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [_ACCOUNT_B_ID],
                )
            conn.commit()
            org_a = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_A_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            org_b = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_B_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org_a)
            seed_marketplace_organization(conn, org_b)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0082-A"),
                    account_id=AccountId(_ACCOUNT_A_ID),
                    organization_id=org_a.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0082-B"),
                    account_id=AccountId(_ACCOUNT_B_ID),
                    organization_id=org_b.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        print("3. seeded ORG_A/ORG_B (each one PUBLISHER account) -> OK\n")

        session_a = BrowserSession()
        session_a.jar.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name="hullq_session",
                value=_mint_cookie(_ACCOUNT_A_ID),
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

        # 1. Real promotion: create -> fill -> promote a professional draft
        # for ORG_A through the actual FastAPI endpoints (no direct SQL
        # insertion, no manual PhysicalBoat/MarketEpisode/NativeListing
        # creation).
        def _promote_ready_listing(listing_label: str) -> tuple[str, str]:
            """Returns `(native_listing_id, physical_boat_id)` for one
            freshly promoted, design-UNRESOLVED NativeListing."""
            status, _, body = session_a.post_json(
                f"{api_base}/api/broker/organizations/{_ORG_A_ID}/drafts",
                {},
                extra_headers=_csrf_headers(web_base, _DRAFT_CSRF_HEADER_VALUE),
            )
            assert status == 201, (status, body)
            draft = _json(body)
            draft_id = draft["draft_id"]
            version = draft["version"]

            status, _, body = session_a.put_json(
                f"{api_base}/api/broker/organizations/{_ORG_A_ID}/drafts/{draft_id}",
                {
                    "expected_version": version,
                    "physical_boat.marketed_brand_claim": "Beneteau",
                    "physical_boat.model_designation_claim": "Oceanis 30.1",
                    "physical_boat.build_year": {
                        "assertion_kind": "VALUE_ASSERTION",
                        "value": 2020,
                    },
                    "listing_offer.asking_price_mode": "AMOUNT",
                    "listing_offer.asking_price_amount": "125000.00",
                    "listing_offer.currency": "EUR",
                    "listing_offer.location_country": "FR",
                    "listing_offer.broker_description": f"{listing_label}: a well-maintained cruising sloop.",
                },
                extra_headers=_csrf_headers(web_base, _DRAFT_CSRF_HEADER_VALUE),
            )
            assert status == 200, (status, body)
            filled = _json(body)

            status, _, body = session_a.post_json(
                f"{api_base}/api/broker/organizations/{_ORG_A_ID}/drafts/{draft_id}/promote",
                {"expected_version": filled["version"]},
                extra_headers=_csrf_headers(web_base, _DRAFT_CSRF_HEADER_VALUE),
            )
            assert status == 201, (status, body)
            native_listing_id = _json(body)["native_listing_id"]

            conn = psycopg.connect(url)
            try:
                listing_record = fetch_native_listing(conn, NativeListingId(native_listing_id))
                assert listing_record is not None
                assert listing_record.listing.market_episode_id is not None
                episode_record = fetch_market_episode(
                    conn, listing_record.listing.market_episode_id
                )
                assert episode_record is not None
                physical_boat_id = episode_record.market_episode.physical_boat_id.value
                physical_boat_record = fetch_physical_boat(conn, PhysicalBoatId(physical_boat_id))
                assert physical_boat_record is not None
                assert physical_boat_record.physical_boat.boat_design_ref is None
                lifecycle = fetch_lifecycle_state(conn, listing_record.listing.id)
                assert lifecycle is not None and lifecycle.value == "DRAFT"
            finally:
                conn.close()
            return native_listing_id, physical_boat_id

        main_listing_id, main_physical_boat_id = _promote_ready_listing("NL-MAIN")
        print(
            f"4. real draft create -> fill -> promote via FastAPI produced {main_listing_id} "
            f"(lifecycle DRAFT, PhysicalBoat {main_physical_boat_id} design-UNRESOLVED) -> OK"
        )

        unlinked_listing_id, _unlinked_physical_boat_id = _promote_ready_listing("NL-UNLINKED")
        print(
            f"   a second independent listing {unlinked_listing_id} was promoted the same way -> OK\n"
        )

        # 2. Real browser: open the editor, search the bounded selector,
        # explicitly confirm the one real canonical candidate via a real
        # same-origin form POST.
        status, _, body = session_a.get(
            f"{web_base}{_edit_page_path(_ORG_A_ID, main_listing_id)}?design_q=Oceanis"
        )
        page_text = body.decode("utf-8")
        candidate_ul_present = "<li>" in page_text and _DESIGN_ID in page_text
        design_form = _form_block(page_text, f"<code>{_DESIGN_ID}</code>")
        parsed_candidate_ref = _hidden_field_value(design_form, "boat_design_ref")
        selector_ok = (
            status == 200
            and candidate_ul_present
            and parsed_candidate_ref == _DESIGN_ID
            and "Unresolved." in page_text
        )
        ok &= selector_ok
        print(
            f"5. the real editor's bounded selector surfaces {_DESIGN_ID} for a search of "
            f"'Oceanis', and the page shows UNRESOLVED before confirmation -> "
            f"{'OK' if selector_ok else 'FAIL'}"
        )

        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, main_listing_id)}",
            {"action": "associate_design", "boat_design_ref": parsed_candidate_ref},
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        confirm_ok = (
            status == 200
            and "Design confirmed and linked." in page_text
            and (f"Linked to <strong>{_DESIGN_ID}</strong>" in page_text)
        )
        ok &= confirm_ok
        print(
            f"   real browser form POST explicitly confirms {_DESIGN_ID}; page now shows LINKED -> "
            f"{'OK' if confirm_ok else 'FAIL'}"
        )

        conn = psycopg.connect(url)
        try:
            linked_record = fetch_physical_boat(conn, PhysicalBoatId(main_physical_boat_id))
            assert linked_record is not None
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM boat_design_association_events WHERE physical_boat_id = %s",
                    [main_physical_boat_id],
                )
                audit_count = cur.fetchone()[0]
        finally:
            conn.close()
        durable_ok = (
            linked_record.physical_boat.boat_design_ref is not None
            and linked_record.physical_boat.boat_design_ref.value == _DESIGN_ID
            and audit_count == 1
        )
        ok &= durable_ok
        print(
            f"   durable: physical_boats.boat_design_ref = {_DESIGN_ID} and exactly one audit "
            f"event recorded (read from a fresh connection) -> {'OK' if durable_ok else 'FAIL'}\n"
        )

        # 3. Negative cases -- zero mutation in every one.
        assoc_path = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/{main_listing_id}"
            "/design-association"
        )
        design_headers = _csrf_headers(web_base, _DESIGN_ASSOCIATION_CSRF_HEADER_VALUE)

        status, _, body = session_a.post_json(
            assoc_path, {"boat_design_ref": _DESIGN_ID}, extra_headers=design_headers
        )
        idempotent_ok = status == 200 and _json(body)["outcome"] == "ALREADY_LINKED"

        status, _, body = session_a.post_json(
            assoc_path, {"boat_design_ref": "BD-0082-E2E-OTHER"}, extra_headers=design_headers
        )
        conflict_ok = status == 409 and _json(body).get("boat_design_ref") == _DESIGN_ID

        # The boat is already linked at this point, so a *different* target
        # -- even one unknown to canonical_boat_designs -- correctly
        # resolves as CONFLICT (an existing link is read-only truth): the
        # DESIGN_NOT_FOUND classification only applies to a genuinely fresh,
        # still-unresolved PhysicalBoat, which is proven with real
        # PostgreSQL in `tests/persistence/
        # test_boat_design_association_persistence.py::
        # test_unknown_design_ref_fails_closed_and_writes_no_row`.
        status, _, body = session_a.post_json(
            assoc_path, {"boat_design_ref": "BD-DOES-NOT-EXIST"}, extra_headers=design_headers
        )
        unknown_design_ok = status == 409 and _json(body).get("boat_design_ref") == _DESIGN_ID

        session_b = BrowserSession()
        session_b.jar.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name="hullq_session",
                value=_mint_cookie(_ACCOUNT_B_ID),
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
        foreign_assoc_path = (
            f"{api_base}/api/broker/organizations/{_ORG_B_ID}/inventory/{main_listing_id}"
            "/design-association"
        )
        status, _, _ = session_b.post_json(
            foreign_assoc_path, {"boat_design_ref": _DESIGN_ID}, extra_headers=design_headers
        )
        foreign_ok = status == 404

        session_a_no_mfa = BrowserSession()
        session_a_no_mfa.jar.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name="hullq_session",
                value=_mint_cookie(_ACCOUNT_A_ID, mfa=False),
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
        status, _, body = session_a_no_mfa.post_json(
            assoc_path, {"boat_design_ref": _DESIGN_ID}, extra_headers=design_headers
        )
        mfa_ok = status == 403 and _json(body).get("error") == "mfa_required"

        conn = psycopg.connect(url)
        try:
            after_negatives = fetch_physical_boat(conn, PhysicalBoatId(main_physical_boat_id))
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM boat_design_association_events WHERE physical_boat_id = %s",
                    [main_physical_boat_id],
                )
                audit_count_after = cur.fetchone()[0]
        finally:
            conn.close()
        assert after_negatives is not None
        zero_mutation_ok = (
            after_negatives.physical_boat.boat_design_ref is not None
            and after_negatives.physical_boat.boat_design_ref.value == _DESIGN_ID
            and audit_count_after == 1
        )

        negatives_ok = (
            idempotent_ok
            and conflict_ok
            and unknown_design_ok
            and foreign_ok
            and mfa_ok
            and zero_mutation_ok
        )
        ok &= negatives_ok
        if not negatives_ok:
            print(
                "   DEBUG: "
                f"idempotent_ok={idempotent_ok} conflict_ok={conflict_ok} "
                f"unknown_design_ok={unknown_design_ok} foreign_ok={foreign_ok} mfa_ok={mfa_ok} "
                f"zero_mutation_ok={zero_mutation_ok}",
                file=sys.stderr,
            )
        print(
            f"6. exact retry idempotent (ALREADY_LINKED), different known/unknown targets both "
            f"conflict (409, carry {_DESIGN_ID}), foreign Organization 404, missing-MFA 403 "
            f"MFA_REQUIRED -- the stored link and audit count are unchanged by every one of these "
            f"attempts -> {'OK' if negatives_ok else 'FAIL'}\n"
        )

        # 4. Complete the concrete-yacht claim (add keel_configuration),
        # attach the required cover image, and publish.
        def _finish_and_publish(listing_id: str, physical_boat_id: str, *, add_keel: bool) -> None:
            conn = psycopg.connect(url)
            try:
                from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
                from hullq.persistence.physical_boat_claims import fetch_current_physical_boat_claim

                current_claim = fetch_current_physical_boat_claim(
                    conn, PhysicalBoatId(physical_boat_id), MarketplaceOrganizationId(_ORG_A_ID)
                )
                assert current_claim is not None
                current_revision_id = current_claim.revision_id.value
            finally:
                conn.close()

            if add_keel:
                claim_path = (
                    f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/{listing_id}/claim"
                )
                status, _, body = session_a.post_json(
                    claim_path,
                    {
                        "revision_id": str(uuid.uuid4()),
                        "expected_current_revision_id": current_revision_id,
                        "physical_boat.marketed_brand_claim": "Beneteau",
                        "physical_boat.model_designation_claim": "Oceanis 30.1",
                        "physical_boat.build_year": {
                            "assertion_kind": "VALUE_ASSERTION",
                            "value": 2020,
                        },
                        "physical_boat.keel_configuration": {
                            "assertion_kind": "VALUE_ASSERTION",
                            "value": "FIN",
                        },
                    },
                    extra_headers=_csrf_headers(web_base, _EDITING_CSRF_HEADER_VALUE),
                )
                assert status == 200, (status, body)

            conn = psycopg.connect(url)
            try:
                attach_d22_minimum_cover_image(
                    conn,
                    listing_id=listing_id,
                    account=AccountId(_ACCOUNT_A_ID),
                    org=MarketplaceOrganization(
                        id=MarketplaceOrganizationId(_ORG_A_ID),
                        professional_category=ProfessionalCategory.BROKER,
                        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            publish_path = (
                f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/{listing_id}/publish"
            )
            status, _, body = session_a.post_json(
                publish_path,
                {},
                extra_headers=_csrf_headers(web_base, _LIFECYCLE_CSRF_HEADER_VALUE),
            )
            assert status == 200, (status, body)
            assert _json(body)["outcome"] == "PUBLISHED", body

        _finish_and_publish(main_listing_id, main_physical_boat_id, add_keel=True)
        _finish_and_publish(unlinked_listing_id, _unlinked_physical_boat_id, add_keel=False)
        print(
            "7. completed the concrete-yacht claim (keel_configuration FIN) on the linked listing, "
            "attached the required cover image, and published both listings -> OK\n"
        )

        # 5. The deliberately unresolved listing remains fully reachable
        # through the existing public route.
        status, _, body = session_a.get(f"{api_base}/api/listings/{unlinked_listing_id}")
        unlinked_public_ok = status == 200
        ok &= unlinked_public_ok
        print(
            f"8. the deliberately design-UNRESOLVED listing {unlinked_listing_id} remains fully "
            f"reachable through the existing public listing route -> "
            f"{'OK' if unlinked_public_ok else 'FAIL'}\n"
        )

        # 6. Search proof.
        status, _, body = session_a.get(f"{api_base}/api/search/en?keel_configuration=FIN")
        search_result = _json(body)
        confirmed_ids = {m["native_listing_id"] for m in search_result.get("confirmed_matches", [])}
        search_ok = (
            status == 200
            and main_listing_id in confirmed_ids
            and unlinked_listing_id not in confirmed_ids
        )
        ok &= search_ok
        print(
            f"9. ordinary public technical Search for keel_configuration=FIN finds {main_listing_id} "
            f"as a CONFIRMED_MATCH and never surfaces the unresolved {unlinked_listing_id} -> "
            f"{'OK' if search_ok else 'FAIL'}"
        )

        draft_status, _, _ = session_a.get(f"{web_base}/en/search?draft_max=1.6")
        unknown_status, _, _ = session_a.get(
            f"{web_base}/en/search?draft_max=1.6&keel_configuration=FIN&beam_max=2.0"
        )
        criterion_count_ok = draft_status == 200 and unknown_status == 400
        ok &= criterion_count_ok
        print(
            f"   the accepted technical Search criterion count remains exactly 2 (draft_max=1.6 -> "
            f"200; an unrecognized third parameter -> 400) -> {'OK' if criterion_count_ok else 'FAIL'}\n"
        )

        print(
            f"BROKER LISTING -> CANONICAL BOATDESIGN ASSOCIATION RESULT -> "
            f"{'PASS' if ok else 'FAIL'}"
        )
        return 0 if ok else 1
    finally:
        for proc in (api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
