# SLICE-0067 — Acceptance Closure

**ID:** SLICE-0067  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #255  
**Accepted implementation HEAD:** `97056e4c0e413ec392b1d2988a9db43b18a42fc5`  
**Implementation merge commit:** `3fcc88892bbb33bf15da3b63be7e6ff8f0903a36`  
**Independent exact-head ACCEPT review:** 2026-09-27  
**Owner acceptance:** explicitly recorded 2026-09-27

## Accepted capability

SLICE-0067 implements the accepted fresh-identity professional promotion branch:

```text
promotion-ready ProfessionalListingDraft
→ server-minted PhysicalBoat
→ server-minted MarketEpisode
→ server-minted NativeListing DRAFT
→ initial Organization PhysicalBoat claim
→ initial NativeListing offer
→ source draft PROMOTED
```

The complete chain is committed in one PostgreSQL transaction. Promotion does not publish the listing and does not make it ACTIVE/public.

## Accepted implementation behavior

- one authoritative PromotionReadiness evaluator is reused for preflight and mutation-time evaluation;
- exact positive draft version is required;
- the exact Organization-owned draft row is locked before promotion;
- current professional workspace/MFA/PUBLISHER authorization and publishing eligibility are enforced without foreign/unknown draft enumeration;
- first successful promotion mints fresh server-owned PhysicalBoatId, MarketEpisodeId, NativeListingId, PhysicalBoatClaimRevisionId and NativeListingOfferRevisionId;
- no BoatDesignRef is synthesized;
- initial PhysicalBoat claim and NativeListing offer contain only accepted draft-backed truth;
- NativeListing starts in DRAFT lifecycle;
- source draft becomes immutable PROMOTED with frozen version, promoted_at and resulting NativeListingId in the same transaction;
- exact retry at the frozen promoted version returns ALREADY_PROMOTED with the same NativeListingId and creates no second chain;
- stale/mismatched versions return VERSION_CONFLICT with zero mutation;
- D09 database uniqueness is `(publishing_organization_id, market_episode_id) WHERE market_episode_id IS NOT NULL`;
- only a PostgreSQL UniqueViolation naming `ux_native_listings_org_episode` is classified as DUPLICATE_EPISODE; unrelated/unknown unique violations propagate as internal invariant failures after rollback;
- successful browser promotion deterministically clears the exact local recovery envelope before any navigation race and renders immutable promoted result context;
- failed promotion preserves recovery;
- Organization inventory exposes the resulting DRAFT listing through the existing private read path;
- the promoted DRAFT listing remains absent from the public/current listing surface;
- Search criterion count remains exactly 2.

## Independent review and amendments

Initial implementation head `f002d6a674cddf450b5ec4fa7cf9c6fe84d49cb9` required two bounded fixes:

1. enforce current PUBLISHER role before draft/result disclosure while preserving authorized exact ALREADY_PROMOTED retry semantics;
2. remove the immediate success redirect that could race browser recovery cleanup.

Amendment head `e1838283ac84bb15672125d421a334153380e8d8` closed those findings. A second review found:

3. promotion caught all UniqueViolation instances as DUPLICATE_EPISODE rather than only the exact D09 uniqueness boundary;
4. the repository handoff still reported READY rather than REVIEW and did not conservatively reflect directly proven acceptance criteria.

Final accepted head `97056e4c0e413ec392b1d2988a9db43b18a42fc5` closed both. The final amendment was exactly one commit over the previously reviewed head and changed only the promotion persistence classifier, focused persistence tests and the slice handoff document.

Four implementation-proof items remain deliberately documented as not directly exercised by dedicated tests: pre-existing-row migration backfill, raw-SQL direct violation probes for the promotion-state/FK/provenance constraints, a genuine concurrent two-connection exact-promotion race, and an identical broker_listing_reference collision proof. The implementation and database design supporting those invariants were reviewed; their absence as dedicated direct probes was not classified as a remaining material defect.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- canonical PromotionReadiness for the accepted fresh-identity professional branch
- ProfessionalListingDraft -> atomic marketplace promotion
- fresh server-owned PhysicalBoat / MarketEpisode / NativeListing creation
- initial Organization PhysicalBoat claim materialization
- initial NativeListing offer materialization
- immutable PROMOTED draft provenance
- exact-version idempotent retry
- D09 Organization+resolved-episode uniqueness and deterministic conflict classification
- professional FastAPI/Astro promotion surface
- promoted DRAFT visibility in Organization inventory
- technical native Search criterion count remains exactly 2

DECIDED_NOT_YET_IMPLEMENTED
- existing-PhysicalBoat / existing-episode reconciliation branch
- media/gallery and media rights/public-usability path
- canonical PublicationReadiness and integrated publication flow
- durable buyer contact / Lead creation
- broker lead operating surface
- post-promotion inventory editing
- explicit sale/outcome workflow
- inventory portability/export
- structured bulk onboarding/import
- Search-fit diagnostics/exclusion explainability
- broker engagement/performance reporting
- buyer persistent monitoring / Saved Search / alerts

EXPLICITLY_DEFERRED
- D19 operational broker-reference revisions
- D20 episode-resolution revision authority/correction
- relist/reuse/correction branches
- publication/ACTIVE transition in 0067
- media, leads, editing, outcomes, analytics, import/export and alerts
- owner-direct publication
- new Search criterion/ranking
- production pilot/public launch

CONFLICT_OR_REGRESSION
- none remain on the accepted exact head
```

## Exact-head verification

Remote verification on exact accepted HEAD `97056e4c0e413ec392b1d2988a9db43b18a42fc5`:

```text
CI #903 → SUCCESS
Manufacturer artifact reproducibility #625 → SUCCESS
```

CI passed dependency audit, Windows and Ubuntu quality, PostgreSQL 18 DB integration and Astro/Node web quality. Reproducibility passed on Ubuntu and Windows.

Implementation-agent validation additionally recorded repository validation PASS, ruff format/check clean, mypy 0 issues, 3238 unit tests passed, full persistence PostgreSQL 18 sweep 818 passed with one pre-existing unrelated skip, 288 web tests passed, clean web typecheck/build, and all retained professional promotion/draft/inventory proof scripts PASS.

PR #255 merged the exact accepted implementation to `main` as `3fcc88892bbb33bf15da3b63be7e6ff8f0903a36`.

## Trigger-gate state after acceptance

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

0067 introduces no real external production inventory, pilot, paid plan or public launch. It changes no accepted Search criterion and no REQ-BROKER-022…030 status marker.

## Broker launch execution checkpoint

The 2026-09-26 execution focus remains controlling: strict truth/auth/provenance stay fixed and vertical broker-launch progress is preferred where risk permits.

With atomic professional promotion now accepted, the next reassessment should evaluate the shortest safe next capability toward normal broker-created inventory becoming publication-ready and useful to buyers. The previously accepted direction identifies media/gallery and canonical publication readiness/publish integration as near-term work, followed by durable buyer contact/leads, broker lead handling and inventory editing. This closure does not select or authorize SLICE-0068.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0067
PROJECT_STATE_QUEUE_SLICE:    0068
```

SLICE-0068 is **UNSELECTED**. Queue numbering does not authorize readiness, implementation, `START_SLICE.bat` or a capability choice.

## Closure decision

```text
SLICE-0067 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0067
PROJECT_STATE_QUEUE_SLICE = 0068
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
