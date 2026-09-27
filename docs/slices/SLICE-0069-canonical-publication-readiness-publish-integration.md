# SLICE-0069 — Canonical PublicationReadiness + Publish Integration

**Type:** IMPLEMENTATION
**Status:** READY
**Status set by this handoff:** `READY`
**Stage:** Broker launch path — publication/current-public integration
**Depends on:** SLICE-0068 owner-accepted / DONE
**Normative contract:** `specs/MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md`

## Capability

Deliver one coherent broker/public-market capability:

```text
Organization-owned NativeListing DRAFT
→ canonical PublicationReadiness
→ authoritative publish-time re-evaluation
→ DRAFT -> ACTIVE
→ canonical CurrentPublicEligibility
→ public listing + mixed-media gallery
→ Direct Search/current-market surfaces reuse the same public-eligibility authority
```

This is the accepted execution-focus step C after SLICE-0068 media/gallery.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
The slice closes one vertical product outcome: an authorized broker can take the already-created, media-equipped NativeListing from DRAFT through canonical publication into a buyer-visible/current-market listing without parallel readiness/public-eligibility rules.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can observe canonical publish blockers in Broker Workspace, publish a genuinely ready DRAFT, resolve the resulting ACTIVE listing through the public page with its public mixed-media gallery, and verify that loss of a current-public requirement suppresses buyer surfaces without rewriting lifecycle.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted 2026-09-26 broker-launch sequence explicitly places canonical PublicationReadiness + publish integration after promotion and minimum viable media/gallery. SLICE-0067 completed promotion and SLICE-0068 completed media/gallery; 0069 is the next vertical step.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current `origin/main` after accepted SLICE-0068, D15/D22/D29, broker-launch execution focus, Broker Workspace launch gate, accepted lifecycle/freshness/public-read/Search implementations, current media contract/implementation and migration state were inspected. Existing SLICE-0049 publish completeness and SLICE-0052 public/current Search eligibility are now subsets of the accepted later D22/D29 direction and must be reconciled rather than copied.

**TRIGGER GATES CHECK:** PASS  
SLICE-0069 adds no technical Search criterion, starts no external production data/pilot/paid plan/public production launch, and therefore does not trigger Production Readiness. Broker Workspace Launch Gate remains NOT_READY.

## Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

- professional Broker Workspace Organization/Membership/MFA boundary;
- Organization publishing-eligibility evaluator;
- NativeListing DRAFT/ACTIVE/WITHDRAWN lifecycle and immutable transition history;
- publication-triggered freshness evidence and reconfirmation;
- immutable creation-envelope MarketEpisode link with FK;
- MarketEpisode -> PhysicalBoat durable chain;
- current NativeListing offer head;
- current Organization PhysicalBoat claim head;
- SLICE-0068 MediaAsset/MediaPlacement truth, image processing/rights/public-usability, ordering/cover, same-Organization reuse and YouTube references;
- public NativeListing exact-read surface;
- Direct Search with exactly two technical criteria;
- existing lifecycle+freshness current-market admission subset.

### DECIDED_NOT_YET_IMPLEMENTED — owned here where stated

- D22 one canonical PublicationReadiness evaluator;
- D22 preflight + authoritative publish-time re-evaluation;
- replacement of SLICE-0049 legacy publication-completeness shortcut with canonical readiness;
- D29 canonical CurrentPublicEligibility;
- D29 ACTIVE-but-suppressed structured reasons in Broker Workspace;
- D29 current-public integration into exact public listing and both Search paths;
- public mixed-media gallery projection using accepted 0068 truth;
- listing-scoped public derivative image route.

### EXPLICITLY_DEFERRED

- D20 explicit MarketEpisode-resolution revision authority and D21 ACTIVE episode correction;
- WITHDRAWN -> ACTIVE republish/relist;
- owner-direct publication;
- post-promotion offer/fact editing;
- direct uploaded VIDEO;
- HEIC/HEIF;
- actual Broker-CI slide rendering when no accepted public CI source exists;
- complete D24 purge/backup-deletion worker;
- cross-Organization media grants;
- new moderation/safety domain;
- leads/CRM, outcome, analytics, import/export, payments;
- Search criterion #3+.

