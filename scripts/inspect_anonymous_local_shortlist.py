"""SLICE-0058 anonymous local shortlist owner-visible end-to-end proof.

Executes the committed anonymous-local-shortlist vertical against a real,
disposable PostgreSQL 18 schema and real local HTTP servers (FastAPI + built
Astro/Node SSR), per `specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md` §16:

    1. a current ACTIVE public listing exists and its ordinary public
       API/web routes behave exactly as SLICE-0049 already accepted
    2. explicit anonymous add: the real shipped `shortlistStore.ts` module
       (run under Node, not reimplemented in Python) records buyer-authored
       membership only on an explicit add call
    3. browser-local ID-only persistence: the raw stored representation
       carries only `version`/`listing_ids`, never a listing-truth field
    4. the shortlist resolves current listing data through the same-origin
       Astro proxy (`/api/shortlist/resolve`), which delegates every id to
       FastAPI's already-accepted public listing read route
    5. current truth is re-resolved live, not read from any stored browser
       payload: withdrawing the listing server-side and repeating the exact
       same resolve request changes its result, proving there is no client
       cache standing in for FastAPI truth
    6. explicit remove drops only the removed id; a repeat remove is
       idempotent
    7. an unavailable saved id (WITHDRAWN, and a never-created id) renders
       through the identical neutral "unavailable" shape -- and remains
       saved in local membership until the buyer explicitly removes it
    8. ordinary Search/public-listing behavior is unaffected by this slice
    9. no account/database shortlist persistence exists (no `*shortlist*`
       table appears in the schema) -- and a genuine upstream/API outage
       resolves every requested id to `"service_error"`, never a fabricated
       "unavailable"/empty result
    10. finish with `ANONYMOUS LOCAL SHORTLIST RESULT -> PASS`

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance), a
pre-built Astro web package (``cd web && npm ci && npm run build``) and a
``node`` executable on PATH capable of running TypeScript directly (Node 23.6+/24,
matching ``web/package.json``'s own ``npm test`` convention).

Run: uv run python scripts/inspect_anonymous_local_shortlist.py
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
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"
SHORTLIST_STORE_MODULE = WEB_DIR / "src" / "lib" / "shortlistStore.ts"

_AVAILABLE_ID = "NL-0058-AVAILABLE"
_WITHDRAWN_ID = "NL-0058-WITHDRAWN"
_NEVER_CREATED_ID = "NL-0058-NEVER-CREATED"
_AVAILABLE_PRICE = "89000.00"

_STORE_HARNESS_SCRIPT = """
import { pathToFileURL } from "node:url";

const [, , storeModulePath, availableId, withdrawnId] = process.argv;
const store = await import(pathToFileURL(storeModulePath).href);

class FakeStorage {
  constructor() { this.data = new Map(); }
  getItem(key) { return this.data.has(key) ? this.data.get(key) : null; }
  setItem(key, value) { this.data.set(key, value); }
}

const storage = new FakeStorage();
const out = {};

out.initial_empty = store.loadShortlistIds(storage);

out.after_add_available = store.addToShortlist(storage, availableId);
out.after_add_withdrawn = store.addToShortlist(storage, withdrawnId);
out.after_duplicate_add = store.addToShortlist(storage, availableId);

const raw = storage.getItem(store.SHORTLIST_STORAGE_KEY);
out.raw_keys = Object.keys(JSON.parse(raw)).sort();

out.after_remove_available = store.removeFromShortlist(storage, availableId);
out.after_remove_available_again = store.removeFromShortlist(storage, availableId);

