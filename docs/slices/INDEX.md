# HullQ Slice Index

**Status:** ACTIVE execution board  
**Updated:** 2026-08-26 — SLICE-0025 accepted / `DONE` (`BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL`); SLICE-0026 bounded Wikidata Tier-1 enrichment evidence pilot handed off `REVIEW`

This file is the **compact operational queue**, not the historical evidence archive. Detailed implementation/review history belongs in each slice contract, acceptance-closure document, retained research package and Git history. Agents should read this file only when queue/status context is actually needed.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Repository bootstrap, locked toolchain and cross-platform CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | DONE | Independent sailboat-design source research and seed evidence | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | DONE | Canonical JSON-Schema contract runtime | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | DONE | Measurement observation + deterministic normalization | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | DONE | Brand/Organization + BoatModel/BoatDesign identity contracts and search labels | SLICE-0004 / ADR-0011 |
| SLICE-0006 | IMPLEMENTATION | DONE | FieldEvidence/FieldResolution provenance boundary | SLICE-0005 / ADR-0006 |
| SLICE-0007 | IMPLEMENTATION | DONE | ResearchJob + source-rights/use gate + extraction telemetry | SLICE-0006 / ADR-0005 |
| SLICE-0008 | IMPLEMENTATION | DONE | First rights-gated real adapter: Wikidata CC0 | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | DONE | Appendage/configuration normalization | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | DONE | `hullq-derived-1.0.0` derived metrics | SLICE-0009 / ADR-0008 |
| SLICE-0011 | DESIGN_RESEARCH | DONE | Controlled 50-design real-web stress benchmark | SLICE-0010 |
| SLICE-0012 | IMPLEMENTATION | DONE | Pre-canonical observations, claim/applicability semantics, promotion and ResearchEvidenceBundle | SLICE-0011 |
| SLICE-0013 | IMPLEMENTATION | DONE | PostgreSQL 18 research persistence + deterministic importer | SLICE-0012 |
| SLICE-0014 | DESIGN_RESEARCH | DONE | Retained 50-design benchmark through real PostgreSQL persistence | SLICE-0013 |
| SLICE-0015 | IMPLEMENTATION | DONE | Negative-path hardening + fixed Stage-2 G3 decision | SLICE-0014 |
| SLICE-0016 | IMPLEMENTATION | DONE | Canonical identity PostgreSQL persistence + Tier-0 admission boundary | SLICE-0015 / G3 PASS |
| SLICE-0017 | IMPLEMENTATION | DONE | Controlled Wikidata Tier-0 1,000-candidate identity bootstrap | SLICE-0016 |
| SLICE-0018 | IMPLEMENTATION | DONE | Baseline-preserving Wikidata expansion to first <=2,500 discovery window | SLICE-0017 |
| SLICE-0019 | DESIGN_RESEARCH | DONE | Global active+historical series-sailboat manufacturer/yard universe + source-yield study | SLICE-0018 |
| SLICE-0020 | DESIGN_RESEARCH | DONE | Manufacturer archive source-clearance + bounded identity-yield pilot | SLICE-0019 |
| SLICE-0021 | DESIGN_RESEARCH | DONE | Alternative Wikidata sailboat-class discovery-semantics pilot | SLICE-0020 |
| SLICE-0022 | IMPLEMENTATION | DONE | Offline admission-safety pilot over exact 57 retained alternative-route candidates | SLICE-0021 |
| SLICE-0023 | DESIGN_RESEARCH | DONE | Bounded English-Wikipedia category identity-lead discovery pilot | SLICE-0022 |
| SLICE-0024 | DESIGN_RESEARCH | DONE | Deterministic 30-QID independent identity-verification/source-cost pilot over accepted SLICE-0023 leads | SLICE-0023 accepted / DONE |
| SLICE-0025 | VALIDATION | DONE | Stage-3.2 breadth-sufficiency / Stage-3.3 parallel-entry governance decision over accepted SLICE-0018/0020/0021/0022/0023/0024 evidence | SLICE-0024 accepted / DONE |
| SLICE-0026 | IMPLEMENTATION | REVIEW | Bounded Wikidata Tier-1 (LOA/LWL/beam/draft/displacement) enrichment evidence pilot over exactly 100 already-canonical BoatModels | SLICE-0025 accepted / DONE |

## Current execution rule

**SLICE-0001 through SLICE-0025 are accepted / `DONE`. SLICE-0026 is handed off `REVIEW`; it is not yet independently reviewed or project-owner accepted, so it is not `DONE`. No SLICE-0027 or later slice is authorized.**

