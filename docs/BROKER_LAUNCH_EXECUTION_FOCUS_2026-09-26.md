# HullQ — Broker Launch Execution Focus

**Date:** 2026-09-26  
**Status:** OWNER_ACCEPTED EXECUTION DIRECTION  
**Purpose:** convert the existing domain/architecture foundation into the shortest coherent path to real broker-created inventory and a real buyer→broker loop without weakening HullQ truth, authorization or launch-gate requirements.

This document changes execution priority and slice-sizing discipline. It does **not** supersede accepted domain decisions, the Broker Workspace Launch Gate, the Mandatory Capability Register, Search truth rules, source-rights rules or the normal exact-head review / Owner Acceptance workflow.

## 1. Why this adjustment exists

By SLICE-0065 HullQ has accumulated substantial accepted foundations:

- technical Search and public marketplace read surfaces;
- authenticated broker and owner-direct workspaces;
- Organization/Membership/MFA authorization;
- immutable/revisioned listing-offer and PhysicalBoat claim truth;
- lifecycle/freshness controls;
- professional draft persistence/recovery;
- publishing-Organization identity;
- explicit provenance and fail-closed truth semantics.

The remaining product risk is no longer primarily whether HullQ can model these concepts correctly. The immediate risk is whether that foundation can become a coherent broker workflow that reaches real users.

From this point forward, ordinary capability selection should strongly prefer work that closes the following operational loop:

```text
BROKER CREATES
→ BROKER ADDS MEDIA
→ BROKER PUBLISHES
→ BUYER CONTACTS
→ BROKER HANDLES LEAD
→ BROKER EDITS / MAINTAINS INVENTORY
→ BROKER CLOSES / RECORDS OUTCOME
```

Work outside this loop may still be selected when it removes a real blocker, protects truth/security/legal safety, satisfies a triggered mandatory capability or has clearly higher product/business leverage.

## 2. Immediate path after the already-selected SLICE-0066

SLICE-0066 remains unchanged:

```text
Required-Response / Assertion Input Alignment
```

It removes the last repository-proven build-year response-shape blocker before truthful promotion.

After 0066 acceptance, reassessment should prefer the shortest safe sequence toward a broker-created public listing:

### A. Professional draft → marketplace promotion

Target outcome:

```text
ProfessionalListingDraft
→ PROMOTION_READY
→ atomic materialization
→ NativeListing DRAFT
```

This must preserve the accepted D01–D12/D18–D21 semantics in `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`.

### B. Minimum viable media/gallery

Target outcome:

```text
NativeListing DRAFT
→ upload/validate/process media
→ order/select cover
→ rights-valid public-usable media state
```

Media remains governed by D13–D15/D24 and the accepted security/privacy/storage direction.

### C. Canonical PublicationReadiness + publish integration

Target outcome:

```text
NativeListing DRAFT
+ canonical current readiness
→ Publish
→ ACTIVE
→ current public listing surface
```

HullQ already has a public NativeListing read path. This work is therefore about allowing normal broker-created inventory to feed the existing public surface truthfully, not inventing a second public-listing architecture.

### D. Durable buyer contact / lead creation

Target outcome:

```text
public listing
→ buyer contact request
→ durable Lead
→ listing/source/Organization attribution captured at creation
```

### E. Broker lead operating surface

Target outcome:

```text
Lead
→ broker inbox/detail
→ assignment/status/notes/follow-up
```

A full enterprise CRM is not required for the first coherent broker baseline; the Broker Workspace Launch Gate remains controlling.

### F. Broker inventory editing

Target outcome:

```text
one broker-facing Edit listing flow
→ offer revisions
→ PhysicalBoat claim revisions where applicable
→ price/status/details maintenance
→ optimistic concurrency / no silent overwrite
```

The accepted D11/D19/D23 semantics remain controlling.

## 3. Import / onboarding priority

Structured bulk/source import is strategically important for broker acquisition, but it must feed the normal HullQ draft/marketplace workflow rather than become a second truth pipeline.

Accepted direction remains:

```text
CSV / feed / lawful source integration
→ import staging
→ validation / durable source mapping
→ ProfessionalListingDraft or mapped target
→ normal HullQ promotion / edit workflows
```

Therefore:

- do not put bulk import ahead of a working ProfessionalListingDraft→marketplace path;
- once the coherent create/publish/operate path is stable, move structured bulk onboarding forward aggressively;
- REQ-BROKER-027 remains mandatory before scaled broker onboarding;
- broker website/API/feed/CSV integration may be supported when lawful and technically appropriate, but public-page scraping is not assumed or authorized by this execution record.

