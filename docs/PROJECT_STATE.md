# HullQ — Current Project State

**Updated:** 2026-08-21  
**Current stage:** Stage 3.2 — SLICE-0018 controlled Wikidata Tier-0 <=2,500-window expansion `READY`  
**Execution plan:** `docs/EXECUTION_PLAN.md`  
**Operational work queue:** `docs/slices/INDEX.md`

## Canonical project direction

HullQ is building an independent, provenance-aware sailboat design universe suitable for technical search/discovery, later market integration and reproducible derived metrics.

Accepted strategic principles remain:

- broad coverage with progressive verification depth;
- search architecture and SEO are product architecture, not later marketing;
- Search stays broadly available while persistence/monitoring are monetization candidates;
- source data, normalized candidates, canonical resolutions and HullQ-derived values remain distinct;
- unknown/conflict is preferable to fabricated completeness;
- one model string is not a reliable technical identity boundary;
- option/variant/state-sensitive values must not be flattened into one scalar baseline;
- source breadth is intentionally broad while canonical confidence remains strict;
- SailboatData is outcome-only post-hoc reference QA, never HullQ evidence/fallback data;
- GitHub `main` is canonical truth; bounded slice/PR review remains mandatory.

## Accepted application/deployment architecture

Target baseline remains:

```text
Cloudflare edge
      |
      v
Contabo Linux VPS
      |
      +-- Astro + TypeScript web
      |     \-- React islands only where state complexity justifies them
      +-- FastAPI / CPython 3.14
      +-- PostgreSQL
      +-- background/scheduled Python worker when needed
      \-- simple VPS deployment / Caddy baseline

Off-VPS backup/artifact direction: Cloudflare R2 when introduced
Later native mobile: Flutter Android/iOS via the same accepted API boundary
```

Auth remains deferred under OQ-014. OQ-006 controls alert cadence/freshness; OQ-015 controls the stable HTTP API/versioning boundary; OQ-018 controls the public SEO/search surface; OQ-009 must be resolved before technical query-engine semantics are frozen.

## Accepted foundation

| Slice | Result |
|---|---|
| SLICE-0001 | repository bootstrap, locked toolchain, Linux/Windows CI |
| SLICE-0002 | independent source research + seed evidence |
| SLICE-0003 | canonical JSON-Schema contract runtime |
| SLICE-0004 | measurement observation + exact normalization |
| SLICE-0005 | Brand/Organization + BoatModel/BoatDesign identity contracts |
| SLICE-0006 | FieldEvidence/FieldResolution provenance boundary |
| SLICE-0007 | ResearchJob + deterministic source-rights gate |
| SLICE-0008 | rights-gated Wikidata CC0 adapter |
| SLICE-0009 | appendage/configuration normalization |
| SLICE-0010 | `hullq-derived-1.0.0` derived metrics |
| SLICE-0011 | controlled 50-design real-web benchmark |
| SLICE-0012 | pre-canonical observations, claim/applicability semantics, research bundle + explicit promotion |
| SLICE-0013 | PostgreSQL 18 research persistence + deterministic transactional importer |
| SLICE-0014 | exact 50-design retained benchmark through PostgreSQL; full semantic roundtrip; G3_CANDIDATE |
| SLICE-0015 | negative-path hardening + fixed Stage-2 G3 scorecard; G3_PASS |
| SLICE-0016 | canonical Tier-0 identity PostgreSQL persistence/admission boundary |
| SLICE-0017 | controlled Wikidata Tier-0 1,000-candidate identity bootstrap; accepted broad Stage-3 baseline |

All slices 0001–0017 are `DONE` and owner-accepted.

Detailed acceptance evidence is retained in the dedicated `docs/slices/SLICE-00xx-acceptance-closure.md` records for the later accepted slices.

## Stage-2 benchmark status retained

Stage-2 Gate G3 remains passed.

The retained 50-design benchmark continues to prove:

```text
50/50 materialized
50/50 first-pass imported
50/50 exact re-import ALREADY_IMPORTED
50/50 fresh-schema imported
0 persistence errors/conflicts
0 semantic readback mismatches
0 fresh-schema semantic mismatches/errors
recommendation: G3_PASS
```

SLICE-0017 exact-head CI #200 re-ran this retained benchmark on the accepted implementation head and again returned exact `G3_PASS`.

Stage-2 passage authorizes only controlled Stage-3 slices. It is not blanket authorization for broad/unbounded ingestion.

