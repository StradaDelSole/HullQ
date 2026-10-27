# SLICE-0093 — First Power Technical Criterion: Current Drive Arrangement

**ID:** SLICE-0093  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Sail+Power internal technical-discovery foundation, first Power specialist criterion (not a public/pilot release)  
**Risk:** HIGH_RISK — category isolation, current-vs-design truth, immutable publisher revisions, FieldResolution/NamedVariant, buyer false positives and URL semantics  
**Depends on:** Owner-accepted, locally FINISHED SLICE-0092; SLICE-0091 VesselCategory resolution; SLICE-0090 research §4 row C; Owner's joint Sail+Power decision #366 and open requirement tracker #372.  
**Owner selection:** 2026-10-27, following owner-confirmed successful `FINISH_SLICE.bat 0092` and explicit “ok lass uns das bitte tun” to plan the next Power search dimension. This authorizes READY preparation only; not implementation bypass, acceptance, external data or launch.  
**Readiness baseline:** canonical main `ff6673641db169b22c6152a83c3fb004f5113c93`.  
**Normative Power v0.1 field contract:** `specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`, submitted in the same docs-only READY PR.  
**Unchanged blockers:** #355 pre-real-external-data/upload/pilot/runtime + scaled Search; #366 joint Sail+Power release; #372 wider Power specialist capability; Source Rights ADR-0005/OQ-007. Launch Pack NOT_STARTED.

## Objective / one observable capability

Give a buyer **one real, category-separated Power technical hard filter** for a listed vessel's *current principal propulsion drive arrangement* — `power_drive=SHAFT|STERNDRIVE|POD|WATERJET|OUTBOARD` — with strict current publishing-Organization claim evidence, no invented BoatDesign fact, the same accepted configuration/leaf MUST evaluator, real PostgreSQL 18/FastAPI/built Astro SSR proof in five locales, and unchanged accepted Sail Search.

The **mandatory minimum positive** is a currently-public-eligible POWER PhysicalBoat **without** a BoatDesignRef, whose publishing Organization asserted the compatible POWER category and drive value in its same durable current claim revision. Show its source as `PUBLISHER_CLAIM`, not “independently verified”. A valid negative or insufficient outcome must be equally inspectable. Design-linked POWER classifications require independently real canonical FieldResolution for design-side values; no schema change/placeholder source is authorized. The broad Power design corpus, other Power filters and equivalent Broker Search-fit remain separate slices. This is **Power domain ordinal 1**, **global technical Search criterion ordinal 10**; existing **nine Sail technical dimensions remain unchanged**, and the global count marker advances 9→10 **only in the eventual Owner-accepted closure**, not in this READY PR.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One new typed Power drive-arrangement Search dimension through existing publisher claim authoring, common domain/query evaluation and buyer-facing results, plus inseparable evidence/negative tests. This is not a separate domain launch, importer rewrite, Power engine model, Power broker search-fit or operating-point measurement framework.

**VISIBLE-RESULT CHECK:** PASS  
Synthetic PostgreSQL18 + FastAPI + built Astro SSR inspector on localhost: an ACTIVE, no-design POWER boat with qualified `POD` current broker claim appears as a separately labelled Power POD hit in one of five locale pages, while an otherwise-identical SAIL boat does not. Changing/retracting the current claim removes the match. The Owner can run a retained script locally and inspect its actual API and HTML without external accounts.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Owner-accepted one quality Sail+Power marketplace; only internal reference milestones until both domains and Broker/Buyer/safety/source-rights/production gates pass. The Power hard criterion is not a marketing or SEO/public-pilot release; source trust/payments are independent, and seller/owner-direct acceptance is not broadened.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Checked exact accepted SLICE-0090/91/92 closures and research, post-0088 Sail+Power reconciliation, current canonical `main` code/test/migration boundary and BOAT_DESIGN_SCHEMA.v0.6, POST_0051 Trigger Gates and Owner-direct pivot; below records actual already-implemented vs genuinely missing components. No second scorer, new BoatDesign truth source or re-opening of nine Sail dimensions.

