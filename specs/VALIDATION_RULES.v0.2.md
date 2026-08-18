# Validation Rules v0.2

**Status: DRAFT.** These checks operationalize validation examples already present in the project context. They do not replace source evidence.

## Severity

- **error** — physical/logical contradiction; block `verified` status.
- **review** — plausible edge case or taxonomy ambiguity; send to review rather than auto-reject.
- **info** — useful completeness/consistency signal.

## Rules

| ID | Severity | Rule |
|---|---|---|
| VAL-001 | error | If both are known, `lwl_m <= loa_m`. |
| VAL-002 | error | If both are known, `ballast_kg < displacement_kg`. |
| VAL-003 | error | If both are known, `draft_min_m <= draft_max_m`. |
| VAL-004 | error | Canonical dimension, mass, area and capacity fields use the declared SI units. |
| VAL-005 | review | `hull_configuration` and `hull_count` should be mutually consistent. |
| VAL-006 | review | `rudder_type = twin` should be consistent with `rudder_count` where count evidence exists. |
| VAL-007 | review | Keel/rudder/skeg classifications with ambiguous source wording must not be guessed. |
| VAL-008 | error | A derived metric may not be populated without the required base parameters and an approved methodology version. |
| VAL-009 | error | A populated production field must have supporting evidence/provenance. |
| VAL-010 | review | Conflicting authoritative evidence creates a conflict/review state; no silent winner. |
| VAL-011 | review | Detect duplicate model/variant and likely generation ambiguity. |
| VAL-012 | review | Apply multihull-specific consistency checks when bridgedeck, daggerboard, centerboard or multiple rudder fields are used. |
| VAL-013 | info | Flag unusually sparse records for enrichment without inventing missing values. |

## Automated test shape

Every validation rule should eventually have:

- one passing fixture
- one failing/review fixture where applicable
- a stable rule ID in test output
- no mutation of raw evidence during validation

## Identity

### VAL-ID-001 — BoatDesign parent
Every canonical BoatDesign MUST reference exactly one existing BoatModel ID.

### VAL-ID-002 — Local identity IDs
Within one BoatDesign, `NamedVariant.id` and `DesignOption.id` values MUST each be unique in their respective collections.

### VAL-ID-003 — Option references
`requires_option_ids` and `excludes_option_ids` MUST reference DesignOptions available on the same BoatDesign, MUST NOT reference themselves, and MUST NOT contain the same option in both sets.

### VAL-ID-004 — Generation boundaries
Where both `first_built` and `last_built` are known, `first_built <= last_built`. Boundary confidence MUST remain explicit when hull/year boundaries are approximate.

### VAL-ID-005 — Effective configuration compatibility
A ResolvedConfiguration MUST NOT include option selections that violate `requires` / `excludes` constraints or documented applicability boundaries.

### VAL-ID-006 — No inherited-value mutation
Resolving a NamedVariant or DesignOption MUST NOT modify the canonical BoatDesign baseline record. Re-resolving the same canonical inputs MUST produce the same effective result.

### VAL-ID-007 — Unknown precision
An identity resolver MUST NOT promote `model` or `candidate_set` resolution to `design_generation`, `named_variant` or `configuration` without supporting evidence.

## Derived metrics / OQ-001 candidate rules

### VAL-RATIO-001 — Input basis present
A ratio-capable BoatDesign/ResolvedConfiguration MUST expose the accepted displacement and sail-area basis enums; insufficient evidence is represented as `unknown`, not by omission.

### VAL-RATIO-002 — Value/status consistency
A derived metric with status `computed` or `computed_provisional` MUST have a numeric value. Every other status MUST have value `null`.

### VAL-RATIO-003 — Multihull applicability
For `catamaran` or `trimaran`, v1 Ballast/Displacement, Brewer Comfort Ratio, CSF and legacy Hull Speed MUST be `null`/`not_applicable`; SA/D and D/L may be computed when inputs qualify.

### VAL-RATIO-004 — Nonstandard basis
`normal_sailing`/`full_load` displacement MUST NOT populate the single canonical v1 displacement-dependent metric slot. `working_sails_actual`/`downwind` sail-area basis MUST NOT populate canonical SA/D.

### VAL-RATIO-005 — Provisional basis
Permitted calculations from `source_unspecified` or `unknown` basis MUST use `computed_provisional`.

### VAL-RATIO-006 — Canonical precision
Derived numeric outputs MUST conform to the accepted six-decimal round-half-even boundary and golden fixtures.

### VAL-RATIO-007 — Legacy heuristic labeling
`hull_speed_kn`, `comfort_ratio` and `capsize_screening_formula` MUST NOT be used as certified safety/performance limits by downstream product logic.
