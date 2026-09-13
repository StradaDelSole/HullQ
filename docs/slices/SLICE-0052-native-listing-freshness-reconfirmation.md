# SLICE-0052 — NativeListing freshness / reconfirmation

**ID:** SLICE-0052  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** post-SLICE-0051 native-marketplace trust / current-inventory correctness  
**Depends on:** SLICE-0041, SLICE-0049, SLICE-0051, accepted post-0051 maintenance/reconciliation on canonical main  
**Blocks:** trustworthy current-inventory monitoring, later Saved Search/alerts, external buyer validation using freshness-rate evidence

## Objective

Add exactly one production capability: evidence-backed freshness/reconfirmation for manual native professional listings so an indefinitely old `ACTIVE` listing cannot continue to appear as current buyer inventory merely because its lifecycle state remains ACTIVE.

The visible end-to-end result is:

```text
ACTIVE + recent confirmation
-> CONFIRMED
-> public listing + Search visible

30 days reached
-> DUE_FOR_CONFIRMATION
-> remains visible during 7-day grace with explicit due disclosure

37 days reached
-> STALE
-> suppressed from current buyer listing/Search surfaces
-> lifecycle remains ACTIVE

authorized reconfirmation
-> new immutable confirmation evidence
-> CONFIRMED
-> current buyer visibility restored
```

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
This slice adds one trust capability only: NativeListing freshness/reconfirmation. Persistence, policy evaluation, current-market gating and buyer disclosure are the necessary vertical parts of that single capability.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can execute the retained PostgreSQL/FastAPI/Astro proof and inspect one listing moving deterministically through CONFIRMED -> DUE_FOR_CONFIRMATION -> STALE -> CONFIRMED, including Search suppression/restoration and buyer-visible due disclosure.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted marketplace architecture explicitly separates lifecycle from freshness, states that ACTIVE does not imply currently confirmed, directs an initial manual-listing confirmation TTL around 30 days plus a grace period around 7 days, and requires freshness as its own bounded capability. This slice implements that accepted trust boundary without pulling Auth0, alerts, feeds, SOLD/ARCHIVED or broader Search forward.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical main was checked after PR #189/#190 maintenance. Existing lifecycle/public read/Search code has no production freshness state or reconfirmation persistence; `ACTIVE` alone currently admits listings to public read and native-inventory Search. The proposed capability is therefore not duplicate implementation.

