# Security Adversarial Evidence — 2026-10 (SLICE-0078)

**Status:** RETAINED EVIDENCE
**Basis:** live adversarial E2E proof against the real FastAPI app (`hullq.api.app.create_app`) and the real Astro web package, not a scanner-only pass.

## 1. New holistic adversarial backend suite

`tests/persistence/test_security_hardening_adversarial_api.py` — exercises the actual accepted HTTP flows (buyer contact, broker login/logout, Organization-scoped reads/writes, media upload) through Starlette's `TestClient` against a real PostgreSQL schema-isolated database per test.

```text
uv run python scripts/workflow/claude_diag.py run-local-test-db-compact scripts/run_pytest_local.py \
  tests/unit/test_rate_limit_unit.py \
  tests/persistence/test_security_hardening_adversarial_api.py -q

34 passed
```

Covers: cross-tenant holistic IDOR sweep (3 tests), session/MFA/revocation adversarial proof (5), CSRF/Origin adversarial proof including the new logout channel (6), bounded abuse-rate protection (4), baseline security response headers (4), input/media abuse (6), plus 6 unit tests for the new `FixedWindowRateLimiter`.

## 2. Affected-surface regression (pre-existing suites, re-run for this slice's changes)

The new rate limiting, baseline response headers, and logout CSRF discipline touch shared middleware/response paths used by every existing broker/lead/media/owner-direct route. Re-ran the full affected set:

```text
tests/persistence/test_broker_workspace_access_api.py
tests/persistence/test_broker_inventory_editing_api.py
tests/persistence/test_broker_inventory_lifecycle_api.py
tests/persistence/test_broker_inventory_read_api.py
tests/persistence/test_broker_performance_api.py
tests/persistence/test_broker_sale_outcome_api.py
tests/persistence/test_broker_lead_operations_api.py
tests/persistence/test_buyer_lead_api.py
tests/persistence/test_lead_provenance_flow_api.py
tests/persistence/test_media_gallery_api.py
tests/persistence/test_owner_direct_draft_api.py

14 + 235 = 249 passed (two batches; see Findings)
```

**Finding during this run, fixed in-slice:** `test_broker_workspace_access_api.py::TestBrokerWorkspaceAccessVertical::test_logout_clears_session` failed with an unhandled `RuntimeError` (`HULLQ_WEB_ORIGIN is not set or empty`) because the newly added `_require_logout_csrf` calls `_resolve_web_origin()`, and this test file's `create_app()` fixture never configured a web origin (logout previously needed none). Fixed by passing `web_origin=_WEB_ORIGIN` into that file's `_build_client`/`create_app()` call and updating the test to send the fixed CSRF header/Origin; added a companion `test_logout_without_csrf_header_is_rejected_and_session_survives` test. Re-run after the fix: 14 passed, 0 failed.

## 3. Web (TypeScript/Astro) verification

```text
npm run check --prefix web
Result (111 files): 0 errors, 0 warnings, 0 hints

node --test web/src/lib/__tests__/*.test.ts
tests 362, pass 362, fail 0
```

362 = 359 pre-existing + 3 new (`logoutProxy.test.ts`, added this slice to cover the previously-untested `web/src/pages/broker/logout.ts` proxy: CSRF-header injection, Cookie/Origin forwarding, Set-Cookie relay, unreachable-upstream 502).

**Finding during this run, fixed in-slice:** `web/src/pages/broker/logout.ts` imported `brokerApi` without the explicit `.ts` extension this repository's other proxy routes use for Node ESM resolution (e.g. `contact.ts` imports `../../../lib/buyerLeadApi.ts`). Astro/Vite's own resolver tolerated it (the production `npm run build` succeeded either way), but it broke `node --test`'s plain ESM resolution. Fixed for convention-consistency; re-verified with `npm run check` (clean) and a fresh `npm run build` (clean).

`web/src/middleware.ts` (the new baseline security-header middleware) imports from the virtual module `astro:middleware`, which plain `node --test` cannot resolve without Astro's Vite plugin — no unit test was added for it; see §4 for its live proof instead.

## 2a. Remote CI caught two more regressions local targeted runs missed

The first push's `db integration` job (the full backend suite plus real-multi-process-HTTP vertical-proof scripts, which this slice's local validation deliberately does not re-run in full per `CLAUDE.md`'s affected-surface default) failed on two items neither the new adversarial suite nor the affected-surface regression list reached:

