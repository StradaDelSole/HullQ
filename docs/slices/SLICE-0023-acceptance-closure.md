# SLICE-0023 — Acceptance Closure

**ID:** SLICE-0023  
**Final status:** DONE  
**Owner accepted:** 2026-08-25  
**Independent-review verdict:** ACCEPT  
**Implementation PR:** #61 — "SLICE-0023: Wikimedia category identity-lead discovery pilot"  
**Final reviewed / accepted implementation head:** `92dc0320e995542226199509fc7236f29a75a254`  
**Implementation merge commit:** `ac2868d978f33f42ccc7e9cc2b1885bfa86b23bb`  
**Exact-head CI:** GitHub Actions run ID `32867281346`, conclusion **SUCCESS**  
**Companion reproducibility CI:** run ID `32867282317`, conclusion **SUCCESS**

## Acceptance result

SLICE-0023 is explicitly accepted by the project owner and closed as `DONE`.

The slice measured one fixed, bounded English-Wikipedia category-discovery path strictly as a **research-lead source** over exactly:

- `Category:Keelboats`;
- `Category:Catamarans`;
- `Category:Trimarans`.

Wikipedia category/page metadata was never promoted to canonical HullQ evidence. No article prose, infobox value, table, image or reference content became HullQ evidence or production data.

The accepted source-level research recommendation is:

```text
FOLLOWUP_VERIFICATION_CANDIDATE
```

This is a research recommendation only. It does not authorize production Wikipedia/Wikimedia discovery, canonical admission, Stage-3.3 enrichment or a later slice.

## Final measured result

The accepted one-shot live acquisition retained:

```text
Keelboats category members                 930
Catamarans category members                116
Trimarans category members                  86
combined memberships before dedup        1,132
unique pages                              1,131
cross-category duplicate page IDs            1
duplicate QIDs                                0
```

Overlap against the immutable accepted Stage-3.2 boundaries:

```text
accepted_direct_qid_overlap               717
retained_alternative_qid_overlap            4
incremental_qid_lead                      409
no_wikidata_qid                             1
```

Exact title-signal probe, using only `value.strip().casefold()`:

```text
exact_signal_other_qid                      0
no_exact_signal                            414
unresolved_structural                       0
```

The deterministic SHA256-ordered quality sample contained exactly 150 incremental QIDs:

```text
Trimarans                                  30
Catamarans                                 30
Keelboats                                  90
total                                     150
```

Final accepted manual quality review after independent-review amendment:

```text
plausible_model_or_class_lead             102   68.00%
obvious_out_of_scope                       19   12.67%
ambiguous                                  29   19.33%
```

Because the unique incremental yield is 409 (>=100), rights/access conditions remain satisfied, and the plausible share is 68.00% (>=50%), the precommitted mechanical recommendation remains `FOLLOWUP_VERIFICATION_CANDIDATE`.

## Immutable comparison boundaries preserved

The accepted historical boundaries reproduced exactly before live acquisition and remain unchanged:

```text
retained direct-discovery candidates     1,829 QIDs
accepted canonical BoatModels            1,770
historical QID -> HullQ-ID mappings       1,772
SLICE-0021 alternative-route union           57 QIDs
```

Accepted retained fingerprints remained:

- SLICE-0017 manifest SHA256: `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`;
- SLICE-0018 manifest SHA256: `41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`;
- SLICE-0021 `discovery_probe.json` Git blob: `16af426991214c445a3c152aacbe56b8088958d6`;
- SLICE-0021 `sampled_candidates.json` Git blob: `5b56851f0c719b8dcf830fcd0416471c6c60596c`.

SLICE-0023 created no canonical identity and did not alter the accepted 1,772-entry historical crosswalk.

## Source-rights and request boundary

Accepted live hosts and request counts:

```text
en.wikipedia.org       27 requests   ceiling 75
www.wikidata.org        3 requests   ceiling 10
total                   30 requests   ceiling 85
```

The final amendment structurally reconciles the 27 Wikipedia requests as:

```text
fixed category requests      4
pageprops requests           23  = ceil(1,131 / 50)
total Wikipedia requests     27
```

