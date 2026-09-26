# SLICE-0066 — Acceptance Closure

**ID:** SLICE-0066  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #252  
**Accepted implementation HEAD:** `3b30cce2f6f7d957a5b9c5991171bb57241e3add`  
**Implementation merge commit:** `944c1fd79389388e3de86ee328bb106735963693`  
**Independent exact-head ACCEPT review:** 2026-09-27  
**Owner acceptance:** explicitly recorded 2026-09-27

## Accepted capability

SLICE-0066 closes the remaining required-response input mismatch for the existing shared draft field:

```text
physical_boat.build_year
```

The owner-direct and professional draft layers can now preserve three mechanically distinct states:

```text
OMITTED
!= UNKNOWN
!= VALUE_ASSERTION(year)
```

No marketplace promotion, fact creation or publication occurs.

## Accepted implementation behavior

The accepted implementation includes:

- a shared typed `BuildYearResponse` / `BuildYearAssertionKind` draft primitive;
- the existing common draft key set remains exactly nine keys;
- canonical structured VALUE_ASSERTION wire/readback:
  ```json
  {"physical_boat.build_year":{"assertion_kind":"VALUE_ASSERTION","value":1987}}
  ```
- canonical explicit UNKNOWN wire/readback:
  ```json
  {"physical_boat.build_year":{"assertion_kind":"UNKNOWN"}}
  ```
- omission remains absence of the key and is never normalized to UNKNOWN;
- historical bare integer draft input remains accepted/readable for compatibility and normalizes internally to VALUE_ASSERTION;
- canonical serialization/new successful writes use the structured response form;
- strict structured-object validation rejects bool/null/unknown assertion kind/missing or extra members/UNKNOWN-with-value;
- both OwnerDirectListingDraft and ProfessionalListingDraft continue to share the same channel-neutral common parser/serializer;
- both Astro editors expose not answered / known year / unknown as distinct states;
- professional browser-local recovery preserves the build-year mode separately through the bounded recovery-only control `physical_boat.build_year.assertion_kind`;
- malformed/tampered recovery assertion-kind values fail the recovery envelope closed;
- owner-direct and professional browser form translation use one strict shared build-year form parser;
- invalid mode, blank Known-year, malformed/partial numeric, decimal or garbage-suffixed Known-year input reaches the visible invalid-save state with zero mutation;
- no Alembic/database schema migration is introduced;
- no PhysicalBoat/MarketEpisode/NativeListing/offer/claim/lifecycle/freshness/Search mutation occurs.

## Independent review and amendment

Initial implementation exact head:

```text
3889312dfa08df1adf26de693596d5a26b387fc1
```

Independent exact-head review found two bounded browser/recovery boundary defects while accepting the core Python domain/API model:

### Finding A — recovery assertion-kind validation

The professional recovery envelope accepted any arbitrary string for the recovery-only `physical_boat.build_year.assertion_kind` field despite the normative vocabulary being exactly:

```text
""
VALUE_ASSERTION
UNKNOWN
```

That allowed a malformed/tampered LocalStorage value such as `ABSENT` to survive recovery parsing instead of failing the envelope closed.

### Finding B — lenient browser Known-year parsing

The two Astro form adapters used lenient `Number.parseInt()` behavior.

Consequences included:

- `VALUE_ASSERTION` selected with blank/invalid year could silently collapse to OMITTED;
- a forged value such as `1987junk` could be coerced to `1987`.

Both violated the accepted unambiguous three-state browser semantics and fail-closed input boundary.

The same-slice amendment produced final accepted head:

```text
3b30cce2f6f7d957a5b9c5991171bb57241e3add
```

The amendment:

- made malformed recovery assertion-kind values fail the whole envelope closed;
- introduced one shared strict `parseBuildYearFormControl()` for both owner-direct and professional Astro editors;
- made invalid mode / invalid Known-year submissions structurally zero-mutation by not calling the update API;
- added focused unit/browser-recovery tests;
- extended both retained real PostgreSQL/FastAPI/built-Astro proof scripts to prove invalid submissions leave version and build-year truth unchanged;
- added the required `Status set by this handoff: REVIEW` marker.

No promotion, marketplace state, Search semantics, schema migration or unrelated slice behavior was added by the amendment.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- shared OwnerDirect/Professional common draft key set remains exactly nine
- physical_boat.build_year supports explicit draft VALUE_ASSERTION(year)
- physical_boat.build_year supports explicit draft UNKNOWN
- omitted build_year remains mechanically distinct from UNKNOWN
- legacy bare integer build_year remains readable/accepted as compatibility input
- canonical build_year serialization/readback uses structured assertion response
- owner-direct and professional channels use one shared common parser/serializer
- both browser editors expose unanswered / known year / unknown explicitly
- invalid browser Known-year/mode input fails with zero mutation
- professional recovery preserves build-year response mode
- malformed recovery assertion-kind values fail closed
- no database migration required for this JSON value-shape evolution
- technical native Search criterion count remains exactly 2
- no promotion/publication occurs in 0066

