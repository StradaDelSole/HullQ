"""SLICE-0085 review amendment Finding D owner-visible end-to-end proof --
real PostgreSQL 18 + real HTTP.

PR #345 review ID 5509076907 Finding D (MAJOR): the original SLICE-0085
handoff carried no executed real-PostgreSQL/FastAPI/built-Astro-SSR proof for
its two new criteria (`loa_min`/`loa_max`, `rudder_configuration`) or for the
Finding A/B fixes landed in this same amendment. This script is that proof,
scoped to exactly what SLICE-0085's amendment changed -- it does not
re-prove SLICE-0084's own already-executed broker Search-fit base behavior
(`scripts/inspect_broker_search_fit.py`) or SLICE-0055/0057's own already-
executed keel/sensitivity base behavior
(`scripts/inspect_first_native_inventory_search.py`); it reuses both
scripts' identical disposable-schema/real-HTTP/real-browser-session
conventions.

PR #345 review ID 5509994284 (second amendment) Finding D coverage gap: the
first version of this script asserted only listing id + match count for
public Search, aggregate `CONFIRMED_MATCH` for broker Search-fit, and only
the `/en/search` locale. Steps 4, 7, and 7b below were extended/added to
check the real rendered per-criterion leaf evidence (observed LOA/rudder/
draft/keel values, design- and concrete-level truth lines) and all five
accepted public Search locales (`en`/`de`/`fr`/`pt`/`es`), each with a real
filtered request, its own real canonical `<link>` href, and its own real
localized observed-evidence text -- not merely that the page returns 200.

Demonstrates, end to end, against one real admitted canonical BoatDesign
(FIN keel, draft_max_m=1.30, loa_m=12.50, rudder_support=skeg -- SKEG_HUNG)
and its one lifecycle-DRAFT, design-linked, confirmed-matching concrete
listing (published partway through, exactly where noted below):

    1. private broker Search-fit SSR (listing still DRAFT): a five-criterion
       scenario (draft_max/keel_configuration/loa_min/loa_max/
       rudder_configuration combined) renders CONFIRMED_MATCH on the real
       built editor page, with private no-store/noindex headers, and the
       real per-criterion design/concrete leaf evidence text (including the
       real observed draft/keel/LOA/rudder values) is actually present, not
       only the aggregate class
    2. negative: a duplicate `sf_loa_max` parameter fails closed on the real
       SSR editor page without ever reaching FastAPI
    3. negative: an unauthenticated real HTTP call to the Search-fit API is
       401
    4. negative: a foreign Organization's real HTTP call to this listing's
       Search-fit API is 404
    5. negative: a malformed (oversized) `loa_max` value is a real HTTP 400
       `invalid_scenario` through the Search-fit API
    6. a real publish transition takes the listing DRAFT -> ACTIVE
    7. public buyer Search SSR (`/en/search`), now against the published
       listing: LOA-only, rudder-only, and all five criteria combined each
       confirm the identical match, each checked against the real rendered
       observed criterion value text, not only the match count
    7b. the same loa_max+rudder_configuration scenario repeated against
       every one of the five accepted public Search locales
       (`/de/`, `/fr/`, `/pt/`, `/es/`, plus `/en/` again): each real
       request is itself the canonical URL (its own real `<link
       rel="canonical">` href is checked), confirms the identical match, and
       renders its own real localized observed LOA/rudder evidence text
    8. Finding B: an oversized raw `loa_max` value fails closed 400 through
       the real SSR page, not merely the unit-level parser; a non-canonical
       parameter order 308-redirects to the canonical order
    9. Finding A: a mixed old+new active-criterion Search (draft_max +
       loa_max) renders the new truthful "sensitivity unavailable" text and
       never the original sensitivity forms; an old-only active-criterion
       Search (draft_max + keel_configuration) still renders the original
       sensitivity forms byte-identically (non-regression)
   10. exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_multicriteria_technical_search.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import json
import os
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

_ORG_ID = "ORG-0085-E2E"
_ORG_FOREIGN_ID = "ORG-0085-FOREIGN"
_ACCOUNT_ID = "ACC-0085-E2E"
_ACCOUNT_FOREIGN_ID = "ACC-0085-FOREIGN"
_EDITING_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"
_LIFECYCLE_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1"

_DESIGN_ID = "BD-0085-E2E"
_MODEL_ID = "BM-0085-E2E"
_LISTING_ID = "NL-0085-MAIN"

# Finding B: comfortably past `src/hullq/search/loa_request.py`'s
# `_MAX_LOA_RAW_LENGTH = 20` cap.
_OVERSIZED_LOA_RAW = "9" * 25


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
    import socket

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
    `scripts/inspect_broker_search_fit.py`'s identical `BrowserSession`."""

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
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0085_api_", suffix=".log")[1])
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
            {
                "dimensions": {"draft_max_m": 1.30, "loa_m": 12.50},
                "appendages": {"keel_type": "fin", "rudder_support": "skeg"},
            }
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


