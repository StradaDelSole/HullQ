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

SLICE-0056 extends the same real PostgreSQL + FastAPI + built-Astro-SSR
proof to the SLICE-0055 `keel_configuration` criterion, closing the browser/
API contract gap the slice exists to fix: a third BoatDesign
(BD-0056-E2E-KEEL) admits both `draft_max_m` and `keel_type` FieldResolutions
directly on its baseline (mirroring `tests/persistence/
test_inventory_search_keel_api.py`'s fixture, deliberately simpler than the
SHALLOW/DEEP two-design NamedVariant-override setup above -- a keel-only or
mixed query needs both criteria resolved on the *same* evaluated
configuration to produce one design-level confirmed match), backing one
ACTIVE listing (NL-0056-E2E-KEEL) with its own concrete `draft`/
`keel_configuration` PhysicalBoat claims:

   10. `/en/search?keel_configuration=FIN` -> 200, keel-only active
       requirement rendered, NL-0056-E2E-KEEL confirmed with its concrete
       FIN evidence visible, the unrelated deep/shallow-draft-only listings
       from steps 1-9 never leak in as keel matches.
   11. `/en/search?draft_max=1.6&keel_configuration=FIN` -> 200, both active
       requirements rendered, both concrete criterion values (1.40 m and
       FIN) visible for the one mixed confirmed match.
   12. `/de/search?draft_max=1.600&keel_configuration=FIN` -> 308 canonical
       redirect to `/de/search?draft_max=1.6&keel_configuration=FIN`
       (draft_max canonicalized, keel_configuration preserved verbatim,
       canonical ordering draft_max-then-keel_configuration).
   13. `/en/search?keel_configuration=LONG_KEEL` -> 400 localized recovery
       (unsupported public v0.1 keel vocabulary), no Search evaluation.
   14. `/en/search?keel_configuration=FIN&draft_max=1.6` (canonical values,
       reversed parameter *order*) -> 308 canonical redirect to
       `/en/search?draft_max=1.6&keel_configuration=FIN` -- independent
       review Finding 2: order-only non-canonicity, distinct from step 12's
       numeral non-canonicity.

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
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

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
    KeelConfiguration,
    KeelConfigurationClaim,
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
    lookup_draft_max_canonical_value,
)
from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_SHALLOW_DESIGN_ID = "BD-0051-E2E-SHALLOW"
_DEEP_DESIGN_ID = "BD-0051-E2E-DEEP"
_SHALLOW_VARIANT_ID = "VAR-0051-E2E-SHALLOW-KEEL"

# SLICE-0056: a dedicated third design/listing for the keel-only/mixed
# browser proof -- see this module's docstring for why it is deliberately
# simpler than the SHALLOW/DEEP NamedVariant-override setup above.
_KEEL_DESIGN_ID = "BD-0056-E2E-KEEL"
_KEEL_LISTING_ID = "NL-0056-E2E-KEEL"

# SLICE-0057: a fourth design/listing (TWIN_KEEL, same 1.30 m baseline draft
# as _KEEL_DESIGN_ID's FIN keel) so the sensitivity proof can exercise a
# genuine same-total/different-membership `keel_configuration` swap:
# _KEEL_DESIGN_ID's own resolved keel_type (fin) is a confirmed mismatch
# against a TWIN_KEEL query, and this design's own resolved keel_type (twin)
# is a confirmed mismatch against a FIN query -- independent review Finding 4
# (2026-09-19): this repository's design/configuration bridge always builds
# an incomplete configuration space
# (hullq.search.boat_design_field_bridge.build_boat_design_configuration_set
# `configuration_space_complete=False`), so a resolved-but-different keel
# value lands in INSUFFICIENT_DATA, never design-level CONFIRMED_NON_MATCH
# (hullq.search.configuration_engine.evaluate_design_configuration_set only
# returns CONFIRMED_NON_MATCH when the configuration space is complete).
# Either way, neither design is ever a confirmed match for the other's own
# keel value, so changing keel_configuration from FIN to TWIN_KEEL still
# swaps which single listing is confirmed rather than merely adding/removing
# one from a shared pool (contract §8/§16 point 5) -- see step 15 below for
# the exact insufficient-data counts this produces.
_TWIN_DESIGN_ID = "BD-0057-E2E-TWIN"
_TWIN_LISTING_ID = "NL-0057-E2E-TWIN"

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


