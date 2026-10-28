# SLICE-0095 — Power Broker Prepublication Technical Search-fit

**ID:** SLICE-0095
**Type:** IMPLEMENTATION
**Status:** READY
**Stage:** Joint Sail+Power Broker Excellence — private prepublication technical discoverability diagnostic for both qualified Power candidate planes
**Risk:** HIGH_RISK — Organization/MFA/PUBLISHER authorization, lifecycle concurrency, publisher category/claim provenance, design-versus-current truth, cross-variant AND and private SSR/API response trust
**Depends on:** Owner-accepted, merged and Owner-local FINISHED SLICE-0094; Owner-accepted SLICE-0084–0087 Sail DRAFT Search-fit, SLICE-0091 category, SLICE-0092 claim-only buyer path and SLICE-0093/0094 Power buyer Search, Owner joint-release direction #366, parity tracker #372.
**Owner selection:** Following confirmed successful Owner-local FINISH 0094, the Owner agreed 2026-10-28 (“ich stimme zu - weiter”) to next-slice evaluation/preparation. Repository-backed reassessment selects **Power Broker Search-fit parity for the already accepted two Power buyer criteria**, rather than an unpaired third buyer filter. This is readiness selection, not permission to bypass Owner START or review/acceptance.
**Readiness baseline:** canonical main `d399bc1a3601387992562ef0f3c9849929d07325` (SLICE-0094 implementation and formal closure merged, local FINISH 0094 SUCCESS); global native hard Search count 11 = Sail 9 / Power 2.
**Normative contract:** `specs/POWER_BROKER_SEARCH_FIT_CONTRACT.v0.1.md` (same docs-only readiness PR); existing 0084 and 0093/0094 source/field contracts remain normative.
**Unchanged STOPs:** #355 pre-real broker/owner-direct production data and pilot/CR-05 Search scale, #366 joint Sail+Power release, #372 broader Power specialist/broker parity, production gate IN_PROGRESS and Launch Pack NOT_STARTED.

## Objective / one observable capability

From an already promoted but still lifecycle-DRAFT, **owned** NativeListing, an authenticated MFA-confirmed Organization PUBLISHER can run a **read-only Power Search-fit preview** for `power_drive`, `power_engine_count`, or both using exact approved Buyer Power tokens and the same current-claim/FieldResolution truth as Buyer Power Search. Whether the vessel is design-linked or design-unresolved, show a typed hypothetical result (match / non-match / insufficient), requested technical leaves, configuration/current-boat sources, safe category blockers and concrete actions available in the existing editor.

**Visibility proof:** An authorized broker with a synthetic D29-incomplete or unpublished DRAFT of a physical POWER boat, own current POWER + SHAFT + 2 installed-motor claims, **without BoatDesign**, can run the combined preview from that DRAFT editor and see `CONFIRMED_MATCH`, clearly marked **publisher-claimed, not independently verified**, with **both** requested criteria TRUE. Adding a genuinely qualified source and linking the matching BoatDesign can add real per-configuration design evidence but never automatically replace current concrete truth. Changing count to 1 produces no combined positive; unrelated Organization, wrong category, split NamedVariants, unknown/absent sources and concurrent revoked publisher role never produce false successful results. The preview does not publish anything, assert D29 eligibility, or say real buyers searched for this configuration.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS
One vertical Broker Workspace user job: evaluate one existing Power DRAFT's hypothetical technical findability against the two already accepted Power criteria. The authorized API, evidence DTO, UI and negative proofs are inseparable parts. No third criterion/import/export/launch/browse capability is bundled.

**VISIBLE-RESULT CHECK:** PASS
The Owner can run the retained real migrated PostgreSQL18 + uvicorn FastAPI + built Astro SSR inspection and the existing local browser workflow to observe real DRAFT claim-only and design-linked Search-fit outcomes, source distinctions, correct broker editor links and unchanged Sail fit. No external account, broker dataset or product pilot required.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS
Broker-first UX and Buyer/Broker coequal quality under the 2026-10-22/23 Owner direction; common marketplace identity, source- and Organization-qualified current facts; fair organic Search; no external Sail-only/C-light pilot. Broker parity is now more valuable than adding a third Power Buyer criterion while published Power technical evidence has no prepublication seller diagnostic. Retain explicit Owner-direct and accepted Sail flows.

