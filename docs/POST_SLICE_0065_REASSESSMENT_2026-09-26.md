# HullQ — Post-SLICE-0065 Repository / Product Reassessment

**Date:** 2026-09-26  
**Canonical base:** `origin/main` at `6c24674fc498e4b3f9ef89e56d6ef8034652a50f`  
**Accepted through:** SLICE-0065  
**Queue:** SLICE-0066 — Required-Response / Assertion Input Alignment selected below, not yet implementation-authorized

## 1. Purpose

SLICE-0065 is owner-accepted, closure-complete and locally finished. This reassessment selects the smallest safe next capability from canonical repository truth before any new implementation starts.

The 2026-09-26 owner decision series is now recorded in `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` and is controlling where relevant.

## 2. Canonical state after SLICE-0065

The professional path now includes:

```text
authenticated Account / Organization / Membership / MFA boundary
→ private ProfessionalListingDraft create/list/read/update
→ optimistic concurrency
→ connectivity-resilient local recovery
→ broker_description retained as professional-only draft input
→ optional boat_name has an accepted PhysicalBoat claim destination
→ existing NativeListing inventory overview
→ existing complete NativeListing DRAFT: Publish
→ existing ACTIVE NativeListing: Withdraw / Reconfirm
```

No draft-to-marketplace promotion exists.

## 3. Repository-proven remaining blocker before truthful promotion

The shared draft parser currently models:

```python
build_year: int | None
```

and accepts only an integer when `physical_boat.build_year` is present.

The canonical Marketplace field registry defines `physical_boat.build_year` as:

```text
REQUIRED_RESPONSE
allowed: VALUE_ASSERTION | UNKNOWN
```

The existing PhysicalBoat claim model already implements `BuildYearClaim(VALUE_ASSERTION(year) | UNKNOWN)`.

Therefore the draft layer currently distinguishes only:

```text
OMITTED
VALUE_ASSERTION(year) via legacy integer form
```

but cannot encode the explicit required response:

```text
UNKNOWN
```

Promotion now would either reject a truthful broker who does not know the build year or incorrectly infer UNKNOWN from omission. Both violate accepted truth semantics.

## 4. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

- shared OwnerDirect/Professional common draft vocabulary is exactly nine keys;
- incomplete drafts may omit every key;
- persisted draft input is private pre-market state, not marketplace truth;
- `physical_boat.build_year` Marketplace truth is REQUIRED_RESPONSE and allows VALUE_ASSERTION or UNKNOWN;
- PhysicalBoat `BuildYearClaim` already represents VALUE_ASSERTION / UNKNOWN;
- omission is conceptually distinct from explicit UNKNOWN in marketplace claim semantics;
- professional local recovery preserves unsaved form input without becoming server truth;
- SLICE-0065 broker_description and boat_name alignment is accepted and merged;
- no draft-to-marketplace promotion currently exists.

### DECIDED_NOT_YET_IMPLEMENTED

- D17: shared draft build-year assertion representation under the existing key;
- legacy integer draft compatibility plus canonical structured serialization;
- UI distinction between unanswered, explicit UNKNOWN and concrete year;
- professional recovery distinction for the new build-year response state;
- later PROMOTION_READY and atomic professional draft promotion.

### EXPLICITLY_DEFERRED

- promotion itself;
- PhysicalBoat/MarketEpisode/NativeListing identity allocation;
- promotion idempotency and duplicate conflict enforcement;
- offer/claim materialization;
- media;
- canonical PublicationReadiness;
- offer/listing editing;
- outcomes, leads, analytics, import/export and buyer alerts.

### GENUINELY_OPEN

None that blocks this bounded assertion-input capability. Later implementation details remain owned by later slices where the owner decisions do not already decide them.

### CONFLICT_OR_REGRESSION

The old workspace-contract wording and current parser shape that define build_year only as an integer conflict with the accepted D17 future-facing direction and with the registry's explicit UNKNOWN-capable REQUIRED_RESPONSE semantics. This slice exists to reconcile that gap without promotion.

## 5. Options considered

### A — implement promotion now

Rejected. Draft input still cannot distinguish omitted from explicit UNKNOWN for required build_year response.

### B — media first

Rejected for sequencing. Media is required before public publication but does not remove the current promotion-readiness input blocker.

### C — Required-Response / Assertion Input Alignment

Selected by Project Owner.

Only `physical_boat.build_year` changes value representation; the key remains unchanged. Legacy integer rows remain readable. New canonical serialization is structured.

### D — generalize all draft fields to assertion objects

Rejected as premature abstraction. Different draft fields do not share identical assertion semantics and there is no current repository-proven need to migrate all nine.

## 6. Selected capability

SLICE-0066:

```text
Required-Response / Assertion Input Alignment
```

Canonical representation:

```json
{
  "physical_boat.build_year": {
    "assertion_kind": "VALUE_ASSERTION",
    "value": 1987
  }
}
```

or:

```json
{
  "physical_boat.build_year": {
    "assertion_kind": "UNKNOWN"
  }
}
```

Omission remains absence of the key.

Legacy persisted/request input:

```json
{"physical_boat.build_year": 1987}
```

remains readable/accepted for compatibility and normalizes internally to VALUE_ASSERTION(1987). Canonical serialization/new writes use the structured form.

## 7. Boundaries

SLICE-0066 does not:

- add a tenth common draft key;
- create marketplace identities or facts;
- promote a draft;
- publish a listing;
- change Search criteria;
- generalize assertion wrappers to unrelated fields;
- add media or offer editing.

Both OwnerDirect and Professional drafts use the same shared parser/serializer semantics.

## 8. Distance estimate

Current directional estimate to first broker-created and publicly visible listing remains approximately four bounded slices including 0066:

```text
0066 assertion input alignment
→ later atomic professional promotion
→ later minimum media/gallery
→ later canonical PublicationReadiness/publish integration
```

This is a planning estimate only. No later slice number or capability is authorized; every accepted slice is followed by fresh reassessment.
