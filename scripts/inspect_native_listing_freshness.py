"""SLICE-0052 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed NativeListing freshness/reconfirmation vertical
against a real, disposable PostgreSQL 18 schema and real local HTTP servers
(FastAPI + built Astro/Node SSR), per
`specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md` §10:

    publish
    -> ACTIVE + CONFIRMED -> public listing visible -> matching Search result visible
    exact +30d -> DUE_FOR_CONFIRMATION -> still visible with due disclosure
    exact +37d -> STALE -> absent from public listing content and Search;
                  lifecycle remains ACTIVE
    authorized reconfirmation -> CONFIRMED again -> visibility restored

Freshness evaluation time is advanced deterministically -- without sleeping
and without rewriting any audit timestamp -- via FastAPI's server-side-only
``HULLQ_FRESHNESS_AS_OF_OVERRIDE_ISO`` environment variable
(``hullq.api.app``): the API process is restarted between phases with a
different override value while Astro (which only proxies to FastAPI over
HTTP) keeps running unchanged against the same API port throughout.

The proof also demonstrates:

    - a pre-existing ACTIVE listing's freshness derives from its real
      historical DRAFT -> ACTIVE publication-transition timestamp, never
      "now at deployment";
    - an ACTIVE listing with no admissible confirmation evidence resolves
      UNKNOWN and is suppressed identically;
    - cross-Organization and DRAFT reconfirmation attempts append zero rows;
    - an exact reconfirmation retry is idempotent and a conflicting
      confirmation-ID reuse fails closed as CONFLICT;
    - STALE never creates a WITHDRAWN/SOLD lifecycle transition -- exactly
      one immutable DRAFT -> ACTIVE record exists for the target listing
      throughout;
    - the SLICE-0051 `draft_max` technical CONFIRMED_MATCH shape (exact
      resolved draft) for the target listing is unchanged by any of this.

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance) and a
pre-built Astro web package (``uv run`` this only after
``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_native_listing_freshness.py
"""

