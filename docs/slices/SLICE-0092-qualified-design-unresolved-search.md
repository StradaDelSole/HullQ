# SLICE-0092 — Qualified Technical Discovery for Design-Unresolved Boats

**ID:** SLICE-0092  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Readiness authority:** Proposed; not operative before independent exact-HEAD readiness review, passing CI/manufacturer reproducibility, READY PR merge to `main` and the Owner's unchanged local `START_SLICE.bat` choosing `0092`.  
**Risk:** HIGH_RISK — newly admitted native Search candidates; truth, publisher identity, rights, provenance, concurrent revisions and buyer-facing evidence  
**Owner selection:** 2026-10-27: following verified successful Owner-local `FINISH_SLICE.bat 0091`, the Owner instructed “weiter gehts herr kollege”. This selects preparing the next bounded readiness proposal, not permission to bypass the normal exact-HEAD review/START workflow.  
**Depends on:** Owner-accepted, locally FINISHED SLICE-0091 (implementation squash `b707c8ebf00a7e40f849e49f60490327583eb74a`; closure `f649186ca6241da2f8a639e6b2b64555efc38aa6`); Owner-accepted SLICE-0090 architecture research §2.3 / §4 row B; joint Sail+Power decision #366 and tracker #372.  
**Baseline:** canonical `main` `f649186ca6241da2f8a639e6b2b64555efc38aa6` on readiness selection.  
**Further STOP:** #355 real external upload/pilot gate remains OPEN, Production Readiness IN_PROGRESS, Launch Pack NOT_STARTED.

## Objective / one visible capability

Enable the **second, strictly qualified PhysicalBoat-current-claim candidate path** for otherwise-eligible **design-unresolved** (`PhysicalBoat.boat_design_ref IS NULL`) broker listings, without treating broker statements as verified canonical BoatDesign facts. A synthetically seeded, currently-public-eligible explicit **SAIL** PhysicalBoat with no BoatDesignRef, authenticated/current publisher evidence and qualified values for the buyer's selected existing Sail dimensions should be discoverable in its existing Direct Search entrypoint with an unambiguous `PUBLISHER_CLAIM` evidence label. Unqualified/ambiguous claims must never produce a confirmed match.

The candidate **enumeration and admission architecture is category-neutral**, so explicit POWER can be represented internally without a BoatDesign link and without misleadingly declaring it searchable through the Sail criterion family; however **NO POWER technical Search, motorsailer dual-domain matching, Power UI, Power CriterionDefinition or new Search dimension is introduced**. Until a separately reviewed Power domain exists, POWER/MOTORSAILER/UNKNOWN/CONFLICT design-unresolved candidates are NOT confirmed through Sail filters; only an explicit, nonconflicted SAIL category may enter this new **claim-only** Sail matching path. Existing design-linked legacy UNKNOWN category behavior from SLICE-0091 remains unchanged.

This is the direct next dependency in SLICE-0090 §4 (row B before Power criterion row C); the proposal accepts only the bounded field-proof policy specified below, not §2.3's whole unratified draft as a hidden ADR.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS

One new qualification/admission path for design-unresolved PhysicalBoats, shared by pure draft-only and mixed existing Sail Search; typing, provenance, public serialization, browser explanation and synthetic proof are inseparable aspects of the same buyer-visible truth. No separate Power criterion or catalog ingest.

**VISIBLE-RESULT CHECK:** PASS

An authorized local PostgreSQL18 + API + built-Astro SSR synthetic scenario displays one otherwise-invisible, design-unresolved SAIL listing as a match explicitly “laut Anbieter/Brokerangabe” (localized, no verified-design claim), and shows denied/insufficient cases, leaving historical design-linked Search matches unchanged. A retained inspector produces independently reproducible evidence even before local browser access.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS

Owner-accepted one HullQ marketplace with two later fully featured specialist domains; this implements a shared prerequisite without authorizing Sail-only, C-light or external early release. Organic rankings and current D29 gating remain uncompromised. No implicit “verified” badge.

**REPOSITORY RECONCILIATION CHECK:** PASS

