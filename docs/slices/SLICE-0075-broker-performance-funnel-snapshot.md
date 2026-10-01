# SLICE-0075 — Broker Performance & Funnel Snapshot

**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Launch Gate §7 — performance/source-to-outcome analytics  
**Depends on:** SLICE-0074 owner-accepted / DONE  
**Normative contract:** `specs/BROKER_PERFORMANCE_FUNNEL_SNAPSHOT_CONTRACT.v0.1.md`

## Capability

Deliver one coherent broker-visible capability:

```text
durable public listing view facts
+ accepted Lead / contact-attempt / provenance / SaleOutcome facts
→ Organization-scoped factual performance snapshot
```

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One recurring broker question: what factual activity and handling/outcome evidence did my listings generate?

**VISIBLE-RESULT CHECK:** PASS  
The Broker Workspace gains a concrete performance surface, not backend-only telemetry.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The create→publish→Lead→operate→close loop is complete. This slice addresses the remaining technical Launch Gate §7 gap.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Reuses accepted public eligibility, Lead identities/provenance, contact-attempt timeline and SaleOutcome truth.

**TRIGGER GATES CHECK:** PASS  
No external production pilot, paid plan or Search criterion is activated.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED:** public listing eligibility; Lead received_at/source/provenance; contact-attempt timeline; explicit SaleOutcome; Organization auth/MFA; focused-local/remote-full validation.  
**DECIDED_NOT_YET_IMPLEMENTED:** durable public view event; factual broker funnel projection; first-contact latency projection; source-to-outcome broker surface; later periodic reporting.  
**EXPLICITLY_DEFERRED:** third-party analytics, fingerprinting, generalized event warehouse, periodic report delivery, Search-fit diagnostics, export/import, payments.  
**GENUINELY_OPEN:** implementation-local schema names and bounded UI composition.  
**CONFLICT_OR_REGRESSION:** stale embedded 0074 sale-outcome status in PROJECT_STATE must be synchronized during readiness.

## Required implementation

1. durable idempotent public NativeListing view event/fact;
2. ingestion wired only to accepted public-listing success path;
3. no private/preview/suppressed-read counting;
4. Organization-scoped performance read projection;
5. exact view + Lead + contacted/handled + explicit SOLD factual counts;
6. earliest CONTACT_ATTEMPT response-time derivation;
7. Lead acquisition/discovery source breakdown from existing provenance;
8. explicit source-to-SOLD linkage only through originating Lead;
9. Broker Workspace performance page/surface;
10. retained real PostgreSQL + FastAPI + built Astro proof.

## Mandatory constraints

- no raw-IP analytics retention;
- no fingerprinting;
- no inferred sale;
- no notification event treated as broker response;
- no status/assignment/note treated as response unless separately accepted;
- no cross-Organization aggregate leakage;
- unknown remains unknown;
- no hidden performance score;
- no new Search criterion;
- no routine local full-suite run.

## Acceptance

Independent exact-head review must verify event idempotency, public-only counting, privacy boundary, Organization isolation, response-time semantics, source/outcome truthfulness, unknown-state rendering and vertical retained proof.

Owner Acceptance remains mandatory before merge.

Initial implementation prompt comes only from `START_SLICE.bat` after readiness review/gates/merge.
