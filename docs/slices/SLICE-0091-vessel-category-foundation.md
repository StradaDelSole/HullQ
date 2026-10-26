# SLICE-0091 — Explicit Sail+Power Vessel Category Foundation

**ID:** SLICE-0091  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Readiness authority:** Proposed; not operative before independent exact-HEAD readiness review, CI/manufacturer reproducibility, merge to canonical main and Owner-local START_SLICE.bat 0091.  
**Risk:** HIGH_RISK — legacy Sail Search exclusion, shared identity/claims, type conflict and category provenance, mixed-supply safety  
**Owner selection:** 2026-10-26: after Owner-confirmed local FINISH_SLICE.bat 0090 SUCCESS and accepted research closure PR #380 merged, Owner approved proceeding with the proposed category foundation (“ok klingt gut, go ahead”). This authorizes **readiness preparation**; implementation only after this contract is independently reviewed/merged and Owner runs START.  
**Depends on:** Owner-accepted SLICE-0090 research and separate acceptance closure, accepted Sail+Power product decision #366; implementation tracker #372; pre-real-data STOP #355.  
**Main baseline at readiness authoring:** `fe7f4c0fbd89136e733646c199d68ffe8f11cee5` (0090 closure merged).  
**Controlling research:** `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md` §2.1 and §4 row A; `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`; `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md`. §2 of the research pack is **DRAFT**, not silently Owner-approved ADR: this READY contract selects the narrowly scoped foundations below, subject to independent readiness review.

## One capability / observable outcome

Implement **one explicit, source-qualified and deterministic vessel category contract** for canonical design and concrete offered boats: SAIL, POWER, MOTORSAILER, UNKNOWN and an independently derivable CONFLICT resolution state. Provide persistent category claims, authorization/provenance and stable internal readback/decision evidence. Prevent unsupported category guesses and category leakage into Sail-specific evaluation **without enabling Power product search**. Synthetic/authorized internal inspector demonstrates each state, design/concrete disagreement, legacy-no-category compatibility and category-specific fail-closed behavior.

**ONE-CAPABILITY CHECK:** PASS

 one category truth foundation; no Power technical criterion, no unrelated feed/import rewrite, no general marketplace browse.  
**VISIBLE-RESULT CHECK:** PASS

 a deterministic, inspectable current category resolution with explicit source/evidence and reason, exposed through a safe internal authorized readback/inspector; observable negative cases for unknown/conflict, no manufactured Power matches.  
**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS

 joint Sail+Power target, one shared marketplace kernel, Buyer/Broker quality parity, no public Sail-only/C-light pilot, no Pay-to-win or truth guessing.  
**REPOSITORY RECONCILIATION CHECK:** PASS, subject to implementer exact-main re-verification listed below.  
**TRIGGER GATES CHECK:** PASS

 nine accepted Sail criteria unchanged; category is an **admission/type foundation**, not technical hard Search criterion #10. Reassess POST_0051 gate only if an implementation unexpectedly introduces a public hard search facet.  
**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS

 MVP-BUY-001/002 remain PARTIAL across Sail+Power, Buyer persistence/Saved Search and owner-direct trust stay OPEN; #355 higher-severity external broker-upload hardening remains mandatory before *any* external inventory; this purely synthetic internal foundational slice does not trigger its production/data gate.  
**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

 required adversarial proof and STOP thresholds below.  
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE

 no production/pilot/data phase transition; Launch Pack remains NOT_STARTED.

## Decision / implementation reconciliation

**Accepted records checked:** docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md, docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md §2.1/§4A, docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md, docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md, docs/governance/POST_0051_TRIGGER_GATES.md, docs/governance/PRODUCTION_READINESS_GATE.md, docs/PRODUCT_EXECUTION_PLAN.md, docs/PROJECT_STATE.md and issues #366/#372/#355.
**Production implementation checked:** src/hullq/domain/market_identity.py PhysicalBoat optional BoatDesignRef; src/hullq/domain/physical_boat_claims.py typed AssertionKind wrappers; src/hullq/search/criteria_registry.py nine shared criterion instances; src/hullq/application/native_inventory_query.py same MUST/AND evaluation; src/hullq/persistence/inventory_search.py design-linked-only; src/hullq/domain/import_nautix.py Sail allowlist and src/hullq/domain/inventory_export.py fixed Sail tag. Implementation agent must inspect actual DB tables and APIs before migration.
**Already implemented / not re-decided:** Nine accepted Sail hard criteria, design/current-boat distinction, immutable publisher-claim revisions, D29 eligibility, accepted 0083 import/0088 export/0089 reporting. No Power technical criterion added by category typing.
**Exact remaining gap:** No explicit, persistently sourced Design-versus-PhysicalBoat Sail/Power/Motorsailer/UNKNOWN/CONFLICT category evidence and readback. This slice builds only this category foundation, not any Power search capability.
**Accepted-but-unimplemented obligations:** #372 future design-unresolved search and Power criteria/SSR/API parity; #355 import/runtime hardening before real external data; #363 local browser check; Buyer Saved Search, owner-direct trust and Launch Pack remain OPEN.
**Material classifications:** DECIDED_AND_IMPLEMENTED = nine Sail dimensions and unchanged shared kernel; DECIDED_NOT_YET_IMPLEMENTED = category persistence/resolution, later Power facets and concrete-only search; EXPLICITLY_DEFERRED = import/export Power mapping and external ingestion; GENUINELY_OPEN = motorsailer search policy and source-specific data rights; CONFLICT_OR_REGRESSION = a new category filter must never erase legacy Sail results or fabricate certainty.

