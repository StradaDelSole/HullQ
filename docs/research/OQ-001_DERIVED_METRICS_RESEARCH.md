# OQ-001 — Derived Ratio / Metric Methodology Research

**Status:** RESEARCH COMPLETE — OQ-001 DECIDED  
**Date:** 2026-08-18  
**Decision:** OQ-001

## Question

Define HullQ's canonical derived-ratio/metric methodology before any implementation: formulas, input semantics, unit conversions, applicability, missing/invalid-input behavior, versioning, rounding and golden fixtures.

## Key finding: the formulas are not the only decision

The existing fields `displacement_kg` and `sail_area_m2` are not sufficiently self-describing for reproducible ratios. Published yacht data may use lightship, design or loaded displacement, and sail-area figures may mean traditional main + foretriangle, actual working sails or another basis. HullQ therefore needs explicit input-basis metadata before canonical ratios can be treated as comparable.

This is not an optional UI detail. It is part of the calculation contract.

## Primary/official references reviewed

### SRC-RATIO-0001 — Rustler Yachts: “3 useful formulas to help you choose a boat”

- Publisher: Rustler Yachts
- URL: https://www.rustleryachts.com/useful-formulas-to-help-you-choose-a-boat/
- Reviewed: 2026-08-18
- Supports:
  - ballast/displacement ratio is presented for monohulls;
  - D/L uses displacement in long tons divided by `(0.01 × LWL_ft)^3`;
  - SA/D uses sail area in square feet divided by displacement volume in cubic feet raised to `2/3`, with `64 lb/ft³` used for the traditional seawater conversion;
  - load state changes D/L and SA/D;
  - traditional SA/D commonly uses mainsail + foretriangle rather than arbitrary actual headsail area;
  - these ratios are indicators, not complete measures of stability/performance.

### SRC-RATIO-0002 — Ted Brewer Yacht Design

- Publisher/author: Ted Brewer
- URL: https://www.tedbrewer.com/yachtdesign.html
- Reviewed: 2026-08-18
- Supports:
  - Brewer Comfort Ratio formula: `D_lb / (0.65 × (0.7×LWL_ft + 0.3×LOA_ft) × Beam_ft^1.333)`;
  - Brewer describes the measure as a rough/tongue-in-cheek comparison and specifically useful between yachts of similar type;
  - Capsize Screening Formula attributed to the Cruising Club of America technical committee: maximum beam divided by cube root of displacement volume in cubic feet;
  - displacement volume for CSF is obtained using `D_lb / 64`.

### SRC-RATIO-0003 — U.S. Naval Academy naval-engineering course material

- Publisher: U.S. Naval Academy, Department of Naval Architecture and Ocean Engineering
- URL: https://www.usna.edu/NAOE/_files/documents/Courses/EN400/02.07b%20Ch7%20PPT%20Slides.pptx
- Reviewed: 2026-08-18
- Supports:
  - legacy displacement-hull “hull speed” is associated with the point where transverse wavelength equals ship length;
  - conventional speed/length treatment uses the familiar `1.34 × sqrt(length_ft)` knots form.

### SRC-RATIO-0004 — NIST SI conversion guidance

- Publisher: National Institute of Standards and Technology
- URL: https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors
- Reviewed: 2026-08-18
- Supports exact/standard unit-conversion practice used by HullQ when converting canonical SI inputs into the traditional Imperial formula definitions.

## Proposed calculation policy

### Canonical storage

HullQ stores physical source/canonical values in SI. Historical yacht ratios are nevertheless evaluated according to their conventional Imperial definitions after deterministic SI→Imperial conversion. This maximizes compatibility with the established sailing literature while retaining a single SI canonical data model.

Use:

- `1 ft = 0.3048 m`;
- `1 lb = 0.45359237 kg`;
- `1 long ton = 2240 lb`;
- legacy seawater conversion used by SA/D and CSF: `64 lb/ft³`.

### Input basis

Proposed displacement basis enum:

- `design`
- `lightship`
- `normal_sailing`
- `full_load`
- `source_unspecified`
- `unknown`

Proposed sail-area basis enum:

- `nominal_main_plus_foretriangle`
- `upwind_100pct`
- `working_sails_actual`
- `downwind`
- `source_unspecified`
- `unknown`

Canonical ratio policy:

- `design` and `lightship` displacement are accepted reference bases;
- `source_unspecified` / `unknown` may generate a **provisional** result so broad coverage is not destroyed, but the uncertainty remains machine-visible;
- `normal_sailing` / `full_load` are valid physical states but are not mixed into the single canonical HullQ ratio slot in v1; they return `nonstandard_input` unless a future multi-profile ratio specification is added;
- SA/D is standard only for `nominal_main_plus_foretriangle` or `upwind_100pct`;
- `working_sails_actual` and `downwind` are not silently treated as the standard SA/D numerator;
- unknown/unspecified sail-area basis may produce a provisional SA/D, never an unqualified result.

## Proposed formulas

