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
| SLICE-0009 | IMPLEMENTATION | DONE | Deterministic appendage/configuration normalization for explicit keel, rudder, skeg, hull and board observations using the existing BoatDesign vocabulary | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | READY | Deterministic `hullq-derived-1.0.0` derived-metrics engine with accepted formulas, status precedence, six-decimal canonical precision and DerivationRecord lineage | SLICE-0009 / ADR-0008 |

## Current execution rule

`SLICE-0009` is `DONE`. It was implemented on `slice/0009-appendage-configuration-normalization`, independently reviewed, amended for scope-safe projection and snapshot-safe raw observations, and merged through PR #20 on 2026-08-19.

Acceptance evidence:

- accepted final implementation/PR head: `9da6a579881b0451a028426b80a8a7281e6f6a0b`;
- GitHub Actions run #114: CI PASS;
- final implementation report: 792 tests PASS, 91.20% branch coverage, `configuration.py` 98.88% branch coverage, repository validator PASS, Ruff/format clean, strict mypy clean, pip-audit clean;
- final independent review: no remaining blocking findings;
- implementation merge commit: `001ca87817f37553b463ca01270c64a26b7716b6`.

The accepted SLICE-0009 boundary provides a versioned source-agnostic configuration normalizer over the existing BoatDesign vocabulary; conservative exact/alias rules; explicit unsupported/ambiguous/malformed outcomes; independent keel/rudder/skeg/hull/board axes; strict count handling; snapshot-safe raw observations; and fail-closed baseline projection so option/variant/state observations cannot silently become baseline facts. It does not create FieldResolution, mutate BoatDesign, perform source acquisition, persist data or calculate derived metrics.

`SLICE-0010` is the **only `READY` implementation slice**. It must implement the already accepted OQ-001 / ADR-0008 methodology `hullq-derived-1.0.0` mechanically from explicit effective input snapshots. It must reproduce the checked-in golden/status fixtures, enforce exact applicability/basis/status-precedence rules, quantize populated outputs to six decimals using round-half-even, and create DerivationRecord lineage for every populated metric.

No implementation agent may begin later benchmark/broad-ingestion work automatically.

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
appendage/configuration hardening     DONE
        ↓
derived metrics                      READY
        ↓
controlled benchmark                 LATER / NOT AUTHORIZED YET
```

## Why derived metrics are next

OQ-001 / ADR-0008 already accepted all normative calculation semantics: six formulas, exact conversion constants, displacement/sail-area basis handling, per-hull applicability, deterministic status precedence, six-decimal round-half-even storage and DerivationRecord lineage. Golden and negative/status fixtures are already checked in.

The prior implementation slices now provide the prerequisites needed to execute that methodology without inventing upstream semantics: physical normalization (SLICE-0004), provenance/DerivationRecord contracts (SLICE-0006), and safe explicit hull/configuration normalization (SLICE-0009). SLICE-0010 therefore implements the accepted calculation boundary only; it does not build a configuration resolver, query engine, persistence layer or safety score.

## Workflow note

The current `START_SLICE` workflow prepares/synchronizes Git state, creates or reuses the isolated slice worktree, and copies the Claude prompt. It deliberately does **not** open, close, reload or switch any VS Code window. The project owner explicitly opens the prepared worktree in the desired VS Code window.

## Rolling-wave note

Exactly one implementation slice is `READY`: SLICE-0010. The next controlled benchmark slice is intentionally not readied yet and may be refined by implementation evidence from SLICE-0010.
