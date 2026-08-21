# SLICE-0018 — Controlled Wikidata Tier-0 2,500-Window Expansion

**ID:** SLICE-0018  
**Type:** IMPLEMENTATION  
**Status:** READY  
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
