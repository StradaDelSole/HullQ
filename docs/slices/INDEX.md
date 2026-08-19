# HullQ Slice Index

**Status:** ACTIVE execution board

The slice index is the canonical operational queue for bounded AI-assisted work. It does not replace `docs/EXECUTION_PLAN.md`, requirements, specs, or ADRs.

| Slice | Type | Status | Objective | Depends on |
|---|---|---|---|---|
| SLICE-0001 | BOOTSTRAP | DONE | Close repository bootstrap: real `uv.lock`, full local gates, first green Linux/Windows CI | OQ-010 / ADR-0009 |
| SLICE-0002 | DESIGN_RESEARCH | DONE | Research independent sailboat-design data sources and a 20–30-design seed evidence sample before domain pipeline code | SLICE-0001 |
| SLICE-0003 | IMPLEMENTATION | DONE | Canonical JSON-Schema contract runtime and local `$id`/reference registry | SLICE-0002 |
| SLICE-0004 | IMPLEMENTATION | DONE | Measurement observation + deterministic unit/basis normalization while preserving raw source semantics | SLICE-0003 |
| SLICE-0005 | IMPLEMENTATION | DONE | First-class Brand/Organization identity contracts, BoatModel/BoatDesign identity migration, entity-scoped aliases and deterministic search-label keys | SLICE-0004 / ADR-0011 |
| SLICE-0006 | IMPLEMENTATION | DONE | Provenance/raw-observation runtime: successor FieldEvidence/FieldResolution contracts, stable provenance subjects, conflict/supersession/current-resolution validation and source-impact lookup | SLICE-0005 / ADR-0006 |
| SLICE-0007 | IMPLEMENTATION | DONE | ResearchJob runtime + deterministic source-rights/use gate + cumulative extraction telemetry so automated acquisition fails closed | SLICE-0006 / ADR-0005 |
| SLICE-0008 | IMPLEMENTATION | DONE | First rights-gated real external acquisition adapter against Wikidata CC0 with bounded discovery/entity acquisition and provenance-aware extraction | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | REVIEW | Deterministic appendage/configuration normalization for explicit keel, rudder, skeg, hull and board observations using the existing BoatDesign vocabulary | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | BACKLOG | Derived-metrics engine under `hullq-derived-1.0.0` after canonical/configuration inputs are hardened | SLICE-0009 |

## Current execution rule

`SLICE-0008` is `DONE`. It was implemented on `slice/0008-wikidata-rights-gated-adapter`, independently reviewed through four precision amendment rounds and merged through PR #19 on 2026-08-19.

Acceptance evidence:

- accepted final implementation/PR head: `491a2db310c75dd6768b15cc1e0dcba57f1a8fc9`;
- GitHub Actions run #108: CI PASS;
- final offline suite reported by the implementation agent: 606 tests PASS, 90.42% branch coverage, Ruff/format clean, strict mypy clean on SLICE-0008 files, pip-audit clean;
- final independent review: no remaining blocking findings;
- implementation merge commit: `e7129cd61145a5a33613a08df5c008555ff569c4`.

The accepted SLICE-0008 boundary provides the first rights-gated real source adapter against Wikidata CC0: bounded direct sailboat-class discovery, official entity acquisition, descriptive contact-bearing User-Agent enforcement, qualifier-aware FieldEvidence, strict physical-dimension normalization guards, deterministic source-quality counts, preferred-language/English fallback, and exact dimensionless handling for P1092 counts. It does not create canonical FieldResolution, mutate BoatDesign/BoatModel records, perform broad ingestion, or solve appendage/configuration taxonomy.

`SLICE-0009` is the **only `READY` implementation slice**. It must implement a conservative, source-agnostic appendage/configuration normalization boundary over the existing `BOAT_DESIGN_SCHEMA.v0.5` vocabulary. It must preserve raw source observations, fail closed on unknown/proprietary/ambiguous semantics, keep option/variant/state applicability separate from baseline, and must not introduce new source acquisition, canonical conflict resolution, persistence, or derived metrics.

No implementation agent may begin SLICE-0010 automatically.

## Evidence-first sequence

```text
reproducible toolchain
        ↓
real design-data source research
        ↓
canonical contract runtime            DONE
        ↓
measurement normalization             DONE
        ↓
Brand / Organization identity         DONE
        ↓
provenance/raw observation boundary   DONE
        ↓
ResearchJob + source-rights gate      DONE
        ↓
FIRST RIGHTS-GATED REAL DATA — Wikidata CC0   DONE
        ↓
appendage/configuration hardening     READY
        ↓
derived metrics                      BACKLOG
        ↓
controlled benchmark → broad ingestion
```

## Why appendage/configuration hardening is next

SLICE-0002 showed that no single broad source provides SailboatData-like breadth plus HullQ-critical keel/rudder/skeg/configuration depth under clearly reusable terms. Manufacturer evidence also showed that configuration frequently lives in options, brochures, manuals, proprietary wording and state-specific measurements rather than one flat model field.

SLICE-0008 proved that HullQ can acquire and preserve rights-cleared structured evidence safely, but Wikidata's strongest common-field model still does not solve generation/variant/configuration identity or rudder/skeg depth. The next safe boundary is therefore not another crawler: it is a deterministic semantic normalizer for explicit configuration observations so later source adapters can emit auditable candidates without guessing.

## Workflow note

The current `START_SLICE` workflow prepares/synchronizes Git state, creates or reuses the isolated slice worktree, and copies the Claude prompt. It deliberately does **not** open, close, reload or switch any VS Code window. The project owner explicitly opens the prepared worktree in the desired VS Code window.

## Rolling-wave note

Exactly one implementation slice is `READY`: SLICE-0009. SLICE-0010 remains directional backlog and may be refined by implementation evidence from SLICE-0009.
