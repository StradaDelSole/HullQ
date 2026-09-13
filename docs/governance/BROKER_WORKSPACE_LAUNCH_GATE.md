# HullQ — Broker Workspace Launch Gate

**Status:** ACCEPTED OWNER DIRECTION  
**Accepted:** 2026-09-13  
**Purpose:** hard product-quality gate preventing broker self-service, paid broker plans or public launch before the professional workspace is genuinely launch-ready

<!-- BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY -->
<!-- BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED -->
<!-- PAID_BROKER_PLAN_STATUS: NOT_STARTED -->

## Trigger

The gate MUST be `PASS` before any of these becomes true:

```text
1. a real external broker self-service production pilot begins
2. a paid broker plan/subscription becomes active
3. HullQ enters public production launch
```

Whichever threshold comes first controls.

Allowed gate states:

```text
NOT_READY
IN_PROGRESS
PASS
```

Allowed broker self-service pilot / paid-plan states:

```text
NOT_STARTED
ACTIVE
```

This gate is independent from `docs/governance/PRODUCTION_READINESS_GATE.md`.

Production Readiness answers whether HullQ is operationally safe/recoverable enough for production. This Broker Workspace Launch Gate answers whether the professional supply-side product is good enough to expose/charge for. Both gates may be required at the same boundary.

Later mandatory broker capabilities and their timing triggers are controlled by:

```text
docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md
```

Passing this gate does not cancel later mandatory commitments.

## Why this is hard-gated

HullQ is broker-first. Inventory quality and supply retention depend on the daily experience of professional brokers. A technically functional CRUD form is not an acceptable launch substitute.

The controlling product direction is:

```text
docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md
```

Normative requirements:

```text
specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md
```

Retained source addendum:

```text
docs/BROKER_WORKSPACE_ADDENDUM_2026-09-12.md
```

## Validation order

Real external broker participation is deliberately **not** a prerequisite for defining or implementing the first coherent broker-workspace baseline.

Before this gate can become `PASS`, HullQ uses:

- accepted Project Owner/product direction;
- domain/architecture correctness;
- representative task/usability testing;
- explicit incumbent/alternative workflow benchmarking.

`PASS` then permits the first real external broker self-service pilot. The pilot becomes the first required source of real professional-user falsification evidence.

After that pilot, `POST_PILOT_REAL_BROKER_VALIDATION_STATUS` in the Mandatory Capability Register must become `PASS` before scaled broker onboarding, paid broker activation or broad public production launch.

This prevents a circular requirement to obtain real broker feedback before the product is allowed to reach a real broker while still making real broker validation mandatory before scaling/commercial rollout.

## PASS evidence

Changing the marker to `PASS` requires repository-backed evidence for every applicable section below. Intention, mockups or roadmap prose alone do not satisfy the gate.

### 1. Authentication, Organization and authorization

- Auth0 EU authentication path exists for the external broker flow;
- HullQ Account/Organization/Membership/role state is durable and authoritative;
- listing/lead/sales authorization is enforced server-side;
- privileged publishing uses accepted MFA/step-up rules where applicable;
- multi-member Organization behavior is tested.

### 2. Low-friction inventory workspace

The external broker can perform the launch-critical inventory jobs without operator/admin intervention:

- create a listing;
- resume an unfinished listing without data loss;
- recover recent work from ordinary connectivity interruption without silent loss;
- edit listing facts/offer facts;
- update price/status where supported;
- publish/withdraw/reconfirm according to accepted domain rules;
- use media workflow where launch inventory requires media;
- avoid retyping information HullQ already knows when safe reuse is possible.

The workflow must preserve `DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH`.

Before PASS, `REQ_BROKER_024_STATUS` in the Mandatory Capability Register must be `IMPLEMENTED`.

### 3. Media operations and broker identity

If launch listings include media:

- multi-file upload is practical for broker use;
- ordering/cover selection is available;
- accepted quarantine/validation/re-encode/EXIF/privacy/storage rules are enforced;
- retry/error recovery does not silently lose listing work.

The publishing Organization/broker identity must be explicit on the broker/listing surface. Legitimate compliant broker branding must not be erased merely because it is broker branding. This does not override media rights/security/privacy rules.

Before PASS, `REQ_BROKER_023_STATUS` in the Mandatory Capability Register must be `IMPLEMENTED`.

### 4. State and sales/outcome model

The production model must not use one overloaded status for unrelated concepts.

Evidence must show the applicable launch version distinguishes:

- publication/lifecycle;
- freshness/reconfirmation;
- commercial/deal state where exposed;
- sale/outcome state where exposed.

A stale or withdrawn listing must never silently become SOLD. Sale/outcome facts must be explicit.

### 5. Durable leads and attribution

A supported HullQ lead/contact request must be a durable first-class record with enough context to answer:

```text
Which listing generated this lead?
Where did it come from?
Which source/channel/campaign/search context is available?
Which Organization/broker owns or handles it?
When was it received?
What happened next?
```

Attribution must be captured at lead creation where available rather than reconstructed later from aggregate reporting.

### 6. Broker lead workflow

The external broker must have a usable lead operating surface with at least the launch-bounded equivalents of:

- inbox/queue;
- lead detail;
- source context;
- assignment;
- status/stage;
- notes/timeline;
- follow-up/response visibility;
- filtering/search sufficient for routine broker work.

A full enterprise CRM is not required, but an email-only notification flow is insufficient for PASS.

### 7. Performance and source-to-outcome analytics

The workspace must provide meaningful operational insight rather than vanity counters.

At minimum launch evidence must show the supported funnel can report its available facts by listing/source and, where implemented, broker/office:

```text
listing exposure / views
-> leads
-> handled/qualified state
-> outcome where explicitly recorded
```

Response-time evidence must be available for supported broker response events.

Where explicit sale/outcome recording exists, source-to-outcome analysis must be structurally possible.

### 8. Sales close-out

If sale/outcome capability is part of the launch workspace, the broker must have a short explicit close-out flow.

It must preserve unknown values rather than force achieved price or other unavailable facts.

If the first self-service pilot intentionally excludes sale/outcome entry, this may be marked NOT_APPLICABLE for that pilot only, but it becomes mandatory before paid broker activation/public launch unless an owner-accepted superseding product decision explicitly changes that requirement.

### 9. Usability benchmark

PASS requires an evidence-backed usability assessment, not a subjective declaration that the UI feels good.

The assessment must include representative broker tasks:

1. create/publish a listing from an already-known HullQ design/configuration context;
2. edit price/status/details;
3. add/reorder media where applicable;
4. open a lead and identify its source;
5. assign/update/follow up the lead;
6. complete the applicable commercial/sale outcome workflow.

For each task, record at least:

- test scenario and starting assumptions;
- observed completion time;
- material interaction/friction points;
- errors/recovery issues;
- whether the task completed without operator assistance;
- corrective disposition for material findings.

Pre-pilot evidence may use representative internal/test participants. It does not require real external brokers. Real external broker evidence begins after PASS through the permitted pilot and then becomes mandatory before scale/commercial rollout as defined above.

### 10. Competitive benchmark

Before PASS, document a comparison against at least two relevant incumbent/alternative professional broker systems or equivalent available workflows.

Boats Group / YachtWorld / BoatWizard are explicit reference competitors when access permits, but the gate is not tied to one vendor.

For launch-critical tasks, the record must identify:

```text
BETTER
EQUIVALENT
DEFICIENT
NOT_COMPARABLE
```

A material `DEFICIENT` result in listing creation, lead-source visibility, lead handling or essential inventory state management blocks PASS until corrected or explicitly owner-accepted as a bounded exception.

### 11. Payment/entitlement boundary

Before `PAID_BROKER_PLAN_STATUS` becomes `ACTIVE`:

- the Broker Workspace Launch Gate is PASS;
- post-pilot real-broker validation is PASS if a pilot has occurred;
- applicable mandatory-capability triggers in `BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md` are satisfied;
- payment/subscription state is durable and auditable;
- entitlement checks do not make core inventory management unusable;
- failure/cancellation/retry semantics are specified and tested.

Exact provider/pricing is owned by the payment/monetization capability and is not predetermined by this gate.

## PASS record requirement

A PASS change must name concrete implementation slices, tests, retained proof, representative usability evidence and benchmark artifacts satisfying the sections above.

It must also prove:

```text
REQ_BROKER_023_STATUS = IMPLEMENTED
REQ_BROKER_024_STATUS = IMPLEMENTED
```

Independent review must reject PASS when evidence is limited to screenshots, mockups, feature lists or provider documentation.

## Reassessment

Reassess this gate when a material broker-product boundary changes, including:

- first paid broker tier;
- substantial inventory workflow redesign;
- new lead channel/call tracking;
- major sales/outcome workflow expansion;
- new Organization/office hierarchy;
- material authorization model change.

Reassessment does not automatically reset PASS, but it must verify that the accepted evidence still matches the active production boundary.
