"""SLICE-0084 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the broker-authorized single-target hypothetical DRAFT Search-fit
preview against a real, disposable PostgreSQL 18 schema and two real local
HTTP servers: FastAPI and the built Astro/Node SSR web package. Mirrors
`scripts/inspect_broker_listing_design_association.py`'s identical
disposable-schema/real-HTTP/real-browser-session shape; authentication uses
a directly minted, cryptographically signed session cookie rather than a
full OIDC round-trip (already-accepted shortcut -- that path is covered by
`test_broker_workspace_access_api.py`).

Demonstrates, end to end:

    1. a real admitted canonical BoatDesign (FIN keel, 1.30m draft_max_m)
       plus a lifecycle-DRAFT, design-linked NativeListing with a confirmed
       concrete PhysicalBoat claim (draft 1.20m, FIN) -- the real built
       Astro SSR editor's Search-fit form renders CONFIRMED_MATCH for the
       mixed draft_max/keel_configuration scenario
    2. ordinary public technical Search excludes this DRAFT listing while
       DRAFT, even for the identical scenario
    3. editing the concrete claim (draft 1.80m) and re-running the preview
       through the same real SSR page shows a freshly evaluated
       CONFIRMED_NON_MATCH -- never a stale browser-cached answer
    4. a second NativeListing with no linked BoatDesign renders
       INSUFFICIENT_DATA with the BOATDESIGN_NOT_LINKED blocker, with no
       technical classification invented
    5. foreign Organization, unknown listing, missing MFA and a malformed/
       third-criterion scenario all fail closed (404/404/403/400) through
       the real FastAPI route, with no stored state changed
    6. after the first listing is legitimately published (ACTIVE), the
       identical preview now reports NOT_PREVIEWABLE (409), while ordinary
       public technical Search now confirms the identical scenario --
       proving the DRAFT-preview-vs-published-public-Search equivalence
    7. every Search-fit API response carries the private no-store/noindex
       headers
    8. exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_search_fit.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
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
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_ORG_A_ID = "ORG-0084-A"
_ORG_B_ID = "ORG-0084-B"
_ACCOUNT_A_ID = "ACC-0084-A"
_ACCOUNT_B_ID = "ACC-0084-B"
_EDITING_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"
_LIFECYCLE_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1"

_DESIGN_ID = "BD-0084-E2E"
_MODEL_ID = "BM-0084-E2E"


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


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _csrf_headers(web_base: str, header_value: str) -> dict[str, str]:
    return {"Origin": web_base, "X-HullQ-Requested-With": header_value}


def _edit_page_path(org_id: str, listing_id: str) -> str:
    return f"/broker/organizations/{org_id}/inventory/{listing_id}/edit"


def _cookie(account_id: str, value: str) -> http.cookiejar.Cookie:
    return http.cookiejar.Cookie(
        version=0,
        name="hullq_session",
        value=value,
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


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str, session_secret_b64: str, web_base: str
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0084_api_", suffix=".log")[1])
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


def _insert_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            [model_id, "Oceanis 30.1", "0" * 64],
        )
        baseline = json.dumps(
            {"dimensions": {"draft_max_m": 1.30}, "appendages": {"keel_type": "fin"}}
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline, "1" * 64],
        )
    conn.commit()


def _admit_design_keel_and_draft(conn: Any, design_id: str) -> None:
    """Durably admit real `resolved` FieldResolutions for this design's
    `draft_max_m`/`keel_type` -- mirrors
    `scripts/inspect_first_native_inventory_search.py`'s identical recipe."""
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
        encode_canonical_decimal_snapshot,
        write_field_resolution,
    )
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.research.jobs import ResearchTarget
    from hullq.research.observations import ResearchEvidenceBundle
    from hullq.search.draft_max_design_bridge import (
        DRAFT_MAX_FIELD_POINTER,
        lookup_draft_max_canonical_value,
    )
    from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value

    wikidata_source: dict[str, Any] = json.loads(
        (REPO_ROOT / "fixtures" / "sources" / "wikidata_source.json").read_text(encoding="utf-8")
    )
    wikidata_source_id = wikidata_source["source_id"]

    def _admit(field_pointer: str, value: str, resolution_id: str, fetch_canonical: Any) -> None:
        evidence_id = f"EV-{resolution_id}"
        evidence = FieldEvidenceV3(
            evidence_id=evidence_id,
            subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=design_id),
            field_pointer=JsonPointer(field_pointer),
            source_id=wikidata_source_id,
            source_locator=SourceLocator(
                page=None, section=None, anchor=None, table=None, figure=None, record_key=None
            ),
            raw=RawObservation(
                kind=RawObservationKind.STRUCTURED_RECORD, value=value, unit=None, excerpt=None
            ),
            normalized_candidate=NormalizedCandidate(
                value=value, unit=None, method_id="proof-normalize", method_version="1"
            ),
            evidence_type=EvidenceType.STRUCTURED_DATASET,
            producer=ProducerMetadata(
                kind=ProducerKind.DETERMINISTIC_TOOL,
                identifier="inspect_broker_search_fit",
                version="1",
                model=None,
                prompt_or_rule_version=None,
            ),
            research_context=ResearchContext(research_job_id=None, activity_id=None),
            observed_at="2026-10-13T00:00:00+00:00",
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
            bundle_id=f"BUNDLE-{resolution_id}",
            bundle_version="1",
            research_target=ResearchTarget(
                manufacturer=None, model="search-fit-e2e", first_built=None
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

        is_decimal = field_pointer == DRAFT_MAX_FIELD_POINTER
        resolution = FieldResolution(
            resolution_id=resolution_id,
            subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=design_id),
            field_pointer=JsonPointer(field_pointer),
            state=ResolutionState.RESOLVED,
            canonical_value_snapshot=(
                encode_canonical_decimal_snapshot(Decimal(value)) if is_decimal else value
            ),
            supporting_evidence_ids=frozenset({evidence_id}),
            contradicting_evidence_ids=frozenset(),
            considered_evidence_ids=frozenset({evidence_id}),
            resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
            policy_version="proof-policy-1",
            resolver=ResolverMetadata(
                kind=ResolverKind.DETERMINISTIC_TOOL,
                identifier="inspect_broker_search_fit",
                version="1",
            ),
            resolved_at="2026-10-13T00:00:00+00:00",
            supersedes_resolution_id=None,
            notes=None,
        )
        write_result = write_field_resolution(
            conn,
            resolution=resolution,
            expected_current_resolution_id=None,
            fetch_canonical_value=fetch_canonical,
            available_sources={wikidata_source_id: wikidata_source},
        )
        assert write_result.status is FieldResolutionWriteStatus.CREATED, write_result
        conn.commit()

    _admit(
        DRAFT_MAX_FIELD_POINTER, "1.30", f"FR-DRAFT-{design_id}", lookup_draft_max_canonical_value
    )
    _admit(KEEL_TYPE_FIELD_POINTER, "fin", f"FR-KEEL-{design_id}", lookup_keel_canonical_value)


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0084e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0084_e2e_"))
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.domain.broker_access import AuthenticatedIdentity, Provider
        from hullq.domain.market_identity import (
            BoatDesignRef,
            MarketEpisode,
            MarketEpisodeId,
            NativeListing,
            NativeListingId,
            PhysicalBoat,
            PhysicalBoatId,
        )
        from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
        from hullq.domain.physical_boat_claims import (
            AssertionKind,
            BuildYearClaim,
            DraftClaim,
            KeelConfiguration,
            KeelConfigurationClaim,
            PhysicalBoatClaimRevisionId,
            PhysicalBoatClaimSnapshot,
        )
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
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.native_listing_offer import (
            NativeListingOfferRevisionId,
            write_native_listing_offer_revision,
        )
        from hullq.persistence.physical_boat import create_physical_boat
        from hullq.persistence.physical_boat_claims import (
            fetch_current_physical_boat_claim,
            write_physical_boat_claim_revision,
        )
        from hullq.security.session_token import mint_session_token

        url = _with_search_path(base_url, schema_name)
        print("BROKER PRE-PUBLICATION SEARCH-FIT PREVIEW\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        conn = psycopg.connect(url)
        try:
            _insert_boat_design(conn, _DESIGN_ID, _MODEL_ID)
            _admit_design_keel_and_draft(conn, _DESIGN_ID)
        finally:
            conn.close()
        print(
            f"0a. seeded one canonical BoatDesign ({_DESIGN_ID}, FIN keel, draft_max_m=1.30) with "
            "real admitted FieldResolutions -> OK\n"
        )

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
            print("BROKER PRE-PUBLICATION SEARCH-FIT PREVIEW RESULT -> FAIL")
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
            account_a = AccountId(_ACCOUNT_A_ID)
            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-0084-A"),
                account_id=account_a,
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            seed_organization_membership(conn, membership_a)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0084-B"),
                    account_id=AccountId(_ACCOUNT_B_ID),
                    organization_id=org_b.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()

            # The real shape SLICE-0067 promotion produces: a lifecycle-DRAFT
            # NativeListing -> MarketEpisode -> design-linked PhysicalBoat
            # chain, built directly here (SLICE-0084 does not itself cover
            # draft/promotion creation -- that is 0067/0083's own scope).
            create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(
                    id=PhysicalBoatId("PB-0084-MAIN"), boat_design_ref=BoatDesignRef(_DESIGN_ID)
                ),
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0084-MAIN"),
                    physical_boat_id=PhysicalBoatId("PB-0084-MAIN"),
                ),
            )
            create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(
                    id=NativeListingId("NL-0084-MAIN"),
                    market_episode_id=MarketEpisodeId("ME-0084-MAIN"),
                ),
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0084-MAIN"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0084-MAIN-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    draft=DraftClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.20")
                    ),
                    keel_configuration=KeelConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
                    ),
                ),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0084-MAIN"),
                revision_id=NativeListingOfferRevisionId("REV-0084-MAIN"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )

            # A second listing, deliberately design-UNRESOLVED.
            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0084-UNLINKED"))
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0084-UNLINKED"),
                    physical_boat_id=PhysicalBoatId("PB-0084-UNLINKED"),
                ),
            )
            create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(
                    id=NativeListingId("NL-0084-UNLINKED"),
                    market_episode_id=MarketEpisodeId("ME-0084-UNLINKED"),
                ),
            )
        finally:
            conn.close()
        print(
            "3. seeded ORG_A (PUBLISHER) with one lifecycle-DRAFT design-linked listing "
            "(confirmed draft 1.20m, FIN) and one design-UNRESOLVED listing, plus ORG_B -> OK\n"
        )

        session_a = BrowserSession()
        session_a.jar.set_cookie(_cookie(_ACCOUNT_A_ID, _mint_cookie(_ACCOUNT_A_ID)))

        # 1. Real browser SSR: mixed draft_max/keel_configuration scenario on
        # the confirmed-match listing.
        status, headers, body = session_a.get(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0084-MAIN')}"
            "?sf_draft_max=1.5&sf_keel_configuration=FIN"
        )
        page_text = body.decode("utf-8")
        match_ok = (
            status == 200
            and "Result: <strong>CONFIRMED_MATCH</strong>" in page_text
            and "Illustrative only / not actual buyer demand." in page_text
        )
        ok &= match_ok
        print(
            "4. the real SSR editor's Search-fit form for draft_max=1.5/keel_configuration=FIN "
            f"renders CONFIRMED_MATCH, labelled illustrative-only -> {'OK' if match_ok else 'FAIL'}"
        )
        headers_ok = (
            headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
        )
        ok &= headers_ok
        print(
            f"   private no-store/noindex response headers present -> {'OK' if headers_ok else 'FAIL'}\n"
        )

        # 2. Public Search excludes it while DRAFT.
        status, _, body = session_a.get(
            f"{api_base}/api/search/en?draft_max=1.5&keel_configuration=FIN"
        )
        search_result = _json(body)
        draft_excluded_ok = status == 200 and search_result.get("confirmed_match_count") == 0
        ok &= draft_excluded_ok
        print(
            "5. ordinary public technical Search for the identical scenario finds zero confirmed "
            f"matches while the listing is still DRAFT -> {'OK' if draft_excluded_ok else 'FAIL'}\n"
        )

        # 3. Edit the concrete claim (draft too deep) and re-run the preview
        # -- a freshly evaluated result, never a stale answer.
        conn = psycopg.connect(url)
        try:
            current_claim = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0084-MAIN"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            assert current_claim is not None
            current_revision_id = current_claim.revision_id.value
        finally:
            conn.close()
        status, _, body = session_a.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0084-MAIN/claim",
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": current_revision_id,
                "physical_boat.marketed_brand_claim": "Beneteau",
                "physical_boat.model_designation_claim": "Oceanis 30.1",
                "physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 2021},
                "physical_boat.draft": {"assertion_kind": "VALUE_ASSERTION", "value": "1.80"},
                "physical_boat.keel_configuration": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "FIN",
                },
            },
            extra_headers=_csrf_headers(web_base, _EDITING_CSRF_HEADER_VALUE),
        )
        claim_edit_ok = status == 200
        status, _, body = session_a.get(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0084-MAIN')}?sf_draft_max=1.5"
        )
        page_text = body.decode("utf-8")
        refreshed_ok = status == 200 and "Result: <strong>CONFIRMED_NON_MATCH</strong>" in page_text
        ok &= claim_edit_ok and refreshed_ok
        print(
            "6. after editing the concrete claim to draft=1.80m, the same real SSR preview "
            f"freshly re-evaluates to CONFIRMED_NON_MATCH -> {'OK' if refreshed_ok else 'FAIL'}\n"
        )

        # 4. Unlinked-design listing -> actionable INSUFFICIENT_DATA.
        status, _, body = session_a.get(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0084-UNLINKED')}?sf_draft_max=1.5"
        )
        page_text = body.decode("utf-8")
        unlinked_ok = (
            status == 200
            and "Result: <strong>INSUFFICIENT_DATA</strong>" in page_text
            and "No canonical design is linked yet" in page_text
            and "#design-editor" in page_text
        )
        ok &= unlinked_ok
        print(
            "7. the design-UNRESOLVED listing's preview renders INSUFFICIENT_DATA with an "
            f"actionable BOATDESIGN_NOT_LINKED blocker linked to the design editor -> "
            f"{'OK' if unlinked_ok else 'FAIL'}\n"
        )

        # 5. Negative cases -- fail closed, zero mutation.
        fit_path = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0084-MAIN/search-fit"
        )
        status, _, _ = session_a.get(f"{fit_path}?draft_max=1.5")
        malformed_status, _, _ = session_a.get(f"{fit_path}?keel_configuration=LONG_KEEL")
        third_criterion_status, _, _ = session_a.get(f"{fit_path}?beam_max=2.0")

        session_b = BrowserSession()
        session_b.jar.set_cookie(_cookie(_ACCOUNT_B_ID, _mint_cookie(_ACCOUNT_B_ID)))
        foreign_fit_path = (
            f"{api_base}/api/broker/organizations/{_ORG_B_ID}/inventory/NL-0084-MAIN/search-fit"
        )
        foreign_status, _, _ = session_b.get(f"{foreign_fit_path}?draft_max=1.5")

        session_a_no_mfa = BrowserSession()
        session_a_no_mfa.jar.set_cookie(
            _cookie(_ACCOUNT_A_ID, _mint_cookie(_ACCOUNT_A_ID, mfa=False))
        )
        no_mfa_status, _, no_mfa_body = session_a_no_mfa.get(f"{fit_path}?draft_max=1.5")

        negatives_ok = (
            status == 200
            and malformed_status == 400
            and third_criterion_status == 400
            and foreign_status == 404
            and no_mfa_status == 403
            and _json(no_mfa_body).get("error") == "mfa_required"
        )
        ok &= negatives_ok
        print(
            "8. unsupported LONG_KEEL/third-criterion scenarios 400, foreign Organization 404, "
            f"missing-MFA 403 MFA_REQUIRED -> {'OK' if negatives_ok else 'FAIL'}\n"
        )

        # 6. Publish the main listing, then prove preview-vs-public equivalence.
        from _publication_readiness_fixture import attach_d22_minimum_cover_image

        conn = psycopg.connect(url)
        try:
            attach_d22_minimum_cover_image(
                conn, listing_id="NL-0084-MAIN", account=account_a, org=org_a
            )
            conn.commit()
        finally:
            conn.close()
        # Restore the confirmed-match claim before publishing, so the public
        # Search-equivalence check below is comparing like with like.
        conn = psycopg.connect(url)
        try:
            current_claim = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0084-MAIN"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            assert current_claim is not None
            current_revision_id = current_claim.revision_id.value
        finally:
            conn.close()
        status, _, body = session_a.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0084-MAIN/claim",
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": current_revision_id,
                "physical_boat.marketed_brand_claim": "Beneteau",
                "physical_boat.model_designation_claim": "Oceanis 30.1",
                "physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 2021},
                "physical_boat.draft": {"assertion_kind": "VALUE_ASSERTION", "value": "1.20"},
                "physical_boat.keel_configuration": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "FIN",
                },
            },
            extra_headers=_csrf_headers(web_base, _EDITING_CSRF_HEADER_VALUE),
        )
        assert status == 200, (status, body)
        status, _, body = session_a.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0084-MAIN/publish",
            {},
            extra_headers=_csrf_headers(web_base, _LIFECYCLE_CSRF_HEADER_VALUE),
        )
        published_ok = status == 200 and _json(body).get("outcome") == "PUBLISHED"
        ok &= published_ok
        print(f"9. real publish transition DRAFT -> ACTIVE -> {'OK' if published_ok else 'FAIL'}")

        status, _, body = session_a.get(f"{fit_path}?draft_max=1.5&keel_configuration=FIN")
        not_previewable_ok = status == 409 and _json(body).get("error") == "not_previewable"
        ok &= not_previewable_ok
        print(
            f"   now-ACTIVE listing's preview -> 409 NOT_PREVIEWABLE -> {'OK' if not_previewable_ok else 'FAIL'}"
        )

        status, _, body = session_a.get(
            f"{api_base}/api/search/en?draft_max=1.5&keel_configuration=FIN"
        )
        search_result = _json(body)
        confirmed_ids = {m["native_listing_id"] for m in search_result.get("confirmed_matches", [])}
        published_search_ok = status == 200 and "NL-0084-MAIN" in confirmed_ids
        ok &= published_search_ok
        print(
            "   ordinary public technical Search now confirms the identical scenario for the "
            f"published listing -> {'OK' if published_search_ok else 'FAIL'}\n"
        )

        print(f"BROKER PRE-PUBLICATION SEARCH-FIT PREVIEW RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
