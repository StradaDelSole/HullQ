# SLICE-0094 — Source-Qualified Power Engine Count and Two-Criterion AND Search

**ID:** SLICE-0094  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Sail+Power internal technical Search; second Power hard criterion and first real Power multi-criterion MUST/AND  
**Risk:** HIGH_RISK — current-vs-factory motorization, publisher/source ownership, MVCC, same-variant conjunction, Search URL/API/browser truth  
**Depends on:** Owner-accepted and locally FINISHED SLICE-0093; SLICE-0092 claim-only qualified Search; SLICE-0091 VesselCategory; SLICE-0090 source-rights research; Owner Sail+Power decision and #372.  
**Owner selection:** Owner's 2026-10-28 “ok weiter” to proceed with post-0093 repository-backed reassessment and next readiness; focused next criterion selected from first Power Search with engine_count present in accepted BoatDesign v0.6 and absent from current PhysicalBoat claims. Owner approval of **implementation** still requires the unchanged local START process after independently reviewed READY merge.  
**Readiness baseline:** canonical main `790ece768943bc38f2e725b55924bf2caf98272e` (SLICE-0093 implementation+acceptance closure merged, Owner-local FINISH 0093 SUCCESS).  
**Normative contract:** `specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` (same readiness PR).  
**Unchanged STOPs:** #355 pre-real-external-inventory-upload/pilot and CR-05 Search-scale; #366 joint Sail+Power external release; #372 Power specialist/broker parity and rights; production IN_PROGRESS, launch pack NOT_STARTED.

## Objective / one observable capability

A buyer can search internal POWER NativeListings using the **exact number of currently installed principal propulsion engines/motors**, either alone or combined as MUST-AND with the already accepted current drive arrangement (`power_drive`). An actual publisher's positive POWER claim and each technical claim must be contemporaneous, source-qualified and current; genuine design-linked proof may use v0.6 `propulsion.engine_count` only when a real FieldResolution qualifies the exact applicable configuration. The existing Sail nine criteria and its entire Search route are unchanged.

**Visibility proof:** A currently public-eligible synthetic POWER yacht with `power_drive=SHAFT` and `power_engine_count=2`, even if design-unresolved, appears correctly on `/de/power/search?power_drive=SHAFT&power_engine_count=2`, with both criterion truths, publisher-source disclaimer, real listing link/discovery token, and noindex. The same listing fails count=1 or drive=POD; wrong category, stale/retracted claim, different Organization, separate design variants or ambiguous factory/refit fact never produce a false combined positive. A normal broker can enter/update count in its existing authorized listing editor; unrelated edits retain the claim. All five locales show the same facts.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One new Power source-qualified technical criterion **with unavoidable composition** against Power criterion #1 in the same buyer Search. Existing ingestion/exports and production provider workflows are not independently changed.

**VISIBLE-RESULT CHECK:** PASS  
Retained PostgreSQL18+FastAPI+built Astro SSR inspector creates synthetic ACTIVE listings and real broker current-claim editor operations, exercises count-only/drive-only/both queries in five locales and tests a realistic failed scenario. It does not require external accounts, real broker data or public deployment.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Directly advances the Owner-accepted joint Sail+Power specialist Search toward useful Power Buyer jobs. Broker-first product priority and #372 Power Broker Search-fit parity remain mandatory; extending the currently one-dimensional Power foundation and proving same-configuration AND is a bounded prerequisite before delivering category-wide multi-criterion Broker Search-fit. No external C-light release, Sail-only pilot, model corpus claim or production-readiness advance.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Accepted 0090–0093 contracts/closures, joint Sail+Power owner decision and the #372 post-0088 reconciliation checked against the present schema, current claim snapshot, Power search registry/bridge, Power buyer API/SSR, shared query/qualification engine, Broker Search-fit and NautiX guard. See detailed six-line reconciliation below. No reimplementation of already accepted drive criterion, categorical parser, D29, publisher current-claim snapshot or Sail nine definitions.

**TRIGGER GATES CHECK:** PASS  
Global accepted technical count is 10 (Sail 9, Power 1), so the new Power criterion is **global ordinal 11**, Power ordinal 2. This READY declares common numeric/categorical bridge reuse and proves no third copied evaluator below. Workflow reassessment PASS, production IN_PROGRESS (not released); prior research/Owner source-rights and no-commercial-ranking gates preserved.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
MVP-BUY-001/002 remain PARTIAL for full Sail+Power Search; this makes one additional category-appropriate Power criterion operational, not entire Buyer Search DONE. MVP-BROKER-010 currently includes only Sail nine-criterion preview; Power Broker Search-fit still due before external joint launch and remains #372. Pending buyer saved search/alert (#MVP-BUY-007), owner-direct trust, onboarding, support, lead operations/supervision and production scaling are not lost; the no-real-data gate #355 is not triggered by synthetic development. P0 broker report #357 is already accepted with nonproduction provider delivery, live delivery separately gated.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS  
See mechanically precise publisher-claim revision/snapshot, design FieldResolution/NamedVariant, retry and downstream fail-closed rules below. New immutable claim field and public Search truth boundary are HIGH_RISK.

