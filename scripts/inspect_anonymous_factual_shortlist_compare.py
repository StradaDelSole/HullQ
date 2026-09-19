"""SLICE-0059 anonymous factual shortlist Compare owner-visible end-to-end proof.

Executes the committed anonymous factual shortlist Compare vertical against a
real, disposable PostgreSQL 18 schema and real local HTTP servers (FastAPI +
built Astro/Node SSR), per
`specs/ANONYMOUS_FACTUAL_SHORTLIST_COMPARE_CONTRACT.v0.1.md` §15:

    1. at least two saved local NativeListingId values (one with a full
       SLICE-0050 PhysicalBoat claim snapshot, one with a partial snapshot
       mixing VALUE_ASSERTION/UNKNOWN/omitted fields, one WITHDRAWN, one
       never-created)
    1b. every column of the rendered comparison -- available or
        unavailable/service-error -- produces the identical aligned row
        count/order (a genuine side-by-side matrix, not independent cards)
    2. the real shipped `shortlistCompareRuntime.ts`/`shortlistCompareText.ts`
       modules (run under Node, not reimplemented in Python) classify the
       compare set as empty/need-one-more/ready from local membership alone
    3. current public data is resolved through the existing accepted
       `/api/shortlist/resolve` transport, not loaded from stored listing
       truth
    4. concrete claim/offer fields render for available items, and
       VALUE_ASSERTION/UNKNOWN/not-supplied semantics remain explicit and
       distinct -- exercised against the real shipped `buildCompareFields`
    5. no PhysicalBoat claims recorded at all leaves every concrete-yacht
       comparison row `null` (never a BoatDesign-baseline fallback)
    6. an unavailable saved id (WITHDRAWN, and a never-created id) remains
       neutral and retained
    7. a resolver/API outage is distinct from unavailable (a genuine upstream
       outage resolves every requested id to `service_error`)
    8. no shortlist mutation occurs from Compare (resolving is read-only;
       local membership is never touched by the server)
    9. no account/database Compare persistence appears (no `*compare*` table)
    10. all five `/{locale}/shortlist/compare` routes exist, are `noindex`
        and `private, no-store`, carry no saved ids in their served markup,
        and the `/{locale}/shortlist` page links to Compare
    11. finish with `ANONYMOUS FACTUAL SHORTLIST COMPARE RESULT -> PASS`
    12. the compare set is sourced from the real shipped `shortlistStore.ts`
        in buyer-authored order (not a hand-typed literal id array), and
        resolving through Compare's own runtime seam
        (`shortlistResolutionApi.ts`) leaves the stored local membership
        byte-identical
    13. after a server-side offer price revision and a PhysicalBoat claim
        revision, the next resolution reflects both new current values while
        the stored shortlist payload itself stays unchanged

Steps 12/13 exercise the real shipped store/resolution modules under Node
against this proof's own running Astro server (with only same-origin-relative
`fetch()` rewritten onto that server's host:port, since a Node harness has no
browser origin) -- this proof does not execute a real browser DOM. The
rendered aligned-matrix HTML itself (blocker 1) is covered separately by
`web/src/lib/__tests__/shortlistCompareRuntime.test.ts` unit tests.

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance), a
pre-built Astro web package (``cd web && npm ci && npm run build``) and a
``node`` executable on PATH capable of running TypeScript directly (Node
23.6+/24, matching ``web/package.json``'s own ``npm test`` convention).

Run: uv run python scripts/inspect_anonymous_factual_shortlist_compare.py
"""

from __future__ import annotations

import base64
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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    LifecycleTransitionStatus,
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    NativeListingOfferWriteStatus,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimWriteStatus,
    write_physical_boat_claim_revision,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"
COMPARE_RUNTIME_MODULE = WEB_DIR / "src" / "lib" / "shortlistCompareRuntime.ts"
COMPARE_TEXT_MODULE = WEB_DIR / "src" / "lib" / "shortlistCompareText.ts"
SHORTLIST_TEXT_MODULE = WEB_DIR / "src" / "lib" / "shortlistText.ts"
STORE_MODULE = WEB_DIR / "src" / "lib" / "shortlistStore.ts"
RESOLUTION_API_MODULE = WEB_DIR / "src" / "lib" / "shortlistResolutionApi.ts"

