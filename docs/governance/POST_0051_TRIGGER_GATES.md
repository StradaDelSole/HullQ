# HullQ — Post-SLICE-0051 Trigger Gates

**Status:** ACCEPTED OWNER DIRECTION — amended by owner-direct marketplace pivot when merged  
**Accepted:** 2026-09-13; mixed-supply amendment 2026-09-14  
**Scope:** post-SLICE-0051 reassessment, slice readiness, production-data/pilot readiness, Search abstraction and process governance

<!-- POST_0051_ARCHITECTURE_RECONCILIATION: PASS -->
<!-- TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2 -->
<!-- WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056 -->
<!-- WORKFLOW_REASSESSMENT_STATUS: PASS -->

## Purpose

This record turns accepted post-SLICE-0051 follow-up points into durable triggers. The 2026-09-14 owner-direct marketplace pivot amends the production-data trigger so private-seller production cannot bypass a gate originally worded around brokers.

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

## Gate 1 — architecture/current-state reconciliation

**Current status: PASS.**

Current-facing architecture/product documents must remain reconciled against accepted rebaselines and later accepted slice/product-direction decisions.

The 2026-09-02 infrastructure/application rebaseline remains controlling where older stack/architecture artifacts conflict. The 2026-09-14 owner-direct product direction now controls marketplace-supply scope where older current-facing documents say private FSBO is out of scope.

Current accepted stack boundaries remain, including:

- Astro as the main web framework, with React only where interaction justifies an island;
- FastAPI as the sole HullQ application/domain API boundary;
- DigitalOcean Managed PostgreSQL 18 in FRA1 as the production database target;
- Auth0 Public Cloud with an EU tenant as authentication-only provider, while HullQ owns account/organization/membership/role/authorization truth in PostgreSQL;
- privileged broker publishing protected by MFA, preferably passkeys/WebAuthn, with step-up for high-risk actions;
- immutable CI-built Docker images, GHCR, versioned Docker Compose and controlled deploy/rollback rather than an initial self-hosted-PaaS layer;
- stateless/replaceable application hosts;
- independently stored encrypted backups and tested restore rather than reliance on provider backup alone.

Historical ADRs/baselines remain valid history. Their superseded portions must not be treated as current architecture.

`POST_0051_ARCHITECTURE_RECONCILIATION` must remain `PASS` for queued slices from SLICE-0052 onward. A later discovered current-facing contradiction changes this marker away from PASS until reconciled; it is not permission to silently reinterpret an accepted decision.

## Gate 2 — production readiness before real external marketplace production data / pilot / launch

Canonical gate record:

```text
docs/governance/PRODUCTION_READINESS_GATE.md
```

Hard trigger after the mixed-supply pivot:

```text
before the first real external broker OR owner-direct seller/listing data
is stored/relied upon as HullQ production data
OR before the first real external production pilot
OR before public production launch,
whichever comes first
→ PRODUCTION_READINESS_GATE_STATUS MUST be PASS
```

This is deliberately earlier than waiting for inventory to become public. Owner-direct/private seller production is not exempt merely because the original 2026-09-13 wording named broker data.

The hard latest-allowed database-resilience boundary is likewise supply-neutral after the pivot:

```text
before real external marketplace inventory is exposed to real external buyers
→ production PostgreSQL has automatic failover with at least one standby
```

The production-readiness PASS may distinguish conditions genuinely not yet applicable during a strictly internal real-data phase, but later external pilot/buyer exposure must re-evaluate them and may not bypass accepted HA/security/abuse requirements.

A triggered gate blocks real production-data use/release progress; it does not force premature production infrastructure while HullQ remains in local/internal development using synthetic/disposable data.

## Gate 3 — technical native Search abstraction trigger

Current accepted buyer-facing hard technical native-inventory Search criteria:

```text
1 — draft_max
2 — keel_configuration
```

The first criterion proved the concrete end-to-end path. SLICE-0055 then satisfied the accepted second-criterion comparison obligation and generalized the genuinely shared design/configuration production mechanics while retaining criterion-specific decoding/mapping behind bounded adapters.

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

The `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` marker records the number already owner-accepted on canonical main. It advances only through an acceptance closure that actually adds another accepted hard technical native-inventory Search criterion; the owner-direct pivot does not increment it.

### Commercial Search independence

Separately from criterion count/abstraction, every future Search capability must preserve the owner-direct rebaseline invariant:

```text
commercial consideration MUST NOT affect
organic eligibility
organic match classification
organic ordering
```

This applies across broker and private inventory. Payment for verification may produce/process evidence but may not buy a Search truth outcome.

## Gate 4 — workflow-overhead reassessment

**Current status: PASS.** The mandatory post-SLICE-0056 evidence-based reassessment is recorded in `docs/POST_SLICE_0056_WORKFLOW_REASSESSMENT_2026-09-18.md`. It found material independent-review defects in all six accepted SLICE-0051 through SLICE-0056 implementation slices, so mandatory implementation review/Owner Acceptance gates remain. Efficiency changes are limited to boundary/risk-focused review, delta-first amendment re-review, autonomous reviewer continuation and approval-autonomy for routine implementation work.

A mandatory workflow reassessment becomes due at the earlier of:

```text
A. five further owner-accepted primary slices after SLICE-0051
   → immediately after SLICE-0056 becomes owner-accepted

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
DUE
PASS
```

Rules:

- through accepted SLICE-0055, `NOT_DUE` is valid unless the production-pilot trigger fires first;
- the SLICE-0056 acceptance closure MUST atomically move the marker from `NOT_DUE` to `DUE`;
- once SLICE-0056 is accepted, `NOT_DUE` is invalid;
- `DUE` is a valid canonical between-slice state but blocks SLICE-0057 readiness/start;
- before SLICE-0057 can become READY, the evidence-based reassessment must be completed, owner-accepted, and the marker changed to `PASS`;
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

After the 2026-09-14 owner-direct pivot, any readiness that touches listing/supply, seller identity/verification, representation conflict, referral, marketplace monetization or Search must additionally inspect:

```text
docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md
specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md
```

A readiness package may not rely on the superseded broker-only/FSBO-out-of-scope assumption.

## Relationship to capability selection

These gates constrain execution; they do not choose the next product capability.

Current queue after accepted SLICE-0059 is:

```text
SLICE-0060
```

Queue number does **not** select a capability. The mandatory post-SLICE-0056 workflow reassessment remains `PASS`; SLICE-0059 acceptance does not change the technical-criterion count, workflow gate, production-readiness gate or launch state. SLICE-0060 requires fresh post-SLICE-0059 repository/product reconciliation, capability selection, readiness preparation, independent readiness review and merge before `START_SLICE`.