1. `tests/persistence/test_public_listing_read_api.py::test_active_listing_response_has_noindex_header_and_no_preview_confidentiality` — asserted `Referrer-Policy` absent on the public listing route, now obsolete since SEC-0078-03 made it universal. Fixed: updated the assertion, added a dedicated baseline-headers test for this route.
2. `scripts/inspect_broker_workspace_access.py` (step 15, a real FastAPI+Astro+OIDC-issuer multi-process HTTP vertical proof, not pytest) posted directly to `/api/auth/logout` with no CSRF header/Origin and no `HULLQ_WEB_ORIGIN` configured for its subprocess — same gap class as the SEC-0078-05 pytest fixture, in a script this slice's test-file regression sweep never touches. Fixed: added `HULLQ_WEB_ORIGIN` to the script's FastAPI subprocess env; changed the logout call to go through `{web_base}/broker/logout` (Astro's proxy) with an explicit `Origin` header, matching what the fixed `web/src/pages/broker/index.astro` form now actually does.

Both fixes verified locally (`test_public_listing_read_api.py`: 12 passed; `inspect_broker_workspace_access.py`: full proof PASS, all 15 contract steps OK) and pushed as a follow-up commit. Full detail: `SECURITY_FINDINGS_REGISTER_2026-10.md` SEC-0078-08.

## 2b. Review-fix amendment — bounded rate-limiter retained state (SEC-0078-09)

Independent review of the merged candidate (exact-head `d8d0fd8`) found that `FixedWindowRateLimiter` retained one dict entry per distinct key forever, reclaimed only if that exact key happened to be observed again after expiry — an unauthenticated attacker able to generate many distinct `request.client.host` values (no botnet needed: IPv6 prefix rotation from one host) could grow retained state without bound against the contact/login limiters. Rewrote `src/hullq/security/rate_limit.py` to cap retained state at `max_keys` (default 10,000) via an LRU-ordered `OrderedDict`, reclaiming expired entries proactively and evicting only the coldest entry under cardinality pressure.

```text
uv run python -m pytest tests/unit/test_rate_limit_unit.py -q
13 passed
```

(6 pre-existing + 1 new construction-validation + 5 new `TestBoundedRetainedState` tests: ordinary counting unchanged, expired-key reclaim, hard-cap under unique-key flood, active-key survives eviction pressure, category independence preserved.)

```text
uv run python scripts/workflow/claude_diag.py run-local-test-db-compact scripts/run_pytest_local.py \
  tests/unit/test_rate_limit_unit.py \
  tests/persistence/test_security_hardening_adversarial_api.py -q
40 passed

uv run python scripts/workflow/claude_diag.py run-local-test-db-compact scripts/run_pytest_local.py \
  tests/persistence/test_security_hardening_adversarial_api.py::TestRateLimitingAdversarial -v
4 passed (all 4 route-level rate-limiting adversarial tests re-verified against the new implementation)

uv run python scripts/validate_repository.py
repository governance validation: PASS
```

Full detail: `SECURITY_FINDINGS_REGISTER_2026-10.md` SEC-0078-09.

## 4. Live production-server header proof (`web/src/middleware.ts`)

```text
npm run build --prefix web        # clean build
node web/dist/server/entry.mjs    # standalone Node server, background, port 4321

curl -sI http://127.0.0.1:4321/en/search
curl -sI http://127.0.0.1:4321/broker
```

Both responses carried, on every route regardless of that route's own `Cache-Control`/`X-Robots-Tag` policy:

```text
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'
permissions-policy: geolocation=(), camera=(), microphone=(), payment=(), usb=()
x-content-type-options: nosniff
x-frame-options: DENY
```

(`/broker` additionally carried its own pre-existing `cache-control: private, no-store`, confirming the middleware adds headers without disturbing page-specific ones.) The `/en/search` 503 is the expected result of the FastAPI backend not running in this smoke check — irrelevant to header presence. Server stopped after the check.

## 5. Dependency / supply-chain review

```text
uv run pip-audit
No known vulnerabilities found (hullq itself is unpublished/unauditable, expected)

npm audit --audit-level=critical --prefix web
0 critical findings (exit 0)
```

One HIGH remains open at the `npm audit` raw-advisory level; disposition and reasoning are in `SECURITY_FINDINGS_REGISTER_2026-10.md` (SEC-0078-07). The CI step (`.github/workflows/ci.yml`, "Audit web dependencies") was set to `--audit-level=critical` rather than `high` for exactly this reason — not pushed/observed on GitHub Actions yet; see gate evidence.
