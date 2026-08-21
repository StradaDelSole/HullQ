# SLICE-0017 — Acceptance Closure

**ID:** SLICE-0017  
**Final status:** DONE  
**Accepted:** 2026-08-21  
**Implementation PR:** #35  
**Accepted implementation head:** `34c2de8fc99ab6babad054a4186cee168cc3a2da`  
**Merge commit:** `e2001d3a926c08706558b6cb97962f235c843379`

## Acceptance result

SLICE-0017 is explicitly accepted by the project owner and closed as `DONE`.

The slice executed HullQ's first controlled broad Stage-3 Wikidata Tier-0 identity bootstrap against the first 1,000 deterministic direct sailboat-class candidates. It retained a replayable source-backed manifest, admitted only safe sparse BoatModel identities through the accepted SLICE-0016 canonical admission boundary, preserved ambiguous candidates for review, and proved the retained result against PostgreSQL 18 with exact replay/idempotency/fresh-schema checks.

It did not infer Brand, Organization, BoatDesign generation, variant or technical completeness from Wikidata identity records.

## Final accepted production measurement

The retained controlled run processed exactly **1,000** candidates:

- `AUTO_ADMIT`: **965**;
- `REVIEW_REQUIRED`: **20**;
- `NOT_ADMITTED`: **15**;
- deterministic collision clusters: **10**;
- retained historical QID→HullQ-ID mappings: **967**;
- retained ResearchObservations / ResearchEvidenceBundles expected on replay: **985**;
- canonical BoatModel admissions / evidence links expected on replay: **965**;
- acquisition failures: **0**;
- live Wikidata retrievals: **21**.

Reason counts in the final retained manifest were:

- `ok`: **965**;
- `name_collision`: **20**;
- `missing_label`: **15**.

The original acquisition timestamp is retained separately from later offline classification/recompute timestamps.

## Final accepted evidence

Exact accepted implementation head:

`34c2de8fc99ab6babad054a4186cee168cc3a2da`

GitHub Actions CI run **#200** (`32499124689`) passed on that exact head.

Verified CI jobs:

- quality / Ubuntu: PASS;
- quality / Windows: PASS;
- dependency audit: PASS;
- db integration / PostgreSQL 18: PASS;
- retained Stage-2 benchmark: PASS with exact recommendation `G3_PASS`;
- SLICE-0017 manifest schema validation: PASS;
- SLICE-0017 production-manifest PostgreSQL replay: PASS;
- SLICE-0017 zero-tolerance verification: PASS.

The exact-head PostgreSQL replay ran against PostgreSQL **18.6** and proved:

### First isolated schema

- expected ResearchEvidenceBundles: **985**;
- imported ResearchEvidenceBundles: **985**;
- bundle already-present/conflict/error/unexpected-status: **0 / 0 / 0 / 0**;
- expected canonical admissions: **965**;
- imported canonical admissions: **965**;
- admission already-present/conflict/reference-error/error/unexpected-status: **0 / 0 / 0 / 0 / 0**;
- deep semantic readback mismatches: **0**;
- unexpected canonical rows for non-admitted candidates: **0**;
- exact canonical BoatModel ID set equality: PASS;
- stray canonical Brand rows: **0**;
- stray canonical Organization rows: **0**;
- stray canonical BoatDesign rows: **0**.

### Exact re-import

- `ALREADY_IMPORTED`: **1,950** total bundle+admission operations;
- conflicts: **0**;
- errors: **0**.

### Independent fresh schema

- ResearchEvidenceBundles imported: **985**;
- canonical admissions imported: **965**;
- semantic mismatches: **0**;
- exact canonical BoatModel ID set equality: PASS;
- stray Brand/Organization/BoatDesign rows: **0 / 0 / 0**;
- expected import counts: PASS.

Final replay result:

`all_zero_tolerance_conditions_clear = true`

## Retained CI artifacts

Bootstrap artifact from exact-head CI #200:

- artifact ID: `9452810477`;
- digest: `sha256:3161e6f43572dcbcafbd6512becc2aea7be44b2f8d1ae56234e49ef37a5eb034`.

The artifact contains the retained manifest/report plus `REPLAY-RESULT.json` and `REPLAY-REPORT.md`.

Retained Stage-2 benchmark artifact from the same exact-head CI:

- artifact ID: `9452803532`;
- digest: `sha256:6cb1414ac7b9c90393ba1545c4fd89adb67fbe298d367d42a29c51775c09684c`.

The retained benchmark remained:

- 50/50 materialized;
- 50/50 first-pass imported;
- 0 first-pass conflicts/errors;
- 50/50 exact re-import `ALREADY_IMPORTED`;
- 50/50 fresh-schema imported;
- 0 semantic mismatches/errors;
- recommendation: `G3_PASS`.

## Final implementation-agent local report

The final narrow CI-fix report stated:

- **1,407 passed, 205 skipped** full suite;
- coverage: **94.29%**;
- `uv lock --check`: PASS;
- repository validator: PASS;
- Ruff lint/format: CLEAN;
- strict mypy: PASS;
- `pip-audit`: no known vulnerabilities.

The real production-manifest PostgreSQL proof was intentionally left to exact-head CI and was subsequently observed as PASS.

## Independent-review hardening retained

SLICE-0017 required several review rounds before acceptance. The accepted implementation now retains the following protections:

1. search-projection collision semantics reuse the accepted HullQ identity/search-key implementation rather than a bootstrap-local approximation;
2. source aliases use stable content-derived alias IDs and are compared losslessly during PostgreSQL readback;
3. the retained QID→HullQ-ID crosswalk fails closed in both conflict directions before live network use;
4. the current bounded candidate set is structurally distinct from the historical retained crosswalk;
5. historical mappings survive discovery-window omission and reuse the byte-identical HullQ ID if the QID later reappears;
6. offline recompute preserves original acquisition identity/timestamp separately from later recompute time;
7. production replay runs in isolated freshly migrated PostgreSQL schemas rather than trusting pre-existing CI database state;
8. first-pass, exact re-import and independent fresh-schema proofs count every relevant importer status and enforce exact expected counts;
9. deep canonical readback checks stable BoatModel IDs, names, aliases, null year/design fields and exact CanonicalEvidenceLink semantics;
10. both replay passes prove no Brand, Organization or BoatDesign rows were inferred;
11. CI keeps the accepted Stage-2 benchmark pinned to exact `G3_PASS`;
12. the final alias-readback regression exercises the actual dict-shaped `fetch_boat_model()` persistence representation.

## Accepted boundary carried forward

The accepted SLICE-0017 baseline consists of:

- the immutable retained SLICE-0017 bootstrap artifact under `research/bootstrap/wikidata/`;
- the 1,000 candidate decisions in that retained run;
- **965** accepted sparse canonical BoatModel identities;
- **20** unresolved review-bound collision candidates;
- **15** non-admitted missing-label candidates;
- **967** retained historical QID→HullQ-ID mappings.

Later expansion work MUST NOT reinterpret this accepted baseline as a disposable rerun. In particular, a later larger discovery window must not silently demote/delete/remint accepted 0017 BoatModels or rewrite the accepted 0017 manifest merely because new candidates appear.

## Next boundary

The next bounded step is:

`SLICE-0018 — Controlled Wikidata Tier-0 2,500-Window Expansion`

Its purpose is to extend the deterministic Wikidata discovery window to at most the first 2,500 direct sailboat-class candidates, process only the expansion delta relative to the accepted 1,000-candidate baseline, preserve all accepted 0017 identities and historical mappings, and measure whether Wikidata alone can continue broadening HullQ's Tier-0 identity universe.

No 5,000 expansion, prior-review resolution campaign, technical enrichment, Brand/Organization inference, BoatDesign-generation work, query engine, API, frontend, marketplace, monitoring or price-history work is authorized merely by closing SLICE-0017.
