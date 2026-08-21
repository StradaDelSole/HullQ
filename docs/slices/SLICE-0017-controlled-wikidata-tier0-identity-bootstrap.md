# SLICE-0017 — Controlled Wikidata Tier-0 Identity Bootstrap

**ID:** SLICE-0017  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 3.1–3.2 — first controlled broad identity bootstrap  
**Depends on:** SLICE-0016 accepted / DONE  
**Blocks:** later 2,500 / 5,000 identity expansion and Stage-3 enrichment planning

## Objective

Run HullQ's first controlled four-digit identity bootstrap using the already-cleared Wikidata structured-data path and the accepted SLICE-0016 canonical PostgreSQL admission boundary.

The slice must process the first approximately **1,000** direct Wikidata sailboat-class candidates in a deterministic bounded order, retain a replayable bootstrap manifest, admit only identity claims that can be made safely at Tier 0, and measure the ambiguity/review burden before HullQ scales further.

The intended flow is:

```text
reviewed Wikidata Source record
        ↓ rights gate ALLOWED
bounded direct-instance discovery (Q106179098)
        ↓
first <=1,000 candidates in deterministic order
        ↓
bounded entity acquisition
        ↓
source-backed Tier-0 identity observations
        ↓
explicit bootstrap classification
        ├─ safe BoatModel admission
        └─ REVIEW_REQUIRED / NOT_ADMITTED
        ↓
versioned bootstrap manifest + review queue
        ↓
ResearchEvidenceBundle persistence
        ↓
SLICE-0016 canonical identity admission
        ↓
PostgreSQL 18 replay / idempotency / fresh-schema proof
```

This is the first broad canonical bootstrap slice. It is **not** a technical-enrichment pass and it MUST NOT invent Brand, Organization or BoatDesign specificity from source labels.

## Why this slice exists

Accepted repository evidence now provides all prerequisites for a controlled bootstrap:

- SLICE-0002 established Wikidata structured data (CC0) as the strongest current broad identity-bootstrap candidate and found a plausible roughly 1,000–1,500 candidate order of magnitude;
- SLICE-0008 provides the rights-gated official Wikidata acquisition path and direct sailboat-class discovery semantics;
- SLICE-0012 provides pre-canonical ResearchObservation / ResearchEvidenceBundle semantics;
- SLICE-0013 provides deterministic research/evidence PostgreSQL persistence;
- SLICE-0015 passed Stage-2 Gate G3;
- SLICE-0016 provides canonical Tier-0 PostgreSQL persistence/admission with caller-supplied stable opaque HullQ IDs and fail-closed provenance/reference behavior.

The remaining question is operational: can HullQ safely turn a four-digit rights-cleared source candidate set into a broad Tier-0 canonical BoatModel universe without silently converting source identity assumptions into false HullQ certainty?

## Controlling artifacts

Read and obey at minimum:

