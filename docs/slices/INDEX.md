# HullQ Slice Index

**Status:** ACTIVE execution board  
**Updated:** 2026-08-21

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, ADRs or accepted slice contracts.

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
| SLICE-0012 | IMPLEMENTATION | DONE | Pre-canonical ResearchObservation, claim/applicability semantics, explicit promotion and ResearchEvidenceBundle | SLICE-0011 |
| SLICE-0013 | IMPLEMENTATION | DONE | PostgreSQL 18 migrations + lossless deterministic ResearchEvidenceBundle importer | SLICE-0012 accepted / DONE |
| SLICE-0014 | DESIGN_RESEARCH | DONE | Run the accepted 50-design benchmark through the real PostgreSQL persistence path and measure determinism/review/throughput | SLICE-0013 accepted / DONE |
| SLICE-0015 | IMPLEMENTATION | DONE | Harden benchmark failure paths and make the Stage-2 Gate G3 decision using the fixed pre-committed scorecard | SLICE-0014 accepted / DONE |
| SLICE-0016 | IMPLEMENTATION | DONE | Canonical Brand/Organization/BoatModel/BoatDesign PostgreSQL persistence + explicit bootstrap-admission boundary | SLICE-0015 accepted / DONE / G3 PASS |
| SLICE-0017 | IMPLEMENTATION | DONE | Controlled Wikidata Tier-0 identity bootstrap across the first 1,000 direct sailboat-class candidates | SLICE-0016 accepted / DONE |
| SLICE-0018 | IMPLEMENTATION | READY | Controlled Wikidata Tier-0 expansion to the first <=2,500 direct sailboat-class discovery window using a baseline-preserving delta | SLICE-0017 accepted / DONE |

## Current execution rule

`SLICE-0018` is the **only READY slice**.

It may start only through the normal isolated `START_SLICE.bat` workflow after this closure/readiness PR is merged to `main`.

SLICE-0018 is a measured Stage-3.2 expansion. It extends the rights-cleared deterministic Wikidata discovery window toward 2,500 while preserving the accepted SLICE-0017 baseline as immutable input.

The key operational rule is:

```text
accepted SLICE-0017 baseline
        !=
current SLICE-0018 discovery window
        !=
SLICE-0018 expansion delta
        !=
historical retained crosswalk
```

Only QIDs in the current first-<=2,500 discovery window that were **not** among the accepted 1,000 SLICE-0017 baseline candidate QIDs receive new SLICE-0018 admission/review/non-admission decisions.

No 5,000 expansion, prior-review resolution campaign, broad technical enrichment, query engine, API, frontend, marketplace or monitoring work is authorized by this readiness transition.

## SLICE-0017 acceptance closure

SLICE-0017 is explicitly accepted and `DONE`.

Acceptance evidence:

- final accepted implementation head: `34c2de8fc99ab6babad054a4186cee168cc3a2da`;
- implementation PR: #35;
- implementation merge commit: `e2001d3a926c08706558b6cb97962f235c843379`;
- GitHub Actions CI run #200 (`32499124689`): PASS on the exact accepted head;
- PostgreSQL **18.6** integration: PASS;
- quality / Ubuntu: PASS;
- quality / Windows: PASS;
- dependency audit: PASS;
- retained Stage-2 benchmark: exact `G3_PASS`;
- controlled manifest: **1,000** candidates;
- final decisions: **965 AUTO_ADMIT / 20 REVIEW_REQUIRED / 15 NOT_ADMITTED**;
- deterministic collision clusters: **10**;
- retained historical QID→HullQ-ID mappings: **967**;
- production replay first pass: **985/985** ResearchEvidenceBundles and **965/965** canonical admissions imported;
- first-pass conflicts/errors/unexpected statuses: **0**;
- deep semantic readback mismatches: **0**;
- unexpected canonical rows for non-admitted candidates: **0**;
- stray Brand/Organization/BoatDesign rows: **0 / 0 / 0**;
- exact re-import: **1,950 ALREADY_IMPORTED**, 0 conflicts/errors;
- independent fresh-schema replay: **985** bundles + **965** admissions, 0 semantic mismatches, exact ID set, 0 stray Brand/Organization/BoatDesign rows;
- `all_zero_tolerance_conditions_clear = true`;
- bootstrap CI artifact ID: `9452810477`;
- bootstrap artifact digest: `sha256:3161e6f43572dcbcafbd6512becc2aea7be44b2f8d1ae56234e49ef37a5eb034`;
- benchmark artifact ID: `9452803532`;
- benchmark artifact digest: `sha256:6cb1414ac7b9c90393ba1545c4fd89adb67fbe298d367d42a29c51775c09684c`;
- implementation-agent final local report: **1,407 passed, 205 skipped**;
- reported coverage: **94.29%**;
- repository validator / Ruff / strict mypy / pip-audit: PASS/CLEAN;
- independent review: all identified blockers corrected;
- explicit project-owner acceptance on 2026-08-21.

Final closure record: `docs/slices/SLICE-0017-acceptance-closure.md`.

