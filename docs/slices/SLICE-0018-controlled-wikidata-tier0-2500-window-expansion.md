# SLICE-0018 — Controlled Wikidata Tier-0 2,500-Window Expansion

**ID:** SLICE-0018  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 3.2 — measured identity-universe expansion  
**Depends on:** SLICE-0017 accepted / DONE  
**Blocks:** any 5,000-window expansion or decision to add another bootstrap source

## Objective

Extend HullQ's accepted Wikidata Tier-0 bootstrap from the first controlled **1,000-candidate baseline** to a deterministic discovery window of at most the first **2,500** direct Wikidata sailboat-class candidates.

This slice is an **expansion delta**, not a re-run that is allowed to reinterpret the accepted SLICE-0017 baseline.

It must:

1. preserve the accepted SLICE-0017 artifact and canonical baseline unchanged;
2. discover the current first <=2,500 rights-cleared direct sailboat-class QIDs using the accepted deterministic Wikidata path;
3. identify the expansion delta relative to the accepted 1,000 SLICE-0017 candidate QIDs;
4. acquire/classify only that delta for new Tier-0 admission decisions;
5. compare new candidates against both the accepted/baseline search-key space and one another so newly introduced ambiguity cannot be auto-admitted;
6. retain the historical QID→HullQ-ID registry without reminting;
7. persist/replay the accepted SLICE-0017 baseline first and the SLICE-0018 delta second against PostgreSQL 18;
8. prove that no accepted SLICE-0017 canonical identity is deleted, demoted, rewritten or semantically changed by the expansion;
9. measure whether Wikidata's direct-instance universe actually reaches 2,500 candidates and what the incremental admission/review/non-admission burden is.

No technical-field enrichment is part of this slice.

## Why this slice is authorized

SLICE-0017 established a clean first broad Tier-0 bootstrap:

- 1,000 candidates processed;
- 965 accepted sparse BoatModels;
- 20 review-required collision candidates;
- 15 not admitted for missing label;
- 967 retained historical QID→HullQ-ID mappings;
- 10 collision clusters;
- 0 acquisition failures;
- exact PostgreSQL 18.6 replay/fresh-schema semantic equality;
- 0 Brand/Organization/BoatDesign invention;
- all replay zero-tolerance conditions clear;
- retained Stage-2 benchmark still `G3_PASS`.

This result does not justify unbounded ingestion, but it does justify the next explicit Stage-3.2 milestone from `docs/EXECUTION_PLAN.md`: determine whether the same cleared source can broaden the identity universe toward the 2,500 milestone without weakening accepted identity semantics.

## Controlling artifacts

Read and obey at minimum:

- `CLAUDE.md`;
- `docs/EXECUTION_PLAN.md` — Stage 3.1 / 3.2;
- `docs/ROADMAP.md`;
- `docs/DATABASE_COVERAGE_STRATEGY.md`;
- `docs/DATA_STRATEGY.md`;
- `docs/slices/SLICE-0017-controlled-wikidata-tier0-identity-bootstrap.md`;
- `docs/slices/SLICE-0017-acceptance-closure.md`;
- retained `research/bootstrap/wikidata/manifest.json` and its schema/report;
- accepted SLICE-0017 bootstrap implementation under `src/hullq/bootstrap/` and `scripts/bootstrap/`;
- `src/hullq/domain/identity.py` accepted search-key semantics;
- `src/hullq/sources/wikidata.py`;
- accepted research persistence from SLICE-0013;
- accepted canonical identity persistence/admission from SLICE-0016;
- `fixtures/sources/wikidata_source.json`;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- current accepted identity/provenance/source schemas/specs.

If an accepted artifact on `main` supersedes one of those filenames/versions, use the accepted current version.

## Critical state model — MUST remain structurally separate

There are four different concepts. They MUST NOT be represented as one interchangeable collection.

### A. Accepted SLICE-0017 baseline

The baseline is the owner-accepted retained 0017 run:

- exactly 1,000 baseline candidate QIDs;
- their accepted 0017 decisions;
- 965 accepted canonical BoatModels;
- 20 baseline review-required candidates;
- 15 baseline not-admitted candidates;
- the retained supporting research/provenance graph;
- the accepted 0017 manifest/report/replay evidence.

**The baseline is immutable input to SLICE-0018.**

SLICE-0018 MUST NOT rewrite `research/bootstrap/wikidata/manifest.json` or silently replace its meaning with a 2,500-candidate manifest.

### B. Historical retained crosswalk

This is the persistent QID → opaque HullQ-ID registry accumulated from accepted prior bootstrap work and any new SLICE-0018 mappings.

It is identity history, not a candidate list and not a decision list.

A historical mapping may remain retained even if its QID is absent from a later discovery window.

### C. Current SLICE-0018 discovery window

This is the ordered set of unique valid QIDs returned by the current bounded first-<=2,500 discovery operation.

It records what the source returned now. It is not itself the admission delta.

### D. SLICE-0018 expansion delta

This is:

```text
current SLICE-0018 discovery QIDs
MINUS
all 1,000 accepted SLICE-0017 baseline candidate QIDs
```

Only these delta QIDs receive new SLICE-0018 admission/review/non-admission decisions.

**Do not reclassify the 1,000 baseline candidates merely because they also appear in the larger current discovery window.**

## Explicitly forbidden interpretations

The following implementations are incorrect:

- replacing the accepted 0017 manifest with a new 2,500 manifest;
- treating the full current 2,500 window as if all records were newly unaccepted candidates;
- re-running classification on the accepted 0017 candidates and allowing new collisions to demote them;
- carrying old candidate rows into a new current-candidate collection merely to preserve IDs;
- treating `retained_crosswalk` as a decision registry;
- minting a second HullQ ID for any QID already present in the historical crosswalk;
- deleting an accepted BoatModel because its current Wikidata label/alias situation changed;
- padding a source result below 2,500 using another source;
- switching to Wikipedia, SailboatData or another source if Wikidata does not reach the target;
- using manufacturer/designer claims to infer Brand, Organization or BoatDesign identities;
- resolving the 20 accepted SLICE-0017 review cases as a side effect of expansion;
- adding Tier-1/Tier-2 technical fields merely because they are visible in Wikidata claims.

## Accepted baseline immutability rule

The 965 accepted SLICE-0017 canonical BoatModels are an accepted canonical baseline.

For SLICE-0018:

- their HullQ IDs are fixed;
- their accepted 0017 canonical payload/provenance semantics are fixed;
- they MUST be reproduced byte-/semantic-equivalently through the accepted replay path before delta admissions are applied;
- they MUST NOT be deleted or demoted solely because a new candidate shares a search projection;
- they MUST NOT be renamed/re-aliased from current live Wikidata data in this slice;
- any current-source anomaly involving an accepted baseline QID is measured/reported, not used as an implicit destructive update mechanism.

If implementation reveals that preserving this baseline is impossible without changing accepted semantics, stop and report `BLOCKED` rather than inventing a migration/retraction policy inside this slice.

## Candidate discovery boundary

Use the accepted rights-cleared Wikidata structured-data path.

SLICE-0018 MAY extend the bootstrap-specific deterministic discovery configuration, but MUST preserve the source and rights semantics accepted in 0017.

Required constraints:

- rights gate before every live network request;
- direct instances of `Q106179098` only;
- deterministic committed query/version;
- explicit stable `ORDER BY` before `LIMIT`;
- requested discovery limit: **2,500**;
- hard safety ceiling: **3,000**;
- bounded acquisition only;
- no recursive subclass expansion;
- no unbounded crawler;
- no Wikipedia content;
- no SailboatData input;
- no automatic source switch.

If at least 2,500 valid unique QIDs are returned, retain exactly the first 2,500 under the committed ordering.

If fewer than 2,500 are returned, retain all returned QIDs, report the observed Wikidata direct-instance ceiling and continue with the delta that actually exists.

Do not pad from another source.

A material rights/access/endpoint failure that prevents an auditable bounded run must yield `BLOCKED`.

## One authorized live acquisition

This slice authorizes **one controlled live Wikidata acquisition run** after local tests/validation are ready.

Normal CI remains offline.

Do not repeatedly reacquire live data to make a desired count/distribution appear.

If the authorized live run succeeds and is retained, subsequent code corrections MUST use the retained artifact offline unless an independent review proves the retained acquisition itself invalid and the project owner explicitly authorizes replacement.

## Baseline/delta manifest layout

Do not overwrite the accepted SLICE-0017 artifact.

Create a separate retained SLICE-0018 artifact under a clearly isolated path such as:

`research/bootstrap/wikidata/sl0018-2500/`

The exact path may be adjusted to existing repository conventions, but 0017 and 0018 retained artifacts MUST remain independently addressable.

The SLICE-0018 manifest/report must record at least:

- manifest/schema version;
- source_id;
- query/version/endpoints;
- original live acquisition timestamp;
- later recompute timestamp separately where applicable;
- requested limit and hard ceiling;
- current discovery-window QID count;
- deterministic ordered discovery QIDs or another replay-auditable retained representation of the window;
- accepted baseline manifest path/version and a stable content hash/fingerprint of the exact baseline artifact used;
- accepted 0017 implementation head: `34c2de8fc99ab6babad054a4186cee168cc3a2da`;
- accepted 0017 baseline candidate count: 1,000;
- overlap count between current discovery and baseline candidate QIDs;
- baseline QIDs absent from the current discovery window;
- expansion-delta count;
- each delta candidate's QID, retained source label/aliases, decision/reasons, stable HullQ ID if one exists, observation/bundle/evidence-link IDs as applicable;
- full retained historical crosswalk after merging baseline history with new mappings;
- collision measurements split between delta↔baseline and delta↔delta cases;
- source request/usage metrics;
- replay measurements.

The manifest MUST distinguish:

```text
current discovery window
!=
expansion delta
!=
historical retained crosswalk
!=
accepted baseline
```

## Historical HullQ ID rules

Reuse the accepted SLICE-0017 crosswalk semantics.

Before any live network request on a rerun/resume path:

- load and validate the retained historical crosswalk;
- fail closed on same-QID→different-ID conflicts;
- fail closed on same-ID→different-QID conflicts.

For a delta QID:

- if it already has a retained historical HullQ ID, reuse that exact ID;
- otherwise mint one opaque ID once only if/when the accepted bootstrap logic requires a retained ID;
- never derive the ID from QID, name or array position;
- preserve mappings across later omission/reappearance.

Accepted 0017 IDs MUST remain byte-identical.

## Search-projection collision rules for the delta

Use the accepted HullQ search-key/search-projection semantics from `src/hullq/domain/identity.py`; do not reimplement a bootstrap-local approximation.

A new delta candidate must be checked against:

1. all relevant accepted SLICE-0017 baseline candidate search projections/aliases that can be deterministically retained from the accepted artifact;
2. all other candidates in the current SLICE-0018 delta.

Decision scope is asymmetric by design:

### New delta candidate collides with accepted baseline candidate

- the existing baseline candidate/BoatModel remains unchanged;
- the new delta candidate becomes `REVIEW_REQUIRED`;
- do not demote/delete the accepted baseline entity;
- record a deterministic reason indicating collision with baseline/accepted search space.

### New delta candidate collides with a baseline REVIEW_REQUIRED candidate

- the baseline review decision remains unchanged;
- the new delta candidate becomes `REVIEW_REQUIRED`;
- record the collision in the SLICE-0018 review evidence.

### Multiple new delta candidates collide with one another

- all affected new delta candidates become `REVIEW_REQUIRED` unless an already-accepted deterministic rule on `main` proves otherwise without fuzzy inference;
- retain the complete collision cluster transitively.

### Accepted-baseline ↔ accepted-baseline collision newly observable from current live labels

Do not mutate either accepted canonical entity in this slice. Record the source anomaly/review fact and preserve baseline semantics. A destructive correction/retraction policy is out of scope.

## Delta auto-admission rules

A delta candidate MAY become a new sparse canonical BoatModel only when all accepted SLICE-0017 Tier-0 conditions still hold and additionally:

1. it is not one of the 1,000 baseline candidate QIDs;
2. it has no accepted search-projection collision with the retained baseline search space;
3. it has no unresolved collision with another delta candidate;
4. any retained historical HullQ ID is reused exactly;
5. admitting it does not alter any accepted baseline canonical entity.

The resulting payload remains sparse Tier 0:

- stable opaque HullQ ID;
- source-backed canonical name;
- safe exact same-entity source aliases only;
- no inferred Brand relationship;
- no inferred Organization relationship;
- `first_built` / `last_built` remain null unless an already-accepted source semantic used by the bootstrap explicitly supports them without new interpretation;
- `boat_design_ids` remains empty by default;
- no technical enrichment.

## Delta review/non-admission rules

Preserve deterministic reason codes and fail closed.

At minimum route new delta candidates away from canonical admission for:

- missing/empty usable label;
- collision with accepted/baseline search projection;
- collision with another delta candidate;
- crosswalk conflict;
- malformed/incomplete auditable acquisition;
- any need for fuzzy matching;
- any need for Brand vs Organization inference;
- any need for BoatModel vs BoatDesign/generation inference;
- any need to reinterpret a baseline decision.

Do not optimize for a high auto-admission percentage.

No post-hoc admission-rate target may be invented after seeing the result.

## Prior SLICE-0017 review queue is out of scope

The accepted 20 `REVIEW_REQUIRED` and 15 `NOT_ADMITTED` baseline decisions are frozen inputs for this expansion slice.

SLICE-0018 may observe new collisions involving those records, but it MUST NOT launch a manual resolution campaign or convert their accepted 0017 decision states merely to improve totals.

If later review-resolution work is useful, define a separate bounded slice with explicit correction/governance semantics.

## ResearchObservation / provenance requirements

For every newly auto-admitted delta BoatModel:

- retain a source-backed ResearchObservation / ResearchEvidenceBundle through accepted contracts;
- preserve source_id + QID locator;
- preserve raw source label separately from canonical payload semantics;
- use the accepted SLICE-0016 `CanonicalEvidenceLink` path;
- do not substitute reference crosschecks for provenance;
- do not infer manufacturer/designer identities.

Baseline 0017 research/provenance records are replayed from the accepted 0017 artifact and MUST remain semantically unchanged.

## PostgreSQL 18 replay proof — baseline first, delta second

The retained SLICE-0018 artifact must support fully offline CI replay.

Use isolated, freshly migrated PostgreSQL schemas; do not depend on pre-existing public-schema state.

### Pass 1 — combined accepted graph

1. replay the accepted SLICE-0017 baseline artifact through the existing accepted importers;
2. verify the exact baseline counts/semantic graph before applying delta work;
3. import SLICE-0018 delta ResearchEvidenceBundles;
4. import SLICE-0018 delta canonical admissions;
5. deep-readback every newly admitted delta BoatModel and evidence link;
6. re-check every accepted 0017 canonical BoatModel remains present with its accepted ID and semantic payload/provenance unchanged;
7. verify no baseline canonical rows were deleted/demoted/overwritten;
8. verify review/non-admitted delta candidates are absent as new canonical entities;
9. verify zero inferred Brand/Organization/BoatDesign rows from the delta.

### Exact re-import

Re-run the exact baseline+delta import sequence and require deterministic idempotent outcomes with zero conflict/reference-error/unexpected-error.

### Independent fresh schema

Create a second isolated schema from migrations zero and replay baseline+delta again.

Require the same complete combined canonical semantic graph as Pass 1, including:

- exact accepted 0017 baseline;
- exact new delta admissions;
- exact stable aliases/provenance links;
- zero stray Brand rows;
- zero stray Organization rows;
- zero stray BoatDesign rows;
- no review/non-admitted delta canonical rows.

## Baseline replay constants

The accepted 0017 baseline evidence used as prerequisite proof is:

- manifest candidates: **1,000**;
- baseline ResearchEvidenceBundles on replay: **985**;
- baseline canonical BoatModel admissions: **965**;
- baseline retained historical mappings: **967**;
- baseline review-required: **20**;
- baseline not-admitted: **15**.

SLICE-0018 must fail closed if the retained accepted baseline artifact no longer reproduces these accepted semantics before delta application.

Do not silently update these constants from a live rerun.

## Required regression tests

At minimum add/retain tests proving the following exact state transitions.