Exact source/evidence map below was reconciled against canonical post-0091 `main`; design-linked, concrete evaluator and category resolver already exist and MUST be reused, not rebuilt.

**TRIGGER GATES CHECK:** PASS

The number and semantics of the **nine** accepted Sail hard technical dimensions remain unchanged; qualified access to existing dimensions is candidate admission, not a tenth criterion. No new Power criterion in this slice. Accepted shared `CriterionDefinition` + `evaluate_configuration` MUST/AND kernel remains one source of technical truth.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS

This advances the PARTIAL `MVP-BUY-001` technical search and `MVP-BUY-002` truthful evidence plus `MVP-DATA-001/005` source provenance/conflict, without claiming those broader cross-domain capabilities DONE. Owner-direct trust, buyer persistence, Saved Search/alerts, source-rights clearance, privacy/support/admin and operations remain separately due by their original gates. Higher-severity #355 is a **before-real-data/pilot STOP**, not a block on this strictly synthetic internal feature; work on #355 must not be replaced or silently deemed closed by Search progress.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

Risk/failure proof below is specific to false matches, conflicting or stale source claims, category races, partial visibility and source-label leakage.

**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE

No real external production data, external users/pilot, new provider or launch-phase transition. Phase stays NOT_STARTED.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md`; `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md` §2.3 / §4 row B; `docs/POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md` §§2–3; SLICE-0091 implementation/closure; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`, `POST_0051_TRIGGER_GATES.md`, `PRODUCTION_READINESS_GATE.md`, `docs/PROJECT_STATE.md`; issues #366/#372/#355/#363.
**Production implementation checked:** `src/hullq/persistence/inventory_search.py` `list_active_design_linked_listings` SQL restricts `pb.boat_design_ref IS NOT NULL`; `src/hullq/application/inventory_search.py` pure `draft_max` entrypoint; `src/hullq/application/native_inventory_query.py` mixed nine-criterion Search and `classify_concrete_candidate`; `src/hullq/application/search_read.py` shared request dispatch/sensitivity; `src/hullq/search/criteria_registry.py` nine typed `CriterionDefinition`s/`read_claim`; `src/hullq/search/configuration_engine.py` `evaluate_configuration`; `src/hullq/persistence/physical_boat_claims.py` current Organization per-field observations/revision/recorded-by/recorded-at; `src/hullq/application/vessel_category_resolution.py` + `src/hullq/persistence/vessel_category_snapshot.py` one-statement current category evidence; `src/hullq/application/current_public_eligibility.py` D29; `src/hullq/api/app.py` direct Search serialization; current Astro Search buyer components/locale handling.
**Already implemented / not re-decided:** Nine Sail dimensions, unchanged qualified design-linked/NamedVariant FieldResolution same-configuration MUST/AND truth, independent current PhysicalBoat claims, D29/freshness, public source-specific evidence, 0091 SAIL/POWER/MOTORSAILER UNKNOWN/CONFLICT resolution with cross-Org guard and legacy category parity. The existing pure draft-only route is a separate current production path and must not be missed.
**Exact remaining gap:** Because every existing candidate query requires `pb.boat_design_ref IS NOT NULL`, a currently-public-eligible, explicitly SAIL, otherwise sufficiently qualified concrete offered boat without a BoatDesign is categorically invisible to buyer technical Search. No accepted, properly labelled source-qualified claim-only alternative currently exists.
**Accepted-but-unimplemented obligations:** #372 Power technical criterion family and Power Buyer/Broker parity, motorsailer policy, Power import/export and conditional measurement/refit/rights; #355 pre-real-upload/pilot hardening; #363 local one-click browser; owner-direct publication/trust and Buyer Saved Search/alerts; real operational provider and Launch Pack. None is waived.
**Material classifications:** DECIDED_AND_IMPLEMENTED = accepted design-linked Sail/Search/category/claim/D29 backbone; DECIDED_NOT_YET_IMPLEMENTED = bounded source-qualified design-unresolved candidate admission and future Power domain; EXPLICITLY_DEFERRED = other-category technical matching, new conditional Power facts/import/export/external sources; GENUINELY_OPEN = future Motorsailer cross-domain policy, Power vocabulary and specific external rights; CONFLICT_OR_REGRESSION = false claim-only matches or loss of existing design-linked Sail results.

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

