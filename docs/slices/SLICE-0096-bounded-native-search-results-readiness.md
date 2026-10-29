# SLICE-0096 — Measured Bounded Native Technical Search Results (Sail + Power)

**ID:** SLICE-0096  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Readiness authority:** READY ON CANONICAL MAIN — Owner-selected Reassessment #403 merged; exact-HEAD project-master source/contract readiness review and amendments documented in PR #404; complete six-job CI and Manufacturer reproducibility/applicable build checks passed; readiness PR #404 squash-merged as `86370ad76bdfa5cc6e1bca1586e04c4df1746809`. This authorizes **Owner-local START**, not implementation acceptance.  
**Stage:** Search safety/product foundation before M1a buyer cards/navigation/filter expansion  
**Risk:** HIGH_RISK — unbounded query work, public D29 eligibility, immutable current-claim and cross-Organization truth, configuration AND, URL/DTO contracts, result continuation consistency  
**Owner selection:** Explicit Owner 2026-10-29 “akzeptiere - go ahead” selected Option A, correctly bounded and measured technical Sail+Power Search retrieval, as 0096 readiness target; not an implementation approval. Decision captured in Owner-selected [post-0095 Search/M1a reassessment PR #403](https://github.com/StradaDelSole/HullQ/pull/403), already merged before READY #404.  
**Source-checked readiness baseline:** original reviewed `e28b2b7a998694131164d51519fef198b5c3ca3c` (accepted 0095, reviewed #401 / #402), updated through Owner-selected Reassessment #403 `1e66bd7005090ea83e760292e6991b77f53585e0` and final READY #404 merge `86370ad76bdfa5cc6e1bca1586e04c4df1746809`. The implementation agent must read this READY from its START-created branch.  
**Normative READY contract:** `specs/NATIVE_TECHNICAL_SEARCH_BOUNDED_PAGING_CONTRACT.v0.1.md`, reviewed and merged with #404; accepted `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`, Power drive/count and historical Sail contracts remain controlling.  
**Depends on:** SLICE-0095 Owner accepted and actually locally FINISHED (confirmed by Owner evidence posted to #397), Owner-selected #403 Reassessment, #355 public Search-scale known gap, #366 joint Sail+Power release, #372 specialist category rights and current truth.  
**STOPs unchanged:** no real external broker/owner production inventory, no external pilot/public launch, no production provider procurement; `PRODUCTION_READINESS_GATE_STATUS=IN_PROGRESS`, launch pack `NOT_STARTED`.

## Objective / one observable capability

**One Buyer Search job:** For any currently accepted Sail or Power hard technical requirement, return a **correct bounded first search result page with truthful, secure continuation**, rather than reading and evaluating the entire ACTIVE inventory in one unbounded public request. Traversal uses **one global, monotonically increasing NativeListing identity cursor** across the existing disjoint design-linked and claim-only source planes; source-plane switches caused by newly associated designs cannot reintroduce or skip an already traversed identity. **PARTIAL requires advancing cursor** even for zero-match pages; **COMPLETE means boundedly proven exhausted**. A user can traverse remaining results without silently losing valid matches or mistaking incomplete evaluation for a completed no-results search.

The permitted alternative to a fully qualified SQL match read is a finite, keyset-ordered *candidate* scan which reports `PARTIAL` plus continuation whenever unchecked candidates remain, **even when the current page contains zero matches**. No implementation may fake completeness after a raw-candidate `LIMIT`. Only a `COMPLETE` scan may claim no remaining matches. Preserve source distinction (`design-linked` vs `publisher-claim-only`) and all accepted truth/eligibility.

**Visible Owner proof:** Real migrated disposable PostgreSQL18 with synthetic Sail/Power ACTIVE+D29-eligible and negative/UNKNOWN/conflict candidates, actual FastAPI and built Astro SSR. First request displays a bounded, source-qualified match page and explicit `PARTIAL`/continuation. Following all pages yields exactly the same confirmed listing IDs/evidence-classification as an independent reference evaluation on stable fixtures. A sparse fixture with matches only after early nonmatches must never show “no matching boats” before complete traversal. A revoked/withdrawn/non-D29 listing never becomes a leaked confirmed result. No cards, filter expansion or paid feature is added.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS

One vertically coherent capability: public technical Search result retrieval under a provable per-request resource budget. Database candidate retrieval, existing evaluator adaptation, request/result DTO, five-locale SSR continuation, tests and measurement are inseparable parts; no unrelated M1a cards/price filters/owner-direct or import feature is included.

**VISIBLE-RESULT CHECK:** PASS

The Owner can repeatedly open the two existing buyer Search pages in a local built browser (with a documented synthetic fixture and requested criteria), advance pages, see source-qualified results versus incomplete evaluation and compare retained SQL/latency/candidate-count reports. No live data or developer-only assertion is substituted for actual browser behavior.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS

Direct Buyer Search is a product prerequisite before much broader Sail+Power facets and excellent M1a result cards. Broker Excellence stays coequal: the broker Search-fit/private DRAFT evaluation is not exposed or rewritten, and later broker workflow improvements remain #400. No speculative field-registry rewrite or imposed fee policy. Owner has already **explicitly deferred** concrete monetization pricing to broker discovery.

**REPOSITORY RECONCILIATION CHECK:** PASS

Exact current accepted code and 0093/0094 performance proofs compared; see required six evidence lines and versioned contract below.

**TRIGGER GATES CHECK:** PASS

Architecture reconciliation PASS, workflow reassessment PASS, current technical Search count **11** unchanged (Sail 9/Power 2), no new technical criterion/third bridge. Production gate remains IN_PROGRESS; #355 Search scale is partly addressed by this synthetic capability but **NOT declared fully closed** without the remaining external/hosted acceptance evidence.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS

MVP-BUY-001/002 remain PARTIAL at broad product level despite the existing eleven source-qualified hard dimensions, and Search paging is not independently reported as a new technical criterion. Anonymous shortlist/compare already exist and must regress green; buyer contact verification, Saved Search, owner-direct publication/trust, full Power criteria and basic product browsing remain pending. Separate broker mandatory commitments (REQ-BROKER-025/029 evidence aggregation and current Search-fit 026, reports 028) remain intact. No unverified search-volume metrics manufactured.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

See explicit high-risk guards and executable adversarial proof below.

**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE

This is synthetic/internal buyer Search retrieval; no deploy or production-data/launch phase transition.

## Decision / implementation reconciliation

**Accepted records checked:** docs/POST_SLICE_0095_SEARCH_M1A_REASSESSMENT_2026-10-29.md (Owner-selected #403; must be merged before READY), docs/PROJECT_STATE.md, docs/PRODUCT_EXECUTION_PLAN.md, docs/PRODUCT_UX_PRINCIPLES.md, docs/HULLQ_OWNER_DECISION_BROKER_PRODUCTIVITY_EXCELLENCE_2026-10-29.md (#401), docs/HULLQ_OWNER_DECISION_MOTORSAILER_SAIL_DISCOVERY_2026-10-29.md (#402), docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md, docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md, docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md, docs/governance/DOCUMENT_AUTHORITY.md, docs/governance/POST_0051_TRIGGER_GATES.md, docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md, docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md, docs/governance/PRODUCTION_READINESS_GATE.md, specs/SEARCH_QUERY_SEMANTICS.v0.1.md, accepted OQ-018 URL-state/unknown-param/canonical-identity decisions, accepted SLICE-0091/0092/0093/0094/0095 closures, #355/#366/#372/#400.

**Production implementation checked:** src/hullq/persistence/inventory_search.py: both `ACTIVE` source-plane `ORDER BY native_listing_id` queries without `LIMIT`; src/hullq/application/inventory_search.py legacy pure-`draft_max`; src/hullq/application/native_inventory_query.py Sail mixed and publisher claim-only; src/hullq/application/power_inventory_query.py Power single/combined and two candidate planes; src/hullq/application/search_read.py and power_search_read.py request facade; src/hullq/api/app.py Search response serializers and discovery-token link source; web/src/lib/searchApi.ts, powerSearchApi.ts strict validators; web/src/lib/searchPageData.ts, powerSearchPageData.ts SSR; web/src/components/SearchPageBody.astro and PowerSearchPageBody.astro; tests/persistence/test_power_inventory_query_performance_slice_0093.py and test_power_engine_count_performance_slice_0094.py and accepted browser/SSR inspector scripts.

**Already implemented / not re-decided:** Eleven accepted technical facets (Sail nine and Power two) with FieldResolution/NamedVariant and current PhysicalBoat publisher claims, consistent source/other-Organization AND proof, D29 ACTIVE eligibility/freshness and source-labelled listing/lead discovery tokens, existing strict canonical OQ-018 Search URL parser, five locales, 0093/0094 real PG18 0/40/200 synthetic cost test fixtures, private Sail+Power Broker DRAFT Search-fit, anonymous shortlist/compare.

**Exact remaining gap:** **No safely bounded full-traversal public technical Search retrieval with honest partial-vs-complete paging**. Existing ACTIVE candidate enumerators fetch all rows and existing direct Search result arrays/counts are designed around whole-result evaluation, so public requests can accrue large candidate, SQL and response costs; any naive first-N candidate SQL `LIMIT` would produce false completeness/false zero results.

**Accepted-but-unimplemented obligations:** M1a buyer base browse/cards/price-year-location-manufacturer filtering + navigation, full relevant Sail/Power/equipment longlist (314 is nonnormative planning input), Owner-accepted Motorsailer Sail-family admission currently excluded in existing 0091 code (tracking #372), broader Power source/import/export parity, seller-rights/lead safety, all remaining #355 runtime/import/trusted-proxy/connection hardening, #366 joint market release, saved searches/alerts and Owner-direct full public trust path. These do not disappear when 0096 is accepted.

**Material classifications:** DECIDED_AND_IMPLEMENTED = existing qualified Sail/Power search truth/D29 and legacy complete-array APIs; DECIDED_NOT_YET_IMPLEMENTED = public safely bounded Search first page/continuation/evidence-accurate paging and Owner-accepted motorsailer future code; EXPLICITLY_DEFERRED = M1a buyer cards/filters, broader 314 planning waves, production provider/pilot/real data, unapproved broker tariffs, optional referral pricing; GENUINELY_OPEN = concrete proven SQL-batching/preselection versus indexed projection/read-model implementation and measured hosted capacity; CONFLICT_OR_REGRESSION = page `LIMIT` without exhaustive continuation, partial returned as empty COMPLETE, stale D29, source claims promoted to design verification, cross-variant/cross-org matches, broken canonical OQ-018 URLs/invalid-result rejection.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

Gate 3: Count stays 11 = Sail 9 + Power 2. The new continuation parameters are **transport/presentation**, not criteria; existing `CriterionDefinition` registries, search expression/FieldResolution and shared matcher are kept. OQ-018 accepted URL semantics require explicit scoped routing for `page_after` and bounded `page_size`; their addition does not authorize unknown/duplicate criteria keys, unconstrained canonical indexing, price filters or weakening the public query parser. Existing old-only Sail sensitivity behavior stays as accepted; no bypass of active constraints via pagination. Owner-accepted Motorsegler Sail-family direction is **not** a silently implemented admission change here.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE

No provider, deployment or real external market data/pilot. #355 Search-scale pre-pilot STOP, #366 joint release and #372 parity remain OPEN regardless of successful synthetic bounded retrieval; production remains IN_PROGRESS, launch pack NOT_STARTED.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK

**Why this classification:** A bounded public query crosses five locale Search URLs, global inventory enumeration, current D29/current publisher claim/admitted design evidence, cross-Organization contradictions and concurrent listing revision/withdrawal. A wrong page cursor or stale truth can omit genuinely matching boats, leak a withdrawn boat or render UNKNOWN as a match; a sync DB/N+1 path can exhaust bounded hosted resources.

**Must-never-change invariant:** Existing D29 and eleven immutable-evidence technical MUST/AND semantics, source basis and publisher attribution remain unchanged; no unbounded candidate or match-array materialization per public request; no incomplete Search response masquerades as complete/empty; no missed/duplicate confirmed matches on static full traversal; no private DRAFT leak, pay-to-rank, raw external Organization source disclosure or contradictory named variant combining.

**Durable source of truth / loss boundary:** Current PostgreSQL NativeListing lifecycle, MarketEpisode/PhysicalBoat identity, D29 eligible authoritative read, Organization publisher immutable current claim heads, cross-Organization observation and approved BoatDesign generation/NamedVariant FieldResolution remain authoritative. Page cursor and browser query are bounded **transient navigation hints**, never durable eligibility evidence or a stored snapshot of a user's data; restart/expiry cannot change authoritative facts.

**Retry / replay / partial-failure behavior:** Stable-data identical first-page and cursor replay deterministic and read-only; a revised/withdrawn listing in a subsequent request must be freshly validated, even though no immutable whole-session MVCC snapshot is promised. Expired/malformed/wrong-query/wrong-category cursor visibly errors or safely restarts per reviewed semantics; SQL/SSR timeout, cancellation and network failure release work/admission without sending fake COMPLETE page or mutating listing state.

**Absence-vs-error / fail-closed behavior:** No current match on **completed** candidate traversal is legitimately `COMPLETE` with zero matches; zero confirmed matches in a bounded but unfinished scan MUST be `PARTIAL` with honest continuation. Unknown/unqualified claim remains insufficient, not a match; missing D29/withdrawn is ineligible; true SQL/serialization/cursor failure is a typed 4xx/5xx, never converted to a 200 empty result. The public TS client treats malformed 200 page/evidence as a real error.

**Executable adversarial proof:** Real disposable migrated PostgreSQL18 mixed Sail/Power 0/40/200 and relevant larger sparse candidate fixture; statement/EXPLAIN/memory latency profiling; static full reference versus pages exact match-ID, source basis and evidence comparison on Sail pure draft/mixed and Power drive/count/combined; early 0-match PARTIAL then later matches, page sizes 1/20/50 and invalid 0/51, tampered/query-swapped/expired cursor, concurrent claims/withdraw/reconfirm, cross-org and NamedVariant contradictions; fast/slow request cancellation and actual built Astro five-locale browser/API proof; all accepted regressions, exact-HEAD CI/manufacturer and applicable deploy-build safety.

**Slice sizing assessment:** COHERENT

Risk-based vertical: one buyer outcome with inseparable persistence, existing app/API/SSR adaptation and tests; **new M1a cards, generic listing browse, new facets/filters/field-registry refactor** are explicitly excluded. If independent reviewer or measured first-pass baseline shows the bounded correct retrieval cannot fit one coherent slice safely, STOP and Owner-reassess/split before execution; never silently widen scope.

## Controlling artifacts

- [Owner-selected post-0095 Search/M1a reassessment](../POST_SLICE_0095_SEARCH_M1A_REASSESSMENT_2026-10-29.md) / [PR #403](https://github.com/StradaDelSole/HullQ/pull/403) (prerequisite)
- [Versioned proposed bounded Search/paging contract](../../specs/NATIVE_TECHNICAL_SEARCH_BOUNDED_PAGING_CONTRACT.v0.1.md)
- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` and accepted OQ-018 canonical/URL/unknown-key decisions
- `docs/PRODUCT_UX_PRINCIPLES.md`; Owner-direct neutrality; coequal Broker/Buyer strategy
- Accepted SLICE-0091 through 0095 specs/closures, domain/registry/schema, existing PG18 performances
- #355 Search scale and pre-external-data STOP, #366 full joint Sail+Power launch, #372 Motorsailer/Power parity

## Required behavior and implementation boundary

1. **Measure first, choose second.** Retain before/after PG18 `EXPLAIN (ANALYZE, BUFFERS)`, instrumented SQL counts, timing distributions, bounded memory/candidate scan and HTTP/SSR behavior. Evidence must include zero-match and sparse nonmatch case. The prior 0093/0094 figures are historical and must not be called newly measured. Set and verify concrete resource budgets from these measurements.
2. **Bound public candidate evaluation.** Exact work caps and approved keyset/qualified preselection or well-justified snapshot projection. Preserve the existing 0091/0092 legacy candidate-enumeration helper semantics for accepted private/reference consumers; new paged reads may be separate helpers and must not silently change non-public broker diagnostics. A global `fetchall()` across unbounded ACTIVE inventory is prohibited on the new public page path; no hidden unbounded loop filling a page.
3. **Make continuation truthful.** Stable source/ID ordering across disjoint design-linked and claim-only candidate planes; explicit `PARTIAL` while unchecked candidates remain; `COMPLETE` only when proven; page-local counts, no invented global totals. Fully traversed static dataset agrees with accepted unbounded reference matcher for supported Sail and Power inputs.
4. **Preserve canonical/API truth.** Coordinated 400/308 URL request rules, explicit nav-only page params, nonindex/canonical and five locales; validated versioned result DTO, existing discovery tokens/links and per-leaf evidences. Navigation parameters require an active technical requirement, are absent from canonical Search identity, reject duplicates/empty/malformed tokens; if a cursor accompanies noncanonical technical query syntax, fail closed rather than redirecting and silently dropping/misapplying the cursor. A 200 malformed/truncated response must be visibly invalid; do not violate stable public Search semantic URL identity.
5. **Preserve source/security truth under change.** D29 checks, current PhysicalBoat own publisher claim with same-revision/current cross-org observation, qualified NamedVariant, category admission, concurrent withdraw/reconfirm/edit races; no Design-only manufacturing/owner-direct trust bypass.
6. **Retain existing user features.** All accepted old Sail/Power criteria, pure-draft and combined requirements, buyer Shortlist/Compare/Sensitivity, broker private Search-fit, publishing and listing detail/contact links remain regressively correct. No new M1a cards here.
7. **Document nonproduction boundaries.** Search boundedness may reduce #355 CR-05 technical risk but not mark pre-pilot safety/hosted performance COMPLETE without actual external/hosted proof. No CI deploy claims as live deploy.

## Deliverables / expected touchpoints

- Existing `src/hullq/persistence/inventory_search.py` and indexed ACTIVE/D29 candidate pathways **only as evidence dictates**, or separate keyset/batched SQL helper with testable maximum work.
- Existing `src/hullq/application/inventory_search.py`, `native_inventory_query.py`, `power_inventory_query.py`, shared current observation/FieldResolution evaluator; preserve accepted source/evidence. No second truth kernel.
- `src/hullq/application/search_read.py`, `power_search_read.py`, `src/hullq/api/app.py` Search request/result serialization. Existing accepted `BASE`/RESULT/invalid redirect/400 semantics retained where applicable, page representation versioned if necessary.
- `web/src/lib/searchApi.ts`, `powerSearchApi.ts`, `searchPageData.ts`, `powerSearchPageData.ts`, shared `SearchPageBody.astro`, `PowerSearchPageBody.astro` and their tests: minimal visible navigation/state only.
- Retained mixed synthetic benchmark and genuine PG18/API/Astro inspector, with before/after measurements, SQL EXPLAIN and owner-executable fixture/readme.
- No new technical criterion count, broad buyer feature bundle, migrations unless justified by reviewed index/projection and safe backward-compatible schema.

## Acceptance criteria

- [ ] Before/after real PG18 baseline retained, including exact 0/40/200 mixed populations and actual `EXPLAIN (ANALYZE, BUFFERS)`, statement counts, elapsed distributions, candidate and memory budgets. No unproven target-SLA number or fabricated hosted results.
- [ ] For a fixed query/static data, all pages across both source planes collectively match accepted reference evaluator's **every confirmed listing ID**, no duplicates or false positives, with exact source classes and leaf truth; cover Sail pure-draft/mixed and Power drive-only/count-only/combined.
- [ ] Per-request enforceable candidate, statement/query, buffered result, request deadline and PostgreSQL statement-timeout limits; CPU/memory measured and non-preemptible driver/CPU risks reported honestly instead of unproven hard CPU guarantees. Worst-case negative-rich fixture does not trigger unbounded work; after reaching cap return `PARTIAL` with valid continuation even for zero matches, never fake `COMPLETE`.
- [ ] New page request/result contract uses explicit safe `page_after`/`page_size` or an equivalently reviewed scope and version, strict canonical locale and technical query identity, noindex/no duplication, bounded/tamper/expiry/query mismatch validation, all five locales and strict TS response consistency. Must include empty PARTIAL that **advances past examined candidates**, identical final-full-page exhausted state, BASE+cursor invalid, two source-plane ordering and design-link change between pages; strict PARTIAL+next_cursor vs COMPLETE+no_cursor invariants.
- [ ] 1/20/50 page-size variants, invalid 0/51, complete-empty, partial-empty, next-page, final-page and concurrent edit/withdraw/reconfirm are proven on real PG18+FastAPI+built Astro SSR with actual source badges/evidence and correct live-listing links.
- [ ] Concurrent/retracted/cross-Organization observations, category UNKNOWN/CONFLICT/explicit MOTORSAILER current code, wrong publisher, split NamedVariants, stale D29, malformed serializations and cancelled/slow requests fail closed without accidental public data leak or coerced match.
- [ ] No new filter, sorting policy, payment relevance, Motorsegler future admission change, unwanted public DRAFT, Import/NautiX/Export or owner-direct publication. Technical count stays **11**, existing API/buyer and Broker Search-fit tests stay green.
- [ ] Owner gets deterministic synthetic local-browser setup and comparison measurement evidence, not only unit tests; delivered value is a truthful bounded page/continuation, not yet M1a polished cards.
- [ ] `uv run python scripts/validate_repository.py`, Ruff format/check, mypy, all applicable tests, real PostgreSQL18 suite and web/Astro build clean. Exact pushed implementation HEAD full six-job remote CI, Manufacturer reproducibility and applicable Deploy-build verification must pass, followed by an **independent exact-HEAD implementation review**, Owner explicit acceptance, implementation merge, separate reviewed acceptance-closure merge and finally Owner `FINISH_SLICE.bat 0096`.

## Stop conditions / independent-review expectations

Stop at review/implementation if measured architecture cannot meet honest capped retrieval without breaking accepted Search truth, if real paging incorrectly claims complete, if the exact old-vs-new RESULT DTO cannot be migrated safely, if canonical/search query parameters become ambiguous, if publisher/cross-org/variant consistency is weaker, or if post-0095/reassessment is not on canonical main. Any new architecture beyond measured need (materialized projection, migration, generic cross-surface field registry) requires explicit review and bounded implementation justification, not interpretation of this slice as a blanket refactor mandate.

## Owner workflow and required handoff

1. Prerequisite **SATISFIED**: Owner-selected docs-only [post-0095 Reassessment PR #403](https://github.com/StradaDelSole/HullQ/pull/403) reviewed and merged; accepted Option A for 0096.
2. Prerequisite **SATISFIED**: Exact readiness HEAD reviewed (source-based project-master review; no false independent Claude review claim), amended, six-job CI/manufacturer and applicable build checks passed, [PR #404](https://github.com/StradaDelSole/HullQ/pull/404) merged and PROJECT_STATE / INDEX reconciled to Owner-local FINISH 0095 evidence #397 and 0096 READY.
3. **NOW THE NEXT ACTION:** The Owner runs `START_SLICE.bat` in the normal HullQ folder and enters **0096**. The utility itself performs local main sync/validation, creates the isolated worktree and copies Claude's **initial** implementation instruction to the clipboard. Per `docs/engineering/AI_SLICE_WORKFLOW.md`, **the Owner does not routinely send START output or the clipboard prompt to the project master**. Open the new worktree in VS Code, use a fresh Claude Code conversation (or `/clear`), paste the clipboard instruction, and let Claude implement. Only share actual START errors for troubleshooting.
4. Claude implements the one selected slice on its branch and reports actual files, SQL measurement, test commands/output, exact push SHA and PR/CI status. ChatGPT independently reviews exact HEAD, issues amendment instructions only inside active slice until accepted. The Owner must explicitly accept before merge.
5. After implementation merge, independent docs-only acceptance closure and Owner-local `FINISH_SLICE.bat 0096`. No next slice selected automatically; post-slice reassessment first.

**No permission is granted by merely opening this PR to start, deploy, import real external data, change tariffs, select another slice or close #355/#366/#372.**
