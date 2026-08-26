# SLICE-0026 — Acceptance Closure

**ID:** SLICE-0026  
**Final status:** DONE  
**Owner accepted:** 2026-08-26  
**Independent-review verdict:** ACCEPT after three amendment rounds  
**Implementation PR:** #73 — "SLICE-0026: bounded Wikidata Tier-1 enrichment evidence pilot"  
**Final reviewed / accepted implementation head:** `370e4edc6b0642a70829b29bc8cb3c2b1a4a5e30`  
**Implementation merge commit:** `db18179f9327612275cf38b22d593940717f0683`  
**Exact-head PR CI:** run `32994651623`, SUCCESS  
**Exact-head PR manufacturer reproducibility:** run `32994650994`, SUCCESS

## Acceptance result

The project owner accepts the independently reviewed SLICE-0026 implementation and closes the slice as `DONE`.

SLICE-0026 successfully completed the bounded Stage-3.3 evidence-path pilot over exactly 100 already-canonical BoatModels with retained historical Wikidata QID mappings. The slice used only the accepted rights-gated Wikidata API path for known QIDs, reused the existing extraction/normalization path, retained evidence for exactly five allowed Tier-1-compatible field pointers, and proved research-evidence persistence/replay without canonical identity mutation.

This acceptance does **not** declare the selected models fully Tier-1 searchable, does not create FieldResolution decisions, does not invent BoatDesign generations, does not complete Stage 3.2 and does not imply G4 passage.

## Accepted pilot evidence

The retained package independently reproduces the accepted identity boundary before pilot selection:

```text
canonical BoatModels                 1,770
historical QID -> HullQ-ID mappings 1,772
```

Pilot acquisition/result boundary:

- exactly 100 distinct accepted canonical BoatModels;
- exactly 100 selected known Wikidata QIDs fetched;
- 2 attributed Wikidata API HTTP requests;
- no SPARQL/discovery query;
- only LOA, LWL, beam, draft_min and displacement field pointers admitted.

Retained per-field coverage:

| field | normalized candidate | source statement only | unsupported / malformed | no usable value |
|---|---:|---:|---:|---:|
| LOA | 0 | 0 | 64 | 36 |
| LWL | 0 | 0 | 64 | 36 |
| beam | 41 | 0 | 0 | 59 |
| draft | 0 | 0 | 29 | 71 |
| displacement | 0 | 0 | 51 | 49 |

These figures are evidence-path measurements only and are not launch-readiness or Tier-1-completeness claims.

## Independent review and amendment history

The initial implementation review found two blocking issues:

1. final retained artifact-digest coverage omitted `REPLAY-RESULT.json` and `REPLAY-REPORT.md`;
2. Decimal persistence was not type-preserving because Decimal values were serialized as numeric-looking strings and readback heuristically converted numeric-looking strings to Decimal.

### Amendment round 1

The first amendment corrected final retained digest coverage and introduced an explicit Decimal marker representation. Independent re-review accepted the digest fix but found a remaining type-domain collision: because `NormalizedCandidate.value` is unconstrained, a legitimate value equal to `{"__decimal__": "12.80"}` could be misread as a Decimal marker.

### Amendment round 2

The second amendment replaced the partial marker with a total discriminated envelope shared by persistence, readback and fingerprinting:

- Decimal values use a dedicated `decimal` branch with exact textual payload;
- every non-Decimal value uses a `raw` branch whose payload is returned uninspected;
- Decimal `12.80`, string `"12.80"`, and a marker-lookalike dict remain pairwise distinguishable in both persistence and fingerprint representations;
- malformed/unwrapped encoded values fail closed.

Independent re-review accepted the type-preservation fix but found one auditability inconsistency: a persistence integration-test docstring stated that remote CI separately persisted the real retained 100-BoatModel package, while the existing CI job at that point only exercised the synthetic integration fixture.

### Amendment round 3

The final amendment changed only `.github/workflows/ci.yml` and made that documented verification path real. The PostgreSQL-18 CI job now:

1. offline-verifies the committed SLICE-0026 retained package before mutation;
2. persists/replays all 100 retained bundles against PostgreSQL 18;
3. explicitly asserts 100 first imports, zero conflicts/errors, zero readback mismatches, 100 idempotent reimports, zero canonical BoatModel rows, zero canonical BoatDesign rows and `clear=true`.

No live Wikidata/network acquisition was added to CI and no retained selection/evidence manifest is regenerated there.

Independent review of final head `370e4edc6b0642a70829b29bc8cb3c2b1a4a5e30` returned **ACCEPT** with no unresolved implementation findings.

## Validation evidence

Final accepted implementation head:

`370e4edc6b0642a70829b29bc8cb3c2b1a4a5e30`

Implementation-agent local validation reported:

- repository validator: PASS;
- Ruff format/lint: PASS;
- mypy: PASS (40 source files);
- pytest: **2,182 passed / 2 skipped**;
- coverage: **93.26%** overall (>=90% gate);
- SLICE-0026 offline verifier: PASS;
- local PostgreSQL 18 retained-package persist/replay: 100 imported, 0 readback mismatches, 100 idempotent reimports, 0 canonical rows.

Independent exact-head remote verification confirmed:

- CI run `32994651623`: SUCCESS;
  - quality (ubuntu-latest): SUCCESS;
  - quality (windows-latest): SUCCESS;
  - dependency audit: SUCCESS;
  - db integration (PostgreSQL 18): SUCCESS;
  - SLICE-0026 retained offline verify: SUCCESS;
  - SLICE-0026 retained 100-bundle PostgreSQL persist/replay: SUCCESS;
  - SLICE-0026 required-condition assertion step: SUCCESS;
- manufacturer reproducibility run `32994650994`: SUCCESS on ubuntu-latest and windows-latest.

Implementation PR #73 was merged as:

`db18179f9327612275cf38b22d593940717f0683`

The project owner explicitly accepted the reviewed result on **2026-08-26**.

## Canonical / production boundary preserved

SLICE-0026 did not:

- create, modify or delete canonical BoatModel identity/crosswalk rows;
- create any canonical BoatDesign row or mint a BoatDesign ID;
- create FieldResolution decisions;
- perform discovery expansion beyond the 100 selected known QIDs;
- add or reinterpret source rights;
- add fields beyond the five contracted Tier-1-compatible pointers;
- declare the pilot models fully Tier-1 searchable;
- complete Stage 3.2 or declare G4 passed;
- start SLICE-0027.

**Stage 3.2 remains OPEN.** The accepted canonical identity state remains exactly 1,770 BoatModels / 1,772 historical QID mappings.

## Evidence trail

- controlling contract: `docs/slices/SLICE-0026-bounded-wikidata-tier1-enrichment-evidence-pilot.md`;
- retained package: `research/stage3/sl0026-wikidata-tier1-enrichment/`;
- implementation PR: #73;
- final reviewed / accepted implementation head: `370e4edc6b0642a70829b29bc8cb3c2b1a4a5e30`;
- implementation merge commit: `db18179f9327612275cf38b22d593940717f0683`;
- exact-head PR CI run `32994651623`, SUCCESS;
- exact-head PR manufacturer reproducibility run `32994650994`, SUCCESS;
- independent-review verdict: **ACCEPT after three amendment rounds**;
- project-owner acceptance: **2026-08-26**.

## Next boundary

This closure does not itself create or authorize SLICE-0027. The next slice must be separately readied under the normal workflow and must remain bounded by the still-open Stage 3.2 / permitted parallel Stage-3.3 boundary and by evidence from the accepted SLICE-0026 pilot.