## Trigger gates

**Production readiness gate:** IN_PROGRESS
**Adds technical native Search criterion:** NO
**Technical Search criterion ordinal:** NOT_APPLICABLE
**Second-criterion bridge comparison:** NOT_APPLICABLE
**Third-copy abstraction guard:** NOT_APPLICABLE
**Workflow reassessment status:** PASS

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE
**Launch-pack phase after this slice:** NOT_APPLICABLE

No Launch Pack stage advances; the existing PRODUCTION_LAUNCH_PACK_PHASE stays NOT_STARTED. Only synthetic internal category contracts/authorized nonproduction validation are in scope.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK
**Why this classification:** Category mishandling can contaminate Sail technical matching, misstate an actual vessel's propulsion/category, or bypass publisher authorization and public eligibility.
**Must-never-change invariant:** No label-based Sail/Power guess, no missing-category Sail backfill, no unauthorized category mutation, no unreviewed verified badge, no second truth kernel and no unqualified Power exposure.
**Durable source of truth / loss boundary:** Canonical PostgreSQL-backed immutable, Organization-scoped concrete claim revisions and separately qualified design evidence; readback always resolves current version and retains conflict provenance.
**Retry / replay / partial-failure behavior:** Revision writes preserve idempotency/uniqueness and current authorization; failed, stale, cancelled or conflicting writes cannot partially replace earlier valid current evidence or create implicit positive classification.
**Absence-vs-error / fail-closed behavior:** No category value, explicit UNKNOWN, contradiction and read/query/auth errors remain distinct; unknown/conflict must not become SAIL by default, and legacy Sail-compatible search cannot be silently removed.
**Executable adversarial proof:** Actual unit and PostgreSQL 18/authorized API/browser checks with synthetic SAIL/POWER/MOTORSAILER/UNKNOWN/CONFLICT, misleading labels, missing design, concurrent/retracted/current revisions, cross-tenant denial, legacy Sail inventory equivalence and explicit category exclusion; no falsely claimed live Power Search proof.
**Slice sizing assessment:** COHERENT

## Repo reconciliation — accepted facts

1. `src/hullq/domain/market_identity.py`: `PhysicalBoat` holds an **optional** `BoatDesignRef`; no inferred manufacturer identity, HIN lookup or category. `PhysicalBoat` must remain a concrete vessel identity even without a recognized design.
2. `src/hullq/domain/physical_boat_claims.py`, and `src/hullq/persistence/physical_boat_claims.py`: current organization/publisher's immutable revision snapshots use typed `AssertionKind` values; omission, explicit UNKNOWN, and asserted concrete values remain separate.
3. `src/hullq/search/criteria_registry.py`, `src/hullq/application/native_inventory_query.py`, `src/hullq/search/configuration_engine.py`: **nine** accepted technical Sail criteria share the same MUST/AND/evidence path; **do not create a second category or Power truth engine**.
4. `src/hullq/persistence/inventory_search.py`: current design-linked candidate SQL includes `pb.boat_design_ref IS NOT NULL`; an independently qualified, design-unresolved candidate path is **future row B**, NOT scope 0091.
5. `src/hullq/domain/import_nautix.py` currently rejects non-Sail source boat-type tokens; `src/hullq/domain/inventory_export.py` unconditionally emits `sail-yacht` under the currently Sail-only admitted export supply. NautiX 1.4 XSD has **33 `power-*` enumerations**, `sail-motorsailer`; category-aware mapping and round-trip work is **future row E**, NOT 0091.
6. No existing design-category storage schema, concrete claim-field allowlist, migrations or API contract may be guessed from a research diagram. **Before implementation** inspect actual `BoatDesign` persistence/readback shape, current revision writer/reader and D29/public eligibility, all DTO/API/SSR boundaries and all relevant tests; use current symbols, not speculative filenames. Record exact impact map in the implementation report.