**TRIGGER GATES CHECK:** PASS  
Architecture/current-state reconciliation is PASS; production readiness is NOT_TRIGGERED; this slice adds no technical native Search criterion; workflow reassessment is NOT_DUE.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §§8, 10–11, 14; `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md` §§3, 6–7; `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`; `docs/governance/OPEN_QUESTIONS.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; accepted SLICE-0041/0049/0051 contracts/closures; `specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md`.  
**Production implementation checked:** `src/hullq/domain/native_listing_lifecycle.py`; `src/hullq/persistence/native_listing_lifecycle.py`; `src/hullq/application/public_listing_read.py`; `src/hullq/persistence/inventory_search.py`; `src/hullq/application/inventory_search.py`; `src/hullq/api/app.py`; current Astro listing/Search pages and retained 0049/0051 proof scripts.  
**Already implemented / not re-decided:** professional publisher eligibility and Organization isolation; DRAFT -> ACTIVE -> WITHDRAWN lifecycle; append-only publication transitions; stable public listing route/noindex behavior; SLICE-0051 `draft_max` design/configuration/PhysicalBoat qualification; exact Decimal and current PhysicalBoat contradiction semantics.  
**Exact remaining gap:** current public listing and native-inventory Search eligibility stop at `lifecycle == ACTIVE`; there is no durable reconfirmation event, no current freshness evaluation, no TTL/grace enforcement and no freshness disclosure/suppression on buyer surfaces.  
**Accepted-but-unimplemented obligations:** separate listing freshness state; manual native confirmation TTL/grace behavior; suppression of unconfirmed stale inventory without inventing SOLD/WITHDRAWN; freshness-rate correctness needed before external buyer validation. Auth0-backed broker workspace, alert cadence, automated reminders/scheduler, feed-driven freshness and SOLD/ARCHIVED remain owned by later capabilities.  
**Material classifications:** freshness/reconfirmation = `DECIDED_NOT_YET_IMPLEMENTED`; existing lifecycle/publisher eligibility/public listing/draft_max Search = `DECIDED_AND_IMPLEMENTED`; Auth0 workspace, alerts/scheduler, feed freshness, SOLD/ARCHIVED, republish = `EXPLICITLY_DEFERRED`; OQ-018 broad/indexable SEO remains `GENUINELY_OPEN` but is not touched by this noindex capability.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** NOT_DUE

This slice operates against local/internal synthetic/disposable data and does not activate real external broker production data, a production pilot or public production launch. It therefore does not trigger the Production Readiness Gate.

## Why this slice exists

SLICE-0049 made an ACTIVE NativeListing public. SLICE-0051 then made ACTIVE native inventory discoverable from a real technical buyer requirement. The current production path therefore has a concrete trust hole:

```text
ACTIVE at publication time
+ no later withdrawal
= can remain publicly/search-visible forever
```

That conflicts with the accepted rule that `ACTIVE` does not automatically mean `CURRENTLY CONFIRMED`.

Freshness is a higher-leverage continuation than the main alternatives at this exact point:

- a second technical Search criterion would broaden discovery before current inventory truth is time-bounded;
- Saved Search/monitoring/alerts would persist and notify against inventory that can currently remain stale indefinitely;
- Auth0/broker workspace is broader and does not by itself correct buyer-visible staleness;
- media is valuable but does not close the current-inventory correctness gap;
- SOLD/ARCHIVED/republish are separate lifecycle semantics and must not be inferred from time passage.

This slice therefore strengthens the already-visible buyer loop before expanding its breadth.

## Controlling artifacts

- Requirement IDs: `REQ-MARKET-007` through `REQ-MARKET-011`.
- Specifications: `specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md`; existing marketplace/public-surface/Search contracts remain controlling where not superseded.
- Accepted ADRs: existing persistence/Alembic/application architecture ADRs; no new infrastructure ADR is required.
- Governance / research protocols: current repository workflow and exact-head review rules.
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`.
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`.
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`.
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`.
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`.
- Post-SLICE-0039 execution reconciliation / precedence: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`.
- Private-owner / public-supply policy where relevant: `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`.
- Native listing market decision: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`.
- Pre-Gate-1 execution amendment: `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`.
- Relevant open questions: OQ-006 remains deferred for automated alert cadence/cache-TTL behavior; this slice does not decide that alert policy. OQ-014 provider/identity architecture is already decided but authenticated broker implementation remains deferred. OQ-018 broad/indexable SEO remains open and is untouched.

## In scope

- Domain freshness vocabulary `CONFIRMED`, `DUE_FOR_CONFIRMATION`, `STALE`, `UNKNOWN` separate from lifecycle.
- Exact production policy `MANUAL_NATIVE_V1`: 30-day TTL + 7-day grace, with exact 30-day and 37-day boundary semantics from the freshness contract.
- A runtime-distinct `FreshnessConfirmationId` and immutable explicit reconfirmation event.
- Alembic migration for durable reconfirmation-event persistence and required constraints/indexes.
- Existing DRAFT -> ACTIVE publication transition as initial confirmation evidence; no deployment-time freshness reset.
- Existing ACTIVE listings derive their initial confirmation age from retained publication history; missing evidence -> UNKNOWN.
- Authorized operator-assisted reconfirmation using the real accepted publishing-eligibility evaluator and exact owning Organization boundary.
- Retry-safe exact reconfirmation ID semantics and conflict-safe immutable history.
- Deterministic freshness evaluation from immutable evidence + explicit timezone-aware UTC `as_of`.
- Current-market gating of the production public listing read path.
- Current-market gating of the existing `draft_max` native-inventory candidate path without changing technical Search semantics.
- Buyer-visible freshness status and `last_confirmed_at` for visible public listing and Search results; DUE state must be visibly distinct from CONFIRMED.
- Astro rendering changes needed to expose freshness/due state on the existing noindex listing/Search surfaces.
- A bounded operator-executable reconfirmation script/service over the real persistence/application path.
- Unit, persistence, concurrency/idempotency, API, web and retained real PostgreSQL 18 -> FastAPI -> Astro proof coverage.