DECIDED_NOT_YET_IMPLEMENTED
- canonical PROMOTION_READY evaluation
- ProfessionalListingDraft -> marketplace atomic promotion/materialization
- PhysicalBoat / MarketEpisode resolution-or-creation during promotion
- NativeListing creation from professional draft
- initial PhysicalBoat claim reconciliation/materialization from promoted draft
- initial offer revision/materialization from promoted draft
- media/gallery and media rights/public-usability path
- canonical PublicationReadiness evaluator and publish integration
- buyer contact / durable Lead creation
- broker lead operating surface
- post-promotion inventory editing
- explicit sale/outcome workflow
- inventory portability/export
- structured bulk onboarding/import
- Search-fit diagnostics/exclusion explainability
- broker engagement/performance reporting
- buyer persistent monitoring / Saved Search / alerts

EXPLICITLY_DEFERRED
- all marketplace promotion/publication behavior beyond this input alignment
- media, lead, editing, outcome, analytics, import/export and alert work not owned by 0066
- external broker self-service pilot
- paid broker activation
- public production launch

CONFLICT_OR_REGRESSION
- none remain on the accepted exact head
```

The owner-accepted 2026-09-26 professional marketplace workflow decisions remain controlling for later promotion/media/publication work. This closure does not preselect SLICE-0067.

## Exact-head verification

Remote verification on exact accepted HEAD `3b30cce2f6f7d957a5b9c5991171bb57241e3add`:

```text
CI #895 → SUCCESS
Manufacturer artifact reproducibility #617 → SUCCESS
```

The CI run passed:

- `quality (ubuntu-latest)`;
- `quality (windows-latest)`;
- `web quality (Astro/Node)`;
- `db integration (PostgreSQL 18)`;
- `dependency audit`.

The implementation-agent validation additionally recorded:

```text
repository validation: PASS
ruff format/check: PASS
mypy src: PASS
full pytest: 4656 passed / 780 skipped
web Astro check: 0 errors
web tests: 272 / 272 PASS
web build: PASS
owner-direct retained real PostgreSQL/FastAPI/built-Astro proof: PASS
professional retained real PostgreSQL/FastAPI/built-Astro proof: PASS
```

PR #252 merged the exact accepted implementation to `main` as:

```text
944c1fd79389388e3de86ee328bb106735963693
```

## Trigger-gate state after acceptance

SLICE-0066 adds no technical Search criterion and introduces no real external production inventory, pilot, paid plan or public launch.

Canonical trigger state remains:

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

SLICE-0066 changes no REQ-BROKER-022…030 status marker.

## Broker launch execution checkpoint

The 2026-09-26 execution recalibration remains controlling:

```text
strict truth / auth / provenance stay fixed
+
micro-slicing is no longer a goal
+
vertical broker-launch progress becomes the default where risk permits
```

With 0066 accepted, the previously identified build-year response-shape blocker is removed.

The next reassessment should therefore evaluate the shortest safe vertical capability toward:

```text
ProfessionalListingDraft
→ PROMOTION_READY
→ atomic marketplace materialization
→ NativeListing DRAFT
```

against the accepted D01–D12/D18–D21 decisions and current repository implementation.

This is a directional execution focus only. SLICE-0067 remains UNSELECTED until a fresh post-0066 reassessment completes.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0066
PROJECT_STATE_QUEUE_SLICE:    0067
```

SLICE-0067 is **UNSELECTED**.

The queue number does not authorize readiness, implementation, `START_SLICE.bat` or a capability choice.

## Product execution checkpoint

HullQ's accepted professional provider path now includes:

```text
Auth0-compatible login
→ durable HullQ Account
→ current Organization/Membership/MFA authorization
→ Organization-owned NativeListing inventory overview
→ private ProfessionalListingDraft workspace
→ optimistic durable drafting + bounded local recovery
→ broker_description retained
→ optional boat_name has a PhysicalBoat claim destination
→ build_year draft input can be OMITTED / UNKNOWN / VALUE_ASSERTION truthfully
→ existing NativeListing Publish / Withdraw / Reconfirm controls
→ no implicit draft promotion
```

The pre-market draft now has the accepted input semantics needed for later promotion-readiness evaluation without inventing build-year truth.

## Closure decision

```text
SLICE-0066 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0066
PROJECT_STATE_QUEUE_SLICE = 0067
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