## Scoped design decisions for SLICE-0091

**A. Semantic separation.** `VesselCategory` values **SAIL, POWER, MOTORSAILER** are positive, explicitly sourced claims. `UNKNOWN` means no reliable selected category; `CONFLICT` means unresolved, material contradiction across the authorized current sources. `CONFLICT` is a **resolution outcome**, NOT a publisher-input enum value and NOT a new `AssertionKind`. Distinguish: not-provided/omitted, explicit `UNKNOWN`, valid positive assertion, retraction and derived cross-source `CONFLICT`. Do not infer a category from display name, hull shape, rig text, engine count, model name, keel or marketing labels.

**B. Two source planes.** Preserve provenance separately for (i) design/generation category, only when established by authorized catalog/design evidence, and (ii) the publisher's latest immutable concrete PhysicalBoat category claim, attributed to its current authorized Organization. Linking a design does not silently produce a current concrete assertion. Make the precedence/resolution matrix explicit, including no-design, either-source UNKNOWN, same-source agreement, design-vs-concrete conflict, competing current publisher/supported claims, and retraction. A design SAIL + concrete POWER inconsistency yields `CONFLICT` absent an explicitly documented and reviewed resolution — not a best guess. A legitimate category change requires versioned evidence rather than destructive overwrite.

**C. Legacy safe adoption.** Existing database rows and existing nine-criterion Sail Search remain behavior-compatible. Do **not** migrate all historical rows to “confirmed Sail” merely because today's admitted supply is Sail. Legacy null category is UNKNOWN at the new read boundary; current pre-category Sail workflows must not be silently emptied by an unqualified category filter. If any category-specific gate is activated for technical Search in this slice, it must have (a) a proved legacy compatibility path scoped only to already-accepted Sail-eligible inventory, (b) fail-closed exclusion of an **explicit** POWER/MOTORSAILER/CONFLICT classification from Sail-only technical-confirmed matches, and (c) no blanket unknown-to-SAIL upgrade. If those cannot be satisfied together without weakening truth, STOP and seek independent review rather than accepting a Sail regression or mislabeling. Do not expose a “category verified” public badge based only on default/legacy assumptions.

**D. Security/current truth.** Durable writes/edit operations must use accepted Organization ownership, current membership/MFA/PUBLISHER authorization and revision boundaries; no cross-tenant claim mutation. Readback must use current snapshot and retain source/issuer/revision/reason, no historical stale snapshots promoted as current. Separate design evidence from broker-provided concrete data. Public D29 eligibility and original lifecycle/freshness/claims read-path protections may not be loosened.

**E. Internal observable result.** Implement an inspectable, deterministic read model and a bounded end-to-end internal test/inspector on synthetic data. If a new API endpoint is required, it must be authenticated, Organization-scoped, nonpublic, read-only unless explicitly justified by the bounded claim-edit capability, and must not create a new external Power listing surface. Reuse existing UI/API patterns where feasible; the tester must be able to see an actual classified category and reason without reading raw SQL.

## Explicit boundaries / out of scope

- No new `CriterionDefinition` technical Power field, conditional operating point, rated engine facts, no new Power buyer Search or Power Search-fit; those remain later work.
- No general category browse, live Power listing eligibility, searchable Power technical results or marketing-ready mixed marketplace.
- No design-unresolved technical Search admission path (SLICE-0090 row B); do not sneak it into category plumbing.
- No generalized NautiX Power import/export, category vocab round-trip, spreadsheet import changes, external feeds, third-party ingestion or rights clearance (row E/F).
- No real external inventory, existing credentials/accounts, external broker-product pilot, public Sail-only launch, owner-direct trust activation or production provider deployment.
- No modification to the owner's `START_SLICE.bat`, `FINISH_SLICE.bat`, `LOCAL_TEST_HULLQ.bat` or ignored local files; no procedure changes.
- No automatic #372 closure, no unilateral new ADR or new policy for motorsailer multi-domain matching. Internal MOTORSAILER is an explicit category; future domain-specific filter semantics remain genuinely undecided.

## Acceptance criteria