**TRIGGER GATES CHECK:** PASS  
Mandatory global ordinal **10** follows accepted 9. This is first Power specialist domain criterion, **not** global ordinal 1. Because the repository gate counts *all* accepted hard native criteria, **Second-criterion bridge comparison: PASS** and **Third-copy abstraction guard: PASS** are mandatory here, not NOT_APPLICABLE. Shared `CriterionDefinition`, typed category/field readers, `evaluate_projection` and `evaluate_configuration` are reused; only category-specific field decoder/projection and a distinct Power request/DTO entrypoint are allowed. No third same-purpose evaluation copy.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
Advances PARTIAL buyer technical discovery (`MVP-BUY-001/002`) and truthful source-specific observation (`MVP-DATA-001/005`) toward accepted Dual Domain Search, without marking their broad criteria DONE. Keeps open first-priority broker provisioning, support/privacy/compliance, owner-direct trust, real delivery/supervision and major #355 runtime/parser/proxy/DB/scale/retention gates; this is a synthetic, narrowly-scoped Owner-selected internal next dependency from accepted SLICE-0090, **not** permission to move these other obligations past their required before-real-data trigger.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS  
Explicit fail-closed category/source/schema/unit/variant/revision/eligibility and concurrency cases below, real persisted tests and a STOP rather than false Power matches.