out.final = store.loadShortlistIds(storage);

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
    preserve one layer down (contract §13)."""
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
            broker_description="SLICE-0058 proof fixture listing.",
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


def _run_store_harness() -> tuple[bool, dict[str, Any]]:
    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0058_store_harness_"))
    harness_path = log_dir / "shortlist_store_harness.mjs"
    harness_path.write_text(_STORE_HARNESS_SCRIPT, encoding="utf-8")
    try:
        result = subprocess.run(
            ["node", str(harness_path), str(SHORTLIST_STORE_MODULE), _AVAILABLE_ID, _WITHDRAWN_ID],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
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
        print(f"store harness produced non-JSON stdout: {result.stdout!r}", file=sys.stderr)
        return False, {}


def _table_names_matching(conn: Any, needle: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name ILIKE %s",
            [f"%{needle}%"],
        )
        return [row[0] for row in cur.fetchall()]


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1
    if not SHORTLIST_STORE_MODULE.exists():
        print(f"{SHORTLIST_STORE_MODULE} does not exist.", file=sys.stderr)
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0058e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0058_e2e_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("ANONYMOUS LOCAL SHORTLIST\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("Alembic upgraded to single current head -> OK\n")

        account = AccountId("ACC-0058-E2E")
        org = _org("ORG-0058-E2E")
        membership = _membership("OM-0058-E2E", account, org)

        conn = psycopg.connect(url)
        try:
            _create_and_publish(
                conn,
                listing_id=_AVAILABLE_ID,
                physical_boat_id="PB-0058-AVAILABLE",
                market_episode_id="ME-0058-AVAILABLE",
                offer_revision_id="REV-0058-AVAILABLE",
                account=account,
                org=org,
                membership=membership,
                asking_price=_AVAILABLE_PRICE,
            )
            _create_and_publish(
                conn,
                listing_id=_WITHDRAWN_ID,
                physical_boat_id="PB-0058-WITHDRAWN",
                market_episode_id="ME-0058-WITHDRAWN",
                offer_revision_id="REV-0058-WITHDRAWN",
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
                "1. one current ACTIVE listing + one WITHDRAWN listing fixture created -> "
                f"{'OK' if step1_ok else 'FAIL'}\n"
            )

            no_shortlist_tables = _table_names_matching(conn, "shortlist")
            conn.commit()
            step9a_ok = no_shortlist_tables == []
            ok &= step9a_ok
            print(
                f"9a. no *shortlist* table exists in the schema -> {'OK' if step9a_ok else 'FAIL'}"
            )
        finally:
            conn.close()

        if not ok:
            print("ANONYMOUS LOCAL SHORTLIST RESULT -> FAIL")
            return 1

        # 2/3/6/7 (partial): explicit anonymous add, ID-only local
        # persistence, explicit remove, an unavailable id remains saved --
        # exercised against the real shipped `shortlistStore.ts` module
        # under Node, not a Python reimplementation of its logic.
        harness_ok, harness = _run_store_harness()
        step23_ok = (
            harness_ok
            and harness.get("initial_empty") == []
            and harness.get("after_add_available") == [_AVAILABLE_ID]
            and harness.get("after_add_withdrawn") == [_AVAILABLE_ID, _WITHDRAWN_ID]
            and harness.get("after_duplicate_add") == [_AVAILABLE_ID, _WITHDRAWN_ID]
            and harness.get("raw_keys") == ["listing_ids", "version"]
        )
        ok &= step23_ok
        print(
            "2/3. explicit anonymous add (idempotent) + raw storage carries only "
            f"version/listing_ids -> {'OK' if step23_ok else 'FAIL'}"
        )
        step67_ok = (
            harness_ok
            and harness.get("after_remove_available") == [_WITHDRAWN_ID]
            and harness.get("after_remove_available_again") == [_WITHDRAWN_ID]
            and harness.get("final") == [_WITHDRAWN_ID]
        )
        ok &= step67_ok
        print(
            "6/7. explicit remove (idempotent on retry); the other saved id remains "
            f"in local membership -> {'OK' if step67_ok else 'FAIL'}\n"
        )

        # Serve FastAPI + Astro.
        api_port = _free_port()
        web_port = _free_port()
        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        # FastAPI's app factory unconditionally requires a preview signing
        # secret (SLICE-0048); this proof never exercises the preview route,
        # but the app cannot start without one.
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
        web_ready = _wait_for_http(f"{web_base}/listings/{_NEVER_CREATED_ID}")
        ok &= web_ready
        print(f"Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("ANONYMOUS LOCAL SHORTLIST RESULT -> FAIL")
            return 1

        # 8. ordinary Search/public-listing behavior is unaffected.
        listing_status, _, listing_body = _http_get(f"{api_base}/api/listings/{_AVAILABLE_ID}")
        search_status, _, search_body = _http_get(f"{api_base}/api/search/en")
        step8_ok = (
            listing_status == 200
            and f'"{_AVAILABLE_PRICE}"'.encode() in listing_body
            and search_status == 200
            and b'"active_requirement":null' in search_body
        )
        ok &= step8_ok
        print(
            f"8. ordinary public listing/Search routes unaffected by this slice -> "
            f"{'OK' if step8_ok else 'FAIL'}"
        )

        # The public listing page itself renders the new add/remove control.
        page_status, _, page_body = _http_get(f"{web_base}/listings/{_AVAILABLE_ID}")
        page_text = page_body.decode("utf-8")
        step_button_ok = (
            page_status == 200
            and "data-shortlist-toggle" in page_text
            and f'data-native-listing-id="{_AVAILABLE_ID}"' in page_text
            and "Save to shortlist" in page_text
        )
        ok &= step_button_ok
        print(
            f"    public listing page renders the shortlist add/remove control -> "
            f"{'OK' if step_button_ok else 'FAIL'}\n"
        )

        # 1 (localized surfaces): all five /{locale}/shortlist pages exist,
        # are noindex and never cached.
        locales_ok = True
        for locale in ("en", "de", "fr", "pt", "es"):
            status, headers, body = _http_get(f"{web_base}/{locale}/shortlist")
            headers_lower = {k.lower(): v for k, v in headers.items()}
            locale_ok = (
                status == 200
                and headers_lower.get("x-robots-tag") == "noindex"
                and headers_lower.get("cache-control") == "private, no-store"
                and 'name="robots" content="noindex"' in body.decode("utf-8")
            )
            locales_ok &= locale_ok
            print(f"    /{locale}/shortlist -> {'OK' if locale_ok else 'FAIL'}")
        ok &= locales_ok
        print()

        # 4/5/7. the shortlist resolves current truth through the same-origin
        # proxy; mixing an available, a withdrawn and a never-created id in
        # one request proves non-enumeration and that one unavailable entry
        # never hides a resolvable one. A duplicate id is included to prove
        # the proxy's own defensive de-duplication.
        resolve_url = f"{web_base}/api/shortlist/resolve"
        resolve_status, resolve_body = _http_post_json(
            resolve_url,
            {"listing_ids": [_AVAILABLE_ID, _WITHDRAWN_ID, _NEVER_CREATED_ID, _AVAILABLE_ID]},
        )
        items = resolve_body.get("items") if isinstance(resolve_body, dict) else None
        step4_ok = (
            resolve_status == 200
            and isinstance(items, list)
            and len(items) == 3
            and items[0]["native_listing_id"] == _AVAILABLE_ID
            and items[0]["state"] == "available"
            and items[0]["data"]["asking_price_amount"] == _AVAILABLE_PRICE
            and items[1] == {"native_listing_id": _WITHDRAWN_ID, "state": "unavailable"}
            and items[2] == {"native_listing_id": _NEVER_CREATED_ID, "state": "unavailable"}
        )
        ok &= step4_ok
        print(
            "4/7. shortlist proxy resolves current truth; WITHDRAWN and never-created "
            f"ids render as the identical neutral unavailable shape -> {'OK' if step4_ok else 'FAIL'}"
        )

        # 5. re-resolve after a server-side state change: withdraw the
        # previously-available listing and repeat the exact same request.
        conn = psycopg.connect(url)
        try:
            re_withdraw = withdraw_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_AVAILABLE_ID),
            )
        finally:
            conn.close()
        step5_pre_ok = re_withdraw.status is LifecycleTransitionStatus.TRANSITIONED
        resolve_status_2, resolve_body_2 = _http_post_json(
            resolve_url, {"listing_ids": [_AVAILABLE_ID]}
        )
        items_2 = resolve_body_2.get("items") if isinstance(resolve_body_2, dict) else None
        step5_ok = (
            step5_pre_ok
            and resolve_status_2 == 200
            and isinstance(items_2, list)
            and items_2 == [{"native_listing_id": _AVAILABLE_ID, "state": "unavailable"}]
        )
        ok &= step5_ok
        print(
            "5. current truth is re-resolved live (withdrawing server-side flips the "
            f"same saved id to unavailable on the next resolve) -> {'OK' if step5_ok else 'FAIL'}\n"
        )

        # 9b. a genuine upstream outage resolves to service_error, never a
        # fabricated "unavailable"/empty result (contract §13). FastAPI is
        # stopped last, since nothing further in this proof needs it.
        api_proc.terminate()
        try:
            api_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api_proc.kill()
            api_proc.wait(timeout=10)
        api_proc = None

        outage_status, outage_body = _http_post_json(
            resolve_url, {"listing_ids": [_WITHDRAWN_ID, _NEVER_CREATED_ID]}
        )
        outage_items = outage_body.get("items") if isinstance(outage_body, dict) else None
        step9b_ok = (
            outage_status == 200
            and isinstance(outage_items, list)
            and all(item["state"] == "service_error" for item in outage_items)
        )
        ok &= step9b_ok
        print(
            "9b. an upstream FastAPI outage resolves every requested id to "
            f"service_error, never a fabricated unavailable/empty result -> "
            f"{'OK' if step9b_ok else 'FAIL'}\n"
        )

        print(f"ANONYMOUS LOCAL SHORTLIST RESULT -> {'PASS' if ok else 'FAIL'}")
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