from __future__ import annotations

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
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    FieldEvidenceV3,
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
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.field_resolution import (
    FieldResolutionWriteStatus,
    encode_canonical_decimal_snapshot,
    write_field_resolution,
)
from hullq.persistence.importer import import_research_evidence_bundle
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_freshness import (
    ReconfirmationStatus,
    reconfirm_native_listing,
)
from hullq.persistence.native_listing_lifecycle import (
    fetch_lifecycle_state,
    list_publication_transitions,
    publish_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import ResearchEvidenceBundle
from hullq.search.draft_max_design_bridge import (
    DRAFT_MAX_FIELD_POINTER,
    lookup_draft_max_canonical_value,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_DESIGN_ID = "BD-0052-E2E"
_DESIGN_BASELINE_DRAFT_MAX_M = Decimal("1.60")
_TARGET_LISTING_ID = "NL-0052-E2E-TARGET"
_UNKNOWN_LISTING_ID = "NL-0052-E2E-UNKNOWN"
_DRAFT_LISTING_ID = "NL-0052-E2E-DRAFTONLY"

_AS_OF_ENV = "HULLQ_FRESHNESS_AS_OF_OVERRIDE_ISO"

_WIKIDATA_SOURCE: dict[str, Any] = json.loads(
    (REPO_ROOT / "fixtures" / "sources" / "wikidata_source.json").read_text(encoding="utf-8")
)
_WIKIDATA_SOURCE_ID = _WIKIDATA_SOURCE["source_id"]


def _base_db_url() -> str:
    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(
            f"{HULLQ_TEST_DATABASE_URL_ENV} is not set. Point it at a disposable "
            "local PostgreSQL 18 instance.",
            file=sys.stderr,
        )
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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            time.sleep(0.2)
    return False


def _http_get(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    membership_id: str, account: AccountId, org: MarketplaceOrganization
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _admit_design_field_resolution(conn: Any) -> None:
    """Durably admits `_DESIGN_ID` as a design-level CONFIRMED_MATCH via one
    real imported FieldEvidence + a real `resolved` FieldResolution --
    mirrors `scripts/inspect_first_native_inventory_search.py`, proving
    SLICE-0052 changes no SLICE-0051 technical design/FieldResolution
    semantics."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            ["BM-0052-E2E", "Model BM-0052-E2E", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [
                _DESIGN_ID,
                "BM-0052-E2E",
                "{}",
                "[]",
                json.dumps({"dimensions": {"draft_max_m": float(_DESIGN_BASELINE_DRAFT_MAX_M)}}),
                "[]",
                "[]",
                "{}",
                "1" * 64,
            ],
        )
    conn.commit()

    evidence_id = "EV-0052-E2E-BASELINE"
    evidence = FieldEvidenceV3(
        evidence_id=evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_DESIGN_ID),
        field_pointer=JsonPointer(DRAFT_MAX_FIELD_POINTER),
        source_id=_WIKIDATA_SOURCE_ID,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD,
            value=str(_DESIGN_BASELINE_DRAFT_MAX_M),
            unit="m",
            excerpt=None,
        ),
        normalized_candidate=NormalizedCandidate(
            value=str(_DESIGN_BASELINE_DRAFT_MAX_M),
            unit="m",
            method_id="proof-normalize",
            method_version="1",
        ),
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="inspect_native_listing_freshness",
            version="1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-09-13T00:00:00+00:00",
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
        bundle_id="BUNDLE-0052-E2E",
        bundle_version="1",
        research_target=ResearchTarget(manufacturer=None, model="0052-e2e", first_built=None),
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

    from hullq.domain.provenance import FieldResolution

    resolution = FieldResolution(
        resolution_id="FR-0052-E2E-BASELINE",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_DESIGN_ID),
        field_pointer=JsonPointer(DRAFT_MAX_FIELD_POINTER),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot=encode_canonical_decimal_snapshot(_DESIGN_BASELINE_DRAFT_MAX_M),
        supporting_evidence_ids=frozenset({evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_native_listing_freshness",
            version="1",
        ),
        resolved_at="2026-09-13T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    write_result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        fetch_canonical_value=lookup_draft_max_canonical_value,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert write_result.status is FieldResolutionWriteStatus.CREATED, write_result
    conn.commit()


def _confirmation_row_count(conn: Any, native_listing_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listing_freshness_confirmations "
            "WHERE native_listing_id = %s",
            [native_listing_id],
        )
        (count,) = cur.fetchone()
    return int(count)


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str, as_of_iso: str | None
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0052_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
    if as_of_iso is not None:
        env[_AS_OF_ENV] = as_of_iso
    else:
        env.pop(_AS_OF_ENV, None)
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


def _stop_api(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0052e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0052_e2e_"))
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("NATIVE LISTING FRESHNESS / RECONFIRMATION\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("1. Alembic migrated to current head (includes native_listing_freshness) -> OK\n")

        account = AccountId("ACC-0052-E2E")
        org = _org("ORG-0052-E2E")
        membership = _membership("OM-0052-E2E", account, org)
        other_account = AccountId("ACC-0052-E2E-OTHER")
        other_org = _org("ORG-0052-E2E-OTHER")
        other_membership = _membership("OM-0052-E2E-OTHER", other_account, other_org)

        setup_conn = psycopg.connect(url)
        try:
            _admit_design_field_resolution(setup_conn)
            print("2a. seeded + durably admitted one real design-level FieldResolution -> OK")

            design_ref = BoatDesignRef(_DESIGN_ID)

            # Target listing: design-linked, concrete draft claim 1.40 m
            # (satisfies draft_max=1.6), published through the real
            # accepted lifecycle path -> initial confirmation evidence.
            create_physical_boat(
                setup_conn,
                physical_boat=PhysicalBoat(
                    id=PhysicalBoatId("PB-0052-E2E-TARGET"), boat_design_ref=design_ref
                ),
            )
            create_market_episode(
                setup_conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0052-E2E-TARGET"),
                    physical_boat_id=PhysicalBoatId("PB-0052-E2E-TARGET"),
                ),
            )
            create_native_listing(
                setup_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_TARGET_LISTING_ID),
                    market_episode_id=MarketEpisodeId("ME-0052-E2E-TARGET"),
                ),
            )
            write_native_listing_offer_revision(
                setup_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=NativeListingOfferRevisionId("REV-0052-E2E-TARGET"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )
            write_physical_boat_claim_revision(
                setup_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0052-E2E-TARGET"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    draft=DraftClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")
                    ),
                ),
            )
            publish_result = publish_native_listing(
                setup_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            assert publish_result.status.value == "transitioned", publish_result

            # DRAFT-only listing: never published, used to prove reconfirm
            # rejects a non-ACTIVE listing without appending a row.
            create_physical_boat(
                setup_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0052-E2E-DRAFTONLY"))
            )
            create_market_episode(
                setup_conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0052-E2E-DRAFTONLY"),
                    physical_boat_id=PhysicalBoatId("PB-0052-E2E-DRAFTONLY"),
                ),
            )
            create_native_listing(
                setup_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_DRAFT_LISTING_ID),
                    market_episode_id=MarketEpisodeId("ME-0052-E2E-DRAFTONLY"),
                ),
            )

            # Unknown-evidence listing: forced to ACTIVE directly, bypassing
            # publish_native_listing, so no publication-transition evidence
            # exists at all -- contract §4.1's UNKNOWN/suppressed case.
            create_physical_boat(
                setup_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0052-E2E-UNKNOWN"))
            )
            create_market_episode(
                setup_conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0052-E2E-UNKNOWN"),
                    physical_boat_id=PhysicalBoatId("PB-0052-E2E-UNKNOWN"),
                ),
            )
            create_native_listing(
                setup_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_UNKNOWN_LISTING_ID),
                    market_episode_id=MarketEpisodeId("ME-0052-E2E-UNKNOWN"),
                ),
            )
            write_native_listing_offer_revision(
                setup_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_UNKNOWN_LISTING_ID),
                revision_id=NativeListingOfferRevisionId("REV-0052-E2E-UNKNOWN"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.POA,
                    location_country="FR",
                    broker_description="Migrated from a pre-freshness system with no evidence.",
                ),
            )
            with setup_conn.cursor() as cur:
                cur.execute(
                    "UPDATE native_listings SET lifecycle_state = 'ACTIVE' "
                    "WHERE native_listing_id = %s",
                    [_UNKNOWN_LISTING_ID],
                )
            setup_conn.commit()

            transitions = list_publication_transitions(
                setup_conn, NativeListingId(_TARGET_LISTING_ID)
            )
            assert len(transitions) == 1
            confirmed_at = transitions[0].occurred_at
            print(
                "2b. seeded target (published), DRAFT-only, and unknown-evidence "
                "(ACTIVE, no publication evidence) listings -> OK\n"
            )
        finally:
            setup_conn.close()

        preview_secret_b64 = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        api_port = _free_port()
        web_port = _free_port()

        # FastAPI phase 1: no override -> real current time -> CONFIRMED.
        api_proc, api_log_path = _start_api(
            url=url, api_port=api_port, preview_secret_b64=preview_secret_b64, as_of_iso=None
        )
        api_base = f"http://127.0.0.1:{api_port}"
        api_ready = _wait_for_http(f"{api_base}/api/search/en")
        ok &= api_ready
        print(f"FastAPI serving -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print("---- api.log ----", file=sys.stderr)
            print(api_log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)
            return 1

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = api_base
        web_env["HOST"] = "127.0.0.1"
        web_env["PORT"] = str(web_port)
        with web_log_path.open("wb") as web_log:
            web_proc = subprocess.Popen(
                ["node", "./dist/server/entry.mjs"],
                cwd=WEB_DIR,
                env=web_env,
                stdout=web_log,
                stderr=subprocess.STDOUT,
            )
        web_base = f"http://127.0.0.1:{web_port}"
        web_ready = _wait_for_http(f"{web_base}/en/search")
        ok &= web_ready
        print(f"Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")
        if not web_ready:
            return 1

        # --- Phase 1: CONFIRMED --------------------------------------------------
        listing_status, _, listing_body = _http_get(f"{api_base}/api/listings/{_TARGET_LISTING_ID}")
        listing_json = json.loads(listing_body) if listing_status == 200 else {}
        search_status, _, search_body = _http_get(f"{api_base}/api/search/en?draft_max=1.6")
        search_json = json.loads(search_body) if search_status == 200 else {}
        web_listing_status, _, web_listing_body = _http_get(
            f"{web_base}/listings/{_TARGET_LISTING_ID}"
        )
        web_listing_text = web_listing_body.decode("utf-8")
        unknown_status, _, _ = _http_get(f"{api_base}/api/listings/{_UNKNOWN_LISTING_ID}")

        step_phase1_ok = (
            listing_status == 200
            and listing_json.get("freshness_status") == "CONFIRMED"
            and listing_json.get("last_confirmed_at") is not None
            and search_status == 200
            and search_json.get("confirmed_match_count") == 1
            and search_json["confirmed_matches"][0]["native_listing_id"] == _TARGET_LISTING_ID
            and search_json["confirmed_matches"][0]["resolved_draft_m"] == "1.40"
            and search_json["confirmed_matches"][0]["freshness_status"] == "CONFIRMED"
            and web_listing_status == 200
            and "Confirmed current by the broker" in web_listing_text
            and unknown_status == 404
        )
        ok &= step_phase1_ok
        print(
            "3. publish -> ACTIVE+CONFIRMED, public listing + Search visible, "
            f"unknown-evidence listing suppressed (UNKNOWN) -> {'OK' if step_phase1_ok else 'FAIL'}"
        )

        verify_conn = psycopg.connect(url)
        try:
            unknown_state = fetch_lifecycle_state(verify_conn, NativeListingId(_UNKNOWN_LISTING_ID))
            step_unknown_lifecycle_ok = unknown_state is NativeListingLifecycleState.ACTIVE
        finally:
            verify_conn.close()
        ok &= step_unknown_lifecycle_ok
        print(
            "   unknown-evidence listing's lifecycle remains ACTIVE (no WITHDRAWN/SOLD "
            f"invented) -> {'OK' if step_unknown_lifecycle_ok else 'FAIL'}\n"
        )

        # --- Phase 2: exact +30d -> DUE_FOR_CONFIRMATION --------------------------
        _stop_api(api_proc)
        due_as_of = (confirmed_at + timedelta(days=30)).isoformat()
        api_proc, api_log_path = _start_api(
            url=url, api_port=api_port, preview_secret_b64=preview_secret_b64, as_of_iso=due_as_of
        )
        ok &= _wait_for_http(f"{api_base}/api/search/en")

        listing_status, _, listing_body = _http_get(f"{api_base}/api/listings/{_TARGET_LISTING_ID}")
        listing_json = json.loads(listing_body) if listing_status == 200 else {}
        search_status, _, search_body = _http_get(f"{api_base}/api/search/en?draft_max=1.6")
        search_json = json.loads(search_body) if search_status == 200 else {}
        web_listing_status, _, web_listing_body = _http_get(
            f"{web_base}/listings/{_TARGET_LISTING_ID}"
        )
        web_listing_text = web_listing_body.decode("utf-8")
        web_search_status, _, web_search_body = _http_get(f"{web_base}/en/search?draft_max=1.6")
        web_search_text = web_search_body.decode("utf-8")

        step_phase2_ok = (
            listing_status == 200
            and listing_json.get("freshness_status") == "DUE_FOR_CONFIRMATION"
            and "Awaiting reconfirmation" in web_listing_text
            and "Confirmed current by the broker" not in web_listing_text
            and search_status == 200
            and search_json.get("confirmed_match_count") == 1
            and search_json["confirmed_matches"][0]["freshness_status"] == "DUE_FOR_CONFIRMATION"
            and web_search_status == 200
            and "Reconfirmation due" in web_search_text
        )
        ok &= step_phase2_ok
        print(
            "4. exact +30d -> DUE_FOR_CONFIRMATION, still visible with buyer-visible "
            f"due disclosure on listing + Search -> {'OK' if step_phase2_ok else 'FAIL'}\n"
        )

        # --- Phase 3: exact +37d -> STALE -----------------------------------------
        _stop_api(api_proc)
        stale_as_of = (confirmed_at + timedelta(days=37)).isoformat()
        api_proc, api_log_path = _start_api(
            url=url, api_port=api_port, preview_secret_b64=preview_secret_b64, as_of_iso=stale_as_of
        )
        ok &= _wait_for_http(f"{api_base}/api/search/en")

        listing_status, _, _ = _http_get(f"{api_base}/api/listings/{_TARGET_LISTING_ID}")
        web_listing_status, _, _ = _http_get(f"{web_base}/listings/{_TARGET_LISTING_ID}")
        search_status, _, search_body = _http_get(f"{api_base}/api/search/en?draft_max=1.6")
        search_json = json.loads(search_body) if search_status == 200 else {}

        step_phase3_ok = (
            listing_status == 404
            and web_listing_status == 404
            and search_status == 200
            and search_json.get("confirmed_match_count") == 0
            and search_json.get("insufficient_data_count") == 0
        )
        ok &= step_phase3_ok
        print(
            "5. exact +37d -> STALE, absent from public listing content and Search "
            f"(never counted as insufficient data) -> {'OK' if step_phase3_ok else 'FAIL'}"
        )

        verify_conn = psycopg.connect(url)
        try:
            stale_lifecycle_state = fetch_lifecycle_state(
                verify_conn, NativeListingId(_TARGET_LISTING_ID)
            )
            stale_transitions = list_publication_transitions(
                verify_conn, NativeListingId(_TARGET_LISTING_ID)
            )
        finally:
            verify_conn.close()
        step_stale_lifecycle_ok = (
            stale_lifecycle_state is NativeListingLifecycleState.ACTIVE
            and len(stale_transitions) == 1
        )
        ok &= step_stale_lifecycle_ok
        print(
            "   lifecycle remains ACTIVE; exactly one immutable DRAFT -> ACTIVE record "
            f"exists (no WITHDRAWN/SOLD invented) -> {'OK' if step_stale_lifecycle_ok else 'FAIL'}\n"
        )

        # --- Authorization / idempotency / conflict proofs (direct persistence) ---
        reconfirm_conn = psycopg.connect(url)
        try:
            cross_org_result = reconfirm_native_listing(
                reconfirm_conn,
                confirmation_id=FreshnessConfirmationId("FC-0052-E2E-CROSSORG"),
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            crossorg_row_count = _confirmation_row_count(reconfirm_conn, _TARGET_LISTING_ID)
            reconfirm_conn.commit()  # release the implicit read transaction before the next write
            step_crossorg_ok = (
                cross_org_result.status is ReconfirmationStatus.ORGANIZATION_MISMATCH
                and crossorg_row_count == 0
            )
            ok &= step_crossorg_ok
            print(
                "6. cross-Organization reconfirmation attempt appends zero rows -> "
                f"{'OK' if step_crossorg_ok else 'FAIL'}"
            )

            draft_result = reconfirm_native_listing(
                reconfirm_conn,
                confirmation_id=FreshnessConfirmationId("FC-0052-E2E-DRAFTONLY"),
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_DRAFT_LISTING_ID),
            )
            draft_row_count = _confirmation_row_count(reconfirm_conn, _DRAFT_LISTING_ID)
            reconfirm_conn.commit()  # release the implicit read transaction before the next write
            step_draft_ok = (
                draft_result.status is ReconfirmationStatus.NOT_ACTIVE and draft_row_count == 0
            )
            ok &= step_draft_ok
            print(
                f"   DRAFT listing reconfirmation attempt appends zero rows -> "
                f"{'OK' if step_draft_ok else 'FAIL'}"
            )

            confirmation_id = FreshnessConfirmationId("FC-0052-E2E-RESTORE")
            authorized_result = reconfirm_native_listing(
                reconfirm_conn,
                confirmation_id=confirmation_id,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            step_reconfirm_ok = authorized_result.status is ReconfirmationStatus.RECONFIRMED
            ok &= step_reconfirm_ok
            print(
                f"   authorized reconfirmation succeeds -> {'OK' if step_reconfirm_ok else 'FAIL'}"
            )

            retry_result = reconfirm_native_listing(
                reconfirm_conn,
                confirmation_id=confirmation_id,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            step_retry_ok = (
                retry_result.status is ReconfirmationStatus.ALREADY_EXISTS
                and retry_result.occurred_at == authorized_result.occurred_at
            )
            ok &= step_retry_ok
            print(f"   exact retry is idempotent -> {'OK' if step_retry_ok else 'FAIL'}")

            conflict_result = reconfirm_native_listing(
                reconfirm_conn,
                confirmation_id=confirmation_id,
                account_id=other_account,
                candidate_organization=org,
                membership=_membership("OM-0052-E2E-CONFLICT", other_account, org),
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            step_conflict_ok = (
                conflict_result.status is ReconfirmationStatus.CONFLICT
                and _confirmation_row_count(reconfirm_conn, _TARGET_LISTING_ID) == 1
            )
            ok &= step_conflict_ok
            print(
                "   conflicting confirmation-ID reuse fails closed, no second row -> "
                f"{'OK' if step_conflict_ok else 'FAIL'}\n"
            )
        finally:
            reconfirm_conn.close()

        # --- Phase 4: restored CONFIRMED ------------------------------------------
        _stop_api(api_proc)
        api_proc, api_log_path = _start_api(
            url=url, api_port=api_port, preview_secret_b64=preview_secret_b64, as_of_iso=None
        )
        ok &= _wait_for_http(f"{api_base}/api/search/en")

        listing_status, _, listing_body = _http_get(f"{api_base}/api/listings/{_TARGET_LISTING_ID}")
        listing_json = json.loads(listing_body) if listing_status == 200 else {}
        search_status, _, search_body = _http_get(f"{api_base}/api/search/en?draft_max=1.6")
        search_json = json.loads(search_body) if search_status == 200 else {}

        step_phase4_ok = (
            listing_status == 200
            and listing_json.get("freshness_status") == "CONFIRMED"
            and search_status == 200
            and search_json.get("confirmed_match_count") == 1
            and search_json["confirmed_matches"][0]["resolved_draft_m"] == "1.40"
        )
        ok &= step_phase4_ok
        print(
            "7. authorized reconfirmation restores CONFIRMED visibility on listing + "
            f"Search, unchanged SLICE-0051 technical match shape -> "
            f"{'OK' if step_phase4_ok else 'FAIL'}\n"
        )

        print(f"NATIVE LISTING FRESHNESS / RECONFIRMATION RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (api_proc, web_proc):
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
