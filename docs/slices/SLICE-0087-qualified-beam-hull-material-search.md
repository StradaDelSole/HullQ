# SLICE-0087 — Qualified Beam & Hull-Material Buyer Search

**ID:** SLICE-0087  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Readiness authority:** NOT OPERATIVE until independent exact-HEAD docs-only READY review ACCEPT, authoritative CI + manufacturer reproducibility SUCCESS, and readiness PR merged into `origin/main`. Owner's `START_SLICE.bat 0087` remains required thereafter.  
**Risk:** HIGH_RISK — authoritative yacht dimensions/material claims, immutable publisher revision writes, FieldResolution/NamedVariant design applicability, cross-Organization conflicts, public hard Search and authorized private DRAFT preview.  
**Stage:** Owner-selected post-0086 qualified technical Search expansion.  
**Previous accepted:** SLICE-0086 Owner accepted, remote closure PR #350 merged and local `FINISH_SLICE.bat 0086` confirmed by Owner.  
**Owner selection:** 2026-10-15: explicitly confirmed a **bounded Beam + Hull Material** Buyer Search bundle with same-criterion Broker Search-fit; no 0088 capability preselected.  
**Governing reconciliation:** `docs/POST_SLICE_0086_BEAM_HULL_MATERIAL_REASSESSMENT_2026-10-15.md`.  
**Canonical baseline:** `29357e421a6eece3b5d9f224ea2efc5b9f642806`; seven accepted native public hard technical dimensions.

## Mandatory readiness checks

**ONE-CAPABILITY CHECK:** PASS  
**ONE USER WORKFLOW:** A buyer combines an independently confirmed actual boat's **maximum/minimum overall beam** and **hull construction material** with existing seven hard technical requirements; the broker explicitly edits/reopens the same physical boat claims and privately previews representative synthetic requirements before publication. One complete two-filter expansion of the existing Search workflow, not an unrelated authoring system or parallel matching kernel.

**VISIBLE-RESULT CHECK:** PASS  
On a synthetic test marketplace backed by real PostgreSQL 18, the buyer can select `beam_min=3.2&beam_max=4.4&hull_material=GRP_FIBERGLASS`, optionally conjunction with any previously supported filters, see only D29-current/public offers that independently satisfy both **the same qualified design/configuration** and **the actual offered boat's current non-conflicting publisher claim**, and inspect per-field design-versus-offer evidence and UNKNOWN reasons in EN/DE/FR/PT/ES. An authorized broker saves explicit beam/material VALUE_ASSERTION or UNKNOWN claims on an owned promoted lifecycle-DRAFT listing, reopens them, and views one illustrative read-only Search-fit verdict with no listing/publication mutation or fabricated real buyer demand.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
After accepted 0085/0086, the Owner's technical Buyer Search breadth priority remains active; bundling two comparable low-taxonomy dimensions avoids one-filter micro-slices. Existing `docs/PRODUCT_UX_PRINCIPLES.md` controls public UI; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md` and mixed-supply/owner-direct direction control seller/launch boundaries. No production provider pilot, real inventory, buyer saved search, paid ranking or owner-direct publishing added.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Post-0086 design schema v0.5/v0.6 and marketplace registry already model beam/material, but live `PhysicalBoatClaimSnapshot`, immutable revision persistence, broker editor and `CriterionDefinition` registry do not implement their current concrete facts or hard queries. Reuse one accepted static registry, numeric/categorical FieldProjectionSpec bridge, one configuration query, one PhysicalBoat observation/classifier and the existing buyer and private broker presentation paths. The separate governing reconciliation names artifacts and implementation evidence.

