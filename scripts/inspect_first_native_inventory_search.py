"""SLICE-0051 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed first Requirements -> Native Inventory Search
vertical against a real, disposable PostgreSQL 18 schema and real local HTTP
servers (FastAPI + built Astro/Node SSR), exercising the actual committed
FieldResolution persistence/admission/read path
(docs/SLICE_0051_FIELD_RESOLUTION_BLOCKER_RECONCILIATION_2026-09-12.md) --
no monkeypatching, no fixture-only bypass:

    PostgreSQL 18
    -> durable evidence (hullq.persistence.importer.import_research_evidence_bundle)
    -> durable active FieldResolution (hullq.persistence.field_resolution.write_field_resolution)
    -> canonical BoatDesign/configuration (hullq.search.draft_max_design_bridge)
    -> deterministic Search (hullq.search.configuration_engine, unchanged)
    -> ACTIVE NativeListing -> concrete publisher PhysicalBoat draft
    -> same-PhysicalBoat contradiction guard
    -> FastAPI (/api/search/{locale})
    -> Astro SSR (/{locale}/search)

    1. Alembic from a clean schema through the current head (includes the
       630ac7da649e field_resolution_persistence revision).
    2. Seed two real BoatDesigns:
       - BD-0051-E2E-SHALLOW: baseline 1.85 m (never itself qualified) plus
         a "shallow-keel" NamedVariant whose own 1.30 m override IS durably
         admitted as a `resolved` FieldResolution, backed by real imported
         evidence from the already-accepted Wikidata source fixture
         (`fixtures/sources/wikidata_source.json`, `production_value:
         allowed` clearance) -- proving one genuinely qualified
         design/configuration end to end.
       - BD-0051-E2E-DEEP: baseline 2.10 m, no FieldResolution ever admitted
         for it -- always non-confirming, never design-level compatible.
       Five ACTIVE NativeListings plus one DRAFT (unpublished) listing, each
       with its own publishing Organization and PhysicalBoat claim state:
       a confirmed shallow draft, an omitted draft, a same-PhysicalBoat
       cross-Organization conflict, an unqualified too-deep design, a
       PhysicalBoat with no BoatDesignRef, and an unpublished listing.
    3. Serve FastAPI + the built Astro SSR server.
    4. `/en/search` (base state): 200, noindex, no result evaluation.
    5. `/de/search?draft_max=1.600` -> 308 canonical redirect to
       `/de/search?draft_max=1.6`.
    6. `/en/search?draft_max=1e0` -> 400, localized recovery, no evaluation.
    7. `/it/search?draft_max=1.6` -> 404 (unsupported locale).
    8. `/en/search?draft_max=1.6` -> 200 with exactly one confirmed match
       (NL-0051-E2E-MATCH, resolved draft 1.40 m) linking to its existing
       public `/listings/{id}` page, insufficient-data behavior covering
       both the omitted-draft and the same-PhysicalBoat conflict cases, and
       no leakage of the unqualified-design/no-identity/DRAFT listings as
       matches.
    9. Following the confirmed match's link renders the existing SLICE-0049/
       0050 public listing page.

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance) and a
pre-built Astro web package (``uv run`` this only after
``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_first_native_inventory_search.py
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
from hullq.persistence.native_listing_lifecycle import publish_native_listing
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
    DRAFT_MAX_OVERRIDE_FIELD_POINTER,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_SHALLOW_DESIGN_ID = "BD-0051-E2E-SHALLOW"
_DEEP_DESIGN_ID = "BD-0051-E2E-DEEP"
_SHALLOW_VARIANT_ID = "VAR-0051-E2E-SHALLOW-KEEL"

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
        except urllib.error.URLError, ConnectionError, TimeoutError, OSError:
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


def _insert_boat_design(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    baseline_draft_max_m: float | None,
    named_variants: list[dict[str, Any]] | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"dimensions": {"draft_max_m": baseline_draft_max_m}})
        variants_json = json.dumps(named_variants or [])
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", baseline_json, variants_json, "[]", "{}", "1" * 64],
        )
    conn.commit()


def _admit_shallow_variant_field_resolution(conn: Any) -> None:
    """Durably admit the one genuinely qualified design/configuration this
    proof demonstrates: a `resolved` FieldResolution for the shallow-keel
    NamedVariant's own `draft_max_m` override, backed by real imported
    evidence from the already-accepted Wikidata source record."""
    evidence_id = "EV-0051-E2E-SHALLOW-VARIANT"
    evidence = FieldEvidenceV3(
        evidence_id=evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.NAMED_VARIANT, id=_SHALLOW_VARIANT_ID),
        field_pointer=JsonPointer(DRAFT_MAX_OVERRIDE_FIELD_POINTER),
        source_id=_WIKIDATA_SOURCE_ID,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD, value="1.30", unit="m", excerpt=None
        ),
        normalized_candidate=NormalizedCandidate(
            value="1.30", unit="m", method_id="proof-normalize", method_version="1"
        ),
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="inspect_first_native_inventory_search",
            version="1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-09-12T00:00:00+00:00",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
        claim_semantics=ClaimSemantics.FACTORY_OPTION_VALUE,
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
        bundle_id="BUNDLE-0051-E2E",
        bundle_version="1",
        research_target=ResearchTarget(
            manufacturer=None, model="shallow-keel-variant", first_built=None
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
        resolution_id="FR-0051-E2E-SHALLOW-VARIANT",
        subject=ProvenanceSubject(kind=SubjectKind.NAMED_VARIANT, id=_SHALLOW_VARIANT_ID),
        field_pointer=JsonPointer(DRAFT_MAX_OVERRIDE_FIELD_POINTER),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot=encode_canonical_decimal_snapshot(Decimal("1.30")),
        supporting_evidence_ids=frozenset({evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_first_native_inventory_search",
            version="1",
        ),
        resolved_at="2026-09-12T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    write_result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert write_result.status is FieldResolutionWriteStatus.CREATED, write_result
    conn.commit()

    # Independently verify DRAFT_MAX_FIELD_POINTER (the BoatDesign baseline
    # field meaning) is genuinely NOT admitted for either design: the
    # confirmed match below must come from the NamedVariant's own override
    # qualification, never a design-wide baseline shortcut.
    from hullq.persistence.field_resolution import fetch_current_field_resolution

    assert (
        fetch_current_field_resolution(
            conn, SubjectKind.BOAT_DESIGN, _SHALLOW_DESIGN_ID, DRAFT_MAX_FIELD_POINTER
        )
        is None
    )
    assert (
        fetch_current_field_resolution(
            conn, SubjectKind.BOAT_DESIGN, _DEEP_DESIGN_ID, DRAFT_MAX_FIELD_POINTER
        )
        is None
    )
    conn.commit()  # leave conn IDLE before the next write requires it


def _make_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_ref: BoatDesignRef | None,
    draft: DraftClaim | None,
    publish: bool = True,
    reuse_physical_boat: bool = False,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(f"OM-{listing_id}", account, org)

    if not reuse_physical_boat:
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(physical_boat_id), boat_design_ref=boat_design_ref
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
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
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
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=draft,
        ),
    )
    if publish:
        result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert result.status.value == "transitioned", result
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
    schema_name = f"hullq_s0051e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0051_e2e_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("FIRST REQUIREMENTS -> NATIVE INVENTORY SEARCH\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("1. Alembic migrated to current head (includes field_resolution_persistence) -> OK\n")

        conn = psycopg.connect(url)
        try:
            _insert_boat_design(
                conn,
                _SHALLOW_DESIGN_ID,
                "BM-0051-E2E-SHALLOW",
                baseline_draft_max_m=1.85,
                named_variants=[
                    {
                        "id": _SHALLOW_VARIANT_ID,
                        "overrides": {"dimensions": {"draft_max_m": 1.30}},
                    }
                ],
            )
            _insert_boat_design(
                conn, _DEEP_DESIGN_ID, "BM-0051-E2E-DEEP", baseline_draft_max_m=2.10
            )
            _admit_shallow_variant_field_resolution(conn)
            print(
                "2a. seeded 2 BoatDesigns; durably admitted one real FieldResolution "
                "(evidence -> resolved snapshot) for the shallow-keel NamedVariant's own "
                "draft_max_m override -> OK"
            )

            shallow_ref = BoatDesignRef(_SHALLOW_DESIGN_ID)
            deep_ref = BoatDesignRef(_DEEP_DESIGN_ID)

            _make_listing(
                conn,
                listing_id="NL-0051-E2E-MATCH",
                physical_boat_id="PB-0051-E2E-MATCH",
                market_episode_id="ME-0051-E2E-MATCH",
                boat_design_ref=shallow_ref,
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")
                ),
            )
            _make_listing(
                conn,
                listing_id="NL-0051-E2E-OMITTED",
                physical_boat_id="PB-0051-E2E-OMITTED",
                market_episode_id="ME-0051-E2E-OMITTED",
                boat_design_ref=shallow_ref,
                draft=None,
            )

            # Same-PhysicalBoat cross-Organization conflict: the publisher's
            # own claim (1.40 m) would otherwise confirm, but a different
            # Organization's current claim for the SAME PhysicalBoatId
            # disagrees (1.90 m) -- must resolve to INSUFFICIENT_DATA, never
            # a confirmed match.
            _make_listing(
                conn,
                listing_id="NL-0051-E2E-CONFLICT",
                physical_boat_id="PB-0051-E2E-CONFLICT",
                market_episode_id="ME-0051-E2E-CONFLICT",
                boat_design_ref=shallow_ref,
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")
                ),
            )
            other_account = AccountId("ACC-0051-E2E-CONFLICT-OTHER")
            other_org = _org("ORG-0051-E2E-CONFLICT-OTHER")
            other_membership = _membership("OM-0051-E2E-CONFLICT-OTHER", other_account, other_org)
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0051-E2E-CONFLICT-OTHER"),
                    physical_boat_id=PhysicalBoatId("PB-0051-E2E-CONFLICT"),
                ),
            )
            create_native_listing(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                listing=NativeListing(
                    id=NativeListingId("NL-0051-E2E-CONFLICT-OTHER"),
                    market_episode_id=MarketEpisodeId("ME-0051-E2E-CONFLICT-OTHER"),
                ),
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                native_listing_id=NativeListingId("NL-0051-E2E-CONFLICT-OTHER"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0051-E2E-CONFLICT-OTHER"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    draft=DraftClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.90")
                    ),
                ),
            )

            _make_listing(
                conn,
                listing_id="NL-0051-E2E-DEEP",
                physical_boat_id="PB-0051-E2E-DEEP",
                market_episode_id="ME-0051-E2E-DEEP",
                boat_design_ref=deep_ref,
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.00")
                ),
            )
            _make_listing(
                conn,
                listing_id="NL-0051-E2E-NOIDENTITY",
                physical_boat_id="PB-0051-E2E-NOIDENTITY",
                market_episode_id="ME-0051-E2E-NOIDENTITY",
                boat_design_ref=None,
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.00")
                ),
            )
            _make_listing(
                conn,
                listing_id="NL-0051-E2E-DRAFTLISTING",
                physical_boat_id="PB-0051-E2E-DRAFTLISTING",
                market_episode_id="ME-0051-E2E-DRAFTLISTING",
                boat_design_ref=shallow_ref,
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.00")
                ),
                publish=False,
            )
            print(
                "2b. seeded 5 ACTIVE listings (match/omitted/conflict/unqualified-deep/"
                "no-identity) + 1 DRAFT (unpublished) listing -> OK\n"
            )
        finally:
            conn.close()

        api_port = _free_port()
        web_port = _free_port()
        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="

        with api_log_path.open("wb") as api_log:
            api_proc = subprocess.Popen(
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
                env=api_env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
            )

        api_base = f"http://127.0.0.1:{api_port}"
        api_ready = _wait_for_http(f"{api_base}/api/search/en")
        ok &= api_ready
        print(f"FastAPI serving -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print("---- api.log ----", file=sys.stderr)
            print(api_log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)

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

        if not ok:
            print("FIRST REQUIREMENTS -> NATIVE INVENTORY SEARCH RESULT -> FAIL")
            return 1

        # 4. Base state: 200, noindex, no result evaluation.
        base_status, base_headers, base_body = _http_get(f"{web_base}/en/search")
        base_headers_lower = {k.lower(): v for k, v in base_headers.items()}
        base_text = base_body.decode("utf-8")
        step4_ok = (
            base_status == 200
            and base_headers_lower.get("x-robots-tag") == "noindex"
            and "NL-0051-E2E-MATCH" not in base_text
        )
        ok &= step4_ok
        print(
            f"4. base /en/search: 200, noindex, no result evaluation -> {'OK' if step4_ok else 'FAIL'}"
        )

        # 5. Non-canonical numeral redirects 308 to the exact canonical URL.
        # urllib follows redirects by default, so a manual opener is required
        # to observe the real 308 status/Location rather than the final hop.
        req = urllib.request.Request(f"{web_base}/de/search?draft_max=1.600")

        class _NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args: Any, **kwargs: Any) -> None:
                return None

        no_redirect_opener = urllib.request.build_opener(_NoRedirect)
        try:
            resp = no_redirect_opener.open(req, timeout=10)
            manual_status, manual_headers = resp.status, dict(resp.headers)
        except urllib.error.HTTPError as exc:
            manual_status, manual_headers = exc.code, dict(exc.headers or {})
        manual_headers_lower = {k.lower(): v for k, v in manual_headers.items()}
        step5_ok = (
            manual_status == 308
            and manual_headers_lower.get("location") == "/de/search?draft_max=1.6"
        )
        ok &= step5_ok
        print(
            f"5. /de/search?draft_max=1.600 -> 308 /de/search?draft_max=1.6 -> "
            f"{'OK' if step5_ok else 'FAIL'}"
        )

        # 6. Invalid lexical spelling -> 400, no evaluation.
        invalid_status, _, invalid_body = _http_get(f"{web_base}/en/search?draft_max=1e0")
        step6_ok = invalid_status == 400 and "NL-0051-E2E-MATCH" not in invalid_body.decode("utf-8")
        ok &= step6_ok
        print(
            f"6. /en/search?draft_max=1e0 -> 400, no evaluation -> {'OK' if step6_ok else 'FAIL'}"
        )

        # 7. Unsupported locale -> 404.
        unsupported_status, _, _ = _http_get(f"{web_base}/it/search?draft_max=1.6")
        step7_ok = unsupported_status == 404
        ok &= step7_ok
        print(f"7. /it/search -> 404 -> {'OK' if step7_ok else 'FAIL'}")

        # 8. Real confirmed match (via the admitted NamedVariant
        # FieldResolution) + real insufficient-data behavior (omitted +
        # cross-Organization conflict) + unqualified-design/no-identity/
        # DRAFT listings never leak.
        result_status, result_headers, result_body = _http_get(
            f"{web_base}/en/search?draft_max=1.6"
        )
        result_headers_lower = {k.lower(): v for k, v in result_headers.items()}
        result_text = result_body.decode("utf-8")
        step8_ok = (
            result_status == 200
            and result_headers_lower.get("x-robots-tag") == "noindex"
            and "/listings/NL-0051-E2E-MATCH" in result_text
            and "1.40" in result_text
            and "NL-0051-E2E-CONFLICT" not in result_text
            and "NL-0051-E2E-DEEP" not in result_text
            and "NL-0051-E2E-NOIDENTITY" not in result_text
            and "NL-0051-E2E-DRAFTLISTING" not in result_text
        )
        ok &= step8_ok
        print(
            f"8. /en/search?draft_max=1.6 -> confirmed match NL-0051-E2E-MATCH (1.40 m via the "
            f"admitted NamedVariant FieldResolution); omitted + conflict listings correctly "
            f"insufficient; unqualified-deep/no-identity/DRAFT listings never leak -> "
            f"{'OK' if step8_ok else 'FAIL'}"
        )

        # 9. Following the confirmed match's link renders the existing public listing page.
        listing_status, _, listing_body = _http_get(f"{web_base}/listings/NL-0051-E2E-MATCH")
        step9_ok = listing_status == 200 and b"Beneteau" in listing_body
        ok &= step9_ok
        print(
            f"9. confirmed match links to the existing public listing page -> "
            f"{'OK' if step9_ok else 'FAIL'}\n"
        )

        print(f"FIRST REQUIREMENTS -> NATIVE INVENTORY SEARCH RESULT -> {'PASS' if ok else 'FAIL'}")
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
