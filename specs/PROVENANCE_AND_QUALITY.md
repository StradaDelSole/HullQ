# Provenance and Quality

**Status:** ACTIVE semantic baseline; OQ-004 persistence shape accepted.

## Core rule

**No production value without provenance.**

The canonical model requires normalized/queryable values to remain traceable at field level. OQ-004 is `DECIDED`. Canonical BoatDesign values are separated from immutable `FieldEvidence`, versioned `FieldResolution`, and `DerivationRecord` lineage. Field addressing uses RFC 6901 JSON Pointer, e.g. `/baseline/dimensions/loa_m`. See `specs/PROVENANCE_MODEL.v0.1.md` and ADR-0006.

## Source record

Each source should capture at least:

- `source_id`
- title
- publisher/organization
- source type
- URL or document identifier
- publication date if known
- accessed timestamp
- notes

Source rights are governed by accepted OQ-007 / ADR-0005. `specs/SOURCE_SCHEMA.v0.2.json` separates license/rights basis, access conditions, permissions/obligations and use-specific HullQ clearance. See `specs/SOURCE_RIGHTS_POLICY.v0.1.md`.

## Confidence

Allowed record-level confidence:

- `high`
- `medium`
- `low`
- `unknown`

Evidence entries carry their own confidence because one BoatDesign can contain strong and weak fields simultaneously.

## Quality status

- `verified` — required/core values are sufficiently supported and no unresolved blocking conflict exists.
- `partial` — valid record, but important fields remain unknown.
- `needs_review` — evidence/classification needs human review.
- `conflict` — authoritative evidence conflicts and has not been resolved.

## Conflict policy

Never silently resolve conflicting authoritative sources. Retain all conflicting FieldEvidence. Represent the current canonical decision in FieldResolution as `conflict`, `needs_review`, or an auditable `resolved_with_conflict`; do not create a hidden record-level `conflicts[]` source of truth.

## Raw versus normalized values

When normalization changes representation, keep both:

- `raw_value` — what the source actually says
- `normalized_value` — the canonical value used by HullQ

A source-backed canonical field MUST agree with its current active FieldResolution snapshot or be null while unresolved.


## Missing-data semantics

A `null`/unknown field means only that HullQ lacks sufficient supported evidence for that field. It must not be interpreted as `false`, `none`, or any specific categorical value.

Search/indexing logic must preserve three conceptual outcomes for an active criterion:

- supported match;
- supported non-match;
- insufficient data / unknown.

This rule allows broad partial coverage without creating silent false negatives. See `docs/DATABASE_COVERAGE_STRATEGY.md`.