def _admit_design_fields(conn: Any, design_id: str) -> None:
    """Durably admit real `resolved` FieldResolutions for this design's
    `draft_max_m`/`keel_type`/`loa_m`/`appendages.rudder_support` -- mirrors
    `scripts/inspect_broker_search_fit.py`'s identical recipe, extended to
    SLICE-0085's two new criteria."""
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
    from hullq.search.loa_design_bridge import LOA_FIELD_POINTER, lookup_loa_canonical_value
    from hullq.search.rudder_design_bridge import lookup_rudder_canonical_value

    _RUDDER_SUPPORT_V06_POINTER = "/baseline/appendages/rudder_support"

    wikidata_source: dict[str, Any] = json.loads(
        (REPO_ROOT / "fixtures" / "sources" / "wikidata_source.json").read_text(encoding="utf-8")
    )
    wikidata_source_id = wikidata_source["source_id"]

    def _admit(
        field_pointer: str,
        value: str,
        resolution_id: str,
        fetch_canonical: Any,
        *,
        is_decimal: bool,
    ) -> None:
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
                identifier="inspect_multicriteria_technical_search",
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
                manufacturer=None, model="multicriteria-search-e2e", first_built=None
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
                identifier="inspect_multicriteria_technical_search",
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
        DRAFT_MAX_FIELD_POINTER,
        "1.30",
        f"FR-DRAFT-{design_id}",
        lookup_draft_max_canonical_value,
        is_decimal=True,
    )
    _admit(
        KEEL_TYPE_FIELD_POINTER,
        "fin",
        f"FR-KEEL-{design_id}",
        lookup_keel_canonical_value,
        is_decimal=False,
    )
    _admit(
        LOA_FIELD_POINTER,
        "12.50",
        f"FR-LOA-{design_id}",
        lookup_loa_canonical_value,
        is_decimal=True,
    )
    _admit(
        _RUDDER_SUPPORT_V06_POINTER,
        "skeg",
        f"FR-RUDDER-{design_id}",
        lookup_rudder_canonical_value,
        is_decimal=False,
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
    schema_name = f"hullq_s0085e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0085_e2e_"))
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
            LoaLengthClaim,
            PhysicalBoatClaimRevisionId,
            PhysicalBoatClaimSnapshot,
            RudderConfiguration,
            RudderConfigurationClaim,
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
        from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
        from hullq.security.session_token import mint_session_token

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _publication_readiness_fixture import attach_d22_minimum_cover_image

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0085 AMENDMENT FINDING D: MULTI-CRITERIA TECHNICAL SEARCH PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        conn = psycopg.connect(url)
        try:
            _insert_boat_design(conn, _DESIGN_ID, _MODEL_ID)
            _admit_design_fields(conn, _DESIGN_ID)
        finally:
            conn.close()
        print(
            f"0a. seeded one canonical BoatDesign ({_DESIGN_ID}: FIN keel, draft_max_m=1.30, "
            "loa_m=12.50, rudder_support=skeg -> SKEG_HUNG) with real admitted "
            "FieldResolutions for all four fields -> OK\n"
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
            print("MULTI-CRITERIA TECHNICAL SEARCH PROOF RESULT -> FAIL")
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
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [_ACCOUNT_FOREIGN_ID],
                )
            conn.commit()
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            org_foreign = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_FOREIGN_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org)
            seed_marketplace_organization(conn, org_foreign)
            account = AccountId(_ACCOUNT_ID)
            membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-0085-A"),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            seed_organization_membership(conn, membership)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0085-FOREIGN"),
                    account_id=AccountId(_ACCOUNT_FOREIGN_ID),
                    organization_id=org_foreign.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()

            create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(
                    id=PhysicalBoatId("PB-0085-MAIN"), boat_design_ref=BoatDesignRef(_DESIGN_ID)
                ),
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0085-MAIN"),
                    physical_boat_id=PhysicalBoatId("PB-0085-MAIN"),
                ),
            )
            create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_LISTING_ID),
                    market_episode_id=MarketEpisodeId("ME-0085-MAIN"),
                ),
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0085-MAIN-1"),
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
                    loa_length=LoaLengthClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("11.80")
                    ),
                    rudder_configuration=RudderConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=RudderConfiguration.SKEG_HUNG,
                    ),
                ),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
                revision_id=NativeListingOfferRevisionId("REV-0085-MAIN"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )
        finally:
            conn.close()
        print(
            "3. seeded ORG_A (PUBLISHER) with one lifecycle-DRAFT design-linked listing "
            "(confirmed draft 1.20m, FIN, loa 11.80m, SKEG_HUNG) plus a foreign ORG -> OK\n"
        )

        session = BrowserSession()
        session.jar.set_cookie(_cookie(_ACCOUNT_ID, _mint_cookie(_ACCOUNT_ID)))
        foreign_session = BrowserSession()
        foreign_session.jar.set_cookie(
            _cookie(_ACCOUNT_FOREIGN_ID, _mint_cookie(_ACCOUNT_FOREIGN_ID))
        )

        fit_path = (
            f"{api_base}/api/broker/organizations/{_ORG_ID}/inventory/{_LISTING_ID}/search-fit"
        )

        # Canonical key order (lexicographic) AND canonical decimal form
        # (trailing zeros stripped -- `canonical_loa_str`/
        # `canonical_draft_max_str`) for every value, so this exact request
        # is itself the canonical RESULT, never a 308 redirect.
        mixed_all_query = (
            "draft_max=1.6&keel_configuration=FIN&loa_max=15&loa_min=10"
            "&rudder_configuration=SKEG_HUNG"
        )

        # The listing is still lifecycle-DRAFT at this point -- broker
        # Search-fit preview (and its negative cases) is exercised first,
        # exactly like `scripts/inspect_broker_search_fit.py`'s own ordering,
        # since a published/ACTIVE listing's preview is 409 NOT_PREVIEWABLE.

        # --- 4. broker Search-fit SSR, all five criteria --------------------
        status, headers, body = session.get(
            f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}"
            "?sf_draft_max=1.6&sf_keel_configuration=FIN&sf_loa_min=10&sf_loa_max=15"
            "&sf_rudder_configuration=SKEG_HUNG"
        )
        page_text = body.decode("utf-8")
        # Review amendment (PR #345 review 5509994284, Finding D coverage
        # gap): the aggregate `CONFIRMED_MATCH` alone does not prove the
        # real per-criterion leaf evidence actually rendered -- check the
        # exact design-level and concrete-level criterion lines
        # `describeCriterion`/the template produce for every one of the
        # five active criteria, including the real observed LOA/rudder
        # values (design loa_m=12.50, concrete claim loa_length=11.80,
        # concrete claim rudder_configuration=SKEG_HUNG).
        broker_fit_ok = (
            status == 200
            and "Result: <strong>CONFIRMED_MATCH</strong>" in page_text
            and "Canonical design result: <strong>CONFIRMED_MATCH</strong>" in page_text
            and headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
            and "draft_max_m &lt;= 1.6: TRUE" in page_text
            and "keel_configuration = FIN: TRUE" in page_text
            and "loa_m &gt;= 10: TRUE" in page_text
            and "loa_m &lt;= 15: TRUE" in page_text
            and "rudder_configuration = SKEG_HUNG: TRUE" in page_text
            and "design value: 12.50" in page_text
            and "this boat's current claim: 1.20" in page_text
            and "this boat's current claim: 11.80" in page_text
            and "this boat's current claim: SKEG_HUNG" in page_text
            and "this boat's current claim: FIN" in page_text
        )
        ok &= broker_fit_ok
        print(
            "4. private broker Search-fit SSR (DRAFT listing), all five criteria -> "
            f"CONFIRMED_MATCH with private no-store/noindex headers -> {'OK' if broker_fit_ok else 'FAIL'}"
        )

        # --- negative: duplicate sf_loa_max rejected client-side ------------
        status, _, body = session.get(
            f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}?sf_loa_max=15&sf_loa_max=5"
        )
        page_text = body.decode("utf-8")
        duplicate_ok = status == 200 and "duplicate/ambiguous parameter was submitted" in page_text
        ok &= duplicate_ok
        print(
            f"   negative: duplicate sf_loa_max -> real SSR ambiguous-scenario rejection -> "
            f"{'OK' if duplicate_ok else 'FAIL'}\n"
        )

        # --- 5. negative: unauthenticated API call -> 401 --------------------
        anonymous_session = BrowserSession()
        status, _, body = anonymous_session.get(f"{fit_path}?loa_max=15")
        unauthenticated_ok = status == 401
        ok &= unauthenticated_ok
        print(
            f"5. negative: unauthenticated Search-fit API call -> 401 -> {'OK' if unauthenticated_ok else 'FAIL'}"
        )

        # --- negative: foreign Organization -> 404 ---------------------------
        status, _, body = foreign_session.get(f"{fit_path}?loa_max=15")
        foreign_ok = status == 404
        ok &= foreign_ok
        print(
            f"   negative: foreign Organization's Search-fit API call -> 404 -> {'OK' if foreign_ok else 'FAIL'}"
        )

        # --- negative: malformed (oversized) loa_max -> 400 invalid_scenario -
        status, _, body = session.get(f"{fit_path}?loa_max={_OVERSIZED_LOA_RAW}")
        malformed_ok = status == 400 and _json(body).get("error") == "invalid_scenario"
        ok &= malformed_ok
        print(
            "   negative: malformed (oversized) loa_max via real Search-fit API -> 400 "
            f"invalid_scenario -> {'OK' if malformed_ok else 'FAIL'}\n"
        )

        # --- 6. publish DRAFT -> ACTIVE --------------------------------------
        conn = psycopg.connect(url)
        try:
            attach_d22_minimum_cover_image(conn, listing_id=_LISTING_ID, account=account, org=org)
            conn.commit()
        finally:
            conn.close()
        status, _, body = session.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_ID}/inventory/{_LISTING_ID}/publish",
            {},
            extra_headers=_csrf_headers(web_base, _LIFECYCLE_CSRF_HEADER_VALUE),
        )
        published_ok = status == 200 and _json(body).get("outcome") == "PUBLISHED"
        ok &= published_ok
        print(f"6. real publish transition DRAFT -> ACTIVE -> {'OK' if published_ok else 'FAIL'}\n")

        # Everything below is real public buyer Search against the now-
        # published listing -- the DRAFT-preview-vs-published-public-Search
        # equivalence SLICE-0084 already proved, extended to the two new
        # criteria.

        # --- 7. LOA-only public Search SSR -----------------------------------
        # Review amendment (PR #345 review 5509994284, Finding D coverage
        # gap): a confirmed-match proof must check the REAL rendered
        # technical evidence (the concrete claim's own observed LOA/rudder
        # value), not merely the listing id and match count.
        status, _, body = session.get(f"{web_base}/en/search?loa_max=15")
        page_text = body.decode("utf-8")
        loa_only_ok = (
            status == 200
            and f"{_LISTING_ID}" in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared length overall: 11.80 m" in page_text
        )
        ok &= loa_only_ok
        print(
            f"7. public Search SSR, loa_max=15 (LOA-only) -> confirmed match with real observed "
            f"LOA evidence -> {'OK' if loa_only_ok else 'FAIL'}"
        )

        # --- rudder-only public Search SSR -----------------------------------
        status, _, body = session.get(f"{web_base}/en/search?rudder_configuration=SKEG_HUNG")
        page_text = body.decode("utf-8")
        rudder_only_ok = (
            status == 200
            and f"{_LISTING_ID}" in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared rudder configuration: Skeg-hung rudder" in page_text
        )
        ok &= rudder_only_ok
        print(
            "   public Search SSR, rudder_configuration=SKEG_HUNG (rudder-only) -> confirmed "
            f"match with real observed rudder evidence -> {'OK' if rudder_only_ok else 'FAIL'}"
        )

        # --- all five criteria combined ---------------------------------------
        status, _, body = session.get(f"{web_base}/en/search?{mixed_all_query}")
        page_text = body.decode("utf-8")
        mixed_all_ok = (
            status == 200
            and f"{_LISTING_ID}" in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared draft: 1.20 m" in page_text
            and "broker-declared keel configuration: Fin keel" in page_text
            and "broker-declared length overall: 11.80 m" in page_text
            and "broker-declared rudder configuration: Skeg-hung rudder" in page_text
        )
        ok &= mixed_all_ok
        print(
            "   public Search SSR, all five criteria combined -> confirmed match with every "
            f"real observed criterion value rendered -> {'OK' if mixed_all_ok else 'FAIL'}\n"
        )

        # --- 7b. all five public Search locales, each with a real filtered,
        # canonical request verifying real rendered LOA/rudder evidence
        # (review amendment Finding D coverage gap) -------------------------
        _locale_text: dict[str, dict[str, str]] = {
            "en": {
                "confirmed_heading": "Confirmed matches",
                "loa_prefix": "broker-declared length overall:",
                "rudder_prefix": "broker-declared rudder configuration:",
                "skeg_hung_label": "Skeg-hung rudder",
            },
            "de": {
                "confirmed_heading": "Bestätigte Treffer",
                "loa_prefix": "vom Makler angegebene Gesamtlänge:",
                "rudder_prefix": "vom Makler angegebene Ruderkonfiguration:",
                "skeg_hung_label": "Skegruder",
            },
            "fr": {
                "confirmed_heading": "Résultats confirmés",
                "loa_prefix": "longueur hors tout déclarée par le courtier :",
                "rudder_prefix": "configuration de safran déclarée par le courtier :",
                "skeg_hung_label": "Safran sur aileron (skeg)",
            },
            "pt": {
                "confirmed_heading": "Correspondências confirmadas",
                "loa_prefix": "comprimento total declarado pelo corretor:",
                "rudder_prefix": "configuração de leme declarada pelo corretor:",
                "skeg_hung_label": "Leme em skeg",
            },
            "es": {
                "confirmed_heading": "Coincidencias confirmadas",
                "loa_prefix": "eslora total declarada por el bróker:",
                "rudder_prefix": "configuración de timón declarada por el bróker:",
                "skeg_hung_label": "Timón en skeg",
            },
        }
        locale_query = "loa_max=15&rudder_configuration=SKEG_HUNG"
        # Astro HTML-escapes the `&` query separator inside the `href`
        # attribute (`&amp;`) -- the raw request URL itself still uses a
        # literal `&` (`session.get` below), only the rendered canonical
        # link text differs.
        locale_canonical_href = (
            f'<link rel="canonical" href="http://127.0.0.1:{web_port}/{{locale}}/search?'
            'loa_max=15&amp;rudder_configuration=SKEG_HUNG">'
        )
        all_locales_ok = True
        for locale, text in _locale_text.items():
            status, _, body = session.get(f"{web_base}/{locale}/search?{locale_query}")
            page_text = body.decode("utf-8")
            locale_ok = (
                status == 200
                and f"{_LISTING_ID}" in page_text
                and f"{text['confirmed_heading']} (1)" in page_text
                and locale_canonical_href.format(locale=locale) in page_text
                and f"{text['loa_prefix']} 11.80 m" in page_text
                and f"{text['rudder_prefix']} {text['skeg_hung_label']}" in page_text
            )
            all_locales_ok &= locale_ok
            print(
                f"7b. public Search SSR /{locale}/search (loa_max+rudder_configuration) -> "
                f"canonical URL + confirmed match with real localized observed evidence -> "
                f"{'OK' if locale_ok else 'FAIL'}"
            )
        ok &= all_locales_ok
        print()

        # --- 8. Finding B: oversized loa_max -> 400 ---------------------------
        status, _, body = session.get(f"{web_base}/en/search?loa_max={_OVERSIZED_LOA_RAW}")
        oversized_loa_ok = status == 400
        ok &= oversized_loa_ok
        print(
            f"8. Finding B: oversized raw loa_max -> real SSR 400 -> {'OK' if oversized_loa_ok else 'FAIL'}"
        )

        # --- non-canonical order -> 308 ----------------------------------------
        status, headers, _ = session.get(f"{web_base}/en/search?loa_min=10&loa_max=15")
        redirect_ok = (
            status == 308 and headers.get("Location") == "/en/search?loa_max=15&loa_min=10"
        )
        ok &= redirect_ok
        print(
            f"   non-canonical loa_min-before-loa_max order -> 308 to canonical order -> "
            f"{'OK' if redirect_ok else 'FAIL'}\n"
        )

        # --- 9. Finding A: mixed old+new -> sensitivity unavailable ----------
        status, _, body = session.get(f"{web_base}/en/search?draft_max=1.6&loa_max=15")
        page_text = body.decode("utf-8")
        mixed_sensitivity_ok = (
            status == 200
            and 'aria-label="requirement sensitivity unavailable"' in page_text
            and "isn&#39;t available while a length overall or rudder configuration filter"
            in page_text
            and 'name="current_draft_max"' not in page_text
        )
        ok &= mixed_sensitivity_ok
        print(
            "9. Finding A: mixed draft_max+loa_max renders truthful sensitivity-unavailable "
            f"text, never the original forms -> {'OK' if mixed_sensitivity_ok else 'FAIL'}"
        )

        # --- Finding A non-regression: old-only keeps original forms ---------
        status, _, body = session.get(f"{web_base}/en/search?draft_max=1.6&keel_configuration=FIN")
        page_text = body.decode("utf-8")
        legacy_sensitivity_ok = (
            status == 200
            and 'aria-label="requirement sensitivity"' in page_text
            and 'name="current_draft_max"' in page_text
            and 'name="current_keel_configuration"' in page_text
            and "sensitivity unavailable" not in page_text
        )
        ok &= legacy_sensitivity_ok
        print(
            "   Finding A non-regression: old-only draft_max+keel_configuration keeps the "
            f"original sensitivity forms byte-identically -> {'OK' if legacy_sensitivity_ok else 'FAIL'}\n"
        )

        print(
            "MULTI-CRITERIA TECHNICAL SEARCH PROOF RESULT -> "
            f"{'PASS' if ok else 'FAIL'} [SLICE-0085-AMENDMENT-FINDING-D-DONE]"
        )
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