## SLICE-0016 canonical admission boundary — accepted

The accepted canonical persistence/admission layer provides:

- Brand / Organization / BoatModel / BoatDesign canonical tables;
- entity-scoped aliases;
- Brand↔BoatModel and Organization↔BoatDesign relationship separation;
- caller-supplied stable opaque HullQ IDs;
- accepted schema validation before mutation;
- auditable links to retained HullQ observations/evidence;
- fail-closed exact-kind target validation for provenance links;
- BoatModel `boat_design_ids` consistency against the normalized BoatDesign graph;
- immutable semantic content fingerprints;
- atomic/idempotent/conflict-safe imports;
- PostgreSQL-native race-safe concurrency;
- lossless semantic readback;
- no fuzzy source-candidate resolution or persistence-layer ID minting.

Final closure record: `docs/slices/SLICE-0016-acceptance-closure.md`.

## SLICE-0017 — DONE / accepted broad Stage-3 baseline

SLICE-0017 executed the first controlled broad Wikidata Tier-0 identity bootstrap.

Accepted implementation head:

`34c2de8fc99ab6babad054a4186cee168cc3a2da`

Implementation PR #35 merge commit:

`e2001d3a926c08706558b6cb97962f235c843379`

Exact-head CI #200 (`32499124689`) passed with PostgreSQL 18.6, Ubuntu/Windows quality, dependency audit, retained Stage-2 `G3_PASS`, production bootstrap replay and every zero-tolerance assertion green.

Final retained live measurement:

```text
requested candidates                         1,000
unique candidates processed                  1,000
AUTO_ADMIT                                     965
REVIEW_REQUIRED                                 20
NOT_ADMITTED                                    15
collision clusters                              10
retained historical QID -> HullQ-ID mappings   967
ResearchEvidenceBundles on replay              985
canonical BoatModel admissions                 965
acquisition failures                             0
live retrievals                                 21
```

Final deterministic reason counts:

- `ok`: 965;
- `name_collision`: 20;
- `missing_label`: 15.

Production PostgreSQL 18.6 replay proved:

```text
first isolated schema:
  985/985 bundles imported
  965/965 admissions imported
  0 conflicts/errors/unexpected statuses
  0 semantic readback mismatches
  exact canonical BoatModel ID set
  0 unexpected canonical rows for non-admitted candidates
  0 Brand / Organization / BoatDesign rows

exact re-import:
  1,950 ALREADY_IMPORTED
  0 conflicts
  0 errors

independent fresh schema:
  985 bundles imported
  965 admissions imported
  0 semantic mismatches
  exact canonical BoatModel ID set
  0 Brand / Organization / BoatDesign rows

all_zero_tolerance_conditions_clear = true
```

Accepted bootstrap semantics now include:

- accepted HullQ search-key semantics for collision detection;
- stable content-derived alias IDs;
- opaque once-minted HullQ IDs independent of QID/name;
- historical retained crosswalk structurally separate from the current candidate set;
- fail-closed crosswalk validation in both conflict directions before live network use;
- stable mappings across discovery-window omission/reappearance;
- original acquisition time preserved separately from later recompute time;
- current candidate rows describe only the current bounded acquisition;
- isolated PostgreSQL replay from migrations zero;
- exact first-pass/importer-status/readback/reimport/fresh-schema proof;
- no Brand/Organization/BoatDesign inference;
- normal CI remains fully offline with respect to Wikidata.

Final closure record: `docs/slices/SLICE-0017-acceptance-closure.md`.

## Current operational position — SLICE-0018 READY

`docs/slices/SLICE-0018-controlled-wikidata-tier0-2500-window-expansion.md` is the only READY primary slice contract.

SLICE-0018 is intentionally an **expansion delta over an immutable accepted baseline**, not a disposable rerun of 0017.

The four state concepts are bindingly separate:

```text
A. accepted SLICE-0017 baseline
B. historical retained crosswalk
C. current SLICE-0018 first-<=2,500 discovery window
D. SLICE-0018 expansion delta = C minus all 1,000 baseline candidate QIDs
```

Only D receives new SLICE-0018 admission/review/non-admission decisions.

The accepted 965 baseline BoatModels must not be reclassified, demoted, deleted, renamed, re-aliased or reminted merely because a larger live discovery window exposes additional collisions or source churn.

