# HullQ — Current Project State

**Updated:** 2026-08-20  
**Current stage:** Stage 2.10–2.11 — SLICE-0011 controlled real-web benchmark `REVIEW`  
**Execution plan:** `docs/EXECUTION_PLAN.md`  
**Operational work queue:** `docs/slices/INDEX.md`

## Canonical project direction

HullQ is building an independent, provenance-aware sailboat design universe suitable for search/discovery, later market integration and reproducible derived metrics.

Accepted strategic principles remain:

- broad coverage with progressive verification depth;
- search architecture and SEO are product architecture, not later marketing;
- Search stays broadly available while persistence/monitoring are monetization candidates;
- source data, normalized candidates, canonical resolutions and HullQ-derived values remain distinct;
- unknown/conflict is preferable to fabricated completeness;
- one model string is not a reliable technical identity boundary;
- option/variant/state-sensitive values must not be flattened into one scalar baseline;
- GitHub `main` is canonical truth; bounded slice/PR review remains mandatory.

## Accepted application/deployment architecture

Target baseline remains:

```text
Cloudflare edge
      |
      v
Contabo Linux VPS
      |
      +-- Astro + TypeScript web
      |     \-- React islands only where state complexity justifies them
      +-- FastAPI / CPython 3.14
      +-- PostgreSQL
      +-- background/scheduled Python worker when needed
      \-- simple VPS deployment / Caddy baseline

Off-VPS backup/artifact direction: Cloudflare R2 when introduced
Later native mobile: Flutter Android/iOS via the same accepted API boundary
```

Auth remains deferred under OQ-014. OQ-006 controls alert cadence/freshness; OQ-015 controls the stable HTTP API/versioning boundary; OQ-018 controls the public SEO/search surface; OQ-009 is required before technical query-engine semantics are frozen.

## Completed foundation and implementation

### SLICE-0001 — repository bootstrap — DONE

Repository governance, docs-to-code workflow, locked toolchain and cross-platform quality gates established.

### SLICE-0002 — real design-data source research — DONE

Retained findings include:

1. Wikidata CC0 is the strongest current broad bootstrap candidate.
2. No single SailboatData replacement exists; HullQ needs broad open bootstrap plus progressive independent enrichment.
3. Appendage/configuration depth is materially harder than ordinary scalar dimensions.
4. Measurement basis, option-sensitive values and source conflicts must remain explicit.
5. Primary sources can conflict or be internally malformed.
6. Rudder/skeg classification creates disproportionate research/review complexity.

The imported/reference SailboatData material remains research/reference only and MUST NOT become an invisible production-value source.

### SLICE-0003 — canonical contract runtime — DONE

Draft-2020-12 schema registry/validation boundary accepted and merged.

### SLICE-0004 — measurement normalization — DONE

Deterministic exact unit normalization accepted with raw text/semantic-label preservation and no arbitrary-string inference.

### SLICE-0005 — identity contracts/search labels — DONE

Accepted first-class Brand/Organization identities, BoatModel/BoatDesign identity separation, entity-scoped aliases and deterministic search-label projections.

### SLICE-0006 — provenance/raw observation runtime — DONE

Accepted FieldEvidence/FieldResolution boundary, immutable raw observations, normalized candidates, conflict/supersession/current-resolution validation and source-impact lookup.

### SLICE-0007 — ResearchJob/source-rights gate — DONE

Accepted deterministic use-specific rights decisions, fail-closed automated-access gating, extraction telemetry and ResearchJob integration.

### SLICE-0008 — first rights-gated real adapter: Wikidata CC0 — DONE

Accepted bounded Wikidata discovery/entity acquisition with rights gate before network access, qualifier-aware FieldEvidence and deterministic extraction behavior.

### SLICE-0009 — appendage/configuration normalization — DONE

Accepted independent keel/rudder/skeg/hull/board axes, exact/explicit-alias normalization, count handling, option/variant/state scope preservation and fail-closed baseline projection.

### SLICE-0010 — derived metrics engine — DONE

Accepted methodology `hullq-derived-1.0.0` after independent review/amendment.

Acceptance evidence:

- final implementation/PR head: `601af0e859a8c771640f473394b78efa32bf918c`;
- GitHub Actions run #120: PASS;
- 915 local tests PASS;
- 92.62% branch coverage; `derived_metrics.py` 99.50%;
- repository validator, Ruff/format, strict mypy and pip-audit clean;
- PR #21 merge commit: `8f9a5ab07f454d6dfbfcb2f133c80c48b14dcc4a`.

The runtime computes the six approved metrics from explicit effective inputs, preserves basis/status/applicability semantics and produces DerivationRecord lineage. It does not resolve source conflicts, build full configurations or persist data.

## Current operational position — SLICE-0011 REVIEW

SLICE-0011 is the master/ChatGPT-led controlled real-web benchmark. Claude Code was deliberately **not** used as the autonomous web-research agent.

Research policy:

```text
broad independent web research
→ source-linked raw observation/context
→ corroboration/conflict detection
→ post-hoc reference comparison
→ benchmark classification/measurement
→ persistence requirements derived from evidence
```

Source discovery intentionally spans manufacturer/shipyard material, original brochures/manuals, designers, class/owners associations, archives, specialist publications/databases, broker technical records, forums/owner communities, refit/restoration material and other useful leads.

