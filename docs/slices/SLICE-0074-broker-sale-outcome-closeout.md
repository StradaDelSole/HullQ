# SLICE-0074 — Broker Sale / Outcome Close-out

**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Status set by this handoff:** `REVIEW`  
**Stage:** Broker launch path — broker closes / records outcome  
**Depends on:** SLICE-0073 owner-accepted / DONE  
**Normative contract:** `specs/BROKER_SALE_OUTCOME_CONTRACT.v0.1.md`

## Capability

Deliver one coherent broker outcome:

```text
existing Organization-owned NativeListing
→ explicit Close as SOLD
→ immutable publisher-scoped SaleOutcome revision
→ optional sold date / achieved price / Lead linkage
→ ACTIVE listing atomically becomes WITHDRAWN
→ current outcome re-read
```

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One recurring broker job: explicitly close a listing as SOLD and retain auditable outcome truth.

**VISIBLE-RESULT CHECK:** PASS  
The broker can complete a bounded close-out flow and immediately see the authoritative sale/outcome result.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This closes the final missing step of the accepted Broker Launch Execution Focus operational loop.

**REPOSITORY RECONCILIATION CHECK:** PASS  
D25/D28, existing NativeListing lifecycle, Lead ownership/attribution, Organization authorization and immutable revision/head patterns are reused rather than redesigned.

**TRIGGER GATES CHECK:** PASS  
No production pilot/payment activation or Search criterion is introduced.

## Decision / implementation reconciliation

**Accepted records checked:** docs/PROJECT_STATE.md; docs/slices/SLICE-0073-acceptance-closure.md; docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md; docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md D25/D28; specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md REQ-BROKER-005/006/012; docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md; docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md.  
**Production implementation checked:** NativeListing lifecycle transitions; broker Organization/current-membership/MFA authorization; Lead persistence/Organization/listing ownership; professional inventory read/edit surfaces; current-public eligibility.  
**Already implemented / not re-decided:** listing identity; Organization publishing principal; lifecycle/freshness separation; immutable revision/current-head pattern; Lead identity/attribution; non-enumerating tenancy; Broker Workspace session/CSRF/MFA.  
**Exact remaining gap:** a broker cannot explicitly record SOLD/outcome truth or close an ACTIVE listing as SOLD while retaining immutable auditable outcome provenance.  
**Accepted-but-unimplemented obligations:** D25/D28 SaleOutcome persistence/revision; broker close-out API/UI; optional achieved-price/sold-date/Lead linkage; atomic ACTIVE→WITHDRAWN + outcome; correction history; later export/Search-fit/reporting commitments.  
**Material classifications:** DECIDED_AND_IMPLEMENTED foundations; DECIDED_NOT_YET_IMPLEMENTED 0074 sale/outcome close-out; EXPLICITLY_DEFERRED global MarketEpisode outcome resolution/analytics/payment/import; GENUINELY_OPEN implementation-local factoring; CONFLICT_OR_REGRESSION none.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** NOT_READY

## Required implementation

1. durable publisher-scoped SaleOutcome revision/current-head persistence;
2. exact optimistic concurrency + retry-safe idempotency;
3. authorized private read projection;
4. SOLD mutation for ACTIVE and WITHDRAWN listings;
5. atomic outcome + ACTIVE→WITHDRAWN transaction;
6. optional sold date / achieved amount+currency;
7. optional same-listing/same-Organization originating Lead linkage;
8. broker inventory UI close-out action and current outcome display;
9. correction/superseding revision path preserving history;
10. retained real PostgreSQL + FastAPI + built Astro proof.

## Mandatory constraints

- WITHDRAWN never implies SOLD;
- achieved price never inferred;
- recorded_at != sold_date;
- no cross-Organization propagation;
- no automatic global MarketEpisode outcome truth;
- no second lifecycle authority;
- no Search rewrite;
- no local full-suite requirement by default.

## Acceptance

Independent exact-head review must verify authorization/tenancy, immutable revision history, concurrency/idempotency, lifecycle atomicity, optional-field truthfulness, Lead linkage safety, cross-Organization isolation and retained vertical proof.

Owner Acceptance remains mandatory before implementation merge.

Initial implementation prompt must come only from `START_SLICE.bat` after readiness review, remote gates and readiness merge.
