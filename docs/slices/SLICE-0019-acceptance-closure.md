# SLICE-0019 — Acceptance Closure

**ID:** SLICE-0019  
**Final status:** DONE  
**Owner accepted:** 2026-08-23  
**Independent-review verdict:** ACCEPT — all 16 SLICE-0019 acceptance criteria PASS  
**Original research PR:** #42 — "SLICE-0019: global series-sailboat manufacturer universe research"  
**Original research merge commit:** `dd4caebb4859ef3404afbc8e8d107cfcccd22969`  
**Amendment PR:** #43 — "SLICE-0019 independent-review amendment (REVIEW, not DONE)"  
**Final reviewed / accepted amendment head:** `98a8916b7634250cf6540ea21abe497b2d664234`  
**Amendment merge commit:** `0f8b94609c6d0886b72caa521f6ee9d5258f0d0f`  
**Post-merge CI:** run ID `32653479069`, conclusion **SUCCESS**

## Acceptance result

SLICE-0019 is explicitly accepted by the project owner and closed as `DONE`.

The slice built the first bounded global research wave of the series-sailboat manufacturer/yard universe (active and historical), plus a 20-entity source-yield study and an exact/unambiguous overlap check against the accepted SLICE-0017/0018 Wikidata universe. It is a research/source-mapping slice: it created and modified no canonical HullQ Brand, Organization, BoatModel or BoatDesign rows and did not ingest a new production dataset.

Research execution (PR #42) was merged to `main` first and placed in `REVIEW`, not `DONE`, pending independent review. Independent review found seven required corrections (evidence-backed relationships dropped to `[]`, two production-era facts degraded to unknown, mixed model-yield semantics, an inflated heritage/archive-surface count, missing verified-record evidence invariants, an undocumented source-yield vocabulary, and no reproducibility proof for the generator chain). A dedicated amendment (PR #43) corrected all seven findings without broadening the research universe, was independently re-reviewed, and was found to satisfy all 16 SLICE-0019 acceptance criteria. The project owner then accepted the amended slice.

## Final retained research state (as of the accepted amendment head)

- total retained research records: **136**;
- verified: **129**;
- needs_review: **1**;
- excluded: **6**;
- strict verified manufacturer/yard floor: **121** (floor >=120: PASS);
- countries represented by strict floor records: **25** (floor >=20: PASS);
- macro-regions represented: **8** (floor >=5: PASS);
- historical/defunct/acquired/renamed strict-floor records: **61** (floor >=40: PASS);
- strict-floor records with a recognized official/heritage archive surface under the corrected strict definition: **61** (floor >=25: PASS) — corrected from an earlier misreported **107**, which had incorrectly treated any non-empty `other_archive_sources` (including internal RESEARCH-007..009 research-batch packets) as a recognized external archive surface;
- 20-entity source-yield sample: complete and reproducible from cited evidence;
- overlap probe against the accepted SLICE-0017/0018 1,770 AUTO_ADMIT union: **57** probed model identities, **8** exact overlaps, **0** unresolved possible overlaps, **49** clearly new candidates in this bounded exact-label probe.

`clearly new` in the overlap probe has the narrow meaning defined in the retained report: absent from the accepted exact preferred-label set and from the retained alias/case-only hint sets within this bounded probe. It does not prove global novelty and does not by itself authorize canonical admission.

## Notes carried forward for future work

- **Columbia Yachts** remains a retained research `needs_review` record because the recovered evidence collapses the original manufacturer and a later revival into one record. This does not invalidate slice acceptance; it is retained review-bound rather than forced to a resolution the evidence does not support.
- **Rights/access status remains separate from public readability.** Every source's `systematic_use_status` assessment (`CLEARED` / `REQUIRES_REVIEW` / `BLOCKED` / `UNKNOWN`) is a distinct judgment from whether the page was publicly viewable during research, and this closure does not convert bounded research access into blanket authorization for future systematic/bulk ingestion from any source in the registry.
- The removable **temporary external reference** used during research remained discovery/gap-detection input only; it is not evidentiary and no registry decision relies on it as a source of record.
- **No SailboatData value was used as HullQ production evidence** anywhere in the retained registry.
- SLICE-0019 created and modified **no** canonical Brand, Organization, BoatModel or BoatDesign rows, and did not remap or resolve the SLICE-0017/0018 review queues.

## Evidence trail

- Original research execution: PR #42, merged as `dd4caebb4859ef3404afbc8e8d107cfcccd22969` (2026-08-23), placed `REVIEW`.
- Independent review identified seven required corrections (relationship retention, production-era/fact retention, model-yield semantics, heritage/archive floor calculation, verified-record evidence invariants, source-yield study contract hardening, generator-chain reproducibility testing) plus governance/status-document accuracy.
- Amendment implementation head: `f9db9e946a6ef53cdbd24f566693316622ea5fca` — corrected all seven findings. CI on this head failed one Windows-only job on a text-mode line-ending artifact in the new reproducibility test (no content/research defect).
- Final reviewed amendment head: `98a8916b7634250cf6540ea21abe497b2d664234` — one follow-up commit normalizing line-ending handling in the reproducibility test only; no research/implementation file changed. CI run `32651630361`: quality (windows-latest) PASS, quality (ubuntu-latest) PASS, db integration (PostgreSQL 18) PASS, dependency audit PASS.
- Independent-review verdict on `98a8916b7634250cf6540ea21abe497b2d664234`: **ACCEPT** — all 16 SLICE-0019 acceptance criteria satisfied.
- Amendment PR #43 merged into `main` as `0f8b94609c6d0886b72caa521f6ee9d5258f0d0f` (parents: `dd4caebb4859ef3404afbc8e8d107cfcccd22969` and `98a8916b7634250cf6540ea21abe497b2d664234` — exact expected head, no drift).
- Post-merge CI on `main`: run ID `32653479069`, conclusion **SUCCESS**.
- Project owner acceptance: 2026-08-23.

## Next boundary

No SLICE-0020 or other later slice is made `READY` by this closure.

Any next Stage-3 step — for example a controlled manufacturer-archive identity expansion, a Tier-1 technical-enrichment pilot, a manufacturer/brand/yard relationship-hardening prerequisite, or another rights-cleared structured identity source — requires its own bounded contract, source-rights analysis where applicable, explicit acceptance criteria and the normal `START_SLICE.bat` workflow.

This closure does not authorize a new production-source ingestion, broad Tier-1/Tier-2 technical enrichment, a review-queue campaign, query-engine/API/frontend work, marketplace/dealer integration, or accounts/alerts/monitoring/price-history work.
