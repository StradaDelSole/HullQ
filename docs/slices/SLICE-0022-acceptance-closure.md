# SLICE-0022 — Acceptance Closure

**ID:** SLICE-0022  
**Final status:** DONE  
**Owner accepted:** 2026-08-25  
**Independent-review verdict:** ACCEPT  
**Implementation PR:** #55 — "SLICE-0022: retained alternative-route Tier-0 admission safety pilot"  
**Final reviewed / accepted implementation head:** `912fe8d0542459df7f260eeccd840bb92c00e8d1`  
**Implementation merge commit:** `5d68399e0efb4f6b34b8dae65817b7ced0ca3d07`  
**Exact-head CI:** GitHub Actions run ID `32843428842`, conclusion **SUCCESS**

## Acceptance result

SLICE-0022 is explicitly accepted by the project owner and closed as `DONE`.

The slice ran the exact **57 retained SLICE-0021 alternative-route candidates** through HullQ's accepted Tier-0 identity admission, collision, provenance and PostgreSQL replay boundaries with **zero live acquisition** and no production Wikidata discovery change.

The final accepted decision result is:

```text
AUTO_ADMIT          0
REVIEW_REQUIRED    31
NOT_ADMITTED       26
```

Route-specific result:

- R1: 53 retained candidates → **0 AUTO_ADMIT / 27 REVIEW_REQUIRED / 26 NOT_ADMITTED**;
- R3: 4 retained repair signals → **0 AUTO_ADMIT / 4 REVIEW_REQUIRED / 0 NOT_ADMITTED**;
- R2: no retained candidate in the SLICE-0022 universe.

The accepted canonical BoatModel universe therefore remains exactly **1,770**, and the accepted retained historical QID→HullQ-ID crosswalk remains exactly **1,772** entries.

## Governance correction accepted during review

The first implementation pass applied the pre-existing SLICE-0017/0018 label/collision rule directly to R1 and would have auto-admitted 27 labeled R1 candidates. Independent review identified a material counterexample: `Q232393` ("Zweier-Canadier"), a German canoe-class term whose retained route membership and usable label were insufficient to prove that the entity belonged in HullQ's sailboat-model universe.

That finding established the accepted governance distinction:

- R1 route membership is **discovery-authoritative** for follow-up research;
- R1 route membership is **not admission-authoritative** for automatic canonical creation.

The accepted R1 amendment therefore requires every structurally usable R1 candidate to remain `REVIEW_REQUIRED` with reason:

```text
r1_alternative_route_requires_review
```

The four R3 candidates remain fail-closed `REVIEW_REQUIRED` with:

```text
r3_repair_signal_requires_review
```

Neither R1 nor R3 route membership can itself produce `AUTO_ADMIT`.

## Final retained decision state

Accepted overall counts:

- candidate universe: **57** unique QIDs;
- R1 membership: **53**;
- R3 membership: **4**;
- R2 membership: **0**;
- AUTO_ADMIT: **0**;
- REVIEW_REQUIRED: **31**;
- NOT_ADMITTED: **26**;
- accepted-baseline search-projection collisions: **0**;
- within-57 unresolved search-projection collisions: **0**.

`Q232393` is retained as `REVIEW_REQUIRED` with `hullq_id: null`. No canonical BoatModel was created for it.

The 26 `NOT_ADMITTED` R1 candidates fail closed because no usable retained source-backed label is available under the accepted Tier-0 rules.

## Immutable baseline preserved

The accepted historical boundaries remain unchanged:

```text
retained direct-discovery candidate universe    1,829 QIDs
accepted canonical BoatModel universe           1,770
retained historical QID→HullQ-ID mappings       1,772
```

Accepted manifest digests remain:

- SLICE-0017 manifest SHA256: `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`;
- SLICE-0018 manifest SHA256: `41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`.

The retained SLICE-0021 inputs remained the fixed 57-candidate set. No new QID discovery or refresh occurred in SLICE-0022.

## PostgreSQL 18 replay proof

The final accepted implementation performs the normal offline baseline-first / delta-second PostgreSQL proof:

1. replay accepted SLICE-0017;
2. replay accepted SLICE-0018;
3. verify the exact **1,770** canonical BoatModel baseline before applying SLICE-0022;
4. apply the SLICE-0022 retained admission package;
5. deep-readback retained canonical state;
6. exact re-import;
7. repeat in an independent fresh schema.