**TRIGGER GATES CHECK:** PASS  
Canonical Gate 1 architecture `PASS`; Gate 2 production readiness `IN_PROGRESS` but not triggered by strictly local synthetic test data; Gate 3 existing criterion count **7**, and Gate 4 workflow `PASS`. First new Search ordinal is **8**, second is **9**; `COMMON STRUCTURE GENERALIZED / REUSED` applies: existing LOA numeric range/draft+keel categorical infrastructure and typed shared Search registry are extended, no separate third bridge or direct raw-data-to-confirmed-match path. Accepted count MUST remain **7** until 0087 Owner-accepted implementation and separate formal closure.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
`MVP-BUY-001` stays IMPLEMENTED/PARTIAL (scope grows only when accepted); `MVP-BUY-002` stays PARTIAL; `MVP-BROKER-010` is already IMPLEMENTED and gains two future preview criteria. Broker portability/export `MVP-BROKER-009`, periodic engagement reporting `MVP-BROKER-008`, buyer Saved Search/alerts, account persistence, owner-direct trust/publication, support/admin/privacy/legal/comms, production host and database HA remain open at their existing gates. None is newly DUE merely because 0087 is selected. Real externally visible inventory still requires Production Readiness PASS and sequential Launch Pack evidence; no go-live is implied.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS  
Risk classification and executable adversarial model are detailed below. This is a single coherent vertical across claim writer/read, Search and browser/preview surfaces; no independently marketable subsystem is packed into this slice.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`, `docs/PRODUCT_EXECUTION_PLAN.md`, `docs/POST_SLICE_0083_SEARCH_PRIORITY_REASSESSMENT_2026-10-13.md`, post-0084/0085 Search decisions, SLICE-0085 and 0086 accepted readiness/closure, `docs/POST_SLICE_0086_BEAM_HULL_MATERIAL_REASSESSMENT_2026-10-15.md`, `docs/PRODUCT_UX_PRINCIPLES.md`, `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`, `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`, `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`, `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`, `docs/governance/POST_0051_TRIGGER_GATES.md`, `docs/governance/PRODUCTION_READINESS_GATE.md`, `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`, `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`, `docs/operations/PRODUCTION_LAUNCH_PACK.md`, `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`, `specs/BOAT_DESIGN_SCHEMA.v0.5.json`/`v0.6.json`, `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` and `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`.

**Production implementation checked:** `src/hullq/search/criteria_registry.py`, `src/hullq/search/boat_design_field_bridge.py`, `src/hullq/search/loa_design_bridge.py`, `src/hullq/application/native_inventory_query.py`, `src/hullq/domain/physical_boat_claims.py`, `src/hullq/domain/inventory_edit_request.py`, `src/hullq/persistence/physical_boat_claims.py`, `alembic/versions/b2c6f94a0d31_sailing_vessel_hull_cockpit_deck_claims.py`, `tests/unit/test_criteria_registry_parity.py`, and the accepted SLICE-0086 two-sided retained PG18/FastAPI/built Astro SSR proof. Existing buyer Search/authorized broker editor and Search-fit are extension points, not new workflows.

**Already implemented / not re-decided:** Seven independent technical Search dimensions; finite criterion/key whitelist; v0.5/v0.6 FieldResolution/NamedVariant current snapshot agreement, MUST/AND on the same applicable configuration, current publisher PhysicalBoat fact required independently, cross-Organization conflict nonconfirmation, D29 public eligibility, current authenticated MFA/PUBLISHER owner-only DRAFT Search-fit, canonical EN/DE/FR/PT/ES queries, existing draft/keel-only sensitivity and no paid search advantage.

**Exact remaining gap:** Two end-to-end filters and optional current concrete publisher facts: overall beam min/max in metres, and exactly the four confidently cross-mapped positive hull materials below, including canonical URL parsing, persistent physical publisher claim authoring, public qualifying results and private Broker Search-fit. No search criterion may count until the entire evidence chain is demonstrated.

**Accepted-but-unimplemented obligations:** Unselected additional technical criteria (displacement/basis, rig, material subtypes, `LONG_KEEL` taxonomy), saved/monitored Buyer Search, broker inventory export and periodic reporting at paid/broad-public gate, safe owner-direct publication, trust/privacy/legal/support/admin, production e-mail and provider/HA/launch pack. The present slice neither discharges nor supersedes them.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` = seven hard Search dimensions/common truth engine; `DECIDED_NOT_YET_IMPLEMENTED` = runtime beam/material concrete claim+filter chain; `EXPLICITLY_DEFERRED` = unsupported composite/wood/carbon/ferrocement material filter in this bounded bundle and all launch work; `GENUINELY_OPEN` = future independently evidenced material aliases and next slice prioritization; `CONFLICT_OR_REGRESSION` = no detected code regression, but current-state text about 0086 FINISH was stale and corrected in this readiness PR.

## Normative public request and source contract

### Beam — numeric range, one new semantic dimension (#8)