- `CLAUDE.md`;
- `docs/EXECUTION_PLAN.md` — Stage 3.1 / 3.2;
- `docs/ROADMAP.md` — broad design-universe ingestion;
- `docs/DATABASE_COVERAGE_STRATEGY.md` — breadth first, Tier 0, sparse data valid;
- `docs/DATA_STRATEGY.md`;
- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`;
- `research/evidence/SOURCE_REGISTER.md`;
- `fixtures/sources/wikidata_source.json`;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- `specs/SOURCE_SCHEMA.v0.2.json`;
- `specs/IDENTITY_MODEL.v0.2.md`;
- `specs/BOAT_MODEL_SCHEMA.v0.2.json`;
- `specs/PROVENANCE_MODEL.v0.1.md`;
- accepted ResearchObservation / ResearchEvidenceBundle contracts;
- `src/hullq/sources/wikidata.py`;
- accepted research persistence from SLICE-0013;
- accepted canonical identity persistence from SLICE-0016;
- `docs/slices/SLICE-0016-acceptance-closure.md`.

If a current accepted artifact supersedes one of these filenames/versions on `main`, use the current accepted version.

## Binding interpretation of “~1,000-design bootstrap”

For this slice, the milestone means **approximately 1,000 source candidates processed through the Tier-0 canonical identity admission decision**, not “invent exactly 1,000 BoatDesign rows.”

A direct Wikidata sailboat-class item is evidence of a source identity candidate. It is **not by itself proof of a distinct HullQ BoatDesign generation**.

Therefore:

- safe candidates may become canonical `BoatModel` Tier-0 identities;
- `BoatDesign` MUST NOT be auto-created merely because a Wikidata QID exists;
- manufacturer `P176` MUST NOT automatically become a Brand or Organization relationship;
- designer `P287` MUST NOT create new identity types in this slice;
- missing technical depth remains unknown and is not a reason to fabricate a design baseline.

The later enrichment layer may add BoatDesign generations only when accepted identity evidence supports them.

## Candidate-set boundary

### Deterministic broad discovery

SLICE-0008's `SLICE_0008_ITEM_CEILING = 100` is a historical controlled-probe cap and MUST NOT be silently mutated into a different meaning.

SLICE-0017 MAY add a separate bootstrap-specific discovery operation/configuration with these constraints:

- rights gate before every network request;
- direct instances of `Q106179098` only;
- deterministic query text/version;
- explicit stable `ORDER BY` before `LIMIT`;
- requested bootstrap candidate limit: **1,000**;
- hard bootstrap safety ceiling: **1,500**;
- one bounded query or another equally bounded deterministic approach;
- no unbounded crawling;
- no recursive subclass expansion;
- no Wikipedia/CC-BY-SA content;
- no source switch if WDQS/API behavior fails.

If the direct-instance query returns at least 1,000 unique valid QIDs, process exactly the first 1,000 under the committed deterministic ordering.

If it returns fewer than 1,000, process all returned direct-instance candidates and report the observed count. Do not pad the dataset from another source merely to hit a number.

If endpoint/rights behavior materially prevents the controlled run, stop and report `BLOCKED` rather than bypassing the accepted source gate.

## Bootstrap manifest

The slice MUST retain a versioned, replayable repository artifact for the actual controlled run, under a bounded location such as:

`research/bootstrap/wikidata/`

Prefer JSON/JSONL plus a human-readable report.

Each candidate record must retain enough information to audit the bootstrap decision, including at least:

- bootstrap manifest/version;
- source_id;
- Wikidata QID;
- source retrieval/probe identity/version;
- preferred source label used for identity evaluation;
- retained exact source aliases needed for audit if collected;
- stable HullQ canonical ID if admitted;
- decision state;
- deterministic decision reason code(s);
- supporting ResearchObservation ID(s);
- review reason(s) where applicable.

The manifest MUST NOT contain SailboatData values or unrelated third-party content.

The committed manifest becomes the reproducible input for offline PostgreSQL replay. CI MUST NOT depend on live network access.

## Stable HullQ ID minting

SLICE-0016 intentionally requires caller-supplied stable opaque HullQ IDs and does not mint them from names/source IDs.

For this bootstrap:

- a new admitted canonical identity receives an opaque HullQ ID **once**;
- the ID MUST NOT encode or be deterministically derived from the BoatModel name or Wikidata QID;
- a UUIDv4-style opaque identifier is acceptable;
- the QID → HullQ-ID crosswalk MUST be retained in the versioned bootstrap manifest;
- once a QID has a retained HullQ ID in the manifest, every replay/re-run MUST reuse it;
- an existing QID MUST NOT be silently reminted;
- a conflicting retained crosswalk MUST fail closed;
- canonical IDs MUST remain stable even if display labels later change.

Do not introduce a global identity-resolution service or generic ID registry beyond the smallest manifest/crosswalk needed for this bootstrap.

## Tier-0 auto-admission rules

A candidate MAY be automatically admitted as a canonical BoatModel only when all of the following are true:

1. the QID came from the rights-cleared direct-instance discovery set;
2. entity acquisition succeeded through the accepted rights-gated path;
3. a non-empty preferred source label is available;
4. the QID has no conflicting retained HullQ-ID mapping;
5. no deterministic exact/accepted search-projection collision inside the candidate set indicates unresolved same-name/reused-name ambiguity;
6. creating the BoatModel requires no inference of Brand, Organization, BoatDesign generation, variant or technical configuration;
7. supporting source identity observation(s) can be persisted and linked through the accepted provenance/admission boundary.

The resulting sparse Tier-0 BoatModel should normally have:

- caller-supplied stable opaque HullQ `id` from the manifest;
- source-backed `canonical_name`;
- exact same-entity source aliases only when they can be retained without role inference;
- empty `brand_relationships` unless separately accepted evidence in the same candidate establishes a Brand relationship without conflating manufacturer role;
- `first_built` / `last_built` only if the accepted source observation semantics support them without guessing; otherwise `null`;
- empty `boat_design_ids` unless a separate explicit evidence rule in this slice proves a technical generation. The default is **no auto-created BoatDesign**.

For this first bootstrap, conservative omission is preferred over inventing role/generation precision.

## Review / non-admission rules

Use deterministic reason classes rather than free-form guesses.

At minimum route to `REVIEW_REQUIRED` or `NOT_ADMITTED` when applicable for:

- missing/empty usable label;
- multiple source candidates colliding under the accepted deterministic identity/search projection where the existing evidence is insufficient to decide one vs multiple BoatModel lineages;
- conflicting retained QID → HullQ-ID mapping;
- malformed/incomplete acquisition result that prevents an auditable identity claim;
- source semantics that require Brand vs Organization inference;
- source semantics that require BoatModel vs BoatDesign/generation inference beyond the accepted rule;
- any condition where admitting would require fuzzy matching or plausibility guessing.

A review-required candidate MUST NOT receive an accepted canonical record merely to maximize the admitted count.

## ResearchObservation / provenance requirements

Every auto-admitted BoatModel MUST have retained HullQ source evidence supporting the identity admission.

At minimum:

- create/persist a source-backed ResearchObservation for the source identity/name claim;
- preserve source_id + QID locator;
- preserve raw source label separately from canonical storage semantics;
- use intended subject/field hints only as hints where accepted by the current contract;
- link the admitted canonical BoatModel to the supporting observation/evidence through SLICE-0016 `CanonicalEvidenceLink`;
- reference crosschecks cannot satisfy admission provenance.

Manufacturer/designer claims MAY be retained as unresolved source observations for later enrichment, but MUST NOT be promoted into canonical Brand/Organization/designer identities automatically in this slice.

## Replay and PostgreSQL proof

The committed bootstrap manifest must be replayable without live network access against PostgreSQL 18.

Required proof:

1. import retained research observations/bundles;
2. import the admitted canonical BoatModels through the accepted SLICE-0016 importer;
3. verify every admitted canonical ID/name/provenance link by semantic readback;
4. exact replay returns deterministic already-present/idempotent outcomes;
5. fresh-schema replay produces the same canonical semantic graph;
6. review/non-admitted candidates never appear as accepted canonical entities;
7. no Brand/Organization/BoatDesign rows are created merely from unresolved Wikidata manufacturer/designer/class semantics.

Do not bypass SLICE-0016 by bulk-inserting directly into canonical tables.

## Required measurements

The completion report and checked-in bootstrap report must distinguish measured fact from interpretation and include at least:

- live discovery request limit;
- unique QIDs returned;
- candidates actually processed;
- fetched entities;
- acquisition failures/throttles/malformed responses;
- candidates auto-admitted as BoatModel;
- candidates `REVIEW_REQUIRED`;
- candidates `NOT_ADMITTED`;
- exact reason counts by deterministic class;
- exact-name/search-projection collision clusters;
- retained QID→HullQ-ID mappings;
- research observations persisted;
- canonical evidence links persisted;
- first replay imported/already-present/conflict/error counts;
- exact re-replay idempotency counts;
- fresh-schema semantic mismatch count;
- PostgreSQL version;
- source request count/usage metrics;
- whether the 1,000-candidate target was reached or the direct-instance set returned fewer candidates.

Do not invent a post-hoc auto-admission-rate threshold after seeing the data. The point of this first broad run is to measure the real safe admission/review distribution.

## Zero-tolerance correctness conditions

The slice is not acceptance-ready if any of these occur:

- source-rights gate bypass: >0;
- SailboatData field value entering HullQ evidence/canonical input: >0;
- canonical ID silently reminted for an existing retained QID: >0;
- fuzzy/heuristic forced merge: >0;
- automatic Brand/Organization role inference from manufacturer label alone: >0;
- automatic BoatDesign generation invention from QID existence alone: >0;
- unexpected canonical persistence conflict/error on accepted manifest replay: >0;
- exact replay semantic mismatch: >0;
- fresh-schema semantic mismatch: >0;
- review/non-admitted candidate accidentally persisted as canonical: >0;
- provenance link to nonexistent/wrong-kind canonical target: >0.

A nonzero legitimate `REVIEW_REQUIRED` rate is **not** itself a failure; ambiguity must remain visible rather than be forced through the gate.

## Required tests

At minimum cover:

1. bootstrap discovery performs zero HTTP requests when rights gate is not ALLOWED;
2. bootstrap discovery limit/cap is explicit and bounded;
3. discovery uses deterministic stable ordering before limiting;
4. invalid/duplicate QIDs are handled deterministically without identity merge inference;
5. normal CI does not perform live network access;
6. existing SLICE-0008 <=100 probe semantics remain unchanged;
7. empty/missing source label cannot auto-admit a BoatModel;
8. unique safe candidate produces a schema-valid sparse BoatModel;
9. manufacturer `P176` does not auto-create Brand/Organization or a Brand relationship;
10. QID existence alone does not auto-create BoatDesign;
11. accepted exact source alias remains entity-scoped and does not mutate source spelling;
12. deterministic same-name/search-projection collision routes candidates to review rather than forced merge/split;
13. newly minted HullQ ID is opaque and does not encode name/QID;
14. retained QID mapping is reused exactly on replay;
15. conflicting retained QID mapping fails closed;
16. every auto-admitted BoatModel has supporting retained observation/evidence linkage;
17. ReferenceCrosscheck cannot satisfy admission provenance;
18. review-required candidate is absent from canonical tables;
19. full retained bootstrap manifest validates against its versioned contract/validator;
20. full retained manifest replays against real PostgreSQL 18;
21. exact second replay is idempotent with zero conflicts/errors;
22. fresh-schema replay is semantically equal;
23. no unexpected Brand/Organization/BoatDesign rows are created during Tier-0 model bootstrap;
24. existing ResearchEvidenceBundle and canonical identity persistence tests remain green;
25. retained Stage-2 50-design benchmark remains `G3_PASS`;
26. no SailboatData values are present in bootstrap manifest/evidence;
27. repository validator, formatting, Ruff, strict mypy, branch coverage and dependency audit remain green.

Add narrower tests if implementation evidence exposes another real failure path inside this scope.

## Live-network policy

Normal tests/CI remain offline.

The implementation agent is explicitly authorized to perform the one controlled live Wikidata bootstrap run needed to produce the retained manifest/report, provided:

- the reviewed source rights decision is still ALLOWED;
- the configured User-Agent/contact requirements are satisfied;
- the run remains bounded to the limits in this contract;
- no aggressive retry/concurrency loop is introduced;
- exact source/query/version/timestamp/counts are reported;
- a throttled/failed run is reported honestly rather than hidden.

After the retained manifest exists, acceptance proof must replay that manifest offline against PostgreSQL 18 in CI.

## Expected touch points

Prefer the smallest coherent set, likely including:

- a bounded bootstrap module/runner under `src/hullq/` and/or `scripts/bootstrap/`;
- minimal extension of `src/hullq/sources/wikidata.py` only where the existing <=100 controlled-probe API cannot support the separately authorized broad discovery;
- a versioned bootstrap manifest schema/value object only if needed;
- retained artifacts under `research/bootstrap/wikidata/`;
- focused unit/contract tests;
- real PostgreSQL integration/replay tests;
- CI changes only if needed to replay the retained manifest under the existing PostgreSQL 18 job;
- this slice document / operational status handoff.

Do not create a generic crawler, queue, distributed worker, ORM or identity-resolution service.

## Pre-existing defects discovered and fixed

Before any SLICE-0017 code could run, `src/hullq/sources/wikidata.py` (line ~540, blamed to commit `c4604937`) and `src/hullq/domain/provenance.py` (line ~766, blamed to the original SLICE-0006 commit `c0163795`) each contained an invalid Python-2-style `except A, B:` clause (missing required parentheses around the exception tuple). Both are genuine `SyntaxError`s under CPython 3.14 — confirmed via `ast.parse()` — that made the entire `hullq.domain.provenance` module (and everything importing it, i.e. most of the package) unimportable. Repository truth wins per `CLAUDE.md`; both were corrected to `except (A, B):` before any other SLICE-0017 work began. Separately, the exact pinned toolchain version `ruff==0.16.3` (`uv.lock`) was found to have a reproducible formatter bug that silently strips the required parentheses back off a bare `except (A, B):` (no `as` clause), reintroducing the same `SyntaxError` — confirmed against both the local environment and a clean independent `pip install`. Both corrected lines are marked `# fmt: skip` so `ruff format --check .` does not re-flag/undo the fix; `ruff format --check .` now passes clean across the full repository.

