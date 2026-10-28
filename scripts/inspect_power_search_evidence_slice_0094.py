"""SLICE-0094 independent-review amendment Round 2, Finding D2 — real
PostgreSQL 18 + real FastAPI + real built Astro SSR proof that visible,
source-labelled per-leaf criterion evidence (requested value, observed
truth, source, explanation, and any non-null reason code) actually renders
for both the design-linked and claim-only Power Search surfaces, for both
a count-only query and a combined drive+count query, across all five
buyer locales.

Mirrors `scripts/inspect_slice_0093_power_drive_search.py`'s Phase-A
buyer-proof shape (plain HTTP GET against the real built SSR output,
substring assertions on the actual rendered HTML -- an "equivalently
reliable executable SSR acceptance proof" per the review, since this
proof concerns server-rendered evidence content, never client-side form
interaction dynamics the way Finding A's Playwright proof did). No
authentication/broker-editor phase is needed -- the public Power Search
surface requires none.

Seeds exactly two candidates:

    1. NL-94D2-CLAIM: a design-UNRESOLVED PhysicalBoat with a current
       publisher POWER + SHAFT + engine_count=2 claim -- matches on the
       claim-only plane, `source_basis=PUBLISHER_CLAIM`.
    2. NL-94D2-LINKED: a design-LINKED PhysicalBoat whose BoatDesign
       baseline has a fully admitted FieldResolution for BOTH
       `drive_type=shaft` and `engine_count=2` (the configuration that
       actually confirms the design-level match), plus one NamedVariant
       that overrides `engine_count` to `4` with NO FieldResolution ever
       admitted for that override -- its own engine_count leaf is
       genuinely UNKNOWN with reason `VALUE_MISSING`, while its drive leaf
       stays TRUE (inherited unchanged from the baseline's own admitted
       FieldResolution). The publisher's current concrete claim (SHAFT +
       engine_count=2) matches, so this candidate's rendered page carries
       BOTH:
         - design-qualified evidence for two configurations (the matching
           baseline, all-TRUE, and the non-matching variant, whose count
           leaf is UNKNOWN and renders a real, non-null, localized reason)
         - publisher-claim-sourced concrete evidence (both leaves TRUE)
       in the same match -- proving the two evidence sources are
       genuinely distinguished and the reason code is not silently
       dropped.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``npm ci --prefix web && npm run build --prefix web``).

Run: uv run python scripts/inspect_power_search_evidence_slice_0094.py
"""

from __future__ import annotations

import base64
import json
import os
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
_LOCALES = ("en", "de", "fr", "pt", "es")

# The exact localized `t.sourcePublisherClaimLabel` / `t.sourceDesignQualifiedLabel`
# / `t.criterionReasonLabel(t.reasonLabels.VALUE_MISSING)` strings
# (`web/src/lib/powerSearchText.ts`), verified by real substring presence
# in each built Astro SSR locale's rendered HTML -- never only in `en`.
_SOURCE_PUBLISHER_CLAIM_BY_LOCALE = {
    "en": "publisher-asserted, not independently verified",
    "de": "Angabe des Anbieters, nicht unabhängig geprüft",
    "fr": "déclaration du vendeur, non vérifiée de manière indépendante",
    "pt": "declaração do vendedor, não verificada de forma independente",
    "es": "declaración del vendedor, no verificada de forma independiente",
}
_SOURCE_DESIGN_QUALIFIED_BY_LOCALE = {
    "en": "design-qualified (BoatDesign/FieldResolution)",
    "de": "design-qualifiziert (BoatDesign/FieldResolution)",
    "fr": "qualifié par le design (BoatDesign/FieldResolution)",
    "pt": "qualificado pelo design (BoatDesign/FieldResolution)",
    "es": "calificado por el diseño (BoatDesign/FieldResolution)",
}
_VALUE_MISSING_REASON_RENDERED_BY_LOCALE = {
    "en": "Reason: value missing",
    "de": "Grund: Wert fehlt",
    "fr": "Raison : valeur manquante",
    "pt": "Motivo: valor em falta",
    "es": "Motivo: valor faltante",
}


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