For an already completed slice, its `*-acceptance-closure.md` is the final acceptance-state record. A primary slice contract may still show its historical implementation handoff state (`REVIEW`); the acceptance closure plus this operational queue control the final operational `DONE` state.

## Latest accepted result — SLICE-0024

SLICE-0024 is a bounded `DESIGN_RESEARCH` verification-source pilot over exactly 30 deterministic candidates drawn from the accepted SLICE-0023 150-QID quality sample. It did **not** research all 409 Wikimedia leads.

The project owner explicitly accepted SLICE-0024's **corrected blocked finding** as `DONE`: its primary contract retains historical status `BLOCKED` (two candidates, `Q119855214`/`Q30681833`, truly exceeded the fixed per-candidate search-query ceiling during original execution and an independent-review round corrected an omitted-action/overstated-evidence finding), but the bounded research slice is complete and its negative/blocked outcome is the accepted final result.

Accepted result:

```text
threshold set (24 prior plausible+ambiguous candidates):
  independently supported in_scope_identity   11  (>=12 required -- NOT MET)
  of those, strong_source                     10  (>=8 required)
  median combined actions (supported in-scope) 2.0  (<=4 required)
recommendation  LOW_INDEPENDENT_VERIFICATION_YIELD
```

This is research-only: it does not authorize a full 409-lead verification campaign, canonical admission, production Wikipedia/Wikimedia use or Stage-3.3 enrichment. Canonical BoatModels remain exactly **1,770** and the historical crosswalk exactly **1,772**.

Acceptance evidence:

- implementation PR #67; final reviewed head `50d20588aa8f6feaffe83212f4e2b3dad2cb27c2`;
- exact-head workflow-dispatch CI `32896517734` / manufacturer reproducibility `32896520470`: SUCCESS;
- PR CI `32899092183` / manufacturer reproducibility `32899092226`: SUCCESS;
- independent-review verdict: **ACCEPT of corrected BLOCKED result**;
- implementation merge `eba0a77d4241514d53ae341439a2109db0f418a3`;
- owner acceptance **2026-08-25**;
- closure: `docs/slices/SLICE-0024-acceptance-closure.md`.

Retained package: `research/bootstrap/wikimedia/sl0024-independent-verification/`.

## SLICE-0025 — breadth/enrichment entry decision, `REVIEW`

SLICE-0025 is a bounded `VALIDATION` slice: using only already-accepted SLICE-0018/0020/0021/0022/0023/0024 evidence (no new external research, no canonical mutation), it reproduces the fixed accepted evidence boundary from retained artifacts and mechanically applies a precommitted decision rule.

Reproduced boundary (zero drift):

```text
accepted canonical BoatModels                              1,770
historical QID -> HullQ-ID mappings                        1,772
SLICE-0018 direct-discovery unique QIDs / requested limit   1,829 / 2,500
SLICE-0020 ADAPTER_READY archive sources                        0
SLICE-0021 alternative-route candidate union                   57
SLICE-0022 AUTO_ADMIT / REVIEW_REQUIRED / NOT_ADMITTED       0 / 31 / 26
SLICE-0023 incremental Wikimedia QID leads                    409
SLICE-0024 threshold-set independently-supported / required   11 / 12
SLICE-0024 final recommendation      LOW_INDEPENDENT_VERIFICATION_YIELD
```

None of the four known Stage-3.2 breadth mechanisms (larger SLICE-0018 direct-discovery limit, SLICE-0020 manufacturer/archive bulk bootstrap, SLICE-0021/0022 alternative Wikidata route, SLICE-0023/0024 full Wikimedia-lead campaign) qualifies as an unexecuted, already-cleared, materially-different, >=100-yield route. All accepted parallel-readiness conditions are met, so the mechanically derived decision is:

```text
BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL
```

This does **not** declare Stage 3.2 complete, does not declare G4 passed, and does not itself authorize any enrichment, admission, query-engine, API, frontend or other implementation work. Stage 3.2 breadth work remains explicitly open. It permits only a later, separately readied slice to pilot a bounded Stage-3.3 Tier-1/basic enrichment subset.

Retained package: `research/stage3/sl0025-breadth-enrichment-entry/` (`decision_input.json`, `decision_result.json`, `REPORT.md`, `ARTIFACT-DIGESTS.json` plus their JSON schemas), reproducible offline via `scripts/bootstrap/sl0025_breadth_enrichment_entry_decision_runner.py --verify`.

Primary contract: `docs/slices/SLICE-0025-stage-3-2-breadth-sufficiency-stage-3-3-parallel-entry-decision.md`.

SLICE-0025 is accepted / `DONE` (see `docs/slices/SLICE-0025-acceptance-closure.md`).