## Measured results — 2026-08-21 live run, corrected 2026-08-21 by offline recompute

The one authorized controlled live run executed successfully (1,000/1,000 candidates, 0 acquisition failures). Independent review then found the collision-detection projection was weaker than the accepted HullQ deterministic search-key semantics (`hullq.domain.identity.generate_search_keys`) and did not consider aliases. Per the review's explicit instruction, the retained manifest was **reclassified offline** (`scripts/bootstrap/wikidata_tier0_runner.py --recompute`, zero network access — the original live acquisition was not repeated) using the corrected collision logic, preserving every already-admitted candidate's exact retained HullQ ID.

Exact measured facts after the offline recompute (see `research/bootstrap/wikidata/manifest.json` / `REPORT.md` for the full retained record):

- live discovery request limit: 1,000 (safety ceiling 1,500, not approached);
- unique QIDs returned: 1,000 (target reached); fetched entities: 1,000; candidates processed: 1,000;
- acquisition failures/throttles/malformed responses: 0;
- candidates auto-admitted as BoatModel: **965** (was 967 before the collision-logic correction);
- candidates `REVIEW_REQUIRED`: **20** (was 18) — all `name_collision`, now detected via the accepted `generate_search_keys` projection (case/whitespace normalization, accepted corporate-suffix stripping, and same-entity aliases) rather than a weaker parallel normalizer;
- candidates `NOT_ADMITTED`: 15 (unchanged, all `missing_label`);
- exact reason counts: `ok`=965, `name_collision`=20, `missing_label`=15;
- **10 complete collision clusters** (retained in `manifest["collision_clusters"]` with their exact shared search key(s)), including two newly caught by the correction that the prior label-only logic missed entirely: `Q109650429`/`Q2461915` ("J-80" vs "J/80", collision found only via `Q2461915`'s retained alias "J-80" exactly matching `Q109650429`'s canonical label) and the other 9 clusters (`flipper`, `etap 28`, `micro`, `dufour 40 performance`, `cavale`, `malibu`, `magnum nova`, `cd1 d2`, `swan 55 frers`);
- retained QID→HullQ-ID crosswalk count: **967** (965 currently admitted + 2 historical IDs preserved-but-not-admitted for the two newly-demoted candidates — never silently reminted, never force-admitted);
- every admitted/previously-admitted ID verified opaque (`BM_WDT0_<uuid4hex>` prefix only, contains neither the source QID nor any substring of the display label) and **byte-for-byte identical** to its pre-correction value for every candidate that remains admitted (zero ID drift, verified programmatically before the corrected manifest was written — see `recompute_manifest_offline`'s refuse-to-overwrite check);
- research observations materialized (offline, dry-run verified): 985 (965 admitted + 20 review-required; the 15 missing-label candidates have no observation);
- canonical evidence links materialized (offline, dry-run verified): 965 (one per currently-admitted BoatModel);
- alias identifiers are now content-derived (`ALIAS-<sha256(name)[:16]>`), not array-position-derived; reordering the same alias set is verified (unit test) to leave every alias's identity unchanged;
- HTTP retrieval count: 21 (1 SPARQL discovery query + 20 wbgetentities batches of ≤50 QIDs, from the original live run — the recompute performed zero HTTP requests);
- extracted record count: 1,000;
- exact acquisition path/version now retained in the manifest itself for audit: SPARQL query version `SLICE-0017-bootstrap-v1`, SPARQL endpoint `https://query.wikidata.org/sparql`, entity API endpoint `https://www.wikidata.org/w/api.php`, entity API version `wbgetentities-labels-aliases-claims-v1`;
- PostgreSQL version, first-replay/re-replay counts, deep semantic readback (canonical-name/alias/evidence-link exact match, canonical BoatModel ID-set exact equality, zero stray Brand/Organization/BoatDesign rows), and fresh-schema full-graph semantic mismatch count: NOT YET OBSERVED against the real production manifest — the strengthened `replay_manifest()` deep-verification code path is covered by real-PostgreSQL integration tests (`tests/persistence/test_wikidata_tier0_bootstrap_integration.py`) exercising the identical function against a small synthetic manifest (including an alias-only collision case), and the full production manifest was independently dry-run materialized offline with zero errors (985/985 bundles, 965/965 admissions, crosswalk-consistent) — but the actual PostgreSQL execution against `research/bootstrap/wikidata/manifest.json` is deferred to CI's `db-integration` job (`scripts/bootstrap/wikidata_tier0_runner.py --replay`, which also now writes `REPLAY-REPORT.md`);
- no post-hoc admission-rate threshold was invented after seeing this data; 96.5% auto-admission at Tier-0 (identity-only) scale is a measured observation, not a pre-committed target.

## Second independent review — 2026-08-21

A second review round found two remaining acceptance blockers plus two audit corrections, all now addressed without changing the 965/20/15 classification or the 10 collision clusters:

1. **PostgreSQL replay isolation.** `replay_manifest()` previously ran its first-pass proof against whatever schema state the connection defaulted to, which is not guaranteed clean (`tests/persistence/` truncates *before* each test but not after, and the benchmark runner truncates only research tables). It now runs the first-pass proof and the independent fresh-schema proof each in their own newly-created, migrated-from-zero, isolated PostgreSQL schema (dropped in a `finally` block), so the acceptance proof cannot be contaminated by prior CI-step state. Every `ImportStatus`/`CanonicalImportStatus` outcome is now explicitly counted (including an unexpected `ALREADY_IMPORTED` on a fresh schema), and the zero-tolerance boolean requires the exact expected imported counts and exact expected canonical BoatModel ID set, not merely an absence of conflict/error counters. A new integration test (`test_replay_is_isolated_from_contaminated_public_schema`) deliberately leaves a synthetic canonical row in the default schema first and proves the isolated replay is still fully clean.
2. **Crosswalk fail-closed + historical retention.** `load_crosswalk_from_manifest` now detects both conflict forms (one QID mapped to two different HullQ IDs; one HullQ ID addressed by two different QIDs) *before* collapsing rows into a dict, validated before any live network request on a rerun. `run_live_bootstrap` now also carries forward any retained candidate whose QID is absent from the current discovery window, unchanged, rather than dropping it — proven by a 3-run regression test (map Q1 → a later window omits Q1 → Q1 reappears and receives its exact original ID).
3. **Acquisition vs. reclassification time.** The manifest now retains `acquired_at` (the original live Wikidata acquisition timestamp, preserved verbatim across every later `--recompute`) separately from `generated_at` (this document's last write time) and `classification_recomputed_at` (set only by `--recompute`). For the current retained manifest, `acquired_at` was recovered from the uniform per-candidate `retrieved_at` history: `2026-08-21T12:52:49.882220+00:00` — the true original live-run timestamp, not the offline recompute time.
4. **CI fixes.** `REPLAY-REPORT.md` is now included in the `bootstrap-outputs` artifact upload; the retained Stage-2 benchmark CI check now requires the recommendation to be exactly `G3_PASS` (not `G3_CANDIDATE`/`HARDEN_FIRST`/`BLOCKED`), consistent with accepted SLICE-0015 G3 passage.

Manifest schema bumped to `0017-v3` (adds `acquired_at`, `classification_recomputed_at`). Local: 1,403 passed, 205 skipped (was 1,397/204); coverage 94.32%; ruff/mypy/validate_repository/pip-audit all clean. The strengthened isolated PostgreSQL replay proof remains pending `db-integration` CI (no local PostgreSQL credentials available to the implementation agent).

## Acceptance criteria

SLICE-0017 is acceptance-ready only when all are true:

- [x] the live rights-cleared direct-instance bootstrap run was executed within the explicit bound, or the slice truthfully stopped `BLOCKED` because the accepted source path materially failed; — executed 2026-08-21, 1000/1000 candidates, see `research/bootstrap/wikidata/manifest.json` / `REPORT.md`;
- [x] up to the first 1,000 deterministic direct-instance candidates were processed (all if fewer than 1,000 were returned); — 1000 processed (target reached);
- [x] a versioned replayable bootstrap manifest + review report are retained; — `research/bootstrap/wikidata/manifest.json` (schema-valid) + `REPORT.md` committed;
- [x] admitted BoatModels use stable opaque retained HullQ IDs not derived from names/QIDs; — verified by unit test and by inspection (`BM_WDT0_<uuid4hex>` prefix only);
- [ ] safe source-backed Tier-0 BoatModels are persisted through the SLICE-0016 boundary, not direct SQL shortcuts; — code path implemented and covered by local PostgreSQL integration tests, but full production-manifest replay against real PostgreSQL has not been directly observed by the implementation agent (no local DB credentials); pending `db-integration` CI;
- [ ] ambiguous candidates remain review/non-admitted rather than being forced; — deterministically proven offline (unit tests); DB-level non-persistence proof pending CI;
- [x] manufacturer/designer source semantics do not silently create Brand/Organization/BoatDesign identities; — `build_admission` never populates brand_relationships/boat_design_ids/brands/organizations, unit-tested;
- [ ] every admitted BoatModel has auditable supporting HullQ observation/evidence linkage; — proven at the code/unit level; real-PostgreSQL confirmation pending CI;
- [ ] exact manifest replay is idempotent with zero unexpected conflicts/errors; — NOT VERIFIED locally (no DB); pending `db-integration` CI;
- [ ] fresh PostgreSQL 18 replay is semantically equal; — NOT VERIFIED locally; pending `db-integration` CI;
- [ ] the existing research persistence and canonical identity persistence suites remain green; — unchanged locally (1403 passed, 205 skipped incl. all persistence tests skipped without a DB); pending `db-integration` CI for actual execution;
- [ ] the retained 50-design benchmark remains `G3_PASS`; — benchmark code untouched by this slice; NOT VERIFIED locally (no DB); pending CI;
- [x] normal CI remains offline with respect to external acquisition; — live acquisition is isolated to `--live` mode of `scripts/bootstrap/wikidata_tier0_runner.py`, never invoked by pytest or the `quality`/`db-integration` CI jobs;
- [ ] exact-head PostgreSQL 18 CI passes; — NOT VERIFIED (not yet observed on the pushed head);
- [x] repository quality gates pass; — local: `uv lock --check`, `validate_repository.py`, `ruff format --check .`, `ruff check .`, `mypy src`, full pytest (1403 passed/205 skipped), `coverage report` (94.32% ≥ 90%), `pip-audit` all PASS; cross-platform (Windows/Ubuntu) CI confirmation still pending;
- [ ] independent review finds no remaining blocker; — first review round's 7 findings and second review round's 2 blockers + 2 audit corrections all addressed; awaiting re-review;
- [ ] project owner explicitly accepts before `DONE`.

## Explicitly out of scope

Do **not** implement or begin:

- 2,500 / 5,000 identity expansion;
- bulk crawling of manufacturer/designer sites;
- ORC ingestion;
- SailboatData ingestion/value persistence;
- fuzzy identity resolution;
- automatic same-name merge/split decisions beyond the deterministic review rule;
- automatic Brand/Organization collapse or role inference;
- automatic BoatDesign generation creation from Wikidata class identity alone;
- NamedVariant / DesignOption enrichment;
- broad Tier-1 technical enrichment;
- keel/rudder/skeg enrichment pass;
- dataset release/snapshot architecture beyond the bootstrap manifest itself;
- query engine / OQ-009 implementation;
- FastAPI public API;
- Astro frontend;
- authentication/accounts;
- marketplace/listing ingestion;
- monitoring/alerts;
- price-history intelligence;
- SEO/public pages;
- distributed infrastructure;
- Powerboat expansion.

## Completion / handoff

The implementation agent MAY move this slice from `READY` to `IN_PROGRESS`, then to `REVIEW` or `BLOCKED` as evidence requires.

The implementation agent MUST NOT mark SLICE-0017 `DONE`.

The implementation agent MUST NOT automatically start 2,500/5,000 expansion or a technical-enrichment slice.

At handoff, report:

- exact branch/head;
- exact live-run parameters and source-rights decision;
- manifest/report paths and counts;
- classification/admission/review counts;
- local validation;
- PostgreSQL replay results;
- exact-head remote CI;
- any source/identity ambiguity discovered;
- the next action supported by measured evidence.

`DONE` requires independent review plus explicit project-owner acceptance.