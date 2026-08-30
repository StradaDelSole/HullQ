# SLICE-0036 — Marine technical entailment contract v0.1

**ID:** SLICE-0036  
**Type:** DESIGN_RESEARCH  
**Status:** READY  
**Stage:** P0 Data Track — marine semantic correctness before first real search vertical  
**Depends on:** SLICE-0034 accepted/DONE; SLICE-0035 accepted/DONE; `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`; `specs/BOAT_DESIGN_SCHEMA.v0.6.json`; `docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md`  
**Blocks:** Oceanis 30.1 practical application and the first real BoatDesign through the existing search kernel

## Objective

Create one finite, versioned, auditable marine-technical entailment contract for the existing HullQ v0.6 technical vocabulary so HullQ may derive a canonical/search-relevant fact only when an already-qualified source fact definitionally or technically guarantees it, while failing closed for ambiguity, domain exceptions, missing applicability or contradiction.

This slice defines and validates **what may be inferred**. It does not build a generic inference engine, add new technical taxonomy, admit real BoatDesign data, or change search truth semantics.

## Why this slice exists

SLICE-0034 decomposed several compressed marine concepts into independent v0.6 fields. Its amended v0.5 -> v0.6 mapping already established the key conservativity rule: assert a concrete decomposed fact only when the predecessor token itself logically guarantees it, never because the relationship is merely typical or conventional. It also established concrete examples such as `masthead_sloop -> sailplan=sloop + masthead_fractional=masthead`, `spade -> rudder_support=free` only on a definitional basis, and `rudder_type=twin -> rudder_count=2`, with explicit conflict rather than silent overwrite when a concrete source count disagrees.

SLICE-0035 then made categorical and configuration-aware values capable of authorizing search truth. That raises the consequence of ad-hoc marine inference: a plausible but non-entailing technical guess can now become a false confirmed match/non-match. HullQ therefore needs an explicit marine entailment boundary before continuing the real P0 BoatDesign data track.

This is correctness work, not breadth work. The boundedness mechanism is the **existing controlled vocabulary and exact field inventory below**, not an open-ended attempt to model marine engineering.

## Controlling artifacts

