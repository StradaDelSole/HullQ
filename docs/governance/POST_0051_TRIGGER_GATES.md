# HullQ — Post-SLICE-0051 Trigger Gates

**Status:** ACCEPTED OWNER DIRECTION
**Accepted:** 2026-09-13
**Scope:** post-SLICE-0051 reassessment, slice readiness, production-pilot readiness, and process governance

<!-- POST_0051_ARCHITECTURE_RECONCILIATION: PASS -->
<!-- TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 1 -->
<!-- WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056 -->
<!-- WORKFLOW_REASSESSMENT_STATUS: NOT_DUE -->

## Purpose

This record turns four accepted post-SLICE-0051 follow-up points into durable, testable triggers. It does not select a SLICE-0052 capability, authorize implementation, reopen an accepted decision, or create a generic framework in advance of demonstrated need.

The controlling rule is:

```text
soft "later" obligation
+ no objective trigger
= unacceptable drift risk

accepted trigger
+ repository-visible state
+ readiness/CI enforcement where deterministic
= durable execution obligation
```

## Gate 1 — architecture/current-state reconciliation before SLICE-0052 selection

**Current status: PASS.**

Before any SLICE-0052 capability is selected or made READY, current-facing architecture/product documents must be reconciled against the accepted 2026-09-02 architecture rebaseline and later accepted slice closures.

The reconciliation is maintenance, not redesign. It must satisfy:

```text
NEW PRODUCT / DOMAIN / ARCHITECTURE DECISIONS = 0
REOPENED OWNER DECISIONS = 0
SEMANTIC CHANGES = 0
KNOWN STALE / CONFLICTING CURRENT-STATE CLAIMS = 0
```

The accepted rebaseline remains controlling where older artifacts conflict, including:

- Astro as the main web framework, with React only where interaction justifies an island;
- FastAPI as the sole HullQ application/domain API boundary;
- DigitalOcean Managed PostgreSQL 18 in FRA1 as the production database target;
- Auth0 Public Cloud with an EU tenant as authentication-only provider, while HullQ owns account/organization/membership/role/authorization truth in PostgreSQL;
- privileged broker publishing protected by MFA, preferably passkeys/WebAuthn, with step-up for high-risk actions;
- immutable CI-built Docker images, GHCR, versioned Docker Compose and controlled deploy/rollback rather than an initial Coolify/Dokploy/self-hosted-PaaS layer;
- stateless/replaceable application hosts;
- independently stored encrypted R2 backups and tested restore rather than reliance on provider backup alone.

Historical ADRs/baselines remain valid history. Their superseded portions must not be treated as current architecture.

`POST_0051_ARCHITECTURE_RECONCILIATION` must remain `PASS` for queued slices from SLICE-0052 onward. A later discovered contradiction changes this marker away from PASS until the contradiction is reconciled; it is not permission to silently reinterpret the accepted decision.

## Gate 2 — production readiness before real broker production use

Canonical gate record:

```text
docs/governance/PRODUCTION_READINESS_GATE.md
```

Hard trigger:

```text
before the first real external broker production inventory
is made available to real external buyers
OR before public production launch,
whichever comes first
→ PRODUCTION_READINESS_GATE_STATUS MUST be PASS
```

This preserves the stronger already-accepted database rule from the 2026-09-02 architecture rebaseline: before that external broker/buyer threshold, production PostgreSQL must have automatic failover with at least one standby. RTO/cost considerations may justify moving earlier, but they do not weaken that hard latest-allowed trigger.

A triggered gate blocks release/pilot progress; it does not force the operational capabilities to be built prematurely while HullQ remains in local/internal development.

## Gate 3 — technical native Search abstraction trigger

Current accepted buyer-facing hard technical native-inventory Search criteria:

```text
1 — draft_max
```

The first criterion proved the concrete end-to-end path. Generalization is deliberately not authorized merely because one implementation exists.

### Second criterion

Any readiness contract that adds the **second** hard technical native-inventory Search criterion MUST:

1. explicitly compare its qualification/FieldResolution/inventory/concrete-boat path with SLICE-0051 `draft_max`;
2. identify which structure is reusable and which logic is criterion-specific;
3. state whether implementation reuses/generalizes a common path or deliberately remains separate, with repository-backed reasoning.

This is a comparison obligation, not an automatic generic-resolver obligation.

### Third and later criteria

A readiness contract for criterion **#3 or later** MUST NOT authorize a third structural copy of an already repeated bridge/path without an explicit abstraction guard result.

It must prove one of:

```text
COMMON STRUCTURE GENERALIZED / REUSED
```

or

```text
STRUCTURALLY DISTINCT — NO THIRD COPY
```

If neither can be proved, readiness is not PASS.

The repository validator checks the machine-readable readiness evidence. Independent readiness review remains responsible for deciding whether the claimed comparison/distinction is substantively true.

The `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` marker records the number already owner-accepted on canonical main. It advances only through an acceptance closure that actually adds another accepted hard technical native-inventory Search criterion; it must not be incremented merely because a criterion is proposed or under implementation.

## Gate 4 — workflow-overhead reassessment

The current independent readiness/exact-head/owner-acceptance/closure workflow remains unchanged now. SLICE-0051 demonstrated that the review process finds material defects, so it must not be weakened speculatively.

A mandatory workflow reassessment becomes due at the earlier of:

```text
A. five further owner-accepted primary slices after SLICE-0051
   → after SLICE-0056 is accepted

B. immediately before the first real production pilot
```

The reassessment must examine actual evidence, including at minimum:

- amendment/review rounds per slice;
- severity and class of defects found by independent review;
- review effort by slice type;
- whether UI/copy/docs-only changes show materially different risk from persistence/security/identity/Search-semantics work;
- whether a risk-tiered lighter review path can preserve the invariants that caught real defects.

Until a reassessment is completed and owner-accepted, no lighter workflow is authorized.

`WORKFLOW_REASSESSMENT_STATUS` values:

```text
NOT_DUE
PASS
```

Rules:

- through accepted SLICE-0055, `NOT_DUE` is valid unless a production pilot is about to start;
- once SLICE-0056 is accepted, `NOT_DUE` is invalid;
- SLICE-0057 cannot become/start READY unless the status is `PASS`;
- if the production-pilot trigger happens earlier, the reassessment must be `PASS` before that pilot begins.

## Readiness evidence from SLICE-0052 onward

Every primary queued slice from SLICE-0052 onward must contain:

```text
**TRIGGER GATES CHECK:** PASS
```

and a section exactly titled:

```text
## Trigger gates
```

with the evidence lines defined by `docs/slices/SLICE_TEMPLATE.md`.

The repository validator checks deterministic syntax/state relationships. Independent readiness review must reject a syntactically valid but false trigger-gate claim.

## Relationship to capability selection

These gates constrain execution; they do not choose the next product capability.

In particular:

```text
SLICE-0052 remains unselected
```

until post-SLICE-0051 product/architecture reassessment has completed against canonical `origin/main` and selected the smallest highest-leverage continuation of the buyer/broker loop.