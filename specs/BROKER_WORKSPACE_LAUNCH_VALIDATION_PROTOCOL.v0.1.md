# Broker Workspace Launch Validation Protocol v0.1

**Status:** ACCEPTED FOR SLICE-0076 READINESS  
**Scope:** Broker Workspace Launch Gate §§9–10 evidence  
**Validation type:** representative usability + current competitive workflow benchmark

## 1. Objective

Produce retained, reviewable evidence for one question:

```text
Is the current HullQ Broker Workspace operationally usable enough
for a deliberately bounded first external self-service pilot,
relative to relevant professional alternatives?
```

This protocol does not authorize production launch, external pilot activation or product fixes outside the assigned validation slice.

## 2. Baseline under test

Validation must run against the exact SLICE-0076 branch candidate built from the accepted SLICE-0075 product boundary.

The six launch-critical tasks must use the ordinary browser-visible Broker Workspace and accepted public/buyer surfaces. During timed tasks the participant must not use direct SQL, internal scripts, FastAPI calls, browser devtools or operator/admin intervention to complete the task.

Environment setup/seeding may be automated before timing starts.

## 3. Representative usability tasks

Use the exact task families required by Broker Workspace Launch Gate §9:

1. **Create + publish listing**
   - start from authenticated Organization workspace;
   - create/resume a professional draft from already-known HullQ design/configuration context;
   - provide required listing/PhysicalBoat facts;
   - add minimum publishable media;
   - promote and publish through ordinary UI.

2. **Edit price / status / details**
   - edit current offer/asking price;
   - edit at least one supported PhysicalBoat/listing fact;
   - exercise an applicable lifecycle/freshness action through UI;
   - verify authoritative re-read.

3. **Media management**
   - upload multiple valid images in one broker workflow;
   - reorder media;
   - set/change cover;
   - exercise one visible recoverable error or invalid-input path where practical.

4. **Lead source identification**
   - open Lead inbox/detail;
   - identify contacted listing;
   - identify acquisition/discovery evidence or explicit UNKNOWN;
   - confirm no operator lookup is required.

5. **Lead handling**
   - assign Lead;
   - update operational status;
   - add note;
   - set follow-up;
   - record contact attempt;
   - use available inbox filtering/search controls to re-find the Lead.

6. **Commercial / sale outcome**
   - complete the applicable close-as-SOLD workflow;
   - preserve unknown achieved price when not supplied;
   - link originating Lead only when explicitly selected/evidenced;
   - verify resulting lifecycle/outcome state.

A seventh untimed observation must verify that the broker can locate and understand the factual performance/funnel snapshot produced by SLICE-0075.

## 4. Evidence captured per task

Retain at least:

- exact branch/commit under test;
- participant label that does not expose unnecessary personal information;
- scenario and starting assumptions;
- start/end time and observed completion duration;
- visible interaction path / material step count;
- completion outcome;
- material friction/confusion;
- errors and recovery behavior;
- whether operator/admin assistance was required;
- any inaccessible or misleading state;
- corrective disposition for each material finding.

The evidence must distinguish product-task time from environment setup time.

## 5. Usability disposition

No aggregate vanity score is required.

For each task, classify:

```text
PASS
PASS_WITH_FRICTION
BLOCKING_DEFICIENCY
NOT_COMPLETED_ENVIRONMENT
```

A `BLOCKING_DEFICIENCY` includes, at minimum:

- task cannot be completed through accepted user-visible surfaces;
- routine task requires direct DB/operator/admin intervention;
- silent data loss or ambiguous authoritative result;
- required Lead source/handling state cannot be located or understood;
- essential inventory/media/lifecycle action lacks a usable recovery path;
- authorization/tenant boundary appears ambiguous to the user.

A material deficiency must be carried into an explicit remediation disposition. Validation must never silently downgrade it to polish.

## 6. Competitive benchmark

Compare HullQ against at least two current relevant professional systems/workflows.

Primary reference set:

1. **BoatWizard / Boats Group**
2. **YATCO BOSS**

Supplementary evidence may use **YachtCloser** for deal/SOLD workflow.

Use official vendor material where available and record source URL + access/publication date. Do not infer member-only behavior that cannot be observed or documented.

Benchmark these functional dimensions:

- listing creation/publish workflow;
- inventory edit/state management;
- media management;
- Lead source visibility;
- Lead handling/filtering/follow-up;
- explicit sale/outcome close-out where comparable;
- listing/performance reporting where comparable.

For each dimension and each reference, classify only:

```text
BETTER
EQUIVALENT
DEFICIENT
NOT_COMPARABLE
```

The classification must include concrete evidence/rationale. Do not produce one overall winner or numeric score.

A material `DEFICIENT` result in listing creation, Lead-source visibility, Lead handling or essential inventory-state management blocks a Launch Gate PASS until corrected or explicitly Owner-accepted as a bounded exception.

Unrelated strengths must not be used to offset a material core-task deficiency.

## 7. Current reference evidence to verify/refresh

At readiness time, current official public evidence included:

- Boats Group BoatWizard product page: inventory management, Lead management, performance reporting;
- Boats Group BoatWizard October 2025 update: Lead search/filter by Portal, Office or Sales Rep;
- Boats Group BoatWizard January/February/May 2026 updates: listing performance, multi-photo management, inventory workflow improvements;
- YATCO BOSS Fleet Manager: add/edit/search listing data, media and vessel history;
- YATCO BOSS CRM Lead Manager: interactions, Lead sources, tasks, contact forms;
- YachtCloser public Help Center: inventory → deal → SOLD workflows.

The implementation/validation agent must refresh or confirm these sources at execution time and retain only factual claims actually evidenced.

## 8. Retained outputs

Required outputs:

```text
docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md
docs/validation/BROKER_WORKSPACE_COMPETITIVE_BENCHMARK_2026-10.md
docs/validation/BROKER_WORKSPACE_LAUNCH_GATE_EVIDENCE_2026-10.md
```

A repeatable local validation harness may be added under `scripts/` and/or a bounded Windows launcher if needed to seed representative data and guide the six tasks.

Retained evidence must be text/audit friendly. Screenshots may supplement but never replace factual task records.

## 9. Launch-gate disposition

SLICE-0076 itself must not silently set `BROKER_WORKSPACE_LAUNCH_GATE_STATUS = PASS`.

Its completion report must recommend one of:

```text
EVIDENCE_SUPPORTS_PASS_REVIEW
REMEDIATION_REQUIRED
VALIDATION_BLOCKED
```

A later independent exact-head review verifies the evidence. Any PASS transition remains subject to that review and explicit Project Owner acceptance.

The separate Security Hardening & Adversarial Validation Gate remains mandatory before `BROKER_SELF_SERVICE_PILOT_STATUS = ACTIVE` even if the Broker Workspace Launch Gate later becomes PASS.

## 10. Non-goals

- visual rebrand/redesign;
- broad production UX implementation;
- product fixes discovered during validation unless separately authorized as a bounded amendment;
- security hardening/adversarial testing;
- production infrastructure;
- external real-broker pilot;
- payments/entitlements;
- owner-direct publication;
- new Search criteria;
- generalized CRM or analytics expansion.