Import is a go-to-market accelerator, not a reason to bypass identity/provenance/reconciliation semantics.

## 4. Pilot vs paid/public launch

Do not collapse the existing governance gates.

### First external broker self-service pilot

Still requires:

```text
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = PASS
```

The launch gate remains the controlling checklist for coherent inventory, media, lead, authorization and usability behavior.

### Scaled broker onboarding

Before scale:

```text
REQ_BROKER_027 structured bulk onboarding/import = IMPLEMENTED
```

### Paid broker activation / broad public production launch

Still requires the registered commitments including:

- explicit sale/outcome workflow;
- inventory portability / no lock-in export;
- pre-publication Search-fit diagnostics;
- engagement/performance reporting;
- post-pilot real-broker validation where applicable.

This execution focus accelerates the route to those gates; it does not waive them.

## 5. Risk-based slice sizing

The existing ONE-CAPABILITY rule remains, but "one capability" means **one coherent user-visible or business-critical outcome**, not "one database column", "one endpoint" or "one layer".

### Keep slices small when they introduce material independent risk

Examples:

- identity allocation/resolution;
- truth/provenance semantics;
- authorization / tenant isolation / MFA;
- money/payment;
- destructive or difficult-to-reverse data migration;
- cross-Organization ownership/rights;
- concurrency/idempotency authority;
- media rights/privacy/security;
- lifecycle/outcome semantics;
- a new Search eligibility rule.

These should continue to use narrow contracts and explicit decisions.

### Permit larger vertical slices when work is mainly composition

A single slice may span persistence + domain/application + API + frontend + tests when all of the following are true:

1. the work delivers one coherent user-visible capability;
2. the layers are mechanically necessary to that capability;
3. no second independent product/domain policy is being smuggled into the slice;
4. accepted truth/auth/concurrency rules already decide the material semantics;
5. rollback/review remains tractable;
6. the slice can still be independently validated end to end.

This explicitly prevents governance from forcing low-risk implementation into artificial micro-slices.

### Stop condition

If implementation discovers a new material policy decision, identity ambiguity, authorization boundary or irreversible migration, stop and split/reassess rather than hiding the risk inside a larger vertical slice.

## 6. Execution-priority test for every post-0066 reassessment

Before selecting a non-blocker capability, ask:

> Does this materially move HullQ toward a working Broker→Listing→Buyer Lead→Broker Operation loop?

If **YES**, it receives priority unless another triggered mandatory capability or safety/truth blocker has higher leverage.

If **NO**, the reassessment must state the concrete reason it should interrupt the launch path.

This is an execution-priority rule, not a guarantee that every next slice has a predetermined number or scope.

## 7. Public listing / SEO clarification

HullQ already has accepted public NativeListing read behavior from earlier marketplace slices.

Therefore the near-term missing capability is not "build a public listing page from zero". It is:

```text
normal broker-created inventory
→ truthfully reaches the existing public listing/read path
```

Broader SEO hardening remains useful later, but it should not preempt the coherent broker inventory / lead loop unless a concrete discoverability blocker is demonstrated.

## 8. Research artifact repository hygiene

Current repository size is materially influenced by retained accepted research artifacts, including large immutable JSON evidence packages.

Those artifacts currently support:

- deterministic offline reproduction;
- accepted evidence hashes;
- CI replay;
- auditability of prior research decisions.

Therefore they are **not** removed as part of this launch acceleration.

Future repo-hygiene work may move large immutable artifacts to durable external object/release storage only when it preserves:

- immutable content hashes in-repo;
- deterministic/reliable retrieval;
- accepted evidence provenance;
- CI/offline reproducibility where still required;
- long-term accessibility.

This is non-blocking technical hygiene and must not interrupt the broker launch path unless repository size demonstrably becomes a development/CI/tooling blocker.

## 9. What this record does not authorize

It does not:

- preassign later slice numbers;
- bypass post-slice reassessment;
- merge promotion + publication into one truth state;
- bypass media rights/security;
- waive Broker Workspace Launch Gate or Mandatory Capability Register requirements;
- authorize scraping;
- relax exact-head review / remote CI / Owner Acceptance;
- change organic Search commercial independence;
- change any accepted D01–D29 domain decision.

## 10. Practical execution rule

From accepted SLICE-0066 onward:

```text
strict truth remains fixed
governance remains
micro-slicing is no longer a goal
vertical launch progress becomes the default
```

The desired outcome is not fewer checks. It is more product progress per reviewed slice where risk permits.
