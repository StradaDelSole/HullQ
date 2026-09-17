# SLICE-0055 — Second Technical Native Inventory Search Criterion: Keel Configuration

**ID:** SLICE-0055  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Native technical Search — multi-criterion production proof  
**Depends on:** SLICE-0054 owner-accepted / DONE; post-0054 product/repository reconciliation completed for this capability  
**Blocks:** later broader multi-criterion Search, BuyerRequirements-backed evaluation and buyer-facing explainability projections

## Objective

Deliver exactly one visible capability:

> A buyer can search native marketplace inventory by hard `keel_configuration`, alone or together with the existing `draft_max`, while HullQ preserves deterministic criterion-level truth/evidence and never guesses unresolved design/configuration or concrete-yacht keel facts.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One Search capability: criterion #2 plus the minimum shared production evaluation abstraction required by the already-accepted criterion-#2 trigger.

**VISIBLE-RESULT CHECK:** PASS  
A buyer can execute Direct Search with keel alone and draft+keel and receive only confirmed matching native listings.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted execution plan prioritizes one visible buyer capability at a time and preserves strict truth/fail-closed Search. The post-SLICE-0054 buyer reconciliation keeps Direct Search as the primary low-friction entry point and requires later Buyer Requirements to reuse, not replace, the same deterministic Search/evaluation semantics. SLICE-0055 advances that path by exactly one hard native Search criterion while leaving BuyerRequirements, decision tools, shortlist/Compare, monitoring and ranking outside this slice. Organic eligibility, match classification and ordering remain commercially independent.

**REPOSITORY RECONCILIATION CHECK:** PASS  
The accepted Search kernel already has `CategoricalLeafCriterion`, `MixedAndQuery`, `CriterionEvaluation`, configuration identity/evaluation, and three-valued aggregation. The current SLICE-0051 production bridge is field-specific and currently discards non-match/insufficient criterion detail at the application outcome. BoatDesign v0.6 already models `appendages.keel_type`; PhysicalBoat claims already model `keel_configuration`. The exact remaining gap is to bring categorical keel evaluation into the production native-inventory funnel without a second copied bridge and preserve criterion evidence through the application boundary.

**TRIGGER GATES CHECK:** PASS  
This is technical native Search criterion ordinal #2. The mandatory second-criterion bridge comparison therefore applies. Criterion count remains 1 until SLICE-0055 is owner-accepted and closed. Workflow reassessment remains due after accepted SLICE-0056, not before 0055. No production-data/pilot trigger is introduced.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `docs/slices/SLICE-0035-categorical-configuration-aware-search.md`; `docs/slices/SLICE-0051-first-requirements-native-inventory-search.md`; `docs/slices/SLICE-0051-acceptance-closure.md`; `docs/slices/SLICE-0054-acceptance-closure.md`; `specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md`; `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`; `specs/BOAT_DESIGN_SCHEMA.v0.6.json`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`.  
**Production implementation checked:** `src/hullq/search/criteria.py`; `src/hullq/search/query_mixed.py`; `src/hullq/search/configuration.py`; `src/hullq/search/configuration_engine.py`; `src/hullq/search/draft_max_design_bridge.py`; `src/hullq/search/draft_max_request.py`; current native inventory Search application/API/browser path and retained SLICE-0051 tests/proofs.  
**Already implemented / not re-decided:** the accepted `draft_max` production native Search criterion; exact Decimal draft semantics; `CategoricalLeafCriterion`; mixed numeric/categorical `MixedAndQuery`; deterministic MUST/AND and three-valued truth semantics; BoatDesign/configuration versus PhysicalBoat truth separation; FieldResolution/current-snapshot qualification; configuration identity; existing BoatDesign `appendages.keel_type` and PhysicalBoat `keel_configuration` vocabularies; owner-direct/professional supply neutrality and organic Search commercial independence.  
**Exact remaining gap:** production Direct Search cannot yet accept/evaluate `keel_configuration` through the native inventory truth funnel, combine it with `draft_max`, preserve criterion-level match/non-match/insufficient evidence through the application boundary, or do so without structurally copying the SLICE-0051 field-specific production bridge.  
**Accepted-but-unimplemented obligations:** SLICE-0055 must add the bounded v0.1 `keel_configuration` hard criterion and criterion-#2 shared-bridge/evidence work. Broader BuyerRequirements, buyer explainability/sensitivity, shortlist/Compare/sharing, Saved Search/alerts, Rare Match/comparables, Broker Search Intelligence, owner-direct publication/admission and later technical criteria remain pending under their existing contracts/triggers and are not pulled into this slice.  
**Material classifications:** `DECIDED_AND_IMPLEMENTED` for the existing Search kernel, `draft_max`, truth/configuration boundaries and accepted keel field vocabularies; `DECIDED_NOT_YET_IMPLEMENTED` for the bounded criterion-#2 production path and criterion-level application evidence; `EXPLICITLY_DEFERRED` for the named out-of-scope buyer/search/seller capabilities; `GENUINELY_OPEN` has no material product/domain/architecture question blocking this bounded slice; `CONFLICT_OR_REGRESSION` has no production-code instance identified by this readiness review, while the readiness-document governance defect is corrected in this amendment.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** YES  
**Technical Search criterion ordinal:** 2  
**Second-criterion bridge comparison:** PASS  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** NOT_DUE

Evidence:

- canonical accepted technical native Search criterion count is `1`, so this capability is exactly criterion #2;
- the readiness contract explicitly compares the SLICE-0051 draft bridge with the keel path and requires shared production mechanics to be reused/generalized while criterion-specific decoding/mapping stays behind adapters;
- criterion #2 therefore satisfies the second-criterion comparison obligation, while the third-copy guard does not apply until criterion #3 or later;
- SLICE-0055 uses internal/synthetic retained proof and introduces no real external marketplace production data, production pilot or public production launch;
- workflow reassessment remains `NOT_DUE` through accepted SLICE-0055 and becomes due after accepted SLICE-0056 unless a production-pilot trigger fires earlier;
- Search remains supply-neutral and commercially independent: professional or owner-direct payment/verification state cannot buy organic eligibility, match classification or ordering.

## Controlling artifacts

- `specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md`
- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`
- `specs/BOAT_DESIGN_SCHEMA.v0.6.json`
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- `docs/PRODUCT_EXECUTION_PLAN.md`
- `docs/PRODUCT_UX_PRINCIPLES.md`
- `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`
- `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`
- `docs/slices/SLICE-0035-categorical-configuration-aware-search.md`
- `docs/slices/SLICE-0051-first-requirements-native-inventory-search.md`
- `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- `docs/governance/POST_0051_TRIGGER_GATES.md`
- `docs/governance/PRODUCTION_READINESS_GATE.md`
- `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`

## In scope

1. Public hard `keel_configuration` query criterion using the exact v0.1 vocabulary in the controlling contract.
2. Keel-only Direct Search through the native inventory truth funnel.
3. Mixed `draft_max AND keel_configuration` Direct Search.
4. FieldResolution-qualified BoatDesign baseline and safely resolvable NamedVariant keel projection.
5. Explicit bounded BoatDesign-keel to Search/PhysicalBoat-keel mapping; unsupported mappings fail closed.
6. Reuse/generalization of SLICE-0051 production bridge responsibilities sufficient to avoid a second structural copy.
7. Concrete PhysicalBoat keel evaluation and contradiction guard.
8. Criterion-level evidence retained for confirmed match, confirmed non-match and insufficient-data outcomes.
9. FastAPI/browser integration consistent with the existing Direct Search surface.
10. PostgreSQL-backed retained proof and non-regression coverage for existing `draft_max`.

## Explicitly out of scope

- automatic `design_options` combination expansion;
- mapping BoatDesign categories not authorized by the v0.1 contract;
- BuyerRequirements persistence or guided journey;
- PREFER/DONT_CARE;
- Why-no-match/sensitivity UI;
- shortlist/Compare/sharing;
- Saved Search/alerts;
- Rare Match/comparables;
- Broker Search Intelligence;
- ranking/recommendation;
- owner-direct publication/admission;
- external production data or pilot.

## Required behavior

### A. Query validation

`keel_configuration` accepts only the contract's finite v0.1 canonical values. Invalid/unsupported values fail as client input; no fuzzy or implicit normalization occurs.

### B. Mixed MUST semantics

Keel alone is one categorical MUST leaf. With `draft_max`, both leaves are evaluated by the existing mixed AND semantics. Any confirmed FALSE prevents a confirmed joint match; unresolved evidence never becomes TRUE.

### C. Design/configuration eligibility remains separate from concrete yacht truth

Design/configuration evaluation only establishes possible eligibility. A concrete listing is a confirmed match only after the accepted native inventory/PhysicalBoat truth funnel also confirms the required keel fact and all other active hard criteria.

### D. No configuration invention

Baseline and safely resolvable NamedVariants may be projected. No generic DesignOption expansion or inferred applicability/combinability is permitted. Existing configuration identity and fail-closed completeness rules remain authoritative.

### E. FieldResolution discipline

Raw BoatDesign JSON presence is not confirmed truth. Current accepted FieldResolution state and canonical snapshot agreement are required for direct design/NamedVariant keel values just as SLICE-0051 requires for draft. Inheritance must not fabricate a second resolution merely to represent inheritance.

### F. Criterion #2 abstraction guard

The implementation must compare the 0051 draft bridge and the new keel path, extract/reuse the genuinely shared production mechanics, and keep only criterion-specific decoding/mapping/value logic behind adapters. A parallel copied keel bridge with duplicated lookup/qualification/configuration/application lifecycle fails readiness.

### G. Evidence preservation

Production Search results must retain typed criterion-level evaluation detail for all three result classes. Buyer-facing explainability is not implemented, but later explainability must be able to project from preserved Search evidence rather than re-run separate truth logic.

### H. Non-regression

Existing `draft_max` public syntax, exact Decimal behavior, truth semantics, listing ordering/classification and retained proofs remain valid.

## Acceptance criteria

1. Keel-only confirmed match is demonstrated end-to-end.
2. Keel-only confirmed non-match and insufficient-data cases are demonstrated without entering primary results.
3. Draft+keel confirmed joint match is demonstrated.
4. Draft TRUE + keel FALSE is non-match; draft TRUE + keel UNKNOWN is insufficient, not match.
5. Concrete PhysicalBoat keel contradiction blocks an otherwise design-eligible listing.
6. Unsupported design taxonomy mapping fails closed.
7. NamedVariant override/inheritance behavior is deterministic and resolution-qualified.
8. Unresolved DesignOption dependency is not expanded or guessed.
9. Application outcome retains criterion-level evidence for all result classes.
10. Existing 0051 draft-only behavior is unchanged.
11. No BuyerRequirements/PREFER/decision-tool scope appears.
12. Repository tests, type/lint gates and retained PostgreSQL proof pass.

## Stop conditions

Stop and return to readiness review rather than inventing semantics if implementation requires any of: automatic option-combination expansion; a new unreviewed keel taxonomy mapping; weakening FieldResolution qualification; changing the meaning of existing `draft_max`; or a third independent production Search bridge architecture.