## Explicitly out of scope

- Auth0 integration, login/session handling or broker workspace UI.
- Persisted general Account/Organization/Membership directory.
- Email/push/browser reminders, automated alerts, alert cadence or monitor scheduling.
- A background scheduler merely to mutate freshness with time.
- Feed-driven freshness, source disappearance/source-health rules or external market adapters.
- `WITHDRAWN -> ACTIVE` republish.
- `SOLD`, `ARCHIVED` or sale inference.
- SavedQuery, Monitor, Alert or subscription/entitlement implementation.
- Price/status history intelligence or Days-on-Market product surfaces.
- Media.
- Any second technical native Search criterion or Search-bridge generalization.
- Generic all-field FieldResolution/canonical resolution work.
- Broad/indexable Search/SEO taxonomy, sitemap/hreflang or structured-data expansion.
- Production deployment/HA/observability work while the Production Readiness Gate remains NOT_TRIGGERED.

## Required behavior

### A. Freshness is derived, not a lifecycle mutation

Time passage MUST NOT write a lifecycle transition. `ACTIVE + STALE` remains lifecycle `ACTIVE` in durable state/history.

There is no required scheduled mutation at 30 or 37 days. A read/Search evaluated at `as_of` derives freshness from evidence and policy.

### B. Exact MANUAL_NATIVE_V1 boundaries

Given `confirmed_at`:

```text
as_of < confirmed_at + 30d              -> CONFIRMED
confirmed_at + 30d <= as_of < +37d      -> DUE_FOR_CONFIRMATION
as_of >= confirmed_at + 37d             -> STALE
no admissible evidence                   -> UNKNOWN
confirmed_at > as_of                     -> UNKNOWN
```

Use timezone-aware UTC datetimes and exact duration boundaries.

### C. Initial confirmation evidence

A successful accepted DRAFT -> ACTIVE publication transition is the initial confirmation evidence. Implementation MUST reuse its retained exact `occurred_at`; it MUST NOT invent `now` at migration/deployment.

No historical transition evidence -> UNKNOWN.

### D. Explicit reconfirmation

A reconfirm request carries explicit typed principal/listing inputs plus stable `FreshnessConfirmationId`. It MUST exercise the accepted SLICE-0041 evaluator and exact listing-owner Organization check.

Only current lifecycle ACTIVE can be reconfirmed.

Success appends one immutable event with database/system `occurred_at`. Caller-supplied arbitrary confirmation timestamps are forbidden.

### E. Idempotency / conflict / concurrency

Same confirmation ID + same immutable envelope is idempotent. Reuse with different listing/actor/Organization fails closed as CONFLICT.

Concurrent valid different confirmations may both become immutable true events and MUST NOT corrupt lifecycle or each other. A successful result means its row is durably committed under the existing top-level transaction-ownership discipline.

### F. Public listing gating

The current public listing model is returned only for:

```text
ACTIVE + CONFIRMED
ACTIVE + DUE_FOR_CONFIRMATION
```

`ACTIVE + STALE` and `ACTIVE + UNKNOWN` collapse to the ordinary current-listing not-found class and expose no stale current offer projection.

Visible models include exact `freshness_status` and `last_confirmed_at`.

### G. Search gating

The existing candidate path must exclude STALE/UNKNOWN before `draft_max` technical classification. Such listings are not technical insufficient-data cases and must not increment SLICE-0051 `insufficient_data_count`.

CONFIRMED and DUE listings preserve all current 0051 design/configuration/FieldResolution/PhysicalBoat/Decimal semantics. Returned matches include freshness status + effective last confirmation timestamp.

