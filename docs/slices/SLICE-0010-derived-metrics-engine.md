# SLICE-0010 — Derived Metrics Engine

**ID:** SLICE-0010  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 2.9 — deterministic derived-metrics runtime  
**Depends on:** SLICE-0009 accepted / DONE  
**Blocks:** controlled Stage-2 benchmark work

## Objective

Implement HullQ methodology `hullq-derived-1.0.0` as one bounded, deterministic, provenance-aware runtime for the six accepted derived yacht metrics, consuming explicit effective configuration inputs and emitting exact schema-compatible values/statuses plus DerivationRecord lineage for populated results.

```text
resolved/effective input snapshot
        +
unresolved-field markers / resolution IDs where available
        ↓
SLICE-0010 deterministic metric engine
        ↓
per-metric validation + applicability + status precedence
        ↓
formula evaluation using accepted constants
        ↓
6-decimal round-half-even canonical value OR null
        ↓
DerivedMetrics projection + DerivationRecord(s)
        ↓
NO search semantics / safety score / persistence
```

The objective is implementation of the already accepted methodology, not new formula research or a redesign of the metric model.

## Why this slice exists

OQ-001 / ADR-0008 already froze HullQ's first derived-metric methodology, including formulas, input-basis semantics, hull-type applicability, deterministic status precedence, precision, rounding and lineage requirements. Golden and negative/status fixtures already exist under `fixtures/ratios/`.

SLICE-0004 established deterministic physical measurement normalization; SLICE-0006 established FieldResolution/DerivationRecord provenance contracts; SLICE-0009 hardened configuration semantics so hull configuration is not inferred casually. The prerequisites for executing the accepted formulas are therefore now present.

HullQ still does not have a full runtime that builds every ResolvedConfiguration from BoatDesign + NamedVariant + DesignOption records. This slice MUST NOT expand into that separate problem. It may consume a small explicit effective-input snapshot corresponding to the accepted `/effective/...` fields and unresolved-input markers. The computation boundary must remain usable later by a full ResolvedConfiguration builder.

## Controlling artifacts

- `architecture/decisions/ADR-0008-derived-metric-methodology.md` — accepted OQ-001 decision.
- `specs/DERIVED_METRICS_SPEC.v1.0.md` — normative formulas/status/applicability/rounding rules.
- `specs/DERIVED_METRICS_SCHEMA.v1.0.json` — canonical output projection contract.
- `specs/RATIO_INPUT_BASIS_SCHEMA.v0.1.json` — accepted displacement/sail-area basis vocabularies.
- `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.2.json` — canonical `/effective` input locations and `derived_metrics` projection.
- `specs/DERIVATION_RECORD_SCHEMA.v0.1.json` — required lineage shape.
- `specs/REQUIREMENTS.md`:
  - `REQ-RATIO-001` internal calculation;
  - `REQ-RATIO-002` versioned methodology;
  - `REQ-RATIO-003` explicit calculation basis;
  - `REQ-RATIO-004` provisional uncertainty;
  - `REQ-RATIO-005` hull-configuration applicability;
  - `REQ-RATIO-006` deterministic canonical precision;
  - `REQ-RATIO-007` derived lineage;
  - `REQ-RATIO-008` no safety-score implication;
  - `REQ-PROV-006` derived values use DerivationRecord lineage.
- `fixtures/ratios/golden_metrics.v0.1.json` — accepted numeric compatibility fixtures.
- `fixtures/ratios/status_cases.v0.2.json` — accepted negative/status fixtures.
- `fixtures/provenance/valid/derivation_configuration.json` — accepted DerivationRecord shape example.
- SLICE-0006 provenance runtime and SLICE-0009 configuration runtime are reusable boundaries but MUST NOT be redesigned here.

## Normative methodology

Methodology version is exactly:

```text
hullq-derived-1.0.0
```

The six canonical outputs are:

1. `sa_displ` — HQR-SAD-1.0.0
2. `ballast_displ_pct` — HQR-BD-1.0.0
3. `displ_length` — HQR-DL-1.0.0
4. `comfort_ratio` — HQR-CR-1.0.0
5. `capsize_screening_formula` — HQR-CSF-1.0.0
6. `hull_speed_kn` — HQM-HS-1.0.0

Accepted conversion constants MUST be used exactly:

```text
METRES_PER_FOOT = 0.3048
KG_PER_POUND = 0.45359237
POUNDS_PER_LONG_TON = 2240
LEGACY_SEAWATER_LB_PER_FT3 = 64
```

No source-specific constants or alternate formula variants are permitted in this slice.