- `specs/TECHNICAL_PROFILE_SPEC.v0.1.md` — CORE_SEARCH technical families, applicability-before-conflict, provenance and canonical/search boundary.
- `specs/BOAT_DESIGN_SCHEMA.v0.6.json` — current canonical technical field shapes, enums and existing bounded cross-field consistency constraints.
- `docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md` — accepted conservative decomposition semantics and regression examples from SLICE-0034.
- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` — unchanged fail-closed search truth semantics.
- `docs/slices/SLICE-0035-categorical-configuration-aware-search.md` — configuration-aware truth boundary and applicability/dependency constraints.
- Existing FieldResolution/provenance/source-rights contracts remain controlling.

## Fixed field inventory

SLICE-0036 is limited to semantic relationships involving these existing v0.6 paths and their NamedVariant/DesignOption override equivalents:

### Multihull / hull configuration

- `configuration.hull_configuration`
- `configuration.hull_count`

### Keel / boards

- `appendages.keel_type`
- `appendages.keel_subtype`
- `appendages.centerboard_count`
- `appendages.centerboard_type`
- `appendages.daggerboard_count`
- `appendages.daggerboard_type`

### Rudder / skeg

- `appendages.rudder_count`
- `appendages.rudder_position`
- `appendages.rudder_support`
- `appendages.rudder_balance`
- `appendages.skeg_type`

### Rig

- `rig.sailplan`
- `rig.masthead_fractional`
- `rig.mast_count`
- `rig.mast_step`
- `rig.rig_variant`

### Cockpit / helm

- `deck.cockpit_position`
- `deck.cockpit_count`
- `deck.helm_type`
- `deck.helm_count`

The corresponding legacy v0.5 `rig_type` and `rudder_type` controlled tokens are in scope only to preserve the already-accepted conservative mapping semantics. No additional legacy taxonomy is introduced.

Free-text subtype/type/variant values may be inventoried as fields, but arbitrary strings MUST NOT authorize a derived fact in v0.1.

## In scope

1. Add a normative `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md` defining the epistemic, applicability, conflict and provenance rules for marine technical derivation.
2. Add a small machine-readable normative rule registry, preferably `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`, containing only declarative rules/coverage metadata. It MUST NOT become a generic executable rules language.
3. Exhaustively classify the **existing controlled enum tokens and bounded relation shapes** in the fixed field inventory. Each source token/relation must resolve to one of:
   - `DEFINITIONAL_ENTAILMENT` — exact cross-field output(s) are authorized because they are logically/definitionally guaranteed;
   - `DIRECT_ONLY` — the fact is usable only as the explicit field value itself; it authorizes no cross-field derivation;
   - `NO_DERIVATION` — ambiguity, source-dependent meaning, a relevant marine exception, sentinel/free-text semantics or lack of accepted basis prevents derived truth.
4. For every `DEFINITIONAL_ENTAILMENT`, record at minimum:
   - stable rule ID;
   - source field/token or bounded relation;
   - exact authorized derived field/value(s) or count relation;
   - required source qualification;
   - prerequisites;
   - applicability/configuration scope rule;
   - relevant exceptions;
   - explicit-conflict behavior;
   - evidence/definition basis;
   - required lineage/provenance payload semantics.
5. Preserve already-accepted SLICE-0034 entailments unless bounded research proves a material contradiction in controlling artifacts. If such a contradiction is found, STOP and report; do not silently rewrite accepted semantics.
6. Research only the finite terms/relations required by the fixed inventory. Prefer authoritative marine standards/rules, original technical definitions, class/measurement sources or recognized naval-architecture references. Record locators and paraphrased basis. Do not build a general marine bibliography.
7. If a proposed derivation cannot be established from controlling artifacts or bounded authoritative evidence, classify it `NO_DERIVATION`; do not keep researching indefinitely merely to avoid UNKNOWN.
8. Add mechanical contract tests that read enum sets from `BOAT_DESIGN_SCHEMA.v0.6.json` (and the relevant v0.5 legacy enums) and fail if any in-scope controlled token is unclassified, if rule IDs duplicate, or if a rule references out-of-scope paths/tokens.
9. Add positive and adversarial tests for every authorized entailment family, including contradiction, missing/unknown/provisional/unresolved input, mismatched applicability/configuration, and unsupported reverse inference.
10. Add a bounded real-design validation sample using only already-existing, rights/provenance-acceptable repository evidence. Select 3–4 technically different existing designs when the retained evidence supports them; the sample is an external acceptance test of the rule contract, not the source of the rules and not canonical admission.
11. Explicitly demonstrate that `UNKNOWN`/no derived fact is a correct successful outcome when the evidence does not entail a concrete value.
12. Preserve deterministic behavior and explicit lineage. A derived technical fact must never be indistinguishable from a directly reported fact.

## Mandatory epistemic rules

### A. Definition/necessity only

A cross-field fact may be derived only when the qualified source fact **definitionally or technically entails** it and no relevant maritime exception defeats that implication.

`usually`, `typically`, `commonly`, design convention, statistical correlation, visual plausibility and model-family familiarity are never sufficient.

### B. No artificial UNKNOWN

When a qualified controlled fact genuinely and definitionally entails another in-scope fact, HullQ must preserve that guaranteed information rather than deliberately returning UNKNOWN. `rudder_type=twin -> rudder_count=2` is the accepted pattern.

### C. Absence is not a negative fact

Missing/null/unknown data never imply absence or the opposite category. No negative inference may be manufactured from a field not being present or concrete.

### D. Applicability before conflict

Entailment occurs only within the same materially relevant BoatDesign/NamedVariant/DesignOption/configuration/applicability scope. Resolve applicability first. Facts from different legitimate configurations MUST NOT be combined into an invented hybrid configuration merely to complete a derivation.

### E. Explicit contradiction is surfaced, never overwritten

If a qualified explicit fact conflicts with a fact that would otherwise be definitionally entailed in the same applicability scope, do not silently prefer either one. Surface the existing conflict/manual-resolution semantics and withhold clean derived truth until resolved.

### F. No unsafe reverse inference

A rule is directional. `A -> B` does not authorize `B -> A` unless a separate rule independently proves the reverse implication. Counts, support, position, rig topology and hull topology must be reviewed for this explicitly.

### G. No recursive generic inference in v0.1

The v0.1 registry is declarative and bounded. Do not create a recursive/general-purpose inference engine, arbitrary rule chaining, self-supporting derivations or circular proofs. Each authorized output must be justified from qualified direct input fact(s) identified by the rule. If multi-step closure becomes necessary for product behavior, stop and return it as a later owner decision.

### H. Free text and sentinels cannot manufacture truth

Arbitrary `keel_subtype`, `centerboard_type`, `daggerboard_type`, `rig_variant` strings do not authorize cross-field derivation in v0.1. `unknown`, `other`, null and equivalent non-concrete sentinels do not authorize a more concrete derived fact unless an existing controlling contract explicitly gives that sentinel a separate semantic effect.

### I. Provenance/lineage is mandatory

The contract must specify that every derived fact retains at least the entailment rule ID/version, the exact supporting input field/value(s), their qualification/applicability scope and enough lineage to distinguish derived from directly reported truth. Do not design a new persistence subsystem in this slice.

## Finite completion criterion

The pass is **not** complete when it merely feels sufficiently researched. It is complete only when all of the following are objectively true:

1. Every controlled enum token in the fixed v0.6 field inventory is represented in the machine-readable coverage registry, including `unknown`, `other` and `not_applicable` where present.
2. Every fixed-inventory free-text field is explicitly classified as non-entailing by default.
3. Count/topology relations needed for the five families are explicitly classified direction by direction; unsupported directions are explicitly negative/no-derivation cases.
4. Every relevant legacy v0.5 `rig_type` and `rudder_type` token remains covered consistently with the accepted SLICE-0034 mapping.
5. Mechanical tests derive enum sets from the schemas themselves, so later enum drift cannot silently leave the matrix incomplete.
6. Every `DEFINITIONAL_ENTAILMENT` has positive, negative/reverse, conflict and applicability-focused verification as appropriate.
7. A 3–4 design retained real-world validation sample has been executed where repository evidence supports it, with expected concrete and expected UNKNOWN outcomes documented. No new canonical admission is implied.
8. No new field family, enum value or ontology concept was added to make the matrix appear complete.

If a currently in-scope schema token cannot be given a safe entailment basis, `DIRECT_ONLY` or `NO_DERIVATION` is a valid completed classification. Unknown is preferable to invented knowledge.

## Required research questions

For each family answer only the bounded cross-field questions exposed by the fixed inventory, including at minimum:

### Keel / boards

- Which existing `keel_type` tokens definitionally entail board presence/count or other in-scope appendage facts, if any?
- Which apparent exclusions are unsafe because real keel-centerboard, stub-keel/board or other hybrid constructions exist?
- Does any count/type fact safely imply another direction, and under exactly what prerequisites?

### Rudder / skeg

- Preserve and verify the accepted `twin -> rudder_count=2` rule and conflict behavior.
- Preserve/verify the accepted conservative distinctions among position, support and balance.
- Determine only definitionally safe skeg/support relations and explicitly reject typical support->position/balance shortcuts.

### Rig

- Preserve the accepted `masthead_sloop` and `fractional_sloop` legacy decompositions.
- Determine which current sailplan tokens definitionally constrain mast count or masthead/fractional applicability, if supported by bounded authoritative definitions.
- Do not infer masthead/fractional from cutter/ketch/yawl/schooner/cat merely from convention.

### Cockpit / helm

- Determine only exact count/position/type entailments encoded by current tokens such as `multiple`, if definitionally safe.
- Do not infer helm count from `wheel`/`tiller`, or cockpit position from unrelated layout conventions.

### Multihull / hull configuration

- Verify the existing schema certainties `monohull -> 1`, `catamaran -> 2`, `trimaran -> 3`.
- Test reverse directions separately; do not assume a count uniquely determines the named hull configuration if an allowed `other` topology can share that count.

## Real-design acceptance sample

Use retained repository-supported evidence only; do not launch a new model-research campaign for this acceptance sample. Prefer technically different designs already used by the technical-profile pilot, for example Rustler 36 / Contessa 32 / Bavaria Cruiser 34 / Sun Odyssey 36i where the retained evidence actually supports the relevant facts.

For each selected design record:

- direct qualified input facts used;
- rule IDs fired;
- concrete derived facts;
- facts intentionally left underived/UNKNOWN;
- conflicts/applicability splits if present;
- confirmation that the validation record is not canonical admission.

The real designs validate the rules; they do not define them. Oceanis 30.1 remains the first practical post-pass consumer and is out of scope for this slice.

## Explicitly out of scope

- New BoatDesign schema version or modification of v0.6 enums/field families.
- New keel/rudder/rig/cockpit/multihull ontology beyond the existing controlled vocabulary.
- Generic expert system, recursive rule engine, probabilistic inference, confidence-to-truth conversion or LLM runtime inference.
- Broad marine-domain research unrelated to a fixed-inventory token/relation.
- Oceanis 30.1 research, admission or production payload creation.
- Canonical admission/promotion of any real BoatDesign.
- P0 corpus breadth expansion.
- Search evaluator changes, Search Query Semantics changes or PREFER/OR/NOT work.
- PostgreSQL/read-model/index changes.
- FastAPI/public HTTP endpoint work.
- Frontend/SEO.
- Listing ingestion/dedup/geography/monitoring/auth/pricing.
- New derived-performance formulas.
- Changes to existing accepted schema constraints merely because a cleaner design is imaginable.

## Deliverables

- `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md`.
- `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json` or an equivalently small declarative machine-readable registry.
- Focused contract tests under `tests/contract/` proving exhaustive controlled-vocabulary coverage and the epistemic invariants.
- A small validation fixture/report under the existing technical-profile fixture/research structure for the retained real-design acceptance sample, if repository evidence supports it without new retrieval.
- Only minimal registry/validator plumbing required to validate the new declarative contract, if any.

Do not add production inference runtime code in this slice.

## Acceptance criteria

- [ ] Normative v0.1 entailment semantics exist and are explicitly limited to the fixed five families/field inventory.
- [ ] Existing v0.6 enum/token sets are mechanically extracted and exhaustively classified without hard-coded self-authorizing fixture coverage.
- [ ] `DEFINITIONAL_ENTAILMENT`, `DIRECT_ONLY` and `NO_DERIVATION` have unambiguous meanings and fail-closed defaults.
- [ ] Every authorized entailment names exact input(s), output(s), prerequisites, exceptions, applicability rule, conflict behavior, evidence basis and lineage requirement.
- [ ] No probability/common-practice inference can authorize a concrete derived fact.
- [ ] Missing/null/unknown/other/free-text inputs cannot silently become a more concrete derived fact.
- [ ] No negative fact is inferred from absence.
- [ ] Applicability/configuration scope is resolved before entailment/conflict evaluation.
- [ ] Explicit same-scope contradiction is surfaced rather than silently overwritten.
- [ ] Reverse implications are not assumed.
- [ ] v0.1 does not implement recursive/general rule chaining or a generic inference engine.
- [ ] Existing accepted SLICE-0034 rig/rudder conservative mappings remain consistent, including `twin -> rudder_count=2` with conflict on contradictory explicit count.
- [ ] Existing v0.6 `monohull/catamaran/trimaran -> hull_count 1/2/3` certainties remain consistent with the new contract.
- [ ] Tests include positive, negative, reverse-inference, conflict, applicability and sentinel/free-text adversarial cases.
- [ ] Retained real-design validation uses 3–4 technically different already-supported designs where evidence permits; UNKNOWN/no-derivation is explicitly accepted when warranted.
- [ ] No real-design validation record is promoted to canonical data by this slice.
- [ ] No schema enum/field family, search behavior, persistence behavior, API or frontend scope changed.
- [ ] Ruff format/check, mypy, repository validator and full pytest pass; repo coverage remains >=90% when coverage is applicable.
- [ ] Exact-head CI and Manufacturer artifact reproducibility pass.

## Adversarial review checklist

Before recommending REVIEW, explicitly inspect/test:

1. Can a rule derive a concrete fact from `unknown`, `other`, null, free text, provisional or unresolved-conflict input?
2. Can a common-but-not-necessary marine correlation enter the registry as if it were definitional?
3. Can an implication be silently used in reverse?
4. Can facts from different variants/options/configurations combine into one synthetic configuration?
5. Can an entailed fact silently overwrite a contradictory explicit fact?
6. Can a derived fact lose its rule/input/applicability lineage and become indistinguishable from reported truth?
7. Can adding a new enum token to v0.6 leave the coverage test green without an explicit classification?
8. Does any test fixture define the same allowed token/rule set that the test claims to independently verify?
9. Did the slice widen v0.6 taxonomy or create a generic rules engine merely to handle one difficult case?
10. Did the real-design sample become an implicit source of normative rules or canonical admission?

Any YES requires repair or an explicit stop/report.

## Expected touch points

- `docs/slices/SLICE-0036-marine-technical-entailment-contract.md`
- `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md`
- `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json` (preferred name)
- focused `tests/contract/`
- small existing `fixtures/technical_profile/` or research-validation artifact if justified
- contract registry/validator only if required for the declarative spec

Do not modify `BOAT_DESIGN_SCHEMA.v0.6.json`, search runtime, persistence runtime or frontend/API code. If correctness appears to require one of those changes, stop and report instead of widening scope.

## Validation

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
uv run python -m pytest
uv run python -m coverage run -m pytest
uv run python -m coverage report
```