No external data/product exposure, deployment, new source ingestion or production phase progression. `PRODUCTION_LAUNCH_PACK_PHASE` stays `NOT_STARTED`.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK
**Why this classification:** The old design-required admission is an explicit trust constraint. Replacing it with unqualified self-reported values could mislead buyers; stale, conflicting, incorrectly scoped or cross-tenant publisher claims could create false confirmations; split SQL read snapshots can tear source/category revisions.
**Must-never-change invariant:** Design-linked candidates and all nine accepted Sail field evaluations remain identical. No inferred BoatDesign/generation/variant; a claim-only positive match requires a *current authorized publisher attestation plus all applicable field-level evidence thresholds*, the publisher's **own** explicit compatible nonconflicted SAIL category claim in that same revision, D29 public eligibility and one shared MUST/AND criterion truth. No `PUBLISHER_CLAIM` may be serialized as `DESIGN_CONFIRMED` / “verified”.
**Durable source of truth / loss boundary:** Existing PostgreSQL `native_listings`, `market_episodes`, `physical_boats`, Organization-specific immutable `physical_boat_claim_revisions/heads`, current category assertions, D29 and listing freshness. No replacement local cache/session/browser data may authorize a Search result. Any additional explicit qualification/evidence persisted by this slice must be additive, versioned and source-/revision-bound, with retention/retraction proof.
**Retry / replay / partial-failure behavior:** Replayed publisher revisions must not create duplicate or resurrected current facts; cancelled/error Search cannot turn into empty/confirmed results; cross-Organization current contradictions must be evaluated from one coherent current state; an earlier category/field value cannot be reused after revision, withdrawal, removal of claim or D29 invalidation.
**Absence-vs-error / fail-closed behavior:** Unknown category, OTHER unsupported token, missing BoatDesign when a design-linked path is demanded, absent/UNKNOWN/invalid/mismatched unit/unsupported basis, unqualified issuer, expired/retracted claims, same-boat cross-Org contradictions, unsupported Power/Motorsailer and DB/auth errors must yield distinct nonconfirmed outcomes and auditable bounded reasons; errors never default to SAIL or `CONFIRMED_MATCH`.
**Executable adversarial proof:** Real PostgreSQL18 + FastAPI + built Astro synthetic run for pure draft-only/mixed existing criteria; explicit SAIL vs POWER/MOTORSAILER/UNKNOWN/CONFLICT; no-design valid claim, partial/UNKNOWN, bad units, wrong applicability, stale revision/retraction, cross-Org disagreement, writer/read race, D29 suppression, tenant/user source spoof, wrong issuer, buyer representation, 5-locale string escaping and no confirmed-design label; before/after design-linked fixture match sets equal.
**Slice sizing assessment:** COHERENT

This is **one** read/admission capability spanning persistence/application/DTO/buyer evidence. Do not make a second broad data-verification framework, arbitrary API or Power Search implementation to satisfy it; if immutable per-field proof cannot fit safe existing architecture, STOP with a specific independently reviewable amendment rather than enabling a weaker shortcut.

## Selected field-proof policy for this slice

**A. Candidate identity and category.** New separately named `list_active_design_unresolved_listings`-style read selects exact ACTIVE listing → MarketEpisode → PhysicalBoat with `boat_design_ref IS NULL`; **never modify** `list_active_design_linked_listings` or its accepted SQL. Reuse the same D29 current-public and freshness checks. Resolve 0091 category from current source-qualified state and require explicit positive, nonconflicted `SAIL` for the new Sail path **AND** require that the *publishing Organization itself*, not merely another current claimant, has an explicit current `VALUE_ASSERTION(SAIL)` category claim. Another Organization's category assertion cannot lend the publisher its Sail eligibility. Both category and constrained technical fields must refer to the same publisher's coherent current claim revision. POWER is a typed future-domain candidate but has **no Sail positive match**; MOTORSAILER dual matching stays undecided, so also no positive Sail match. Do not assume UNKNOWN means Sail here, unlike the **pre-existing** design-linked legacy compatibility path.