def _http_get(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _seed(conn: Any) -> None:
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
        PhysicalBoatClaimRevisionId,
        PhysicalBoatClaimSnapshot,
        PowerDriveConfiguration,
        PowerDriveConfigurationClaim,
        PowerEngineCountClaim,
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
    from hullq.search.power_drive_design_bridge import lookup_power_drive_canonical_value
    from hullq.search.power_engine_count_design_bridge import (
        lookup_power_engine_count_canonical_value,
    )

    sys.path.insert(0, str(REPO_ROOT / "tests" / "persistence"))
    from _field_resolution_support import (  # type: ignore[import-not-found]
        admit_resolved_categorical_field,
        admit_resolved_draft_max,
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

    def _publish(
        listing_id: str,
        physical_boat_id: str,
        market_episode_id: str,
        org_id: str,
        boat_design_id: str | None,
        vessel_category: VesselCategoryClaim | None,
        power_drive_configuration: PowerDriveConfigurationClaim | None,
        power_engine_count: PowerEngineCountClaim | None,
    ) -> None:
        account = AccountId(f"ACC-{listing_id}")
        org = _org(org_id)
        membership = _membership(org, account, f"OM-{listing_id}")
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(physical_boat_id),
                boat_design_ref=BoatDesignRef(boat_design_id) if boat_design_id else None,
            ),
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
                broker_description="A well-maintained motor yacht.",
                asking_price_amount=Decimal("250000.00"),
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
                model_designation_claim="Swift Trawler 35",
                build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                vessel_category=vessel_category,
                power_drive_configuration=power_drive_configuration,
                power_engine_count=power_engine_count,
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

    # 1. design-unresolved, publisher-owned POWER + SHAFT + count=2 claim.
    _publish(
        "NL-94D2-CLAIM",
        "PB-94D2-CLAIM",
        "ME-94D2-CLAIM",
        "ORG-94D2-CLAIM",
        None,
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        PowerDriveConfigurationClaim(assertion_kind=VA, value=PowerDriveConfiguration.SHAFT),
        PowerEngineCountClaim(assertion_kind=VA, value=2),
    )

    # 2. design-linked: baseline fully qualified (shaft + count=2, the
    #    matching configuration); one NamedVariant overrides engine_count
    #    to 4 with NO FieldResolution ever admitted for that override --
    #    its own count leaf is genuinely UNKNOWN/VALUE_MISSING while its
    #    drive leaf stays TRUE (inherited from the baseline's own admitted
    #    FieldResolution, unchanged).
    design_id = "BD-94D2-LINKED"
    model_id = "BM-94D2-LINKED"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"propulsion": {"drive_type": "shaft", "engine_count": 2}})
        named_variants_json = json.dumps(
            [{"id": "NV-94D2-UNQ", "overrides": {"propulsion": {"engine_count": 4}}}]
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, %s::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, named_variants_json, "1" * 64],
        )
    conn.commit()
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/drive_type",
        value="shaft",
        resolution_id=f"FR-PWRDRV-{design_id}",
        fetch_canonical_value=lookup_power_drive_canonical_value,
    )
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/engine_count",
        value=Decimal(2),
        resolution_id=f"FR-PWRCNT-{design_id}",
        fetch_canonical_value=lookup_power_engine_count_canonical_value,
    )
    # Deliberately NO FieldResolution admitted for
    # /overrides/propulsion/engine_count on NV-94D2-UNQ.
    _publish(
        "NL-94D2-LINKED",
        "PB-94D2-LINKED",
        "ME-94D2-LINKED",
        "ORG-94D2-LINKED",
        design_id,
        VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        PowerDriveConfigurationClaim(assertion_kind=VA, value=PowerDriveConfiguration.SHAFT),
        PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    conn.commit()


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0094d2_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
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
    schema_name = f"hullq_s0094d2_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0094 AMENDMENT ROUND 2 FINDING D2 — SOURCE-LABELLED PER-LEAF EVIDENCE PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic migrated to current head -> OK\n")

        conn = psycopg.connect(url)
        try:
            _seed(conn)
            print(
                "1. seeded NL-94D2-CLAIM (claim-only, POWER+SHAFT+count=2) and "
                "NL-94D2-LINKED (design-linked: baseline fully qualified shaft+2, one "
                "NamedVariant with an unresolved engine_count override) -> OK\n"
            )
        finally:
            conn.close()

        # Application-level funnel sanity check before ever touching HTTP.
        conn2 = psycopg.connect(url)
        try:
            from hullq.application.power_inventory_query import evaluate_power_requirement

            combined_outcome = evaluate_power_requirement(
                conn2, power_drive="SHAFT", power_engine_count=Decimal(2), as_of=datetime.now(UTC)
            )
            claim_ids = {m.native_listing_id.value for m in combined_outcome.claim_only_matches}
            design_ids = {m.native_listing_id.value for m in combined_outcome.design_linked_matches}
            step2_ok = claim_ids == {"NL-94D2-CLAIM"} and design_ids == {"NL-94D2-LINKED"}
            ok &= step2_ok
            design_match = next(
                m
                for m in combined_outcome.design_linked_matches
                if m.native_listing_id.value == "NL-94D2-LINKED"
            )
            variant_evidence = next(
                ce
                for ce in design_match.design_configuration_evidence
                if ce.configuration_id
                != design_match.design_evaluation.matching_configuration_ids[0]
            )
            variant_count_leaf = next(
                e
                for e in variant_evidence.criterion_evidence
                if e.criterion.field == "power_engine_count"
            )
            reason_present_ok = (
                variant_count_leaf.evaluation.truth.value == "UNKNOWN"
                and variant_count_leaf.evaluation.reason is not None
                and variant_count_leaf.evaluation.reason.value == "VALUE_MISSING"
            )
            ok &= reason_present_ok
            print(
                "2. application funnel: combined SHAFT+2 claim_only_matches="
                f"{sorted(claim_ids)}, design_linked_matches={sorted(design_ids)}, "
                f"variant's own count leaf is UNKNOWN/VALUE_MISSING -> "
                f"{'OK' if (step2_ok and reason_present_ok) else 'FAIL'}\n"
            )
        finally:
            conn2.close()

        api_port = _free_port()
        web_port = _free_port()
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        preview_secret = os.urandom(32)

        api_proc, api_log_path = _start_api(
            url=url,
            api_port=api_port,
            preview_secret_b64=base64.urlsafe_b64encode(preview_secret).decode("ascii"),
        )
        api_ready = _wait_for_http(f"{api_base}/api/search/en/power")
        ok &= api_ready
        print(f"3. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print(
                api_log_path.read_text(encoding="utf-8", errors="replace")[-4000:], file=sys.stderr
            )

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = api_base
        web_env["HOST"] = "127.0.0.1"
        web_env["PORT"] = str(web_port)
        web_log_path = Path(tempfile.mkstemp(prefix="hullq_s0094d2_web_", suffix=".log")[1])
        with web_log_path.open("wb") as web_log:
            web_proc = subprocess.Popen(
                ["node", "./dist/server/entry.mjs"],
                cwd=WEB_DIR,
                env=web_env,
                stdout=web_log,
                stderr=subprocess.STDOUT,
            )
        web_ready = _wait_for_http(f"{web_base}/en/power/search")
        ok &= web_ready
        print(
            f"4. Astro SSR serving (real built Node process) -> {'OK' if web_ready else 'FAIL'}\n"
        )

        if not ok:
            print("SLICE-0094 FINDING D2 PROOF RESULT -> FAIL")
            return 1

        queries = {
            "count-only": "power_engine_count=2",
            "combined": "power_drive=SHAFT&power_engine_count=2",
        }

        for locale in _LOCALES:
            for query_label, query_string in queries.items():
                page_status, page_body = _http_get(
                    f"{web_base}/{locale}/power/search?{query_string}"
                )
                page_text = page_body.decode("utf-8")
                claim_present = "NL-94D2-CLAIM" in page_text
                linked_present = "NL-94D2-LINKED" in page_text
                source_claim_ok = _SOURCE_PUBLISHER_CLAIM_BY_LOCALE[locale] in page_text
                source_design_ok = _SOURCE_DESIGN_QUALIFIED_BY_LOCALE[locale] in page_text
                reason_rendered_ok = _VALUE_MISSING_REASON_RENDERED_BY_LOCALE[locale] in page_text
                locale_ok = (
                    page_status == 200
                    and claim_present
                    and linked_present
                    and source_claim_ok
                    and source_design_ok
                    and reason_rendered_ok
                )
                ok &= locale_ok
                print(
                    f"5.[{locale}/{query_label}] GET /{locale}/power/search?{query_string} "
                    f"(built Astro SSR): claim-only match renders={('OK' if claim_present else 'FAIL')}, "
                    f"design-linked match renders={('OK' if linked_present else 'FAIL')}, "
                    f"publisher-claim source label present={('OK' if source_claim_ok else 'FAIL')}, "
                    f"design-qualified source label present={('OK' if source_design_ok else 'FAIL')}, "
                    f"non-null VALUE_MISSING reason rendered={('OK' if reason_rendered_ok else 'FAIL')} "
                    f"-> {'OK' if locale_ok else 'FAIL'}"
                )
        print()

        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secrets_clean = base64.urlsafe_b64encode(preview_secret).decode("ascii") not in (
            api_log_text + web_log_text
        )
        ok &= secrets_clean
        print(
            f"    ordinary API/web logs contain no preview-signing secret -> {'OK' if secrets_clean else 'FAIL'}\n"
        )

        print(f"SLICE-0094 FINDING D2 PROOF RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