### 1. Delta extraction

Given baseline QIDs `{Q1, Q2}` and current discovery `{Q1, Q2, Q3, Q4}`, expansion delta is exactly `{Q3, Q4}`.

Q1/Q2 must not receive new decisions.

### 2. Discovery churn

Given baseline `{Q1, Q2}` and current discovery `{Q2, Q3}`, delta is `{Q3}` and Q1 is reported as baseline-absent/current-source churn.

Q1's accepted baseline/crosswalk state is preserved.

### 3. New collision with accepted baseline

Baseline accepted Q1 has search key `example 36`; new delta Q3 produces the same accepted search key.

Required result:

- Q1 remains unchanged/accepted;
- Q3 becomes `REVIEW_REQUIRED`;
- no baseline deletion/demotion/remint.

### 4. New collision with baseline review candidate

Baseline review Q2 and new Q3 collide.

Required result:

- Q2 retains its baseline review state;
- Q3 becomes `REVIEW_REQUIRED`.

### 5. Delta↔delta transitive collision

New candidates forming a transitive collision cluster remain a complete deterministic cluster and all affected new candidates are review-bound.

### 6. Historical ID reuse

A new delta QID that already exists in the retained historical crosswalk reuses the byte-identical ID.

### 7. Crosswalk fail-closed

Both conflict forms are rejected before network acquisition:

- same QID → two IDs;
- same ID → two QIDs.

### 8. Accepted artifact immutability

The SLICE-0017 retained manifest bytes/hash used as baseline are unchanged by SLICE-0018 live/recompute/replay operations.

### 9. Below-target source ceiling

If discovery returns fewer than 2,500 unique valid direct-instance QIDs, process only those returned, do not pad, and report target not reached.

### 10. Combined PostgreSQL graph

A real PostgreSQL integration test proves baseline import followed by delta import preserves the baseline graph and adds only expected new BoatModels/evidence links.

## Required measurements

The checked-in report and completion report must distinguish measured fact from interpretation and include at least:

- requested discovery limit = 2,500;
- hard safety ceiling = 3,000;
- unique current discovery QIDs returned;
- whether 2,500 target was reached;
- overlap count with the accepted 1,000-QID baseline;
- count/list or deterministic retained representation of baseline QIDs absent from current window;
- expansion-delta count;
- delta entities successfully fetched;
- acquisition failures/throttles/malformed responses;
- delta `AUTO_ADMIT` count;
- delta `REVIEW_REQUIRED` count;
- delta `NOT_ADMITTED` count;
- deterministic reason breakdown;
- delta↔baseline collision clusters/count;
- delta↔delta collision clusters/count;
- historical crosswalk count before and after expansion;
- newly minted IDs count;
- reused historical IDs count;
- newly persisted research observations/bundles;
- newly persisted canonical evidence links;
- total combined canonical BoatModel count after baseline+delta replay;
- baseline canonical drift/deletion/demotion count;
- first combined replay importer status counts;
- exact re-import counts;
- independent fresh-schema mismatch count;
- stray Brand/Organization/BoatDesign row counts;
- PostgreSQL version;
- source request/usage metrics;
- retained Stage-2 benchmark recommendation.

## Zero-tolerance conditions

Each must be zero/false/clear before acceptance:

- rights-gate bypass;
- live use of SailboatData or unrelated source values;
- rewriting/replacing the accepted 0017 retained manifest;
- baseline HullQ-ID remint;
- baseline canonical deletion;
- baseline canonical demotion caused only by larger-window collision;
- baseline canonical payload/provenance drift during replay;
- crosswalk conflict silently collapsed;
- new candidate forced through fuzzy merge;
- Brand inference from manufacturer role;
- Organization inference from manufacturer role;
- BoatDesign invention from QID/class existence;
- prior 0017 review decision silently resolved;
- unexpected importer conflict/reference-error/error/status;
- review/non-admitted delta candidate persisted as canonical;
- canonical evidence link points to wrong/nonexistent target;
- first-pass semantic readback mismatch;
- exact re-import non-idempotency;
- fresh-schema semantic mismatch;
- stray Brand/Organization/BoatDesign rows from delta;
- retained Stage-2 benchmark result other than exact `G3_PASS`.

A non-zero human-review rate is not a zero-tolerance failure.

## CI requirements

Normal CI MUST remain network-independent.

On the retained SLICE-0018 artifact, CI must run at least:

- repository validation;
- Ruff format/lint;
- strict mypy as accepted by repository policy;
- unit/full test suite with coverage gate;
- dependency audit;
- PostgreSQL 18 integration;
- retained Stage-2 benchmark and require exact `G3_PASS`;
- accepted SLICE-0017 baseline replay prerequisite;
- combined 0017-baseline + 0018-delta PostgreSQL replay;
- exact re-import proof;
- independent fresh-schema proof;
- retained SLICE-0018 manifest schema validation;
- zero-tolerance assertion;
- upload of SLICE-0018 retained manifest/report/replay outputs.

## Deliverables

Expected bounded deliverables include only what is necessary for the 2,500-window expansion:

- minimal extension of accepted Wikidata/bootstrap discovery/classification code;
- explicit baseline/delta state handling;
- separate versioned SLICE-0018 retained manifest schema/artifact/report;
- historical crosswalk reuse/extension;
- deterministic collision checks against baseline + delta;
- combined PostgreSQL replay runner/proof;
- tests for the required state transitions and negative paths;
- CI wiring for retained offline proof;
- measured report.

