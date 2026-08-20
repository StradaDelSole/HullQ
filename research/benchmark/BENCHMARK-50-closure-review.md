# HullQ Benchmark-50 — Independent Closure Review

**Date:** 2026-08-20  
**Scope:** SLICE-0011 closure review after the 50-design corpus and manual classification were complete

This review does not change the coded 50-design measurements. It checks whether the research artifacts and proposed next boundary are internally consistent with accepted HullQ contracts and the project-owner research policy.

## Measurement verification

`BENCHMARK-50-classification.csv` was independently recounted:

- rows: exactly 50;
- identity / lineage: 30;
- configuration / state: 30;
- measurement / definition basis: 22;
- temporal / production applicability: 32;
- appendage complexity: 42;
- conflict / unresolved: 20;
- authoritative/original-document path: 44;
- material secondary/community/broker dependence: 30;
- reference anomaly/incompleteness/definition issue: 28.

The percentages stated in `BENCHMARK-50-analysis.md` therefore reproduce exactly. They remain stress-corpus incidences, not population prevalence estimates.

## Closure finding 1 — pre-canonical research cannot require FieldEvidence

The first SLICE-0012 draft assumed a `ResearchEvidenceBundle` could simply contain successor `FieldEvidence` records.

That is inconsistent with accepted upstream contracts:

- `ResearchTarget` is deliberately only raw `manufacturer`, `model`, `first_built` input and explicitly does not assert canonical Brand/Organization identity;
- `ResearchJob` does not write canonical BoatDesign identity;
- `FieldEvidence` requires a stable typed `ProvenanceSubject`.

The benchmark itself shows identity/generation ambiguity frequently enough that forcing a canonical subject during web research would recreate the exact under/over-splitting risk HullQ is designed to avoid.

**Correction:** SLICE-0012 now requires:

```text
ResearchTarget
→ pre-canonical ResearchObservation
→ ResearchEvidenceBundle
→ explicit identity resolution outside the bundle contract
→ caller supplies stable ProvenanceSubject
→ deterministic explicit promotion
→ successor FieldEvidence
```

Promotion must not perform fuzzy identity resolution, create FieldResolution or mutate canonical entities.

## Closure finding 2 — reference comparison must be outcome-only

The project-owner policy is stricter than merely saying SailboatData is not canonical provenance: HullQ independently researches the facts first, then uses SailboatData only to check whether conclusions appear to agree or disagree.

Some early narrative Wave 03–06 summaries explained comparison differences by repeating concrete reference values. Those values were never used as HullQ evidence, but retaining them was unnecessary and inconsistent with the intended outcome-only crosscheck rule.

**Correction:** Waves 03–06 were sanitized. Retained reference comparison now records only outcomes/anomaly classes such as:

- match / strong agreement;
- partial match / incomplete option coverage;
- conflict;
- definition/basis difference;
- chronology difference;
- identity/duplicate ambiguity;
- no useful reference record found.

No SailboatData field value is retained in the benchmark summaries or structured observation exports as HullQ research evidence.

## Closure finding 3 — retain the early structured exports, but do not freeze their ad-hoc shape

Waves 01 and 02 produced 58 and 138 structured JSONL observations before a formal `ResearchEvidenceBundle` contract existed. The summaries were in the repository, but the exact exports were initially outside it.

**Correction:** the exact files are now losslessly retained under `research/benchmark/legacy-observations/`, gzip-compressed and Base64 text encoded, with decoded-row counts and SHA-256 hashes.

They are explicitly migration fixtures only:

- not canonical FieldEvidence;
- not the future bundle schema;
- not production data;
- not a reason to preserve either ad-hoc Wave 01/02 key shape.

After SLICE-0012 freezes the successor research-observation/bundle contract, the master/research role can encode the full 50-design corpus into that contract without performing new web research or inventing missing facts.

## Scope review

PR #22 remains documentation/research only. No runtime, schema, test, CI or production source file is modified by SLICE-0011 itself. The SLICE-0012 document is a blocked future implementation contract, not implementation.

The benchmark does **not** authorize:

- PostgreSQL yet;
- broad 1,000+ design ingestion;
- autonomous crawling;
- canonical conflict resolution;
- query/API/frontend/auth work.

## Closure recommendation

After current exact-head CI passes, SLICE-0011 has no remaining research-scope blocker identified by this review.

The correct next sequence remains:

```text
SLICE-0011 acceptance / merge
→ SLICE-0012 pre-canonical ResearchObservation + claim/applicability + ResearchEvidenceBundle + explicit promotion
→ PostgreSQL persistence/import slice
→ run the same benchmark through importer/DB
→ measure actual automation/review/idempotency/cost
→ only then consider broad bootstrap
```
