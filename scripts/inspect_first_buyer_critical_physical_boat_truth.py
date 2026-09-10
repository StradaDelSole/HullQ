"""SLICE-0050 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed first-buyer-critical-PhysicalBoat-truth vertical
against a real, disposable PostgreSQL 18 schema and real local HTTP servers
(FastAPI + built Astro/Node SSR), per SLICE-0050 §15:

    1. Alembic from the accepted pre-0050 head through the new revision
    2. create a real PhysicalBoat -> MarketEpisode -> NativeListing ->
       current LISTING_OFFER chain through accepted persistence paths
    3. link the PhysicalBoat to a BoatDesign whose baseline draft/keel
       values would make a projection bug observable
    4. publish the listing through the accepted SLICE-0049 lifecycle path
    5. before any 0050 claim revision exists, the ACTIVE listing remains
       public and no BoatDesign value is invented into THIS BOAT
    6. a cross-Organization write attempt is denied and leaves zero
       revision/head rows, then the real owning principal records the
       first seven-field snapshot through the real SLICE-0041 gate
    7. the public FastAPI read returns broker-declared brand/model/
       build-year semantics and the selected technical facts
    8. the public Astro page visibly shows THIS BOAT without a preview
       token/login, with broker text escaped/inert
    9. one omitted field (keel_configuration) and one explicit UNKNOWN
       field (draft) remain distinguishable end-to-end
    10. the BoatDesign baseline value never fills either the omitted or the
        UNKNOWN field
    11. a same-authority correction with an explicit predecessor retains
        the old revision and publishes the new current value
    12. a stale correction attempt is rejected, head/history unchanged
    13. an exact retry of an already-durable identical revision is
        idempotent (no duplicate revision/head movement)
    14. two concurrent corrections from the same predecessor resolve to
        exactly one head advance
    15. withdrawing the NativeListing restores the accepted SLICE-0049
        ordinary public 404 behavior, revealing no claim data
    16. the accepted SLICE-0048 preview boundary and SLICE-0049 production-
        public regression still behave per their accepted contracts

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance) and a
pre-built Astro web package (``uv run`` this only after
``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_first_buyer_critical_physical_boat_truth.py
"""

from __future__ import annotations

import base64
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

from alembic import command
from hullq.application.listing_intake import (
    ListingIntakeOutcome,
    ListingIntakeRequest,
    run_listing_intake,
)
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
    alembic_config,
    alembic_upgrade_head,
    prepare_alembic_baseline,
)
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimWriteStatus,
    fetch_current_physical_boat_claim,
    fetch_physical_boat_claim_revision,
    list_physical_boat_claim_revisions,
    write_physical_boat_claim_revision,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_PRE_0050_HEAD = "8b6d3f0a2c17"  # SLICE-0049 native_listing_lifecycle revision

_TARGET_LISTING_ID = "NL-0050-E2E-001"
_PHYSICAL_BOAT_ID = "PB-0050-E2E-001"
_MARKET_EPISODE_ID = "ME-0050-E2E-001"
_OFFER_REVISION_ID = "REV-0050-E2E-001"
_BOAT_MODEL_ID = "BM-0050-E2E-001"
_BOAT_DESIGN_ID = "BD-0050-E2E-001"
_PREVIEW_LISTING_ID = "NL-0050-PREVIEW-001"
_NEVER_CREATED_ID = "NL-0050-NEVER-CREATED"

_MALICIOUS_MODEL_TEXT = "Oceanis 30.1 <script>alert('xss')</script>"
_BASELINE_DRAFT_TEXT = "1.80"  # BoatDesign baseline draft -- must never leak publicly
_BASELINE_KEEL_TEXT = "FIN"  # BoatDesign baseline keel -- must never leak publicly


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


