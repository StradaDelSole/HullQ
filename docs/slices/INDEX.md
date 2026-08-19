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
| SLICE-0006 | IMPLEMENTATION | DONE | Provenance/raw-observation runtime: FieldEvidence/FieldResolution contracts, stable provenance subjects, conflict/supersession/current-resolution validation and source-impact lookup | SLICE-0005 / ADR-0006 |
| SLICE-0007 | IMPLEMENTATION | DONE | ResearchJob runtime + deterministic source-rights/use gate + cumulative extraction telemetry so automated acquisition fails closed | SLICE-0006 / ADR-0005 |
| SLICE-0008 | IMPLEMENTATION | DONE | First rights-gated real external acquisition adapter against Wikidata CC0 with bounded discovery/entity acquisition and provenance-aware extraction | SLICE-0007 |
| SLICE-0009 | IMPLEMENTATION | DONE | Deterministic appendage/configuration normalization for explicit keel, rudder, skeg, hull and board observations using the existing BoatDesign vocabulary | SLICE-0008 |
| SLICE-0010 | IMPLEMENTATION | DONE | Deterministic `hullq-derived-1.0.0` derived-metrics engine with accepted formulas, status precedence, six-decimal canonical precision and DerivationRecord lineage | SLICE-0009 / ADR-0008 |
| SLICE-0011 | DESIGN_RESEARCH | IN_PROGRESS | Controlled 50–100-design real-web benchmark: broad independent source research, provenance/conflict capture, post-hoc reference crosscheck and measured research quality | SLICE-0010 |

## Current execution rule

`SLICE-0010` is `DONE` and accepted.

Acceptance evidence:

- accepted final implementation/PR head: `601af0e859a8c771640f473394b78efa32bf918c`;
- GitHub Actions run #120: PASS on the accepted head;
- final local implementation report: 915 tests PASS, 92.62% branch coverage, `derived_metrics.py` 99.50% branch coverage, repository validator PASS, Ruff/format clean, strict mypy clean, pip-audit clean;
- independent review found four blocking precision issues; all four were amended and independently rechecked with no remaining blockers;
- PR #21 merged on 2026-08-19;
- implementation merge commit: `8f9a5ab07f454d6dfbfcb2f133c80c48b14dcc4a`.

`SLICE-0011` is now the active controlled benchmark research wave. It is **research-led, not an autonomous Claude/network-crawling slice**. ChatGPT/master research performs the real-web source discovery and evidence assessment. Claude Code remains the implementation agent for later deterministic import/persistence/processing work.

No implementation agent may automatically begin persistence, broad ingestion, query-engine, API or frontend work from this research status.

## Evidence-first sequence

```text
reproducible toolchain                         DONE
        ↓
seed design-data source research               DONE
        ↓
canonical contract runtime                     DONE
        ↓
measurement normalization                      DONE
        ↓
Brand / Organization identity                  DONE
        ↓
provenance/raw observation boundary            DONE
        ↓
ResearchJob + source-rights gate               DONE
        ↓
first rights-gated real adapter — Wikidata     DONE
        ↓
appendage/configuration hardening              DONE
        ↓
derived metrics                               DONE
        ↓
controlled real-web benchmark                  IN PROGRESS — SLICE-0011
        ↓
persistence/import boundary                    LATER — refine from benchmark evidence
        ↓
broad design-universe ingestion                NOT AUTHORIZED YET
```

## SLICE-0011 research rules

1. Research independently across the broad useful web: manufacturer/shipyard, original brochures/manuals, designer/class/owners associations, archives, specialist publications/databases, brokers where appropriate, forums/owner communities and other discoverable evidence.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, retrieval date, source identity and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData is **reference crosscheck only after independent research**. No SailboatData value becomes HullQ FieldEvidence, no missing field is filled from it, and no reference value is copied into canonical candidates. Crosscheck output is limited to outcomes such as match/partial/conflict/not-found and follow-up research triggers.
6. Benchmark outputs are research evidence, not production canonical data.
7. Benchmark target remains 50–100 deliberately difficult designs; work proceeds in auditable waves.

## Workflow note

The `START_SLICE` / `FINISH_SLICE` worktree workflow continues to govern Claude implementation slices. SLICE-0011 is intentionally different: it is a master-led DESIGN_RESEARCH slice and does not require Claude to perform web research.

GitHub `origin/main` remains canonical truth. Research changes are prepared on `research/0011-controlled-benchmark` and go through a PR before becoming canonical.

## Rolling-wave note

The current research wave may continue without waiting for an implementation agent. Findings from SLICE-0011 will determine the smallest safe persistence/import implementation slice that follows; that downstream implementation slice must be specified and readied separately before Claude starts it.
