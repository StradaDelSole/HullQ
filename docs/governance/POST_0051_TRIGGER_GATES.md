# HullQ — Post-SLICE-0051 Trigger Gates

**Status:** ACCEPTED OWNER DIRECTION — amended by owner-direct marketplace pivot when merged  
**Accepted:** 2026-09-13; mixed-supply amendment 2026-09-14  
**Scope:** post-SLICE-0051 reassessment, slice readiness, production-data/pilot readiness, Search abstraction and process governance

<!-- POST_0051_ARCHITECTURE_RECONCILIATION: PASS -->
<!-- TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 11 -->
<!-- WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056 -->
<!-- WORKFLOW_REASSESSMENT_STATUS: PASS -->
<!-- BUYER_CONTACT_EMAIL_VERIFICATION_STATUS: PENDING -->

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
- **PlanetScale Managed PostgreSQL 18** as the accepted intended production database provider per Owner-accepted `architecture/decisions/ADR-0012-planetscale-managed-postgresql.md` (superseding the earlier DigitalOcean Managed PostgreSQL 18 FRA1 target); actual EU region, plan economics, security, backup/restore and standby/failover are not yet provider-verified or provisioned, and no purchase is authorized;
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
3 — loa (loa_min / loa_max counted once)
4 — rudder_configuration
5 — hull_configuration
6 — cockpit_position
7 — deck_saloon
8 — beam (beam_min / beam_max count once)
9 — hull_material (GRP_FIBERGLASS, STEEL, ALUMINUM, WOOD)
10 — power_drive_configuration (POWER ONLY; SHAFT, STERNDRIVE, POD, WATERJET, OUTBOARD; first Power criterion)
11 — power_engine_count (POWER ONLY; exact public installed principal propulsion count 1–8; current immutable publisher claim authorable 1–32; combinable MUST/AND with drive)
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

The `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` marker records the number already owner-accepted on canonical main. SLICE-0085 added exactly **two** hard public technical dimensions (LOA range counted once and qualified rudder counted once), changing the count **2 → 4**. Owner-accepted SLICE-0086 adds exactly **three** further orthogonal qualified structural hard dimensions — `hull_configuration`, `cockpit_position`, `deck_saloon` — changing it **4 → 7** in the separate formal 0086 acceptance closure (`docs/slices/SLICE-0086-acceptance-closure.md`), not in readiness or implementation. Eight technical query keys are seven criteria because `loa_min` and `loa_max` count as one LOA dimension. `OTHER` hull/cockpit and `NONE` deck are concrete claim-only, never additional public filters/dimensions; buyer evidence requires generation/NamedVariant qualified BoatDesign facts **and** independent current nonconflicting PhysicalBoat publisher assertions. Imported platform tags cannot be promoted by inference. The existing keel six-value public vocabulary remains unchanged; `LONG_KEEL` stays unsupported and adds no separate dimension without future independently decided taxonomy/claim mapping. The common static typed `CriterionDefinition`/FieldResolution/configuration/qualified concrete-claim kernel must be reused without an arbitrary schema resolver or a third structural copy. Buyer sensitivity for any LOA/rudder/structural criterion remains deliberately unavailable rather than silently omitting constraints; old-only draft/keel sensitivity is preserved. Owner-accepted SLICE-0087 adds Beam overall width min/max (one semantic dimension) and the conservative GRP_FIBERGLASS/STEEL/ALUMINUM/WOOD Hull Material hard filter (one), advancing the accepted Gate 3 count 7 → 9 only in the formal separate closure. Eleven public technical query keys are nine dimensions because LOA and Beam min/max are each one. Broader concrete PhysicalBoat material values FERROCEMENT/CARBON_COMPOSITE/OTHER remain claim-only; design wood_composite/carbon are not mapped by inference. The common FieldResolution/NamedVariant/PhysicalBoat same-configuration AND evaluation, UNKNOWN/conflict guards and impartial organic Search remain unchanged. Count advances only after reviewed Owner-accepted implementation closure; production readiness and owner-direct gates remain separate.