Run focused contract tests added by this slice.

## Stop conditions

Stop and report instead of inventing a solution if:

- a safe entailment would require a new schema token/field family or modifying `BOAT_DESIGN_SCHEMA.v0.6.json`;
- controlling HullQ artifacts materially contradict each other;
- bounded authoritative evidence contradicts an already-accepted SLICE-0034 entailment;
- a rule requires probabilistic/common-practice reasoning rather than definition/technical necessity;
- a proposed relation depends on arbitrary free-text interpretation;
- correct behavior would require recursive/general rule chaining or production inference-engine implementation;
- real-design validation would require a new broad retrieval/research campaign or canonical promotion;
- fulfilling the slice would require search/persistence/API/frontend work.

In an ambiguous case, `DIRECT_ONLY`/`NO_DERIVATION` is preferred over expanding scope.

## Product guardrail after this slice

After SLICE-0036, do **not** insert another general schema/breadth/governance slice before at least one real BoatDesign is searchable through the existing search kernel, unless a genuine technical blocker discovered by exact implementation work requires an explicit Project Owner decision.

The intended sequence is:

`SLICE-0036 entailment contract -> Oceanis 30.1 practical application -> first real BoatDesign through existing search kernel (minimal local owner-test surface) -> only then next API/frontend architecture decision.`

## Status handoff rule

The research/implementation agent may leave `IN_PROGRESS`, `BLOCKED` or `REVIEW` as appropriate, but MUST NOT mark the slice DONE or merge it.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md` exactly and concisely. In addition report:

- exact in-scope schema paths/tokens classified;
- number/list of authorized `DEFINITIONAL_ENTAILMENT` rules;
- explicit `DIRECT_ONLY` / `NO_DERIVATION` areas with material rationale;
- authoritative definition sources used beyond controlling repo artifacts;
- real-design validation sample and concrete-vs-UNKNOWN outcomes;
- exact tests proving schema-derived coverage completeness;
- any relation that was deliberately left non-entailing because of a real maritime exception or unresolved definition;
- exact final branch HEAD SHA and exact-head remote gate state.

Do not propose or begin the next slice in the completion report.