_FULL_CLAIMS_ID = "NL-0059-FULL-CLAIMS"
_PARTIAL_CLAIMS_ID = "NL-0059-PARTIAL-CLAIMS"
_WITHDRAWN_ID = "NL-0059-WITHDRAWN"
_NEVER_CREATED_ID = "NL-0059-NEVER-CREATED"
_FULL_PRICE = "129000.00"
_FULL_PRICE_REVISED = "141000.00"
_PARTIAL_PRICE = "45000.00"

_LOCALES = ("en", "de", "fr", "pt", "es")

_HARNESS_SCRIPT = """
import { pathToFileURL } from "node:url";

const [, , runtimeModulePath, textModulePath, shortlistTextModulePath] = process.argv;
const runtime = await import(pathToFileURL(runtimeModulePath).href);
const compareText = await import(pathToFileURL(textModulePath).href);
const shortlistTextModule = await import(pathToFileURL(shortlistTextModulePath).href);

const t = compareText.shortlistCompareText.en;
const st = shortlistTextModule.shortlistText.en;
const labels = {
  priceOnApplicationLabel: st.priceOnApplicationLabel,
  freshnessConfirmedLabel: st.freshnessConfirmedLabel,
  freshnessDueLabel: st.freshnessDueLabel,
};

function listingFixture(overrides) {
  return {
    asking_price_mode: "AMOUNT",
    asking_price_amount: "1.00",
    currency: "EUR",
    location_country: "FR",
    location_region: null,
    broker_summary: null,
    broker_description: "x",
    known_history_narrative: null,
    vat_tax_status_claim: null,
    publishing_organization_id: "ORG",
    offer_recorded_at: "2026-01-01T00:00:00Z",
    hullq_vat_verification_status: "UNVERIFIED",
    physical_boat_claims: null,
    freshness_status: "CONFIRMED",
    last_confirmed_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const out = {};

out.state_zero = runtime.compareSetState([]);
out.state_one = runtime.compareSetState(["A"]);
out.state_two = runtime.compareSetState(["A", "B"]);
out.state_many = runtime.compareSetState(["A", "B", "C"]);

const fullClaimsListing = listingFixture({
  asking_price_amount: "129000.00",
  physical_boat_claims: {
    marketed_brand_claim: "Beneteau",
    model_designation_claim: "Oceanis 30.1",
    build_year: { assertion_kind: "VALUE_ASSERTION", value: 2021 },
    loa_length: { assertion_kind: "VALUE_ASSERTION", value: "9.53" },
    draft: { assertion_kind: "VALUE_ASSERTION", value: "1.85" },
    keel_configuration: { assertion_kind: "VALUE_ASSERTION", value: "FIN" },
    rudder_configuration: { assertion_kind: "VALUE_ASSERTION", value: "SPADE" },
  },
});
const partialClaimsListing = listingFixture({
  physical_boat_claims: {
    marketed_brand_claim: "Jeanneau",
    model_designation_claim: "Sun Odyssey 349",
    build_year: { assertion_kind: "UNKNOWN", value: null },
    loa_length: null,
    draft: null,
    keel_configuration: { assertion_kind: "UNKNOWN", value: null },
    rudder_configuration: null,
  },
});
const noClaimsListing = listingFixture({});

const fullFields = runtime.buildCompareFields(fullClaimsListing, t, labels);
out.full_identity = fullFields.identityHeading;
out.full_build_year = fullFields.buildYear;
out.full_loa = fullFields.loa;
out.full_keel = fullFields.keel;
out.full_price = fullFields.price;

const partialFields = runtime.buildCompareFields(partialClaimsListing, t, labels);
out.partial_build_year = partialFields.buildYear;
out.partial_loa = partialFields.loa;
out.partial_keel = partialFields.keel;
out.partial_rudder = partialFields.rudder;

const noClaimsFields = runtime.buildCompareFields(noClaimsListing, t, labels);
out.no_claims_identity_is_null = noClaimsFields.identityHeading === null;
out.no_claims_build_year_is_null = noClaimsFields.buildYear === null;
out.no_claims_loa_is_null = noClaimsFields.loa === null;

const poaFields = runtime.buildCompareFields(
  listingFixture({ asking_price_mode: "POA", asking_price_amount: null, currency: null }),
  t,
  labels,
);
out.poa_price = poaFields.price;

// The aligned side-by-side matrix itself: prove every column (available or
// not) produces the exact same row count/order, and that an
// unavailable/service-error column's row values are the neutral
// placeholder rather than a repeated status sentence (independent review
// 2026-09-19, PR #221, blocker 1).
const rowLabels = runtime.compareRowLabels(t);
out.row_label_count = rowLabels.length;
out.full_row_values = runtime.compareRowValues(fullFields, t);
out.placeholder_row_values = runtime.compareRowValues(null, t);
out.rows_are_aligned =
  out.full_row_values.length === rowLabels.length &&
  out.placeholder_row_values.length === rowLabels.length;

process.stdout.write(JSON.stringify(out));
"""