**B. Publisher source and legal scope.** Only the publishing Organization's **current**, authenticated/MFA/PUBLISHER-authored `PhysicalBoatClaimRevision` may assert the concrete value; historical actor/revision/time and owning Org must be inspectable. A recorded publisher statement is `source_basis = PUBLISHER_CLAIM`, **not** independent manufacturer verification. Reuse accepted claim-write authorization and D29 terms; do not treat other Organizations' statements as permission to syndicate their data, or third-party documents/media as cleared content. No owner-direct claim-only Search admission until its separately reviewed trust/rights boundary is accepted.

**C. Per-criterion proof (all nine existing Sail dimensions, but only selected request fields constrain).** For each active `CriterionDefinition`: explicit current publisher `VALUE_ASSERTION`; matching exact static type + canonical allowed enum or typed finite Decimal and its declared **internal unit** (draft/LOA/beam meters; other accepted values exact enum tokens); attribution to same current publishing Organization, revision, actor and time; applicability to a SAIL PhysicalBoat; non-retracted within current public freshness; no conflicting other-current-Organization positive claim. An implied or source-document-only unit is not enough; where accepted typed storage already fixes the unit, reuse it, don't invent a parallel free-text unit. Conditions/operating points are **not** among the existing nine Sail constraints, thus basis comparisons are `NOT_APPLICABLE` here rather than secretly “passed”. The existing `CriterionDefinition.read_claim`, shared concrete qualification and `evaluate_configuration` MUST/AND truth kernel are mandatory; do **not** add a second ad hoc per-field comparator. More than one selected criterion means **all** selected criteria must pass on the *same current PhysicalBoat and coherent publisher revision*, never a cross-vessel/Org mix.

