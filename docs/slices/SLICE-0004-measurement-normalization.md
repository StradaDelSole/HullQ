# SLICE-0004 — Measurement Observation and Deterministic Unit/Basis Normalization

**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 2.3 — deterministic normalization foundation  
**Depends on:** SLICE-0003 accepted / DONE  
**Blocks:** SLICE-0005

## Objective

Implement the smallest pure Python measurement-normalization boundary needed by the real source evidence from SLICE-0002.

This slice converts **explicit numeric values in explicit units** into canonical SI values while preserving the source representation/semantic label and explicit accepted ratio-input basis. It MUST NOT interpret arbitrary manufacturer prose, infer a basis from a free-text label, resolve options/configurations, attach provenance decisions, or perform source acquisition.

The purpose is to make later adapters deterministic: extraction/source-specific parsing may decide that a source observation means `12.3 ft`, but this library owns only the reproducible conversion from that explicit observation into SI.

## Why this slice exists

SLICE-0002 demonstrated that common dimensions are often available, but their representation varies materially:

- mixed metric and imperial values;
- LOA/LWL/beam/draft expressed in metres, centimetres, feet and inches;
- displacement/ballast expressed in kilograms, pounds, tonnes or long tons;
- sail area expressed in square metres or square feet;
- source labels such as `lightship`, `half-load`, `measurement trim`, `EEC light`, `working sails`, `100% foretriangle`, etc.;
- 11/21 researched cases exposed a non-generic displacement/mass basis;
- basis labels cannot be silently flattened to one generic displacement or sail-area meaning.

The accepted ratio methodology already requires machine-visible displacement/sail-area basis. This slice provides deterministic plumbing for values whose unit and accepted basis are already explicit; it does not create a synonym classifier for source prose.

## Controlling artifacts

### Requirements supported

- `REQ-DATA-003` — raw vs normalized evidence must remain auditable;
- `REQ-DATA-005` — canonical physical values use SI where practical;
- `REQ-DATA-008` — sparse/partial records remain valid rather than invented;
- `REQ-RATIO-003` — displacement and sail-area basis remain explicit;
- `REQ-RATIO-004` — unknown/source-unspecified basis remains machine-visible;
- repository quality/toolchain requirements under ADR-0009.

### Specifications and evidence

- `specs/RATIO_INPUT_BASIS_SCHEMA.v0.1.json`;
- `specs/DERIVED_METRICS_SPEC.v1.0.md`;
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json`;
- `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.2.json`;
- `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`;
- `research/benchmark/SEED_RESEARCH_NOTES.md`;
- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`;
- ADR-0008 — derived metric methodology;
- ADR-0009 — Python toolchain.

## Core semantic rule

**Conversion is not interpretation.**

The normalization library MAY convert:

```text
12 ft -> 3.6576 m
2240 lb -> 1016.0469088 kg
100 ft² -> 9.290304 m²
```

It MUST NOT independently decide:

```text
"half-load displacement" -> normal_sailing
"EEC light" -> lightship
"working sails" -> working_sails_actual
"LOA incl. bowsprit" -> canonical hull LOA
```

Those are source-semantic classification decisions requiring explicit evidence/rules/review. Free-text source labels MUST be preservable unchanged.

## In scope

Implement a small pure package boundary under `src/hullq/`, likely `src/hullq/domain/measurements.py` or an equivalently focused location.

### 1. Quantity kinds

Support at least:

- length;
- mass;
- area.

Do not add speed, volume, temperature, pressure or other units in this slice.

### 2. Explicit units

Support deterministic conversion for at least:

**Length**
- metre (`m`);
- centimetre (`cm`);
- millimetre (`mm`);
- foot (`ft`);
- inch (`in`).

**Mass**
- kilogram (`kg`);
- gram (`g`);
- metric tonne (`t` or one canonical internal token chosen by the implementation);
- pound (`lb`);
- long ton (`long_ton`).

**Area**
- square metre (`m2`);
- square foot (`ft2`).

Aliases MAY be accepted only when explicitly enumerated and tested. Do not implement fuzzy unit recognition.

### 3. Exact conversion constants

Use exact/defined relationships consistent with accepted HullQ methodology:

```text
1 ft = 0.3048 m
1 in = 0.0254 m
1 lb = 0.45359237 kg
1 long ton = 2240 lb = 1016.0469088 kg
1 metric tonne = 1000 kg
1 ft² = 0.09290304 m²
```

Do not copy source-published converted values when HullQ can deterministically derive the canonical SI value from an explicit source value/unit.

### 4. Precision behavior

Unit normalization MUST NOT apply the six-decimal final rounding policy used by derived metrics. That rounding belongs to `hullq-derived-1.0.0`, not generic physical-value conversion.

Use a deterministic numeric representation suitable for exact conversion tests. `Decimal` is preferred for the normalization primitive unless implementation evidence shows a conflict with the accepted schema/runtime boundary. Conversion to ordinary JSON numeric values belongs at an explicit projection boundary, not through hidden rounding inside the conversion function.

Reject non-finite numeric input. Do not add field-specific min/max validation here; accepted JSON Schemas/domain rules own whether a specific field may be zero or negative.

### 5. Raw observation preservation

Provide a small immutable value object or equivalent pure representation that can retain at least:

- quantity kind;
- explicit source numeric value;
- explicit source unit;
- optional raw/source text representation;
- optional source semantic label;
- canonical SI value/unit after normalization.

This is an in-memory/domain utility contract, **not a new persistence/provenance schema**. Do not embed Source IDs, FieldEvidence IDs or resolution logic in this slice.

If a raw text string is supplied, preserve it byte-for-byte/string-for-string; normalization MUST NOT rewrite it.

