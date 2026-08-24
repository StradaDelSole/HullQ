# SLICE-0020 — Acceptance Closure

**ID:** SLICE-0020  
**Final status:** DONE  
**Owner accepted:** 2026-08-24  
**Independent-review verdict:** ACCEPT  
**Original implementation/research PR:** #47 — "SLICE-0020: manufacturer archive source clearance + bounded identity pilot"  
**Final reviewed / accepted implementation-research head:** `ced18800c20a6a2c328794d3af5cb0686d59c20d`  
**Implementation/research merge commit:** `5c2a9cc40a05fbaebe2a4db2bcfff7d3498a58d9`  
**Exact-head CI:** GitHub Actions run #250, run ID `32727915597`, conclusion **SUCCESS**

## Acceptance result

SLICE-0020 is explicitly accepted by the project owner and closed as `DONE`.

The slice assessed use-specific rights/access clearance for a fixed, precommitted sample of ten manufacturer/heritage archive surfaces and ran a strictly bounded (<=20 model identities per source, <=200 total), research-only identity-yield pilot against those same surfaces, measuring overlap against the accepted SLICE-0017/0018 1,770 AUTO_ADMIT BoatModel universe. It is a source-clearance and identity-yield research slice: it created and modified no canonical HullQ Brand, Organization, BoatModel or BoatDesign row, performed no automated/bulk acquisition, and did not build or stage a production adapter.

Exact-head CI on the final accepted head (`ced18800c20a6a2c328794d3af5cb0686d59c20d`) — run #250 / ID `32727915597` — passed with all jobs `SUCCESS`: quality (ubuntu-latest), quality (windows-latest), db integration (PostgreSQL 18), dependency audit.

## Final retained research state (as of the accepted head)

- fixed sources assessed: **10**;
- source-clearance result: **0** `ADAPTER_READY`, **9** `RESEARCH_ONLY` / `REVIEW_REQUIRED`, **1** `BLOCKED` (Bénéteau);
- bounded identity pilot: **100** total identities retained (10 per source, within the <=20/source, <=200-total cap);
- exact-overlap result against the accepted 1,770 BoatModel universe: **9** `exact_overlap`, **91** `no_exact_overlap_signal`, **0** `unresolved_possible_overlap`;
- accepted exact overlaps: Catalina 16.5, Catalina 18, Catalina 25, Catalina 27, Catalina 28, Pearson 26, Pearson 30, Pearson 303, Hallberg-Rassy 40.

A truthful result of zero `ADAPTER_READY` sources is a fully valid, expected outcome under the slice's own "Classification vocabulary" test; it was not padded or rounded up to avoid reporting it.

## Research ownership boundary

ChatGPT performed the external research/orchestration pass — visiting the ten fixed-sample manufacturer/heritage archive surfaces, reading terms/robots/licence evidence, and discovering the bounded model-identity sample. Claude performed repository integration/deterministic computation/validation only: transcribing supplied findings into the accepted schema/data structures, writing and running the deterministic overlap computation against the accepted SLICE-0017/0018 manifests, validating both retained JSON documents against strict schemas, writing and running the pytest reproducibility/invariant suite, and writing the human-readable report. Claude performed no independent external research for the retained research result.

## Retained rights and identity semantics

- **Access is not reuse.** Public/manual readability, robots/API/automation posture and copyright/licence/database reuse rights were recorded and judged separately for every source.
- **Clearance is use-specific and fails closed.** Each source received an independent judgment across the seven accepted HullQ clearance keys; absent, thin or ambiguous evidence was recorded as `unknown` / `REQUIRES_REVIEW`, never rounded up.
- **Public readability alone never implied systematic-use permission.** No source reached `CLEARED` merely because a page was publicly viewable.
- **Bénéteau is `BLOCKED`** for the contemplated automated archive-adapter use: its retained Terms of Use explicitly prohibit technical-protocol indexing/extraction and substantial-portion database extraction without prior written consent (`automated_ingestion = prohibited`, `bulk_bootstrap = prohibited`).
- The other nine sources remain research-only/review-required; none satisfied the full `ADAPTER_READY` test (`identity_seed = allowed` and `automated_ingestion = allowed`, no contradictory access/permission field, and either `bulk_bootstrap = allowed` or documented bounded/non-bulk conditions).
- **`no_exact_overlap_signal` carries only its narrow defined meaning** — absence of an exact/unambiguous overlap signal under this bounded probe. It does not prove global novelty, does not prove no matching HullQ BoatModel exists, and does not authorize canonical admission.
- Matching used exact/case-insensitive comparison only, with surrounding-whitespace trimming and no internal-whitespace collapsing: no fuzzy matching, no manufacturer-prefix insertion/removal, no token reordering, no punctuation rewriting.
- Reused model numbers/generations and brand-vs-yard relationship hazards (Bénéteau "First N" numbering, Grand Soleil "GS N" abbreviation, Westerly no-prefix names, Pearson mixed-rightsholder archive, Hallberg-Rassy narrow newsletter permission) were preserved as explicit review notes, not silently resolved.