Accepted replay result:

```text
prior baseline candidates      1,829
prior canonical admissions     1,770
combined bundles               1,837
combined admissions            1,770
new canonical admissions           0
conflicts                          0
errors                             0
stray rows                         0
all_zero_tolerance_conditions_clear true
```

The crosswalk remains byte-identical to the accepted 1,772-entry baseline crosswalk. No new Brand, Organization or BoatDesign row is created.

## Retained replay-evidence amendment

Final independent review left one narrow governance requirement after the admission-policy correction: checked-in replay evidence had to be verified **before** a fresh replay could overwrite it.

Final amendment head `912fe8d0542459df7f260eeccd840bb92c00e8d1` closed that requirement by adding:

- pure self-consistency verification for retained `REPLAY-RESULT.json` against the already-verified manifest and accepted baseline;
- deterministic pure rendering of `REPLAY-REPORT.md` and byte-for-byte report/result consistency checking;
- `--verify` validation of checked-in replay evidence when present;
- a pre-mutation replay gate that validates existing replay evidence before the first `psycopg.connect()` call;
- tamper tests proving inconsistent retained replay evidence aborts before any database mutation;
- explicit exclusion of accepted nondeterministic runtime metadata (`run_timestamp`, PostgreSQL version and wall-clock duration) from deterministic equality checks.

No admission-policy rule or retained decision changed in this amendment.

## Validation evidence

Final accepted head:

`912fe8d0542459df7f260eeccd840bb92c00e8d1`

Local validation reported:

- `ruff format --check .`: PASS;
- `ruff check .`: PASS;
- `mypy src`: PASS;
- pytest: **1,874 passed, 2 skipped**;
- coverage: **93.97%**;
- `scripts/validate_repository.py`: PASS;
- fresh local PostgreSQL 18.6 replay: PASS.

Exact-head GitHub Actions run `32843428842` passed all four required jobs:

- quality (ubuntu-latest): SUCCESS;
- quality (windows-latest): SUCCESS;
- db integration (PostgreSQL 18): SUCCESS;
- dependency audit: SUCCESS.

Independent review verdict after the final replay-evidence amendment: **ACCEPT**.

Implementation PR #55 was merged as:

`5d68399e0efb4f6b34b8dae65817b7ced0ca3d07`

The project owner explicitly accepted SLICE-0022 on **2026-08-25**.

## No production/canonical scope crossed

SLICE-0022 does **not** authorize or perform:

- production adoption of R1 subclass-closure discovery;
- production adoption of the R3 description/repair rule;
- any change to `WikidataAdapter.discover_sailboat_qids` or the accepted production direct-discovery query;
- live WDQS or `wbgetentities` acquisition;
- manufacturer/archive acquisition;
- Wikipedia, PetScan, DBpedia, SailboatData or search-engine acquisition;
- canonical admission of any of the 57 retained alternative-route candidates;
- creation of new Brand, Organization or BoatDesign identities;
- Tier-1/Tier-2 technical enrichment;
- a review-queue resolution campaign;
- query-engine, API, frontend, marketplace, account, alert, monitoring or price-history implementation.

## Evidence trail

- controlling slice contract: `docs/slices/SLICE-0022-retained-alternative-route-tier0-admission-safety-pilot.md`;
- R1 governance amendment: `docs/slices/SLICE-0022-r1-admission-governance-amendment.md`;
- retained package: `research/bootstrap/wikidata/sl0022-alt-route-admission/`;
- implementation PR: #55;
- final reviewed / accepted implementation head: `912fe8d0542459df7f260eeccd840bb92c00e8d1`;
- exact-head CI run ID: `32843428842`, SUCCESS;
- independent-review verdict: **ACCEPT**;
- implementation merge commit: `5d68399e0efb4f6b34b8dae65817b7ced0ca3d07`;
- project-owner acceptance: **2026-08-25**.

## Next boundary

No SLICE-0023 or later slice is made `READY` by this closure.

The accepted result establishes that the retained R1/R3 alternatives are useful **discovery/review signals**, but not safe automatic canonical-admission routes under the current evidence boundary. A future production-route decision, review workflow, additional authoritative evidence path or Stage-3.3 enrichment step requires its own bounded readiness contract, explicit acceptance criteria and the normal `START_SLICE.bat` workflow.

No later slice begins automatically.