**SLICE-0093 Owner-accepted addition (2026-10-28):** Global technical native Search criterion count advances **9 → 10** only in the separate reviewed SLICE-0093 docs-only Owner acceptance closure, after implementation PR #390 was independently reviewed, explicitly Owner-accepted and squash-merged as `c38a60d821a6e9a88fba023a0008a36a3dcd51e1`. The per-domain split is **SAIL 9 / POWER 1**. This first Power dimension is the exact five-token current drive arrangement, a distinct category-isolated request route reusing the existing categorical configuration/qualified-current-claim kernel rather than a third evaluator. It requires the publishing Organization's own positive POWER category and specific current drive in one revision, with D29 and fail-closed design/factory-vs-installation provenance. Existing Sail nine criteria and source truth stay unchanged. **No new Power criterion, category-agnostic browse, full Power parity, real external broker data/pilot or public release** is authorized; #355 hosted Search scaling and pre-real-data STOP, #366 joint release and #372 remaining Power duties stay OPEN. The launch pack remains NOT_STARTED and Production Readiness remains IN_PROGRESS.

**SLICE-0094 Owner-accepted addition (2026-10-28):** Global technical native Search criterion count advances **10 → 11** only in the separate SLICE-0094 docs-only Owner acceptance closure after independently reviewed implementation PR [#393](https://github.com/StradaDelSole/HullQ/pull/393) was explicitly Owner-accepted at exact HEAD `76f542635d3d04ae9e8c4c05c8a704912f0ba3d4` and squash-merged as `9ac9705825bcc3bdab83a85c74f011eaf285d67a`. Per-domain split is **SAIL 9 / POWER 2**. The second Power criterion is the current, installed principal propulsion engine count: strict public exact count 1–8, publisher-editable typed current count 1–32. This numeric RANGE(min=max) criterion shares the existing typed configuration/MUST-AND kernel; combined `power_drive` + `power_engine_count` accepts positive only when both qualify from the same current publishing Organization/revision and the same actual FieldResolution-qualified BoatDesign/NamedVariant configuration. Raw factory values and cross-revision/variant combinations never suffice. All five Power buyer locales, broker edits, truthful source-labelled evidence, D29 and noindex remain applicable; original Sail nine criteria and Power drive-only behavior unchanged. Retained PG18 0/40/200 synthetic both-plane comparison and browser/SSR proof do **not** authorize production Search scale. **No additional Power criterion or Power Broker Search-fit parity, external real data/pilot, category-agnostic browse or public launch** is authorized; #355 pre-real-data/pilot Search scale, #366 joint Sail+Power release and #372 remaining Power commitments stay OPEN. Production Readiness remains IN_PROGRESS, Launch Pack NOT_STARTED.

### Commercial Search independence

Separately from criterion count/abstraction, every future Search capability must preserve the owner-direct rebaseline invariant:

```text
commercial consideration MUST NOT affect
organic eligibility
organic match classification
organic ordering
```

This applies across broker and private inventory. Payment for verification may produce/process evidence but may not buy a Search truth outcome.

## Gate 3A — buyer-contact email verification follow-up

**Current status: PENDING.**

Accepted D32 permits anonymous buyer contact requests and SLICE-0070 may persist the submitted contact email as explicitly `UNVERIFIED`. This is a temporary product boundary, not permission to forget verification.

Hard trigger:

```text
before the first real external production buyer-contact flow is exposed or relied upon
OR before HullQ represents/uses a buyer contact email as verified/trusted,
whichever comes first
→ BUYER_CONTACT_EMAIL_VERIFICATION_STATUS MUST be IMPLEMENTED
```

Allowed states:

```text
PENDING
DUE
IMPLEMENTED
```

An authenticated HullQ Account does not by itself verify an arbitrary email entered into a contact form. Delivery success, broker response or later lead handling likewise do not constitute verification evidence.

The implementing capability must provide explicit verification evidence/state transition and must preserve anonymous-contact usability unless a later Owner-accepted decision changes that product boundary.

This trigger does not require SLICE-0070 to build email delivery/token infrastructure while HullQ remains internal/synthetic. It prevents public/real buyer-contact exposure from silently shipping with permanently unverified contact identity.

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