Wikipedia remains limited to research-lead use under the retained Source record. Wikidata CC0 was used only for the deterministic <=150-QID quality sample context.

## Independent-review amendment

The initial implementation head `2913d9aea01dfa6b2b56e2abb4db20862d8ad165` passed exact-head CI but independent review returned `AMEND` for retained-evidence verification and four overly generous manual quality judgments.

Final amendment head `92dc0320e995542226199509fc7236f29a75a254` closed those findings without any second live acquisition by adding:

- exact `wikidata_context` coverage verification against the selected sample, rejecting missing, extra or duplicate QIDs;
- independent `rights_access_ok` recomputation from the reviewed Source records plus retained rights gate;
- fail-closed rejection when the retained rights gate disagrees with Source records;
- structural Wikipedia request reconciliation from category counts and pageprops batch arithmetic;
- additional end-to-end tamper tests covering QID mapping, context coverage, request breakdown and coherent rights/recommendation/digest manipulation;
- conservative re-review of `Q92475330`, `Q112632201`, `Q114568605` and `Q119855214`, moving all four from `plausible_model_or_class_lead` to `ambiguous` because retained per-entry evidence did not independently prove model/class status.

The quality result therefore changed from 106/19/25 to the accepted **102 plausible / 19 out-of-scope / 29 ambiguous**, while the 409-lead yield and final recommendation remained unchanged.

## Validation evidence

Final accepted head:

`92dc0320e995542226199509fc7236f29a75a254`

Local validation reported:

- repository validator: PASS;
- `ruff format --check .`: PASS;
- `ruff check .`: PASS;
- `mypy src`: PASS (37 source files);
- pytest: **1,790 passed, 209 skipped**;
- coverage: **93.10%** (>=90% floor);
- offline retained-package `--verify`: PASS with zero mismatches.

Exact-head GitHub Actions run `32867281346` passed all required jobs:

- quality (ubuntu-latest): SUCCESS;
- quality (windows-latest): SUCCESS;
- db integration (PostgreSQL 18): SUCCESS;
- dependency audit: SUCCESS.

Companion manufacturer-artifact reproducibility run `32867282317` passed on Ubuntu and Windows.

Independent review verdict after the amendment: **ACCEPT**.

Implementation PR #61 was merged as:

`ac2868d978f33f42ccc7e9cc2b1885bfa86b23bb`

The project owner explicitly accepted SLICE-0023 on **2026-08-25**.

## No production/canonical scope crossed

SLICE-0023 does **not** authorize or perform:

- production Wikipedia/Wikimedia identity discovery;
- canonical admission of any of the 409 incremental QID leads;
- creation or modification of canonical Brand, Organization, BoatModel or BoatDesign rows;
- minting HullQ IDs for new leads;
- modification of the accepted historical crosswalk;
- production Wikidata discovery-query changes;
- article-prose or infobox ingestion;
- recursive/non-English Wikipedia category expansion;
- resolution of prior review queues;
- Tier-1/Tier-2 technical enrichment;
- query-engine, API, frontend, marketplace, account, monitoring or price-history implementation.

## Evidence trail

- controlling contract: `docs/slices/SLICE-0023-wikimedia-category-identity-lead-discovery-pilot.md`;
- retained package: `research/bootstrap/wikimedia/sl0023-category-leads/`;
- implementation PR: #61;
- final reviewed / accepted implementation head: `92dc0320e995542226199509fc7236f29a75a254`;
- exact-head CI run ID: `32867281346`, SUCCESS;
- companion reproducibility run ID: `32867282317`, SUCCESS;
- independent-review verdict: **ACCEPT**;
- implementation merge commit: `ac2868d978f33f42ccc7e9cc2b1885bfa86b23bb`;
- project-owner acceptance: **2026-08-25**.

## Next boundary

The accepted result establishes that the bounded Wikimedia category path has enough incremental yield and sample quality to justify a **separate future verification decision**. It does not itself authorize that verification campaign, production adoption or canonical admission.

No SLICE-0024 or later slice is made `READY` by this closure.

No later slice begins automatically.
