# SLICE-0075 — Broker Performance & Funnel Snapshot

**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Status set by this handoff:** `REVIEW`  
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

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; SLICE-0070/0071/0074 contracts and acceptance closures.  
**Production implementation checked:** current public-listing read/eligibility path; durable BuyerLead persistence/provenance; Lead timeline/contact-attempt persistence; Broker Workspace Organization authorization; SaleOutcome persistence/read model.  
**Already implemented / not re-decided:** public listing eligibility; Lead received_at/source/acquisition/discovery provenance; append-only broker contact-attempt timeline; explicit SaleOutcome; Organization auth/MFA; focused-local / authoritative-remote validation.  
**Exact remaining gap:** HullQ has no accepted durable public-listing view fact and no Organization-scoped factual broker projection combining views, Leads, first contact-attempt timing and explicit SOLD outcomes.  
**Accepted-but-unimplemented obligations:** Broker Workspace Launch Gate §7 performance/source-to-outcome analytics; REQ-BROKER-011 response measurability; REQ-BROKER-012 source-to-outcome linkage surface; REQ-BROKER-013 factual-vs-derived analytics discipline; later REQ-BROKER-028 periodic reporting remains separate.  
**Material classifications:** DECIDED_AND_IMPLEMENTED foundations above; DECIDED_NOT_YET_IMPLEMENTED public view telemetry + broker funnel snapshot; EXPLICITLY_DEFERRED third-party tracking/fingerprinting/generalized analytics/periodic delivery; GENUINELY_OPEN implementation-local schema/layout; CONFLICT_OR_REGRESSION stale embedded 0074 sale-outcome marker in PROJECT_STATE corrected by readiness.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** NOT_READY

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