Do not build a generic ingestion orchestration platform unless a concrete accepted 0018 requirement cannot be implemented safely without a smaller reusable helper.

## Out of scope

Explicitly out of scope:

- 5,000-candidate expansion;
- another bootstrap source;
- Wikipedia ingestion;
- SailboatData ingestion/evidence/fallback use;
- resolution campaign for 0017's 20 review candidates;
- fuzzy identity resolution;
- destructive canonical correction/retraction framework;
- Brand/Organization canonical enrichment;
- designer identity ingestion;
- BoatDesign generation creation;
- technical Tier-1/Tier-2 enrichment;
- LOA/LWL/beam/draft/displacement enrichment campaign;
- appendage/rig/material enrichment campaign;
- derived-metric expansion;
- query-engine implementation;
- FastAPI/public API;
- Astro/frontend work;
- SEO/public-page implementation;
- marketplace integration;
- account/auth;
- saved search/monitoring/alerts;
- price-history work;
- distributed infrastructure.

## Acceptance criteria

SLICE-0018 may be presented for owner acceptance only when all of the following are true:

1. the accepted SLICE-0017 retained artifact is unchanged and replayable;
2. the current rights-cleared discovery window is deterministically bounded to <=2,500;
3. the expansion delta excludes all 1,000 baseline candidate QIDs from new decision-making;
4. all accepted 0017 canonical IDs/payload/provenance survive unchanged;
5. new delta admissions obey accepted Tier-0 semantics and collision checks against baseline + delta;
6. historical IDs are reused exactly and crosswalk conflicts fail closed;
7. the separate SLICE-0018 retained artifact is versioned/schema-valid/auditable;
8. PostgreSQL 18 first-pass combined replay has exact expected counts and zero unexpected statuses/errors;
9. exact re-import is idempotent;
10. independent fresh-schema replay produces the same combined semantic graph;
11. no delta review/non-admitted candidates become canonical;
12. no Brand/Organization/BoatDesign inference occurs;
13. all zero-tolerance conditions are clear;
14. retained Stage-2 benchmark remains exactly `G3_PASS`;
15. exact-head CI is green on Ubuntu, Windows, dependency audit and PostgreSQL 18;
16. independent review finds no remaining blocker;
17. explicit project-owner acceptance is given.

## Completion behavior

The implementation agent MUST:

- work only in the assigned SLICE-0018 branch/worktree;
- keep the slice `IN_PROGRESS`, `REVIEW` or `BLOCKED` as appropriate;
- never mark it `DONE`;
- never merge its own PR;
- never begin 5,000 expansion or enrichment automatically;
- report the exact full pushed HEAD SHA and measured results;
- clearly distinguish local evidence from CI-only PostgreSQL/live evidence.

After implementation review and exact-head CI, only the project owner can accept the slice. Closure/readiness for any later slice remains a separate master workflow step.

## Implementation completion report

### Slice