**D. Source/evidence and result semantics.** The new design-unresolved evidence shape must retain typed `source_basis=PUBLISHER_CLAIM`, category basis and bounded reason, claiming publisher identity/source reference and current claim revision/time for authorized internal/audit views; public DTO/SSR may disclose only safe publisher/source-type and the fact is **publisher-stated, not independently design verified** (never another Organization's private identifiers/account or private raw provenance). Do not fabricate `boat_design_id`, `DesignQueryEvaluation`, `NamedVariant`, `DESIGN_CONFIRMED` or run the design-level evaluator on fictional design facts. A new clearly discriminated claim-only branch/union DTO is safer than stuffing fake “design” fields into existing required types. Exact buyer/search-fit serialization must preserve machine-readable `CONFIRMED_MATCH` meaning *matches the requested condition on qualified publisher claims* while clearly conveying *source certainty differs* from accepted design-confirmed results. Existing design-linked matches must retain their original evidence.

**E. One coherent snapshot / false-positive prevention.** Either evaluate the publisher/other-current-Org claim values, revision and category from **one coherent PostgreSQL statement** for each PhysicalBoat, or own an explicitly `REPEATABLE READ` transaction **before any search read**, including prior listing eligibility/design reads. An already-running `READ COMMITTED` connection must never allow combining earlier category with newer conflicting numeric fields for a falsely confirmed result. D29 must be independently re-evaluated at the accepted `as_of`; an eligibility failure always overrides Search fact confirmation.

**F. All accepted Sail entrypoints / visible results.** Wire this optional additive path through (i) **pure `draft_max`** `evaluate_draft_max_requirement` (SLICE-0051), (ii) mixed `evaluate_native_inventory_requirements` (nine accepted dimensions), (iii) `search_read.evaluate_requirement_search_outcome` and Buyer sensitivity use, and (iv) FastAPI public Search + five-locale Astro browser read/SSR, as needed to avoid invisible/misleading matches. Preserve already-qualified design-linked outputs *byte/field-compatible where possible*; add explicit source-basis discrimination for new matches, no unqualified “verified yacht” prose. The SLICE-0084 broker Search-fit **still only previews a DRAFT linked-design listing**; extending it to design-unresolved DRAFT/Power (and its matching product decision) remains a separate Owner-selected task rather than being incorrectly implied by this active-public candidate path. If existing Buyer sensitivity cannot faithfully compare the new result subset, make its limitation explicit and nonmisleading rather than silently dropping constraints.

## Explicitly out of scope

- NO Power technical `CriterionDefinition`, numeric/conditional fields, engine/propulsion/range model, Power Buyer Search or Broker Power Search-fit. The category-neutral candidate enumerator does **not** make POWER technical Search done.
- NO automatic qualification of OWNER_DIRECT listings or unverified private seller statements without a separate reviewed source/trust scope. The inherited D29 behavior remains; do not infer a professional status from a client-provided string.
- NO expansion of 0091 `HULLQ_CATALOG_ADMISSION_SECRET` into generic rights clearance. This secret gates design-category writes, not concrete publisher evidence quality.
- NO NautiX import/export Sail/Power changes, spreadsheet formats, new external source feeds, scraping, paid provider acquisition or rights bypass.
- NO real broker datasets, pilot, early external Sail-only/C-light product, public launch, new real provider wiring or production-operations phase.
- NO new dynamic user-authored Search criterion schemas, ranking/scores, marketing truth badges, named model inference, global generic FieldResolution rewrite or weakening existing design-linked FieldResolution gates.
- NO modifications to Owner's `START_SLICE.bat`, `FINISH_SLICE.bat`, ignored `LOCAL_TEST_HULLQ.bat` or locally held environment/credentials.

## Deliverables / expected touchpoints

1. Additive persistence DTO and **new separate** design-unresolved ACTIVE candidate reader in `src/hullq/persistence/inventory_search.py`; unchanged existing design-linked reader proven by exact SQL/test diff.
2. Narrow shared criterion-qualified publisher-claim evaluation pathway in `src/hullq/application/native_inventory_query.py` / existing `criteria_registry.py` and `configuration_engine.py` (reuse, **not duplicate**) plus 0091 category snapshot integration; only add a migration if a genuinely mandatory source qualification cannot be safely retained using already-durable publisher revision metadata.
3. Additive outcome/evidence shapes so claim-only and design-linked results are discriminable without fictional BoatDesign provenance. `src/hullq/application/inventory_search.py` pure draft branch, `search_read.py` common dispatch, public FastAPI serializer and impacted five-locale Astro Search rendering; Buyer sensitivity parity or explicit truthful limitation. No new Search filter URL keys.
4. Executable unit and PostgreSQL18 integration/regression tests, synthetic authenticated FastAPI/SSR inspector and compact retained evidence table documenting threshold decisions per each of nine existing criteria; scenarios from synthetic SLICE-0090 corpus (FIX-0090-08,09,11,13 plus 01 as design-linked control, adapted only as far as this field set actually supports).
5. Documentation of internally admitted SAIL and *not yet technically searchable* POWER/MOTORSAILER cases, source rights/status, and exact untouched future obligations #372/#355.

## Acceptance criteria

- [ ] Existing design-linked SQL and accepted nine-dimension results are unchanged; compare the same legacy fixtures before/after, including UNKNOWN category, all D29/freshness, unsupported values and cross-Organization conflicts.
- [ ] Separate, bounded ACTIVE `BoatDesignRef IS NULL` candidate enumeration proves strict design-null isolation and no DRAFT/WITHDRAWN/foreign/broken-chain promotion, with pagination/size consideration and no N+1 explosion silently introduced.
- [ ] Real PostgreSQL18 synthetic listing with **no BoatDesignRef** and explicit nonconflicted SAIL category qualifies on known current authorized typed broker assertions for *pure draft_max*, at least one categorical and at least one multi-criterion AND scenario using the accepted kernel; public API returns this listing with `source_basis=PUBLISHER_CLAIM`, **no** `DesignQueryEvaluation`.
- [ ] Per-field threshold proof for each currently selectable Sail dimension: only current publisher `VALUE_ASSERTION` with matching typed unit/vocabulary/applicability, revision/issuer/time, current D29/freshness, current cross-Org nonconflict; source uncertainty never upgraded to independent verification. Missing/UNKNOWN/wrong unit/unsupported other known token/issuer/retraction produces nonconfirmed reason. No new public dimension count.
- [ ] New design-unresolved POWER/MOTORSAILER/UNKNOWN/CONFLICT candidates never produce confirmed Sail matches; **publisher missing/UNKNOWN category with only a different Organization asserting SAIL** is explicitly nonconfirmed; design-linked legacy UNKNOWN categories keep their accepted 0091 result sets. No inaccurate assumption that motorsailer equals Sail without future review.
- [ ] Claim revision/retraction, stale contributor, D29 suppression, authorization/cross-tenant, two-connection concurrent category+criterion write, and degraded DB error all have deterministic fail-closed tests (not result-empty-as-success or false match).
- [ ] Exact public API and built Astro SSR provide meaningful, escaped publisher-source explanation in **all five existing locales**, with preserved listing identity/freshness/discovery attribution and normal buyer contact path. No competitor publisher identity leaked in evidence. New claim-only results do not get fabricated design/generation evidence.
- [ ] Buyer search dispatch, old-only sensitivity, Shortlist/Compare downstream consumption and unrelated accepted broker DRAFT Search-fit remain non-regressed. Any unsupported claimant-only sensitivity case is visibly restricted; no partly applied constraint silently produces a confident result.
- [ ] Existing safe-bound Candidate/SQL indexes and performance validated with deterministic representative synthetic populations; no unbounded duplicate or N+1 cross-vessel provenance query introduced without an explicit independently reviewed sizing justification.
- [ ] Current `docs/governance/POST_0051_TRIGGER_GATES.md` technical dimension count remains **9**; same `CriterionDefinition`/MUST-AND semantics, commercial Search neutrality and truth/provenance separation proven by unit + real PG tests.
- [ ] `uv run python scripts/validate_repository.py`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src`, full relevant unit/PG/FastAPI/web tests pass; then exact-HEAD independent review, **six-job GitHub CI** and manufacturer reproducibility pass before explicit Owner acceptance.
- [ ] Production Readiness remains `IN_PROGRESS`, Launch Pack `NOT_STARTED`, production data `NOT_PRESENT`, no external real brokers/products/pilot; Power Search, Power sources and imported Power files not silently enabled.

## Stop conditions / review expectations

- A `CONFIRMED_MATCH` requires inventing a BoatDesignRef, using an unqualified self-asserted field, ignoring field-specific unit/revision/provenance, or weakening original `CriterionDefinition` evidence → **STOP, BLOCKED**.
- A Category `UNKNOWN`/`CONFLICT` or unqualified `POWER`/`MOTORSAILER` becomes a Sail positive, or legacy Sail results disappear → **STOP, BLOCKED**.
- The required source/issuer/rights threshold cannot be established from current broker-claim facts without a distinct Owner/legal/verification decision → **STOP and report exact gap**; do not invent a generic entitlement or hardcode fictitious third-party source rights.
- Shared kernel reuse would require a second competing Search scorer, unbounded query expansion or a fake design identity → **STOP and seek a bounded independently reviewed amendment**.
- No real external broker data or provider installation is permitted. External tests/gates remain unverified until actually run. No owner-local setup workflow change.

## Sequence and Owner workflow

1. Readiness **only**: independent exact-HEAD review, required remote CI/manufacturer reproduction and merge docs-only READY PR into `main`.
2. Owner executes the **unchanged** `START_SLICE.bat` and selects `0092`. **No START output submission is required**; continue established Owner/Claude handoff.
3. Claude implements exclusively on generated `slice/0092-...` branch, commits/pushes, returns `REVIEW` with exact SHA and actually executed proof. No automatic DONE/merge.
4. Independent exact-HEAD review; amendments on same implementation branch; full CI/manufacturer; explicit Owner acceptance before implementation merge.
5. Separate docs-only acceptance closure PR with independent exact-HEAD remote gates/merge; then Owner runs unchanged local `FINISH_SLICE.bat 0092`.
6. No successor slice auto-selected. Power criterion, Power category import/export, source-rights and runtime #355 remain separately tracked.

## Required completion report

Use mandatory `docs/slices/SLICE_TEMPLATE.md` fields: Slice, Product execution checks, Changes, Validation, External verification, Findings/deviations, Follow-up, Agent declaration. Distinguish locally executed evidence from remote gates and genuine public feature availability.