- Public raw keys `beam_min` and `beam_max` (lexicographically canonicalized using existing backend rules), each optional; individually usable or combined, **inclusive** SI metres, positive finite exact `Decimal`. Adopt existing `loa` strict lexical, precision, duplicate-key, bound and canonical-redirect policy rather than invent a separate numeric grammar. Equal minimum and maximum means exact equality; inverted range is INVALID, not zero hits. Zero, negative, NaN, infinity, exponent, overprecision, duplicate/conflicting or oversized values obey fail-closed existing numeric-parameter policy. Both public keys count as ONE technical dimension.
- Design/NamedVariant v0.5 and v0.6 source is `/baseline/dimensions/beam_m` and `/overrides/dimensions/beam_m` where the named variant actually supports that override and qualification; no inferred beam from `beam_waterline_m`, advertised width or a related design. `FieldResolution` qualification and applicability unchanged. Same configuration must satisfy both bounds and all other active MUSTs; NEVER splice beam from variant A and hull material from variant B.
- Concrete claim `physical_boat.beam` is optional: omitted is not explicit `UNKNOWN`; `VALUE_ASSERTION` must hold validated finite positive exact Decimal metres; explicit `UNKNOWN` stores no number; no `ABSENT` assertion. Independently qualified current per-Organization claim must confirm range membership before any public match. Do not copy BoatDesign or imported feed dimensions into current physical claim.
- Browser label must unambiguously mean **overall beam / maximale Bootsbreite**, not beam at waterline, width at berth with fenders, or approximate berth dimensions. Use existing UI and locale unit display conventions.

### Hull material — categorical positive, one new semantic dimension (#9)

The accepted existing marketplace registry has a **broader actual-boat claim vocabulary** than the bounded qualified v0.5/v0.6 BoatDesign baseline. Do NOT rewrite that accepted registry vocabulary. Add the missing runtime claim implementation for the full existing physical vocabulary, but permit only these four **public positive hard-filter tokens** where design/actual meanings directly align:

| BoatDesign v0.5/v0.6 `construction.hull_material` | Public `hull_material` | Actual PhysicalBoat VALUE_ASSERTION |
|---|---|---|
| `grp_fiberglass` | `GRP_FIBERGLASS` | `GRP_FIBERGLASS` |
| `steel` | `STEEL` | `STEEL` |
| `aluminium` | `ALUMINUM` | `ALUMINUM` |
| `wood` | `WOOD` | `WOOD` |

- Existing registry actual-claim tokens `FERROCEMENT`, `CARBON_COMPOSITE`, `OTHER` remain valid positive *concrete declarations* but are **not** public hard-filter values in 0087. `wood_composite` is NOT the same as `wood`; v0.5/v0.6 `carbon` is not silently treated as the more specific current `CARBON_COMPOSITE`; design `other`/`unknown` and absent construction facts do not confirm a positive material. Multiple construction layers/hybrid material cannot be forced into one category from marketing names.
- Public `hull_material` takes exactly one of these four supported canonical ASCII tokens or is absent. Unsupported/duplicate values => existing 400/canonical validation semantics, **not** silently ignored or a filtered-zero result. Existing public Search remains neutral when this criterion is absent. No free-text type search, OR groups, material preference/ranking, inferred vessel category or conversion from `hull_configuration`.
- Physical `physical_boat.hull_material`: optional, `VALUE_ASSERTION` exact registry enum; explicit `UNKNOWN` with null; entire wrapper omitted distinct; no `ABSENT` kind. The current publisher writes through the authorized append-only PhysicalBoat revision/head boundary; competing Organization current claims may make the value non-confirmed. Source rights/import tags stay as unverified allegations until a separate qualified action provides an independently asserted physical fact.
- Same BoatDesign v0.5/v0.6 construction baseline and safely applicable NamedVariant construction override (only where permitted by schema) participate under the existing `FieldProjectionSpec` bridge. The same physical listing must independently confirm the selected material; design alone is insufficient. Show `UNKNOWN` or truthful typed non-match, never a soft score.

## Shared implementation requirements

