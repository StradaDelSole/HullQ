# SLICE-0009 — Appendage / Configuration Normalization

**ID:** SLICE-0009  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 2.8 — appendage/configuration hardening  
**Depends on:** SLICE-0008 accepted / DONE  
**Blocks:** SLICE-0010

## Objective

Implement one bounded, deterministic, provenance-safe normalization boundary for explicit sailboat appendage/configuration observations — keel, rudder, skeg, centerboard/daggerboard state/count and hull configuration — using the existing `BOAT_DESIGN_SCHEMA.v0.5` vocabulary without inventing a new taxonomy.

The slice must turn explicit source observations into reviewable normalized configuration candidates while preserving the raw observation and refusing ambiguous inference.

```text
explicit source observation
        ↓
raw FieldEvidence / source semantics retained
        ↓
SLICE-0009 deterministic configuration normalizer
        ↓
exact canonical vocabulary candidate OR explicit unknown/unsupported/review
        ↓
NO automatic FieldResolution / BoatDesign mutation
```

## Why this slice exists

SLICE-0002 established that appendage/configuration depth is the hardest and most irregular part of the sailboat domain. Reviewed real sources show materially different source shapes: manufacturer pages and brochures may use terms such as long keel, fin keel, shoal bulb, lifting keel, centreboard, twin rudder, keel-hung rudder, partial-skeg rudder, or proprietary keel terminology; some configurations are independent factory options rather than one flat model fact.

SLICE-0008 then proved the controlled rights-gated acquisition/provenance path and confirmed that Wikidata is strong for common scalar facts but does not solve HullQ generation/variant/configuration identity or rudder/skeg depth. Therefore this slice hardens the semantic normalization boundary before derived metrics or broad ingestion.

The goal is not to classify arbitrary prose. The goal is to make explicit, source-backed configuration observations deterministic, auditable and safe for later resolution.

## Controlling artifacts