**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  
No production provider provisioning, real external data, production pilot, public SEO/indexing or change of launch phase.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md`; `docs/POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md`; `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md`; SLICE-0091/0092/0093 closure and READY/spec; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; broker launch execution and mandatory commitments; owner-direct product direction, ADR-0005/source rights; issues #355/#366/#372.  
**Production implementation checked:** `specs/BOAT_DESIGN_SCHEMA.v0.6.json` `$defs.propulsion_shape.engine_count` (integer/null, minimum 0); `src/hullq/domain/physical_boat_claims.py` has existing `power_drive_configuration` but not current `power_engine_count`; `persistence/physical_boat_claims.py` observation/revision; `application/inventory_editing.py`; broker Astro editor; `search/power_criteria_registry.py` exactly one fixed Power definition; `application/power_inventory_query.py` one-leaf query and two source planes; `persistence/power_category_drive_snapshot.py` single statement MVCC; `search/power_drive_design_bridge.py`, `search/boat_design_field_bridge.py`, `configuration_engine.py` and `query_mixed.py`; `application/power_search_read.py`, `api/app.py`, `web/src/lib/powerSearchApi.ts` and five Power SSR locale routes; Sail broker `application/broker_search_fit.py` separate only-Sail preview.  
**Already implemented / not re-decided:** Nine Sail hard criteria, Power drive token taxonomy/one-leaf results, current publisher-owned positive POWER category, D29/freshness and noncommercial ranking, qualified source/lifecycle and immutable snapshot, real FieldResolution/variant resolution machinery, separate Power base/result/redirect/invalid HTTP contract, strict BASE/result body validation, five noindex Astro pages, rejected Power export as Sail NautiX and synthetic performance inspector.  
**Exact remaining gap:** No current PhysicalBoat primary propulsion engine-count claim, no exact count Power criterion, and no **combined drive+count Power query**. A raw v0.6 factory `engine_count` is *not* source-qualified current installation; the sole existing Power buyer criterion cannot distinguish single/twin engine count.  
**Accepted-but-unimplemented obligations:** Power Broker Search-fit parity, real POWER model/motorization corpus and rights, remaining Power facets, speed/range/consumption under operating conditions, category-correct Power NautiX import/export, genuine Sail+Power listing browse, Motorsailer policy, source rights and publisher/owner-direct trust (#372); Search CR-05/runtime #355; joint external product/pilot #366; buyer save/monitor/alerts, support/production email/operations/legal and scalable data.  
**Material classifications:** DECIDED_AND_IMPLEMENTED = all current Sail/Power drive Search, D29, broker ownership/source and generic MUST/AND engine; DECIDED_NOT_YET_IMPLEMENTED = source-qualified installed Power engine count and combined drive+count; EXPLICITLY_DEFERRED = condition-qualified performance criteria, full Power broker parity, NautiX power mapping, v0.7 design schema and external corpus; GENUINELY_OPEN = motorsailer dual-domain admission and genuinely licensed broad Power corpus; CONFLICT_OR_REGRESSION = design-only/factory count treated as installed engine count, cross-org or cross-revision/variant false positives, production/launch shortcuts.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** YES  
**Technical Search criterion ordinal:** 11  
**Second-criterion bridge comparison:** PASS  
**Third-copy abstraction guard:** PASS  
**Workflow reassessment status:** PASS  

**Gate 3 technical comparison:** Existing SLICE-0051 numeric draft max, SLICE-0055 categorical keel, SLICE-0085 numeric LOA range, and SLICE-0093 Power categorical drive already use the same static `CriterionDefinition` + source-qualified `FieldProjectionSpec`/current-claim accessor + `MixedAndQuery` and `evaluate_configuration` MUST-AND. The count filter uses an exact **numeric RANGE with threshold_min=threshold_max**, so the common kernel is reused **without** another count scorer or a categorical misstatement of integer truth. Count and drive must be evaluated on the **same** resolved design configuration and same publisher current claim revision. The design bridge may use the existing FieldResolution machinery with two bounded pointer pairs. Existing SLICE-0093 category-and-drive MVCC snapshot must be extended/coherently reused for category+drive+count, not followed by independent claim reads. Thus **COMMON STRUCTURE GENERALIZED / REUSED**. The second Power criterion specifically tests multi-dimensional Power composition; do not simply union separate per-criterion candidate matches. Do not change original Sail parser/evaluator to make Power keys work.

**Marker discipline:** Canonical `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` remains **10** during READY, implementation and review, and existing Sail remains 9. Only after a separately reviewed Owner-accepted SLICE-0094 acceptance closure may it advance 10→11 (Sail 9 / Power 2).

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  

Production Readiness remains IN_PROGRESS, `PRODUCTION_LAUNCH_PACK_PHASE` NOT_STARTED. The external broker upload/pilot hard STOP from #355 stays in force. This internal synthetic Search increment does not change provider plans or start a production launch phase.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** Public search eligibility/evidence across new immutable count field, publication/lifecycle identity and current-vs-factory truth; concurrent category/drive/count claim revisions and conflicting NamedVariants can manufacture a false match unless all evidence is coherent.  
**Must-never-change invariant:** No count match without publisher's own current positive POWER category and current explicit qualified installed count from one immutable current revision. Drive+count positive requires both same-revision claims, and for design-linked candidates **the same actual qualified DesignConfiguration** must satisfy both leaves; never independently combine different variants or another Organization's claims. Count-only does not require drive. An unsupported factory source or unqualified refit never proves actual count. Sail old Search remains unchanged.  
**Durable source of truth / loss boundary:** Existing Organization-owned immutable PhysicalBoatClaimSnapshot revision/head, preserved authorized issuer/account/timestamp, broker editing, D29 eligible listing/episode/offer/media, separately admitted BoatDesign FieldResolution/NamedVariant. Migration adds one optional typed count claim, preserving historical omission. Browser draft/local state, a factory raw JSON value, cache, search result DTO or external feed cannot be promoted to durable publisher truth.  
**Retry / replay / partial-failure behavior:** Exact immutable revision replay remains idempotent, old historical omission retains its original hash/meaning, optimistic stale editor save fails zero mutation, unrelated edit does not clear count, invalid/out-of-range boolean/float/string does not write any field, authorized count retraction removes old positives. Interrupted transaction cannot leave a new head pointing to an incompletely persisted claim. Query failures do not return a false 200 empty search.  
**Absence-vs-error / fail-closed behavior:** Missing/UNKNOWN/unsupported count; conflicting other Organization; omitted publisher POWER or non-Power category; stale/ambiguous/contradictory canonical field or NamedVariant; unqualified factory-to-current mismatch → INSUFFICIENT_DATA or typed exclusion, not affirmative. Actual API/DB/source/transport exceptions remain errors, not fabricated absence. Valid empty matching inventory remains a valid empty RESULT distinct from error; partial wire responses fail 502.  
**Executable adversarial proof:** Real PostgreSQL18 revision claim editor and backcompat; own POWER category+count with no drive count-only TRUE; Drive+count same revision TRUE; both criteria split across revisions or Organizations never TRUE; two-connection MVCC update toggles count and drive+category so no torn composite; design-level two variants separately satisfy criterion leaves but never combined match; true same-variant qualifying FieldResolution positive; unsupported v0.6 factory count 0/NULL/unresolved; real retrofit ambiguity; API duplicate/order/invalid/count echo errors; all five built Astro SSR locales, private provenance, noindex/canonical; NautiX guard and all Sail routes. Synthetic 0/40/200 mixed candidates + query plans/statement counts/retention evidence.  
**Slice sizing assessment:** COHERENT  

A new count field through the single existing broker immutable-claim editor and the first multi-criterion Power Buyer Search is one buyer-observable capability. Expanding broker preview, import/export, generic browse, publisher provisioning, 2nd/3rd Power engine taxonomy or hosted scaling independently would be separate acceptance domains and is not bundled here.

## Why this slice exists

The owner-approved Sail+Power product requires genuine specialist criteria rather than a single Power dropdown. Existing BoatDesign v0.6 includes `propulsion.engine_count`, but no accepted current installed engine count is recorded by PhysicalBoat claim or available as a Power Buyer filter. A current publisher-attested exact count adds useful single/twin/multiple engine buyer selection while forcing the already accepted joint Search kernel to prove correct per-configuration AND. This is a higher-value internal capability now than Power Broker Search-fit parity for only one specialist criterion, though Broker Search-fit parity remains required before launch and must be selected separately. Pure generic browse and #355 hosted Search protection remain independent work and must not be forgotten.

## Controlling artifacts

- Normative specs: `specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` and unchanged `specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`; `specs/BOAT_DESIGN_SCHEMA.v0.6.json`.
- Owner/requirements: Sail+Power full specialist platform decision, #366, #372, post-0088 source and claim reconciliation; D29 and current publication readiness; `docs/governance/POST_0051_TRIGGER_GATES.md`.
- Existing production code: `physical_boat_claims.py` domain/persistence; authorized inventory editing and broker Astro editor; Power registry/bridge/query/request/serializer/SSR; shared FieldResolution/AND core; exact SLICE-0093 tests and inspector.
- Open constraints: #355 real-data/production/runtime, #366 joint release, #372 full Power model and broker parity, ADR-0005 source rights.

## Required behavior / implementation boundary

1. Add the optional **typed positive integer** `PhysicalBoat` current `power_engine_count` claim, exact accepted 1–32 storage range with VALUE_ASSERTION/UNKNOWN/omitted distinct, immutable revision migration, authorized broker editor/create/read/write and unrelated-field preservation. Existing historical rows and snapshot replay meaning unchanged; zero/bool/fraction/string-coercion unsupported.
2. Add exactly **one** Power CriterionDefinition and bounded v0.6 design FieldResolution bridge for baseline and NamedVariant `propulsion.engine_count`. Raw `engine_count` in BoatDesign is never automatically qualified without current FieldResolution. No v0.7. An accepted qualifying design factory count also requires a separately qualified current installed count; incompatible refit without source qualification is not a positive.
3. Extend Power-only query to accept `power_engine_count=1..8` alone and optionally with `power_drive=SHAFT|STERNDRIVE|POD|WATERJET|OUTBOARD`, constructing a shared numeric RANGE(min=max) leaf and existing categorical leaf in a single `MixedAndQuery`. No OR, fuzzy values, buckets, ranking or independent per-criterion result union. More than eight current claimed principal units may be faithfully stored 9–32 but not searched affirmatively in this initial whitelist; same numeric query properly non-matches a known count outside requested value.
4. Category/drive/count admission uses a coherent shared observation snapshot for both claim-only and design-linked branches. Positive POWER must be publisher-owned; fresh contradictory other-org claim fails closed. Design query joins source-qualified fields on the exact same generation/NamedVariant; no cross-variant conjunction or false factory/current equivalence.
5. Existing Power API/SSR five locales show both controls, exact active criterion echo, source label and both criterion evidence; maintain BASE/RESULT/REDIRECT/INVALID, strict 400/308/502, canonical ordering `power_drive` then `power_engine_count`, noindex, genuine empty result vs unavailable distinction, escaped HTML and protected discovery tokens. Drive-only endpoint contract and original Sail routes remain unchanged.
6. Retain actual PG18/FastAPI/built Astro SSR broker-to-buyer inspector and adversarial tests for source, revision, FieldResolution, two-connection concurrency, cross-Organization conflicts, wrong category, D29, user input, malformed nested JSON, five locales, existing Sail, NautiX false Sail export and existing count 10 until acceptance closure.
7. Report synthetic real PG18 at 0/40/200 mixed population, actual retained-match counts, EXPLAIN/BUFFERS/statement counts; never present this as production throughput or remove #355. Avoid unnecessary per-candidate new SQL statements and no unbounded accidental cross product.
8. Do not change existing customer/broker visibility, real external data or launch state. No Power NautiX import/export, no new broad source rights, no Power Broker Search-fit, no full engine-make/model/horsepower/fuel/operating metrics, no generic Sail+Power browse, no production email/provider.

## Deliverables / touchpoints

- `specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` and bounded documentation of trusted source/units; additive Alembic migration; optional `power_engine_count` claim and current observation in existing domain/persistence/authorized inventory editor.
- Static Power criterion #2 and `power_engine_count_design_bridge.py` reusing the accepted FieldResolution/NamedVariant/qualification infrastructure. Keep Power domain separate from Sail.
- Generalize existing single Power query/read/HTTP serializer/TS validation and the five SSR pages **only to two optional criteria and their AND**, not a new generic query DSL.
- Add real PostgreSQL18 tests and retained end-to-end broker+Search inspector; actual reviewer-verifiable negative/positive and 0/40/200 performance evidence. Existing Power criterion #1 and nine Sail tests remain green.
- PR at exact branch HEAD with full independent adversarial review, 6-job remote CI, Manufacturer reproducibility and Deploy workflow checks; explicit Owner acceptance before merge, separate docs-only acceptance closure, then Owner-local FINISH.

## Acceptance criteria

- [ ] Exactly one additional Power hard technical criterion; canonical numeric query tokens 1–8 and current count claim 1–32, typed, authorable and readback; old 0093 drive-only Search returns identical results and Sail nine untouched.
- [ ] Real broker authorized editor → immutable current claim revision preserves positive POWER, count and existing drive, stale/foreign/invalid mutations write nothing, historical snapshots/replay/omission retained.
- [ ] Design-unresolved ACTIVE+D29 publisher own positive category+count Search matches count-only without a drive; combined drive+count succeeds iff all active leaves TRUE on the publisher's one current revision; no third scorer or cross-Org borrowing.
- [ ] Design-linked exact qualified `engine_count` FieldResolution uses BoatDesign v0.6 and correct single NamedVariant with current installed assertion; cross-variant split, unsupported count=0, false factory/refit inference yield no false positive.
- [ ] Single real PostgreSQL snapshot category+drive+count and two-connection revision race test; other Org count/drive conflict and category SAIL/MOTORSAILER/CONFLICT never produce Power positives.
- [ ] Strict 400/308 canonical query, 502 malformed/wrong-request 200, unchanged BASE and genuine empty RESULT, noindex five SSR locales, evidence and safe listing/discovery provenance; Sail API rejects Power key unchanged.
- [ ] NautiX Sail-only category guard, D29, public privacy, Organic Search neutrality, no broader importer/exports or undesired supplier exposure; existing Sail tests and Power drive tests green.
- [ ] PG18 benchmark 0/40/200 and EXPLAIN retained with true match retention and no false throughput claim; #355 OPEN as pre-real-data/pilot STOP. #366/#372 remain OPEN and launch phase untouched.
- [ ] Repository validator, Ruff check/format, mypy, PG18 and web tests/astro check/build, local inspector, exact-HEAD full six-job CI + Manufacturer + Deploy workflow as applicable, independent exact-head implementation review, explicit Owner acceptance BEFORE implementation merge.
- [ ] Separate reviewed Owner acceptance closure changes global marker **10→11** (Sail 9, Power 2), preserves production IN_PROGRESS/Launch Pack NOT_STARTED, tracks Power Broker Search-fit backlog and does not start another slice automatically.

## Stop conditions / independent-review expectations

- A count-only/combined positive can be produced from raw v0.6 design data, wrong NamedVariant, another Org category/count, stale claim, a category+drive+count torn snapshot, a guessed hybrid unit count or a false factory-versus-current equivalence.
- A current publisher count disappears during an unrelated edit; invalid/stale/foreign claim edits mutate any durable state; an early claim revision is treated as current.
- New Power multi-criterion code introduces an ad-hoc independent scorer, unions separate matches, changes Sail routes/criteria/old 0093 drive semantics, silently widens public count/input grammar or returns a valid zero-result for transport/DB failures.
- The implementation requires actual Power source schema migration beyond v0.6, real broker data, Power broker fit parity, broad import/export, or production Search operational changes. Stop with a bounded documented reviewer finding rather than silently widening this slice.
- No external pilot, first upload, public Sail-only/C-light launch, or Power feature marketing without later gates.

## Owner workflow and required handoff

1. READY/spec are prepared and reviewed as **docs-only** PR, with repository validator and exact-HEAD external CI/Manufacturer/Deploy checks. READY merge must precede Owner's unchanged `START_SLICE.bat` use.
2. Only after the docs-only READY PR is reviewed, CI-green and merged does the Owner run `START_SLICE.bat`, entering **0094**. The launcher-generated initial Claude implementation prompt is the *only* authorized initial prompt; this readiness is not a substitute. Do not require Owner to paste START output unless a genuine error needs diagnosis.
3. Claude implements on its generated `slice/0094-...` branch, executes tests and retained proof, pushes an exact HEAD and hands off **REVIEW**, not DONE. Independent exact-head review/amendments, full remote gates and **explicit Owner acceptance** precede implementation merge.
4. A separate docs-only acceptance closure advances the marker and state only after acceptance/merge; then the Owner runs unchanged `FINISH_SLICE.bat 0094` and confirms success. No next slice is auto-selected.

The implementing agent's handoff MUST use the field structure of `docs/slices/SLICE_TEMPLATE.md`: Slice; Product execution checks; Changes; Validation with actual commands and adversarial evidence; External verification with per-run status; Findings; Follow-up; Agent declaration. No unexecuted remote gate may be marked PASS, and no implementing agent may mark the slice DONE.
