# Security Attack-Surface Matrix — 2026-10 (SLICE-0078)

**Status:** RETAINED EVIDENCE
**Scope:** the coherent broker/public/owner-direct-draft product boundary accepted through SLICE-0077 — public listing, buyer contact/Lead, broker auth/Organization access, listing create/edit/publish/withdraw/reconfirm, media, Lead handling/assignment, SaleOutcome, performance snapshot.
**Format:** `asset → attacker/trust level → attack path → expected control → adversarial test/proof → finding/disposition`

Each row below is a representative case for its attacker class/domain, not an exhaustive enumeration of every route; the holistic cross-tenant sweep (row 1) additionally covers every org-scoped read surface in one proof rather than one row per route.

## 1. Cross-Organization attacker (authenticated, foreign tenant)

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Every org-scoped read route (`organizations/{org}`, `/inventory`, `/performance`, `/leads`, `/leads/counts`, `/notification-config`, `/media/library`, `/drafts`, `/inventory/{id}/edit`, `/sale-outcome`, `/media`) | Authenticated member of Org B requests Org A's `organization_id` | 404, never 200/403 leaking existence | `TestCrossTenantHolisticSweep.test_foreign_organization_id_denied_across_every_org_scoped_read_surface` | PASS — no change needed |
| Media asset, Lead (nested resource IDOR) | Own org id + another org's nested resource id (sharper IDOR shape) | 404 | `test_own_organization_id_with_foreign_media_asset_id_denied`, `test_own_organization_id_with_foreign_lead_id_denied` | PASS — no change needed |

## 2. Authenticated ordinary Account (no membership / revoked membership)

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Broker Organization context | Account holds no membership | 404 on org-scoped routes | Covered by SLICE-0053/0077 retained suites; re-exercised implicitly by every cross-tenant test above | PASS |
| Session validity vs. membership state | Membership revoked mid-session (Organization/role deliberately not embedded in the session token) | The very next request after revocation is denied | `TestSessionAdversarial.test_revoked_membership_denies_the_very_next_request_on_the_same_session` | PASS |

## 3. Broker member without required privilege / MFA

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Draft-create (role-gated, MFA-gated mutation) | Session without `mfa_satisfied` evidence attempts a privileged write | 403 `mfa_required` | `TestSessionAdversarial.test_mfa_required_role_blocked_without_mfa_evidence` | PASS |

## 4. Hostile browser input (CSRF / Origin / forged headers)

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Media upload | Missing `Origin` | 403 | `TestCsrfAdversarial.test_missing_origin_rejected_on_media_upload` | PASS |
| Media upload | Forged cross-site `Origin` | 403 | `test_forged_origin_rejected_on_media_upload` | PASS |
| Media upload | Valid CSRF header minted for a *different* write channel (buyer-lead) replayed | 403 — channel-specific header value, never generically accepted | `test_cross_channel_csrf_header_replay_rejected` | PASS |
| Broker logout | Bare cross-site-shaped POST (no CSRF header) | 403, session unaffected | `test_logout_without_csrf_header_rejected` (backend) + `test_logout_without_csrf_header_is_rejected_and_session_survives` (`test_broker_workspace_access_api.py`) | **SEC-0078-01 — FIXED this slice**: logout previously had no CSRF discipline at all (a bare browser `<form>` POST straight to FastAPI). Added `_require_logout_csrf` (exact-Origin + fixed header, mirroring every other mutating channel) plus an Astro same-origin proxy (`web/src/pages/broker/logout.ts`) so the browser never needs to set a custom header itself. |
| Broker logout | Correct Origin + correct CSRF header | 200, session cleared | `test_logout_with_correct_csrf_header_succeeds_and_clears_session` | PASS |

## 5. Unauthenticated session/token forgery

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Session cookie | Tampered signature byte | 401 | `TestSessionAdversarial.test_tampered_signature_rejected` | PASS |
| Session cookie | Signed with a different (wrong) secret | 401 | `test_wrong_secret_signature_rejected` | PASS |
| Session cookie | Expired token (TTL elapsed) | 401 | `test_expired_token_rejected` | PASS |

## 6. Buyer/public — abuse and malformed/oversized input

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| `/api/listings/{id}/contact` | Unbounded repeated submissions (Lead spam / enumeration) | Bounded fixed-window rate limit (5/5min), 429 | `TestRateLimitingAdversarial.test_contact_route_blocks_after_its_bounded_window` | **SEC-0078-02 — FIXED this slice**: no bound previously existed. Added `FixedWindowRateLimiter` (`hullq.security.rate_limit`). |
| `/api/auth/login` | Repeated login-flow initiation (auth-flow abuse) | Bounded (20/5min), 429 | `test_login_route_blocks_after_its_bounded_window` | **SEC-0078-02 — FIXED** (same mechanism, separate budget) |
| `/media/images` upload | Repeated per-account uploads (storage-cost abuse) | Bounded (30/hour, keyed by account), 429 | `test_media_upload_route_blocks_after_its_bounded_window` | **SEC-0078-02 — FIXED** (same mechanism, separate budget) |
| All three limiters | One category's traffic exhausts another's budget | Independent per-category budgets | `test_rate_limit_keys_are_independent_across_route_categories` | PASS (new control, verified independent) |
| `FixedWindowRateLimiter`'s own retained state | Unauthenticated attacker (contact/login routes require no auth) sends traffic from many distinct `request.client.host` values (e.g. IPv6 prefix rotation, no botnet required) to grow retained per-key state without bound — the mitigation for abuse becoming a new unbounded-memory DoS vector itself | Hard-capped LRU-evicted retained state (`max_keys`, default 10,000), with proactive reclaim of expired/inactive keys so memory shrinks back down, not merely caps | `tests/unit/test_rate_limit_unit.py::TestBoundedRetainedState` (5 tests: ordinary counting unchanged, expired-key reclaim, hard-cap under unique-key flood, active-key survival under eviction pressure, category independence preserved) | **SEC-0078-09 — FOUND by independent review, FIXED this amendment.** See `SECURITY_FINDINGS_REGISTER_2026-10.md`. |
| Contact body | SQL-injection-shaped text in free-text fields | Stored/returned literally via parameterized queries; never executed as SQL | `TestInputAndMediaAbuseAdversarial.test_sql_injection_shaped_text_round_trips_literally_and_safely` | PASS |
| Contact body | Malformed JSON / non-object JSON | 400, no crash | `test_malformed_json_body_rejected_cleanly`, `test_non_object_json_body_rejected` | PASS |
| Contact body | Declared size over the bound (padding field) | 413 before any field-level validation | `test_oversized_declared_content_length_rejected_before_body_read` | PASS |