**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  
No production provisioning, external user/product visibility, real broker data, third-party content ingestion, provider billing or launch-state advance.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md`, `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md` §2.2/2.3/§4 row C, `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`, `docs/POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md`, SLICE-0091 and 0092 accepted closures, Owner-direct product direction/requirements, `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`, `POST_0051_TRIGGER_GATES.md`, `PRODUCTION_READINESS_GATE.md`, `docs/PROJECT_STATE.md`, ADR-0005/OQ-007, issues #355/#366/#372/#363.

**Production implementation checked:** `src/hullq/domain/physical_boat_claims.py` / `persistence/physical_boat_claims.py` durable optional current assertions, immutable revisions/heads, current actor+timestamp and batched observations; `domain/inventory_edit_request.py` / `application/inventory_editing.py` / real broker `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro` complete claim editor and stale save; `application/native_inventory_query.py` separate design-linked/claim-only Search evidence and qualified category admission; `application/current_public_eligibility.py` D29; `search/criteria_registry.py` fixed nine Sail instances and generic definition shape, `search/configuration_engine.py` shared AND evaluator and `search/boat_design_field_bridge.py` source-bounded design projection, `application/search_read.py` Sail routing, `api/app.py` search endpoints, `web/src/lib/searchApi.ts`, `web/src/components/SearchPageBody.astro`, locale pages. The current `specs/BOAT_DESIGN_SCHEMA.v0.6.json` supports only factory drive tokens `shaft`, `saildrive`, `outboard`, `other` and `unknown`; new POD/jet/sterndrive cannot be design-confirmed from v0.6's generic `other`.

**Already implemented / not re-decided:** Accepted nine Sail hard dimensions, exact canon/redirect/invalid Search contract and old-only sensitivity, FieldResolution/NamedVariant same-configuration MUST/AND, qualified concrete nonconflicting publisher claims, explicit SAIL/POWER/MOTORSAILER UNKNOWN/CONFLICT category, design-unresolved SAIL publisher-claim path with D29 and source-aware results, secure broker actor/claim editor, private source provenance, five existing locales, separate #355 runtime and scale hard gate. Existing Sail count 9 remains true after Power criterion #1.

**Exact remaining gap:** There is no single implemented Power `CriterionDefinition`, current-drive claim field, category-separated Power buyer search API/page, or canonical Power input vocabulary. A currently eligible no-design POWER broker listing with an authorized drive assertion cannot yet be found by *any Power-specific* hard technical predicate.

**Accepted-but-unimplemented obligations:** Additional Power engine/planing/equipment/conditional range/consumption/speed criteria, Power model identity and true variants, Power Buyer+Broker Search-fit parity, non-inferred motorsailer policy, category-correct NautiX import/export and real rights-cleared source acquisition (#372), all runtime/DB/abuse and representative Search scaling #355, joint Sail+Power product/pilot release #366, owner-direct trust, buyer saved search/alerts, support/compliance and operational providers. Do not claim any of these as part of first Power criterion.

**Material classifications:** DECIDED_AND_IMPLEMENTED = accepted Sail kernel/source/public eligibility, category and no-design qualified Sail claim Search; DECIDED_NOT_YET_IMPLEMENTED = first Power drive-configuration hard criterion, Power specialist proof/variant and further Power filters; EXPLICITLY_DEFERRED = unsupported factory-drive vocabulary beyond v0.6, operating points, importer/exporter/third-party source rights and full broker parity; GENUINELY_OPEN = motorsailer dual-domain rules, rights-cleared Power model corpus and future higher-order Power filter taxonomy; CONFLICT_OR_REGRESSION = crossing category boundary, treating v0.6 `other` as pod/jet/sterndrive, adding global criterion without updating acceptance count, or falsely claiming production launch readiness.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** YES  
**Technical Search criterion ordinal:** 10  
**Second-criterion bridge comparison:** PASS  
**Third-copy abstraction guard:** PASS  
**Workflow reassessment status:** PASS  

**Gate 3 comparison and no-third-copy proof:** Existing SLICE-0051 draft maximum, SLICE-0055 keel configuration and later accepted Sail criteria share one typed `CriterionDefinition` → already qualified design and current claim values → common `MixedAndQuery`/`evaluate_projection`/`evaluate_configuration` → source-qualified NativeInventory Search pipeline. The new Power categorical leaf maps to the identical qualified categorical projection loop; it differs only by an explicitly separate category filter, a typed drive claim accessor, an at-most-two-token legitimate v0.6 FieldResolution mapping, and Power URL/API/UI presentation. Its claimed current no-design matches reuse the accepted 0092 batched observation, D29 and publisher-source branches rather than a new Power scorer. This is **COMMON STRUCTURE GENERALIZED / REUSED**, not a third copy. The Power-domain's own second criterion will still need an independently reviewed next-step comparison; do not bypass this global marker.

**Marker discipline:** `docs/governance/POST_0051_TRIGGER_GATES.md` stays at `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9` and Sail remains 9 in READY and implementation review. After explicit Owner acceptance, the **separate closure** updates global count to 10 and adds an unambiguous textual split (SAIL 9, POWER 1); only then may the next criterion use global ordinal 11.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  

No hosted deployment, customer data, external provider, Pilot, SEO indexation or launch-phase transition; phase remains NOT_STARTED and Production Readiness stays IN_PROGRESS.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** First new category-specific public technical predicate controls a buyer's inclusion/exclusion; factory-vs-installed distinction, immutable actor revisions, domain URL parsing and missing design vocabulary can silently create false positives.  
**Must-never-change invariant:** No SAIL/MOTORSAILER/UNKNOWN/CONFLICT boat receives a Power positive. No drive without a publisher's own positive POWER and current specific drive in one revision qualifies, and no third-party or design v0.6 `other` source is mislabelled independently confirmed. D29/freshness and all Sail results unchanged. A mixed-drive or unspecified source is never hard-matched by heuristic.  
**Durable source of truth / loss boundary:** Existing Organization-owned immutable PhysicalBoat claim revisions/heads with publisher+actor+time, D29 listings/episode/media/freshness, separately admitted canonical BoatDesign and FieldResolution where truly available. Additive typed drive field/migration; no local session/browser draft or vendor filename permits Search-positive evidence.  
**Retry / replay / partial-failure behavior:** Exact revision replay idempotent; stale write returns conflict without mutation; unrelated broker form edit preserves drive claim; publisher drive/category retraction removes old match, no phantom fallback to prior version. Concurrent unrelated organizations cannot splice facts; old snapshot/migration payload meaning remains stable. Failed publish/edit/search does not return invented positive.  
**Absence-vs-error / fail-closed behavior:** Absent/UNKNOWN/MIXED/OTHER or invalid drive, no current POWER category, wrong actor/Org, conflicting current claimant, expired/non-public listing, missing applicable variant, unsupported BoatDesign v0.6 mapping and partial data → nonconfirmed/typed bounded reason. DB/auth/parser/transport failures return an error, **not** empty-confirmed data, default Power admission or price-based ranking.  
**Executable adversarial proof:** Real PostgreSQL18 multi-Organization revisions, two-connection races, valid/invalid category/drive scenarios for each token, D29/cover/expiry denial, unsupported Sail/saildrive/v0.6-other design values, FieldResolution/NamedVariant factory-vs-current refit evidence, malformed and mixed-route URLs, five-locale SSR XSS, unaltered original Sail buyer and broker API/SSR, synthetic 0/40/200 candidate cost and retained inspector.  
**Slice sizing assessment:** COHERENT  

One current-drive predicate necessarily spans persisted claim editing, category-evidence evaluation, one Power buyer API/SSR view and tests. It **does not** include unrelated engine count, range, NautiX Power mapping, source acquisition, power broker scorecard, full Power design schema v0.7 or general dual-domain browse.

## Required behavior / implementation boundary

1. Implement precisely the five public drive tokens in the companion normative spec. Keep claim-only `MIXED`/`OTHER`/UNKNOWN distinct but not query-match eligible, and do not conflate energy source, engine count, or saildrive. Allow legacy snapshot omission without schema rewrite.
2. Add one optional typed drive field, strictly validated and serialized through the **existing** PhysicalBoat claim lifecycle, current head/readback, broker editor and complete Astro form. If an unrelated edit silently erases the new field, the slice fails.
3. Add a separate Power-only buyer request parser and canonical noindex route. Do **not** widen Sail parser to accept Power keys or silently feed Power into Sail's existing nine-dimension search; preserve old API and URL behavior. Each of five locale pages displays accurate current publisher-source evidence.
4. Implement exactly one new static categorical Power `CriterionDefinition` using existing shared configuration/evidence/scoring kernel. Derive category and drive from the publisher's same current revision; fail closed across organizations. Preserve the accepted public category gate and D29; do not confuse technical match with third-party-independent validation.
5. Where genuinely available, a design-side bridge may only qualify `shaft` and `outboard` from accepted v0.6 canonical FieldResolution/NamedVariant paths with exact factory+current distinction; unsupported factory POD/STERNDRIVE/WATERJET records are **INSUFFICIENT_DATA** rather than imagined. No automatic v0.7. Document any deferred design-linked scope explicitly in buyer result limitation and issue #372, never claim whole Power model coverage.
6. Benchmark a synthetic real PG 0/40/200 mixed Sail/Power population, compare category exclusions and query counts, do not silently truncate accepted Power matches. Existing O(N) design-linked/claim-only Search and #355 pre-pilot scaling gate remain open even if this slice runs quickly on localhost.
7. No Power NautiX ingestion or export is authorized; the existing Sail-only output writer must not be allowed to coerce a Power listing to a `sail-yacht` label. If the existing export path would do so for the tested Power row, add a **narrow fail-closed eligibility guard at its preexisting boundary**, not a new Power writer, and demonstrate the accepted seven Sail output formats unaffected.

## Explicitly out of scope

Separate Power engine/fuel/horsepower/count/model and displacement/hull behavior criteria, conditional operating-point values/range/speed/consumption, broad refit validation, drive mixtures as multi-select semantics, future schema v0.7 redesign, full Power Broker Search-fit, additional Sail criteria, full category-agnostic browse, source feed scraping, real brokers/owner-direct trust, production deployment, joint release/pilot, Paid Search relevance, full NautiX import/export mapping, XLSB export (#362) and operations source-rights clearance.

## Deliverables / expected touchpoints

- Normative exact drive-token and source-provenance policy: companion `specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md` (no alternative hidden taxonomy allowed).
- Domain enum/claim/migration and full authorized editor parser/readback/form: `src/hullq/domain/physical_boat_claims.py`, `src/hullq/persistence/physical_boat_claims.py`, `src/hullq/domain/inventory_edit_request.py`, `src/hullq/application/inventory_editing.py`, broker edit `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro`.
- Separate static Power criterion definition and shared-kernel evaluation: `src/hullq/search/criteria_registry.py` and a bounded `power_drive_design_bridge.py` adapter if source-qualified v0.6 FieldResolution exists; `src/hullq/application/native_inventory_query.py` plus typed result source and category qualifier, new Power request-state/application routing; existing Sail path untouched.
- New Power FastAPI route `/api/search/{locale}/power`; five noindex Astro SSR Power pages `/{locale}/power/search` with localized controls, safely escaped result list/empty states and existing listing contact provenance; shared TS API types. All five locale routes are a single UI capability, not five slices.
- Synthetic tests/retained inspector: every positive Power token and rejected category, current revision/tenant/concurrency, real Design FieldResolution exclusions, D29, URL/DTO/source privacy, untouched nine Sail dimensions, HTML five locales, safe noindex and 0/40/200 SQL evidence. Fix localized URL canonical redirects without introducing duplicate-content exposure.
- Retained evidence table for first Power drive criterion mapping, sources, result states, all limitations, and update #372 only once actual implementation passes exact independent review and Owner accepts.

## Acceptance criteria

- [ ] One Power categorical `CriterionDefinition` with exact five-token enum; reuse accepted `CategoricalLeafCriterion` / common MUST/AND kernel and no new Power ad hoc evaluator. Sail 9 unchanged; global accepted total stays 9 until later acceptance closure advances to 10.
- [ ] Real current publisher claim of drive and own category POWER from one immutable current revision, valid authorization/revocation/stale handling and D29 make a design-unresolved POWER boat match only the correct Power query, with `PUBLISHER_CLAIM` explanation and safely serialized private provenance.
- [ ] Every token positive+negative tested, including mixed/other/unknown/unsupported Sail drive; explicit SAIL/MOTORSAILER/UNKNOWN/CONFLICT exclusions, other-org-only POWER and cross-org disagreements all fail closed; no Sail-to-Power result contamination.
- [ ] Full backend authorization + claim edit and real Astro SSR form round-trip; save of unrelated field retains existing drive; malformed/stale/foreign submission changes zero durable rows. Legacy NULL/omitted vs explicit UNKNOWN preserved.
- [ ] Current boat refit vs original factory drive distinguished; synthetic source-qualified BoatDesign v0.6 SHAFT/OUTBOARD FieldResolution if actually admissible; v0.6 `other`/`unknown`/`saildrive` never proves unsupported drive; missing design bridge prominently classified insufficient, never silently marked complete.
- [ ] Power-only API and five-locale noindex SSR route show exact condition, correct current publisher label, buyer listing identity/link/contact where permitted, truthful no-data vs no-result vs transport error and safe canonical redirect/invalid parser. No real external pilot/public Search marketing or SEO indexing.
- [ ] All accepted Sail search/sensitivity and Broker search-fit tests still pass unchanged; local Shortlist/Compare unaffected; no third evaluator, price/publisher benefit/sponsorship rank influence or category fallback.
- [ ] D29, concurrent revisions, partial DB errors, orphan category, deleted/withdrawn listing, actor scope, source/rights, cross-Org conflict and NautiX false Sail label adversarial proof exercised with real PG18, FastAPI and Astro. No use of unlicensed external data.
- [ ] Synthetic representative 0/40/200 inventory cost and exact admissible-match retention reported, query plan/index and bounded O(N) caveat documented. No unsupported production throughput SLA; issue #355 pre-real-data STOP unchanged.
- [ ] Quality: real PostgreSQL 18 tests, `uv run python scripts/validate_repository.py`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src`, unit, web `npm test` / `astro check`/build, retained local inspector, then **exact-HEAD six-job remote CI + manufacturer reproducibility**, independent code review and explicit Owner acceptance BEFORE merge.
- [ ] After reviewed Owner acceptance and separate docs-only closure, global criterion marker reconciles 9→10 with per-domain split Sail 9 / Power 1. Production Readiness IN_PROGRESS, Launch Pack NOT_STARTED, real external data NOT_PRESENT, pilot/public launch NOT_STARTED; #355/#366/#372 remain open.