### H. Buyer disclosure

Astro listing and Search surfaces must render DUE_FOR_CONFIRMATION distinctly from CONFIRMED. They may use concise wording, but MUST NOT label a DUE listing simply "confirmed".

Noindex/canonical behavior stays as already accepted.

### I. Failure behavior

Denied/cross-Organization/DRAFT/WITHDRAWN/missing/conflicting reconfirm attempts write zero new confirmation rows. No failure path may generate SOLD/WITHDRAWN or rewrite an earlier confirmation event.

### J. Retained proof

The proof uses real PostgreSQL 18 persisted state and real FastAPI/Astro rendering. It must demonstrate CONFIRMED -> DUE -> STALE -> reconfirmed CONFIRMED without sleeping, by injecting/evaluating explicit `as_of` boundaries.

## Deliverables

- `specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md` implemented exactly.
- Domain freshness policy/state/ID types.
- One forward Alembic migration for reconfirmation event persistence.
- Persistence read/write functions for freshness evidence/reconfirmation.
- Application freshness resolver/current-market predicate.
- Operator-assisted reconfirmation entry point.
- Public listing read/API projection updated with freshness gating/data.
- Existing native-inventory Search candidate/result path updated with freshness gating/data only.
- Existing Astro listing/Search surfaces updated with freshness status/due disclosure.
- Unit + PostgreSQL integration + concurrency/idempotency + API/web tests.
- `scripts/inspect_native_listing_freshness.py` or equivalently named retained real vertical proof.
- CI integration of the retained proof alongside the existing production-listing/native-inventory proofs.

## Acceptance criteria

- [ ] `MANUAL_NATIVE_V1` is exactly 30 days TTL + 7 days grace and exact +30d/+37d boundary tests pass.
- [ ] Freshness vocabulary is runtime-distinct from lifecycle and no code path maps STALE/UNKNOWN to SOLD/WITHDRAWN.
- [ ] DRAFT -> ACTIVE publication transition timestamp is used as initial confirmation evidence; deployment/migration does not reset freshness age.
- [ ] Pre-existing ACTIVE with no admissible publication/reconfirmation evidence resolves UNKNOWN and is buyer-suppressed.
- [ ] Successful reconfirmation requires real accepted publisher eligibility + owning Organization + lifecycle ACTIVE.
- [ ] Reconfirmation appends immutable audit evidence with system/database timestamp and cannot accept arbitrary caller confirmation time.
- [ ] Exact retry of the same confirmation ID/envelope is idempotent; conflicting reuse fails closed without mutation.
- [ ] Denied, cross-Organization, missing, DRAFT and WITHDRAWN attempts append zero confirmation events.
- [ ] Transaction-ownership and concurrency tests prove no false durable success/partial state and allow concurrent true reconfirm events safely.
- [ ] Public listing API/Astro serves ACTIVE+CONFIRMED and ACTIVE+DUE, includes freshness metadata, and buyer-visibly distinguishes DUE.
- [ ] Public listing API/Astro suppresses ACTIVE+STALE and ACTIVE+UNKNOWN without changing lifecycle/history.
- [ ] Existing `draft_max` Search excludes STALE/UNKNOWN before technical classification and does not count them as technical insufficient data.
- [ ] Existing `draft_max` Search returns CONFIRMED/DUE matches with freshness metadata while preserving every accepted 0051 technical qualification invariant.
- [ ] Search/listing `noindex` and canonical-route semantics remain unchanged.
- [ ] Retained PostgreSQL 18 -> FastAPI -> Astro proof demonstrates CONFIRMED -> exact +30d DUE -> exact +37d STALE suppression -> authorized reconfirmation -> CONFIRMED restoration.
- [ ] Retained proof demonstrates stale lifecycle remains ACTIVE and no SOLD/WITHDRAWN event is invented.
- [ ] No Auth0, scheduler/alerts, feed freshness, republish, SOLD/ARCHIVED, Saved Search, media, second Search criterion or generic resolver is introduced.
- [ ] `uv run python scripts/validate_repository.py`, Ruff format/lint, mypy, full tests/coverage, web check/build/tests and required PostgreSQL-18 CI all pass on the exact implementation head.
- [ ] Remote CI and any manufacturer/reproducibility gate required by repository workflow pass on the exact implementation head before independent ACCEPT.

