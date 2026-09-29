# SLICE-0069 — Acceptance Closure

**ID:** SLICE-0069  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #264  
**Accepted implementation HEAD:** `b85872f5aef5666babf590735f6a87b6d83fe45f`  
**Implementation merge commit:** `641d50a2d7f4d0f1d02669c0bb3b29c5a8216273`  
**Independent exact-head ACCEPT review:** 2026-09-29  
**Owner acceptance:** explicitly recorded 2026-09-29

## Accepted capability

SLICE-0069 closes the broker publication/current-public vertical:

```text
Organization-owned NativeListing DRAFT
→ canonical PublicationReadiness
→ authoritative publish-time re-evaluation
→ DRAFT -> ACTIVE
→ canonical CurrentPublicEligibility
→ public listing + mixed-media gallery
→ Direct Search/current-market surfaces reuse the same public-eligibility authority
```

## Accepted implementation behavior

- one canonical D22 PublicationReadiness evaluator serves preflight and publish;
- publish re-evaluates current readiness inside the lifecycle transaction after locking the NativeListing row;
- legacy SLICE-0049 publication completeness is no longer a second publication definition;
- readiness consumes the accepted current offer, PhysicalBoat claim, episode/PhysicalBoat link, Organization publishing eligibility, public-usable IMAGE minimum and explicit valid cover;
- BoatDesign/Search fit, multiple-photo quality, YouTube presence and Broker-CI slide do not block publication;
- pre-D20 episode resolution continues to use only the existing immutable creation-envelope MarketEpisode link;
- one canonical D29 CurrentPublicEligibility authority governs current buyer/public-market admission;
- ACTIVE alone is not sufficient for current-public eligibility;
- stale freshness, ineligible Organization, broken episode/PhysicalBoat chain, missing current offer/claim, or invalid media/cover suppress buyer surfaces without rewriting lifecycle;
- exact public listing read and both accepted Direct Search paths consume canonical current-public eligibility;
- technical Search criterion count and classification semantics remain exactly unchanged at 2 criteria;
- public listing projection now includes bounded public mixed-media gallery state from accepted SLICE-0068 truth;
- public image delivery is listing-scoped, serves only processed derivatives, and fails closed;
- private originals/object keys/uploader/provenance/source metadata remain private;
- YouTube remains normalized structured identity only;
- Broker Workspace exposes structured publication blockers and ACTIVE-but-suppressed current-public reasons;
- withdraw/reconfirm semantics remain unchanged;
- no WITHDRAWN -> ACTIVE republish path, D20/D21 correction authority, owner-direct publication, direct VIDEO upload, new moderation domain, lead/CRM or inventory-editing capability was introduced.

## Independent review and amendment

Initial implementation HEAD `f33ec972d8322e91dfbcdf0c3b93ef07dc634ace` correctly implemented the accepted D22/D29 authority and public/Search integration, but independent review required two acceptance-proof amendments:

1. add explicit real-PostgreSQL concurrency proofs for publish vs readiness-relevant offer/claim/media mutation;
2. run the complete final PostgreSQL suite and repair retained proof fixtures that still assumed the pre-D22 publication minimum.

Amendment HEAD `b85872f5aef5666babf590735f6a87b6d83fe45f` closed both findings.

Six deterministic multi-connection PostgreSQL tests now prove:

- publish blocks on an in-flight readiness-relevant NativeListing lock;
- concurrent offer revision + publish resolves coherently without deadlock;
- concurrent PhysicalBoat claim revision + publish resolves coherently without deadlock;
- writer-first retirement of the only cover image leaves DRAFT publication BLOCKED on authoritative recheck;
- publish-first protects the ACTIVE listing through the existing media invariant;
- a genuine concurrent cover-image retirement/publish race resolves to exactly one valid ordering without deadlock.

The pre-existing competing-publish exactly-once proof remains intact.

Retained proof scripts were updated only to construct the accepted D22 minimum claim/media/cover fixture; production semantics were not weakened.

No material implementation finding remains on the accepted exact head.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- D22 canonical PublicationReadiness
- D22 advisory preflight + authoritative publish-time re-evaluation
- D22 required current offer / PhysicalBoat claim / episode / media / cover publication truth
- D29 canonical CurrentPublicEligibility
- ACTIVE-but-suppressed semantics without lifecycle rewrite
- exact public listing read consuming canonical current-public eligibility
- both accepted Direct Search paths consuming canonical current-public eligibility
- bounded public IMAGE + YOUTUBE gallery projection
- listing-scoped public processed-derivative image delivery
- structured Broker Workspace publication blockers/current-public suppression reasons
- race-safe publish/readiness serialization proofs
- technical native Search criteria remain exactly 2

DECIDED_NOT_YET_IMPLEMENTED
- D20 explicit MarketEpisode-resolution revision authority
- D21 ACTIVE MarketEpisode correction/rebinding
- WITHDRAWN -> ACTIVE republish/relist
- owner-direct publication
- post-promotion marketplace offer/fact editing
- durable buyer contact / Lead creation
- broker lead operating surface
- sale/outcome workflow
- full D24 retention/legal-hold/backup-purge worker
- direct uploaded VIDEO
- virtual Broker-CI slide rendering/CI authoring controls
- cross-Organization media grants
- import/export, analytics, alerts, payments

EXPLICITLY_DEFERRED
- HEIC/HEIF
- arbitrary external embeds
- new moderation/safety domain absent a separately accepted requirement
- production pilot/public launch in this slice

CONFLICT_OR_REGRESSION
- none remain on the accepted exact head
```

## Exact-head verification

Remote verification on exact accepted HEAD `b85872f5aef5666babf590735f6a87b6d83fe45f`:

```text
CI run 36505900197 → SUCCESS
Manufacturer artifact reproducibility run 36505900233 → SUCCESS
```

Independent exact-head implementation review: **ACCEPT**, review ID `5346564596`.

Final implementation-agent validation additionally recorded:

```text
repository validator: PASS
ruff check / format-check: PASS
mypy: PASS (127 files)
PostgreSQL-backed Python suite: 5682 passed / 3 skipped / 0 failed
all CI-required inspect_*.py retained proofs: PASS
Astro check/build: PASS
web tests: 312 / 312 passed
```

PR #264 merged the exact accepted implementation to `main` as `641d50a2d7f4d0f1d02669c0bb3b29c5a8216273`.

## Trigger-gate state after acceptance

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
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

0069 changes no Search criterion and starts no external pilot, paid plan or production launch.

## Broker launch execution checkpoint

The broker launch path is now:

```text
BROKER CREATES
→ BROKER ADDS MEDIA
→ BROKER PUBLISHES   [implemented through SLICE-0069]
→ BUYER CONTACTS
→ BROKER HANDLES LEAD
→ BROKER EDITS / MAINTAINS INVENTORY
→ BROKER CLOSES / RECORDS OUTCOME
```

The next post-0069 reassessment should evaluate the shortest safe next launch-path capability, with durable buyer contact/Lead creation the accepted next directional step unless repository evidence reveals a higher-priority blocker. This closure does not itself authorize SLICE-0070 implementation.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0069
PROJECT_STATE_QUEUE_SLICE:    0070
```

SLICE-0070 is **UNSELECTED**. Queue numbering does not authorize readiness, implementation, `START_SLICE.bat` or a capability choice.

## Closure decision

```text
SLICE-0069 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0069
PROJECT_STATE_QUEUE_SLICE = 0070
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