## Core rules

1. **Accepted formulas only.** Do not reinterpret, modernize or substitute formulas.
2. **Effective inputs only.** The engine receives explicit effective/canonical inputs; it does not choose between conflicting source observations.
3. **Unresolved is explicit.** A required field marked unresolved must participate in status evaluation as `unresolved_input` even if a stale/snapshot numeric value is also present.
4. **All detectable problems matter.** Status precedence determines the emitted status, but diagnostics should retain all independently detectable input problems where a bounded result type can do so without changing the canonical schema.
5. **Null unless computed.** Canonical metric value MUST be null unless status is `computed` or `computed_provisional`.
6. **Basis semantics are normative.** `normal_sailing` / `full_load` displacement and `working_sails_actual` / `downwind` sail-area basis do not populate the single canonical v1 slots.
7. **Hull applicability is normative.** Do not calculate monohull-only metrics for known catamarans/trimarans merely because the arithmetic is possible.
8. **Unknown is not applicability.** Hull configuration `other` / `unknown` produces `applicability_unknown` where specified.
9. **Precision is canonical.** Final populated values are quantized to exactly six decimal places with decimal round-half-even semantics.
10. **Lineage, not fake evidence.** HullQ-calculated metrics produce DerivationRecord lineage and MUST NOT create FieldEvidence pretending the metric came directly from a source.
11. **No safety inference.** The engine returns formulas/statuses only. No bluewater score, seaworthiness score, stability certificate, comfort guarantee or performance ceiling classification.
12. **Pure/deterministic core.** The same input snapshot, unresolved markers and methodology version produce the same metric values/statuses. Runtime clock/ID generation must not be hidden inside the formula core.

## In scope

### 1. Typed effective input snapshot

Add the smallest immutable input/value-object boundary needed to compute the methodology without implementing full configuration inheritance/resolution.

It should represent at least:

- resolved configuration identity / target ID supplied by the caller;
- `hull_configuration`;
- effective `loa_m`;
- effective `lwl_m`;
- effective `beam_m`;
- effective `displacement_kg`;
- effective `ballast_kg`;
- effective `sail_area_m2`;
- `displacement_basis`;
- `sail_area_basis`;
- explicit unresolved field pointers;
- optional current FieldResolution IDs keyed by effective input field pointer where available.

Canonical effective pointers are the accepted `RESOLVED_CONFIGURATION_SCHEMA.v0.2` locations, e.g.:

- `/effective/dimensions/loa_m`
- `/effective/dimensions/lwl_m`
- `/effective/dimensions/beam_m`
- `/effective/dimensions/displacement_kg`
- `/effective/dimensions/ballast_kg`
- `/effective/dimensions/sail_area_m2`
- `/effective/configuration/hull_configuration`
- `/effective/ratio_input_basis/displacement_basis`
- `/effective/ratio_input_basis/sail_area_basis`

The input snapshot must be caller-mutation safe if it contains mutable collections.

Do not implement BoatDesign + NamedVariant + DesignOption merge logic in this slice.

### 2. Metric result/status runtime

Expose typed status vocabulary matching `DERIVED_METRICS_SCHEMA.v1.0.json` exactly:

- `computed`
- `computed_provisional`
- `missing_input`
- `unresolved_input`
- `invalid_input`
- `not_applicable`
- `applicability_unknown`
- `nonstandard_input`

Implement per-metric evaluation that retains at least:

- metric key;
- canonical value or null;
- status;
- methodology/method ID;
- bounded diagnostic/problem information useful for tests/audit.

Provide a deterministic projection matching `DERIVED_METRICS_SCHEMA.v1.0.json`:

```text
methodology_version
six numeric-or-null metric fields
status object with six statuses
```

Do not add fields to the canonical projection that are not allowed by the schema.

### 3. Exact formula implementation

Implement the formulas exactly as specified.

#### SA/D

```text
sail_area_ft2 / ((displacement_lb / 64) ^ (2/3))
```

Inputs: sail area > 0, displacement > 0, displacement basis, sail-area basis. Applicable to monohull/catamaran/trimaran; `other`/`unknown` → applicability_unknown.

#### Ballast / Displacement %

```text
100 * ballast_kg / displacement_kg
```

Inputs: ballast >= 0, displacement > 0, displacement basis. Monohull only. `ballast_kg > displacement_kg` → invalid_input.

#### Displacement / Length

```text
(displacement_lb / 2240) / ((0.01 * lwl_ft) ^ 3)
```