# Independent review 2026-09-19 (PR #221), blocker 3: the harness above only
# proves `buildCompareFields`/`compareRowValues` in isolation against
# hand-built fixture objects -- it never touches the real shipped
# `shortlistStore.ts`, so it does not prove the Compare set is actually
# sourced from local Shortlist membership, that using Compare leaves that
# membership unchanged, or that a later server-side truth change is
# reflected without ever rewriting the stored payload. This second harness
# imports the real, unmodified `shortlistStore.ts` and
# `shortlistResolutionApi.ts` modules (the exact modules
# `shortlistCompareRuntime.ts` itself calls) under Node and exercises them
# against the already-running Astro server this proof started -- the only
# change from real browser behavior is rewriting a same-origin-relative
# fetch() onto that server's actual host:port, since this harness has no
# browser origin of its own. It does not execute a real browser DOM; the
# rendered aligned-matrix HTML is covered separately by
# `shortlistCompareRuntime.test.ts` unit tests, and that limitation is
# disclosed here rather than overclaimed.
_STORE_SOURCED_HARNESS_SCRIPT = """
import { pathToFileURL } from "node:url";

const [
  ,
  ,
  storeModulePath,
  resolutionApiModulePath,
  runtimeModulePath,
  webBaseUrl,
  fullId,
  partialId,
  withdrawnId,
  neverCreatedId,
] = process.argv;

const store = await import(pathToFileURL(storeModulePath).href);
const resolutionApi = await import(pathToFileURL(resolutionApiModulePath).href);
const runtime = await import(pathToFileURL(runtimeModulePath).href);

// shortlistResolutionApi.ts calls bare fetch("/api/shortlist/resolve", ...),
// same-origin-relative by design for the real browser/Astro-proxy topology.
// This harness process has no browser origin, so it rewrites any
// leading-slash request onto the live Astro server this proof already
// started, without touching the module's own (unmodified) request-building
// logic at all.
const realFetch = globalThis.fetch;
globalThis.fetch = (input, init) => {
  const url =
    typeof input === "string" && input.startsWith("/") ? new URL(input, webBaseUrl).toString() : input;
  return realFetch(url, init);
};

class FakeStorage {
  constructor() {
    this.data = new Map();
  }
  getItem(key) {
    return this.data.has(key) ? this.data.get(key) : null;
  }
  setItem(key, value) {
    this.data.set(key, value);
  }
}

const storage = new FakeStorage();
// Buyer-authored add order, via the real shipped store module -- this is
// the exact seam that makes the compare set "sourced from the accepted
// versioned Shortlist store" rather than a hand-typed literal array.
store.addToShortlist(storage, fullId);
store.addToShortlist(storage, partialId);
store.addToShortlist(storage, withdrawnId);
store.addToShortlist(storage, neverCreatedId);

const out = {};

const ids = store.loadShortlistIds(storage);
out.ids = ids;
out.compare_state = runtime.compareSetState(ids);

const rawBefore = storage.getItem(store.SHORTLIST_STORAGE_KEY);
out.raw_before = rawBefore;

// This is the exact resolution call Compare's own runtime makes.
const resolution = await resolutionApi.resolveShortlistListings(ids);

const rawAfter = storage.getItem(store.SHORTLIST_STORAGE_KEY);
out.raw_after = rawAfter;
out.raw_unchanged = rawBefore === rawAfter;

out.resolution_kind = resolution.kind;
if (resolution.kind === "loaded") {
  const byId = Object.fromEntries(resolution.items.map((item) => [item.native_listing_id, item]));
  out.full_state = byId[fullId] ? byId[fullId].state : null;
  out.full_price = byId[fullId] && byId[fullId].data ? byId[fullId].data.asking_price_amount : null;
  const partialClaims =
    byId[partialId] && byId[partialId].data ? byId[partialId].data.physical_boat_claims : null;
  out.partial_build_year_kind = partialClaims ? partialClaims.build_year.assertion_kind : null;
  out.partial_build_year_value = partialClaims ? partialClaims.build_year.value : null;
  out.withdrawn_state = byId[withdrawnId] ? byId[withdrawnId].state : null;
  out.never_created_state = byId[neverCreatedId] ? byId[neverCreatedId].state : null;
}

process.stdout.write(JSON.stringify(out));
"""


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