1. Extend `src/hullq/domain/physical_boat_claims.py` and the bounded current PhysicalBoat snapshot with exactly two optional typed claim wrappers. Extend authorized `src/hullq/domain/inventory_edit_request.py` parser/serialization, existing broker inventory editor forms and immutable `src/hullq/persistence/physical_boat_claims.py` revision/head/current observation. A narrowly scoped Alembic schema migration is permitted for these two persisted optional assertions; historical revisions, legacy bytes and exact idempotency semantics must survive. Existing unrelated claims must not change or become retroactively UNKNOWN.
2. Reuse existing `src/hullq/search/criteria_registry.py` static typed definitions, `boat_design_field_bridge.py` source-qualification and same-configuration aggregation. Criterion-specific beam and material mapping adapters may be thin; **no** alternate query evaluator, direct importer-tag assertion, separate material search engine, third full resolver or unbounded generic all-fields schema introspection.
3. Extend existing public Search request parsing, typed API, actual canonical ordering/identity, buyer SSR controls/translated labels/reason/evidence and read-only private broker Search-fit from **the same** two new definitions. New filters may be active individually and with any subset of the previously seven accepted hard dimensions. No requirement drops silently from canonical links, request builders, metadata, shortlist/Compare, source-qualified explanation or broker preview.
4. Broker authenticated `PUBLISHER` with current Organization access and MFA may edit the actual current PhysicalBoat beam/material claims on an owned promoted lifecycle-DRAFT or otherwise authorized existing inventory as current editor policy permits. Save/reopen durable immutable revisions/heads with existing optimistic concurrency, revocation and idempotency; display true UNKNOWN/omission distinctly. Illustrative DRAFT Search-fit causes ZERO writes and never claims actual buyer traffic. Never leak foreign Organization/private inventory.
5. Keep legacy buyer sensitivity for supported draft/keel-only constraints; when **beam or hull material** participates, do not silently drop active hard requirements to compute an invalid legacy sensitivity: show unavailable or reject by existing truthful contract. Preserve new-first-level structure search and all existing current-public/non-indexed browser behavior.
6. All five locales EN/DE/FR/PT/ES: accessible form labels/keyboard, correct units, selected value persistence/canonical link, per-criterion applied result and qualified BoatDesign-versus-offered-PhysicalBoat evidence. Do not implement unrestricted empty-query browse or paid boost.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** YES  
**Technical Search criterion ordinal:** 8  
**Second-criterion bridge comparison:** PASS  
**Third-copy abstraction guard:** PASS  
**Workflow reassessment status:** PASS  

