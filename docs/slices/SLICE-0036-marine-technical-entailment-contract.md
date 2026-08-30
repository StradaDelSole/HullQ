# SLICE-0036 — Marine technical entailment contract v0.1

**ID:** SLICE-0036  
**Type:** DESIGN_RESEARCH  
**Status:** READY  
**Stage:** P0 Data Track — marine semantic correctness before first real search vertical  
**Depends on:** SLICE-0034 accepted/DONE; SLICE-0035 accepted/DONE; `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`; `specs/BOAT_DESIGN_SCHEMA.v0.6.json`; `docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md`  
**Blocks:** Oceanis 30.1 practical application and first real BoatDesign through the existing search kernel

## Objective

Create one finite, versioned and auditable marine-technical entailment contract for the **existing** HullQ v0.6 technical vocabulary.

HullQ may derive a canonical/search-relevant fact only when already-qualified source fact(s) definitionally or technically guarantee it and no relevant maritime exception defeats the implication. Ambiguity, missing applicability or contradiction fail closed.

This slice defines and validates **what may be inferred**. It does not add taxonomy, build a generic inference engine, admit real BoatDesigns, or change search truth semantics.

## Why this slice exists

SLICE-0034 established the conservative rule for decomposing marine facts: assert only what the source token logically guarantees, never what is merely typical. Accepted examples include `masthead_sloop -> sloop + masthead`, `spade -> rudder_support=free` on a definitional basis, and `rudder_type=twin -> rudder_count=2`, with explicit conflict for a contradictory concrete count.

SLICE-0035 now allows qualified categorical/configuration-aware values to authorize search truth. Ad-hoc marine inference could therefore create false confirmed matches/non-matches. This pass closes that correctness boundary before the real P0 BoatDesign track continues.

Boundedness is objective: the pass is limited to the existing v0.6 vocabulary and fixed field inventory below. It is not an open-ended marine ontology project.

## Controlling artifacts