## Amendment / review history

1. **Initial independent review → AMEND.** The initial research/implementation head (`1ca06c3`) was independently reviewed and returned an `AMEND` verdict rather than immediate acceptance.
2. **First amendment (`44ed42c`, PR #47)** corrected Elan and Hallberg-Rassy source-surface provenance, removed the unsupported Elan E3 timeline/identity hazard and the unsupported Bénéteau "First 32"/"First 38" era-mismatch hazard (both unsupported by the official heritage pages once checked), and tightened `compute_overlap.py`'s exact-match implementation so that it trims only surrounding whitespace and never collapses internal whitespace, matching the slice's accepted exact-match semantics. No rights classification changed, and the regenerated overlap totals (9 / 91 / 0) were confirmed unchanged after the stricter implementation was applied.
3. **Second, docs-only amendment (`ced1880`)** corrected the report's own characterization of amendment correction #5 (the exact-match implementation fix), clarifying that it was an implementation correction to `compute_overlap.py`'s `normalize()` function, not a wording-only change, while confirming no rights classification or overlap total changed as a result.
4. **Final independent review → ACCEPT.** The corrected head (`ced18800c20a6a2c328794d3af5cb0686d59c20d`) was independently re-reviewed and found to satisfy the slice's acceptance criteria.
5. Implementation/research PR #47 was merged to `main` as `5c2a9cc40a05fbaebe2a4db2bcfff7d3498a58d9`.
6. The project owner then explicitly accepted the slice on 2026-08-24.

## No production/canonical scope crossed

- no production adapter was built or staged;
- no automated/bulk acquisition was performed against any of the ten sources;
- no canonical Brand/Organization/BoatModel/BoatDesign row was created or modified;
- no SailboatData value was used as production evidence anywhere in this slice's outputs;
- no subjective bluewater/offshore/luxury suitability classification was introduced by HullQ (a supplied research finding for Oyster Yachts truthfully quotes that manufacturer's own marketing self-description, consistent with existing SLICE-0019 `registry.json` precedent);
- accepted SLICE-0019 retained artifacts (`research/manufacturers/registry.json`, `registry_schema.json`, `source_yield_study.json`, `overlap_result.json`, `REPORT.md`) were not modified;
- SLICE-0021 was not created or started.

## Evidence trail

- Initial research/implementation execution: PR #47, head `1ca06c3` — placed `REVIEW`.
- Independent review verdict: **AMEND**.
- Amendment implementation: `44ed42c` — corrected the findings described above.
- Docs-only follow-up correction: `ced1880` — corrected the report's own AMEND-note characterization of correction #5.
- Final reviewed / accepted head: `ced18800c20a6a2c328794d3af5cb0686d59c20d`.
- Independent-review verdict on the final head: **ACCEPT**.
- Implementation/research PR #47 merged into `main` as `5c2a9cc40a05fbaebe2a4db2bcfff7d3498a58d9`.
- Exact-head CI on the final accepted implementation/research head `ced18800c20a6a2c328794d3af5cb0686d59c20d`: GitHub Actions run #250, run ID `32727915597`, conclusion **SUCCESS** — quality (ubuntu-latest) SUCCESS, quality (windows-latest) SUCCESS, db integration (PostgreSQL 18) SUCCESS, dependency audit SUCCESS.
- Project owner acceptance: 2026-08-24.

## Next boundary

No SLICE-0021 or other later slice is made `READY` by this closure.

This closure does not authorize a production archive-adapter build, automated/bulk acquisition from any assessed source, a bounded permission/partnership outreach step, an alternative-cleared-source Stage-3 direction, broad Tier-1/Tier-2 technical enrichment, a review-queue campaign, query-engine/API/frontend work, marketplace/dealer integration, or accounts/alerts/monitoring/price-history work. Any next Stage-3 step requires its own bounded contract, source-rights analysis where applicable, explicit acceptance criteria and the normal `START_SLICE.bat` workflow.
