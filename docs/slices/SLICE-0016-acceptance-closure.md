# SLICE-0016 — Acceptance Closure

**ID:** SLICE-0016  
**Final status:** DONE  
**Accepted:** 2026-08-21  
**Implementation PR:** #33  
**Accepted implementation head:** `61b500c2de061abb09dd7ddc36a0bfaa724ceece`  
**Merge commit:** `ae34363f5db8111a75d108b9b936084f76b56cef`

## Acceptance result

SLICE-0016 is explicitly accepted by the project owner and closed as `DONE`.

The slice establishes the missing Stage-3 canonical Tier-0 identity persistence/admission boundary on PostgreSQL 18 for Brand, Organization, BoatModel, BoatDesign, aliases, Brand↔BoatModel relationships, Organization↔BoatDesign relationships and auditable links to retained HullQ observations/evidence.

It does not perform identity resolution from source candidates and did not run the ~1,000-design bootstrap.

## Final accepted evidence

Exact accepted head:

`61b500c2de061abb09dd7ddc36a0bfaa724ceece`

GitHub Actions CI run **#195** (`32478124648`) passed on that exact head.

Verified CI evidence:

- PostgreSQL **18.6** integration: PASS;
- persistence suite: **199 passed**;
- benchmark runner: PASS;
- benchmark result-schema validation: PASS;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS.

The retained Stage-2 benchmark remained unchanged and clean on the accepted SLICE-0016 head:

- 50/50 materialized;
- 50/50 first-pass imported;
- 0 first-pass conflicts/errors;
- 0 semantic readback mismatches;
- 50/50 exact re-import `ALREADY_IMPORTED`;
- 0 re-import conflicts/errors;
- 50/50 fresh-schema imported;
- 0 fresh-schema semantic mismatches/errors;
- recommendation: `G3_PASS`;
- result-schema validation: PASS.

Exact-head benchmark artifact:

- artifact ID: `9445058966`;
- digest: `sha256:03a190278d9591879d3e3dfd8e7ec6b3c1d51b0c40bfaee843f3ce0eef7ebdc6`.

Implementation-agent final local report:

- **1354 passed, 201 skipped**;
- branch coverage: **94.31%**;
- Ruff format/lint: PASS;
- strict mypy: PASS;
- repository validator: PASS.

Real PostgreSQL tests were not available locally to the agent because local credentials were unavailable; this was reported honestly and was then independently verified by exact-head CI against PostgreSQL 18.6.

## Independent-review hardening retained

The first review found three blockers. All were corrected before acceptance:

1. the genuine 001→002 upgrade test now cleans up in valid FK dependency order without weakening production referential integrity;
2. every `CanonicalEvidenceLink` now fails closed unless `(entity_kind, entity_id)` addresses a real canonical entity/relationship of the exact kind, including same-transaction targets and rollback behavior;
3. caller-supplied `BoatModel.boat_design_ids` remains a normalized derived projection but is now checked order-independently against the actual canonical BoatDesign graph and fails closed on missing/extra/misattributed designs.

The exact-head PostgreSQL integration suite proves these negative paths, including wrong-kind targets, nonexistent targets, same-admission entity/relationship targets, full-admission rollback, BoatModel/BoatDesign graph consistency and concurrent exact/conflicting admissions.

## Accepted boundary carried forward

SLICE-0016 deliberately starts at an **already-admitted canonical payload** boundary.

It does not decide whether arbitrary source candidates are the same real HullQ identity. It does not:

- fuzzy-match identities;
- mint canonical IDs from names/source IDs inside persistence;
- infer Brand from Organization or Organization from Brand;
- infer BoatDesign generations from source labels;
- automatically promote ResearchObservation/FieldEvidence into canonical entities;
- run broad ingestion.

Those decisions remain explicit concerns of the controlled bootstrap layer.

## Next boundary

The next bounded step is:

`SLICE-0017 — Controlled Wikidata Tier-0 Identity Bootstrap`

Its purpose is to process the first approximately 1,000 rights-cleared direct sailboat-class candidates through a reproducible bootstrap manifest and the accepted canonical admission boundary, while preserving ambiguity instead of inventing Brand/Organization/BoatDesign specificity.

No 2,500/5,000 expansion, technical-enrichment pass, query-engine work or later product work is authorized merely by closing SLICE-0016.