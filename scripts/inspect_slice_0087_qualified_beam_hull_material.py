"""SLICE-0087 owner-visible end-to-end proof -- real PostgreSQL 18 + real
HTTP + real **built** Astro SSR.

Mirrors `scripts/inspect_slice_0086_technical_search.py`'s identical
disposable-schema/real-HTTP/real-browser-session/real-FieldResolution-
admission conventions, scoped to exactly SLICE-0087's own two new facets
(`beam_min`/`beam_max` as one dimension, `hull_material`) rather than
re-proving SLICE-0051/0055/0084/0085/0086's own already-executed base
behavior.

Demonstrates, end to end:

    1. private broker Search-fit SSR (listing still DRAFT): both new facets
       combined render CONFIRMED_MATCH on the real built editor page, with
       the real per-criterion design/concrete evidence text actually present
    2. broker claim save -> real HTTP write of the beam/hull_material claim
       fields, then a real re-GET of the built editor page proves the saved
       values are genuinely reopened from durable state, not merely echoed
       back from the POST response
    3. a real publish transition takes the listing DRAFT -> ACTIVE
    4. public buyer Search SSR (`/en/search`), now against the published
       listing: each new facet alone, and both combined, confirm the
       identical match with the real rendered observed concrete value, plus
       the separate design/configuration-level evidence FastAPI returns
    5. the same combined scenario repeated against every one of the five
       accepted public Search locales, each with its own real canonical
       `<link>` href and its own real localized observed-evidence text
    4c. real built-SSR positive matches for the three remaining material
        options (STEEL/ALUMINUM/WOOD), each absent from every other
        material's own result (review amendment Finding A)
    4d. a real built-SSR request mixing a legacy accepted hard criterion
        (`keel_configuration`) with both new facets, confirmed match with
        every criterion's own evidence rendered (review amendment Finding A)
    6. negative: a real BoatDesign/listing whose `hull_material` is
       confirmed `wood_composite` (no v0.1 mapping) never produces a false
       confirmed match for a buyer requesting `WOOD`, through the real built
       SSR page (never only the unit-level bridge check)
    7. negative: an unsupported `hull_material=FERROCEMENT` value is a real
       SSR 400; an inverted `beam_min`>`beam_max` range is a real SSR 400; a
       non-canonical key order (`hull_material` before `beam_max`)
       308-redirects to the canonical order
    8. exact finish marker

Review amendment (PR #352 comment 6200576826): Finding A required real
built-SSR positive coverage for all four material options plus a real
mixed legacy+new SSR request (items 4c/4d above, added without a second
harness -- reusing the exact same fixture/session/admission helpers).
Finding B required explicit accessible `<label for>` pairing for the four
new broker claim-editor controls (fixed in `edit.astro`) plus a focused
built-SSR markup assertion proving each `for` resolves to exactly one
control with a distinct label (added to the step-2 reopen check below).

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_slice_0087_qualified_beam_hull_material.py
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

_ORG_ID = "ORG-0087-E2E"
_ACCOUNT_ID = "ACC-0087-E2E"
_EDITING_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"
_LIFECYCLE_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1"

_DESIGN_ID = "BD-0087-E2E"
_MODEL_ID = "BM-0087-E2E"
_LISTING_ID = "NL-0087-MAIN"

# Negative fixture: a design/listing whose hull_material is confirmed
# `wood_composite` (no v0.1 mapping) -- must never falsely match `WOOD`.
_NEG_DESIGN_ID = "BD-0087-NEG"
_NEG_MODEL_ID = "BM-0087-NEG"
_NEG_LISTING_ID = "NL-0087-NEG"
_NEG_ORG_ID = "ORG-0087-NEG"
_NEG_ACCOUNT_ID = "ACC-0087-NEG"

# Review amendment Finding A: one additional confirmed design/listing per
# remaining public hull_material token (GRP_FIBERGLASS is already proven by
# the main fixture above), each its own Organization/account/listing so a
# real built-SSR request for one token can be proven absent from every
# other token's own result. (public token, BoatDesign raw value, locale
# display label).
_MATERIAL_FIXTURES: tuple[tuple[str, str, str], ...] = (
    ("STEEL", "steel", "Steel"),
    ("ALUMINUM", "aluminium", "Aluminum"),
    ("WOOD", "wood", "Wood"),
)


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
    `scripts/inspect_slice_0086_technical_search.py`'s identical
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
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0087_api_", suffix=".log")[1])
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
    beam_m: float | None,
    hull_material: str | None,
    keel_type: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline = json.dumps(
            {
                "dimensions": {"beam_m": beam_m},
                "construction": {"hull_material": hull_material},
                "appendages": {"keel_type": keel_type},
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
    -- mirrors `scripts/inspect_slice_0086_technical_search.py`'s identical
    `_admit_design_field` recipe exactly."""
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
            identifier="inspect_slice_0087_qualified_beam_hull_material",
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
        research_target=ResearchTarget(manufacturer=None, model="slice-0087-e2e", first_built=None),
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
            identifier="inspect_slice_0087_qualified_beam_hull_material",
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
    schema_name = f"hullq_s0087e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0087_e2e_"))
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.domain.broker_access import AuthenticatedIdentity, Provider
        from hullq.domain.market_identity import NativeListingId
        from hullq.domain.physical_boat_claims import (
            AssertionKind,
            BeamClaim,
            BuildYearClaim,
            HullMaterial,
            HullMaterialClaim,
            KeelConfiguration,
            KeelConfigurationClaim,
            PhysicalBoatClaimRevisionId,
            PhysicalBoatClaimSnapshot,
        )
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )
        from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
        from hullq.search.beam_design_bridge import BEAM_FIELD_POINTER, lookup_beam_canonical_value
        from hullq.search.hull_material_design_bridge import (
            HULL_MATERIAL_FIELD_POINTER,
            lookup_hull_material_canonical_value,
        )
        from hullq.search.keel_design_bridge import (
            KEEL_TYPE_FIELD_POINTER,
            lookup_keel_canonical_value,
        )
        from hullq.security.session_token import mint_session_token

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _publication_readiness_fixture import attach_d22_minimum_cover_image

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0087 QUALIFIED BEAM & HULL-MATERIAL SEARCH PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        conn = psycopg.connect(url)
        try:
            # --- Main design/listing: both new facets confirmed, consistent,
            # plus a legacy hard criterion (keel_configuration) so Finding A's
            # mixed legacy+new real SSR request has a genuine design to match.
            _insert_boat_design(
                conn,
                _DESIGN_ID,
                _MODEL_ID,
                beam_m=3.80,
                hull_material="grp_fiberglass",
                keel_type="fin",
            )
            _admit_design_field(
                conn,
                design_id=_DESIGN_ID,
                field_pointer=BEAM_FIELD_POINTER,
                raw_value="3.80",
                resolution_id=f"FR-BEAM-{_DESIGN_ID}",
                fetch_canonical=lookup_beam_canonical_value,
                is_decimal=True,
            )
            _admit_design_field(
                conn,
                design_id=_DESIGN_ID,
                field_pointer=HULL_MATERIAL_FIELD_POINTER,
                raw_value="grp_fiberglass",
                resolution_id=f"FR-HULLMAT-{_DESIGN_ID}",
                fetch_canonical=lookup_hull_material_canonical_value,
                is_decimal=False,
            )
            _admit_design_field(
                conn,
                design_id=_DESIGN_ID,
                field_pointer=KEEL_TYPE_FIELD_POINTER,
                raw_value="fin",
                resolution_id=f"FR-KEEL-{_DESIGN_ID}",
                fetch_canonical=lookup_keel_canonical_value,
                is_decimal=False,
            )

            # --- Negative fixture: confirmed hull_material=wood_composite ---
            _insert_boat_design(
                conn, _NEG_DESIGN_ID, _NEG_MODEL_ID, beam_m=None, hull_material="wood_composite"
            )
            _admit_design_field(
                conn,
                design_id=_NEG_DESIGN_ID,
                field_pointer=HULL_MATERIAL_FIELD_POINTER,
                raw_value="wood_composite",
                resolution_id=f"FR-HULLMAT-{_NEG_DESIGN_ID}",
                fetch_canonical=lookup_hull_material_canonical_value,
                is_decimal=False,
            )

            # --- Review amendment Finding A: one confirmed design per
            # remaining public hull_material token (STEEL/ALUMINUM/WOOD) ---
            for token, raw_value, _label in _MATERIAL_FIXTURES:
                design_id = f"BD-0087-{token}"
                model_id = f"BM-0087-{token}"
                _insert_boat_design(conn, design_id, model_id, beam_m=None, hull_material=raw_value)
                _admit_design_field(
                    conn,
                    design_id=design_id,
                    field_pointer=HULL_MATERIAL_FIELD_POINTER,
                    raw_value=raw_value,
                    resolution_id=f"FR-HULLMAT-{design_id}",
                    fetch_canonical=lookup_hull_material_canonical_value,
                    is_decimal=False,
                )
        finally:
            conn.close()
        print(
            "0a. seeded canonical BoatDesigns: main (3.80 m beam / GRP_FIBERGLASS / FIN keel, "
            "all confirmed), negative (confirmed hull_material=wood_composite, no v0.1 "
            "mapping), and one each for STEEL/ALUMINUM/WOOD -- all with real admitted "
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
            print("SLICE-0087 TECHNICAL SEARCH PROOF RESULT -> FAIL")
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
                physical_boat_id="PB-0087-MAIN",
                market_episode_id="ME-0087-MAIN",
                design_id=_DESIGN_ID,
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0087-MAIN-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Lagoon",
                    model_designation_claim="42",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2019
                    ),
                    beam=BeamClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("3.80")
                    ),
                    hull_material=HullMaterialClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=HullMaterial.GRP_FIBERGLASS,
                    ),
                    keel_configuration=KeelConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
                    ),
                ),
            )

            neg_account, neg_org, neg_membership = _seed_org_account_listing(
                conn,
                org_id=_NEG_ORG_ID,
                account_id=_NEG_ACCOUNT_ID,
                listing_id=_NEG_LISTING_ID,
                physical_boat_id="PB-0087-NEG",
                market_episode_id="ME-0087-NEG",
                design_id=_NEG_DESIGN_ID,
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=neg_account,
                candidate_organization=neg_org,
                membership=neg_membership,
                native_listing_id=NativeListingId(_NEG_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0087-NEG-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Jeanneau",
                    model_designation_claim="Sun Odyssey",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2018
                    ),
                    hull_material=HullMaterialClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullMaterial.WOOD
                    ),
                ),
            )

            # --- Review amendment Finding A: one confirmed listing per
            # remaining public hull_material token (STEEL/ALUMINUM/WOOD) ---
            material_identities: dict[str, tuple[Any, Any, Any]] = {}
            for token, _raw_value, _label in _MATERIAL_FIXTURES:
                design_id = f"BD-0087-{token}"
                listing_id = f"NL-0087-{token}"
                org_id = f"ORG-0087-{token}"
                account_id = f"ACC-0087-{token}"
                m_account, m_org, m_membership = _seed_org_account_listing(
                    conn,
                    org_id=org_id,
                    account_id=account_id,
                    listing_id=listing_id,
                    physical_boat_id=f"PB-0087-{token}",
                    market_episode_id=f"ME-0087-{token}",
                    design_id=design_id,
                )
                write_physical_boat_claim_revision(
                    conn,
                    account_id=m_account,
                    candidate_organization=m_org,
                    membership=m_membership,
                    native_listing_id=NativeListingId(listing_id),
                    revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-0087-{token}-1"),
                    expected_current_revision_id=None,
                    claims=PhysicalBoatClaimSnapshot(
                        marketed_brand_claim="Jeanneau",
                        model_designation_claim="Sun Odyssey",
                        build_year=BuildYearClaim(
                            assertion_kind=AssertionKind.VALUE_ASSERTION, value=2020
                        ),
                        hull_material=HullMaterialClaim(
                            assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullMaterial(token)
                        ),
                    ),
                )
                material_identities[token] = (m_account, m_org, m_membership)
        finally:
            conn.close()
        print(
            "3. seeded ORG_A (main, PUBLISHER, lifecycle-DRAFT) plus the negative fixture and "
            "one STEEL/ALUMINUM/WOOD Organization/listing each -> OK\n"
        )

        session = BrowserSession()
        session.jar.set_cookie(_cookie(_ACCOUNT_ID, _mint_cookie(_ACCOUNT_ID)))
        neg_session = BrowserSession()
        neg_session.jar.set_cookie(_cookie(_NEG_ACCOUNT_ID, _mint_cookie(_NEG_ACCOUNT_ID)))

        # --- 1. broker Search-fit SSR, both new facets, listing DRAFT -------
        status, headers, body = session.get(
            f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}"
            "?sf_beam_min=3.2&sf_beam_max=4.4&sf_hull_material=GRP_FIBERGLASS"
        )
        page_text = body.decode("utf-8")
        _checks = {
            "status": status == 200,
            "result": "Result: <strong>CONFIRMED_MATCH</strong>" in page_text,
            "design_result": "Canonical design result: <strong>CONFIRMED_MATCH</strong>"
            in page_text,
            "cache_control": headers.get("Cache-Control") == "private, no-store",
            "robots": headers.get("X-Robots-Tag") == "noindex",
            "beam_min_true": "beam_m &gt;= 3.2: TRUE" in page_text,
            "beam_max_true": "beam_m &lt;= 4.4: TRUE" in page_text,
            "hull_material_true": "hull_material = GRP_FIBERGLASS: TRUE" in page_text,
            "design_value_beam": "design value: 3.80" in page_text,
            "design_value_hull": "design value: GRP_FIBERGLASS" in page_text,
        }
        broker_fit_ok = all(_checks.values())
        ok &= broker_fit_ok
        print(
            "1. private broker Search-fit SSR (DRAFT listing), both SLICE-0087 facets -> "
            f"CONFIRMED_MATCH with real per-criterion evidence -> "
            f"{'OK' if broker_fit_ok else 'FAIL'}\n"
        )

        # --- 2. broker claim save (real HTTP write) + real re-GET reopen ----
        # Mirrors the real built editor's full-snapshot form submission: a
        # genuine browser POST re-submits every currently-selected claim
        # field, not only the two this amendment is proving -- omitting
        # keel_configuration here would itself silently erase the main
        # listing's already-confirmed FIN claim on this save (the write path
        # replaces the whole snapshot, it does not patch individual fields).
        save_fields = {
            "action": "save_claim",
            "revision_id": "PBCREV-0087-MAIN-2",
            "expected_current_revision_id": "PBCREV-0087-MAIN-1",
            "marketed_brand_claim": "Lagoon",
            "model_designation_claim": "42",
            "build_year_kind": "VALUE_ASSERTION",
            "build_year_value": "2019",
            "keel_configuration_kind": "VALUE_ASSERTION",
            "keel_configuration_value": "FIN",
            "beam_kind": "VALUE_ASSERTION",
            "beam_value": "3.80",
            "hull_material_kind": "VALUE_ASSERTION",
            "hull_material_value": "GRP_FIBERGLASS",
        }
        status, _, body = session.post_form(
            f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}",
            save_fields,
            extra_headers=_csrf_headers(web_base, _EDITING_CSRF_HEADER_VALUE),
        )
        save_ok = status == 200
        ok &= save_ok
        print(
            f"2. real broker claim save (POST, new HullQ facet fields) -> {'OK' if save_ok else 'FAIL'}"
        )

        status, _, body = session.get(f"{web_base}{_edit_page_path(_ORG_ID, _LISTING_ID)}")
        page_text = body.decode("utf-8")
        reopen_ok = (
            status == 200
            and 'name="hull_material_value"' in page_text
            and 'value="GRP_FIBERGLASS" selected' in page_text
            and 'name="beam_value" value="3.80"' in page_text
        )
        ok &= reopen_ok
        print(
            "   real re-GET of the built editor page reopens the saved 3.80 m / "
            f"GRP_FIBERGLASS claim from durable state -> {'OK' if reopen_ok else 'FAIL'}\n"
        )

        # Review amendment Finding B: the four new claim-editor controls each
        # have exactly one real rendered <label for="..."> paired with
        # exactly one real element carrying that same id, and the four label
        # texts are pairwise distinct -- a fieldset legend alone is never an
        # individual control's accessible name.
        _new_control_ids = ("beam_kind", "beam_value", "hull_material_kind", "hull_material_value")
        _new_control_labels = (
            "Beam assertion status",
            "Overall beam in metres",
            "Hull material assertion status",
            "Hull material value",
        )
        accessibility_ok = (
            all(page_text.count(f'id="{control_id}"') == 1 for control_id in _new_control_ids)
            and all(page_text.count(f'for="{control_id}"') == 1 for control_id in _new_control_ids)
            and all(label in page_text for label in _new_control_labels)
            and len(set(_new_control_labels)) == len(_new_control_labels)
        )
        ok &= accessibility_ok
        print(
            "   real built-SSR markup: each new beam/hull_material control has a unique id "
            f"paired with exactly one label, and all four labels are distinct -> "
            f"{'OK' if accessibility_ok else 'FAIL'}\n"
        )

        # --- 3. publish DRAFT -> ACTIVE for every listing --------------------
        conn = psycopg.connect(url)
        try:
            attach_d22_minimum_cover_image(conn, listing_id=_LISTING_ID, account=account, org=org)
            attach_d22_minimum_cover_image(
                conn, listing_id=_NEG_LISTING_ID, account=neg_account, org=neg_org
            )
            for token, _raw_value, _label in _MATERIAL_FIXTURES:
                m_account, m_org, _m_membership = material_identities[token]
                attach_d22_minimum_cover_image(
                    conn, listing_id=f"NL-0087-{token}", account=m_account, org=m_org
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
        status, _, body = neg_session.post_json(
            f"{api_base}/api/broker/organizations/{_NEG_ORG_ID}/inventory/{_NEG_LISTING_ID}/publish",
            {},
            extra_headers=_csrf_headers(web_base, _LIFECYCLE_CSRF_HEADER_VALUE),
        )
        neg_published_ok = status == 200 and _json(body).get("outcome") == "PUBLISHED"
        ok &= neg_published_ok

        material_published_ok = True
        for token, _raw_value, _label in _MATERIAL_FIXTURES:
            m_session = BrowserSession()
            m_session.jar.set_cookie(
                _cookie(f"ACC-0087-{token}", _mint_cookie(f"ACC-0087-{token}"))
            )
            status, _, body = m_session.post_json(
                f"{api_base}/api/broker/organizations/ORG-0087-{token}"
                f"/inventory/NL-0087-{token}/publish",
                {},
                extra_headers=_csrf_headers(web_base, _LIFECYCLE_CSRF_HEADER_VALUE),
            )
            material_published_ok &= status == 200 and _json(body).get("outcome") == "PUBLISHED"
        ok &= material_published_ok
        print(
            "3. real publish transitions DRAFT -> ACTIVE for every listing (main, negative, "
            f"STEEL/ALUMINUM/WOOD) -> "
            f"{'OK' if (published_ok and neg_published_ok and material_published_ok) else 'FAIL'}\n"
        )

        # --- 4. public buyer Search SSR, each new facet alone ----------------
        status, _, body = session.get(f"{web_base}/en/search?beam_max=4.4&beam_min=3.2")
        page_text = body.decode("utf-8")
        beam_only_ok = (
            status == 200
            and _LISTING_ID in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared overall beam: 3.80 m (not independently verified)" in page_text
        )
        ok &= beam_only_ok
        print(
            f"4. public Search SSR, beam_min=3.2&beam_max=4.4 -> {'OK' if beam_only_ok else 'FAIL'}"
        )

        status, _, body = session.get(f"{web_base}/en/search?hull_material=GRP_FIBERGLASS")
        page_text = body.decode("utf-8")
        hull_material_only_ok = (
            status == 200
            and _LISTING_ID in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared hull material: GRP / fiberglass (not independently verified)"
            in page_text
        )
        ok &= hull_material_only_ok
        print(
            "   public Search SSR, hull_material=GRP_FIBERGLASS -> "
            f"{'OK' if hull_material_only_ok else 'FAIL'}"
        )

        # Canonical order: beam_max, beam_min, hull_material.
        combined_query = "beam_max=4.4&beam_min=3.2&hull_material=GRP_FIBERGLASS"
        status, _, body = session.get(f"{web_base}/en/search?{combined_query}")
        page_text = body.decode("utf-8")
        combined_ok = (
            status == 200
            and _LISTING_ID in page_text
            and "Confirmed matches (1)" in page_text
            and "broker-declared overall beam: 3.80 m (not independently verified)" in page_text
            and "broker-declared hull material: GRP / fiberglass (not independently verified)"
            in page_text
        )
        ok &= combined_ok
        print(
            "   public Search SSR, both SLICE-0087 facets combined -> confirmed match with "
            f"every real observed value rendered -> {'OK' if combined_ok else 'FAIL'}\n"
        )

        # --- 4b. design/configuration evidence visibly distinct --------------
        design_evidence_ok = (
            'aria-label="design configuration evidence"' in page_text
            and "Design/configuration specification (separate from this boat&#39;s own claim)"
            in page_text
            and f"{_DESIGN_ID}::baseline" in page_text
            and "beam_m &gt;= 3.2: confirmed" in page_text
            and "hull_material = GRP_FIBERGLASS: confirmed" in page_text
        )
        ok &= design_evidence_ok
        print(
            "4b. the same combined-match page also renders the separate design/configuration-"
            f"level evidence -> {'OK' if design_evidence_ok else 'FAIL'}\n"
        )

        # --- 4c. Review amendment Finding A: real built-SSR positive match
        # for each remaining public hull_material token, each absent from
        # every other token's own result (never only a nonzero API count) --
        all_listing_ids = {_LISTING_ID, _NEG_LISTING_ID} | {
            f"NL-0087-{other_token}" for other_token, _, _ in _MATERIAL_FIXTURES
        }
        material_checks_ok = True
        for token, _raw_value, label in _MATERIAL_FIXTURES:
            listing_id = f"NL-0087-{token}"
            other_listing_ids = all_listing_ids - {listing_id}
            status, _, body = session.get(f"{web_base}/en/search?hull_material={token}")
            page_text = body.decode("utf-8")
            token_ok = (
                status == 200
                and listing_id in page_text
                and "Confirmed matches (1)" in page_text
                and f"broker-declared hull material: {label} (not independently verified)"
                in page_text
                and all(other_id not in page_text for other_id in other_listing_ids)
            )
            material_checks_ok &= token_ok
            print(
                f"4c. public Search SSR, hull_material={token} -> real built-SSR confirmed "
                f"match, absent from every other material's own result -> "
                f"{'OK' if token_ok else 'FAIL'}"
            )
        ok &= material_checks_ok
        print()

        # --- 4d. Review amendment Finding A: a real built-SSR request mixing
        # a legacy accepted hard criterion (keel_configuration) with both new
        # facets, with every criterion's own evidence actually rendered -----
        mixed_query = (
            "beam_max=4.4&beam_min=3.2&hull_material=GRP_FIBERGLASS&keel_configuration=FIN"
        )
        status, headers, body = session.get(f"{web_base}/en/search?{mixed_query}")
        page_text = body.decode("utf-8")
        _mixed_checks = {
            "status": status == 200,
            "listing_id": _LISTING_ID in page_text,
            "count": "Confirmed matches (1)" in page_text,
            "beam_evidence": "broker-declared overall beam: 3.80 m (not independently verified)"
            in page_text,
            "hull_material_evidence": (
                "broker-declared hull material: GRP / fiberglass (not independently verified)"
                in page_text
            ),
            "keel_evidence": (
                "broker-declared keel configuration: Fin keel (not independently verified)"
                in page_text
            ),
        }
        mixed_ok = all(_mixed_checks.values())
        ok &= mixed_ok
        print(
            "4d. public Search SSR, beam_min/beam_max + hull_material mixed with a legacy "
            "hard criterion (keel_configuration=FIN) -> real built-SSR confirmed match with "
            f"every criterion's own evidence rendered -> {'OK' if mixed_ok else 'FAIL'}\n"
        )

        # --- 5. all five public Search locales, combined scenario ------------
        _locale_text: dict[str, dict[str, str]] = {
            "en": {
                "confirmed_heading": "Confirmed matches",
                "beam_evidence": "broker-declared overall beam: 3.80 m (not independently verified)",
                "hull_material_evidence": "broker-declared hull material: GRP / fiberglass (not independently verified)",
                "design_heading": "Design/configuration specification (separate from this boat&#39;s own claim)",
            },
            "de": {
                "confirmed_heading": "Bestätigte Treffer",
                "beam_evidence": "vom Makler angegebene Breite über alles: 3.80 m (nicht unabhängig verifiziert)",
                "hull_material_evidence": "vom Makler angegebenes Rumpfmaterial: GFK / Fiberglas (nicht unabhängig verifiziert)",
                "design_heading": "Design-/Konfigurationsspezifikation (getrennt von der Angabe des Maklers)",
            },
            "fr": {
                "confirmed_heading": "Résultats confirmés",
                "beam_evidence": "largeur hors tout déclarée par le courtier : 3.80 m (non vérifiée de manière indépendante)",
                "hull_material_evidence": "matériau de coque déclaré par le courtier : PRV / fibre de verre (non vérifié de manière indépendante)",
                "design_heading": "Spécification du design/de la configuration (distincte de la déclaration du courtier)",
            },
            "pt": {
                "confirmed_heading": "Correspondências confirmadas",
                "beam_evidence": "boca declarada pelo corretor: 3.80 m (não verificada de forma independente)",
                "hull_material_evidence": "material de casco declarado pelo corretor: PRFV / fibra de vidro (não verificado de forma independente)",
                "design_heading": "Especificação do design/configuração (separada da declaração do corretor)",
            },
            "es": {
                "confirmed_heading": "Coincidencias confirmadas",
                "beam_evidence": "manga declarada por el bróker: 3.80 m (no verificada de forma independiente)",
                "hull_material_evidence": "material de casco declarado por el bróker: PRFV / fibra de vidrio (no verificado de forma independiente)",
                "design_heading": "Especificación del diseño/configuración (independiente de la declaración del bróker)",
            },
        }
        locale_canonical_href = (
            f'<link rel="canonical" href="http://127.0.0.1:{web_port}/{{locale}}/search?'
            'beam_max=4.4&amp;beam_min=3.2&amp;hull_material=GRP_FIBERGLASS">'
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
                and text["beam_evidence"] in page_text
                and text["hull_material_evidence"] in page_text
                and text["design_heading"] in page_text
            )
            all_locales_ok &= locale_ok
            print(
                f"5. public Search SSR /{locale}/search (both SLICE-0087 facets) -> "
                "canonical URL + confirmed match with real localized concrete AND design "
                f"evidence -> {'OK' if locale_ok else 'FAIL'}"
            )
        ok &= all_locales_ok
        print()

        # --- 6. negative: confirmed wood_composite never falsely matches WOOD
        status, _, body = session.get(f"{web_base}/en/search?hull_material=WOOD")
        page_text = body.decode("utf-8")
        negative_ok = status == 200 and _NEG_LISTING_ID not in page_text
        ok &= negative_ok
        print(
            "6. negative: a listing whose design hull_material is confirmed `wood_composite` "
            f"(no v0.1 mapping) never falsely matches hull_material=WOOD -> "
            f"{'OK' if negative_ok else 'FAIL'}\n"
        )

        # --- 7. negative: unsupported value -> 400; inverted range -> 400;
        #        non-canonical order -> 308
        status, _, body = session.get(
            f"{web_base}/en/search?hull_material=FERROCEMENT", extra_headers={}
        )
        invalid_value_ok = status == 400
        ok &= invalid_value_ok
        print(
            f"7. negative: hull_material=FERROCEMENT -> real SSR 400 -> "
            f"{'OK' if invalid_value_ok else 'FAIL'}"
        )

        status, _, body = session.get(f"{web_base}/en/search?beam_min=4.5&beam_max=3.2")
        invalid_range_ok = status == 400
        ok &= invalid_range_ok
        print(
            "   negative: beam_min > beam_max -> real SSR 400 -> "
            f"{'OK' if invalid_range_ok else 'FAIL'}"
        )

        status, headers, _ = session.get(f"{web_base}/en/search?hull_material=WOOD&beam_max=4.4")
        redirect_ok = (
            status == 308
            and headers.get("Location") == "/en/search?beam_max=4.4&hull_material=WOOD"
        )
        ok &= redirect_ok
        print(
            "   negative: non-canonical key order (hull_material before beam_max) -> 308 to "
            f"canonical order -> {'OK' if redirect_ok else 'FAIL'}\n"
        )

        print(
            "SLICE-0087 QUALIFIED BEAM & HULL-MATERIAL SEARCH PROOF RESULT -> "
            f"{'PASS' if ok else 'FAIL'} [SLICE-0087-DONE]"
        )
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
