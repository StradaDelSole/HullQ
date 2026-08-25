# SLICE-0022 — Retained Alternative-Route Tier-0 Admission Safety Pilot

**ID:** SLICE-0022  
**Type:** IMPLEMENTATION  
**Status:** DONE  
**Stage:** 3.2 — canonical identity breadth / bounded admission proof  
**Depends on:** SLICE-0021 accepted / DONE  
**Blocks:** any production adoption of alternative Wikidata discovery semantics or broader alternative-route bootstrap

## Objective

Run the exact **57 retained SLICE-0021 alternative-route candidates** through HullQ's already accepted Tier-0 identity-admission, collision, provenance and PostgreSQL replay boundaries, without any new live acquisition and without changing the production Wikidata discovery query.

The slice must determine how many of the retained R1 candidates can be safely admitted as sparse canonical BoatModels under the same conservative rules accepted in SLICE-0017/0018, while keeping every R3 repair signal fail-closed and review-bound.

This is an **admission-safety pilot over retained evidence**, not production adoption of R1/R3 discovery.

## Why this slice exists

SLICE-0018 established the accepted direct-instance Wikidata boundary:

- 1,829 retained direct-discovery QIDs;
- 1,770 accepted sparse canonical BoatModels;
- 1,772 historical retained QID→HullQ-ID mappings;
- accepted baseline/delta collision semantics;
- exact PostgreSQL replay and fresh-schema proof.

SLICE-0021 then measured four fixed Wikidata discovery routes without canonical mutation. The accepted result was:

```text
R0 current direct control                    1,829
R0 drift                                         0
R1 sailboat-class P31/P279* closure          1,882
R1 incremental vs current R0                    53
R2 legacy closure                                0
R2 incremental                                   0
R3 structured repair signal                      4
R3 incremental                                   4
alternative-route union                         57
pairwise alternative-route overlaps              0
```

All 57 incremental QIDs were retained with identity-relevant structured details. Their SLICE-0021 exact QID/label/alias probe found 57 `no_exact_identity_signal`, but that category explicitly did **not** prove novelty or admission safety. R1 and R3 therefore ended only as `FOLLOWUP_DISCOVERY_CANDIDATE`; no candidate was admitted and the production discovery rule remained unchanged.

The next smallest evidence-based step is to test the accepted admission machinery against those exact retained facts. Jumping directly from `FOLLOWUP_DISCOVERY_CANDIDATE` to a production R1 query would skip the collision/admission proof that protected SLICE-0017/0018.

## Controlling artifacts

Read and obey at minimum:

- `CLAUDE.md`;
- `docs/EXECUTION_PLAN.md` — Stage 3.1 / 3.2;
- `docs/DATABASE_COVERAGE_STRATEGY.md`;
- `docs/DATA_STRATEGY.md` where relevant;
- `docs/slices/SLICE-0016-canonical-identity-persistence-bootstrap-admission.md`;
- `docs/slices/SLICE-0017-controlled-wikidata-tier0-identity-bootstrap.md` and acceptance closure;
- `docs/slices/SLICE-0018-controlled-wikidata-tier0-2500-window-expansion.md` and acceptance closure;
- `docs/slices/SLICE-0021-wikidata-alternative-sailboat-class-discovery-pilot.md` and acceptance closure;
- `research/bootstrap/wikidata/manifest.json`;
- `research/bootstrap/wikidata/sl0018-2500/manifest.json`;
- `research/bootstrap/wikidata/sl0021-alt-discovery/discovery_probe.json`;
- `research/bootstrap/wikidata/sl0021-alt-discovery/sampled_candidates.json`;
- `research/bootstrap/wikidata/sl0021-alt-discovery/REPORT.md`;
- accepted bootstrap/admission implementation under `src/hullq/bootstrap/` and `scripts/bootstrap/`;
- `src/hullq/domain/identity.py` accepted search-key/search-projection semantics;
- accepted ResearchEvidenceBundle and canonical PostgreSQL persistence/importer boundaries;
- `fixtures/sources/wikidata_source.json` and `specs/SOURCE_RIGHTS_POLICY.v0.1.md`.

If an accepted artifact on `main` supersedes a filename/version, use the accepted current version without inventing new semantics.

## Immutable retained inputs

SLICE-0022 performs **zero live Wikidata requests**. Its source facts are the already accepted SLICE-0021 retained artifacts.

Before any decision generation, execution MUST verify the exact accepted input identity:

```text
SLICE-0021 final accepted implementation head:
2cf0ab437d2347a574fd5a01b3e5577ca4c6b521

sampled_candidates.json Git blob:
5b56851f0c719b8dcf830fcd0416471c6c60596c

discovery_probe.json Git blob:
16af426991214c445a3c152aacbe56b8088958d6

retained direct-discovery universe: 1,829 QIDs
accepted canonical AUTO_ADMIT universe: 1,770 BoatModels
accepted historical QID→HullQ-ID mappings: 1,772

SLICE-0017 manifest raw SHA256:
076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845

SLICE-0018 manifest raw SHA256:
41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f
```

Execution MUST fail closed if the accepted retained inputs do not match those identities/counts.

The SLICE-0021 retained input must contain exactly:

- 57 selected unique candidate QIDs;
- 53 with R1 route membership;
- 0 with R2 route membership;
- 4 with R3 route membership;
- no QID belonging to more than one alternative route in the accepted retained set;
- no accepted-QID overlap reported by the accepted 0021 exact signal result.

Do not regenerate, rewrite or normalize the accepted SLICE-0017, SLICE-0018 or SLICE-0021 retained artifacts.

## Network boundary — zero live acquisition

This slice MUST NOT perform:

- WDQS requests;
- `wbgetentities` requests;
- manufacturer/archive requests;
- Wikipedia/PetScan/DBpedia requests;
- SailboatData requests;
- search-engine discovery;
- any other external acquisition.

All classification, manifest construction and replay must be reproducible from committed retained inputs.

If the retained evidence is insufficient for a candidate, route that candidate to review/non-admission under accepted rules. Do not fetch more data merely to improve the admission rate.

## Candidate universe and decision scope

The SLICE-0022 candidate universe is exactly the 57 retained SLICE-0021 incremental candidates.

Do not add:

- current new Wikidata items;
- current R0 drift;
- additional R1/R2/R3 results;
- SLICE-0017/0018 review candidates as new work;
- manufacturer-archive identities;
- manually discovered candidates.

The accepted 1,829 direct-discovery candidate universe is an immutable comparison/collision baseline, not a new decision queue.

Only the 57 retained SLICE-0021 candidates receive new SLICE-0022 decisions.

## Accepted decision vocabulary

Reuse the accepted bootstrap decision vocabulary:

- `AUTO_ADMIT`;
- `REVIEW_REQUIRED`;
- `NOT_ADMITTED`.

Do not introduce a new canonical decision state merely for this slice.

Preserve deterministic reason codes. Existing accepted reason semantics such as missing usable label and search-projection collision must be reused where applicable rather than reimplemented under new names without need.

One new explicit review reason is authorized for the accepted R3 boundary:

```text
r3_repair_signal_requires_review
```

This reason records the source of the fail-closed review requirement. It does not imply that the candidate is a valid BoatModel.

## R1 admission rules — reuse accepted Tier-0 semantics

The 53 retained R1 candidates are eligible for ordinary conservative Tier-0 classification using the accepted SLICE-0017/0018 machinery.

An R1 candidate MAY become `AUTO_ADMIT` only when all accepted conditions hold, including:

1. the retained candidate has a usable source-backed label;
2. its QID is not already part of the accepted 1,829 direct candidate universe;
3. historical crosswalk validation is conflict-free;
4. no accepted HullQ search-projection collision exists against the complete retained 1,829 candidate baseline where usable identity text exists;
5. no unresolved search-projection collision exists against another one of the 57 SLICE-0022 candidates;
6. admission requires no fuzzy matching, punctuation rewriting, manufacturer-prefix manipulation, token reordering, generation collapsing or semantic inference;
7. admission requires no Brand/Organization/BoatDesign invention;
8. the accepted sparse Tier-0 payload can be produced without changing accepted identity semantics.

If any of those conditions is not satisfied, route the candidate deterministically to `REVIEW_REQUIRED` or `NOT_ADMITTED` using accepted rules.

Do not optimize for a high `AUTO_ADMIT` percentage. Zero auto-admissions is a valid result if that is what the retained evidence supports.

## R3 fail-closed rule — never auto-admit

The four retained R3 candidates are structured **repair signals** and MUST NOT be `AUTO_ADMIT` in SLICE-0022.

For a structurally usable R3 candidate, the decision MUST be `REVIEW_REQUIRED` and include:

```text
r3_repair_signal_requires_review
```

If an accepted non-admission rule independently applies, such as a malformed record or no usable source-backed label, `NOT_ADMITTED` remains allowed. In no case may R3 membership itself create an admission rule.

The retained description text containing `sailboat class` is review context only. It MUST NOT be interpreted as proof that the QID is correctly modeled or that a HullQ BoatModel should be created.

