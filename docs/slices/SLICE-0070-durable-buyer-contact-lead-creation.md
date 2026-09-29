# SLICE-0070 — Durable Buyer Contact / Lead Creation

**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker launch path — buyer contact / durable Lead creation  
**Depends on:** SLICE-0069 owner-accepted / DONE  
**Normative contract:** `specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md`

## Capability

Deliver one bounded buyer→broker contact capability:

```text
currently public-eligible NativeListing
→ anonymous or authenticated buyer contact
→ authoritative current-public recheck
→ durable Lead
→ immutable listing / publishing-Organization / source attribution
→ explicit UNVERIFIED email state
→ buyer-visible deterministic result
```

This is execution-focus step D after SLICE-0069 publication/current-public integration.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
Only durable Lead creation is owned. Broker Lead operations remain a later capability.

**VISIBLE-RESULT CHECK:** PASS  
A buyer can submit a contact request from a currently public listing and receive a deterministic accepted/rejected result; retained proof can read back the exact durable Lead.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted broker-launch path explicitly places durable buyer contact / Lead creation immediately after publish/current-public.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current `main` after accepted SLICE-0069, current public listing/current-public eligibility, auth/session boundary, broker launch focus, Broker Workspace Launch Gate, post-0054 buyer/seller direction and production trigger gates were inspected. No marketplace Lead/contact truth exists to reuse.

**TRIGGER GATES CHECK:** PASS  
0070 adds no Search criterion and starts no external production/pilot/public launch. The newly registered email-verification follow-up remains `PENDING` and is not triggered by synthetic/internal implementation.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; SLICE-0069 acceptance closure; `docs/POST_SLICE_0069_REASSESSMENT_2026-09-29.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; D32 in `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`.

**Production implementation checked:** current public NativeListing read/current-public eligibility; FastAPI route/session topology; broker/public Astro patterns; PostgreSQL migration/persistence patterns; repository public-mutation/CSRF patterns; current Search/current-market integration.

**Already implemented / not re-decided:** anonymous-capable buyer discovery; optional Account session identity; canonical D29 CurrentPublicEligibility; immutable publishing Organization ownership; public listing page; technical Search criterion count 2.

**Exact remaining gap:** there is no durable marketplace buyer contact / Lead identity or persistence path, so the current public listing cannot create the first-class attributed Lead required by the broker launch gate.

**Accepted-but-unimplemented obligations:** D32 durable anonymous-capable contact creation; optional Account attribution; explicit UNVERIFIED email state; hard follow-up trigger for email verification; later broker Lead operating surface.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` public/current-listing/auth foundations; `DECIDED_NOT_YET_IMPLEMENTED` Lead creation and email verification; `EXPLICITLY_DEFERRED` broker CRM/email delivery/verification token flow/phone/CAPTCHA/outcomes/analytics/editing; `GENUINELY_OPEN` implementation-local names/factoring only; `CONFLICT_OR_REGRESSION` none.

### DECIDED_AND_IMPLEMENTED

- public NativeListing exact-read/current-public boundary;
- D29 canonical CurrentPublicEligibility;
- publishing Organization identity;
- optional authenticated Account/session boundary;
- anonymous-capable buyer Search/listing access;
- current public Astro listing page;
- exactly two accepted technical Search criteria.

### DECIDED_NOT_YET_IMPLEMENTED — owned here where stated

- durable LeadId + retry-safe submission identity;
- server-derived NativeListing/publishing-Organization attribution;
- required bounded name/email/message;
- optional authenticated AccountId attribution;
- explicit contact-email verification state initially UNVERIFIED;
- buyer-visible public listing contact form/result;
- private/internal readback for proof.

### DECIDED_NOT_YET_IMPLEMENTED — mandatory later

- actual email verification evidence/token/delivery capability;
- `BUYER_CONTACT_EMAIL_VERIFICATION_STATUS = IMPLEMENTED` before real external production buyer-contact exposure/trusted-email use;
- broker Lead operating surface.

### EXPLICITLY_DEFERRED

- broker inbox/detail/assignment/status/notes/timeline;
- outbound broker email notification;
- email-verification token/delivery flow;
- phone/SMS verification;
- CAPTCHA/provider selection;
- Lead scoring/ranking;
- sale/outcome;
- analytics/performance reporting;
- inventory editing;
- lead transfer;
- Search criterion #3+.

### GENUINELY_OPEN

Exact module/table/route names, exact bounded string limits, exact response token names, and internal source-context field naming, provided the normative contract is preserved.

### CONFLICT_OR_REGRESSION

None found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Buyer contact email verification:** PENDING  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** NOT_READY

No real external buyer traffic, broker pilot, paid plan or public production launch is authorized.

## Scope

Implementation may span:

- Lead domain identity/value/result types;
- PostgreSQL migration/persistence;
- application orchestration;
- optional-session attribution plumbing;
- FastAPI public contact endpoint;
- Astro public listing contact form/proxy as appropriate;
- deterministic retry/idempotency;
- current-public authoritative recheck/serialization;
- focused unit/persistence/API/web tests;
- retained real-PostgreSQL end-to-end proof.

No broker Lead workspace or email-delivery system may be introduced.

## Mandatory implementation invariants

Implementation MUST satisfy every rule in `MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md`, especially:

1. Account login is not required;
2. name/email/message are required and bounded;
3. AccountId is optional attribution only;
4. contact email is explicitly UNVERIFIED in v0.1;
5. login/delivery/broker handling never imply verification;
6. target Organization is derived server-side from NativeListing truth;
7. creation requires current canonical D29 eligibility at authoritative creation time;
8. stale listing visibility cannot create a Lead after eligibility loss;
9. submission retries are idempotent and conflicting reuse is deterministic;
10. Lead creation is atomic and concurrent duplicate-safe;
11. no raw IP/User-Agent becomes Lead marketplace truth;
12. public outcomes are bounded/non-enumerating;
13. Lead creation changes no listing/lifecycle/freshness/Search truth;
14. email verification remains a durable mandatory follow-up trigger;
15. broker CRM/inbox/status/notes are not smuggled into this slice.

## Required proof

At minimum prove the normative contract §17 matrix, including real PostgreSQL concurrency for stale-public/duplicate submission boundaries and a retained FastAPI + built Astro + PostgreSQL vertical.

## Readiness stop conditions

Stop and return for reassessment if:

- safe creation requires changing D29 semantics rather than consuming them;
- anonymous contact cannot be protected without introducing a materially new identity/trust policy;
- a provider-specific CAPTCHA/email vendor becomes architecturally mandatory for internal/synthetic proof;
- Lead creation would require storing raw network identifiers as marketplace truth;
- broker operational workflow must be invented to create a Lead;
- implementation would activate real production buyer traffic or a production trigger.

## Acceptance

Independent exact-head implementation review must verify the normative contract, migration, retry/concurrency behavior, privacy boundary and proof matrix.

Owner Acceptance remains mandatory before implementation merge.

The initial implementation prompt must come only from `START_SLICE.bat` after this readiness package is independently reviewed, remote gates are green and readiness is merged to `main`.