### 6. Ratio-input basis handling

The library may provide typed values/enums for the **already accepted** basis vocabulary in `RATIO_INPUT_BASIS_SCHEMA.v0.1.json`:

Displacement basis:
- `design`;
- `lightship`;
- `normal_sailing`;
- `full_load`;
- `source_unspecified`;
- `unknown`.

Sail-area basis:
- `nominal_main_plus_foretriangle`;
- `upwind_100pct`;
- `working_sails_actual`;
- `downwind`;
- `source_unspecified`;
- `unknown`.

The implementation MUST NOT maintain a second divergent vocabulary. If typed Python enums are introduced, tests MUST prove their values exactly match the normative schema enums.

Basis is supplied explicitly by the caller. **No free-text basis inference/classification is permitted in this slice.**

## Explicitly out of scope

Do not implement:

- parsing arbitrary strings such as `36' 4 1/2\"`, `ca. 7.5 t`, or locale-specific numeric prose;
- manufacturer-label synonym classification;
- automatic mapping of `half-load`, `EEC light`, `unladen`, etc. to accepted ratio basis values;
- LOA-vs-hull-length semantic adjudication;
- draft up/down or shallow/deep option pairing;
- BoatDesign/NamedVariant/DesignOption resolution;
- keel/rudder/skeg/rig normalization;
- source acquisition/HTTP/PDF/HTML parsing;
- provenance/FieldEvidence/FieldResolution behavior;
- persistence, PostgreSQL, ORM or migrations;
- FastAPI/frontend/Contabo/Cloudflare deployment work;
- derived metric formulas or six-decimal metric rounding.

## API shape

Keep the public surface small and explicit. A reasonable conceptual API is:

```python
observation = MeasurementObservation(
    quantity=Quantity.LENGTH,
    value=Decimal("12"),
    unit=LengthUnit.FOOT,
    raw_text="12 ft",
    semantic_label="LOA",
)

normalized = normalize_measurement(observation)
assert normalized.canonical_value == Decimal("3.6576")
assert normalized.canonical_unit == "m"
assert normalized.raw_text == "12 ft"
```

Equivalent naming is acceptable if the semantics remain this small and explicit.

Do not create generic plugin frameworks, registries, parsers or class hierarchies beyond what these three quantity groups need.

## Required tests

Add focused unit/property tests for at least:

1. metre/centimetre/millimetre identity and conversion;
2. foot and inch to metre exactness;
3. kilogram/gram/metric-tonne conversion;
4. pound to kilogram exactness;
5. long-ton to kilogram exactness;
6. square-foot to square-metre exactness;
7. raw text/source semantic label preserved unchanged;
8. quantity/unit mismatch rejected explicitly;
9. unsupported unit rejected explicitly;
10. NaN/infinite/non-finite input rejected;
11. explicit `unknown` and `source_unspecified` bases remain distinct and unchanged;
12. Python displacement-basis vocabulary exactly equals the normative JSON Schema enum if a Python enum is introduced;
13. Python sail-area-basis vocabulary exactly equals the normative JSON Schema enum if a Python enum is introduced;
14. no source-label text causes automatic basis inference;
15. conversion does not apply derived-metric six-decimal rounding.

Use Hypothesis where it adds genuine value, especially for conversion invariants/finite-number behavior, but do not add meaningless property tests merely to increase count.

## Expected touch points

Likely:

- `src/hullq/domain/measurements.py` or a similarly small pure module;
- `src/hullq/domain/__init__.py` only if public exports are useful;
- `tests/unit/test_measurements.py`;
- property tests only if useful;
- this slice and `docs/slices/INDEX.md` for handoff status.

Avoid new dependencies. Python stdlib `decimal`, `dataclasses` and `enum` are sufficient unless a concrete blocker is found.

## Acceptance criteria

- [ ] explicit length/mass/area units normalize deterministically to SI;
- [ ] accepted exact conversion constants are covered by tests;
- [ ] raw source representation and semantic label can be retained unchanged;
- [ ] basis values remain explicit and no free-text inference occurs;
- [ ] `unknown` and `source_unspecified` remain distinct;
- [ ] typed basis vocabulary, if introduced, cannot drift from the normative schema unnoticed;
- [ ] unit/quantity mismatches and unsupported/non-finite inputs fail explicitly;
- [ ] no derived-metric rounding is applied in generic normalization;
- [ ] no source acquisition, identity, appendage, provenance, persistence, API or frontend behavior is introduced;
- [ ] repository validator, Ruff, mypy, pytest/coverage and dependency audit pass locally;
- [ ] required remote CI is reported truthfully and is not guessed.

## Validation

Run at minimum:

```bash
uv lock --check
uv sync --locked --all-groups
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

If formatting is the only failing gate, apply the repository formatter and rerun the relevant full gate set.

## Stop conditions

Stop and report instead of inventing semantics if:

- a required unit/conversion contradicts an accepted HullQ methodology constant;
- the normative ratio-basis vocabulary cannot be represented without changing accepted schema semantics;
- real requirements appear to demand inference from raw manufacturer labels in this slice;
- correct implementation appears to require modifying BoatDesign/ResolvedConfiguration/provenance semantics;
- a new third-party dependency appears necessary;
- scope expands into parsing, source acquisition, configuration/options, persistence, API or frontend.

## Required completion report

Use the exact completion-report structure in `docs/slices/SLICE_TEMPLATE.md`.

Also report:

- final public measurement API;
- supported unit tokens;
- numeric representation/precision choice;
- how raw representation is preserved;
- how schema basis vocabulary is kept aligned;
- any source-semantic mapping intentionally deferred.

Successful implementation hands the slice to `REVIEW`, never `DONE`. Do not begin SLICE-0005.