- [ ] Exact current-main design and concrete-claim persistence/DTO/API/SSR map documented and reconciled before making migrations; additive backward-compatible schema plus typed `VesselCategory` and qualified revision/readback approved through existing patterns.
- [ ] Category state machine correctly distinguishes positive `SAIL`/`POWER`/`MOTORSAILER`, omission, `UNKNOWN`, `CONFLICT`, retraction, unauthorized or stale input; no `CONFLICT` accepted as publisher's positive category token.
- [ ] Authorized design-side and concrete-side category facts have independent provenance, evidence, revisions and deterministic precedence; unknown/conflict are never promoted to confirmed by heuristics.
- [ ] The current nine Sail criteria continue passing unchanged accepted regression suites, including existing design-linked listings with legacy null category; explicitly categorized POWER/MOTORSAILER/CONFLICT input cannot silently yield a Sail confirmed-match. No accidental expansion of category support in existing import/export.
- [ ] Current authorized Organizations may perform only intended category claim write/update; cross-tenant, stale-current-role, unauthenticated and replayed revisions rejected. No unreviewed public category verification UI or weak API admission.
- [ ] Targeted unit, persistence, PostgreSQL 18 integration and bounded FastAPI/Astro/SSR inspector where applicable show all three positive categories plus UNKNOWN/CONFLICT and at least one scenario each for missing design link, disagreement, category retraction and legacy-safe Sail behavior. Distinguish executed results from future/excluded proof.
- [ ] Synthetic hard-case corpus `FIX-0090-03,08,11` and control `01,02` mapped to executable 0091 tests for **category-only** relevant assertions; do not claim Power Search test success.
- [ ] `uv run python scripts/validate_repository.py` PASS; implementer reports actual changed files and focused tests; independent **exact-HEAD** review plus PR CI (all jobs)/manufacturer reproducibility success before Owner acceptance, merge and separate closure.
- [ ] All existing STOPs and project state remain truthful: Production Readiness `IN_PROGRESS`, Launch Pack `NOT_STARTED`, external production data `NOT_PRESENT`, no pilot/public launch, Sail Search 9 technical criteria.
- [ ] If persistent category write/readback is impossible without introducing a second truth engine, inventing manufacturer evidence, silently changing legacy Sail acceptance or allowing unsupported Power admission: report BLOCKED, not a partially “DONE” slice.

## Risk register and bounded proof

| Failure mode | Required negative evidence | STOP |
|---|---|---|
| POWER or MOTORSAILER leaks into Sail technical matches | Dedicated cross-category non-match/exclusion unit+PG read test | Any falsely confirmed Sail match |
| Legacy Sail rows disappear when category null | Before/after accepted Sail fixture inventory equivalence | Any unexpected Sail loss |
| Design/category is guessed from a label | Negative tests for deceptively named synthetic designs | Any heuristic inferred category |
| Concrete assertion automatically overrides design truth | Disagreement producing explicit CONFLICT with both sources retained | Any overwrite, implicit precedence |
| UNKNOWN silently becomes SAIL in durable data | DB/default/readback proof for legacy rows | Any silent backfill |
| Stale/retracted/cross-tenant source changes current category | Current revision and authorization/freshness tests | Any authorization or revision violation |
| Current D29/public eligibility bypass | Existing publication/auth invariant regression suite | Any newly visible unqualified listing |
| External source rights or real broker data assumed | No new ingestion/provider path or real data | Any external activation |

## Sequence and owner workflow

1. **Readiness only (this document):** independent exact-HEAD readiness review, successful CI/manufacturer reproducibility and merge of docs-only READY PR.
2. **Owner only:** run unchanged `START_SLICE.bat` selecting `0091`, then share the output as usual.
3. **Claude implementation:** reconcile current HEAD; work on the created `slice/0091-...` branch; complete only the above capability; commit/push and return `REVIEW` with exact HEAD, changed files, test matrix, unmapped ambiguities and STOP outcomes.
4. **Independent review:** amendments on same branch for findings, exact-HEAD remote gates; explicit Owner approval before implementation merge.
5. **Separate acceptance closure:** after implementation merge, docs-only closure PR and its own exact-HEAD CI/manufacturer; after closure merge Owner runs unchanged `FINISH_SLICE.bat` 0091.
6. **Next reassessment:** no successor slice auto-start; 0090 decision-map rows B–H remain unselected.

## Completion report

Use the **exact mandatory fields** of `docs/slices/SLICE_TEMPLATE.md`: Slice, Product execution checks, Changes, Validation, External verification, Findings, Follow-up, Agent declaration. Report only actually executed proof; future capabilities or unsupported production claims stay FUTURE/NOT APPLICABLE.