Accepted Stage-3 bootstrap semantics now include:

- controlled rights-gated deterministic direct-instance discovery;
- sparse source-backed Tier-0 BoatModel admission only;
- accepted HullQ search-key semantics for collision detection;
- stable content-derived alias IDs;
- stable opaque HullQ IDs that do not encode QID/name;
- historical retained QID→HullQ-ID mapping independent of current candidate rows;
- fail-closed crosswalk conflict detection in both directions before live network use;
- preserved acquisition timestamp distinct from later recompute time;
- isolated PostgreSQL replay from migrations zero;
- exact first-pass, re-import and independent fresh-schema proof;
- deep alias/provenance semantic readback;
- zero automatic Brand/Organization/BoatDesign invention;
- no SailboatData value contamination;
- retained Stage-2 `G3_PASS` regression gate.

## Historical acceptance closures

The detailed accepted evidence for completed prior slices remains in the dedicated closure records:

- `docs/slices/SLICE-0012-acceptance-closure.md`;
- `docs/slices/SLICE-0013-acceptance-closure.md`;
- `docs/slices/SLICE-0014-acceptance-closure.md`;
- `docs/slices/SLICE-0015-acceptance-closure.md`;
- `docs/slices/SLICE-0016-acceptance-closure.md`;
- `docs/slices/SLICE-0017-acceptance-closure.md`.

## Evidence-first sequence

```text
reproducible toolchain                            DONE
        ↓
seed design-data source research                  DONE
        ↓
canonical contracts / measurements / identity     DONE
        ↓
provenance + source-rights + first adapter         DONE
        ↓
appendage/configuration + derived metrics          DONE
        ↓
controlled 50-design real-web benchmark           DONE — SLICE-0011
        ↓
pre-canonical observation + applicability/bundle  DONE — SLICE-0012
        ↓
research PostgreSQL persistence                   DONE — SLICE-0013
        ↓
run same benchmark through importer/DB            DONE — SLICE-0014 / G3_CANDIDATE
        ↓
harden negative paths + Stage-2 Gate G3           DONE — SLICE-0015 / G3 PASS
        ↓
canonical identity persistence/admission boundary DONE — SLICE-0016
        ↓
controlled Wikidata Tier-0 1,000 bootstrap        DONE — SLICE-0017
        ↓
baseline-preserving Wikidata <=2,500 expansion    READY — SLICE-0018
        ↓
measured next Stage-3 decision                     LATER / NOT AUTHORIZED
```

## SLICE-0018 boundary

`docs/slices/SLICE-0018-controlled-wikidata-tier0-2500-window-expansion.md` is the controlling READY contract.

The slice is deliberately restricted to the next measured identity-universe milestone:

- retain the accepted SLICE-0017 manifest as immutable baseline input;
- discover the current first <=2,500 direct Wikidata sailboat-class QIDs under the accepted rights gate and deterministic ordering;
- compute the expansion delta as current discovery QIDs minus all 1,000 accepted SLICE-0017 candidate QIDs;
- classify/admit only the delta;
- compare new delta search projections against retained baseline projections and other delta candidates;
- preserve accepted baseline BoatModels even when a new candidate collides with them;
- retain/reuse the historical crosswalk without reminting;
- keep SLICE-0018 retained artifacts separate from the accepted SLICE-0017 artifact;
- replay baseline first and delta second against isolated PostgreSQL 18 schemas;
- prove zero accepted-baseline drift/deletion/demotion and zero Brand/Organization/BoatDesign invention;
- measure whether Wikidata reaches the 2,500 target; if it returns fewer, report the observed ceiling and do not pad from another source.

It explicitly does **not** authorize reclassification/destructive correction of the accepted 0017 baseline or resolution of the 0017 review queue.

## Retained research rules

1. Research independently across the broad useful web only when an assigned research/acquisition slice explicitly authorizes it.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, source identity, retrieval context and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData remains post-hoc reference crosscheck only; no SailboatData field value becomes HullQ evidence, fallback data or canonical input.
6. Benchmark outputs are research evidence/stress fixtures, not automatically production canonical data.
7. Stage-2 G3 passage authorizes controlled Stage-3 work only through explicit bounded slice contracts; it is not a blanket ingestion authorization.
8. Accepted bootstrap artifacts are immutable baselines for later expansion unless a separate owner-accepted correction/migration slice explicitly changes that policy.

## Workflow note

`START_SLICE.bat` / `FINISH_SLICE.bat` govern Claude implementation/research worktrees.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned slice branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

After this closure/readiness PR is merged, the project owner may first run `FINISH_SLICE.bat` for SLICE-0017 to remove the merged local worktree/branch, then may run `START_SLICE.bat` for SLICE-0018 when ready.

`START_SLICE.bat` must find exactly one primary SLICE-0018 document with `**Status:** READY`; the implementation agent must return SLICE-0018 in `REVIEW`, `BLOCKED` or `IN_PROGRESS` and must not mark it `DONE` or start the 5,000/enrichment step automatically.