## Latest handoff — SLICE-0026 (`REVIEW`, not yet accepted)

SLICE-0026 is a bounded Stage-3.3 evidence-path pilot (not a canonical technical-resolution rollout) over exactly 100 already-canonical BoatModels selected deterministically from the accepted 1,770/1,772 identity boundary. It fetches only those known QIDs via the existing rights-gated Wikidata `wbgetentities` adapter (no discovery query) and measures per-field coverage for LOA/LWL/beam/draft/displacement only. It creates/mutates no canonical BoatModel/BoatDesign row and mints no BoatDesign ID.

Retained package: `research/stage3/sl0026-wikidata-tier1-enrichment/` (`selection.json`, `evidence_manifest.json`, `REPORT.md`, `ARTIFACT-DIGESTS.json`, `REPLAY-RESULT.json`/`REPLAY-REPORT.md` plus JSON schemas), reproducible offline via `scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py --verify`.

Primary contract: `docs/slices/SLICE-0026-bounded-wikidata-tier1-enrichment-evidence-pilot.md`.

This entry records the implementation agent's own measurement and does not itself constitute independent review or project-owner acceptance. SLICE-0026 is `REVIEW`, not `DONE`. No SLICE-0027 or later slice is created/started.

## Latest accepted boundary — SLICE-0023

SLICE-0023 tested exactly three English-Wikipedia main-namespace category roots as a **research-lead surface only**:

```text
Category:Keelboats
Category:Catamarans
Category:Trimarans
```

Accepted result:

```text
unique pages                         1,131
incremental QID leads                  409
quality sample                         150
  plausible_model_or_class_lead        102  (68.00%)
  obvious_out_of_scope                  19  (12.67%)
  ambiguous                             29  (19.33%)
recommendation  FOLLOWUP_VERIFICATION_CANDIDATE
```

Immutable accepted boundaries remain:

```text
direct-discovery candidate QIDs      1,829
canonical BoatModels                 1,770
historical QID -> HullQ-ID mappings  1,772
SLICE-0021 alternative-route union      57
```

The accepted recommendation is research-only. SLICE-0023 does **not** authorize production Wikipedia/Wikimedia discovery, canonical admission of the 409 leads, Stage-3.3 enrichment, query-engine/API/frontend work or any later slice except where separately readied.

Acceptance evidence:

- implementation PR #61;
- final reviewed head `92dc0320e995542226199509fc7236f29a75a254`;
- exact-head CI run `32867281346`: SUCCESS;
- manufacturer reproducibility run `32867282317`: SUCCESS;
- implementation merge `ac2868d978f33f42ccc7e9cc2b1885bfa86b23bb`;
- independent-review verdict: **ACCEPT**;
- project-owner acceptance: **2026-08-25**;
- closure: `docs/slices/SLICE-0023-acceptance-closure.md`.

## Earlier accepted Stage-3 identity milestones

- **SLICE-0017:** first controlled Wikidata Tier-0 identity bootstrap.
- **SLICE-0018:** direct discovery reached **1,829 QIDs**, yielding **1,770** accepted canonical BoatModels and **1,772** historical crosswalk mappings.
- **SLICE-0019:** manufacturer/yard universe + source-yield research.
- **SLICE-0020:** fixed archive sample produced **0 ADAPTER_READY / 9 review-required / 1 blocked** sources.
- **SLICE-0021:** alternative Wikidata routes yielded **57** additional discovery signals (R1 +53 / R2 +0 / R3 +4).
- **SLICE-0022:** those 57 candidates produced **0 AUTO_ADMIT / 31 REVIEW_REQUIRED / 26 NOT_ADMITTED**; canonical BoatModels remained 1,770.
- **SLICE-0023:** bounded Wikimedia categories yielded **409** incremental QID research leads and passed the precommitted follow-up-candidate threshold.
- **SLICE-0024:** deterministic 30-candidate independent verification pilot over the 409 leads found only **11/24** threshold candidates independently supported (below the required 12); accepted corrected recommendation `LOW_INDEPENDENT_VERIFICATION_YIELD`.

Detailed reasoning, amendments, CI IDs and retained evidence stay in each slice's closure and research package rather than being duplicated here.

## Operational references

- Current project state: `docs/PROJECT_STATE.md`
- Execution plan: `docs/EXECUTION_PLAN.md`
- AI slice workflow: `docs/engineering/AI_SLICE_WORKFLOW.md`
- AI token-efficiency standard: `docs/engineering/AI_TOKEN_EFFICIENCY.md`
- Slice template: `docs/slices/SLICE_TEMPLATE.md`

No later slice starts automatically.