R3 candidates still participate in the full 57-candidate collision graph. If an R1 candidate collides with an R3 candidate under accepted HullQ search-projection semantics, the R1 candidate MUST NOT be auto-admitted.

## Collision universe

Use `src/hullq/domain/identity.py` accepted search-key/search-projection semantics. Do not implement a slice-local approximation.

Each new candidate must be checked against:

1. the complete accepted SLICE-0017+0018 retained candidate identity space (1,829 QIDs), including usable retained labels/aliases from accepted auto-admit, review-required and non-admitted candidate records where available;
2. every other candidate in the exact 57-candidate SLICE-0022 set.

The existing 1,829 baseline decisions never change because a new candidate collides with them.

A new candidate colliding with an accepted/review baseline candidate becomes review-bound under accepted semantics. Do not resolve or demote the existing baseline record.

Transitive collision clusters among the 57 must be retained completely and deterministically.

## Retained labels / aliases / descriptions

Use the identity-relevant facts already retained by SLICE-0021.

For canonical Tier-0 identity decisions:

- canonical name may come only from a usable retained source-backed label under accepted bootstrap semantics;
- safe exact same-entity aliases may be retained only under accepted semantics;
- description text MUST NOT be converted into a manufactured canonical name;
- `P176` / `P287` MUST NOT create Brand, Organization, designer or BoatDesign relationships;
- `P31` / `P279` remain route/source context and MUST NOT trigger new canonical entity kinds;
- missing data stays missing.

## Historical HullQ-ID / crosswalk rules

Reuse the accepted SLICE-0017/0018 historical crosswalk behavior exactly.

Before generating new mappings:

- load and validate the accepted historical crosswalk;
- fail closed on same-QID→different-ID conflicts;
- fail closed on same-ID→different-QID conflicts;
- preserve all accepted 1,772 historical mappings unchanged.

For any SLICE-0022 QID already present in accepted history, reuse the exact historical HullQ ID.

For genuinely new mappings, use the accepted opaque once-minted ID mechanism; never derive IDs from QID, name, route or array position.

Do not modify the accepted 0017/0018 manifests/crosswalk in place. Retain any extended 0022 historical crosswalk only inside the new SLICE-0022 artifact package.

## Sparse canonical payload boundary

Any new `AUTO_ADMIT` result remains sparse Tier 0 only:

- stable opaque HullQ BoatModel ID;
- source-backed canonical name;
- safe exact aliases only where accepted;
- no inferred Brand;
- no inferred Organization;
- no inferred BoatDesign;
- `boat_design_ids` empty by default;
- no LOA/LWL/beam/draft/displacement/material/rig/keel/rudder/skeg enrichment;
- no derived metrics.

This slice must not use the opportunity to begin Stage-3.3 field enrichment.

## Research/provenance materialization

For every new auto-admitted BoatModel, materialize/reuse the accepted ResearchObservation / ResearchEvidenceBundle / CanonicalEvidenceLink path from the retained Wikidata structured facts.

Requirements:

- source_id remains the accepted Wikidata source;
- QID locator remains explicit;
- retained raw source label remains distinct from canonical payload;
- provenance must be sufficient for deterministic replay;
- reference/crosscheck data must not become provenance;
- no live refresh timestamp may be invented because this slice performs no network acquisition;
- preserve the original retained SLICE-0021 acquisition time as source-fact acquisition context where applicable, while recording later SLICE-0022 computation time separately.

## Required retained package

Create an isolated package, for example:

```text
research/bootstrap/wikidata/sl0022-alt-route-admission/
    manifest_schema.json
    manifest.json
    REPORT.md
```

A separate replay-result artifact/schema may be added if that matches the accepted 0017/0018 conventions and materially improves auditability.

The retained package must record at minimum:

- schema/version;
- exact immutable input paths and Git blob/raw SHA references;
- 1,829 / 1,770 / 1,772 accepted baseline counts;
- exact ordered 57-candidate QID set;
- route membership for every candidate;
- retained source label/aliases used for classification;
- deterministic decision + complete reasons for every candidate;
- collision memberships against baseline and within the 57-candidate set;
- stable HullQ ID where accepted semantics retain one;
- extended historical crosswalk where applicable;
- decision totals split by R1 and R3;
- canonical-admission count;
- expected combined canonical BoatModel count = `1770 + SLICE-0022 AUTO_ADMIT count`;
- replay/import/readback metrics;
- computation timestamps distinct from retained source acquisition timestamps;
- deterministic artifact/content digests.

## PostgreSQL 18 replay proof

