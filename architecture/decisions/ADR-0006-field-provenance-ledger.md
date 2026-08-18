# ADR-0006 — Separate Field Provenance Ledger

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Decision:** OQ-004

## Context

HullQ needs field-level traceability while keeping BoatDesign and related domain objects efficient for broad technical search. Earlier drafts embedded evidence inside BoatDesign records and used project-specific dot-path field addressing.

The identity model now also introduces stable BoatModel, BoatDesign, NamedVariant and DesignOption subjects, while ResolvedConfiguration and ratios are derived rather than direct source facts.

## Decision

Adopt a persistence-agnostic separate provenance ledger consisting of:

1. immutable `FieldEvidence` source observations;
2. versioned `FieldResolution` canonical decisions;
3. `DerivationRecord` lineage for calculated/inherited values.

Canonical domain values remain plain searchable values.

Use RFC 6901 JSON Pointer for field addressing relative to a stable subject ID. Do not use array positions as persistent identity for NamedVariants/DesignOptions.

Do not implement the complete W3C PROV ontology; retain only compatible Entity/Activity/Agent concepts in HullQ's domain-specific contracts.

## Consequences

### Positive

- canonical query records stay compact;
- one source may support many fields without duplicating source metadata;
- reverse source-impact lookup is efficient to model;
- conflicts and adjudication history remain visible;
- source-backed evidence is distinct from calculated lineage;
- database technology remains open until OQ-012.

### Negative

- provenance-rich reads require joins/lookups;
- persistence must enforce canonical-value ↔ active-resolution consistency;
- append-oriented history increases provenance-row count.

## Rejected alternatives

- per-field `{value,evidence}` wrappers;
- canonical embedded `evidence[]` ledger inside every BoatDesign.

Both may be used as read/export projections but not as canonical persistence.

## Acceptance evidence

The decision was explicitly accepted on 2026-08-18. At acceptance:

- the FieldEvidence, FieldResolution and DerivationRecord schemas validated under JSON Schema Draft 2020-12;
- representative positive and negative fixtures behaved as intended;
- BoatDesign v0.3 was reconciled so canonical search records do not embed redundant source lists;
- Open Questions, requirements, schema status and project state were updated to the accepted persistence semantics.
