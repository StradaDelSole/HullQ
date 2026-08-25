# HullQ Slice Index

**Status:** ACTIVE execution board  
**Updated:** 2026-08-25 — SLICE-0023 accepted / `DONE`; SLICE-0024 `READY`

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
| SLICE-0024 | DESIGN_RESEARCH | READY | Deterministic 30-QID independent identity-verification/source-cost pilot over accepted SLICE-0023 leads | SLICE-0023 accepted / DONE |

## Current execution rule

**SLICE-0001 through SLICE-0023 are accepted / `DONE`. SLICE-0024 is the only `READY` slice. No later slice is authorized.**

SLICE-0024 starts only through the normal `START_SLICE.bat` workflow from current `origin/main`, in a fresh isolated worktree and fresh Claude conversation. Nothing in SLICE-0024 readiness authorizes SLICE-0025.

For an already completed slice, its `*-acceptance-closure.md` is the final acceptance-state record. A primary slice contract may still show its historical implementation handoff state (`REVIEW`); the acceptance closure plus this operational queue control the final operational `DONE` state.

## Current READY boundary — SLICE-0024

SLICE-0024 is a bounded `DESIGN_RESEARCH` verification-source pilot. It does **not** research all 409 Wikimedia leads.

It selects exactly 30 candidates from the final accepted SLICE-0023 150-QID quality sample using deterministic SHA256 ordering within the prior review strata:

```text
prior plausible_model_or_class_lead   18
prior ambiguous                         6
prior obvious_out_of_scope              6
total                                  30
```

For each candidate it measures whether independent non-Wikipedia evidence can support an in-scope identity, which source class is required, and how many bounded research actions are needed. Search results, Wikipedia/Wikidata context and SailboatData are discovery/context only and cannot qualify as verification evidence.

The precommitted result can recommend a later full-409 verification campaign only if independent verification yield, strong-source coverage and research-action economics meet the fixed thresholds. SLICE-0024 itself performs **zero canonical admission** and no Stage-3.3 work.

Primary contract: `docs/slices/SLICE-0024-wikimedia-lead-independent-identity-verification-pilot.md`.

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

Detailed reasoning, amendments, CI IDs and retained evidence stay in each slice's closure and research package rather than being duplicated here.

## Operational references

- Current project state: `docs/PROJECT_STATE.md`
- Execution plan: `docs/EXECUTION_PLAN.md`
- AI slice workflow: `docs/engineering/AI_SLICE_WORKFLOW.md`
- AI token-efficiency standard: `docs/engineering/AI_TOKEN_EFFICIENCY.md`
- Slice template: `docs/slices/SLICE_TEMPLATE.md`

No later slice starts automatically.