Inputs: displacement > 0, LWL > 0, displacement basis. Applicable to mono/cat/tri.

#### Brewer Comfort Ratio

```text
displacement_lb /
(0.65 * (0.7*lwl_ft + 0.3*loa_ft) * beam_ft^1.333)
```

The exponent MUST be literal decimal `1.333`. Monohull only.

#### Capsize Screening Formula

```text
beam_ft / ((displacement_lb / 64) ^ (1/3))
```

Monohull only.

#### Legacy Hull Speed

```text
1.34 * sqrt(lwl_ft)
```

Monohull only in v1. No displacement/sail-area basis dependency.

### 4. Deterministic status precedence

Implement the accepted precedence exactly:

1. `invalid_input`
2. `unresolved_input`
3. `not_applicable`
4. `applicability_unknown`
5. `missing_input`
6. `nonstandard_input`
7. `computed_provisional`
8. `computed`

Each metric must independently evaluate its own required inputs and applicability.

Examples of required behavior:

- missing sail area blocks SA/D but not Hull Speed;
- unresolved displacement blocks displacement-dependent metrics but not Hull Speed;
- displacement 0 is invalid and outranks an unresolved marker on the same metric;
- catamaran monohull-only metric → `not_applicable` even when another required formula input is missing, unless a higher-priority invalid/unresolved condition exists;
- unknown hull configuration → `applicability_unknown` where the methodology says so;
- nonstandard input basis returns null;
- unknown/source-unspecified allowed basis yields a numeric provisional value where otherwise computable.

### 5. Basis handling

Displacement basis:

- `design`, `lightship` → standard;
- `source_unspecified`, `unknown` → provisional where the metric depends on displacement basis;
- `normal_sailing`, `full_load` → nonstandard_input.

Sail-area basis for SA/D:

- `nominal_main_plus_foretriangle`, `upwind_100pct` → standard;
- `source_unspecified`, `unknown` → provisional;
- `working_sails_actual`, `downwind` → nonstandard_input.

Hull Speed remains independent of both basis fields.

### 6. Numeric validation and quantization

Before formula evaluation, required numeric inputs must be finite, non-boolean real numbers with the required sign constraints.

At minimum:

- displacement > 0 where required;
- LOA/LWL/beam > 0 where required;
- sail area > 0 for SA/D;
- ballast >= 0 for B/D;
- ballast > displacement invalidates B/D only.

Do not accept NaN or infinity as valid canonical inputs.

Final populated values MUST be quantized to six decimal places using decimal round-half-even. Golden fixtures are the compatibility authority for implementation behavior.

Do not apply separate display rounding in this slice.

### 7. DerivationRecord lineage

For every metric with status `computed` or `computed_provisional`, produce a schema-valid DerivationRecord-equivalent lineage record under `DERIVATION_RECORD_SCHEMA.v0.1.json`.

Required lineage semantics:

- target kind `resolved_configuration` for this slice's effective-input boundary;
- target ID supplied by caller;
- target field pointer under `/derived_metrics/<metric_key>`;
- method ID exactly the metric's accepted formula ID;
- method version/methodology version consistent with `hullq-derived-1.0.0`;
- input entries for every effective field that actually affects formula, applicability or basis status;
- input `value_snapshot` preserved;
- matching FieldResolution ID included where caller supplied one, otherwise null;
- output value snapshot equals the canonical six-decimal value;
- producer kind `deterministic_tool`;
- generated timestamp and derivation IDs supplied explicitly by caller/context or another deterministic testable boundary — do not hide `now()` or random UUID generation inside formula evaluation.

No derivation record is required for metrics that do not produce a value.

Do not create source FieldEvidence for the derived output.

### 8. Existing fixtures are normative tests

The implementation must execute the existing checked-in fixtures rather than duplicating them into hand-coded expected values.

`fixtures/ratios/golden_metrics.v0.1.json` must match exactly, including:

- standard monohull values;
- catamaran applicability split;
- provisional basis case;
- Rustler D/L compatibility case.

`fixtures/ratios/status_cases.v0.2.json` must match exact expected statuses/values for each stated metric.

Additional focused tests are required for uncovered precedence and numeric-boundary cases.

## Explicitly out of scope

Do not implement:

- full ResolvedConfiguration inheritance/override construction;
- automatic NamedVariant/DesignOption selection;
- FieldResolution conflict resolution;
- source authority ranking;
- new source/network acquisition;
- Wikidata changes;
- appendage taxonomy changes;
- BoatDesign or ResolvedConfiguration persistence;
- PostgreSQL;
- background workers/scheduling;
- query/search semantics under OQ-009;
- filtering on computed/provisional statuses;
- API/FastAPI;
- frontend/display rounding;
- opaque composite scoring;
- “bluewater”, seaworthiness, stability, comfort or performance certification;
- alternate/custom metric formulas;
- source-published ratios becoming canonical HullQ calculations.