Normal CI must prove the accepted combined baseline plus the SLICE-0022 admission delta from migrations zero without network access.

### Pass 1 — accepted baseline first, 0022 delta second

1. replay the accepted SLICE-0017 baseline;
2. replay the accepted SLICE-0018 delta;
3. verify the exact accepted combined canonical baseline of **1,770 BoatModels** before applying 0022;
4. import SLICE-0022 ResearchEvidenceBundles for newly admitted candidates as required by accepted semantics;
5. import SLICE-0022 canonical admissions;
6. deep-readback every newly admitted BoatModel/alias/evidence link;
7. re-check every accepted baseline BoatModel remains byte-/semantically unchanged;
8. require canonical BoatModel count exactly `1770 + auto_admit_count`;
9. require every SLICE-0022 `REVIEW_REQUIRED` / `NOT_ADMITTED` candidate to be absent as a new canonical row;
10. require zero new Brand, Organization and BoatDesign rows.

### Exact re-import

Re-run the exact combined import sequence and require only accepted idempotent outcomes, with zero conflict/reference/unexpected errors.

### Independent fresh schema

Create a second isolated schema from migrations zero and replay the accepted 0017 + 0018 baseline plus 0022 again.

Require the same complete canonical IDs, payloads, aliases/provenance and zero stray Brand/Organization/BoatDesign rows.

## Reproducibility / offline verification

Provide an offline verification path that fails closed if retained output is inconsistent with immutable inputs or accepted deterministic computations.

At minimum verify/recompute:

- exact input blob/hash identities;
- exact 57 candidate QIDs and route memberships;
- R1/R3 split 53/4 and R2 zero;
- no duplicate QIDs;
- accepted baseline counts 1,829 / 1,770 / 1,772;
- search-projection collision graph;
- per-candidate decision/reasons;
- R3 never `AUTO_ADMIT`;
- decision totals;
- historical crosswalk bijection/preservation;
- expected canonical total;
- deterministic IDs/aliases/evidence-link identity where applicable;
- replay result invariants.

Tamper-focused tests must prove the verifier rejects manipulated candidate QIDs, route membership, decisions, collision membership, R3 auto-admission, baseline references/counts, crosswalk mappings and expected totals.

## Production discovery remains unchanged

SLICE-0022 MUST NOT:

- change `WikidataAdapter.discover_sailboat_qids` / accepted direct production discovery semantics;
- add R1 or R3 to the production discovery path;
- schedule R1/R3 acquisition;
- create a generalized subclass crawler;
- automatically import future R1/R3 candidates;
- turn R3 description matching into a production classification rule.

The outcome may recommend a later bounded production-route implementation slice, but that later slice must have its own readiness contract and owner acceptance path.

## Explicitly out of scope

- any live external acquisition;
- production adoption of R1/R2/R3 discovery;
- manufacturer/archive permissions or ingestion;
- Wikipedia/PetScan/DBpedia/SailboatData acquisition;
- resolving accepted SLICE-0017/0018 review queues;
- manually resolving R3 identities;
- destructive correction/retraction of accepted canonical identities;
- Brand/Organization/BoatDesign inference;
- Tier-1/Tier-2 technical enrichment;
- keel/rudder/skeg/material/rig enrichment;
- derived-metric computation for new records;
- query engine/API/frontend/search UX;
- marketplace/listing work;
- accounts/saved queries/alerts/monitoring;
- price-history work;
- SLICE-0023 creation or start.

## Expected touch points

Likely/allowed touch points include:

- new SLICE-0022 pure/bootstrap logic under `src/hullq/bootstrap/` where reuse of existing functions is insufficient;
- a deterministic offline runner under `scripts/bootstrap/`;
- focused unit/integration tests;
- new retained package under `research/bootstrap/wikidata/sl0022-alt-route-admission/`;
- `.github/workflows/ci.yml` only if needed to add offline schema/verify/replay gates;
- `docs/slices/SLICE-0022-retained-alternative-route-tier0-admission-safety-pilot.md`;
- `docs/slices/INDEX.md` and `docs/PROJECT_STATE.md` for normal status handoff.

Do not modify accepted SLICE-0017/0018/0021 retained artifacts.

## Acceptance criteria