- `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`
- `specs/BOAT_DESIGN_SCHEMA.v0.6.json`
- `docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md`
- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`
- `docs/slices/SLICE-0035-categorical-configuration-aware-search.md`
- Existing FieldResolution, provenance and source-rights contracts

## Fixed field inventory

Only semantic relations among these existing paths and their NamedVariant/DesignOption override equivalents are in scope:

- **Hull/multihull:** `configuration.hull_configuration`, `configuration.hull_count`
- **Keel/boards:** `appendages.keel_type`, `keel_subtype`, `centerboard_count`, `centerboard_type`, `daggerboard_count`, `daggerboard_type`
- **Rudder/skeg:** `appendages.rudder_count`, `rudder_position`, `rudder_support`, `rudder_balance`, `skeg_type`
- **Rig:** `rig.sailplan`, `masthead_fractional`, `mast_count`, `mast_step`, `rig_variant`
- **Cockpit/helm:** `deck.cockpit_position`, `cockpit_count`, `helm_type`, `helm_count`

Relevant legacy v0.5 `rig_type` and `rudder_type` tokens are in scope only to preserve accepted SLICE-0034 mapping semantics. No new legacy taxonomy is allowed.

Free-text subtype/type/variant fields are part of coverage but arbitrary strings MUST NOT authorize derived facts in v0.1.

## Required deliverable semantics

Add:

1. `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md` — normative human-readable contract.
2. `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json` — small declarative normative coverage/rule registry. It MUST NOT become a generic executable rules language.
3. Focused contract tests proving coverage and fail-closed invariants.
4. A bounded validation artifact for exactly **at least three** technically different, already repository-supported real designs.

Every in-scope controlled token/relation must be classified as exactly one of:

- `DEFINITIONAL_ENTAILMENT` — exact cross-field output(s) are authorized because the input logically/definitionally guarantees them.
- `DIRECT_ONLY` — the explicit fact is usable directly but authorizes no cross-field derivation.
- `NO_DERIVATION` — ambiguity, source-dependent meaning, relevant exception, sentinel/free-text semantics, or absent accepted basis prevents derived truth.

For every `DEFINITIONAL_ENTAILMENT`, record at minimum:

- stable rule ID/version;
- exact source field/token or bounded relation;
- exact authorized output field/value(s) or count relation;
- required source qualification;
- prerequisites;
- applicability/configuration scope;
- relevant exceptions;
- explicit-conflict behavior;
- evidence/definition basis;
- lineage/provenance requirements.

## Mandatory epistemic rules

### Definition/necessity only

A cross-field fact may be derived only when qualified input fact(s) **definitionally or technically entail** it. `Usually`, `typically`, `commonly`, design convention, statistical correlation, visual plausibility and model-family familiarity are never sufficient.

### No artificial UNKNOWN

If a qualified controlled fact genuinely entails another in-scope fact, preserve the guaranteed information rather than discarding it. `rudder_type=twin -> rudder_count=2` is the accepted pattern.

### Absence is not negative evidence

Missing/null/unknown data never imply absence or an opposite category.

### Applicability before conflict

All supporting facts must belong to the same materially relevant BoatDesign/NamedVariant/DesignOption/configuration/applicability scope. Never combine different legitimate configurations into a synthetic one.

### Explicit contradiction is never overwritten

If a qualified explicit same-scope fact contradicts an otherwise entailed fact, surface existing conflict/manual-resolution semantics and withhold clean derived truth. Do not silently choose either side.

### Directionality; no unsafe reverse inference

`A -> B` does not authorize `B -> A` unless a separate rule independently establishes that direction.

### No recursive generic inference in v0.1

No arbitrary chaining, recursive/general-purpose rule engine, self-supporting derivation or circular proof. Each authorized output must be justified from the qualified direct input fact(s) named by its rule. If product correctness requires multi-step closure, STOP and return it for a later owner decision.

### Free text and sentinels cannot manufacture truth

Arbitrary `keel_subtype`, `centerboard_type`, `daggerboard_type`, `rig_variant` strings are non-entailing by default. `unknown`, `other`, null and equivalent non-concrete sentinels cannot authorize a more concrete derived fact unless an existing controlling contract explicitly assigns that semantic effect.

### Derived lineage is mandatory

Every derived fact must retain rule ID/version, exact supporting input fact(s), their qualification/applicability scope, and enough provenance to remain distinguishable from directly reported truth. Do not design a new persistence subsystem here.

## Finite completion criterion

SLICE-0036 is complete only when all are objectively true:

1. Every controlled enum token in the fixed v0.6 inventory is present in the machine-readable coverage registry, including `unknown`, `other`, and `not_applicable` where present.
2. Every in-scope free-text field is explicitly non-entailing by default.
3. Relevant count/topology implications are classified **direction by direction**; unsupported directions are explicit `DIRECT_ONLY`/`NO_DERIVATION` cases.
4. Every relevant legacy v0.5 `rig_type` and `rudder_type` token remains covered consistently with accepted SLICE-0034 semantics.
5. Mechanical tests read enum sets from the schemas themselves, so later enum drift cannot silently leave coverage incomplete.
6. Every authorized entailment has positive verification plus appropriate reverse/negative, conflict and applicability tests.
7. At least **three technically different real designs** already supported by retained repository evidence have been run through the validation matrix, with concrete and expected-UNKNOWN outcomes documented.
8. No new field family, enum value or ontology concept was added to obtain completion.

If fewer than three suitable retained real-design evidence sets exist without a new retrieval/research campaign, the slice is **BLOCKED**, not accepted with a smaller sample. Do not broaden research to manufacture the sample.

`DIRECT_ONLY`, `NO_DERIVATION` and UNKNOWN are valid completed outcomes when a safe entailment basis does not exist.

## Bounded research questions

### Keel / boards

- Which existing `keel_type` tokens, if any, definitionally entail board presence/count or another in-scope appendage fact?
- Which apparent exclusions are unsafe because keel-centerboard, stub-keel/board or other hybrid constructions can exist?
- Which count/type implications are safe in each direction, under which exact prerequisites?

### Rudder / skeg

- Preserve/verify `twin -> rudder_count=2` and explicit-count conflict behavior.
- Preserve/verify the conservative separation of rudder position, support and balance.
- Authorize only definitionally safe skeg/support relations; reject support->position/balance shortcuts based on convention.

### Rig

- Preserve legacy `masthead_sloop` and `fractional_sloop` decompositions.
- Determine only definitionally supported sailplan->mast-count or applicability relations.
- Do not infer masthead/fractional for cutter/ketch/yawl/schooner/cat from convention.

### Cockpit / helm

- Determine only exact count/position/type implications encoded by current controlled tokens.
- Do not infer helm count from `wheel`/`tiller`, or cockpit position from unrelated layout conventions.

### Multihull / hull configuration

- Verify existing v0.6 certainties `monohull -> 1`, `catamaran -> 2`, `trimaran -> 3`.
- Test reverse directions independently; do not assume a hull count uniquely identifies a named topology if an allowed `other` topology can share that count.

## Research/evidence rule

Research only the finite terms/relations above. Prefer authoritative marine standards/rules, original technical definitions, class/measurement material, or recognized naval-architecture references. Record locators and paraphrased bases; do not build a general bibliography.

If a proposed implication cannot be established from controlling artifacts or bounded authoritative evidence, classify it `NO_DERIVATION`. Do not continue researching indefinitely merely to avoid UNKNOWN.

If bounded authoritative evidence materially contradicts an already-accepted SLICE-0034 entailment, STOP and report rather than silently rewriting it.

## Real-design validation

Use exactly the retained repository evidence; do not launch a new model-research campaign. Select at least three technically different existing designs already represented/supportable by that evidence. A fourth is optional only if already available and materially useful.

For each selected design record:

- qualified direct inputs;
- rule IDs applied;
- concrete derived facts;
- intentionally underived/UNKNOWN facts;
- conflicts/applicability splits;
- explicit statement that validation is not canonical admission.

The designs validate the rules; they do not define them. **Oceanis 30.1 is out of scope for 0036 and remains the first practical post-pass consumer.**

## Mechanical/adversarial verification

Tests MUST at minimum prove:

- v0.6 enum sets are extracted from `BOAT_DESIGN_SCHEMA.v0.6.json`, not duplicated by a self-authorizing fixture;
- relevant v0.5 enum sets are likewise covered;
- no in-scope controlled token is unclassified;
- no duplicate rule ID exists;
- no rule references an out-of-scope path/token;
- sentinel/free-text/provisional/unresolved inputs cannot derive concrete truth;
- absence cannot create negative truth;
- unsupported reverse implications fail closed;
- cross-configuration/applicability mixing cannot create a synthetic derivation;
- entailed facts cannot silently overwrite contradictory explicit facts;
- derived output retains rule/input/applicability lineage;
- adding a new schema enum token would make coverage fail until explicitly classified.

## Explicitly out of scope

- New BoatDesign schema version or changes to v0.6 enums/field families.
- New keel/rudder/rig/cockpit/multihull ontology.
- Generic expert system, recursive rule engine, probabilistic inference, confidence-to-truth conversion, or LLM runtime inference.
- Broad marine research unrelated to the fixed inventory.
- Oceanis 30.1 research/admission/payload creation.
- Canonical admission/promotion of any real BoatDesign.
- P0 corpus breadth expansion.
- Search evaluator/Semantics changes, PREFER/OR/NOT.
- PostgreSQL/read-model/index work.
- FastAPI/public HTTP endpoint or frontend/SEO work.
- Listing ingestion/dedup/geography/monitoring/auth/pricing.
- New derived-performance formulas.

## Acceptance criteria

- [ ] Human-readable normative contract and small declarative registry exist and are limited to the fixed inventory.
- [ ] `DEFINITIONAL_ENTAILMENT`, `DIRECT_ONLY`, `NO_DERIVATION` are unambiguous and fail closed.
- [ ] Existing schema/legacy controlled vocabularies are mechanically and exhaustively classified.
- [ ] Every authorized entailment records exact input/output, prerequisites, exceptions, applicability, conflict behavior, evidence basis and lineage.
- [ ] No probability/common-practice, absence, sentinel, arbitrary free text or unsupported reverse inference can authorize concrete truth.
- [ ] Applicability is resolved before entailment/conflict; same-scope contradictions are surfaced, never overwritten.
- [ ] No recursive/general rule engine or arbitrary chaining was implemented.
- [ ] Accepted SLICE-0034 conservative rig/rudder semantics remain consistent, including `twin -> rudder_count=2` with conflict on contradictory explicit count.
- [ ] Existing v0.6 hull-configuration/count certainties remain consistent.
- [ ] At least three technically different retained real designs pass the external validation requirement; UNKNOWN is accepted where warranted.
- [ ] No validation record is promoted to canonical data.
- [ ] No schema/search/persistence/API/frontend scope changed.
- [ ] Ruff format/check, mypy, repository validator, full pytest and repo coverage >=90% pass where applicable.
- [ ] Exact-head CI and Manufacturer artifact reproducibility pass.

## Expected touch points

- `docs/slices/SLICE-0036-marine-technical-entailment-contract.md`
- `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md`
- `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`
- focused `tests/contract/`
- one small existing `fixtures/technical_profile/` or research-validation artifact
- contract registry/validator only if necessary for declarative validation

Do not modify `BOAT_DESIGN_SCHEMA.v0.6.json`, search runtime, persistence runtime or frontend/API code. If correctness requires one, stop and report.

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

Run focused contract tests added by the slice.

## Stop conditions

Stop and report instead of inventing a solution if:

- safe entailment requires a new schema token/field family or v0.6 modification;
- controlling HullQ artifacts materially contradict one another;
- bounded authoritative evidence contradicts an accepted SLICE-0034 entailment;
- a rule depends on probability/common practice or arbitrary free-text interpretation;
- correct behavior requires recursive/general rule chaining or production inference runtime;
- at least three retained real-design validation cases cannot be supported without a new broad retrieval campaign;
- fulfilling the slice requires search/persistence/API/frontend work.

In ambiguity, `DIRECT_ONLY`/`NO_DERIVATION` is preferred over scope expansion.

## Product guardrail after this slice

After SLICE-0036, do **not** insert another general schema/breadth/governance slice before at least one real BoatDesign is searchable through the existing search kernel, unless exact implementation work discovers a genuine technical blocker requiring an explicit Project Owner decision.

Intended sequence:

`SLICE-0036 -> Oceanis 30.1 practical application -> first real BoatDesign through existing search kernel / minimal local owner-test surface -> API/frontend architecture decision.`

## Status handoff rule

The agent may leave `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark the slice DONE or merge it.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md` exactly and concisely. Also report:

- exact in-scope paths/tokens classified;
- authorized `DEFINITIONAL_ENTAILMENT` rules;
- material `DIRECT_ONLY` / `NO_DERIVATION` decisions;
- authoritative sources used beyond repo controlling artifacts;
- the real-design validation sample and concrete-vs-UNKNOWN outcomes;
- tests proving schema-derived coverage;
- deliberate non-entailments caused by maritime exceptions/definition uncertainty;
- exact final HEAD and exact-head remote gate state.

Do not propose or begin the next slice.