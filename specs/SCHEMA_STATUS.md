# HullQ — Schema Status Register

**Status:** ACTIVE

This register prevents draft/historical schemas from being mistaken for production contracts.

| Schema | Status | Role | Blockers |
|---|---|---|---|
| `reference/imported/HullQ_BOAT_SCHEMA.v0.1.json` | HISTORICAL | Uploaded original type sketch | Not a production contract |
| `reference/history/BOAT_DESIGN_SCHEMA.v0.2.json` | HISTORICAL | Pre-OQ-003 integrated draft | Superseded for identity semantics |
| `specs/BOAT_MODEL_SCHEMA.v0.1.json` | ACCEPTED | BoatModel identity envelope from OQ-003 | None for identity semantics |
| `reference/history/BOAT_DESIGN_SCHEMA.v0.3.json` | HISTORICAL ACCEPTED | Pre-OQ-001 canonical BoatDesign contract | Superseded by v0.4 |
| `reference/history/RESOLVED_CONFIGURATION_SCHEMA.v0.1-DRAFT.json` | HISTORICAL DRAFT | Pre-OQ-001 ResolvedConfiguration draft | Superseded by accepted v0.2 |
| `reference/history/SOURCE_SCHEMA.v0.1.json` | HISTORICAL | Pre-OQ-007 Source metadata | Superseded by accepted v0.2 |
| `specs/RATIO_INPUT_BASIS_SCHEMA.v0.1.json` | ACCEPTED | Displacement/sail-area calculation-basis contract | None |
| `specs/DERIVED_METRICS_SCHEMA.v1.0.json` | ACCEPTED | Versioned derived-metric values/status projection | None |
| `specs/BOAT_DESIGN_SCHEMA.v0.4.json` | ACCEPTED | Current canonical BoatDesign contract with explicit ratio-input basis | None |
| `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.2.json` | ACCEPTED | Effective configuration + ratio-input basis + derived_metrics | None for domain semantics; persistence implementation remains downstream |
| `specs/SOURCE_SCHEMA.v0.2.json` | ACCEPTED | Structured rights/access/clearance Source contract | None; governed by OQ-007 / ADR-0005 |
| `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json` | ACCEPTED | Immutable source observation per subject field | None |
| `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json` | ACCEPTED | Versioned canonical field decision | None |
| `specs/DERIVATION_RECORD_SCHEMA.v0.1.json` | ACCEPTED | Generic derived-value lineage contract | Ratio method/formula semantics remain OQ-001 |
| `specs/RESEARCH_JOB_SCHEMA.v0.1.json` | DRAFT | Research workflow state | OQ-010 toolchain does not change domain intent |
| `specs/MARKET_LISTING_SCHEMA.v0.1.json` | DRAFT | Canonical listing adapter output | OQ-005 before cross-source dedup semantics |

## Rule

A DRAFT or SUPERSEDED DRAFT schema MUST NOT be treated as a released persistence contract. Accepted semantic specs and ADRs control the next draft revision until all blocking OQs are closed.