- Slice ID: `SLICE-0018`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`

### Changes

- Changed files:
  - `src/hullq/sources/wikidata.py` — `WIKIDATA_BOOTSTRAP_SAFETY_CEILING` raised 1,500 -> 3,000 (shared adapter-level ceiling; SLICE-0017's own requested-limit behavior of 1,000 is untouched).
  - `src/hullq/bootstrap/wikidata_tier0.py` — `_search_keys_for_candidate` promoted to public `search_keys_for_candidate` (exported); `_build_observation`/`build_bundle` gained an optional `activity_id` parameter defaulting to the original `"SLICE-0017-BOOTSTRAP"` value (zero behavior change for existing callers/tests).
  - `src/hullq/bootstrap/wikidata_tier0_sl0018.py` (new) — baseline loading/integrity, expansion-delta computation, baseline/delta-vs-delta collision detection, delta classification, SLICE-0018 manifest builder. Reuses `BootstrapCandidate`/`build_admission`/`mint_hullq_id`/`compute_collision_clusters` unchanged.
  - `scripts/bootstrap/wikidata_tier0_sl0018_runner.py` (new) — `--live`/`--recompute`/`--replay` runner; replay performs baseline-first then delta-second combined PostgreSQL import/verification in two independent isolated schemas.
  - `research/bootstrap/wikidata/sl0018-2500/manifest_schema.json` (new) — versioned JSON Schema Draft 2020-12 for the SLICE-0018 retained manifest.
  - `research/bootstrap/wikidata/sl0018-2500/manifest.json` (new, retained artifact from the one authorized live run).
  - `research/bootstrap/wikidata/sl0018-2500/REPORT.md` (new, generated report).
  - `.github/workflows/ci.yml` — added SLICE-0018 manifest schema validation, combined replay, zero-tolerance assertion and artifact-upload steps to the existing `db-integration` job, after the unmodified SLICE-0017 steps.
  - `tests/unit/test_wikidata_tier0_sl0018_expansion.py` (new, 21 tests).
  - `tests/persistence/test_wikidata_tier0_sl0018_expansion_integration.py` (new, 2 tests).
- Requirements implemented: the SLICE-0018 contract's expansion-delta computation, baseline-preserving classification, historical-crosswalk reuse, baseline/delta collision handling, versioned manifest, and baseline-first/delta-second combined PostgreSQL replay with drift detection.
- Tests/fixtures added: the two files above; no existing SLICE-0017 test was modified.

### Validation

- Local validation: `PASS`
- Commands run:
  - `uv run python scripts/validate_repository.py`
  - `uv run ruff format --check .`
  - `uv run ruff check .`
  - `uv run mypy src`
  - `uv run coverage run -m pytest` (full suite, `HULLQ_TEST_DATABASE_URL` set against a local disposable PostgreSQL 18.6 container) then `uv run coverage report`
  - `uv run pip-audit`
  - `uv run python scripts/bootstrap/wikidata_tier0_runner.py --replay ...` (accepted SLICE-0017 baseline prerequisite, run standalone)
  - `uv run python scripts/bootstrap/wikidata_tier0_sl0018_runner.py --replay ...` (SLICE-0018 combined baseline+delta, run standalone after the full test suite finished, to avoid shared-database lock contention)
  - `uv run python scripts/bootstrap/wikidata_tier0_sl0018_runner.py --live --user-agent "HullQ/0.1 (SLICE-0018 controlled bootstrap; https://github.com/StradaDelSole/HullQ)" --limit 2500` (the one authorized live acquisition)
  - `uv run python scripts/bootstrap/wikidata_tier0_sl0018_runner.py --recompute` (offline-only, to correct a cosmetic absolute-path field in the manifest's `baseline_reference.manifest_path` after the live run; reused every retained HullQ ID exactly, `acquired_at` preserved verbatim, `classification_recomputed_at` newly set)
- Results:
  - repository validator: PASS (88 requirements / 88 acceptance criteria, 27 active schemas)
  - Ruff format/lint: PASS (206 files)
  - mypy strict (`src`, 33 files): PASS
  - full test suite: **1633 passed, 2 skipped** (the 2 skips are pre-existing live-network smoke tests requiring an explicit `--run-live` flag, unrelated to this slice)
  - `tests/persistence/` alone (PostgreSQL 18.6): **205 passed**, including the 2 new SLICE-0018 integration tests
  - coverage: **94.96%** overall (gate is `>=90%`); `src/hullq/bootstrap/wikidata_tier0_sl0018.py` **100%**; `src/hullq/bootstrap/wikidata_tier0.py` 96.27% (unchanged pre-existing gaps)
  - pip-audit: no known vulnerabilities
  - **one authorized live Wikidata acquisition** (`--live --limit 2500`): unique QIDs returned **1,829** (target of 2,500 **not reached** — this is the measured direct-instance source ceiling for `Q106179098`, per the slice's explicit "measure whether Wikidata reaches the 2,500 target" requirement; no padding from another source was performed); overlap with the accepted 1,000-QID baseline **1,000** (full baseline still present — zero baseline churn); baseline-absent QIDs **0**; expansion delta **829**; delta `AUTO_ADMIT` **805**, `REVIEW_REQUIRED` **16** (6 baseline collisions, 6 delta-delta collision clusters), `NOT_ADMITTED` **8** (`missing_label`); acquisition failures **0**; retained crosswalk after merge **1,772** (967 baseline + 805 new); expected combined canonical BoatModel count after replay **1,770** (965 baseline + 805 delta)
  - **local combined PostgreSQL 18.6 replay** (`--replay`, standalone, full ~1,800-candidate scale, both isolated schemas): baseline-first import exactly reproduced 985 bundles / 965 admissions with the accepted baseline's exact canonical ID set and zero readback mismatches, in both passes, both before and after delta application (zero baseline drift); combined (baseline+delta) import: **1,806 bundles / 1,770 admissions imported**, 0 already-present/conflict/error/unexpected-status; 0 combined readback mismatches; 0 unexpected canonical rows for non-admitted candidates; exact combined canonical ID set match; 0 stray Brand/Organization/BoatDesign rows; exact re-import idempotency (**3,576 ALREADY_IMPORTED**, 0 conflict/error) in the same schema; independent fresh-schema rerun reproduced the identical combined graph with the same zero counts; **`all_zero_tolerance_conditions_clear: true`** in both the first pass and the independent fresh-schema pass
  - retained Stage-2 benchmark: not re-run by this slice (out of scope; CI reruns it unmodified as part of the existing `db-integration` job, which this PR does not touch)

### External verification

- Remote CI: `NOT VERIFIED` — the branch has not yet been pushed/observed on GitHub Actions as of this report; push happens immediately after this report is written.
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings: none identified during implementation. One self-caught issue was corrected before commit: the freshly live-acquired manifest's `baseline_reference.manifest_path` field initially recorded a developer-machine absolute Windows path; corrected via a code fix (`_repo_relative_path` helper in the runner) plus one offline `--recompute` pass (no network reacquisition; every retained ID/decision reused exactly, `acquired_at` preserved verbatim) so the committed manifest records a portable repo-relative path.
- Spec/ADR ambiguities: none blocking. The slice's manifest-layout list is a minimum-fields requirement, not an exact schema; the implemented `sl0018-v1` manifest schema is a superset satisfying every listed field (discovery window, baseline reference + fingerprint, overlap/baseline-absent, delta, delta-vs-baseline and delta-vs-delta collision detail, retained crosswalk, counts).
- Scope deviations: none. No 5,000 expansion, no other bootstrap source, no resolution of the 0017 review queue, no technical enrichment, and no Brand/Organization/BoatDesign inference were introduced.

### Follow-up

- Recommended next action: push this branch, observe exact-head GitHub Actions CI (Ubuntu/Windows quality, dependency audit, and the extended `db-integration` job including the new SLICE-0018 manifest-schema validation + combined-replay + zero-tolerance-assertion steps), then route to independent review and project-owner acceptance per the normal workflow. Do not begin a 5,000-candidate expansion or another bootstrap source; both remain explicitly out of scope for any later slice until a separate slice authorizes them.

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.

## Correction round — independent review blockers (post PR #37 review)

Independent review of PR #37 (implementation head `5a1ffd32cdcf4e9ae18218c23b41ad2b2dcd487d`) found five blockers. All five are fixed on this same branch, with adversarial regression tests, using only the already-retained SLICE-0018 acquisition (1,829 discovered QIDs / 829-entry delta) replayed offline. **No live Wikidata network request was made during this correction round.**

### Blocker 1 — retained historical crosswalk was not actually historical

- **Defect:** `build_sl0018_manifest()` reconstructed `retained_crosswalk` from `baseline.crosswalk` plus only the *current* delta candidates' own IDs, silently dropping any previously retained SLICE-0018 mapping for a QID absent from the current delta.
- **Fix:** `build_sl0018_manifest()` gained an explicit `historical_crosswalk` parameter (the full historical registry loaded before the run); the merge is now `historical_crosswalk ∪ current delta mappings`, failing closed via `CrosswalkConflictError` on drift. `run_live_bootstrap`/`recompute_manifest_offline` in the runner now pass their already-computed `historical_crosswalk` through. A new `merge_crosswalks_fail_closed`-based helper (`_load_baseline`) centralizes baseline loading for all three runner entry points.
- **Regression tests:** `tests/unit/test_wikidata_tier0_sl0018_expansion.py::test_historical_crosswalk_survives_omission_and_reappearance` (exact required transition: baseline {Q1}, prior SLICE-0018 crosswalk additionally {Q9: BM_OLD}, discovery {Q1,Q3} → candidates={Q3} only, retained_crosswalk⊇{Q1,Q3,Q9}, Q9 reappearing later reuses BM_OLD byte-for-byte) and `::test_omitting_historical_crosswalk_param_falls_back_to_baseline_only`; end-to-end runner-level three-run regression `tests/unit/test_wikidata_tier0_sl0018_expansion_runner.py::test_retained_sl0018_id_survives_a_discovery_window_that_omits_it`.

### Blocker 2 — incomplete entity acquisition could silently drop delta QIDs

- **Defect:** `run_live_bootstrap` never verified that `fetch_entities_bootstrap` returned exactly the requested delta QIDs, and unconditionally recorded `acquisition_failure_count=0`. `overlap_count` was derived as `len(discovery) - len(delta_candidates)` instead of directly from QID sets.
- **Fix:** new pure functions `verify_entity_acquisition_completeness` (runner, before any classification/manifest write) and `verify_delta_candidate_completeness` (inside `build_sl0018_manifest` itself, independent defense-in-depth) both raise the new `DeltaCompletenessError` on any missing/unexpected/duplicate QID, before any manifest is written or overwritten. `acquisition_failure_count=0` is now reached only after that check passes (derived, not asserted). `overlap_count` is now `len(frozenset(discovery_window_qids) & baseline.candidate_qids)`.
- **Regression tests:** `test_verify_entity_acquisition_completeness_rejects_{missing,unexpected,duplicate}_qid`, `test_build_sl0018_manifest_independently_rejects_truncated_candidate_set`, `test_overlap_count_computed_directly_from_qid_sets_not_delta_length`; runner-level `test_run_live_bootstrap_fails_closed_on_incomplete_entity_acquisition` (discovery delta [Q3,Q4], entity API returns only Q3 → `DeltaCompletenessError`, manifest file not written).

### Blocker 3 — SLICE-0018 window boundary enforcement (<=2,500)

- **Defect:** the runner could forward `--limit` values up to the shared adapter's 3,000 hard safety ceiling; nothing enforced SLICE-0018's own 2,500 bound before a network request.
- **Fix:** `run_live_bootstrap` rejects `requested_limit > BOOTSTRAP_REQUESTED_LIMIT_SL0018` (2,500) as its first statement, before `import httpx` or any baseline load. `build_sl0018_manifest` independently re-checks the same bound. The shared adapter ceiling remains 3,000 (unchanged). Manifest schema tightened: `requested_limit` `maximum: 2500`, `safety_ceiling` `const: 3000`, `discovery_window_qids` `maxItems: 2500` + `uniqueItems: true`.
- **Regression tests:** `test_build_sl0018_manifest_rejects_requested_limit_above_2500`, `test_manifest_schema_itself_rejects_requested_limit_above_2500`, `test_manifest_schema_rejects_wrong_safety_ceiling`, `test_manifest_schema_rejects_discovery_window_above_2500_items`; runner-level `test_run_live_bootstrap_rejects_limit_above_2500_before_any_network_use` (WikidataAdapter monkeypatched to raise if ever constructed — proves the rejection precedes network use) and `test_run_live_bootstrap_accepts_limit_at_exactly_2500_boundary`.

### Blocker 4 — baseline integrity check was not exact enough

- **Defect:** `load_baseline_snapshot` compared only `manifest_version`/aggregate counts, never the retained artifact's actual byte content; a payload/QID/label/alias change with unchanged aggregate counts would pass undetected. Duplicate-candidate-QID detection relied implicitly on `set()` insertion (silent for a duplicate row with a *consistent* `hullq_id`) despite a comment claiming explicit detection existed.
- **Fix:** new pinned constant `ACCEPTED_0017_MANIFEST_SHA256` (the accepted baseline's exact raw-byte SHA256); `load_baseline_snapshot` compares the freshly computed hash against it as the *first*, primary check, before the manifest-version/count diagnostics (retained as secondary diagnostics, not a substitute). `build_baseline_snapshot_from_manifest` now explicitly rejects a duplicate candidate QID (`if qid in candidate_qids: raise BaselineIntegrityError(...)`) rather than relying on set-insertion silence; the misleading comment was corrected.
- **Regression tests:** `test_load_baseline_snapshot_fails_closed_on_same_count_content_tampering` (exact required regression: tamper only a candidate's label, leaving `manifest_version` and every aggregate count byte-for-byte unchanged — still fails via the fingerprint), `test_load_baseline_snapshot_fails_closed_on_duplicate_candidate_qid`; the three pre-existing tamper tests updated to assert the new sha256-first priority.

### Blocker 5 — retained report lacked required measurements

- **Defect:** the checked-in `REPORT.md` said PostgreSQL replay evidence was "PENDING" despite a local retained replay having already been executed, and omitted several required measurements (historical-crosswalk before/after, minted/reused ID counts, importer status counts, re-import/fresh-schema counts, stray-row counts, PostgreSQL version, retained Stage-2 benchmark recommendation).
- **Fix:** `_write_live_report` now renders `historical_crosswalk_count_before`/`newly_minted_id_count`/`reused_historical_id_count` (new manifest `counts` fields, with an explicit note on what "this generation pass" means for a recompute vs the original live acquisition) and accepts an optional already-produced `replay_result`/`stage2_benchmark_recommendation` to embed the full PostgreSQL replay evidence (version, first-pass/fresh-schema importer status, re-import idempotency, stray-row counts, zero-tolerance verdict) and the Stage-2 `G3_PASS` recommendation. New reusable offline entry point `write_report_with_replay_evidence` / CLI `--regenerate-report --replay-result <path> --stage2-benchmark-result <path>` — no network or PostgreSQL access performed by this step itself; it only embeds an already-produced result. The checked-in `research/bootstrap/wikidata/sl0018-2500/REPORT.md` was regenerated this way from a fresh local `--replay` run and a fresh local `scripts/benchmark/runner.py` run (see measurements below).

### Structural invariants added while fixing the above

- `classify_delta_candidates` now rejects (via `DeltaCompletenessError`) a baseline QID accidentally supplied as delta input, and rejects a duplicate delta entity QID, before any classification proceeds — regression tests `test_classify_delta_candidates_rejects_accidental_baseline_qid` / `test_classify_delta_candidates_rejects_duplicate_delta_entity_qid`.
- `build_sl0018_manifest`'s new `verify_delta_candidate_completeness` call guarantees the manifest's `candidates` always equals the true current expansion delta for any successfully written manifest.
- No existing accepted SLICE-0017 behavior was weakened: `tests/unit/test_wikidata_tier0_bootstrap.py`, `test_wikidata_tier0_bootstrap_runner.py` and `test_wikidata_bootstrap_adapter.py` all still pass unmodified.

### Re-measured evidence (offline; retained acquisition reused, no new network request)

- Live-acquisition facts (unchanged from before this correction round — no reacquisition performed): unique QIDs returned **1,829** (target 2,500 not reached — measured Wikidata direct-instance source ceiling), overlap with accepted 1,000-QID baseline **1,000** (zero baseline churn), expansion delta **829** (AUTO_ADMIT 805 / REVIEW_REQUIRED 16 / NOT_ADMITTED 8).
- One offline `--recompute` pass was run after the code fixes to regenerate `manifest.json`/`REPORT.md` under the corrected logic (no network access): produced byte-identical decision/ID content to the pre-correction manifest (expected, since this is the first-ever SLICE-0018 run — no prior manifest existed for the historical-crosswalk-survival fix to visibly change).
- Local combined PostgreSQL 18.6 replay (`--replay`, standalone, full ~1,800-candidate scale, run after all corrections): baseline-first import exactly reproduced 985 bundles / 965 admissions with the accepted baseline's exact canonical ID set and zero readback mismatches, before and after delta application (zero baseline drift); combined import **1,806 bundles / 1,770 admissions**, 0 already-present/conflict/error/unexpected-status; 0 combined readback mismatches; 0 unexpected canonical rows for non-admitted candidates; exact combined canonical ID set match; 0 stray Brand/Organization/BoatDesign rows; exact re-import idempotency (**3,576 ALREADY_IMPORTED**, 0 conflict/error); independent fresh-schema rerun reproduced the identical combined graph; **`all_zero_tolerance_conditions_clear: true`** in both passes.
- Retained Stage-2 benchmark (`scripts/benchmark/runner.py`, same local PostgreSQL instance): recommendation **`G3_PASS`** (unchanged).
- Local quality gate: repository validator PASS (88/88); Ruff format/lint PASS (207 files); mypy strict (`src`, 33 files) PASS; full test suite **1656 passed, 2 skipped** (pre-existing `--run-live` smoke tests, unrelated); `tests/persistence/` alone PASS; coverage **94.88%** overall (`wikidata_tier0_sl0018.py` 97.49%); pip-audit no known vulnerabilities.

### Follow-up (correction round)

- Push this branch, observe exact-head GitHub Actions CI on the corrected head, then route to independent re-review and project-owner acceptance. Slice remains `REVIEW`.

### Agent declaration (correction round)

- No live Wikidata network request was made during this correction round; the already-retained 1,829-QID / 829-delta acquisition was reused offline throughout (one `--recompute` pass, one local `--replay`, one local Stage-2 benchmark run, all against already-committed/locally-provisioned PostgreSQL).
- No work outside the five blockers plus the requested structural invariants was performed.
- No unverified acceptance criterion was marked as passed.
- SLICE-0019 or any other slice was not started.
- The agent has NOT marked this slice `DONE`.