def _http_post_json(url: str, payload: dict[str, Any]) -> tuple[int | None, Any]:
    """POST *payload* as JSON. Returns `(None, None)` for a genuine transport
    failure (connection refused/timeout) -- distinct from any real HTTP
    status, exactly the distinction the shortlist resolver itself must
    preserve one layer down (contract §9)."""
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"content-type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else None
        except json.JSONDecodeError:
            parsed = None
        return exc.code, parsed
    except urllib.error.URLError, ConnectionError, TimeoutError, OSError:
        return None, None


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


def _create_and_publish(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    asking_price: str,
) -> None:
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
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
        revision_id=NativeListingOfferRevisionId(offer_revision_id),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="SLICE-0059 proof fixture listing.",
            asking_price_amount=Decimal(asking_price),
            currency="EUR",
        ),
    )
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    if publish_result.status is not LifecycleTransitionStatus.TRANSITIONED:
        raise RuntimeError(f"fixture publish failed for {listing_id}: {publish_result.status}")


def _write_full_claims(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(_FULL_CLAIMS_ID),
        revision_id=PhysicalBoatClaimRevisionId("PBC-0059-FULL"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            loa_length=LoaLengthClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.53")
            ),
            draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.85")),
            keel_configuration=KeelConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
            ),
            rudder_configuration=RudderConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=RudderConfiguration.SPADE
            ),
        ),
    )
    if result.status is not PhysicalBoatClaimWriteStatus.CREATED:
        raise RuntimeError(f"full-claims fixture write failed: {result.status}")


def _write_partial_claims(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(_PARTIAL_CLAIMS_ID),
        revision_id=PhysicalBoatClaimRevisionId("PBC-0059-PARTIAL"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Jeanneau",
            model_designation_claim="Sun Odyssey 349",
            # build_year is REQUIRED_RESPONSE but the broker may answer UNKNOWN.
            build_year=BuildYearClaim(assertion_kind=AssertionKind.UNKNOWN),
            loa_length=None,  # omitted entirely -- distinct from UNKNOWN
            draft=None,
            keel_configuration=KeelConfigurationClaim(assertion_kind=AssertionKind.UNKNOWN),
            rudder_configuration=None,
        ),
    )
    if result.status is not PhysicalBoatClaimWriteStatus.CREATED:
        raise RuntimeError(f"partial-claims fixture write failed: {result.status}")


def _bump_full_price(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    new_price: str,
) -> None:
    """Write a second offer revision for the full-claims fixture listing,
    changing only its asking price. Proves (independent review 2026-09-19,
    PR #221, blocker 3) that a later server-side offer change is reflected
    on the next Compare resolution."""
    result = write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(_FULL_CLAIMS_ID),
        revision_id=NativeListingOfferRevisionId("REV-0059-FULL-2"),
        expected_current_revision_id=NativeListingOfferRevisionId("REV-0059-FULL"),
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="SLICE-0059 proof fixture listing.",
            asking_price_amount=Decimal(new_price),
            currency="EUR",
        ),
    )
    if result.status is not NativeListingOfferWriteStatus.REVISED:
        raise RuntimeError(f"full-claims price bump failed: {result.status}")


