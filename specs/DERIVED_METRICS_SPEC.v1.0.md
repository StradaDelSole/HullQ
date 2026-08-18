# HullQ — Derived Ratios / Metrics Specification v1.0

**Status:** ACCEPTED  
**Decision:** OQ-001  
**Methodology version:** `hullq-derived-1.0.0`

## 1. Scope

This specification normatively defines HullQ's first calculation methodology for:

- Sail Area / Displacement (`sa_displ`)
- Ballast / Displacement % (`ballast_displ_pct`)
- Displacement / Length (`displ_length`)
- Brewer Comfort Ratio (`comfort_ratio`)
- Capsize Screening Formula (`capsize_screening_formula`)
- legacy/theoretical Hull Speed estimate (`hull_speed_kn`)

The last item is a derived metric rather than a ratio; the canonical projection is therefore named `derived_metrics`.

## 2. General rules

1. HullQ MUST calculate canonical derived values from canonical/effective base values; a source-published ratio MUST NOT silently become the canonical HullQ value.
2. Calculations MUST use the effective `ResolvedConfiguration` after all accepted NamedVariant and DesignOption overrides.
3. Every populated result MUST identify methodology version `hullq-derived-1.0.0` and MUST be traceable through a `DerivationRecord`.
4. Canonical physical storage remains SI.
5. Historical formulas defined in Imperial units MUST be evaluated after deterministic conversion using Section 4.
6. A derived value MUST be `null` whenever its status is not `computed` or `computed_provisional`.
7. These metrics are comparative indicators. HullQ MUST NOT transform them into an opaque safety, seaworthiness or “bluewater” certification.

## 3. Ratio input basis

Every BoatDesign baseline and every ResolvedConfiguration MUST expose:

```text
ratio_input_basis.displacement_basis
ratio_input_basis.sail_area_basis
```

### 3.1 Displacement basis

Allowed values:

- `design`
- `lightship`
- `normal_sailing`
- `full_load`
- `source_unspecified`
- `unknown`

For v1 canonical displacement-dependent metrics:

- `design` or `lightship` → standard basis;
- `source_unspecified` or `unknown` → calculation may proceed but status MUST be `computed_provisional`;
- `normal_sailing` or `full_load` → canonical v1 metric MUST be `null` with `nonstandard_input`.

### 3.2 Sail-area basis

Allowed values:

- `nominal_main_plus_foretriangle`
- `upwind_100pct`
- `working_sails_actual`
- `downwind`
- `source_unspecified`
- `unknown`

For canonical SA/D:

- `nominal_main_plus_foretriangle` or `upwind_100pct` → standard basis;
- `source_unspecified` or `unknown` → calculation may proceed but MUST be `computed_provisional`;
- `working_sails_actual` or `downwind` → `null` with `nonstandard_input`.

## 4. Unit conversion constants

HullQ MUST use:

```text
METRES_PER_FOOT = 0.3048
KG_PER_POUND = 0.45359237
POUNDS_PER_LONG_TON = 2240
LEGACY_SEAWATER_LB_PER_FT3 = 64
```

Derived conversions:

```text
ft = m / 0.3048
lb = kg / 0.45359237
ft² = m² / (0.3048²)
```

No source-specific conversion constants may override this bundle.

## 5. Formula contracts

### 5.1 HQR-SAD-1.0.0 — Sail Area / Displacement

Required inputs:

- `/effective/dimensions/sail_area_m2` > 0
- `/effective/dimensions/displacement_kg` > 0
- ratio input basis

Formula:

```text
SA_D = sail_area_ft2 / ((displacement_lb / 64) ^ (2/3))
```

Applicability:

- `monohull`, `catamaran`, `trimaran`: applicable;
- `other`, `unknown`: `applicability_unknown`.

Cross-hull-configuration interpretation MUST NOT be implied by HullQ.

### 5.2 HQR-BD-1.0.0 — Ballast / Displacement %

Required inputs:

- `/effective/dimensions/ballast_kg` >= 0
- `/effective/dimensions/displacement_kg` > 0
- displacement basis

Formula:

```text
B_D_pct = 100 * ballast_kg / displacement_kg
```

Applicability:

- `monohull`: applicable;
- `catamaran`, `trimaran`: `not_applicable`;
- `other`, `unknown`: `applicability_unknown`.

If `ballast_kg > displacement_kg`, result MUST be `invalid_input`.

### 5.3 HQR-DL-1.0.0 — Displacement / Length

Required inputs:

- `/effective/dimensions/displacement_kg` > 0
- `/effective/dimensions/lwl_m` > 0
- displacement basis