def _http_post_json(url: str, payload: dict[str, Any]) -> tuple[int, dict[str, str], bytes]:
    """SLICE-0057: POST *payload* as JSON, mirroring `_http_get`'s manual
    status/header/body capture (used against FastAPI's
    `POST /api/{locale}/search/sensitivity` JSON contract)."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _http_post_form(
    url: str, fields: dict[str, str] | list[tuple[str, str]]
) -> tuple[int, dict[str, str], bytes]:
    """SLICE-0057: POST *fields* as an ordinary
    `application/x-www-form-urlencoded` browser form submission, mirroring
    the exact transport the built Astro `/{locale}/search/sensitivity` page
    receives from `SearchPageBody.astro`'s native `<form method="post">`.

    *fields* accepts a `list[tuple[str, str]]` (in addition to the ordinary
    `dict[str, str]`) so a caller can construct a raw form body with a
    deliberately duplicated field name -- `urlencode` preserves duplicate
    keys from a list of pairs, unlike a `dict` -- for independent review
    Finding 5's tampered-POST proof (step 25 below).

    Sends an explicit same-origin `Origin` header: Astro's built-in
    cross-site POST-form protection (enabled by default for server-rendered
    pages) rejects a state-changing form POST whose `Origin` does not match
    the request's own host -- exactly what a real browser's own same-origin
    form submission sends, and exactly what this deterministic HTTP client
    must reproduce to observe genuine page behavior rather than a false
    CSRF rejection.
    """
    origin_parts = urlsplit(url)
    data = urlencode(fields).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    request.add_header("Origin", f"{origin_parts.scheme}://{origin_parts.netloc}")
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
    baseline_keel_type: str | None = None,
    named_variants: list[dict[str, Any]] | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline: dict[str, Any] = {"dimensions": {"draft_max_m": baseline_draft_max_m}}
        if baseline_keel_type is not None:
            # SLICE-0056: `write_field_resolution`'s Finding-7 canonical-
            # consistency enforcement (`lookup_keel_canonical_value` ->
            # `hullq.search.boat_design_field_bridge.
            # lookup_boat_design_baseline_snapshot`) reads this raw baseline
            # JSONB column directly -- a keel FieldResolution can only be
            # admitted `resolved` if this durable value already agrees with
            # it (mirrors `dimensions.draft_max_m` above).
            baseline["appendages"] = {"keel_type": baseline_keel_type}
        baseline_json = json.dumps(baseline)
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
        fetch_canonical_value=lookup_draft_max_canonical_value,
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


def _admit_keel_design_field_resolutions(conn: Any) -> None:
    """SLICE-0056: durably admit `draft_max_m` and `keel_type` `resolved`
    FieldResolutions on the SAME `BD-0056-E2E-KEEL` baseline configuration --
    unlike `_admit_shallow_variant_field_resolution` above, both criteria
    must resolve on one evaluated configuration to produce a single
    design-level confirmed match for a mixed query (this module's docstring
    explains why the SHALLOW/DEEP design pair above cannot be reused for
    this). Mirrors `tests/persistence/test_inventory_search_keel_api.py`'s
    fixture end to end through the real accepted write path."""
    draft_evidence_id = "EV-0056-E2E-KEEL-DRAFT"
    draft_evidence = FieldEvidenceV3(
        evidence_id=draft_evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_KEEL_DESIGN_ID),
        field_pointer=JsonPointer(DRAFT_MAX_FIELD_POINTER),
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
        observed_at="2026-09-18T00:00:00+00:00",
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
    keel_evidence_id = "EV-0056-E2E-KEEL-TYPE"
    keel_evidence = FieldEvidenceV3(
        evidence_id=keel_evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_KEEL_DESIGN_ID),
        field_pointer=JsonPointer(KEEL_TYPE_FIELD_POINTER),
        source_id=_WIKIDATA_SOURCE_ID,
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
            identifier="inspect_first_native_inventory_search",
            version="1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-09-18T00:00:00+00:00",
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
        bundle_id="BUNDLE-0056-E2E",
        bundle_version="1",
        research_target=ResearchTarget(manufacturer=None, model="keel-design", first_built=None),
        research_job_id=None,
        activity_id=None,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=(draft_evidence, keel_evidence),
        reference_crosschecks=(),
    )
    import_result = import_research_evidence_bundle(conn, bundle)
    assert import_result.status.value in ("imported", "already_imported"), import_result
    conn.commit()

    draft_resolution = FieldResolution(
        resolution_id="FR-0056-E2E-KEEL-DRAFT",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_KEEL_DESIGN_ID),
        field_pointer=JsonPointer(DRAFT_MAX_FIELD_POINTER),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot=encode_canonical_decimal_snapshot(Decimal("1.30")),
        supporting_evidence_ids=frozenset({draft_evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({draft_evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_first_native_inventory_search",
            version="1",
        ),
        resolved_at="2026-09-18T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    draft_write_result = write_field_resolution(
        conn,
        resolution=draft_resolution,
        expected_current_resolution_id=None,
        fetch_canonical_value=lookup_draft_max_canonical_value,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert draft_write_result.status is FieldResolutionWriteStatus.CREATED, draft_write_result
    conn.commit()

    keel_resolution = FieldResolution(
        resolution_id="FR-0056-E2E-KEEL-TYPE",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_KEEL_DESIGN_ID),
        field_pointer=JsonPointer(KEEL_TYPE_FIELD_POINTER),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot="fin",
        supporting_evidence_ids=frozenset({keel_evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({keel_evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_first_native_inventory_search",
            version="1",
        ),
        resolved_at="2026-09-18T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    keel_write_result = write_field_resolution(
        conn,
        resolution=keel_resolution,
        expected_current_resolution_id=None,
        fetch_canonical_value=lookup_keel_canonical_value,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert keel_write_result.status is FieldResolutionWriteStatus.CREATED, keel_write_result
    conn.commit()


def _admit_twin_design_field_resolutions(conn: Any) -> None:
    """SLICE-0057: durably admit `draft_max_m`/`keel_type` `resolved`
    FieldResolutions on `BD-0057-E2E-TWIN`'s baseline -- the same 1.30 m
    draft as `_admit_keel_design_field_resolutions`'s FIN design, but
    `keel_type="twin"` (`TWIN_KEEL`). Mirrors that function exactly except
    for the keel value/identifiers; see this module's docstring and the
    `_TWIN_DESIGN_ID`/`_TWIN_LISTING_ID` comment for why a fourth design is
    needed (the sensitivity same-total/different-membership proof)."""
    draft_evidence_id = "EV-0057-E2E-TWIN-DRAFT"
    draft_evidence = FieldEvidenceV3(
        evidence_id=draft_evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_TWIN_DESIGN_ID),
        field_pointer=JsonPointer(DRAFT_MAX_FIELD_POINTER),
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
        observed_at="2026-09-18T00:00:00+00:00",
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
    keel_evidence_id = "EV-0057-E2E-TWIN-TYPE"
    keel_evidence = FieldEvidenceV3(
        evidence_id=keel_evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_TWIN_DESIGN_ID),
        field_pointer=JsonPointer(KEEL_TYPE_FIELD_POINTER),
        source_id=_WIKIDATA_SOURCE_ID,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD, value="twin", unit=None, excerpt=None
        ),
        normalized_candidate=NormalizedCandidate(
            value="twin", unit=None, method_id="proof-normalize", method_version="1"
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
        observed_at="2026-09-18T00:00:00+00:00",
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
        bundle_id="BUNDLE-0057-E2E",
        bundle_version="1",
        research_target=ResearchTarget(
            manufacturer=None, model="twin-keel-design", first_built=None
        ),
        research_job_id=None,
        activity_id=None,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=(draft_evidence, keel_evidence),
        reference_crosschecks=(),
    )
    import_result = import_research_evidence_bundle(conn, bundle)
    assert import_result.status.value in ("imported", "already_imported"), import_result
    conn.commit()

    draft_resolution = FieldResolution(
        resolution_id="FR-0057-E2E-TWIN-DRAFT",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_TWIN_DESIGN_ID),
        field_pointer=JsonPointer(DRAFT_MAX_FIELD_POINTER),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot=encode_canonical_decimal_snapshot(Decimal("1.30")),
        supporting_evidence_ids=frozenset({draft_evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({draft_evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_first_native_inventory_search",
            version="1",
        ),
        resolved_at="2026-09-18T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    draft_write_result = write_field_resolution(
        conn,
        resolution=draft_resolution,
        expected_current_resolution_id=None,
        fetch_canonical_value=lookup_draft_max_canonical_value,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert draft_write_result.status is FieldResolutionWriteStatus.CREATED, draft_write_result
    conn.commit()

    keel_resolution = FieldResolution(
        resolution_id="FR-0057-E2E-TWIN-TYPE",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=_TWIN_DESIGN_ID),
        field_pointer=JsonPointer(KEEL_TYPE_FIELD_POINTER),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot="twin",
        supporting_evidence_ids=frozenset({keel_evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({keel_evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="proof-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="inspect_first_native_inventory_search",
            version="1",
        ),
        resolved_at="2026-09-18T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    keel_write_result = write_field_resolution(
        conn,
        resolution=keel_resolution,
        expected_current_resolution_id=None,
        fetch_canonical_value=lookup_keel_canonical_value,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert keel_write_result.status is FieldResolutionWriteStatus.CREATED, keel_write_result
    conn.commit()


def _make_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_ref: BoatDesignRef | None,
    draft: DraftClaim | None,
    keel: KeelConfigurationClaim | None = None,
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
            keel_configuration=keel,
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

            # SLICE-0056: a dedicated design/listing for the keel-only/mixed
            # browser proof (this module's docstring explains why it is
            # separate from the SHALLOW/DEEP pair above).
            _insert_boat_design(
                conn,
                _KEEL_DESIGN_ID,
                "BM-0056-E2E-KEEL",
                baseline_draft_max_m=1.30,
                baseline_keel_type="fin",
            )
            _admit_keel_design_field_resolutions(conn)
            _make_listing(
                conn,
                listing_id=_KEEL_LISTING_ID,
                physical_boat_id="PB-0056-E2E-KEEL",
                market_episode_id="ME-0056-E2E-KEEL",
                boat_design_ref=BoatDesignRef(_KEEL_DESIGN_ID),
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")
                ),
                keel=KeelConfigurationClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
                ),
            )
            print(
                "2c. seeded 1 ACTIVE keel/draft-qualified BoatDesign + listing "
                f"({_KEEL_LISTING_ID}, FIN keel, 1.40 m draft) -> OK\n"
            )

            # SLICE-0057: a fourth design/listing (TWIN_KEEL, same 1.30 m
            # baseline draft) so the sensitivity proof can exercise a real
            # same-total/different-membership keel_configuration swap
            # against _KEEL_LISTING_ID (see _TWIN_DESIGN_ID's comment above).
            _insert_boat_design(
                conn,
                _TWIN_DESIGN_ID,
                "BM-0057-E2E-TWIN",
                baseline_draft_max_m=1.30,
                baseline_keel_type="twin",
            )
            _admit_twin_design_field_resolutions(conn)
            _make_listing(
                conn,
                listing_id=_TWIN_LISTING_ID,
                physical_boat_id="PB-0057-E2E-TWIN",
                market_episode_id="ME-0057-E2E-TWIN",
                boat_design_ref=BoatDesignRef(_TWIN_DESIGN_ID),
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")
                ),
                keel=KeelConfigurationClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.TWIN_KEEL
                ),
            )
            print(
                "2d. seeded 1 ACTIVE keel/draft-qualified BoatDesign + listing "
                f"({_TWIN_LISTING_ID}, TWIN_KEEL keel, 1.40 m draft) -> OK\n"
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

        # 10. SLICE-0056: keel-only Search submitted/rendered through the
        # public SSR surface (contract §H.2) -- keel-only active requirement
        # rendered, the concrete FIN evidence visible, none of the
        # draft-only-scenario listings leak in as keel matches.
        keel_status, keel_headers, keel_body = _http_get(
            f"{web_base}/en/search?keel_configuration=FIN"
        )
        keel_headers_lower = {k.lower(): v for k, v in keel_headers.items()}
        keel_text = keel_body.decode("utf-8")
        step10_ok = (
            keel_status == 200
            and keel_headers_lower.get("x-robots-tag") == "noindex"
            and f"/listings/{_KEEL_LISTING_ID}" in keel_text
            and "Fin keel" in keel_text
            and "NL-0051-E2E-MATCH" not in keel_text
            and "NL-0051-E2E-DEEP" not in keel_text
        )
        ok &= step10_ok
        print(
            f"10. /en/search?keel_configuration=FIN -> keel-only confirmed match "
            f"{_KEEL_LISTING_ID} (concrete FIN evidence visible) -> {'OK' if step10_ok else 'FAIL'}"
        )

        # 11. SLICE-0056: draft+keel Search submitted/rendered through the
        # public SSR surface (contract §H.3/§H.5) -- both active
        # requirements and both concrete criterion values visible for the
        # one mixed confirmed match.
        mixed_status, mixed_headers, mixed_body = _http_get(
            f"{web_base}/en/search?draft_max=1.6&keel_configuration=FIN"
        )
        mixed_headers_lower = {k.lower(): v for k, v in mixed_headers.items()}
        mixed_text = mixed_body.decode("utf-8")
        step11_ok = (
            mixed_status == 200
            and mixed_headers_lower.get("x-robots-tag") == "noindex"
            and f"/listings/{_KEEL_LISTING_ID}" in mixed_text
            and "1.40" in mixed_text
            and "Fin keel" in mixed_text
        )
        ok &= step11_ok
        print(
            f"11. /en/search?draft_max=1.6&keel_configuration=FIN -> mixed confirmed match "
            f"{_KEEL_LISTING_ID} (both concrete 1.40 m + FIN evidence visible) -> "
            f"{'OK' if step11_ok else 'FAIL'}"
        )

        # 12. SLICE-0056: non-canonical mixed request redirects to the exact
        # canonical Location (draft_max canonicalized, keel_configuration
        # preserved, canonical ordering draft_max-then-keel_configuration --
        # contract §H.7).
        mixed_redirect_req = urllib.request.Request(
            f"{web_base}/de/search?draft_max=1.600&keel_configuration=FIN"
        )
        try:
            mixed_redirect_resp = no_redirect_opener.open(mixed_redirect_req, timeout=10)
            mixed_redirect_status = mixed_redirect_resp.status
            mixed_redirect_headers = dict(mixed_redirect_resp.headers)
        except urllib.error.HTTPError as exc:
            mixed_redirect_status = exc.code
            mixed_redirect_headers = dict(exc.headers or {})
        mixed_redirect_headers_lower = {k.lower(): v for k, v in mixed_redirect_headers.items()}
        step12_ok = (
            mixed_redirect_status == 308
            and mixed_redirect_headers_lower.get("location")
            == "/de/search?draft_max=1.6&keel_configuration=FIN"
        )
        ok &= step12_ok
        print(
            f"12. /de/search?draft_max=1.600&keel_configuration=FIN -> 308 "
            f"/de/search?draft_max=1.6&keel_configuration=FIN -> {'OK' if step12_ok else 'FAIL'}"
        )

        # 13. SLICE-0056: unsupported public v0.1 keel vocabulary -> 400
        # localized recovery, no Search evaluation (contract §H.7).
        invalid_keel_status, _, invalid_keel_body = _http_get(
            f"{web_base}/en/search?keel_configuration=LONG_KEEL"
        )
        step13_ok = invalid_keel_status == 400 and _KEEL_LISTING_ID not in invalid_keel_body.decode(
            "utf-8"
        )
        ok &= step13_ok
        print(
            f"13. /en/search?keel_configuration=LONG_KEEL -> 400, no evaluation -> "
            f"{'OK' if step13_ok else 'FAIL'}"
        )

        # 14. SLICE-0056 independent review Finding 2: a semantically valid
        # mixed request whose *parameter order* is reversed (both values
        # already individually canonical) must still 308-redirect to the
        # exact canonical draft_max-then-keel_configuration order rather than
        # remain a second successful 200 identity
        # (docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md,
        # docs/OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md).
        # This exercises order-only non-canonicity, which the pre-existing
        # step 12 (a non-canonical *numeral* in already-canonical key order)
        # does not.
        order_redirect_req = urllib.request.Request(
            f"{web_base}/en/search?keel_configuration=FIN&draft_max=1.6"
        )
        try:
            order_redirect_resp = no_redirect_opener.open(order_redirect_req, timeout=10)
            order_redirect_status = order_redirect_resp.status
            order_redirect_headers = dict(order_redirect_resp.headers)
        except urllib.error.HTTPError as exc:
            order_redirect_status = exc.code
            order_redirect_headers = dict(exc.headers or {})
        order_redirect_headers_lower = {k.lower(): v for k, v in order_redirect_headers.items()}
        step14_ok = (
            order_redirect_status == 308
            and order_redirect_headers_lower.get("location")
            == "/en/search?draft_max=1.6&keel_configuration=FIN"
        )
        ok &= step14_ok
        print(
            f"14. /en/search?keel_configuration=FIN&draft_max=1.6 (reversed canonical order) -> "
            f"308 /en/search?draft_max=1.6&keel_configuration=FIN -> "
            f"{'OK' if step14_ok else 'FAIL'}\n"
        )

        print(
            f"FIRST REQUIREMENTS -> NATIVE INVENTORY SEARCH RESULT -> {'PASS' if ok else 'FAIL'}\n"
        )

        # ---------------------------------------------------------------
        # SLICE-0057: buyer-requirement-sensitivity real vertical proof
        # (contract §16), extending the same retained PostgreSQL 18 ->
        # FastAPI -> built Astro SSR proof above rather than a second
        # script.
        # ---------------------------------------------------------------
        sensitivity_ok = True

        # 15. A buyer-authored keel_configuration replacement (FIN ->
        # TWIN_KEEL) is a genuine same-total/different-membership case:
        # totals are equal (1 and 1) while the confirmed listing identity
        # swaps entirely, proving newly_confirmed_match_count/
        # no_longer_confirmed_match_count are real stable-ID set
        # differences, never max(0, alternative_total - current_total)
        # (contract §8's hard requirement, points 4/5/6). Insufficient-data
        # counts stay identical (5) and separate under either keel value
        # (point 7): the four ACTIVE SHALLOW/DEEP-family listings (keel_type
        # never resolved there at all) PLUS the one design that resolves a
        # *different* keel value than requested -- this repo's design/
        # configuration bridge always builds an incomplete configuration
        # space (`configuration_space_complete=False`,
        # `hullq.search.boat_design_field_bridge.
        # build_boat_design_configuration_set`), so a design-level FALSE
        # alone never yields CONFIRMED_NON_MATCH, only INSUFFICIENT_DATA --
        # a confirmed-different keel value is therefore counted as
        # insufficient evidence for *this* query, exactly like a missing
        # one, never a negative match claim.
        keel_swap_status, _, keel_swap_body = _http_post_json(
            f"{api_base}/api/search/en/sensitivity",
            {
                "current": {"keel_configuration": "FIN"},
                "change": {"criterion": "keel_configuration", "value": "TWIN_KEEL"},
            },
        )
        keel_swap = json.loads(keel_swap_body.decode("utf-8")) if keel_swap_status == 200 else {}
        step15_ok = (
            keel_swap_status == 200
            and keel_swap.get("current_confirmed_match_count") == 1
            and keel_swap.get("alternative_confirmed_match_count") == 1
            and keel_swap.get("newly_confirmed_match_count") == 1
            and keel_swap.get("no_longer_confirmed_match_count") == 1
            and keel_swap.get("current_insufficient_data_count") == 5
            and keel_swap.get("alternative_insufficient_data_count") == 5
            and keel_swap.get("alternative_search_path")
            == "/en/search?keel_configuration=TWIN_KEEL"
        )
        sensitivity_ok &= step15_ok
        print(
            "15. keel_configuration sensitivity FIN -> TWIN_KEEL: same-total "
            "(1/1) different-membership set-difference (newly=1, no_longer=1), "
            f"insufficient-data stays separate (5/5) -> {'OK' if step15_ok else 'FAIL'}"
        )

        # 16. Mixed current requirement (draft_max=1.6 & keel_configuration=
        # FIN, confirmed only by NL-0056-E2E-KEEL): changing draft_max to
        # 1.2 while keel_configuration is preserved exactly removes that
        # confirmed match (its own baseline draft is 1.30 m > 1.2 m) --
        # "mixed Search can change draft while preserving keel exactly".
        draft_change_status, _, draft_change_body = _http_post_json(
            f"{api_base}/api/search/en/sensitivity",
            {
                "current": {"draft_max": "1.6", "keel_configuration": "FIN"},
                "change": {"criterion": "draft_max", "value": "1.2"},
            },
        )
        draft_change = (
            json.loads(draft_change_body.decode("utf-8")) if draft_change_status == 200 else {}
        )
        step16_ok = (
            draft_change_status == 200
            and draft_change.get("current_confirmed_match_count") == 1
            and draft_change.get("alternative_confirmed_match_count") == 0
            and draft_change.get("no_longer_confirmed_match_count") == 1
            and draft_change.get("newly_confirmed_match_count") == 0
            and draft_change.get("alternative_requirement")
            == {"draft_max": "1.2", "keel_configuration": "FIN"}
        )
        sensitivity_ok &= step16_ok
        print(
            "16. mixed sensitivity: draft_max 1.6 -> 1.2 removes the one confirmed "
            "match, keel_configuration=FIN preserved exactly -> "
            f"{'OK' if step16_ok else 'FAIL'}"
        )

        # 17. Same mixed current requirement: changing keel_configuration to
        # TWIN_KEEL while draft_max is preserved exactly swaps the confirmed
        # listing to NL-0057-E2E-TWIN -- "mixed Search can change keel while
        # preserving draft exactly".
        keel_change_status, _, keel_change_body = _http_post_json(
            f"{api_base}/api/search/en/sensitivity",
            {
                "current": {"draft_max": "1.6", "keel_configuration": "FIN"},
                "change": {"criterion": "keel_configuration", "value": "TWIN_KEEL"},
            },
        )
        keel_change = (
            json.loads(keel_change_body.decode("utf-8")) if keel_change_status == 200 else {}
        )
        step17_ok = (
            keel_change_status == 200
            and keel_change.get("current_confirmed_match_count") == 1
            and keel_change.get("alternative_confirmed_match_count") == 1
            and keel_change.get("alternative_requirement")
            == {"draft_max": "1.6", "keel_configuration": "TWIN_KEEL"}
            and keel_change.get("alternative_search_path")
            == "/en/search?draft_max=1.6&keel_configuration=TWIN_KEEL"
        )
        sensitivity_ok &= step17_ok
        print(
            "17. mixed sensitivity: keel_configuration FIN -> TWIN_KEEL swaps the "
            "confirmed match, draft_max=1.6 preserved exactly, exact canonical "
            f"alternative_search_path -> {'OK' if step17_ok else 'FAIL'}"
        )

        # 18. Same-value proposal ("FIN" again) is a deterministic zero
        # delta -- never an error, never reworded as advice.
        same_value_status, _, same_value_body = _http_post_json(
            f"{api_base}/api/search/en/sensitivity",
            {
                "current": {"keel_configuration": "FIN"},
                "change": {"criterion": "keel_configuration", "value": "FIN"},
            },
        )
        same_value = json.loads(same_value_body.decode("utf-8")) if same_value_status == 200 else {}
        step18_ok = (
            same_value_status == 200
            and same_value.get("current_confirmed_match_count")
            == same_value.get("alternative_confirmed_match_count")
            and same_value.get("newly_confirmed_match_count") == 0
            and same_value.get("no_longer_confirmed_match_count") == 0
        )
        sensitivity_ok &= step18_ok
        print(
            f"18. same-value proposal -> deterministic zero delta -> {'OK' if step18_ok else 'FAIL'}"
        )

        # 19. The changed criterion must already be active in `current`.
        inactive_status, _, _ = _http_post_json(
            f"{api_base}/api/search/en/sensitivity",
            {
                "current": {"draft_max": "1.6"},
                "change": {"criterion": "keel_configuration", "value": "FIN"},
            },
        )
        step19_ok = inactive_status == 400
        sensitivity_ok &= step19_ok
        print(
            "19. changed criterion absent from current Search -> 400, no "
            f"sensitivity claim -> {'OK' if step19_ok else 'FAIL'}"
        )

        # 20. Malformed proposed draft_max -> 400.
        malformed_draft_status, _, _ = _http_post_json(
            f"{api_base}/api/search/en/sensitivity",
            {"current": {"draft_max": "1.6"}, "change": {"criterion": "draft_max", "value": "1e0"}},
        )
        step20_ok = malformed_draft_status == 400
        sensitivity_ok &= step20_ok
        print(f"20. malformed proposed draft_max -> 400 -> {'OK' if step20_ok else 'FAIL'}")

        # 21. Unsupported/tampered proposed keel_configuration -> 400.
        unsupported_keel_status, _, _ = _http_post_json(
            f"{api_base}/api/search/en/sensitivity",
            {
                "current": {"keel_configuration": "FIN"},
                "change": {"criterion": "keel_configuration", "value": "LONG_KEEL"},
            },
        )
        step21_ok = unsupported_keel_status == 400
        sensitivity_ok &= step21_ok
        print(
            "21. unsupported/tampered proposed keel_configuration -> 400 -> "
            f"{'OK' if step21_ok else 'FAIL'}"
        )

        # 22. Posting through the built locale Astro sensitivity page (not
        # the bare FastAPI JSON route) renders the factual delta and the
        # exact canonical alternative Search link -- the same FIN ->
        # TWIN_KEEL swap as step 15, this time via the real native browser
        # POST target `SearchPageBody.astro`'s sensitivity form submits to.
        web_sensitivity_status, web_sensitivity_headers, web_sensitivity_body = _http_post_form(
            f"{web_base}/en/search/sensitivity",
            {
                "current_keel_configuration": "FIN",
                "changed_criterion": "keel_configuration",
                "changed_value": "TWIN_KEEL",
            },
        )
        web_sensitivity_headers_lower = {k.lower(): v for k, v in web_sensitivity_headers.items()}
        web_sensitivity_text = web_sensitivity_body.decode("utf-8")
        step22_ok = (
            web_sensitivity_status == 200
            and web_sensitivity_headers_lower.get("x-robots-tag") == "noindex"
            and 'href="/en/search?keel_configuration=TWIN_KEEL"' in web_sensitivity_text
            and 'aria-label="newly confirmed"' in web_sensitivity_text
            and 'aria-label="no longer confirmed"' in web_sensitivity_text
            and "recommended" not in web_sensitivity_text.lower()
            and "optimal" not in web_sensitivity_text.lower()
        )
        sensitivity_ok &= step22_ok
        if not step22_ok:
            print(
                f"DEBUG step22 status={web_sensitivity_status} "
                f"headers={web_sensitivity_headers_lower} body={web_sensitivity_text[:2000]!r}",
                file=sys.stderr,
            )
        print(
            "22. built Astro /en/search/sensitivity POST renders the factual "
            "delta and the exact canonical alternative Search link, noindex, "
            f"no recommendation language -> {'OK' if step22_ok else 'FAIL'}"
        )

        # 23. Ordinary Direct Search behavior is unchanged by the sensitivity
        # feature and its extra fixtures: the exact keel-only query from step
        # 10 still confirms exactly NL-0056-E2E-KEEL (the new TWIN_KEEL
        # design/listing never leaks in as a FIN match).
        regression_status, _, regression_body = _http_get(
            f"{web_base}/en/search?keel_configuration=FIN"
        )
        regression_text = regression_body.decode("utf-8")
        step23_ok = (
            regression_status == 200
            and f"/listings/{_KEEL_LISTING_ID}" in regression_text
            and _TWIN_LISTING_ID not in regression_text
        )
        sensitivity_ok &= step23_ok
        print(
            "23. ordinary /en/search?keel_configuration=FIN behavior is unchanged "
            f"by the sensitivity feature -> {'OK' if step23_ok else 'FAIL'}"
        )

        # 24. A direct GET to the POST-only sensitivity page never
        # manufactures a sensitivity result (contract §13).
        get_sensitivity_status, _, get_sensitivity_body = _http_get(
            f"{web_base}/en/search/sensitivity"
        )
        get_sensitivity_text = get_sensitivity_body.decode("utf-8")
        step24_ok = (
            get_sensitivity_status >= 400
            and "newly confirmed" not in get_sensitivity_text
            and "TWIN_KEEL" not in get_sensitivity_text
        )
        sensitivity_ok &= step24_ok
        print(
            "24. direct GET to /en/search/sensitivity never manufactures a "
            f"sensitivity result -> {'OK' if step24_ok else 'FAIL'}"
        )

        # 25. Independent review Finding 5 (2026-09-19): a real, browser-
        # faithful tampered POST -- a duplicated `current_draft_max` field,
        # ambiguous as to which value is the buyer's real current requirement
        # -- through the built Astro sensitivity page must fail closed to
        # the bounded invalid state, never a fabricated sensitivity result.
        tampered_status, _, tampered_body = _http_post_form(
            f"{web_base}/en/search/sensitivity",
            [
                ("current_draft_max", "1.6"),
                ("current_draft_max", "1.2"),
                ("changed_criterion", "draft_max"),
                ("changed_value", "1.7"),
            ],
        )
        tampered_text = tampered_body.decode("utf-8")
        step25_ok = (
            tampered_status == 400
            and "newly confirmed" not in tampered_text
            and "no longer confirmed" not in tampered_text
        )
        sensitivity_ok &= step25_ok
        print(
            "25. tampered POST (duplicated current_draft_max) to "
            "/en/search/sensitivity fails closed to the bounded invalid "
            f"state, never a fabricated result -> {'OK' if step25_ok else 'FAIL'}\n"
        )

        ok &= sensitivity_ok
        print(f"BUYER REQUIREMENT SENSITIVITY RESULT -> {'PASS' if sensitivity_ok else 'FAIL'}")
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