## Required tests

Cover at least:

1. runtime methodology version is exactly `hullq-derived-1.0.0`.
2. status vocabulary exactly matches `DERIVED_METRICS_SCHEMA.v1.0.json`.
3. input-basis vocabularies exactly match `RATIO_INPUT_BASIS_SCHEMA.v0.1.json` or reuse an existing contract boundary without drift.
4. all six formula IDs are stable and exact.
5. accepted conversion constants are exact.
6. every case in `golden_metrics.v0.1.json` reproduces expected six-decimal values/statuses.
7. every assertion in `status_cases.v0.2.json` reproduces expected value/status.
8. monohull standard case computes all six values.
9. catamaran/trimaran compute only the metrics permitted by v1 applicability.
10. `other`/`unknown` hull configuration produces applicability_unknown where required.
11. provisional displacement basis affects only metrics depending on that basis.
12. provisional sail-area basis affects SA/D only.
13. nonstandard displacement basis nulls displacement-dependent canonical metrics but not Hull Speed.
14. nonstandard sail-area basis nulls SA/D only.
15. missing input affects only metrics requiring that input.
16. unresolved input affects only metrics requiring that input.
17. status precedence is exact, including invalid > unresolved and applicability > missing/nonstandard where applicable.
18. zero/negative/non-finite required values are invalid, not computed.
19. ballast > displacement invalidates B/D only.
20. booleans are not accepted as numeric canonical inputs.
21. final canonical values use six-decimal round-half-even and repeated runs are identical.
22. canonical projection validates against `DERIVED_METRICS_SCHEMA.v1.0.json` using the existing contract runtime.
23. every populated metric produces one matching schema-valid DerivationRecord.
24. derivation target pointer, method ID/version, inputs, resolution IDs and output snapshot are correct.
25. no derivation record is fabricated for null/noncomputed metrics.
26. derived outputs create no FieldEvidence.
27. mutable caller-owned unresolved/resolution-ID collections cannot mutate an already-created input snapshot.
28. no search/filter/safety-score semantics are introduced.
29. existing SLICE-0003–0009 tests remain green.
30. repository validator, Ruff, formatting, strict mypy, pytest branch coverage >=90% and dependency audit pass.

## Deliverables

- one bounded derived-metrics runtime, preferably under `src/hullq/domain/`;
- typed effective-input, metric-result and status primitives;
- six accepted formula implementations;
- deterministic status-precedence/basis/applicability handling;
- canonical `DerivedMetrics` projection helper;
- deterministic DerivationRecord lineage helper/boundary;
- fixture-driven unit/contract tests;
- updated SLICE-0010 handoff documentation.

## Expected touch points

Prefer a bounded set such as:

- `src/hullq/domain/derived_metrics.py`;
- `tests/unit/test_derived_metrics.py`;
- `tests/contract/test_derived_metrics_contract.py` only if useful for existing schema validation;
- existing `fixtures/ratios/` should normally be consumed unchanged; modify them only if an accepted artifact is internally contradictory and stop/report first;
- `docs/slices/SLICE-0010-derived-metrics-engine.md`;
- `docs/slices/INDEX.md` and `docs/PROJECT_STATE.md` only for normal handoff status updates.

Avoid modifying `measurements.py`, `configuration.py`, `provenance.py` or frozen schemas unless a hard accepted-contract contradiction is found. If such a contradiction appears, stop for master review rather than silently changing foundations.

## Validation

Use the repository's current canonical commands. At minimum:

```bash
uv run python scripts/validate_repository.py
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/hullq/domain/derived_metrics.py tests/unit/test_derived_metrics.py
uv run coverage run -m pytest tests/unit/ tests/contract/ -q
uv run coverage report
uv run pip-audit
```

If additional SLICE-0010 files are created, include them in the strict mypy boundary.

Normal validation is deterministic and offline.

## Acceptance criteria