**Source breadth is intentionally broad; canonical confidence is intentionally strict.**

### SailboatData reference rule

SailboatData is used only after independent HullQ research as a QA/reference comparison.

- no SailboatData value becomes HullQ FieldEvidence;
- no missing HullQ value is filled from SailboatData;
- SailboatData does not resolve conflicts;
- comparison records retain outcomes/anomaly triggers only, not reference field values as HullQ provenance.

### Research corpus

Six waves reached the deliberate minimum corpus:

| Wave | Designs | Cumulative |
|---|---:|---:|
| 01 | 5 | 5 |
| 02 | 12 | 17 |
| 03 | 8 | 25 |
| 04 | 8 | 33 |
| 05 | 8 | 41 |
| 06 | 9 | 50 |

Detailed evidence is under `research/benchmark/waves/` and the rolling ledger is `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`.

### Measured 50-design stress benchmark

Retained coded analysis:

- `research/benchmark/BENCHMARK-50-classification.csv`;
- `research/benchmark/BENCHMARK-50-analysis.md`.

Measured non-exclusive incidences in the intentionally difficult stress corpus:

- authoritative/original-document path found: **44/50 (88%)**;
- appendage/configuration complexity: **42/50 (84%)**;
- temporal/production applicability mattered: **32/50 (64%)**;
- identity/generation/lineage semantics mattered: **30/50 (60%)**;
- option/variant/operating-state semantics mattered: **30/50 (60%)**;
- secondary/community/broker evidence materially needed: **30/50 (60%)**;
- post-hoc reference anomaly/incompleteness/definition issue: **28/50 (56%)**;
- measurement/definition-basis semantics mattered: **22/50 (44%)**;
- material explicit conflict or unresolved question: **20/50 (40%)**.

These values are **not population prevalence estimates**. The corpus was deliberately selected to be difficult.

Actual automated-acceptance rate, false-normalization rate, idempotency, machine processing cost and human review minutes cannot be measured from manual research and are intentionally deferred until an executable importer/persistence path exists.

## Benchmark-derived architecture decision

The 50-design corpus validates most accepted domain foundations and identifies three concrete lossless-data gaps that should be closed **before** freezing PostgreSQL tables:

1. **claim semantics:** existing `EvidenceType` describes source/document class but does not distinguish nominal design values, factory option values, operating-state values, individual-hull values, class-rule constraints, measurement-certificate values, published calculations or identity/chronology claims;
2. **evidence applicability:** FieldEvidence needs structured year/hull/variant/option/state/individual-hull scope where known rather than hiding critical applicability in free-text notes;
3. **research handoff:** master research needs a versioned machine-ingestible `ResearchEvidenceBundle` so source-linked partial/unresolved research can enter deterministic import/persistence without narrative text silently becoming canonical data.

The existing identity model, FieldResolution states, independent appendage axes and raw/normalized separation remain directionally correct and should not be redesigned wholesale.

Operating-state projection and explicit technical/marketing lineage relationships remain bounded later concerns; they do not justify another broad architecture phase before persistence.

## SLICE-0012 — drafted, BLOCKED

`docs/slices/SLICE-0012-evidence-applicability-research-bundle.md` defines the small benchmark-driven contract hardening boundary.

It is intentionally limited to:

- observation claim semantics separate from source/document EvidenceType;
- structured FieldEvidence applicability;
- successor FieldEvidence contract without mutating v0.2;
- versioned ResearchEvidenceBundle;
- structurally separate non-provenance reference-crosscheck entries;
- deterministic runtime/value-object/validation support and benchmark-derived fixtures.

It explicitly excludes PostgreSQL, ORM/migrations, web acquisition/crawling, authority ranking, automatic conflict resolution, broad taxonomy expansion, query/API/frontend work and SailboatData ingestion.

SLICE-0012 remains `BLOCKED` until SLICE-0011 is accepted/DONE. No implementation slice is currently `READY`.

## Near-term path

```text
SLICE-0011  controlled 50-design benchmark + analysis        REVIEW
      ↓
SLICE-0012  evidence applicability + ResearchEvidenceBundle BLOCKED
      ↓
SLICE-0013  PostgreSQL persistence + deterministic importer LATER
      ↓
execute same benchmark through importer/DB                  LATER
      ↓
measure automation/review/idempotency/cost                  LATER
      ↓
1,000-design broad bootstrap                                NOT AUTHORIZED YET
```

The benchmark corpus should not be expanded merely to reach a higher count. Additional designs are justified only if later importer execution exposes a materially missing problem class.

## AI repository workflow — ACTIVE

Implementation slices normally use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It must refuse slices whose own slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned implementation branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

SLICE-0011 is different: it is master-led DESIGN_RESEARCH and is prepared on `research/0011-controlled-benchmark` through PR #22.

## Current closure gates

SLICE-0011 may become `DONE` only after:

- current exact PR head CI passes;
- independent closure review finds no blocking scope/data-governance issue;
- explicit project-owner acceptance;
- PR #22 merge and canonical `main` verification.

Until then:

- do not start SLICE-0012;
- do not start PostgreSQL persistence;
- do not start broad production ingestion;
- do not start unbounded crawler work;
- do not start query/API/frontend/auth/alert work from this research status.