## Stop conditions / review expectations

- The new Power Drive criterion matches a SAIL/MOTORSAILER/UNKNOWN/CONFLICT category or a Power listing without the publishing Organization's own current positive category/drive assertion.
- An external manufacturer spec, textual tag, v0.6 `other` token, boat model/engine brand or unproven variant is silently treated as a qualified current drive or independent design truth.
- The editor loses the new field on unrelated save; stale retry or unauthorized actor changes a durable claim; category and field are combined from different revisions.
- A design-linked positive requires fake BoatDesignRef/FieldResolution, invented v0.7 migration, silent acceptance of unlabeled powertrain/refit or a second independent Power scorer.
- Existing Sail data/URL/criterion regression, D29, API-source boundary, organic neutrality, safe NautiX Power exclusion, unbounded serial performance amplification or a false production readiness claim cannot be prevented within one coherent feature. STOP with a specific independently reviewable amendment rather than silently lowering this contract.

## Sequence / Owner workflow

1. **READY only:** prepare this doc plus exact Power normative spec, reconcile `docs/PROJECT_STATE.md` + compact slice index (Owner FINISH 0092 SUCCESS, 0093 SELECTED/READY), independent exact-HEAD docs/spec review, full remote 6-job CI/manufacturer/Deploy PASS and squash merge docs-only READY PR to canonical `main`.
2. Owner executes unchanged `START_SLICE.bat` with `0093`. **No START-output submission required**, no tool/script rewrites.
3. Claude implements on its generated `slice/0093-...` branch only; returns exact HEAD and real PG/API/SSR proofs as **REVIEW**, with unexecuted external gates distinguished.
4. Independent exact-HEAD implementation review; findings amended on the same branch; full remote CI/manufacturer and explicit Owner acceptance before implementation merge.
5. Separate docs-only acceptance closure with its own exact-HEAD remote gates and merge; only then Owner runs unchanged `FINISH_SLICE.bat 0093`.
6. No automatic next slice, provider activation, real broker data, external pilot, public search indexation or market launch.

## Required completion report

Use every mandatory `docs/slices/SLICE_TEMPLATE.md` handoff field: Slice, Product execution checks, Changes, Local validation and exact commands/results, External verification separately by run ID, Findings/deviations, Follow-up, Agent declaration. Never mark unrun gate PASS or status DONE.