- [ ] all six accepted formulas are implemented exactly under `hullq-derived-1.0.0`.
- [ ] accepted unit constants, applicability, basis rules and status precedence are implemented without alternate semantics.
- [ ] existing golden fixtures reproduce exactly at the six-decimal canonical boundary.
- [ ] existing status fixtures reproduce exactly.
- [ ] noncomputed statuses always emit null canonical values.
- [ ] provisional results remain machine-visible and numeric only when permitted.
- [ ] invalid/unresolved/missing/nonstandard/applicability conditions are deterministic and metric-local.
- [ ] canonical projection validates against `DERIVED_METRICS_SCHEMA.v1.0.json`.
- [ ] every populated result has schema-valid DerivationRecord lineage with correct formula/input snapshots.
- [ ] no calculated output is represented as direct source FieldEvidence.
- [ ] mutable caller inputs are snapshot-safe.
- [ ] no configuration resolver, persistence, query semantics, API/frontend or safety-score behavior is introduced.
- [ ] existing SLICE-0003–0009 behavior remains backward-compatible.
- [ ] repository validator, Ruff, formatting, strict mypy, pytest branch coverage >=90% and dependency audit pass locally.
- [ ] required remote CI is independently observed before owner acceptance.

An implementation agent MUST NOT mark unverified acceptance criteria as passed.

## Stop conditions

Stop and report instead of inventing a solution when:

- an accepted golden/status fixture contradicts `DERIVED_METRICS_SPEC.v1.0.md` materially;
- the accepted schema cannot represent a required normative result without modification;
- implementing lineage would require changing the frozen DerivationRecord schema rather than using its existing fields;
- a required effective-input semantic depends on unimplemented option/configuration resolution rather than a caller-supplied snapshot;
- formula behavior would require choosing an alternate historical definition not present in the accepted spec;
- implementation begins to decide OQ-009 search semantics or infer safety/seaworthiness classifications;
- accepted artifacts contradict each other materially.

## Status handoff rule

The implementation agent may set `IN_PROGRESS`, `BLOCKED` or `REVIEW` as appropriate, but MUST NOT mark SLICE-0010 `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review and explicit project-owner acceptance under `CLAUDE.md`.

A successful implementation therefore normally hands the slice off in `REVIEW`.

## Required completion report

### Slice

- Slice ID: `SLICE-0010`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`

### Changes

- Changed files:
  - `src/hullq/domain/derived_metrics.py` — new: bounded derived-metrics engine
  - `tests/unit/test_derived_metrics.py` — new: 107 unit tests
  - `tests/contract/test_derived_metrics_contract.py` — new: 16 contract/schema tests
  - `docs/slices/SLICE-0010-derived-metrics-engine.md` — status update and completion report
  - `docs/slices/INDEX.md` — status updated to REVIEW
  - `docs/PROJECT_STATE.md` — SLICE-0010 section updated

- Requirements implemented:
  - REQ-RATIO-001 through REQ-RATIO-008 (internal calculation, versioned methodology, explicit basis, provisional uncertainty, hull applicability, canonical precision, derived lineage, no safety inference)
  - REQ-PROV-006 (derived values use DerivationRecord lineage)

- Tests/fixtures added or updated:
  - `tests/unit/test_derived_metrics.py` — 107 new tests covering all required scenarios
  - `tests/contract/test_derived_metrics_contract.py` — 16 new contract tests validating against schemas
  - Existing fixtures `golden_metrics.v0.1.json` and `status_cases.v0.2.json` consumed unchanged

### Validation

- Local validation: `PASS`
- Commands run:
  ```
  uv run python scripts/validate_repository.py
  uv run ruff check src/ tests/
  uv run ruff format --check src/ tests/
  uv run mypy src/hullq/domain/derived_metrics.py tests/unit/test_derived_metrics.py tests/contract/test_derived_metrics_contract.py
  uv run coverage run -m pytest tests/unit/ tests/contract/ -q
  uv run coverage report
  uv run pip-audit
  ```
- Results:
  - repository validator: PASS (22 schemas, 88 requirements, 88 acceptance criteria)
  - Ruff check: All checks passed
  - Ruff format: 35 files formatted/already formatted
  - mypy: clean (no output = no errors)
  - pytest: 915 passed (792 prior + 123 new) in ~25s
  - coverage total: 92.62% branch; derived_metrics.py: 99.50% branch
  - pip-audit: No known vulnerabilities found

### External verification

- Remote CI: `NOT VERIFIED` — branch pushed to GitHub; CI run not yet observed
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings: none
- Spec/ADR ambiguities: none encountered; all golden/status fixtures reproduced exactly
- Scope deviations: none — full ResolvedConfiguration resolution, persistence, API, search semantics, safety scoring explicitly not implemented per slice boundary

### Follow-up

- Recommended next action: push branch to GitHub, verify CI pass, then owner may accept or request review amendments

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.