Formula:

```text
D_L = (displacement_lb / 2240) / ((0.01 * lwl_ft) ^ 3)
```

Applicability:

- `monohull`, `catamaran`, `trimaran`: applicable;
- `other`, `unknown`: `applicability_unknown`.

### 5.4 HQR-CR-1.0.0 — Brewer Comfort Ratio

Required inputs:

- `/effective/dimensions/displacement_kg` > 0
- `/effective/dimensions/lwl_m` > 0
- `/effective/dimensions/loa_m` > 0
- `/effective/dimensions/beam_m` > 0
- displacement basis

Formula:

```text
CR = displacement_lb /
     (0.65 * (0.7*lwl_ft + 0.3*loa_ft) * beam_ft^1.333)
```

The exponent MUST be the literal decimal `1.333` for compatibility with Brewer's published expression.

Applicability:

- `monohull`: applicable;
- `catamaran`, `trimaran`: `not_applicable`;
- `other`, `unknown`: `applicability_unknown`.

HullQ MUST present this as a rough comparative indicator, not an objective comfort guarantee.

### 5.5 HQR-CSF-1.0.0 — Capsize Screening Formula

Required inputs:

- `/effective/dimensions/displacement_kg` > 0
- `/effective/dimensions/beam_m` > 0
- displacement basis

Formula:

```text
CSF = beam_ft / ((displacement_lb / 64) ^ (1/3))
```

Applicability:

- `monohull`: applicable;
- `catamaran`, `trimaran`: `not_applicable`;
- `other`, `unknown`: `applicability_unknown`.

HullQ MUST label this as a legacy screening formula. It MUST NOT be treated as a stability certification or automatically converted into a HullQ “bluewater” classification.

### 5.6 HQM-HS-1.0.0 — Legacy/theoretical Hull Speed

Required input:

- `/effective/dimensions/lwl_m` > 0

Formula:

```text
HullSpeed_kn = 1.34 * sqrt(lwl_ft)
```

Applicability in v1:

- `monohull`: applicable;
- `catamaran`, `trimaran`: `not_applicable`;
- `other`, `unknown`: `applicability_unknown`.

HullQ MUST NOT label this value as a hard maximum speed.

## 6. Result status

Every derived metric MUST have exactly one status:

- `computed`
- `computed_provisional`
- `missing_input`
- `unresolved_input`
- `invalid_input`
- `not_applicable`
- `applicability_unknown`
- `nonstandard_input`

### 6.1 Status precedence

When more than one failure condition exists, use this precedence:

1. `invalid_input`
2. `unresolved_input`
3. `not_applicable`
4. `applicability_unknown`
5. `missing_input`
6. `nonstandard_input`
7. `computed_provisional`
8. `computed`

This precedence exists only to make output deterministic; validation MUST still report all independently detectable input problems.

## 7. Precision, canonical storage and display

1. Computation MUST use at least IEEE-754 binary64 precision.
2. The final numeric result MUST be quantized to 6 decimal places using decimal round-half-even.
3. Canonical search/filter operations MUST use the 6-decimal value, not separately rounded display text.
4. UI/display rounding is non-normative presentation policy and MUST NOT overwrite canonical values.
5. Golden fixtures define the cross-implementation compatibility contract.

## 8. Provenance / derivation

Every `computed` or `computed_provisional` result MUST have a `DerivationRecord` identifying:

- `method_id` from Section 5;
- `methodology_version = hullq-derived-1.0.0`;
- input subject/configuration;
- effective input snapshots;
- ratio-input basis;
- supporting input FieldResolution IDs where available;
- canonical output value.

Externally published ratios may be stored as evidence for comparison but are not authoritative calculations.

## 9. Search semantics boundary

This specification defines calculation status only.

OQ-009 MUST decide whether `computed_provisional`, `missing_input`, `unresolved_input`, `applicability_unknown` and other nonconfirmed states are included, excluded or separately surfaced by technical filters.

## 10. Safety / interpretation guardrail

HullQ MUST NOT:

- imply that a single ratio proves offshore safety;
- generate an opaque “bluewater score” from these metrics without a separately accepted methodology;
- represent Hull Speed as a guaranteed performance ceiling;
- compare monohull-only metrics against multihulls.

## 11. Acceptance evidence

OQ-001 was accepted after:

- the formula and input-basis schemas validated;
- golden fixtures reproduced expected results;
- negative/status fixtures behaved deterministically;
- BoatDesign and ResolvedConfiguration migrations reflected the input-basis and derived-metric semantics;
- requirements and validation rules referenced this methodology.