**Gate 3 finding:** `COMMON STRUCTURE GENERALIZED / REUSED`; seven accepted dimensions stay authoritative throughout implementation. Two additional dimensions (beam numeric range as #8; material as #9) can raise count to **9** ONLY in post-Owner-acceptance independent formal closure. Private Search-fit mirroring never counts separately. `LONG_KEEL` does not become enabled in this slice.

## Production phase transition check

**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  
**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  

Only synthetic/disposable local and CI test data. Canonical Launch Pack stays `NOT_STARTED`, Production Readiness stays `IN_PROGRESS`. No provider spend, real external broker/owner/customer data, pilot, public production exposure, automatic database HA provisioning or paid activation authorized.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** Beam and construction material are buyer-critical technical facts; failure can create false positive matches, cross-Organization leaks or destructive revisions. Search request parsing, current PhysicalBoat immutable revision storage, generation-aware BoatDesign FieldResolution and authenticated DRAFT preview are trust, persistence and concurrency boundaries.  
**Must-never-change invariant:** For each selected beam/material hard leaf AND every prior active criterion, the **same** qualified applicable BoatDesign/NamedVariant configuration and independently asserted current nonconflicting actual PhysicalBoat claim both confirm it before a D29-current-public listing receives CONFIRMED_MATCH. UNKNOWN, stale source, paid interest, conflicting current publisher state, DRAFT state or inferred import fields NEVER satisfy a hard leaf.  
**Durable source of truth / loss boundary:** PostgreSQL versioned canonical BoatDesign/NamedVariant + FieldResolutions and immutable per-Organization PhysicalBoat claim revisions/heads, NativeListing/MarketEpisode/current D29 state. Client inputs, SSR caches, imports and a lost process/worktree do not establish durable technical truth. Failed writes never replace a current head nor mint partial positive claims.  
**Retry / replay / partial-failure behavior:** Previous revision/request envelope and old exact retries remain equivalent after additive fields/migration; omitted optional fields are not silently serialized as explicit UNKNOWN, UNKNOWN is not a value, concurrent authorized writes retain optimistic/version/head rejection, and rejected authorization or data errors have zero writer-side effects. Duplicate/invalid public requests cannot silently become weaker filtered requests. Preview is read-only across retries, snapshot-consistent under existing broker transaction/reauthorization logic.  
**Absence-vs-error / fail-closed behavior:** Missing/unqualified/mismatched design value, variant conflict, unsupported composite taxonomy, missing/stale/UNKNOWN/concurrent other-Org concrete claims => typed insufficient/contradicted evidence, never confirmed result. Unsupported positive public material/invalid beam range => typed 400; backend/DB/auth/access/rights error => appropriate 401/403/404/409/503 as established, NOT valid zero matches or invented data. Confirmed material `OTHER` is known different, not missing; explicit UNKNOWN distinct from omitted.  
**Executable adversarial proof:** Before first implementation REVIEW, real disposable PostgreSQL 18 + FastAPI + **built Astro SSR** verifies each new stand-alone filter (all four material choices), beam min/max inclusive/equal/inverted, all accepted old+new MUST mixing and no cross-variant pick-and-mix, qualified v0.5/v0.6 design and NamedVariant source/pointer state, material `wood_composite`/carbon/other negative, current physical claim omitted/UNKNOWN/other/competitor contradiction, older bytes and idempotent retry, publisher MFA/ownership/revocation and concurrent writes, independent actual boat editing/reopen and no preview writes, D29/DRAFT and five locales/canonical 308/invalid 400, sensitivity safe suppression, full old Search/shortlist/lead provenance regression. Real test execution required; a script not run or SSR not built is NOT passing proof.  
**Slice sizing assessment:** COHERENT  

## Why this slice exists

The Owner expressly chose incremental but bundled buyer-visible technical breadth after 0086. HullQ's current Search can qualify form/rig-adjacent characteristics and LOA but cannot yet answer real berth-width or basic hull-material constraints. Both design-generation schemas and the already accepted marketplace field registry model the underlying meanings, and 0085's typed shared registry can carry the additional two leaves. This bundle has one user experience, one shared claim writer/reader + query evaluation, one release acceptance gate; unrelated displacement-basis and rig vocabulary issues remain separated.

## Controlling artifacts

- `docs/POST_SLICE_0086_BEAM_HULL_MATERIAL_REASSESSMENT_2026-10-15.md`; `docs/PRODUCT_UX_PRINCIPLES.md`; `docs/PRODUCT_EXECUTION_PLAN.md`.
- `specs/BOAT_DESIGN_SCHEMA.v0.5.json`, `specs/BOAT_DESIGN_SCHEMA.v0.6.json`, `docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md`, `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`, `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`, `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`.
- `docs/governance/POST_0051_TRIGGER_GATES.md`, `docs/governance/PRODUCTION_READINESS_GATE.md`, `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`, `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`, and applicable retained 0085/0086 closure evidence.
- Source/test seams: `src/hullq/search/{criteria_registry,boat_design_field_bridge,loa_design_bridge}.py`, `src/hullq/application/{native_inventory_query,search_read,broker_search_fit}.py`, `src/hullq/domain/{physical_boat_claims,inventory_edit_request}.py`, `src/hullq/persistence/physical_boat_claims.py`, `src/hullq/api/app.py`, `web/src/components/SearchPageBody.astro`, `web/src/lib/{searchApi,searchPageData,searchText,brokerSearchFitApi}.ts`, `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro`, `tests/unit/test_criteria_registry_parity.py`, `scripts/inspect_slice_0086_technical_search.py`. New narrowly scoped tests and inspector may be added; reuse rather than duplicate old orchestration.

## In scope

- Actual two optional PhysicalBoat publisher claim definitions (runtime, immutable persistence, read, authorized broker edit).
- Public native Buyer Search beam range (one dimension) + categorical positive hull material (one), including mixed current seven requirements, canonical URL, locales, qualified evidence/negative states and SSR.
- Mirrored private illustrative broker Search-fit for owned promoted lifecycle-DRAFT.
- Targeted migration and proofs necessary for those exact behaviors, regression of accepted past Search and rights/truth invariants.

## Explicitly out of scope

- Displacement/basis, rig, broader material subdivisions or invented synonyms, long/full keel, derived ratios, new search ranking, PREFER/OR, recommendations, Saved Search/alert persistence, price/paid features, production provisioning/pilot/launch, new import adapters or unbounded Search rearchitecture.
- Automatic conversion of broker website claims, imported tags, BoatDesign facts, advertising copy or images into current physical facts.
- Owner-direct public admission and trust, business/account/contact pipeline changes, mass reclassification of historical records.

## Deliverables

- Updated marketplace-contract consumers and concrete PhysicalBoat types/request, immutable revision persistence/migration and authorized broker form/readback.
- Two additional finite `CriterionDefinition`s with exact qualified design/variant/concrete evaluation; public parsing/links/SSR and private Broker Search-fit parity.
- Focused unit and real PG18/FastAPI/built Astro SSR negative+positive tests, retained proof script, all five-locale parity, final implementer self-review, full exact-HEAD remote quality/manufacturer gates.

## Acceptance criteria

- [ ] Public beam_min and beam_max separately and combined apply inclusive exact SI Decimal range (one dimension), fail on invalid/duplicate/inverted request; per-criterion actual vs design evidence truthful.
- [ ] Public hull material admits exactly GRP_FIBERGLASS/STEEL/ALUMINUM/WOOD and rejects all other positive search tokens; legacy actual material assertion vocabulary preserved without guessed mappings.
- [ ] Each new facet independently requires qualified v0.5/v0.6 design/variant and separately current actual publisher claim on identical configuration; missing/conflicting/other/UNKNOWN NEVER confirmed; no DRAFT/current-public D29 bypass.
- [ ] Publisher-authorized actual claims persist/reopen through immutable revision/head with omission distinct from UNKNOWN, historical retries stable; cross-Organization, MFA/role, concurrency and error failures tested with zero leak/write.
- [ ] Buyer search combinations with all existing seven, broker Search-fit zero-write behavior, existing sensitivity truthful suppression, native listing/shortlist/compare/lead-provenance nonregression.
- [ ] Browser controls, translated errors/evidence, correct units and canonical URLs in EN/DE/FR/PT/ES; actual rendered built Astro SSR inspected against real FastAPI/PG.
- [ ] Exact tested implementation final HEAD: focused and full required suites, Ruff/mypy, web type/build/tests, migration/retained adversarial proof and authoritative CI/manufacturer reproducibility; independently reviewed with all material findings closed before Owner acceptance.

## Expected touch points

Likely: two new thin `src/hullq/search/*_design_bridge.py` adapters if existing shared FieldProjectionSpec cannot express them directly; `criteria_registry.py`; current claim types/persistence, `inventory_edit_request.py`, Alembic additive revision, public `search_read.py`/API, broker Search-fit/client/editor, `SearchPageBody.astro` and language messages, targeted unit/contract/persistence/web tests and bounded two-sided inspector. Preserve source APIs outside this vertical.

## Validation

```bash
uv run ruff check src/hullq/search src/hullq/domain/physical_boat_claims.py src/hullq/domain/inventory_edit_request.py
uv run ruff format --check src/hullq/search src/hullq/domain/physical_boat_claims.py src/hullq/domain/inventory_edit_request.py
uv run python -m pytest tests/unit/test_criteria_registry_parity.py -q
# Implementer: add changed-domain-focused unit/DB tests; use existing local disposable PG18 harness.
# At final candidate: full remote CI/manufacturer reproducibility on exact pushed implementation HEAD.
# Built Astro SSR + real disposable PG18/FastAPI two-sided new-filter inspector must be actually executed.
```

## Stop conditions

Stop and report if the accepted v0.5/v0.6 material construction pointer/NamedVariant semantics fail independent qualification, if an agreed material cannot be mapped without unsupported taxonomy inference, if older immutable revision or exact-retry compatibility breaks, or if any new field would require unapproved production rights/second Search backend/data truth. Stop on any cross-Organization leak, active publication bypass, unrelated production gate trigger, required extra domain decision or failure to build/run real two-sided inspector. No automatic scope expansion or weaker match semantics.

## Status handoff rule

Claude implementation agent may hand off only `REVIEW` or `BLOCKED`, never self-accept `DONE`. Owner `START_SLICE.bat 0087` requires the separate independently reviewed, remote-validated and merged docs-only READY PR. After implementation, the exact final pushed implementation HEAD requires independent code review, authoritative external CI/repro, explicit Owner acceptance, implementation PR merge and separate acceptance closure; only then local `FINISH_SLICE.bat 0087`. A new 0088 is not thereby automatically selected.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md`'s mandatory one-screen report: exact candidate HEAD, changed files, tested evidence + negative cases, locale/browser/PG proofs, CI not-yet-verified clearly marked until independently observed, open findings/risks, next review action and agent declaration.
