"""SLICE-0092 owner-visible end-to-end proof — real PostgreSQL + real HTTP +
built Astro SSR.

Executes the new design-unresolved claim-only Sail candidate path against a
real, disposable PostgreSQL 18 schema and real local HTTP servers (FastAPI +
built Astro/Node SSR) — no monkeypatching, no fixture-only bypass:

    PostgreSQL 18
    -> new persistence reader (hullq.persistence.inventory_search.
       list_active_design_unresolved_listings)
    -> publisher-owned SAIL category admission + concrete per-criterion
       claims (hullq.application.native_inventory_query.
       evaluate_claim_only_candidates, reusing the unchanged
       evaluate_configuration/evaluate_projection MUST/AND kernel)
    -> FastAPI (/api/search/{locale}) publisher_claim_matches surface
    -> Astro SSR (/{locale}/search) "publisher claim matches" section

Seeds four ACTIVE listings and proves, through the real committed code
paths:

    1. NL-0092-INSP-LINKED: a design-LINKED listing (keel_type=fin resolved
       on a real BoatDesign) matching `keel_configuration=FIN`. Historical
       design-linked Search behavior (SLICE-0051/0055/0086/0087) is
       unaffected by this slice's additive claim-only path — this listing
       surfaces in the ordinary `confirmed_matches` set, exactly as before.
    2. NL-0092-INSP-CLAIM: a design-UNRESOLVED listing (`PhysicalBoat.
       boat_design_ref IS NULL`) whose publishing Organization has an
       explicit current `VALUE_ASSERTION(SAIL)` category claim plus
       `keel_configuration=FIN` — otherwise completely invisible to native
       technical Search today. Surfaces in the new, separate
       `publisher_claim_matches` set, `source_basis=PUBLISHER_CLAIM`, never
       merged with/labelled as a design-confirmed match.
    3. NL-0092-INSP-POWER: a design-UNRESOLVED listing with an explicit
       current POWER category claim and the same matching
       `keel_configuration=FIN` — proves the negative: never a falsely
       confirmed Sail match merely because the concrete technical fields
       would otherwise qualify.
    4. NL-0092-INSP-CLAIM-TWIN: a design-UNRESOLVED, publisher-owned-SAIL
       listing with `keel_configuration=TWIN_KEEL` — amendment review
       Finding A's exact named scenario ("0 design matches + 1 publisher
       claim match"): under a `keel_configuration=TWIN_KEEL` query this is
       the ONLY confirmed match of any kind, proving the public API/SSR
       never render a misleading "no confirmed matches" message while a
       publisher-claim match is shown.

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance) and a
pre-built Astro web package (``cd web && npm ci && npm run build`` first).

Run: uv run python scripts/inspect_slice_0092_claim_only_search.py
"""

from __future__ import annotations

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