- `specs/BOAT_DESIGN_SCHEMA.v0.5.json` — existing canonical configuration vocabulary and field locations.
- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md` — reviewed appendage/configuration evidence shapes and edge cases.
- `docs/research/SEED_RESEARCH_LOG.md` / related SLICE-0002 seed artifacts where present — difficult-design examples.
- `architecture/decisions/ADR-0004-*` / accepted BoatModel–BoatDesign generation/variant/option identity rules.
- `architecture/decisions/ADR-0006-*` — field-level provenance.
- SLICE-0005 identity contracts.
- SLICE-0006 provenance/raw-observation runtime in `src/hullq/domain/provenance.py`.
- SLICE-0008 Wikidata adapter as the first real evidence producer; do not couple the normalizer to Wikidata.

Existing canonical vocabulary in `BOAT_DESIGN_SCHEMA.v0.5` includes:

- `hull_configuration`: `monohull | catamaran | trimaran | other | unknown`
- `hull_count`: integer/null
- `keel_type`: `full | modified_full | long_fin | fin | wing | bulb | twin | bilge | centerboard | daggerboard | swing | lifting | shoal | other | unknown`
- `keel_subtype`: string/null
- `rudder_type`: `keel_hung | skeg_hung | partial_skeg | spade | transom_hung | twin | other | unknown`
- `rudder_count`: integer/null
- `skeg_type`: `full | partial | none | unknown`
- `daggerboard_count`: integer/null
- `centerboard_count`: integer/null

The slice must normalize **to this vocabulary**, not silently change it. If the vocabulary proves insufficient for a real reviewed case, stop and report the missing semantic instead of extending the schema inside implementation code.

## Core rules

1. **Explicit evidence only.** Normalize only values whose source observation explicitly names or structurally encodes the relevant configuration concept. Do not infer from boat name, designer, era, draft value, image appearance or unrelated free text.
2. **Raw-before-normalized.** Source text/token/structured value remains preserved independently of the normalized candidate.
3. **No fuzzy semantic guessing.** Case, punctuation, whitespace and clearly equivalent spelling variants may be normalized deterministically. Semantic near-matches require an explicit reviewed alias/rule.
4. **Unknown stays unknown.** Unrecognized, conflicting or underspecified observations must produce `unknown`/unsupported/review outcomes, never a guessed canonical type.
5. **Axes remain independent.** Keel type, rudder type/count, skeg type, board type/count and hull configuration are independent dimensions. Do not derive one from another unless the mapping is logically explicit and documented.
6. **Option/state is not baseline fact.** Source observations describing factory options, board-up/board-down states, shallow-draft alternatives, twin-rudder options or named variants must remain option/state scoped and must not overwrite baseline configuration automatically.
7. **No composite-token flattening.** A term such as `shoal bulb keel` may support more than one semantic component only if the rule is explicit and each component has a clear target; otherwise retain the source phrase and route to review.
8. **No source-specific privilege.** Normalization rules are source-agnostic. Source authority/conflict resolution remains outside this slice.
9. **No canonical write.** This slice may create normalized candidates / typed normalization results, but must not create accepted `FieldResolution`, mutate BoatDesign records or persist canonical values.
10. **Deterministic and testable.** Same explicit input + same ruleset version must always produce the same outcome.

## In scope

### 1. Versioned configuration-normalization vocabulary boundary

Add a small runtime module, preferably under `src/hullq/domain/` or another existing domain-normalization location justified by repository structure.

It must expose typed enums/value objects matching the existing canonical schema values rather than duplicating uncontrolled string literals throughout the code.

At minimum cover:

- hull configuration;
- keel type;
- rudder type;
- skeg type;
- rudder count;
- centerboard count;
- daggerboard count.

`keel_subtype` remains a preserved source/detail field and must not become an uncontrolled second taxonomy.

### 2. Explicit normalization input/result contract

Define a small immutable input representing an explicit configuration observation. It must preserve enough semantics for deterministic normalization, for example:

- target configuration field/axis;
- raw value/token;
- optional explicit source qualifier/state such as baseline / option / board-up / board-down when already present in evidence;
- source/evidence identity reference where appropriate.

Define a result that distinguishes at least:

- exact canonical mapping;
- normalized spelling/alias mapping;
- unsupported/unrecognized;
- ambiguous/review-required;
- malformed input.

Do not use confidence scores to hide ambiguity.

### 3. Conservative deterministic alias rules

Implement an explicit, versioned alias table/ruleset for clear lexical equivalents only.

Examples that MAY be safe when represented as exact reviewed rules:

- `fin keel` → `fin`
- `full keel` → `full`
- `full-keel` → `full`
- `modified full keel` → `modified_full`
- `wing keel` → `wing`
- `twin keel` → `twin`
- `bilge keel` / `bilge keels` → `bilge`
- `centerboard` / `centreboard` → `centerboard`
- `daggerboard` → `daggerboard`
- `swing keel` → `swing`
- `lifting keel` / `lift keel` → `lifting`
- `keel hung rudder` / `keel-hung rudder` → `keel_hung`
- `skeg hung rudder` / `skeg-hung rudder` → `skeg_hung`
- `partial skeg` only when the observation explicitly refers to the rudder support → `partial_skeg`
- `spade rudder` → `spade`
- `transom hung rudder` / `transom-hung rudder` → `transom_hung`
- explicit `twin rudders` → rudder type `twin` and, only when count semantics are explicit, rudder count `2`
- explicit `catamaran` / `trimaran` / `monohull` → corresponding hull configuration.

Do not assume every colloquial or manufacturer-specific term belongs in the alias map. Terms such as proprietary keel names, `long keel`, `shoal bulb`, `semi-balanced`, `protected rudder`, or generic `keelboat` must be handled only if their mapping is unambiguous against the existing schema. Otherwise route to review and record why.

### 4. Count normalization

Provide deterministic handling for explicit non-negative integer counts on:

- hull_count;
- rudder_count;
- centerboard_count;
- daggerboard_count.

Rules:

- reject booleans as integers;
- reject negative counts;
- do not parse arbitrary prose such as `two rudders` unless a specific explicit lexical rule is intentionally included and tested;
- do not infer `rudder_count=2` merely because `rudder_type=twin` unless the same observation explicitly encodes twin-count semantics and the rule documents that coupling;
- no impossible cross-field repair logic in this slice.

### 5. Option/state-safe projection

Add a deterministic way to retain whether the normalized observation applies to:

- baseline/common configuration;
- named variant;
- design option;
- state-specific observation such as board-up / board-down where that state is explicitly supplied.

This does not require creating/updating full `NamedVariant` or `DesignOption` records. It requires preventing a non-baseline observation from being silently treated as baseline.

If the existing SLICE-0005 applicability/option primitives already provide an appropriate type, reuse them instead of inventing parallel semantics.

### 6. Provenance-safe candidate creation

Where the existing SLICE-0006 `FieldEvidence` / `NormalizedCandidate` structure is appropriate, provide a deterministic adapter/helper that can attach the normalized categorical/count candidate to the correct configuration JSON Pointer while retaining the raw observation.

Expected canonical target pointers include:

- `/baseline/configuration/hull_configuration`
- `/baseline/configuration/hull_count`
- `/baseline/configuration/keel_type`
- `/baseline/configuration/keel_subtype`
- `/baseline/configuration/rudder_type`
- `/baseline/configuration/rudder_count`
- `/baseline/configuration/skeg_type`
- `/baseline/configuration/daggerboard_count`
- `/baseline/configuration/centerboard_count`

If SLICE-0006 `NormalizedCandidate` is measurement-specific and cannot correctly represent categorical candidates without changing its frozen contract, **stop and report**. Do not force categorical data into a measurement contract. A separate bounded normalization result may be the correct output for this slice.

### 7. Synthetic edge-case fixtures derived from reviewed source shapes

Add repository-safe synthetic fixtures/tests representing the semantic shapes observed during SLICE-0002 research, without copying protected source prose or private boat-list content.

Cover at least these classes of case:

- full/long-keel design with keel-hung rudder;
- fin or bulb/wing/shoal-style explicit keel wording;
- centerboarder with board state kept separate from keel taxonomy;
- lifting/swing keel as explicit option rather than baseline when supplied as option-scoped;
- twin rudders;
- skeg-hung rudder;
- partial-skeg rudder;
- twin rudders with explicit skeg protection where skeg semantics are separately stated;
- catamaran/trimaran hull configuration and explicit hull count;
- proprietary/unknown manufacturer terminology routed to review rather than guessed;
- conflicting explicit observations retained as separate normalization outcomes, not auto-resolved.

## Explicitly out of scope

Do not implement:

- new network acquisition or scraping;
- manufacturer-specific crawlers/adapters;
- Wikidata appendage inference;
- image/diagram classification;
- LLM/free-text semantic classification;
- fuzzy NLP taxonomy inference;
- source authority ranking or conflict resolution;
- accepted FieldResolution generation;
- canonical BoatDesign mutation/persistence;
- automatic NamedVariant/DesignOption construction;
- generation detection;
- measurement/draft-state derivation from appendage type;
- derived metrics (SLICE-0010);
- production database schema;
- FastAPI/frontend/search;
- broad ingestion;
- changing `BOAT_DESIGN_SCHEMA.v0.5` vocabulary unless implementation demonstrates a hard blocking contradiction and stops for master review.

## Required tests

Cover at least:

1. runtime vocabulary exactly matches the relevant `BOAT_DESIGN_SCHEMA.v0.5` enum values.
2. exact canonical values normalize idempotently.
3. case/whitespace/punctuation normalization is deterministic.
4. British/American `centreboard` / `centerboard` equivalence is deterministic.
5. clear keel aliases map correctly.
6. clear rudder aliases map correctly.
7. clear skeg aliases map correctly.
8. unknown/proprietary terms do not map to a guessed canonical value.
9. a term valid for one axis is not silently accepted on another axis.
10. malformed/empty observations are explicit failures.
11. count normalization rejects booleans, negatives and non-integral numbers.
12. explicit count values normalize without prose inference.
13. twin-rudder semantics do not silently imply unrelated skeg/keel facts.
14. option-scoped observation cannot be projected as baseline without explicit caller action.
15. board-up/down state remains separate from board type/count.
16. multiple conflicting observations are not auto-resolved.
17. raw source representation remains available after normalization.
18. deterministic rule/version metadata is emitted.
19. no `FieldResolution` / canonical BoatDesign write occurs.
20. existing SLICE-0003–0008 tests remain green.
21. repository validator, Ruff, format, strict mypy, branch coverage >=90% and dependency audit pass.

## Deliverables

- one bounded appendage/configuration normalization runtime;
- explicit/versioned canonical vocabulary and lexical alias rules;
- typed normalization input/result objects;
- count normalization;
- option/state-safe applicability handling;
- provenance integration only where compatible with accepted SLICE-0006 contracts;
- focused synthetic fixtures/tests based on reviewed semantic edge cases;
- updated slice handoff documentation.

## Expected touch points

Prefer a bounded set such as:

- `src/hullq/domain/configuration.py` or a similarly justified single domain module;
- `tests/unit/test_configuration.py`;
- optional small synthetic fixture file under `fixtures/` if it improves contract readability;
- `docs/slices/SLICE-0009-appendage-configuration-normalization.md`;
- `docs/slices/INDEX.md` and `docs/PROJECT_STATE.md` only for handoff status updates at completion.

Do not modify unrelated adapters, persistence, API or frontend code.

## Validation

Run the repository's established validation gates. At minimum:

```bash
uv run python scripts/validate_repo.py
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/hullq/domain/configuration.py tests/unit/test_configuration.py
uv run coverage run -m pytest tests/unit/ tests/contract/ -q
uv run coverage report
uv run pip-audit
```

If repository commands differ on the current branch, follow the canonical repository configuration rather than weakening a gate.

Normal validation must be offline and deterministic.

## Acceptance criteria

- [ ] existing BoatDesign configuration vocabulary is reused exactly; no hidden second taxonomy is introduced.
- [ ] explicit keel/rudder/skeg/hull/board observations can be normalized deterministically.
- [ ] unknown/proprietary/ambiguous terms fail closed to unsupported/review rather than being guessed.
- [ ] raw source representation remains separate from normalized output.
- [ ] wrong-axis observations cannot silently map.
- [ ] count semantics are strict and deterministic.
- [ ] baseline vs option/variant/state applicability is preserved and cannot silently collapse.
- [ ] synthetic edge cases cover the difficult source shapes identified by SLICE-0002 research.
- [ ] no source acquisition, authority ranking, FieldResolution, canonical BoatDesign write or derived metric is introduced.
- [ ] existing SLICE-0003–0008 behavior remains backward-compatible.
- [ ] repository validator, Ruff, formatting, strict mypy, pytest branch coverage >=90% and dependency audit pass locally.
- [ ] required remote CI is independently observed before owner acceptance.

An implementation agent MUST NOT mark unverified acceptance criteria as passed.

## Stop conditions

Stop and report instead of inventing a solution when:

- a real reviewed appendage/configuration case cannot be represented by the existing `BOAT_DESIGN_SCHEMA.v0.5` vocabulary without semantic distortion;
- categorical normalization would require changing a frozen SLICE-0006 provenance contract;
- option/variant/state semantics conflict with accepted SLICE-0005 identity/applicability rules;
- a proposed alias depends on naval-architecture interpretation rather than explicit lexical equivalence;
- implementation begins to require source-specific scraping, NLP/LLM classification, canonical conflict resolution, persistence or derived metrics;
- accepted artifacts contradict each other materially.

## Status handoff rule

The implementation agent may set `IN_PROGRESS`, `BLOCKED` or `REVIEW` as appropriate, but MUST NOT mark SLICE-0009 `DONE`.

`DONE` requires verified acceptance criteria, required remote checks, independent review and explicit project-owner acceptance under `CLAUDE.md`.

A successful implementation therefore normally hands the slice off in `REVIEW`.

## Required completion report

### Slice

- Slice ID: `SLICE-0009`
- Recommended slice state: `REVIEW` | `BLOCKED`
- Scope completed: `YES` | `NO`

### Changes

- Changed files:
- Requirements implemented:
- Tests/fixtures added or updated:

### Validation

- Local validation: `PASS` | `FAIL` | `PARTIAL`
- Commands run:
- Results:

### External verification

- Remote CI: `PASS` | `FAIL` | `NOT VERIFIED`
- Other external gates: `PASS` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`

### Findings

- Unresolved findings:
- Spec/ADR ambiguities:
- Scope deviations:

### Follow-up

- Recommended next action:

### Agent declaration

- No work outside SLICE-0009 was started.
- No unverified acceptance criterion was marked as passed.
- SLICE-0010 was not started automatically.
- The agent has NOT marked SLICE-0009 `DONE`.