def _bump_partial_build_year(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    """Write a second PhysicalBoat claim revision for the partial-claims
    fixture listing, resolving its build_year from UNKNOWN to a
    VALUE_ASSERTION. Proves (independent review 2026-09-19, PR #221,
    blocker 3) that a later server-side concrete-claim change is reflected
    on the next Compare resolution."""
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(_PARTIAL_CLAIMS_ID),
        revision_id=PhysicalBoatClaimRevisionId("PBC-0059-PARTIAL-2"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBC-0059-PARTIAL"),
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Jeanneau",
            model_designation_claim="Sun Odyssey 349",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2022),
            loa_length=None,
            draft=None,
            keel_configuration=KeelConfigurationClaim(assertion_kind=AssertionKind.UNKNOWN),
            rudder_configuration=None,
        ),
    )
    if result.status is not PhysicalBoatClaimWriteStatus.REVISED:
        raise RuntimeError(f"partial-claims build-year bump failed: {result.status}")


def _table_names_matching(conn: Any, needle: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name ILIKE %s",
            [f"%{needle}%"],
        )
        return [row[0] for row in cur.fetchall()]


def _run_compare_harness() -> tuple[bool, dict[str, Any]]:
    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0059_compare_harness_"))
    harness_path = log_dir / "shortlist_compare_harness.mjs"
    harness_path.write_text(_HARNESS_SCRIPT, encoding="utf-8")
    try:
        result = subprocess.run(
            [
                "node",
                str(harness_path),
                str(COMPARE_RUNTIME_MODULE),
                str(COMPARE_TEXT_MODULE),
                str(SHORTLIST_TEXT_MODULE),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)

    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False, {}
    try:
        return True, json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"compare harness produced non-JSON stdout: {result.stdout!r}", file=sys.stderr)
        return False, {}