### GENUINELY_OPEN

Implementation details that do not alter accepted semantics: exact module/table-free read-model factoring; stable reason-code token naming; whether readiness read is embedded in inventory projection or exposed through a dedicated endpoint in addition to it; exact listing-scoped public media URL shape; efficient reuse/caching of canonical current-public evaluation inside one request; exact locking/recheck implementation provided stale readiness cannot publish and lock order composes with accepted 0068 MediaAsset -> NativeListing -> gallery-head ordering.

### CONFLICT_OR_REGRESSION

No current implementation regression found.

There is one accepted-later-vs-legacy semantic gap to reconcile in this slice, not a product-decision conflict:

- SLICE-0049 publish currently checks only non-null episode -> existing episode -> existing PhysicalBoat -> current offer;
- public listing/Search currently gate primarily on ACTIVE + freshness.

D22/D29 explicitly supersede those predicates as the canonical future boundary. 0069 owns that reconciliation.

D20/D21 are not a blocker: until their later explicit resolution-head authority exists, the immutable non-null FK-valid NativeListing creation-envelope `market_episode_id` remains the only implemented current episode authority. 0069 must not invent another interim authority.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

Broker Workspace Launch Gate remains `NOT_READY`. External broker self-service pilot, paid broker plan and public production launch remain not started.

## Scope

Implementation may span:

- canonical publication/current-public domain/application evaluators;
- persistence read/locking helpers required for one safe authoritative snapshot;
- lifecycle publish integration;
- Broker Workspace readiness/suppression API + UI;
- public listing read/API/page;
- public listing-scoped derivative image delivery;
- mixed-media public gallery composition;
- both accepted Direct Search paths;
- tests and retained proofs.

No new marketplace identity, lifecycle state, Search criterion, media-rights model or episode-resolution authority may be introduced.

## Mandatory implementation invariants

The implementation MUST satisfy every rule in `MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md`, especially:

1. exactly one canonical PublicationReadiness rule set serves preflight and publish;
2. publish re-evaluates current truth under race-safe authority;
3. SLICE-0049 legacy completeness is not retained as a second publication definition;
4. required offer/PhysicalBoat/media rules match D22 exactly;
5. pre-D20 episode resolution uses only the existing immutable creation link;
6. BoatDesign/Search fit/multiple-photo quality never block publication;
7. exactly one canonical CurrentPublicEligibility authority owns D29;
8. ACTIVE != current-public;
9. suppression does not rewrite lifecycle;
10. public listing and both Search paths consume canonical current-public eligibility;
11. Search criterion semantics/count remain exactly unchanged;
12. public gallery exposes only accepted public media truth;
13. private originals/object keys/uploader/provenance/source notes never leak;
14. public image delivery is listing-scoped and fail-closed;
15. YouTube uses normalized structured identity only;
16. Broker Workspace exposes structured readiness/suppression reasons;
17. concurrency composes with SLICE-0068 locking and cannot publish stale readiness;
18. withdraw/reconfirm remain semantically unchanged.

## Readiness stop conditions

Stop implementation and return for reassessment if any of these emerges:

- D22 cannot be implemented without first creating D20's episode-resolution revision authority;
- a new rights/identity/Organization/publication policy decision is required;
- a new moderation/safety domain would be required merely to complete current-public eligibility;
- public media delivery would require exposing raw provider/object identity;
- canonical Search truth would need to change rather than only current-inventory admission;
- safe publish-time re-evaluation cannot be achieved without a materially new global transaction/locking policy;
- an irreversible migration beyond the existing accepted authorities is discovered.

## Acceptance

Independent exact-head implementation review must verify the normative contract and required proof matrix. Owner Acceptance remains mandatory before merge.

The initial implementation prompt must come only from `START_SLICE.bat` after this readiness package is independently reviewed, remote gates are green and readiness is merged to `main`.