**REPOSITORY RECONCILIATION CHECK:** PASS
Current main actually contains an extensive Sail-only `broker_search_fit.py` adapted from shared Search qualification, but no Power-private DRAFT scenario route or form. Public `power_inventory_query.py` filters ACTIVE+D29 candidate populations so it cannot itself be called as a DRAFT preview; reuse its bounded projection/query/admission/classification mechanics, not its candidate enumerator.

**TRIGGER GATES CHECK:** PASS
Accepted architecture PASS, production IN_PROGRESS, global technical count 11 unchanged, workflow reassessment PASS. Adds NO technical native Search criterion; public Power and Sail registries/vocabularies unchanged.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS
Read `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`: MVP-BROKER-010 and REQ-BROKER-026 are implemented only within accepted Sail nine-criterion preview; **Power coverage is an additional category gap**, not a second independent business requirement. MVP-BUY-001/002 remain PARTIAL for joint-market parity. Broker onboarding/import/export/source rights (#372), runtime/pilot safety #355, mixed-category discovery, owner-direct trust, buyer saved searches/alerts, support, legal and operations are retained and not pronounced DONE. Source-qualified Power Broker diagnostics bring an immediate valuable seller benefit without starting the prohibited external pilot. This prioritization explicitly defers still-open buyer alerts and production work because the joint Power broker loop is missing a basic already-accepted buyer criterion counterpart.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS
See full high-risk qualification below.

**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE
This is a synthetic/internal, read-only DRAFT preview. No provider, actual production data, public surface or product pilot transition.

## Decision / implementation reconciliation

**Accepted records checked:** Owner joint Sail+Power decision `docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md`; `docs/POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md`; accepted SLICE-0084 and 0087 broker Search-fit; accepted SLICE-0091 category, 0092 qualified claim-only, 0093 drive and 0094 count READY/spec and closure; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`; `specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md`; owner-direct direction, post-0051 trigger gates, Production Readiness Gate, Overall MVP and Broker Workspace registers, #355/#366/#372.

**Production implementation checked:** `src/hullq/application/broker_search_fit.py` parser, DRAFT own-listing REPEATABLE READ snapshot + fresh role/lifecycle recheck, nine Sail-only definitions, blockers and concrete/design evidence; `src/hullq/api/app.py` exact existing Sail /search-fit private GET/serializer; `web/src/lib/brokerSearchFitApi.ts`, its tests and `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro` SSR Search-fit form/query/Result; `src/hullq/application/power_inventory_query.py` accepted `build_power_query`, `_resolve_power_category_admission`, `_downgrade_mixed_non_match_to_insufficient_data`, qualified design-linked + publisher claim-only paths; `src/hullq/application/native_inventory_query.py` shared `classify_claim_only_candidate`, `classify_concrete_candidate`, `build_configuration_evidence`, `run_mixed_boat_design_configuration_query`; `src/hullq/persistence/power_category_drive_snapshot.py` current coherent snapshot; Power static criteria/parser, broker current claim editor, and existing 0084/0093/0094 PG/SSR tests.

**Already implemented / not re-decided:** Broker PUBLISHER/MFA Organization boundary; private promoted-DRAFT Search-fit for all nine Sail criteria including no-write and concurrency semantics; nine Sail and two Power public criteria, Power separate buyer API and five locales, publisher's own positive POWER category, exact count 1–8/drive five-token buyer input, same-variant AND, immutable current observations, D29 for ACTIVE public results only, existing shared design qualification/FieldResolution and current claim classifiers.

**Exact remaining gap:** The existing Sail-only DRAFT Search-fit cannot accept any `power_drive`/`power_engine_count` scenario. No private Power DRAFT adapter or broker UI/API/typed blockers exists, so a broker cannot inspect hypothetical Power discoverability for the two already-accepted Power filters; simply calling public Power Search would evaluate unrelated D29 eligible ACTIVE listings and violate DRAFT ownership boundaries.

**Accepted-but-unimplemented obligations:** Full broader Power specialist criteria (engine models/types/hours, hull/displacement/planing, operating-condition-qualified speed/fuel/range), Power broker Search-fit parity once more criteria are accepted, Sail design-unresolved broker fit parity future reconciliation, general joint-category browse, Power import/export and compliant corpus/source rights, Motorsailer policy, buyer Saved Search/alerts, owner-direct seller/trust, pre-pilot operational/production/security safeguards #355, joint external product readiness #366 and ongoing #372.

**Material classifications:** DECIDED_AND_IMPLEMENTED = existing Sail broker DRAFT fit and two Power Buyer source-qualified criteria plus shared evaluator; DECIDED_NOT_YET_IMPLEMENTED = Power DRAFT Search-fit adapter/UI/API for both current Power criteria and both candidate planes; EXPLICITLY_DEFERRED = new criteria, real data, Power import/export, broad corpus and runtime/launch; GENUINELY_OPEN = future Motorsailer dual-domain path, full model/source-rights coverage and selection of successor after FINISH; CONFLICT_OR_REGRESSION = treating DRAFT as ACTIVE/D29 search, false design-only or other-Org Power admission, fabricated design link/Factory verification, cross-variant/cross-revision positive or leaking foreign listing identity.

## Trigger gates

**Production readiness gate:** IN_PROGRESS
**Adds technical native Search criterion:** NO
**Technical Search criterion ordinal:** NOT_APPLICABLE
**Second-criterion bridge comparison:** NOT_APPLICABLE
**Third-copy abstraction guard:** NOT_APPLICABLE
**Workflow reassessment status:** PASS

**Gate 3 technical comparison:** This creates **zero** new hard technical criteria or Search predicate implementations. Global marker `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` must remain **11**, category split Sail 9 / Power 2. The accepted static Power definitions and shared query / configuration / concrete-claim classifiers are reused. The private DRAFT orchestration is structurally distinct from ACTIVE/D29 public candidate enumeration; no third copy of a technical truth engine or new resolution policy is authorized. Original Sail private /search-fit and public Search remain intact.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE
**Launch-pack phase after this slice:** NOT_APPLICABLE

This uses only synthetic/private DRAFT listing inspection and is not a production-stage transition. Public listing D29 readiness must remain independently enforced.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK

**Why this classification:** A private single-target listing diagnostic crosses session/membership/MFA authorization, persisted lifecycle and mutable current claim revisions. A bad snapshot, leaked category source or reused ACTIVE enumerator could expose another Organization's DRAFT, fabricate a Power-positive, or mislead a broker about publishability. The diagnostic must preserve accepted 0084/0093/0094 current-versus-design and UNKNOWN distinctions.

**Must-never-change invariant:** Only an exact currently ACTIVE PUBLISHER membership with MFA may inspect its own lifecycle-DRAFT NativeListing; foreign or missing IDs remain non-enumerating. A POWER-positive preview requires this Organization's current explicit POWER claim and true requested drive/count from a coherent current revision. For design-linked, the same genuinely FieldResolution-qualified design configuration satisfies all criteria **and** actual claims independently match. A design-unresolved listing can match on publisher claims without fabricated design identity; missing evidence remains INSUFFICIENT_DATA; the preview writes nothing and proves no D29/publication status or real buyer demand.

**Durable source of truth / loss boundary:** Canonical Organization membership/role/MFA session, NativeListing identity + episode + PhysicalBoat link/lifecycle, immutable PhysicalBoatClaimRevision/head including category/drive/count and claiming Organization, admitted canonical BoatDesign/FieldResolution/NamedVariant where present. Browser query/local state or cached API result is transient illustration; process/browser/server loss cannot promote it to a listing or a verified design fact. No schema migration is required.

**Retry / replay / partial-failure behavior:** Read-only re-evaluation against fresh PostgreSQL facts yields recomputed typed evidence; duplicate GET has no effect. Within one consistent REPEATABLE READ transaction evaluate owner chain, category, all criteria and design evidence; afterward revalidate present-role/MFA and DRAFT lifecycle fresh, explicitly including foreign ownership. If role revoked, MFA expires, or listing becomes ACTIVE/WITHDRAWN between first snapshot and final recheck, return denial/not-previewable rather than OK. Concurrent revision replacement may yield a coherent earlier snapshot but never a hybrid of category, drive and count. Broken chain/DB fault fails as 503/service error, not as false match/unknown.

**Absence-vs-error / fail-closed behavior:** Missing linked design is a legitimate **claim-only** path, not inherently a missing-data blocker; dangling non-null link is integrity failure, not claim-only. Missing publisher-owned POWER, other-Organization disagreement, unresolved/ambiguous design variant, missing count/drive or unsupported POWER drive MIXED yield safe INSUFFICIENT_DATA/typed category non-match as appropriate. Invalid scenario is 400, no session 401, MFA/role denial 403, foreign/unknown 404, wrong lifecycle 409; real DB/service/JSON error is never a successful technical 200. Buyer claim-only provenance is not independent verification.

**Executable adversarial proof:** Real PostgreSQL18 two-connection auth/lifecycle and revision races, POWER/SAIL/MOTORSAILER/UNKNOWN/CONFLICT publisher and cross-Organization cases, count-only/drive-only/both, same-config vs split-variant matches, factory/raw/unqualified versus current installed refit, no BoatDesign positive, dangling design link integrity fault, invalid/duplicate/blank/unsupported inputs, no writes, private API/SSR typed outcomes and no cross-account data. Regression on Sail broker Search-fit 0084–0087 and Power buyer 0093/0094, 5-locale public Power, NautiX and category gates.

**Slice sizing assessment:** COHERENT
A one-listing read-only Power DRAFT diagnostic uses the same exact two already implemented Power predicates. It spans API/private UI/test/provenance because the complete broker action is one capability, not multiple independent feature domains. A new Power criterion or cross-category generic browse would be SPLIT_REQUIRED.

## Why this slice exists

Power's existing internal buyer Search now has two useful combinable hard criteria, but a mixed-stock broker editing a POWER DRAFT has no category-appropriate technical Search-fit forecast. A third Power buyer filter without its current seller-side diagnostic widens the Buyer/Broker parity deficit. This slice closes the directly observable broker usability gap without bringing external data, corpus, operational launch or new technical dimensions into scope. It is prerequisite groundwork for remaining #372 Power Broker Excellence, not full parity completion.

## Controlling artifacts

- `specs/POWER_BROKER_SEARCH_FIT_CONTRACT.v0.1.md` (this readiness PR), existing accepted 0084 private fit and 0093/0094 Power criteria contracts.
- `src/hullq/application/broker_search_fit.py`, `src/hullq/application/power_inventory_query.py`, `src/hullq/application/native_inventory_query.py`, `src/hullq/application/vessel_category_resolution.py`, `src/hullq/persistence/power_category_drive_snapshot.py`, broker auth read, persisted claim observations, `src/hullq/api/app.py`, broker SSR editor and JS client.
- `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`, `docs/governance/POST_0051_TRIGGER_GATES.md`, `docs/governance/PRODUCTION_READINESS_GATE.md`, `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`, `docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md`, `docs/POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md`; issues #355, #366, #372.

## Required behavior / implementation boundary

1. Create a **bounded, separate private Power DRAFT Search-fit** evaluator and API route under the same authorized broker Organization/listing chain, not a mutation of legacy Sail fit's accepted parser or result semantics. Preserve 0084 PUBLISHER/MFA, DRAFT lifecycle and REPEATABLE READ with fresh post-snapshot recheck. Do not enumerate ACTIVE public candidates or test D29 to allow a DRAFT preview.
2. Reuse Power `build_power_query` and its two static definitions, the accepted `classify_claim_only_candidate`, `classify_concrete_candidate`, `run_mixed_boat_design_configuration_query`, coherent design snapshot and Power category admission/MIXED interpretation. If a helper is currently private, extract/reuse narrowly with existing callers tested rather than copying its business logic or taking an unsafe independently timed claim read.
3. Add a design-unresolved broker-claim-only Power evaluation using the same current category+drive+count observation set with no fabricated BoatDesign. Include a safe source type and no design evidence; missing actual publisher current POWER/category/criterion never yields a positive.
4. For genuine design links evaluate all requested leaves on each properly qualified baseline/NamedVariant, require one matching same configuration and an independently qualified current publisher claim. Preserve evidence for other nonmatching/unknown configurations, and apply POWER category admission coherently. A dangling design link is a typed integrity error.
5. Broker API accepts only canonical `power_drive` and/or `power_engine_count` (strict presence/duplicates/grammar); returns a correctly scoped typed single-listing result with explicit source labels and actionable blockers, not public Search list, source identity leakage, D29 state or real-demand metrics. Non-success HTTP statuses preserve existing private auth/validation/error distinctions; typed malformed 200 is rejected in frontend.
6. Update existing authorized inventory editor SSR with a separate marked Power Search-fit GET form. Query fields use distinct page-local `psf_*` keys, no silent duplicates/blank-to-missing; selected branch cannot trigger Sail fit or vice versa. Preserve accurate claim-editor vs design-editor blocker links. A separate preview outage never breaks unrelated editor read/edit.
7. Add persisted PG18 adversarial tests, immutable state no-write assertions, concurrency, API/DTO/client malformed cases, and a retained real PostgreSQL18+FastAPI+Astro SSR owner-inspectable proof. Retain Sail broker, Power buyer, D29 and category regressions.
8. No new independent Power evaluator, schema/claim field, public Search filter, listing release, import/export, production provider or full broker parity claim.

## Deliverables / touchpoints

- `specs/POWER_BROKER_SEARCH_FIT_CONTRACT.v0.1.md` and this accepted READY remain source of truth.
- Bounded application adapter (prefer `src/hullq/application/power_broker_search_fit.py`) and minimal qualified shared helper extraction if needed; private API serializer+GET route; isolated typed SSR client/form/result section in the existing broker editor.
- Real PostgreSQL18 auth, lifecycle, category/claims, baseline/variant, concurrent-revision and private HTTP regression fixtures; browser/SSR contract tests with actual current publisher vs design truth. No database schema change.
- Retained inspector `scripts/inspect_slice_0095_power_broker_search_fit.py` or equivalent, executable with local PG18 and real backend/SSR and visible result/error assertions.

## Acceptance criteria

- [ ] Only an authorized active PUBLISHER with MFA can inspect its own promoted lifecycle-DRAFT listing. Private 401/403/404/409/503 distinguish auth, non-enumeration, lifecycle and real integrity fault; no write from preview.
- [ ] Public Power drive 5-token/count exact 1–8 grammar reused; count-only, drive-only and combined scenario return typed factually correct per-leaf truth. Empty, blank, duplicates, extra keys, invalid count=9 and unsupported drive fail 400 rather than silently default.
- [ ] Design-unresolved current publisher-owned POWER+count2+SHAFT positively confirms **claim-only** combined Search-fit without requiring BoatDesign link or claiming design verification; contradictory other-Org/missing publisher POWER does not.
- [ ] Design-linked qualifiers use qualified baseline/NamedVariant, explicit current publisher POWER+technical claims and coherent snapshot; split-variant apparent AND never matches, factory-only/refit/unresolved never invents concrete truth. Other configurations' FALSE/UNKNOWN evidence remains explainable.
- [ ] Browser editor preserves Sail Search-fit, supports separate POWER form with no blank/duplicate shadow key effects, shows truthful source/evidence/explanations and correct claim/design blocker links, retains noindex/private/no-store protections.
- [ ] Actual PG18 two-connection revision/MVCC/auth/lifecycle races, wrong org/category, wrong owner, stale conditions and genuine chain-integrity failure are tested; cross-Organization IDs and account actors never leak publicly.
- [ ] A retained **real PostgreSQL18 + uvicorn FastAPI + built Astro SSR** proof demonstrates draft preview count-only/combined true, false and insufficient with appropriate labels and one Sail legacy control. No live external data or public pilot.
- [ ] Existing 0084–0087 Sail broker fit, 0093/0094 public Power Search, nine Sail public Search, D29, NautiX category guard, repository validator all pass; technically accepted criteria marker remains **11** and workflow/production gates unchanged.
- [ ] Full exact pushed implementation HEAD has six-job CI, Manufacturer and applicable Deploy workflow success, independent reviewer acceptance and explicit Owner Acceptance before implementation merge. Separate closure follows; Owner-local FINISH only last.

## Stop conditions / independent-review expectations

- A broker gets a Power TRUE for missing current publisher POWER category, another Organization's assertion, design-only category or an inferred factory configuration.
- A DRAFT is inserted into ACTIVE/D29 public Search to produce preview, or a current-fact revision is spliced with stale design/category read.
- Original Sail Broker Search-fit changes semantics or drops supported nine Sail criteria; Power public filter whitelist, Sail routes or D29 eligibility are modified.
- The form silently collapses duplicates/blank, suppresses real errors as unknown, promotes publisher attestation into independent verification, or leaks private authors/other Organization identities.
- New Power fields/schema/third criterion, generic browse, Power import/export, actual external brokers, product pilot or public launch become necessary; stop and request a distinct later readiness/Owner decision, not scope creep.

## Owner workflow and required handoff

This is a **docs-only readiness contract** and normative spec. Confirm its exact-HEAD independent review and remote gates, merge it to main, and **only then** have the Owner locally run the unchanged `START_SLICE.bat` for **0095**. Do not claim START occurred until the Owner supplies actual output. The implementing Claude agent works only on the assigned `slice/0095-...` worktree/branch, produces the compact SLICE_TEMPLATE handoff and NEVER marks DONE, accepts itself, merges or starts another slice. ChatGPT project master independently reviews the code and owns all remote post-Owner-Acceptance closure work until local Owner FINISH, per the binding 2026-10-28 workflow in `CLAUDE.md` and `docs/engineering/AI_SLICE_WORKFLOW.md`. No automatic next slice.
