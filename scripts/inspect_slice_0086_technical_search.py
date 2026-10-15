"""SLICE-0086 PR #349 independent-review Finding C owner-visible end-to-end
proof -- real PostgreSQL 18 + real HTTP + real **built** Astro SSR.

PR #349 review (exact HEAD `6402dfdaf11f6e09d4faa97c34a9c2f7cea459c3`) Finding
C (MAJOR / PROOF GATE): the original SLICE-0086 handoff added PG18/FastAPI
persistence+API tests, Node component/text tests and an Astro build, but no
retained executable proof that exercises the three new facets
(`hull_configuration`/`cockpit_position`/`deck_saloon`) against the real
**built** Astro SSR surfaces -- `scripts/inspect_multicriteria_technical_search.py`
documents only the 0085 LOA/rudder criteria. This script is that proof,
scoped to exactly SLICE-0086's own three new facets plus the same amendment's
Finding A/B/D fixes; it reuses
`scripts/inspect_multicriteria_technical_search.py`'s identical disposable-
schema/real-HTTP/real-browser-session/real-FieldResolution-admission
conventions rather than re-proving SLICE-0051/0055/0084/0085's own
already-executed base behavior.

Demonstrates, end to end:

    1. private broker Search-fit SSR (listing still DRAFT): all three new
       facets combined render CONFIRMED_MATCH on the real built editor page,
       with the real per-criterion design/concrete evidence text actually
       present (not only the aggregate class)
    2. broker claim save -> real HTTP write of the three new claim fields,
       then a real re-GET of the built editor page proves the saved values
       are genuinely reopened from durable state, not merely echoed back
       from the POST response
    3. a real publish transition takes the listing DRAFT -> ACTIVE
    4. public buyer Search SSR (`/en/search`), now against the published
       listing: each new facet alone, and all three combined, each confirm
       the identical match with the real rendered observed concrete value
    4b. Finding D: the same combined-match page also renders the separate
        design/configuration-level evidence FastAPI already returns --
        proving the buyer-visible distinction between design truth and
        physical-offer truth, not only a type-level check
    5. the same three-facet combined scenario repeated against every one of
       the five accepted public Search locales, each with its own real
       canonical `<link>` href and its own real localized observed-evidence
       text (concrete AND design-level)
    6. Finding A: a second real BoatDesign/listing whose `deck_saloon` is a
       confirmed, source-backed `none` never produces a false confirmed
       match for a buyer requesting `DECK_SALOON`, through the real built
       SSR page (never only the unit-level bridge check)
    7. Finding B: a third real BoatDesign/listing whose `cockpit_position`
       is confirmed `multiple` but whose own `cockpit_count` is confirmed
       `1` never produces a false confirmed match for a buyer requesting
       `MULTIPLE`, through the real built SSR page
    8. negative: an unsupported `hull_configuration=OTHER` value is a real
       SSR 400; a non-canonical key order (`hull_configuration` before
       `cockpit_position`) 308-redirects to the canonical order
    9. exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_slice_0086_technical_search.py
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

_ORG_ID = "ORG-0086-E2E"
_ACCOUNT_ID = "ACC-0086-E2E"
_EDITING_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"
_LIFECYCLE_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1"

_DESIGN_ID = "BD-0086-E2E"
_MODEL_ID = "BM-0086-E2E"
_LISTING_ID = "NL-0086-MAIN"

# Finding A proof fixture: a design/listing whose deck_saloon is a confirmed
# `none`.
_NONE_DESIGN_ID = "BD-0086-NONE"
_NONE_MODEL_ID = "BM-0086-NONE"
_NONE_LISTING_ID = "NL-0086-NONE"
_NONE_ORG_ID = "ORG-0086-NONE"
_NONE_ACCOUNT_ID = "ACC-0086-NONE"

# Finding B proof fixture: a design/listing whose cockpit_position is
# confirmed `multiple` but cockpit_count is confirmed 1 (contradiction).
_MULTI_DESIGN_ID = "BD-0086-MULTI1"
_MULTI_MODEL_ID = "BM-0086-MULTI1"
_MULTI_LISTING_ID = "NL-0086-MULTI1"
_MULTI_ORG_ID = "ORG-0086-MULTI1"
_MULTI_ACCOUNT_ID = "ACC-0086-MULTI1"


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
    `scripts/inspect_multicriteria_technical_search.py`'s identical
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

    def post_form(
        self, url: str, fields: dict[str, str], *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            **(extra_headers or {}),
        }
        from urllib.parse import urlencode

        return self.request(
            "POST", url, extra_headers=headers, data=urlencode(fields).encode("utf-8")
        )

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
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0086_api_", suffix=".log")[1])
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


def _insert_boat_design(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    hull_configuration: str | None,
    hull_count: int | None,
    cockpit_position: str | None,
    cockpit_count: int | None,
    deck_saloon: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline = json.dumps(
            {
                "configuration": {
                    "hull_configuration": hull_configuration,
                    "hull_count": hull_count,
                },
                "deck": {
                    "cockpit_position": cockpit_position,
                    "cockpit_count": cockpit_count,
                    "deck_saloon": deck_saloon,
                },
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


def _admit_design_field(
    conn: Any,
    *,
    design_id: str,
    field_pointer: str,
    raw_value: str,
    resolution_id: str,
    fetch_canonical: Any,
    is_decimal: bool,
) -> None:
    """Admit one real `resolved` FieldResolution via the genuine production
    write path (`import_research_evidence_bundle` + `write_field_resolution`)
    -- mirrors `scripts/inspect_multicriteria_technical_search.py`'s
    `_admit_design_fields` recipe exactly, generalized to one call per field
    so this script can admit an arbitrary bounded set per design fixture."""
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

    wikidata_source: dict[str, Any] = json.loads(
        (REPO_ROOT / "fixtures" / "sources" / "wikidata_source.json").read_text(encoding="utf-8")
    )
    wikidata_source_id = wikidata_source["source_id"]

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
            kind=RawObservationKind.STRUCTURED_RECORD, value=raw_value, unit=None, excerpt=None
        ),
        normalized_candidate=NormalizedCandidate(
            value=raw_value, unit=None, method_id="proof-normalize", method_version="1"
        ),
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="inspect_slice_0086_technical_search",
            version="1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-10-15T00:00:00+00:00",
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
            manufacturer=None, model="slice-0086-e2e", first_built=None
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
            encode_canonical_decimal_snapshot(Decimal(raw_value)) if is_decimal else raw_value
        ),
        supporting_evidence_ids=frozenset({evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_slice_0086_technical_search",
            version="1",
        ),
        resolved_at="2026-10-15T00:00:00+00:00",
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


def _seed_org_account_listing(
    conn: Any,
    *,
    org_id: str,
    account_id: str,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    design_id: str,
) -> Any:
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

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )
    conn.commit()
    org = MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    seed_marketplace_organization(conn, org)
    account = AccountId(account_id)
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-{org_id}"),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    seed_organization_membership(conn, membership)
    conn.commit()

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(design_id)
        ),
    )
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
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
            broker_description="A well-maintained cruising boat.",
            asking_price_amount=Decimal("250000.00"),
            currency="EUR",
        ),
    )
    return account, org, membership


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0086e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0086_e2e_"))
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.domain.broker_access import AuthenticatedIdentity, Provider
        from hullq.domain.market_identity import NativeListingId
        from hullq.domain.physical_boat_claims import (
            AssertionKind,
            BuildYearClaim,
            CockpitPosition,
            CockpitPositionClaim,
            DeckSaloon,
            DeckSaloonClaim,
            HullConfiguration,
            HullConfigurationClaim,
            PhysicalBoatClaimRevisionId,
            PhysicalBoatClaimSnapshot,
        )
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )
        from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
        from hullq.search.cockpit_design_bridge import lookup_cockpit_position_canonical_value
        from hullq.search.deck_saloon_design_bridge import lookup_deck_saloon_canonical_value
        from hullq.search.hull_design_bridge import lookup_hull_configuration_canonical_value
        from hullq.security.session_token import mint_session_token

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _publication_readiness_fixture import attach_d22_minimum_cover_image

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0086 PR #349 FINDING C: TECHNICAL SEARCH PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        conn = psycopg.connect(url)
        try:
            # --- Main design/listing: all three facets confirmed, consistent ---
            _insert_boat_design(
                conn,
                _DESIGN_ID,
                _MODEL_ID,
                hull_configuration="catamaran",
                hull_count=2,
                cockpit_position="center",
                cockpit_count=2,
                deck_saloon="deck_saloon",
            )
            _admit_design_field(
                conn,
                design_id=_DESIGN_ID,
                field_pointer="/baseline/configuration/hull_configuration",
                raw_value="catamaran",
                resolution_id=f"FR-HULLCFG-{_DESIGN_ID}",
                fetch_canonical=lookup_hull_configuration_canonical_value,
                is_decimal=False,
            )
            _admit_design_field(
                conn,
                design_id=_DESIGN_ID,
                field_pointer="/baseline/deck/cockpit_position",
                raw_value="center",
                resolution_id=f"FR-COCKPITPOS-{_DESIGN_ID}",
                fetch_canonical=lookup_cockpit_position_canonical_value,
                is_decimal=False,
            )
            _admit_design_field(
                conn,
                design_id=_DESIGN_ID,
                field_pointer="/baseline/deck/deck_saloon",
                raw_value="deck_saloon",
                resolution_id=f"FR-DECKSALOON-{_DESIGN_ID}",
                fetch_canonical=lookup_deck_saloon_canonical_value,
                is_decimal=False,
            )

            # --- Finding A fixture: confirmed deck_saloon=none ------------------
            _insert_boat_design(
                conn,
                _NONE_DESIGN_ID,
                _NONE_MODEL_ID,
                hull_configuration=None,
                hull_count=None,
                cockpit_position=None,
                cockpit_count=None,
                deck_saloon="none",
            )
            _admit_design_field(
                conn,
                design_id=_NONE_DESIGN_ID,
                field_pointer="/baseline/deck/deck_saloon",
                raw_value="none",
                resolution_id=f"FR-DECKSALOON-{_NONE_DESIGN_ID}",
                fetch_canonical=lookup_deck_saloon_canonical_value,
                is_decimal=False,
            )

            # --- Finding B fixture: confirmed multiple + confirmed count=1 ------
            _insert_boat_design(
                conn,
                _MULTI_DESIGN_ID,
                _MULTI_MODEL_ID,
                hull_configuration=None,
                hull_count=None,
                cockpit_position="multiple",
                cockpit_count=1,
                deck_saloon=None,
            )
            _admit_design_field(
                conn,
                design_id=_MULTI_DESIGN_ID,
                field_pointer="/baseline/deck/cockpit_position",
                raw_value="multiple",
                resolution_id=f"FR-COCKPITPOS-{_MULTI_DESIGN_ID}",
                fetch_canonical=lookup_cockpit_position_canonical_value,
                is_decimal=False,
            )
            _admit_design_field(
                conn,
                design_id=_MULTI_DESIGN_ID,
                field_pointer="/baseline/deck/cockpit_count",
                raw_value="1",
                resolution_id=f"FR-COCKPITCOUNT-{_MULTI_DESIGN_ID}",
                fetch_canonical=lookup_cockpit_position_canonical_value,
                is_decimal=True,
            )
        finally:
            conn.close()
        print(
            "0a. seeded three canonical BoatDesigns (main: CATAMARAN/CENTER/DECK_SALOON "
            "all confirmed; Finding A: confirmed deck_saloon=none; Finding B: confirmed "
            "cockpit_position=multiple with confirmed cockpit_count=1) with real admitted "
            "FieldResolutions -> OK\n"
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
        api_ready = _wait_for_http(f"{api_base}/api/broker/context", timeout_seconds=40.0)
        ok &= api_ready
        print(f"1. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print(
                f"    (api log: {api_log_path})\n"
                + api_log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
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
        web_ready = _wait_for_http(f"{web_base}/broker", timeout_seconds=40.0)
        ok &= web_ready
        print(f"2. Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")
        if not web_ready:
            print(
                f"    (web log: {web_log_path})\n"
                + web_log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            )

        if not ok:
            print("SLICE-0086 TECHNICAL SEARCH PROOF RESULT -> FAIL")
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

        from hullq.domain.publishing_eligibility import AccountId

        conn = psycopg.connect(url)
        try:
            account, org, membership = _seed_org_account_listing(
                conn,
                org_id=_ORG_ID,
                account_id=_ACCOUNT_ID,
                listing_id=_LISTING_ID,
                physical_boat_id="PB-0086-MAIN",
                market_episode_id="ME-0086-MAIN",
                design_id=_DESIGN_ID,
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0086-MAIN-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Lagoon",
                    model_designation_claim="42",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2019
                    ),
                    hull_configuration=HullConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=HullConfiguration.CATAMARAN,
                    ),
                    cockpit_position=CockpitPositionClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=CockpitPosition.CENTER,
                    ),
                    deck_saloon=DeckSaloonClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=DeckSaloon.DECK_SALOON,
                    ),
                ),
            )

            none_account, none_org, none_membership = _seed_org_account_listing(
                conn,
                org_id=_NONE_ORG_ID,
                account_id=_NONE_ACCOUNT_ID,
                listing_id=_NONE_LISTING_ID,
                physical_boat_id="PB-0086-NONE",
                market_episode_id="ME-0086-NONE",
                design_id=_NONE_DESIGN_ID,
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=none_account,
                candidate_organization=none_org,
                membership=none_membership,
                native_listing_id=NativeListingId(_NONE_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0086-NONE-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Jeanneau",
                    model_designation_claim="Sun Odyssey",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2018
                    ),
                ),
            )

            multi_account, multi_org, multi_membership = _seed_org_account_listing(
                conn,
                org_id=_MULTI_ORG_ID,
                account_id=_MULTI_ACCOUNT_ID,
                listing_id=_MULTI_LISTING_ID,
                physical_boat_id="PB-0086-MULTI1",
                market_episode_id="ME-0086-MULTI1",
                design_id=_MULTI_DESIGN_ID,
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=multi_account,
                candidate_organization=multi_org,
                membership=multi_membership,
                native_listing_id=NativeListingId(_MULTI_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0086-MULTI1-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Bavaria",
                    model_designation_claim="Cruiser 46",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2017
                    ),
                ),
            )
        finally:
            conn.close()
        print(
            "3. seeded ORG_A (main, PUBLISHER, lifecycle-DRAFT) plus the Finding A and "
            "Finding B fixture Organizations/listings -> OK\n"
        )

        session = BrowserSession()
        session.jar.set_cookie(_cookie(_ACCOUNT_ID, _mint_cookie(_ACCOUNT_ID)))
        none_session = BrowserSession()
        none_session.jar.set_cookie(_cookie(_NONE_ACCOUNT_ID, _mint_cookie(_NONE_ACCOUNT_ID)))
        multi_session = BrowserSession()
        multi_session.jar.set_cookie(_cookie(_MULTI_ACCOUNT_ID, _mint_cookie(_MULTI_ACCOUNT_ID)))

        # --- 1. broker Search-fit SSR, all three new facets, listing DRAFT ---
        status, headers, body = session.get(
            f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}"
            "?sf_hull_configuration=CATAMARAN&sf_cockpit_position=CENTER&sf_deck_saloon=DECK_SALOON"
        )
        page_text = body.decode("utf-8")
        broker_fit_ok = (
            status == 200
            and "Result: <strong>CONFIRMED_MATCH</strong>" in page_text
            and "Canonical design result: <strong>CONFIRMED_MATCH</strong>" in page_text
            and headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
            and "hull_configuration = CATAMARAN: TRUE" in page_text
            and "cockpit_position = CENTER: TRUE" in page_text
            and "deck_saloon = DECK_SALOON: TRUE" in page_text
            and "design value: CATAMARAN" in page_text
            and "design value: CENTER" in page_text
            and "design value: DECK_SALOON" in page_text
        )
        ok &= broker_fit_ok
        print(
            "1. private broker Search-fit SSR (DRAFT listing), all three SLICE-0086 "
            f"facets -> CONFIRMED_MATCH with real per-criterion evidence -> "
            f"{'OK' if broker_fit_ok else 'FAIL'}\n"
        )

        # --- 2. broker claim save (real HTTP write) + real re-GET reopen -----
        save_fields = {
            "action": "save_claim",
            "revision_id": "PBCREV-0086-MAIN-2",
            "expected_current_revision_id": "PBCREV-0086-MAIN-1",
            "marketed_brand_claim": "Lagoon",
            "model_designation_claim": "42",
            "build_year_kind": "VALUE_ASSERTION",
            "build_year_value": "2019",
            "hull_configuration_kind": "VALUE_ASSERTION",
            "hull_configuration_value": "CATAMARAN",
            "cockpit_position_kind": "VALUE_ASSERTION",
            "cockpit_position_value": "CENTER",
            "deck_saloon_kind": "VALUE_ASSERTION",
            "deck_saloon_value": "DECK_SALOON",
        }
        status, _, body = session.post_form(
            f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}",
            save_fields,
            extra_headers=_csrf_headers(web_base, _EDITING_CSRF_HEADER_VALUE),
        )
        save_ok = status == 200
        ok &= save_ok
        print(f"2. real broker claim save (POST, new HullQ facet fields) -> {'OK' if save_ok else 'FAIL'}")

        status, _, body = session.get(f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}")
        page_text = body.decode("utf-8")
        reopen_ok = (
            status == 200
            and 'name="hull_configuration_value"' in page_text
            and 'value="CATAMARAN" selected' in page_text
            and 'value="CENTER" selected' in page_text
            and 'value="DECK_SALOON" selected' in page_text
        )
        ok &= reopen_ok
        print(
            "   real re-GET of the built editor page reopens the saved CATAMARAN/CENTER/"
            f"DECK_SALOON claim from durable state -> {'OK' if reopen_ok else 'FAIL'}\n"
        )

        # --- 3. publish DRAFT -> ACTIVE for the main listing ------------------
        conn = psycopg.connect(url)
        try:
            attach_d22_minimum_cover_image(conn, listing_id=_LISTING_ID, account=account, org=org)
            attach_d22_minimum_cover_image(
                conn, listing_id=_NONE_LISTING_ID, account=none_account, org=none_org
            )
            attach_d22_minimum_cover_image(
                conn, listing_id=_MULTI_LISTING_ID, account=multi_account, org=multi_org
            )
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
        status, _, body = none_session.post_json(
            f"{api_base}/api/broker/organizations/{_NONE_ORG_ID}/inventory/{_NONE_LISTING_ID}/publish",
            {},
            extra_headers=_csrf_headers(web_base, _LIFECYCLE_CSRF_HEADER_VALUE),
        )
        none_published_ok = status == 200 and _json(body).get("outcome") == "PUBLISHED"
        ok &= none_published_ok
        status, _, body = multi_session.post_json(
            f"{api_base}/api/broker/organizations/{_MULTI_ORG_ID}/inventory/{_MULTI_LISTING_ID}/publish",
            {},
            extra_headers=_csrf_headers(web_base, _LIFECYCLE_CSRF_HEADER_VALUE),
        )
        multi_published_ok = status == 200 and _json(body).get("outcome") == "PUBLISHED"
        ok &= multi_published_ok
        print(
            "3. real publish transitions DRAFT -> ACTIVE for all three listings -> "
            f"{'OK' if (published_ok and none_published_ok and multi_published_ok) else 'FAIL'}\n"
        )

        # --- 4. public buyer Search SSR, each new facet alone -----------------
        status, _, body = session.get(f"{web_base}/en/search?hull_configuration=CATAMARAN")
        page_text = body.decode("utf-8")
        hull_only_ok = (
            status == 200
            and _LISTING_ID in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared hull form: Catamaran (not independently verified)" in page_text
        )
        ok &= hull_only_ok
        print(f"4. public Search SSR, hull_configuration=CATAMARAN -> {'OK' if hull_only_ok else 'FAIL'}")

        status, _, body = session.get(f"{web_base}/en/search?cockpit_position=CENTER")
        page_text = body.decode("utf-8")
        cockpit_only_ok = (
            status == 200
            and _LISTING_ID in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared cockpit position: Center cockpit (not independently verified)"
            in page_text
        )
        ok &= cockpit_only_ok
        print(f"   public Search SSR, cockpit_position=CENTER -> {'OK' if cockpit_only_ok else 'FAIL'}")

        status, _, body = session.get(f"{web_base}/en/search?deck_saloon=DECK_SALOON")
        page_text = body.decode("utf-8")
        deck_saloon_only_ok = (
            status == 200
            and _LISTING_ID in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared deck saloon/pilothouse: Deck saloon (not independently verified)"
            in page_text
        )
        ok &= deck_saloon_only_ok
        print(
            f"   public Search SSR, deck_saloon=DECK_SALOON -> {'OK' if deck_saloon_only_ok else 'FAIL'}"
        )

        # Canonical order: cockpit_position, deck_saloon, hull_configuration.
        combined_query = "cockpit_position=CENTER&deck_saloon=DECK_SALOON&hull_configuration=CATAMARAN"
        status, _, body = session.get(f"{web_base}/en/search?{combined_query}")
        page_text = body.decode("utf-8")
        combined_ok = (
            status == 200
            and _LISTING_ID in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared hull form: Catamaran (not independently verified)" in page_text
            and "broker-declared cockpit position: Center cockpit (not independently verified)"
            in page_text
            and "broker-declared deck saloon/pilothouse: Deck saloon (not independently verified)"
            in page_text
        )
        ok &= combined_ok
        print(
            "   public Search SSR, all three SLICE-0086 facets combined -> confirmed match "
            f"with every real observed value rendered -> {'OK' if combined_ok else 'FAIL'}\n"
        )

        # --- 4b. Finding D: design/configuration evidence visibly distinct ---
        design_evidence_ok = (
            'aria-label="design configuration evidence"' in page_text
            and "Design/configuration specification (separate from this boat&#39;s own claim)"
            in page_text
            and f"{_DESIGN_ID}::baseline" in page_text
            and "hull_configuration = CATAMARAN: confirmed" in page_text
            and "cockpit_position = CENTER: confirmed" in page_text
            and "deck_saloon = DECK_SALOON: confirmed" in page_text
        )
        ok &= design_evidence_ok
        print(
            "4b. Finding D: the same combined-match page also renders the separate "
            f"design/configuration-level evidence -> {'OK' if design_evidence_ok else 'FAIL'}\n"
        )

        # --- 5. all five public Search locales, combined scenario ------------
        _locale_text: dict[str, dict[str, str]] = {
            "en": {
                "confirmed_heading": "Confirmed matches",
                "hull_evidence": "broker-declared hull form: Catamaran (not independently verified)",
                "cockpit_evidence": "broker-declared cockpit position: Center cockpit (not independently verified)",
                "deck_saloon_evidence": "broker-declared deck saloon/pilothouse: Deck saloon (not independently verified)",
                "design_heading": "Design/configuration specification (separate from this boat&#39;s own claim)",
            },
            "de": {
                "confirmed_heading": "Bestätigte Treffer",
                "hull_evidence": "vom Makler angegebene Rumpfform: Katamaran (nicht unabhängig verifiziert)",
                "cockpit_evidence": "vom Makler angegebene Cockpit-Position: Mittiges Cockpit (nicht unabhängig verifiziert)",
                "deck_saloon_evidence": "vom Makler angegebener Decksalon/Pilothouse: Decksalon (nicht unabhängig verifiziert)",
                "design_heading": "Design-/Konfigurationsspezifikation (getrennt von der Angabe des Maklers)",
            },
            "fr": {
                "confirmed_heading": "Résultats confirmés",
                "hull_evidence": "forme de carène déclarée par le courtier : Catamaran (non vérifiée de manière indépendante)",
                "cockpit_evidence": "position de cockpit déclarée par le courtier : Cockpit central (non vérifiée de manière indépendante)",
                "deck_saloon_evidence": "salon de pont/timonerie déclaré par le courtier : Salon de pont (non vérifié de manière indépendante)",
                "design_heading": "Spécification du design/de la configuration (distincte de la déclaration du courtier)",
            },
            "pt": {
                "confirmed_heading": "Correspondências confirmadas",
                "hull_evidence": "forma de casco declarada pelo corretor: Catamarã (não verificada de forma independente)",
                "cockpit_evidence": "posição de cockpit declarada pelo corretor: Cockpit central (não verificada de forma independente)",
                "deck_saloon_evidence": "salão de convés/casa do leme declarado pelo corretor: Salão de convés (não verificado de forma independente)",
                "design_heading": "Especificação do design/configuração (separada da declaração do corretor)",
            },
            "es": {
                "confirmed_heading": "Coincidencias confirmadas",
                "hull_evidence": "forma de casco declarada por el bróker: Catamarán (no verificada de forma independiente)",
                "cockpit_evidence": "posición de bañera declarada por el bróker: Bañera central (no verificada de forma independiente)",
                "deck_saloon_evidence": "salón de cubierta/timonera declarado por el bróker: Salón de cubierta (no verificado de forma independiente)",
                "design_heading": "Especificación del diseño/configuración (independiente de la declaración del bróker)",
            },
        }
        locale_canonical_href = (
            f'<link rel="canonical" href="http://127.0.0.1:{web_port}/{{locale}}/search?'
            "cockpit_position=CENTER&amp;deck_saloon=DECK_SALOON&amp;hull_configuration=CATAMARAN\">"
        )
        all_locales_ok = True
        for locale, text in _locale_text.items():
            status, _, body = session.get(f"{web_base}/{locale}/search?{combined_query}")
            page_text = body.decode("utf-8")
            locale_ok = (
                status == 200
                and _LISTING_ID in page_text
                and f"{text['confirmed_heading']} (1)" in page_text
                and locale_canonical_href.format(locale=locale) in page_text
                and text["hull_evidence"] in page_text
                and text["cockpit_evidence"] in page_text
                and text["deck_saloon_evidence"] in page_text
                and text["design_heading"] in page_text
            )
            all_locales_ok &= locale_ok
            print(
                f"5. public Search SSR /{locale}/search (all three SLICE-0086 facets) -> "
                "canonical URL + confirmed match with real localized concrete AND design "
                f"evidence -> {'OK' if locale_ok else 'FAIL'}"
            )
        ok &= all_locales_ok
        print()

        # --- 6. Finding A: confirmed deck_saloon=none never falsely matches --
        status, _, body = session.get(f"{web_base}/en/search?deck_saloon=DECK_SALOON")
        page_text = body.decode("utf-8")
        finding_a_ok = status == 200 and _NONE_LISTING_ID not in page_text
        ok &= finding_a_ok
        print(
            "6. Finding A: a listing whose design deck_saloon is confirmed `none` never "
            f"falsely matches deck_saloon=DECK_SALOON through the real built SSR page -> "
            f"{'OK' if finding_a_ok else 'FAIL'}"
        )
        status, _, body = session.get(f"{web_base}/en/search?deck_saloon=PILOTHOUSE")
        page_text = body.decode("utf-8")
        finding_a_pilothouse_ok = status == 200 and _NONE_LISTING_ID not in page_text
        ok &= finding_a_pilothouse_ok
        print(
            "   Finding A: the same confirmed-none listing never falsely matches "
            f"deck_saloon=PILOTHOUSE either -> {'OK' if finding_a_pilothouse_ok else 'FAIL'}\n"
        )

        # --- 7. Finding B: confirmed multiple+count=1 never falsely matches --
        status, _, body = session.get(f"{web_base}/en/search?cockpit_position=MULTIPLE")
        page_text = body.decode("utf-8")
        finding_b_ok = status == 200 and _MULTI_LISTING_ID not in page_text
        ok &= finding_b_ok
        print(
            "7. Finding B: a listing whose design cockpit_position is confirmed `multiple` "
            "but whose own cockpit_count is confirmed 1 never falsely matches "
            f"cockpit_position=MULTIPLE through the real built SSR page -> "
            f"{'OK' if finding_b_ok else 'FAIL'}\n"
        )

        # --- 8. negative: unsupported value -> 400; non-canonical order -> 308
        status, _, body = session.get(
            f"{web_base}/en/search?hull_configuration=OTHER", extra_headers={}
        )
        invalid_value_ok = status == 400
        ok &= invalid_value_ok
        print(
            f"8. negative: hull_configuration=OTHER -> real SSR 400 -> "
            f"{'OK' if invalid_value_ok else 'FAIL'}"
        )

        status, headers, _ = session.get(
            f"{web_base}/en/search?hull_configuration=CATAMARAN&cockpit_position=CENTER"
        )
        redirect_ok = (
            status == 308
            and headers.get("Location")
            == "/en/search?cockpit_position=CENTER&hull_configuration=CATAMARAN"
        )
        ok &= redirect_ok
        print(
            "   negative: non-canonical key order (hull_configuration before "
            f"cockpit_position) -> 308 to canonical order -> {'OK' if redirect_ok else 'FAIL'}\n"
        )

        print(
            "SLICE-0086 TECHNICAL SEARCH PROOF RESULT -> "
            f"{'PASS' if ok else 'FAIL'} [SLICE-0086-FINDING-C-DONE]"
        )
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