def _run_store_sourced_harness(web_base: str) -> tuple[bool, dict[str, Any]]:
    """Run `_STORE_SOURCED_HARNESS_SCRIPT` against the real shipped
    `shortlistStore.ts`/`shortlistResolutionApi.ts`/`shortlistCompareRuntime.ts`
    modules, resolving through *web_base*'s already-running Astro server
    (independent review 2026-09-19, PR #221, blocker 3)."""
    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0059_store_sourced_harness_"))
    harness_path = log_dir / "shortlist_compare_store_sourced_harness.mjs"
    harness_path.write_text(_STORE_SOURCED_HARNESS_SCRIPT, encoding="utf-8")
    try:
        result = subprocess.run(
            [
                "node",
                str(harness_path),
                str(STORE_MODULE),
                str(RESOLUTION_API_MODULE),
                str(COMPARE_RUNTIME_MODULE),
                web_base,
                _FULL_CLAIMS_ID,
                _PARTIAL_CLAIMS_ID,
                _WITHDRAWN_ID,
                _NEVER_CREATED_ID,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)

    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False, {}
    try:
        return True, json.loads(result.stdout)
    except json.JSONDecodeError:
        print(
            f"store-sourced compare harness produced non-JSON stdout: {result.stdout!r}",
            file=sys.stderr,
        )
        return False, {}


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1
    required_modules = (
        COMPARE_RUNTIME_MODULE,
        COMPARE_TEXT_MODULE,
        SHORTLIST_TEXT_MODULE,
        STORE_MODULE,
        RESOLUTION_API_MODULE,
    )
    if not all(module.exists() for module in required_modules):
        print("SLICE-0059 compare/shortlist runtime modules do not exist.", file=sys.stderr)
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0059e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0059_e2e_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("ANONYMOUS FACTUAL SHORTLIST COMPARE\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("Alembic upgraded to single current head -> OK\n")

        account = AccountId("ACC-0059-E2E")
        org = _org("ORG-0059-E2E")
        membership = _membership("OM-0059-E2E", account, org)

        conn = psycopg.connect(url)
        try:
            _create_and_publish(
                conn,
                listing_id=_FULL_CLAIMS_ID,
                physical_boat_id="PB-0059-FULL",
                market_episode_id="ME-0059-FULL",
                offer_revision_id="REV-0059-FULL",
                account=account,
                org=org,
                membership=membership,
                asking_price=_FULL_PRICE,
            )
            _write_full_claims(conn, account=account, org=org, membership=membership)

            _create_and_publish(
                conn,
                listing_id=_PARTIAL_CLAIMS_ID,
                physical_boat_id="PB-0059-PARTIAL",
                market_episode_id="ME-0059-PARTIAL",
                offer_revision_id="REV-0059-PARTIAL",
                account=account,
                org=org,
                membership=membership,
                asking_price=_PARTIAL_PRICE,
            )
            _write_partial_claims(conn, account=account, org=org, membership=membership)

            _create_and_publish(
                conn,
                listing_id=_WITHDRAWN_ID,
                physical_boat_id="PB-0059-WITHDRAWN",
                market_episode_id="ME-0059-WITHDRAWN",
                offer_revision_id="REV-0059-WITHDRAWN",
                account=account,
                org=org,
                membership=membership,
                asking_price="50000.00",
            )
            withdraw_result = withdraw_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_WITHDRAWN_ID),
            )
            conn.commit()
            step1_ok = withdraw_result.status is LifecycleTransitionStatus.TRANSITIONED
            ok &= step1_ok
            print(
                f"1. fixture listings (two available with claims, one withdrawn) created -> {'OK' if step1_ok else 'FAIL'}\n"
            )

            no_compare_tables = _table_names_matching(conn, "compare")
            conn.commit()
            step9_ok = no_compare_tables == []
            ok &= step9_ok
            print(f"9. no *compare* table exists in the schema -> {'OK' if step9_ok else 'FAIL'}")
        finally:
            conn.close()

        if not ok:
            print("ANONYMOUS FACTUAL SHORTLIST COMPARE RESULT -> FAIL")
            return 1

        # 2/4/5. the real shipped compareSetState/buildCompareFields modules,
        # run under Node, classify compare-set size and preserve
        # VALUE_ASSERTION/UNKNOWN/omitted claim-scope distinctions without
        # any BoatDesign-baseline fallback.
        harness_ok, harness = _run_compare_harness()
        step2_ok = (
            harness_ok
            and harness.get("state_zero") == "empty"
            and harness.get("state_one") == "need_one_more"
            and harness.get("state_two") == "ready"
            and harness.get("state_many") == "ready"
        )
        ok &= step2_ok
        print(
            f"2. compareSetState classifies zero/one/two-plus saved ids -> {'OK' if step2_ok else 'FAIL'}"
        )

        step4_ok = (
            harness_ok
            and harness.get("full_identity") == "Beneteau Oceanis 30.1"
            and harness.get("full_build_year") == "2021"
            and harness.get("full_loa") == "9.53"
            and harness.get("full_keel") == "FIN"
            and harness.get("full_price") == "129000.00 EUR"
            and harness.get("poa_price") == "Price on application"
        )
        ok &= step4_ok
        print(
            f"4. concrete claim/offer fields render for a fully-claimed listing -> {'OK' if step4_ok else 'FAIL'}"
        )

        step5_ok = (
            harness_ok
            and harness.get("partial_build_year") == "Unknown"
            and harness.get("partial_keel") == "Unknown"
            and harness.get("partial_loa") == "Not supplied"
            and harness.get("partial_rudder") == "Not supplied"
            and harness.get("no_claims_identity_is_null") is True
            and harness.get("no_claims_build_year_is_null") is True
            and harness.get("no_claims_loa_is_null") is True
        )
        ok &= step5_ok
        print(
            "5. explicit UNKNOWN stays 'Unknown' (distinct from omitted 'Not supplied'); "
            f"no PhysicalBoat claims recorded leaves every row null, never a fallback -> {'OK' if step5_ok else 'FAIL'}"
        )

        # 1b (independent review 2026-09-19, PR #221, blocker 1): every
        # column -- available or unavailable/service-error -- produces the
        # exact same row count in the exact same order, the defining
        # property of a genuinely aligned side-by-side matrix rather than
        # independently-shaped cards.
        step_aligned_ok = (
            harness_ok
            and harness.get("row_label_count", 0) > 0
            and harness.get("full_row_values") is not None
            and len(harness.get("full_row_values", [])) == harness.get("row_label_count")
            and len(harness.get("placeholder_row_values", [])) == harness.get("row_label_count")
            and all(value == "—" for value in harness.get("placeholder_row_values", []))
            and harness.get("rows_are_aligned") is True
        )
        ok &= step_aligned_ok
        print(
            "1b. every column (available or unavailable/service-error) renders the identical "
            f"aligned row count/order -> {'OK' if step_aligned_ok else 'FAIL'}\n"
        )

        # Serve FastAPI + Astro.
        api_port = _free_port()
        web_port = _free_port()
        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = base64.urlsafe_b64encode(os.urandom(32)).decode(
            "ascii"
        )

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
        if not api_ready:
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
        web_ready = _wait_for_http(f"{web_base}/en/shortlist/compare")
        ok &= web_ready
        print(f"Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("ANONYMOUS FACTUAL SHORTLIST COMPARE RESULT -> FAIL")
            return 1

        # 3/6. the shortlist resolver (reused unchanged from SLICE-0058)
        # resolves current truth for the compare set; WITHDRAWN and
        # never-created ids render as the identical neutral unavailable
        # shape, and one unavailable entry never hides the resolvable ones.
        resolve_url = f"{web_base}/api/shortlist/resolve"
        resolve_status, resolve_body = _http_post_json(
            resolve_url,
            {
                "listing_ids": [
                    _FULL_CLAIMS_ID,
                    _PARTIAL_CLAIMS_ID,
                    _WITHDRAWN_ID,
                    _NEVER_CREATED_ID,
                ]
            },
        )
        items = resolve_body.get("items") if isinstance(resolve_body, dict) else None
        step36_ok = (
            resolve_status == 200
            and isinstance(items, list)
            and len(items) == 4
            and items[0]["native_listing_id"] == _FULL_CLAIMS_ID
            and items[0]["state"] == "available"
            and items[0]["data"]["physical_boat_claims"]["keel_configuration"]["assertion_kind"]
            == "VALUE_ASSERTION"
            and items[1]["native_listing_id"] == _PARTIAL_CLAIMS_ID
            and items[1]["state"] == "available"
            and items[1]["data"]["physical_boat_claims"]["loa_length"] is None
            and items[1]["data"]["physical_boat_claims"]["build_year"]["assertion_kind"]
            == "UNKNOWN"
            and items[2] == {"native_listing_id": _WITHDRAWN_ID, "state": "unavailable"}
            and items[3] == {"native_listing_id": _NEVER_CREATED_ID, "state": "unavailable"}
        )
        ok &= step36_ok
        print(
            "3/6. compare set resolves current truth through the existing shortlist proxy; "
            f"WITHDRAWN/never-created stay neutral unavailable, claim distinctions survive transport -> {'OK' if step36_ok else 'FAIL'}\n"
        )

        # 12/13 (independent review 2026-09-19, PR #221, blocker 3): prove
        # the compare set is sourced from the real shipped shortlist store
        # in buyer-authored order (not a hand-typed literal), that resolving
        # through Compare's own runtime seam leaves local membership
        # byte-identical, and that a later server-side offer/claim revision
        # is reflected on the next resolution while the local shortlist
        # payload itself never changes.
        before_ok, before = _run_store_sourced_harness(web_base)
        step_store_before_ok = (
            before_ok
            and before.get("ids")
            == [_FULL_CLAIMS_ID, _PARTIAL_CLAIMS_ID, _WITHDRAWN_ID, _NEVER_CREATED_ID]
            and before.get("compare_state") == "ready"
            and before.get("raw_unchanged") is True
            and before.get("full_state") == "available"
            and before.get("full_price") == _FULL_PRICE
            and before.get("partial_build_year_kind") == "UNKNOWN"
            and before.get("withdrawn_state") == "unavailable"
            and before.get("never_created_state") == "unavailable"
        )
        ok &= step_store_before_ok
        print(
            "12. compare set is sourced from the real shortlist store in buyer order; resolving "
            f"through Compare's own seam leaves local membership byte-identical -> {'OK' if step_store_before_ok else 'FAIL'}"
        )

        conn = psycopg.connect(url)
        try:
            _bump_full_price(
                conn, account=account, org=org, membership=membership, new_price=_FULL_PRICE_REVISED
            )
            _bump_partial_build_year(conn, account=account, org=org, membership=membership)
            conn.commit()
        finally:
            conn.close()

        after_ok, after = _run_store_sourced_harness(web_base)
        step_store_after_ok = (
            after_ok
            and after.get("ids") == before.get("ids")
            and after.get("raw_before") == before.get("raw_before")
            and after.get("raw_unchanged") is True
            and after.get("full_price") == _FULL_PRICE_REVISED
            and after.get("full_price") != before.get("full_price")
            and after.get("partial_build_year_kind") == "VALUE_ASSERTION"
            and after.get("partial_build_year_value") == 2022
        )
        ok &= step_store_after_ok
        print(
            "13. a later server-side offer/claim revision is reflected on the next resolution "
            f"while the stored shortlist payload stays unchanged -> {'OK' if step_store_after_ok else 'FAIL'}\n"
        )

        # 10. all five locale compare routes exist, are noindex/private, and
        # carry no saved ids in their served (pre-JS) markup.
        locales_ok = True
        for locale in _LOCALES:
            status, headers, body = _http_get(f"{web_base}/{locale}/shortlist/compare")
            headers_lower = {k.lower(): v for k, v in headers.items()}
            text = body.decode("utf-8")
            locale_ok = (
                status == 200
                and headers_lower.get("x-robots-tag") == "noindex"
                and headers_lower.get("cache-control") == "private, no-store"
                and 'name="robots" content="noindex"' in text
                and _FULL_CLAIMS_ID not in text
                and _PARTIAL_CLAIMS_ID not in text
            )
            locales_ok &= locale_ok
            print(f"    /{locale}/shortlist/compare -> {'OK' if locale_ok else 'FAIL'}")
        ok &= locales_ok

        shortlist_status, _, shortlist_body = _http_get(f"{web_base}/en/shortlist")
        shortlist_text = shortlist_body.decode("utf-8")
        step_link_ok = shortlist_status == 200 and 'href="/en/shortlist/compare"' in shortlist_text
        ok &= step_link_ok
        print(f"    /en/shortlist links to Compare -> {'OK' if step_link_ok else 'FAIL'}\n")

        # 8. ordinary Search/public-listing behavior is unaffected; Compare
        # is read-only (no shortlist mutation) since the resolver has no
        # persistence side effect. This runs after step 13's price bump, so
        # the ordinary public listing route must now reflect the revised
        # price -- the same current truth Compare itself just re-resolved,
        # proving both surfaces share the identical accepted read model
        # rather than Compare caching/diverging from it.
        listing_status, _, listing_body = _http_get(f"{api_base}/api/listings/{_FULL_CLAIMS_ID}")
        step8_ok = listing_status == 200 and f'"{_FULL_PRICE_REVISED}"'.encode() in listing_body
        ok &= step8_ok
        print(
            f"8. ordinary public listing route unaffected by this slice -> {'OK' if step8_ok else 'FAIL'}\n"
        )

        # 7. a genuine upstream outage resolves to service_error, never a
        # fabricated "unavailable"/empty result (contract §9/§13). FastAPI is
        # stopped last, since nothing further in this proof needs it.
        api_proc.terminate()
        try:
            api_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api_proc.kill()
            api_proc.wait(timeout=10)
        api_proc = None

        outage_status, outage_body = _http_post_json(
            resolve_url, {"listing_ids": [_FULL_CLAIMS_ID, _WITHDRAWN_ID]}
        )
        outage_items = outage_body.get("items") if isinstance(outage_body, dict) else None
        step7_ok = (
            outage_status == 200
            and isinstance(outage_items, list)
            and all(item["state"] == "service_error" for item in outage_items)
        )
        ok &= step7_ok
        print(
            "7. an upstream FastAPI outage resolves every requested id to service_error, "
            f"never a fabricated unavailable/empty result -> {'OK' if step7_ok else 'FAIL'}\n"
        )

        print(f"ANONYMOUS FACTUAL SHORTLIST COMPARE RESULT -> {'PASS' if ok else 'FAIL'}")
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
