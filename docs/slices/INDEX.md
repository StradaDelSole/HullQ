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
| SLICE-0011 | DESIGN_RESEARCH | REVIEW | Controlled 50-design real-web stress benchmark, measured ambiguity/conflict classes, post-hoc reference QA and benchmark-derived persistence requirements | SLICE-0010 |
| SLICE-0012 | IMPLEMENTATION | BLOCKED | Add pre-canonical ResearchObservation, claim/applicability semantics, explicit promotion to FieldEvidence and machine-ingestible ResearchEvidenceBundle before physical persistence | SLICE-0011 accepted / DONE |

## Current execution rule

`SLICE-0010` is `DONE` and accepted.

Acceptance evidence:

- accepted final implementation/PR head: `601af0e859a8c771640f473394b78efa32bf918c`;
- GitHub Actions run #120: PASS on the accepted head;
- final local implementation report: 915 tests PASS, 92.62% branch coverage, `derived_metrics.py` 99.50% branch coverage, repository validator PASS, Ruff/format clean, strict mypy clean, pip-audit clean;
- independent review found four blocking precision issues; all four were amended and independently rechecked with no remaining blockers;
- PR #21 merged on 2026-08-19;
- implementation merge commit: `8f9a5ab07f454d6dfbfcb2f133c80c48b14dcc4a`.

`SLICE-0011` is in `REVIEW`. The master-led research pass reached the minimum 50-design difficult corpus, coded the retained cases, measured recurring stress classes and derived the next bounded pre-persistence requirements. It remains research-led: ChatGPT/master performed real-web source discovery and evidence assessment; Claude Code was not used as an autonomous network-research agent.

Benchmark closure artifacts include:

- Waves 01–06 under `research/benchmark/waves/`;
- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`;
- `research/benchmark/BENCHMARK-50-classification.csv`;
- `research/benchmark/BENCHMARK-50-analysis.md`;
- retained pre-contract structured exports for Waves 01/02 under `research/benchmark/legacy-observations/`.

The 50-design stress corpus is deliberately difficult; its measured incidences are not sailboat-population prevalence estimates. Runtime automation/review/idempotency/cost metrics remain deferred until an executable importer/persistence path exists.

The closure review found and corrected two important governance/architecture issues before acceptance:

1. post-hoc SailboatData comparison is outcome-only in retained summaries/exports; no SailboatData field value is HullQ evidence or retained as fallback data;
2. ResearchJob targets are intentionally pre-canonical, while FieldEvidence requires a stable provenance subject. SLICE-0012 therefore introduces pre-canonical `ResearchObservation` and explicit caller-supplied promotion to FieldEvidence rather than forcing identity during research.

`SLICE-0012` is drafted but `BLOCKED`. It MUST NOT start until SLICE-0011 has passed current-head CI, independent closure review and explicit owner acceptance/DONE. No implementation agent may automatically begin it.

## Evidence-first sequence

```text
reproducible toolchain                            DONE
        ↓
seed design-data source research                  DONE
        ↓
canonical contract runtime                        DONE
        ↓
measurement normalization                         DONE
        ↓
Brand / Organization identity                     DONE
        ↓
provenance/raw observation boundary               DONE
        ↓
ResearchJob + source-rights gate                  DONE
        ↓
first rights-gated real adapter — Wikidata        DONE
        ↓
appendage/configuration hardening                 DONE
        ↓
derived metrics                                  DONE
        ↓
controlled 50-design real-web benchmark           REVIEW — SLICE-0011
        ↓
pre-canonical observation + evidence applicability
+ ResearchEvidenceBundle                          BLOCKED — SLICE-0012
        ↓
PostgreSQL persistence + deterministic importer   LATER
        ↓
execute same benchmark through importer/DB        LATER
        ↓
broad design-universe ingestion                   NOT AUTHORIZED YET
```

## SLICE-0011 retained research rules

1. Research independently across the broad useful web: manufacturer/shipyard, original brochures/manuals, designer/class/owners associations, archives, specialist publications/databases, brokers where appropriate, forums/owner communities and other discoverable evidence.
2. Source breadth is intentionally broad; canonical confidence is intentionally strict.
3. Preserve raw wording/value, unit, measurement basis, configuration/variant/state, retrieval date, source identity and confidence.
4. Never invent missing values or silently resolve conflicts.
5. SailboatData is **reference crosscheck only after independent research**. No SailboatData value becomes HullQ FieldEvidence, no missing field is filled from it, and no reference value is retained as canonical/research evidence. Crosscheck output is limited to comparison outcomes/anomaly triggers.
6. Benchmark outputs are research evidence, not production canonical data.

## Benchmark-derived next boundary

The 50-design analysis found that existing identity/configuration/provenance foundations are directionally sound, but four lossless handoff semantics must be explicit before a physical database schema is frozen:

1. pre-canonical web research needs `ResearchObservation` because accepted `ResearchTarget` deliberately does not assert a canonical HullQ subject;
2. source/document `EvidenceType` must remain separate from the semantic claim role of an observation;
3. observation/evidence applicability must preserve year/hull/variant/option/state/individual-hull restrictions where known;
4. master research needs a versioned machine-ingestible `ResearchEvidenceBundle`, with explicit promotion to successor FieldEvidence only after a stable canonical `ProvenanceSubject` is supplied; optional reference crosschecks remain outside both ResearchObservation and FieldEvidence provenance.

`docs/slices/SLICE-0012-evidence-applicability-research-bundle.md` defines that small boundary. It does not authorize PostgreSQL, broad ingestion, network acquisition, identity resolution, automatic conflict resolution or a general ontology/graph redesign.

## Workflow note

The `START_SLICE` / `FINISH_SLICE` worktree workflow continues to govern Claude implementation slices. SLICE-0011 is a master-led DESIGN_RESEARCH slice and does not require Claude to perform web research.

GitHub `origin/main` remains canonical truth. Research changes are prepared on `research/0011-controlled-benchmark` and go through PR #22 before becoming canonical.

## Rolling-wave note

No implementation slice is currently `READY`. SLICE-0012 remains `BLOCKED` until SLICE-0011 is explicitly accepted/DONE. After 0012 acceptance, the intended next bounded implementation is PostgreSQL persistence plus deterministic ResearchEvidenceBundle import/promotion handling, followed by execution of the same benchmark corpus before broad ingestion is considered.