## 7. Media / object-storage boundary

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Upload pipeline | Decompression-bomb-shaped PNG (huge declared pixel count, small wire size) | 422 `REJECTED` before full decode | `test_decompression_bomb_image_rejected_through_live_upload_route` | PASS |
| Upload pipeline | Forged bytes claiming to be an image, no/incorrect `Content-Type`, server never trusts client-declared type | 422 `REJECTED` | `test_forged_bytes_claiming_to_be_an_image_rejected` | PASS |

## 8. Response/transport hardening (XSS/framing/cache/transport)

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Every FastAPI response | No baseline `X-Content-Type-Options` / `X-Frame-Options` / CSP / `Permissions-Policy` existed on routes outside the few path-scoped header dicts (e.g. media-bytes, upload, lead-ops, draft, sale-outcome, performance) | Baseline strict headers (`default-src 'none'`, `frame-ancestors 'none'`) on every response | `TestSecurityHeadersAdversarial.test_baseline_headers_present_on_public_route`, `test_baseline_headers_present_on_authenticated_broker_route` | **SEC-0078-03 — FIXED this slice**: added `_BASELINE_SECURITY_RESPONSE_HEADERS`, merged on every response ahead of path-scoped overrides. |
| Session cookie transport | HSTS asserted even when cookies are not configured `Secure` (local/CI HTTP) | HSTS only when `HULLQ_SESSION_COOKIE_SECURE`-equivalent production config is active | `test_hsts_absent_when_cookies_not_configured_secure`, `test_hsts_present_once_cookies_are_configured_secure` | PASS (new control, conditioned correctly) |
| Every Astro web response | No centralized security-header enforcement existed in `web/` at all — each page only set its own `Cache-Control`/`X-Robots-Tag` individually | CSP/`X-Frame-Options`/`X-Content-Type-Options`/`Permissions-Policy`/HSTS(HTTPS) on every response, without disturbing existing per-page cache/robots headers | `web/src/middleware.ts` added; verified live via built production server (`npm run build` + `node dist/server/entry.mjs`), headers observed on `/broker` and `/en/search` responses | **SEC-0078-04 — FIXED this slice**. No dedicated unit test: `astro:middleware`'s `defineMiddleware` is a virtual-module import not resolvable under plain `node --test`; proof is the live-server header capture plus `astro check` (0 errors) covering the file's type correctness. |

## 9. Infrastructure / supply-chain

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Python runtime dependencies | Known-vulnerable transitive package | `uv run pip-audit` clean in CI (`dependency-audit` job, pre-existing) | Re-run locally this slice: "No known vulnerabilities found" | PASS |
| Web (`npm`) runtime/build dependencies | Known-vulnerable transitive package | `npm audit` in CI (new `Audit web dependencies` step) | `npm audit --audit-level=critical`: 0 critical. One HIGH (`http-cache-semantics` via `astro`'s remote-image cache-policy module) remains, with no patched release published at any version and no reachable call site in HullQ's code (`web/src` has zero `astro:assets`/`<Image>`/`getImage()` usage) | **SEC-0078-07 — GENUINELY_OPEN, Project-Owner risk-acceptance pending.** See `SECURITY_FINDINGS_REGISTER_2026-10.md`. |

## 10. Privacy / PII / logging

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Application-level logging | Buyer/broker PII (name/email/message) written to application logs | No application-level logging statements exist in `hullq.api.app` that touch request bodies | Verified by inspection: `hullq/api/app.py` contains no `logging`/`logger`/`print` call sites at all | PASS (nothing to fix); access-log format/retention is a deployment-configuration concern under ADR-0010, not in this slice's required outputs beyond this note |

## 11. Deployment / infrastructure configuration

| Asset | Attack path | Expected control | Proof | Disposition |
|---|---|---|---|---|
| Session cookie | Cookie served without `Secure`/`__Host-` in production | `HULLQ_SESSION_COOKIE_SECURE` default-on behavior, `__Host-`-prefixed cookie | Pre-existing SLICE-0053/independent-review coverage (`test_broker_workspace_access_api.py::secure_client` fixture) — re-run clean this slice | PASS, no regression |
| HTTPS transport | HSTS not asserted once TLS-terminated cookies are configured | Asserted (see row 8) | Covered above | PASS |