An implementation agent MUST NOT check an acceptance criterion that it has not actually verified. External criteria remain unchecked until their results have actually been observed.

## Expected touch points

Expected, not exhaustive permission to broaden scope:

- `src/hullq/domain/native_listing_freshness.py` (new) or a tightly equivalent bounded module;
- `src/hullq/persistence/native_listing_freshness.py` (new);
- `src/hullq/persistence/native_listing_lifecycle.py` only where initial publication evidence/current-state locking must be reused, without changing accepted lifecycle semantics;
- one new Alembic revision;
- `src/hullq/application/public_listing_read.py`;
- `src/hullq/persistence/inventory_search.py` and/or `src/hullq/application/inventory_search.py` for freshness admission/projection only;
- `src/hullq/api/app.py` for freshness projection/current-time injection only;
- existing Astro listing/Search rendering modules/pages;
- focused unit/integration/web tests;
- `scripts/inspect_native_listing_freshness.py`;
- CI workflow only to execute the retained proof if needed.

Do not modify unrelated data research, Search criteria, auth, media, alert/subscription or deployment systems.

## Validation

```bash
uv lock --check
uv sync --locked --all-groups
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest

cd web
npm ci
npm run check
npm test
npm run build
```

PostgreSQL-specific freshness tests and the retained real vertical proof MUST run against PostgreSQL 18 using the repository's existing test/CI database conventions. Do not replace the real DB proof with mocks/SQLite.

## Stop conditions

Stop and report instead of inventing a solution when:

- a required controlling freshness/lifecycle/auth decision is absent or contradicts this readiness contract;
- implementation would require changing the accepted DRAFT/ACTIVE/WITHDRAWN lifecycle vocabulary;
- implementation would require treating stale/disappeared as SOLD or WITHDRAWN;
- a pre-existing ACTIVE listing cannot be freshness-evaluated without inventing evidence rather than using retained publication history/UNKNOWN;
- the existing publication transition cannot safely serve as initial confirmation evidence under actual persisted schema/transaction semantics;
- operator reconfirmation cannot exercise the real accepted publisher-eligibility/Organization boundary without a bypass;
- Search freshness admission would require changing `draft_max` criterion semantics or adding a second criterion;
- a post-0051 trigger gate changes from its readiness value and is no longer satisfied;
- implementation requires Auth0, scheduler/alerts, feed freshness, media, broad SEO or other explicit out-of-scope capability.

## Status handoff rule

The implementation agent may recommend or set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent exact-head review and explicit Project Owner acceptance.

A successful implementation completion therefore hands SLICE-0052 off in `REVIEW`.

## Required completion report

### Slice

- Slice ID: `SLICE-0052`
- Recommended slice state: `REVIEW` | `BLOCKED`
- Scope completed: `YES` | `NO`
- Exact final branch HEAD SHA:

### Product execution checks

- ONE-CAPABILITY CHECK: `PASS` | `FAIL`
- VISIBLE-RESULT CHECK: `PASS` | `FAIL`
- PRODUCT EXECUTION PLAN ALIGNMENT: `PASS` | `FAIL`
- REPOSITORY RECONCILIATION CHECK: `PASS` | `FAIL`
- TRIGGER GATES CHECK: `PASS` | `FAIL`

### Changes

- Changed files:
- Requirements implemented or researched:
- Tests/fixtures added or updated:

### Validation

- Local validation: `PASS` | `FAIL` | `PARTIAL`
- Commands run:
- Results:

### External verification

- Remote CI: `PASS` | `FAIL` | `NOT VERIFIED`
- Other external gates: `PASS` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`

### Findings

- Unresolved findings:
- Spec/ADR ambiguities:
- Scope deviations:

### Follow-up

- Recommended next action:

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.