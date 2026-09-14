# SLICE-0053 — Acceptance closure

**Slice:** SLICE-0053  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #196  
**Original implementation HEAD:** `a7fee1a0c4252132c1af578b75711a0127fced17`  
**First amended HEAD:** `97774960c62ef169ff5f5a81e38f596d750f69ce`  
**Accepted implementation HEAD:** `784c035d93c2ce68304278e3d6e916b64a05bd5c`  
**Implementation merge commit:** `2644d537fac82aa4c7f520df2c69d393c6907b0e`  
**Owner acceptance:** explicitly recorded 2026-09-14

## Accepted capability

SLICE-0053 adds HullQ's first authenticated professional Broker Workspace access vertical:

```text
Auth0-compatible authenticated external identity
→ durable provider-agnostic HullQ Account
→ durable HullQ Organization / Membership / roles
→ server-side FastAPI tenant authorization
→ protected Astro Broker Workspace landing
```

The slice implements the access/identity/tenant boundary only. It does not introduce broker listing CRUD, media, leads, sales/outcomes, analytics, payments, self-service Organization administration or a real external broker pilot.

Direct requirements completed by this slice:

```text
REQ-BROKER-014 — Organization/team context is first-class
REQ-BROKER-015 — authentication does not own authorization truth
```

`REQ-BROKER-001` remains broader Broker Workspace product context and is not completed by this slice alone.

## Authentication / identity boundary

Accepted identity chain:

```text
validated (provider, issuer, subject)
→ AuthIdentity
→ immutable HullQ AccountId
```

Auth0 remains authentication-only. It is not authoritative for HullQ Organizations, membership, marketplace roles, publishing eligibility, listing ownership, verification, moderation or entitlements. Email is not an immutable identity key and is not used to auto-link identities.

First valid authentication may JIT-create one Account plus AuthIdentity mapping. Persistence uses the unique external-identity tuple and a PostgreSQL transaction-scoped advisory lock so retries/concurrent first logins converge on one mapping without orphan Account rows.

## Durable actor directory

The accepted migration adds normalized durable state for `accounts`, `auth_identities`, `marketplace_organizations`, `organization_memberships` and `organization_membership_roles`.

The schema supports multiple Organizations per Account, multiple Accounts per Organization, multiple roles per membership, ACTIVE/INACTIVE membership state and unique `(provider, issuer, subject)` authentication identity mapping.

The migration deliberately adds no unconditional retroactive foreign keys from the pre-existing `native_listings.created_by_account_id` or `native_listings.publishing_organization_id` columns. Existing accepted historical/synthetic actor IDs therefore remain migration-compatible.

## Authorization and tenant isolation

FastAPI/domain code remains the sole authorization owner. The HullQ browser session carries authentication/account evidence only and does not embed Organization membership or role truth. Each Organization-scoped request reads current HullQ membership state again.

Accepted Organization access behavior:

```text
missing membership OR INACTIVE membership → denied
ACTIVE MEMBER-only membership → workspace allowed without privileged MFA
ACTIVE PUBLISHER / OWNER / ADMIN membership → validated MFA required
```

Unknown Organizations and unauthorized existing Organizations collapse to the same non-enumerating external failure shape. Astro remains presentation/navigation only and obtains Account/Organization context through FastAPI.

## OIDC and session security

The accepted authorization-code adapter validates RS256 allowlisting, configured JWKS signing key/signature, exact issuer, correct audience/client ID, expiry/time claims, subject, OIDC nonce and callback `state` binding. Inadmissible authentication fails closed before broker data is returned.

The browser session contains no Organization roles/memberships and has a bounded lifetime. Provider tokens and secrets are not stored in ordinary browser JavaScript storage.

### Cookie hardening accepted during review

Independent review identified that host-only cookies alone were insufficient against sibling-subdomain cookie injection/cookie tossing. The accepted implementation therefore combines:

1. production `__Host-` authentication/session cookie names with `Secure`, `Path=/` and no `Domain`;
2. an HMAC-signed, canonical-base64url login-state payload.

Local plain-HTTP deterministic testing uses explicit `HULLQ_SESSION_COOKIE_SECURE=false`; this is not the production default. Personalized FastAPI and Astro Broker Workspace responses use `Cache-Control: private, no-store` and are noindex.

## Current session-topology invariant

Because the production session cookie is host-only, browser-visible FastAPI auth/callback and Astro Broker Workspace must share the same hostname under the current SLICE-0053 architecture. Ports may differ and a same-host reverse-proxy topology is valid.

Cross-host configuration such as `api.hullq.com` for callback versus `hullq.com` for `/broker` fails closed through `SessionTopologyError`. Any future cross-host session architecture requires its own reviewed change.

## Privileged MFA / Auth0 step-up

Privileged roles remain:

```text
PUBLISHER
OWNER
ADMIN
→ validated MFA required
```

HullQ requests step-up with:

```text
http://schemas.openid.net/pape/policies/2007/06/multi-factor
```