def _insert_boat_design_with_leaky_baseline(conn: Any, design_id: str, model_id: str) -> None:
    """Minimal direct-SQL admission of one canonical BoatDesign row carrying a
    draft/keel baseline that differs from what this proof's PhysicalBoat
    claims will state -- mirrors
    tests/persistence/test_physical_boat_persistence.py's
    `_insert_canonical_boat_design`, extended with a baseline payload a
    projection bug would leak if BoatDesign values ever backfilled an
    omitted/UNKNOWN PhysicalBoat claim (SLICE-0050 §12)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = (
            '{"draft": {"value": "' + _BASELINE_DRAFT_TEXT + '", "unit": "m"}, '
            '"keel_configuration": "' + _BASELINE_KEEL_TEXT + '"}'
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", baseline_json, "[]", "[]", "{}", "1" * 64],
        )
    conn.commit()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0050e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0050_e2e_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("FIRST BUYER-CRITICAL PHYSICAL BOAT TRUTH\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1

        # 1. Genuinely migrate from the accepted pre-0050 head through the
        # new physical_boat_claim_facts revision.
        command.upgrade(alembic_config(url), _PRE_0050_HEAD)
        alembic_upgrade_head(url)
        print(
            "1. Alembic migrated from the accepted pre-0050 head through the new revision -> OK\n"
        )

        account = AccountId("ACC-0050-E2E")
        org = _org("ORG-0050-E2E")
        membership = _membership("OM-0050-E2E", account, org)
        other_account = AccountId("ACC-0050-E2E-OTHER")
        other_org = _org("ORG-0050-E2E-OTHER")
        other_membership = _membership("OM-0050-E2E-OTHER", other_account, other_org)

        conn = psycopg.connect(url)
        try:
            # 3. Link the PhysicalBoat to a BoatDesign with a leaky baseline.
            _insert_boat_design_with_leaky_baseline(conn, _BOAT_DESIGN_ID, _BOAT_MODEL_ID)

            # 2. Real PhysicalBoat -> MarketEpisode -> NativeListing -> offer chain.
            pb_result = create_physical_boat(
                conn,
                physical_boat=PhysicalBoat(
                    id=PhysicalBoatId(_PHYSICAL_BOAT_ID),
                    boat_design_ref=BoatDesignRef(_BOAT_DESIGN_ID),
                ),
            )
            me_result = create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId(_MARKET_EPISODE_ID),
                    physical_boat_id=PhysicalBoatId(_PHYSICAL_BOAT_ID),
                ),
            )
            nl_result = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_TARGET_LISTING_ID),
                    market_episode_id=MarketEpisodeId(_MARKET_EPISODE_ID),
                ),
            )
            offer_result = write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=NativeListingOfferRevisionId(_OFFER_REVISION_ID),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )
            step2_ok = (
                pb_result.status.value == "created"
                and me_result.status.value == "created"
                and nl_result.status.value == "created"
                and offer_result.status.value == "created"
            )
            ok &= step2_ok
            print(
                f"2. real PhysicalBoat -> MarketEpisode -> NativeListing -> offer chain created "
                f"(BoatDesign-linked, SLICE-0046) -> {'OK' if step2_ok else 'FAIL'}"
            )
            print("3. PhysicalBoat linked to a BoatDesign with a leaky draft/keel baseline -> OK\n")

            # 4. Publish through the accepted SLICE-0049 lifecycle path.
            publish_result = publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            step4_ok = publish_result.status.value == "transitioned"
            ok &= step4_ok
            print(
                f"4. published through the accepted SLICE-0049 lifecycle path -> {'OK' if step4_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        # Serve FastAPI + Astro.
        preview_secret = os.urandom(32)
        api_port = _free_port()
        web_port = _free_port()
        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = _b64url(preview_secret)

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
        api_ready = _wait_for_http(f"{api_base}/api/listings/{_NEVER_CREATED_ID}")
        ok &= api_ready
        print(f"FastAPI serving -> {'OK' if api_ready else 'FAIL'}")

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
        web_ready = _wait_for_http(f"{web_base}/listings/{_NEVER_CREATED_ID}")
        ok &= web_ready
        print(f"Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("FIRST BUYER-CRITICAL PHYSICAL BOAT TRUTH RESULT -> FAIL")
            return 1

        # 5. Before any 0050 claim revision exists, the ACTIVE listing
        # remains public and no BoatDesign value is invented into THIS BOAT.
        pre_claim_status, _, pre_claim_body = _http_get(
            f"{api_base}/api/listings/{_TARGET_LISTING_ID}"
        )
        pre_claim_text = pre_claim_body.decode("utf-8")
        step5_ok = (
            pre_claim_status == 200
            and '"physical_boat_claims":null' in pre_claim_text
            and _BASELINE_DRAFT_TEXT not in pre_claim_text
            and _BASELINE_KEEL_TEXT not in pre_claim_text
        )
        ok &= step5_ok
        print(
            f"5. before any claim exists, ACTIVE listing stays public with physical_boat_claims=null "
            f"and no invented BoatDesign value -> {'OK' if step5_ok else 'FAIL'}\n"
        )

        # 6a. A cross-Organization write attempt is denied and writes nothing.
        conn = psycopg.connect(url)
        try:
            cross_org_attempt = write_physical_boat_claim_revision(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-CROSSORG"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Jeanneau",
                    model_designation_claim="Sun Odyssey 349",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2019
                    ),
                ),
            )
            conn.commit()
            history_after_cross_org = list_physical_boat_claim_revisions(
                conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), org.id
            )
            conn.commit()
            step6a_ok = (
                cross_org_attempt.status is PhysicalBoatClaimWriteStatus.CROSS_ORGANIZATION_DENIED
                and history_after_cross_org == []
            )
            ok &= step6a_ok
            print(
                f"6a. cross-Organization write attempt denied, zero revision/head rows -> "
                f"{'OK' if step6a_ok else 'FAIL'}"
            )

            # 6b. the real owning principal records the first seven-field
            # snapshot through the real SLICE-0041 gate. draft is explicit
            # UNKNOWN and keel_configuration is omitted (point 9/10);
            # loa_length/rudder_configuration are ordinary VALUE_ASSERTIONs
            # (point 7); model_designation_claim carries a malicious
            # HTML-like string (point 8 escaping proof).
            first_claim = write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-001"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim=_MALICIOUS_MODEL_TEXT,
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    loa_length=LoaLengthClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.14")
                    ),
                    draft=DraftClaim(assertion_kind=AssertionKind.UNKNOWN),
                    keel_configuration=None,
                    rudder_configuration=RudderConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=RudderConfiguration.SPADE,
                    ),
                ),
            )
            step6b_ok = (
                first_claim.status is PhysicalBoatClaimWriteStatus.CREATED
                and first_claim.current_revision_id
                == PhysicalBoatClaimRevisionId("PBCREV-0050-001")
            )
            ok &= step6b_ok
            print(
                f"6b. owning principal records the first snapshot via the real SLICE-0041 gate -> {'OK' if step6b_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        if not ok:
            print("FIRST BUYER-CRITICAL PHYSICAL BOAT TRUTH RESULT -> FAIL")
            return 1

        # 7/9/10. Public FastAPI read: broker-declared brand/model/build-year
        # + selected technical facts; omitted (keel) vs explicit UNKNOWN
        # (draft) distinguishable; no BoatDesign baseline leak.
        api_status, api_headers, api_body = _http_get(
            f"{api_base}/api/listings/{_TARGET_LISTING_ID}"
        )
        api_headers_lower = {k.lower(): v for k, v in api_headers.items()}
        api_text = api_body.decode("utf-8")
        step7_ok = (
            api_status == 200
            and '"marketed_brand_claim":"Beneteau"' in api_text
            and '"build_year":{"assertion_kind":"VALUE_ASSERTION","value":2021}' in api_text
            and '"loa_length":{"assertion_kind":"VALUE_ASSERTION","value":"9.14"}' in api_text
            and '"draft":{"assertion_kind":"UNKNOWN","value":null}' in api_text
            and '"keel_configuration":null' in api_text
            and '"rudder_configuration":{"assertion_kind":"VALUE_ASSERTION","value":"SPADE"}'
            in api_text
            and api_headers_lower.get("x-robots-tag") == "noindex"
            and "cache-control" not in api_headers_lower
        )
        ok &= step7_ok
        print(
            f"7. public FastAPI THIS BOAT projection carries the expected typed values -> {'OK' if step7_ok else 'FAIL'}"
        )

        step9_10_api_ok = (
            _BASELINE_DRAFT_TEXT not in api_text and '"keel_configuration_value"' not in api_text
        )
        ok &= step9_10_api_ok
        print(
            f"9/10. omitted keel vs explicit UNKNOWN draft distinguishable, no BoatDesign leak (API) -> "
            f"{'OK' if step9_10_api_ok else 'FAIL'}\n"
        )

        # 8/9/10. Public Astro page: THIS BOAT section visible, no preview
        # token/login, broker text escaped, no BoatDesign leak.
        web_status, web_headers, web_body = _http_get(f"{web_base}/listings/{_TARGET_LISTING_ID}")
        web_headers_lower = {k.lower(): v for k, v in web_headers.items()}
        page_text = web_body.decode("utf-8")
        step8_ok = (
            web_status == 200
            and web_headers_lower.get("x-robots-tag") == "noindex"
            and "THIS BOAT" in page_text
            and "Beneteau" in page_text
            and "LOA: 9.14" in page_text
            and "Draft: unknown" in page_text
            and "Keel configuration: not supplied" in page_text
            and "Rudder configuration: SPADE" in page_text
            and _MALICIOUS_MODEL_TEXT not in page_text
            and "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in page_text
        )
        ok &= step8_ok
        print(
            f"8. public Astro page shows THIS BOAT without a preview token, broker text escaped, "
            f"still noindex (SLICE-0049 SEO contract unchanged) -> {'OK' if step8_ok else 'FAIL'}"
        )

        # Explicit textual check that the leaked baseline keel value never
        # appears as this boat's rendered keel configuration text.
        step9_10_web_ok = (
            _BASELINE_DRAFT_TEXT not in page_text and "Keel configuration: FIN" not in page_text
        )
        ok &= step9_10_web_ok
        print(
            f"9/10. omission ('not supplied') vs UNKNOWN ('unknown') distinguishable, no BoatDesign "
            f"leak (web) -> {'OK' if step9_10_web_ok else 'FAIL'}\n"
        )

        # 11. Same-authority correction with an explicit predecessor.
        conn = psycopg.connect(url)
        try:
            correction = write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-002"),
                expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-001"),
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    loa_length=LoaLengthClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.20")
                    ),
                    draft=DraftClaim(assertion_kind=AssertionKind.UNKNOWN),
                    rudder_configuration=RudderConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=RudderConfiguration.SPADE,
                    ),
                ),
            )
            old_revision = fetch_physical_boat_claim_revision(
                conn, PhysicalBoatClaimRevisionId("PBCREV-0050-001")
            )
            conn.commit()
            step11_ok = (
                correction.status is PhysicalBoatClaimWriteStatus.REVISED
                and old_revision is not None
                and old_revision.claims.loa_length is not None
                and old_revision.claims.loa_length.value == Decimal("9.14")
            )
            ok &= step11_ok
            print(
                f"11. same-authority correction applied, old revision retained -> {'OK' if step11_ok else 'FAIL'}"
            )

            # 12. Stale correction attempt rejected, head/history unchanged.
            stale = write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-003-STALE"),
                expected_current_revision_id=PhysicalBoatClaimRevisionId(
                    "PBCREV-0050-001"
                ),  # stale
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1 STALE",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                ),
            )
            history_after_stale = list_physical_boat_claim_revisions(
                conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), org.id
            )
            current_after_stale = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), org.id
            )
            conn.commit()
            step12_ok = (
                stale.status is PhysicalBoatClaimWriteStatus.CONFLICT
                and len(history_after_stale) == 2
                and current_after_stale is not None
                and current_after_stale.revision_id
                == PhysicalBoatClaimRevisionId("PBCREV-0050-002")
            )
            ok &= step12_ok
            print(
                f"12. stale correction attempt rejected, head/history unchanged -> {'OK' if step12_ok else 'FAIL'}"
            )

            # 13. Exact retry of the already-durable PBCREV-0050-002 is idempotent.
            retry = write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-002"),
                expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-001"),
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    loa_length=LoaLengthClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.20")
                    ),
                    draft=DraftClaim(assertion_kind=AssertionKind.UNKNOWN),
                    rudder_configuration=RudderConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION,
                        value=RudderConfiguration.SPADE,
                    ),
                ),
            )
            history_after_retry = list_physical_boat_claim_revisions(
                conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), org.id
            )
            conn.commit()
            step13_ok = (
                retry.status is PhysicalBoatClaimWriteStatus.ALREADY_EXISTS
                and retry.current_revision_id == PhysicalBoatClaimRevisionId("PBCREV-0050-002")
                and len(history_after_retry) == 2
            )
            ok &= step13_ok
            print(
                f"13. exact retry of an already-durable revision is idempotent, no duplicate -> {'OK' if step13_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        # 14. Two concurrent corrections from the same predecessor resolve
        # to exactly one head advance.
        results: list[Any] = []
        errors: list[BaseException] = []
        barrier = threading.Barrier(2)

        def _race_worker(suffix: str) -> None:
            try:
                race_conn = psycopg.connect(url)
                try:
                    barrier.wait(timeout=10)
                    result = write_physical_boat_claim_revision(
                        race_conn,
                        account_id=account,
                        candidate_organization=org,
                        membership=membership,
                        native_listing_id=NativeListingId(_TARGET_LISTING_ID),
                        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-0050-RACE-{suffix}"),
                        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-0050-002"),
                        claims=PhysicalBoatClaimSnapshot(
                            marketed_brand_claim="Beneteau",
                            model_designation_claim=f"Oceanis 30.1 (race {suffix})",
                            build_year=BuildYearClaim(
                                assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                            ),
                        ),
                    )
                    results.append(result)
                finally:
                    race_conn.close()
            except Exception as exc:  # pragma: no cover - surfaced via errors assertion
                errors.append(exc)

        threads = [
            threading.Thread(target=_race_worker, args=("A",)),
            threading.Thread(target=_race_worker, args=("B",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)

        conn = psycopg.connect(url)
        try:
            history_after_race = list_physical_boat_claim_revisions(
                conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), org.id
            )
        finally:
            conn.close()
        statuses = [r.status for r in results]
        step14_ok = (
            not errors
            and len(results) == 2
            and statuses.count(PhysicalBoatClaimWriteStatus.REVISED) == 1
            and statuses.count(PhysicalBoatClaimWriteStatus.CONFLICT) == 1
            and len(history_after_race) == 3  # 001, 002, + exactly one race winner
        )
        ok &= step14_ok
        print(
            f"14. two concurrent corrections from the same predecessor -> exactly one head advance -> "
            f"{'OK' if step14_ok else 'FAIL'}\n"
        )

        if not ok:
            print("FIRST BUYER-CRITICAL PHYSICAL BOAT TRUTH RESULT -> FAIL")
            return 1

        # 15. Withdraw the listing; public routes return the accepted
        # SLICE-0049 ordinary 404, identical to never-created, revealing no
        # claim data even though claims remain durable.
        conn = psycopg.connect(url)
        try:
            withdraw_result = withdraw_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            conn.commit()
            still_durable = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), org.id
            )
            conn.commit()
        finally:
            conn.close()

        withdrawn_api_status, _, withdrawn_api_body = _http_get(
            f"{api_base}/api/listings/{_TARGET_LISTING_ID}"
        )
        never_created_api_status, _, never_created_api_body = _http_get(
            f"{api_base}/api/listings/{_NEVER_CREATED_ID}"
        )
        withdrawn_web_status, _, withdrawn_web_body = _http_get(
            f"{web_base}/listings/{_TARGET_LISTING_ID}"
        )
        never_created_web_status, _, never_created_web_body = _http_get(
            f"{web_base}/listings/{_NEVER_CREATED_ID}"
        )
        step15_ok = (
            withdraw_result.status.value == "transitioned"
            and still_durable is not None  # claim history untouched by lifecycle withdrawal
            and withdrawn_api_status == 404
            and never_created_api_status == 404
            and withdrawn_api_body == never_created_api_body
            and withdrawn_web_status == 404
            and never_created_web_status == 404
            and withdrawn_web_body == never_created_web_body
        )
        ok &= step15_ok
        print(
            f"15. withdrawn listing is ordinary not-found identical to never-created, claims remain "
            f"durable but unpublished -> {'OK' if step15_ok else 'FAIL'}\n"
        )

        # 16. SLICE-0048 preview boundary + SLICE-0049 production-public
        # regression still behave per their accepted contracts.
        preview_account = AccountId("ACC-0050-PREVIEW")
        preview_org = _org("ORG-0050-PREVIEW")
        preview_membership = _membership("OM-0050-PREVIEW", preview_account, preview_org)
        preview_request = ListingIntakeRequest(
            account_id=preview_account,
            organization=preview_org,
            membership=preview_membership,
            physical_boat_id=PhysicalBoatId("PB-0050-PREVIEW"),
            boat_design_ref=None,
            market_episode_id=MarketEpisodeId("ME-0050-PREVIEW"),
            native_listing_id=NativeListingId(_PREVIEW_LISTING_ID),
            broker_listing_reference=None,
            offer_revision_id=NativeListingOfferRevisionId("REV-0050-PREVIEW"),
            offer=NativeListingOfferSnapshot(
                asking_price_mode=AskingPriceMode.POA,
                location_country="ES",
                broker_description="Preview-only listing, never published.",
            ),
        )
        conn = psycopg.connect(url)
        try:
            preview_intake_result = run_listing_intake(
                conn, request=preview_request, preview_signing_secret=preview_secret
            )
        finally:
            conn.close()
        preview_intake_ok = preview_intake_result.outcome is ListingIntakeOutcome.SUCCEEDED
        assert preview_intake_result.preview_token is not None
        preview_token = preview_intake_result.preview_token

        preview_status, preview_headers, preview_body = _http_get(
            f"{api_base}/api/_preview/listings/{preview_token}"
        )
        preview_headers_lower = {k.lower(): v for k, v in preview_headers.items()}
        tampered_token = preview_token[:-1] + ("A" if preview_token[-1] != "A" else "B")
        tampered_status, _, _ = _http_get(f"{api_base}/api/_preview/listings/{tampered_token}")

        # SLICE-0049 production-public regression: the withdrawn listing's
        # own API response still carries noindex + no preview-confidentiality
        # headers, and the never-created id resolves identically.
        never_created_headers_lower = {
            k.lower(): v
            for k, v in _http_get(f"{api_base}/api/listings/{_NEVER_CREATED_ID}")[1].items()
        }

        step16_ok = (
            preview_intake_ok
            and preview_status == 200
            and b'"asking_price_mode":"POA"' in preview_body
            and preview_headers_lower.get("cache-control") == "private, no-store"
            and preview_headers_lower.get("x-robots-tag") == "noindex, nofollow, noarchive"
            and tampered_status == 404
            and never_created_headers_lower.get("x-robots-tag") == "noindex"
            and "cache-control" not in never_created_headers_lower
        )
        ok &= step16_ok
        print(
            f"16. SLICE-0048 preview boundary and SLICE-0049 production-public regression intact -> "
            f"{'OK' if step16_ok else 'FAIL'}\n"
        )

        # Logs must never contain the preview token or signing secret.
        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secret_b64 = _b64url(preview_secret)
        logs_clean = (
            preview_token not in api_log_text
            and preview_token not in web_log_text
            and secret_b64 not in api_log_text
            and secret_b64 not in web_log_text
        )
        ok &= logs_clean
        print(
            f"    ordinary API/web logs contain no token/secret -> {'OK' if logs_clean else 'FAIL'}\n"
        )

        print(f"FIRST BUYER-CRITICAL PHYSICAL BOAT TRUTH RESULT -> {'PASS' if ok else 'FAIL'}")
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