A new delta candidate that collides with baseline search space is review-bound; the accepted baseline entity remains unchanged.

### Authorized live boundary

SLICE-0018 may perform one controlled live Wikidata acquisition after its local implementation/tests are ready:

- same accepted rights-gated direct-instance source;
- direct instances of `Q106179098` only;
- deterministic ordered query;
- requested limit: **2,500**;
- hard safety ceiling: **3,000**;
- no recursive subclass expansion;
- no source switch;
- no padding from another source if Wikidata returns fewer than 2,500.

If Wikidata direct-instance discovery returns fewer than 2,500 candidates, that observed ceiling is itself a measured Stage-3 result and will determine the next source/expansion decision.

### Retained artifact boundary

SLICE-0018 must create a separate retained artifact path and must not overwrite the accepted `research/bootstrap/wikidata/manifest.json` baseline.

The new artifact must explicitly retain/audit:

- accepted baseline identity/hash;
- current discovery window;
- expansion delta;
- historical crosswalk;
- baseline↔delta and delta↔delta collision measurements;
- source usage;
- combined baseline+delta PostgreSQL replay evidence.

### PostgreSQL acceptance proof

Offline CI must:

1. replay accepted 0017 baseline first;
2. verify exact accepted baseline graph;
3. apply 0018 delta bundles/admissions second;
4. prove zero baseline drift/deletion/demotion;
5. deep-readback new admitted delta BoatModels/provenance;
6. exact-reimport baseline+delta idempotently;
7. reproduce the same complete combined graph in an independent fresh schema;
8. prove zero stray Brand/Organization/BoatDesign rows;
9. keep the retained Stage-2 benchmark exactly `G3_PASS`.

## Near-term path

```text
SLICE-0011  controlled 50-design benchmark + analysis          DONE
      ↓
SLICE-0012  ResearchObservation + applicability/bundle         DONE
      ↓
SLICE-0013  research PostgreSQL persistence                    DONE
      ↓
SLICE-0014  same 50 cases through importer/database            DONE / G3_CANDIDATE
      ↓
SLICE-0015  harden negative paths + Stage-2 G3 decision        DONE / G3 PASS
      ↓
SLICE-0016  canonical identity persistence/admission boundary  DONE
      ↓
SLICE-0017  controlled Wikidata Tier-0 1,000 bootstrap         DONE
      ↓
SLICE-0018  baseline-preserving Wikidata <=2,500 expansion     READY
      ↓
measured 5,000/source/enrichment decision                      NOT AUTHORIZED YET
```

The benchmark corpus should not be expanded merely to increase its count. Additional stress cases are justified only if a materially new problem class is demonstrated.

## Continuous new-model intake — accepted future doctrine

Once broad design-universe ingestion is accepted, HullQ should treat historical/bootstrap coverage and ongoing new-model intake as separate tracks:

```text
historical / bootstrap universe
        +
continuous new-model intake
```

The future continuous track should progressively handle discovery → identity triage → technical intake → validation/persistence → deep enrichment, with explicit maturity such as announced/preliminary/production-confirmed/verified rather than pretending announcement data is final production specification.

SLICE-0018 is still historical/bootstrap-universe work. It does not implement the continuous new-model track.

## AI repository workflow — ACTIVE

Implementation/research slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It refuses slices whose own primary slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

After the SLICE-0017 closure / SLICE-0018 readiness PR is merged, the project owner may run `FINISH_SLICE.bat` for 0017 and then, when ready, `START_SLICE.bat` for 0018.

## Do not start yet

- 5,000 identity expansion before SLICE-0018 acceptance and measurement;
- another bootstrap source before SLICE-0018 measures whether Wikidata reaches the 2,500 window, unless SLICE-0018 is explicitly `BLOCKED` by the source boundary;
- resolution campaign for SLICE-0017 review candidates;
- broad Tier-1/Tier-2 technical enrichment;
- unbounded crawler work;
- automatic fuzzy/canonical identity resolution;
- destructive canonical correction/retraction framework;
- automatic Brand/Organization role inference from manufacturer labels;
- automatic BoatDesign generation invention from Wikidata QIDs;
- query-engine implementation;
- public FastAPI API;
- Astro frontend;
- account/auth;
- marketplace adapters;
- alerts/monitoring execution;
- multi-source listing deduplication;
- price-history pipeline;
- SEO/public-page implementation;
- HullQ Design Watch implementation;
- Powerboat expansion.