All calculations use effective `ResolvedConfiguration` inputs after NamedVariant/DesignOption resolution.

### HQR-SAD-1.0.0 — Sail Area / Displacement

Required values: `sail_area_m2`, `displacement_kg` plus basis metadata.

After conversion:

`SA_D = sail_area_ft2 / ((displacement_lb / 64) ^ (2/3))`

Applicability:

- monohull: yes;
- catamaran: yes;
- trimaran: yes;
- `other` / `unknown`: applicability remains uncertain.

Interpretation MUST NOT imply direct equivalence between different hull configurations.

### HQR-BD-1.0.0 — Ballast / Displacement %

`B_D_pct = 100 × ballast_kg / displacement_kg`

Applicability:

- monohull only in v1;
- catamaran/trimaran: `not_applicable`;
- other/unknown: `applicability_unknown`.

This ratio MUST NOT be represented as a complete stability measure; ballast location and hull/keel form are not represented.

### HQR-DL-1.0.0 — Displacement / Length

After conversion:

`D_L = (displacement_lb / 2240) / ((0.01 × lwl_ft) ^ 3)`

Applicability:

- monohull, catamaran and trimaran;
- comparisons SHOULD remain within comparable hull families unless a future validated interpretation says otherwise.

### HQR-CR-1.0.0 — Brewer Comfort Ratio

After conversion:

`CR = displacement_lb / (0.65 × (0.7 × lwl_ft + 0.3 × loa_ft) × beam_ft^1.333)`

Important compatibility choice: use exponent **`1.333` exactly as published by Brewer**, rather than silently substituting mathematical `4/3`.

Applicability:

- monohull only in HullQ v1;
- intended as a rough comparative indicator between broadly similar yacht types;
- MUST NOT be exposed as a safety certification or objective “comfort score”.

### HQR-CSF-1.0.0 — Capsize Screening Formula

After conversion:

`CSF = beam_ft / ((displacement_lb / 64) ^ (1/3))`

Applicability:

- monohull only in HullQ v1;
- MUST be labelled as a legacy screening formula, not as proof of offshore safety or compliance with a modern stability standard.

HullQ MUST NOT automatically transform a CSF threshold into a generic “bluewater” certification.

### HQM-HS-1.0.0 — Legacy Hull-Speed Estimate

`HullSpeed_kn = 1.34 × sqrt(lwl_ft)`

This is a derived metric, not a ratio and not a hard maximum speed.

Applicability in HullQ v1:

- monohull only;
- catamaran/trimaran: `not_applicable` because the traditional approximation is too easy to misinterpret for slender multihull forms;
- other/unknown: `applicability_unknown`.

The UI MUST call this a legacy/theoretical hull-speed estimate, not “maximum speed”.

## Output status model

Each metric has a direct numeric value plus a parallel status:

- `computed`
- `computed_provisional`
- `missing_input`
- `unresolved_input`
- `invalid_input`
- `not_applicable`
- `applicability_unknown`
- `nonstandard_input`

`null` therefore never has to mean only one thing.

OQ-009 will later define exactly how provisional/unknown statuses participate in confirmed search matches.

## Precision and determinism

Proposed implementation contract:

1. canonical stored physical inputs remain SI;
2. conversions use the defined exact conversion constants;
3. computation uses at least IEEE-754 binary64 numerical precision;
4. only the final derived value is quantized to **6 decimal places** using decimal round-half-even;
5. UI display precision is presentation policy and MUST NOT alter canonical stored/filter values;
6. re-evaluating identical inputs with the same method version MUST reproduce the same 6-decimal canonical result.

## Missing, conflict and invalid behavior

- Missing required canonical field → value `null`, status `missing_input`.
- Input known to be unresolved/conflicted in FieldResolution → `null`, status `unresolved_input`.
- Zero/negative displacement, zero/negative required length/beam/sail area, ballast > displacement, or equivalent impossible input → `null`, status `invalid_input` and validation signal.
- Known incompatible hull configuration → `null`, status `not_applicable`.
- Hull configuration insufficient to decide applicability → `null`, status `applicability_unknown`.
- Known noncanonical load/sail-area basis → `null`, status `nonstandard_input`.
- Unspecified basis where v1 permits calculation → calculated value plus `computed_provisional`.

## Derived lineage

Each populated derived value MUST create or reference a `DerivationRecord` containing at least:

- subject/configuration ID;
- output field pointer;
- method ID and methodology bundle version;
- effective input values;
- input basis metadata;
- relevant input FieldResolution IDs where available;
- calculated output.

A source-published ratio may be retained as `FieldEvidence` for comparison/QA but MUST NOT replace the HullQ calculation when required base inputs exist.

## Recommendation

Accept the methodology as **HullQ Derived Metrics 1.0.0**, add explicit ratio-input-basis metadata to BoatDesign/ResolvedConfiguration, rename the draft `derived_ratios` projection to the semantically accurate `derived_metrics`, and promote the accompanying schemas/fixtures after approval.