The Auth0 tenant must react through configured Post-Login Action logic. HullQ trusts only signed ID-token authentication-strength evidence (`amr` containing `mfa`), never Auth0 roles/Organizations/app metadata as HullQ authorization truth.

The repository's Action note is deployment guidance, not an executed real-tenant integration; current Auth0 documentation must be rechecked when that tenant Action is deployed.

## Browser-visible states

The accepted minimal workspace demonstrates unauthenticated login-only behavior, a safe no-membership state, authorized Organization selection, non-enumerating cross-Organization denial, privileged MFA blocking/step-up, successful MFA-gated workspace entry and logout/session invalidation.

## Retained deterministic proof

The retained vertical is:

```text
local deterministic OIDC/JWKS issuer
→ real authorization-code/token/JWKS validation
→ FastAPI
→ real PostgreSQL 18 actor/authorization state
→ built Astro SSR Broker Workspace
```

The final amendment replaced the former hand-rolled cookie dictionary with `http.cookiejar.CookieJar` + `HTTPCookieProcessor`, exercising normal host/domain/path/Secure/expiry/deletion semantics. The issuer runs on distinct loopback host `127.0.0.2`; HullQ API/web use `127.0.0.1`, and the proof verifies HullQ cookies are not sent to the issuer.

Production `__Host-` storage behavior requires a real HTTPS browser and is verified here through exact production `Set-Cookie` wire-shape tests rather than by falsely replaying Secure cookies over HTTP. Real HTTPS/reverse-proxy deployment remains production-readiness work.

## Independent review history

Original handoff:

```text
a7fee1a0c4252132c1af578b75711a0127fced17
```

First review found cookie hardening, Auth0 MFA ACR and Astro cache-control defects. Review ID: `5199424861`.

First amended head:

```text
97774960c62ef169ff5f5a81e38f596d750f69ce
```

Second review accepted those fixes but found the retained proof's non-browser cookie replay, required explicit same-host topology and corrected Auth0 Action guidance. Review ID: `5201187761`.

Final amended head:

```text
784c035d93c2ce68304278e3d6e916b64a05bd5c
```

Fresh exact-head review returned `ACCEPT`, review ID `5201868161`. The Project Owner explicitly accepted that exact implementation on 2026-09-14.

## Exact-head verification

Remote verification on exact accepted HEAD `784c035d93c2ce68304278e3d6e916b64a05bd5c`:

```text
CI run 34885240631 → SUCCESS
Manufacturer artifact reproducibility run 34885240626 → SUCCESS
```

Final implementation-agent validation reported:

```text
full pytest: 4994 passed / 3 skipped / 0 failed
branch coverage: 93.08% (>= 90%)
ruff format --check: PASS
ruff check: PASS
mypy src: PASS
web check/build/tests: PASS
repository governance validation: PASS
retained broker workspace access proof: PASS
```

PR #196 merged that exact owner-accepted head to `main` as:

```text
2644d537fac82aa4c7f520df2c69d393c6907b0e
```

## Scope retained / explicitly deferred

SLICE-0053 deliberately does not add listing CRUD/publish/reconfirm UI/API, Organization self-service/staff administration, broker verification, media, broker-branding completion, connectivity-resilient drafts, leads/CRM/attribution, sale/outcome workflow, Search-fit/exclusion/demand analytics, bulk import/export, Saved Search/alerts, payments, broad SEO, production operations or a real broker pilot.

`REQ-BROKER-023` broker identity/branding and `REQ-BROKER-024` connectivity-resilient draft recovery remain PENDING and mandatory before Broker Workspace Launch Gate PASS.

## Trigger-gate state after acceptance

SLICE-0053 neither activates production/pilot/public-launch triggers nor adds a technical native Search criterion.

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 1
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: NOT_DUE

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

No Mandatory Capability Register item `REQ-BROKER-022..029` becomes IMPLEMENTED merely because authenticated access exists. `REQ-BROKER-030` remains IMPLEMENTED.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0053
PROJECT_STATE_QUEUE_SLICE:    0054
```

`SLICE-0054` is only the next queue number. **This closure does not select a SLICE-0054 capability and does not authorize implementation.**

The next capability must be selected through post-SLICE-0053 reassessment and repository reconciliation, including explicit inspection of the Broker Workspace Mandatory Capability Register and post-0051 trigger gates.

## Product execution checkpoint

HullQ now has two real product-side verticals:

```text
Buyer side
→ public listing
→ concrete-yacht truth
→ deterministic technical native Search
→ evidence-backed freshness

Provider side
→ external authentication
→ stable HullQ Account
→ durable Organization/Membership/roles
→ tenant-safe + MFA-gated authorization
→ protected Broker Workspace landing
```

The next reassessment must choose the smallest highest-leverage visible continuation from actual repository state; it must not assume listing CRUD, leads, Saved Search, media or Search expansion is automatically next.

No future capability beyond queue number `0054` is allocated by this closure.

## Closure decision

```text
SLICE-0053 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent closure review and guarded merge.