- [ ] execution uses exactly the accepted 57 retained SLICE-0021 candidates and performs zero live network requests;
- [ ] accepted SLICE-0021 input Git blobs and accepted SLICE-0017/0018 raw manifest SHA256 values are checked fail-closed;
- [ ] accepted baseline counts are hard-asserted at 1,829 candidate QIDs / 1,770 canonical BoatModels / 1,772 historical mappings;
- [ ] exact retained route membership is 53 R1 / 0 R2 / 4 R3 with 57 unique total;
- [ ] accepted search-projection semantics from `src/hullq/domain/identity.py` are reused rather than approximated locally;
- [ ] all 57 candidates are collision-checked against the complete accepted 1,829 candidate identity space and against one another;
- [ ] transitive collision clusters are retained deterministically;
- [ ] R1 decisions reuse accepted Tier-0 `AUTO_ADMIT` / `REVIEW_REQUIRED` / `NOT_ADMITTED` semantics without post-hoc admission targets;
- [ ] no R3 candidate can become `AUTO_ADMIT` and structurally usable R3 candidates carry `r3_repair_signal_requires_review`;
- [ ] no fuzzy matching, punctuation rewriting, prefix manipulation, token reordering, generation collapsing or semantic identity inference is introduced;
- [ ] no candidate is given a manufactured canonical name from description/P176/P287/context;
- [ ] the accepted historical QID→HullQ-ID mapping is preserved conflict-free and any extension follows accepted opaque-ID semantics;
- [ ] accepted SLICE-0017/0018/0021 retained artifacts remain byte-unchanged;
- [ ] every new admission is sparse Tier 0 only and creates no Brand/Organization/BoatDesign row;
- [ ] every new admission has accepted provenance/research material sufficient for deterministic PostgreSQL replay;
- [ ] retained SLICE-0022 artifacts validate against strict schemas and reproduce offline;
- [ ] PostgreSQL 18 replay verifies the exact accepted 1,770 baseline before 0022 and exact final canonical count `1770 + auto_admit_count` after 0022;
- [ ] review/non-admitted SLICE-0022 candidates are absent from canonical PostgreSQL rows;
- [ ] exact re-import and independent fresh-schema replay are deterministic with zero conflicts/unexpected errors/semantic mismatches;
- [ ] normal CI performs no live Wikidata request;
- [ ] production Wikidata discovery semantics remain unchanged;
- [ ] no accepted prior review queue is resolved as a side effect;
- [ ] SLICE-0023 is not created or started;
- [ ] required remote CI is actually observed before final handoff;
- [ ] independent review is completed before owner acceptance;
- [ ] explicit project-owner acceptance is required before closure to `DONE`.

## Validation

At minimum run:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Also run the new SLICE-0022 offline verifier and PostgreSQL replay path defined by the implementation. No validation command may require live Wikidata access.

## Stop conditions

Stop and report `BLOCKED` instead of inventing a solution if:

- immutable accepted input hashes/blobs/counts do not match;
- reproducing the 57-candidate set requires a live refresh;
- existing accepted Tier-0 rules cannot classify the retained candidates without changing identity semantics;
- preserving the 1,770 accepted canonical baseline is impossible;
- a candidate requires fuzzy/semantic resolution to avoid a collision;
- an R3 candidate would require auto-admission to satisfy an implementation assumption;
- implementation would require modifying accepted prior retained artifacts;
- implementation would require changing production discovery semantics;
- implementation requires scope outside this slice.

## Status handoff rule

Claude Code may hand SLICE-0022 back only as `REVIEW`, `BLOCKED` or `IN_PROGRESS`.

It MUST NOT merge its own PR, mark the slice `DONE`, create/start SLICE-0023 or begin production R1/R3 adoption automatically.

## Mandatory completion report additions

In addition to the exact `docs/slices/SLICE_TEMPLATE.md` structure required by the hardened `START_SLICE` workflow, the final operator-facing report must explicitly include:

1. exact final branch HEAD SHA and complete changed-file list;
2. confirmation **zero live network requests** were made;
3. accepted immutable input blob/hash checks and 1,829 / 1,770 / 1,772 assertions;
4. exact R1/R3 candidate counts and proof of the 57-candidate universe;
5. decision totals overall and split by route;
6. every decision reason count;
7. collision counts/clusters versus accepted baseline and within the 57 candidates;
8. proof all R3 candidates are non-auto-admitted;
9. new historical mapping count and final crosswalk count;
10. new canonical admission count and exact final expected/observed canonical BoatModel count;
11. retained artifact paths/digests;
12. PostgreSQL first-pass/re-import/fresh-schema metrics;
13. local validation/tests/coverage;
14. remote CI status on the exact final pushed head;
15. explicit confirmation production discovery query is unchanged and SLICE-0023 was not created/started.

The complete report must be returned directly in Claude's final chat response. A committed report or PR body does not substitute for that operator-facing handoff.