def _base_db_url() -> str:
    url = os.environ.get("HULLQ_TEST_DATABASE_URL", "").strip()
    if not url:
        print(
            "HULLQ_TEST_DATABASE_URL is not set. Point it at a disposable "
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


def _seed(conn: Any) -> None:
    import json

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
        KeelConfiguration,
        KeelConfigurationClaim,
        PhysicalBoatClaimRevisionId,
        PhysicalBoatClaimSnapshot,
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
    from hullq.search.keel_design_bridge import lookup_keel_canonical_value

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

    def _publish_design_unresolved(
        listing_id: str,
        physical_boat_id: str,
        market_episode_id: str,
        org_id: str,
        vessel_category: VesselCategoryClaim | None,
        keel_configuration: KeelConfiguration = KeelConfiguration.FIN,
    ) -> None:
        account = AccountId(f"ACC-{listing_id}")
        org = _org(org_id)
        membership = _membership(org, account, f"OM-{listing_id}")
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id), boat_design_ref=None),
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
                broker_description="A well-maintained cruising boat with no matched design record.",
                asking_price_amount=Decimal("95000.00"),
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
                marketed_brand_claim="Unbranded",
                model_designation_claim="Unmatched Model",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                keel_configuration=KeelConfigurationClaim(
                    assertion_kind=VA, value=keel_configuration
                ),
                vessel_category=vessel_category,
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

    # --- design-linked control listing (regression: untouched by this slice) ---
    design_id = "BD-0092-INSP-LINKED"
    model_id = "BM-0092-INSP-LINKED"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"appendages": {"keel_type": "fin"}})
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
        field_pointer="/baseline/appendages/keel_type",
        value="fin",
        resolution_id=f"FR-KEEL-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )

    account = AccountId("ACC-0092-INSP-LINKED")
    org = _org("ORG-0092-INSP-LINKED")
    membership = _membership(org, account, "OM-0092-INSP-LINKED")
    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-0092-INSP-LINKED"), boat_design_ref=BoatDesignRef(design_id)
        ),
    )
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-0092-INSP-LINKED"),
            physical_boat_id=PhysicalBoatId("PB-0092-INSP-LINKED"),
        ),
    )
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-0092-INSP-LINKED"),
            market_episode_id=MarketEpisodeId("ME-0092-INSP-LINKED"),
        ),
    )
    write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-0092-INSP-LINKED"),
        revision_id=NativeListingOfferRevisionId("REV-0092-INSP-LINKED"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising boat.",
            asking_price_amount=Decimal("180000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-0092-INSP-LINKED"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-0092-INSP-LINKED"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 40",
            build_year=BuildYearClaim(assertion_kind=VA, value=2019),
            keel_configuration=KeelConfigurationClaim(
                assertion_kind=VA, value=KeelConfiguration.FIN
            ),
        ),
    )
    _attach_cover("NL-0092-INSP-LINKED", org, account)
    publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-0092-INSP-LINKED"),
    )

    # --- design-unresolved, publisher-owned SAIL: the new claim-only match ---
    _publish_design_unresolved(
        "NL-0092-INSP-CLAIM",
        "PB-0092-INSP-CLAIM",
        "ME-0092-INSP-CLAIM",
        "ORG-0092-INSP-CLAIM",
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )

    # --- design-unresolved, explicit POWER: never a falsely confirmed match ---
    _publish_design_unresolved(
        "NL-0092-INSP-POWER",
        "PB-0092-INSP-POWER",
        "ME-0092-INSP-POWER",
        "ORG-0092-INSP-POWER",
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )

    # --- design-unresolved, publisher-owned SAIL, TWIN_KEEL: amendment
    # review Finding A proof ("0 design matches + 1 publisher-claim match")
    # -- under a keel_configuration=TWIN_KEEL query, NL-0092-INSP-LINKED
    # (keel=FIN) is not a design-confirmed match, while this listing is the
    # ONLY confirmed match of any kind -- entirely claim-only.
    _publish_design_unresolved(
        "NL-0092-INSP-CLAIM-TWIN",
        "PB-0092-INSP-CLAIM-TWIN",
        "ME-0092-INSP-CLAIM-TWIN",
        "ORG-0092-INSP-CLAIM-TWIN",
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        keel_configuration=KeelConfiguration.TWIN_KEEL,
    )


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
    schema_name = f"hullq_s0092insp_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)
    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0092_insp_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0092 CLAIM-ONLY DESIGN-UNRESOLVED SEARCH PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("1. Alembic migrated to current head -> OK\n")

        conn = psycopg.connect(url)
        try:
            _seed(conn)
            print(
                "2. seeded 1 design-linked control listing (NL-0092-INSP-LINKED), "
                "1 design-unresolved publisher-owned-SAIL listing (NL-0092-INSP-CLAIM), "
                "1 design-unresolved explicit-POWER listing (NL-0092-INSP-POWER), "
                "all keel_configuration=FIN -> OK\n"
            )
        finally:
            conn.close()

        # Also prove the application-level funnel directly against real
        # PostgreSQL before ever touching HTTP -- an independent,
        # non-HTTP-dependent proof of the exact same evaluation.
        conn2 = psycopg.connect(url)
        try:
            from hullq.application.native_inventory_query import (
                evaluate_native_inventory_requirements,
            )

            app_outcome = evaluate_native_inventory_requirements(
                conn2, draft_max=None, keel_configuration="FIN", as_of=datetime.now(UTC)
            )
            confirmed_ids = {m.native_listing_id.value for m in app_outcome.confirmed_matches}
            claim_match_ids = {m.native_listing_id.value for m in app_outcome.claim_only_matches}
            claim_non_match_ids = {
                m.native_listing_id.value for m in app_outcome.claim_only_non_matches
            }
            step3_ok = (
                confirmed_ids == {"NL-0092-INSP-LINKED"}
                and claim_match_ids == {"NL-0092-INSP-CLAIM"}
                and "NL-0092-INSP-POWER" in claim_non_match_ids
            )
            ok &= step3_ok
            print(
                "3. application funnel (evaluate_native_inventory_requirements): "
                f"design-linked confirmed_matches={sorted(confirmed_ids)}, "
                f"claim_only_matches={sorted(claim_match_ids)}, "
                f"NL-0092-INSP-POWER in claim_only_non_matches={'NL-0092-INSP-POWER' in claim_non_match_ids} "
                f"-> {'OK' if step3_ok else 'FAIL'}\n"
            )
        finally:
            conn2.close()

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
            print("SLICE-0092 CLAIM-ONLY DESIGN-UNRESOLVED SEARCH PROOF RESULT -> FAIL")
            return 1

        # 4. Public FastAPI JSON contract: source_basis=PUBLISHER_CLAIM,
        # never a design_evaluation key, never merged into confirmed_matches.
        api_status, _, api_body = _http_get(f"{api_base}/api/search/en?keel_configuration=FIN")
        import json as _json

        api_json = _json.loads(api_body.decode("utf-8"))
        confirmed_ids = {m["native_listing_id"] for m in api_json.get("confirmed_matches", [])}
        claim_matches = api_json.get("publisher_claim_matches", [])
        claim_ids = {m["native_listing_id"] for m in claim_matches}
        claim_entry = next(
            (m for m in claim_matches if m["native_listing_id"] == "NL-0092-INSP-CLAIM"), None
        )
        step4_ok = (
            api_status == 200
            and confirmed_ids == {"NL-0092-INSP-LINKED"}
            and claim_ids == {"NL-0092-INSP-CLAIM"}
            and claim_entry is not None
            and claim_entry.get("source_basis") == "PUBLISHER_CLAIM"
            and "design_evaluation" not in claim_entry
            and "NL-0092-INSP-POWER" not in claim_ids
        )
        ok &= step4_ok
        print(
            "4. GET /api/search/en?keel_configuration=FIN: confirmed_matches="
            f"{sorted(confirmed_ids)}, publisher_claim_matches={sorted(claim_ids)}, "
            f"source_basis={claim_entry.get('source_basis') if claim_entry else None} -> "
            f"{'OK' if step4_ok else 'FAIL'}"
        )

        # 5. Built Astro SSR page: the new claim-only candidate is rendered
        # in a visibly distinct section with the PUBLISHER_CLAIM disclaimer,
        # never implying design-confirmed/verified provenance; the
        # historical design-linked match is unaffected; the excluded POWER
        # listing never appears at all.
        page_status, _, page_body = _http_get(f"{web_base}/en/search?keel_configuration=FIN")
        # Astro/JSX escapes an apostrophe in rendered text content as the
        # HTML entity `&#39;` (correct, expected HTML output) -- match on
        # the surrounding text only, not the literal apostrophe character.
        page_text = page_body.decode("utf-8")
        step5_ok = (
            page_status == 200
            and "NL-0092-INSP-LINKED" in page_text
            and "NL-0092-INSP-CLAIM" in page_text
            and "NL-0092-INSP-POWER" not in page_text
            and "own current statement meets this requirement" in page_text
            and "not because HullQ has independently verified the design" in page_text
        )
        ok &= step5_ok
        print(
            "5. GET /en/search?keel_configuration=FIN (built Astro SSR): design-linked "
            "match + new publisher-claim section (with disclaimer) both render; "
            f"excluded POWER listing never appears -> {'OK' if step5_ok else 'FAIL'}\n"
        )

        # 6. Amendment (independent review PR #387, Finding A): the exact
        # scenario the review named -- 0 design-confirmed matches + 1
        # publisher-claim-only match -- must never render a bare "no
        # confirmed matches" message that reads as a totally empty result
        # when a publisher-claim match is shown right below it.
        api_status6, _, api_body6 = _http_get(
            f"{api_base}/api/search/en?keel_configuration=TWIN_KEEL"
        )
        api_json6 = _json.loads(api_body6.decode("utf-8"))
        confirmed_ids6 = {m["native_listing_id"] for m in api_json6.get("confirmed_matches", [])}
        claim_ids6 = {m["native_listing_id"] for m in api_json6.get("publisher_claim_matches", [])}
        page_status6, _, page_body6 = _http_get(
            f"{web_base}/en/search?keel_configuration=TWIN_KEEL"
        )
        page_text6 = page_body6.decode("utf-8")
        step6_ok = (
            api_status6 == 200
            and confirmed_ids6 == set()
            and claim_ids6 == {"NL-0092-INSP-CLAIM-TWIN"}
            and page_status6 == 200
            and "No design-confirmed matches" in page_text6
            and "1 additional match(es) based on the broker" in page_text6
            and "NL-0092-INSP-CLAIM-TWIN" in page_text6
        )
        ok &= step6_ok
        print(
            "6. GET keel_configuration=TWIN_KEEL (0 design + 1 claim-only): API "
            f"confirmed_matches={sorted(confirmed_ids6)}, publisher_claim_matches="
            f"{sorted(claim_ids6)}; SSR shows the unambiguous zero-design-matches-"
            f"with-publisher-claims disclosure -> {'OK' if step6_ok else 'FAIL'}\n"
        )

        print(
            f"SLICE-0092 CLAIM-ONLY DESIGN-UNRESOLVED SEARCH PROOF RESULT -> "
            f"{'PASS' if ok else 'FAIL'} [SLICE-0092-DONE]"
        )
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
