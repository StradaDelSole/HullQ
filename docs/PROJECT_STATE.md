# HullQ — Current Project State

**Updated:** 2026-08-20  
**Current stage:** Stage 2.12 — SLICE-0012 evidence/applicability/research-bundle contract `READY`  
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
Retained findings include broad open bootstrap + progressive independent enrichment, explicit measurement/configuration semantics, conflict preservation and stronger appendage review needs. The old/reference SailboatData material remains research/reference only and MUST NOT become an invisible production-value source.

### SLICE-0003 — canonical contract runtime — DONE
Draft-2020-12 schema registry/validation boundary accepted and merged.

### SLICE-0004 — measurement normalization — DONE
Deterministic exact unit normalization accepted with raw text/semantic-label preservation and no arbitrary-string inference.

### SLICE-0005 — identity contracts/search labels — DONE
Accepted Brand/Organization identities, BoatModel/BoatDesign separation, entity-scoped aliases and deterministic search-label projections.

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

### SLICE-0011 — controlled 50-design benchmark — DONE

The master/ChatGPT-led real-web benchmark reached the 50-design minimum gate and was explicitly accepted by the project owner.

Acceptance evidence:

- final accepted PR head: `9f1859fe9762e05bd2a5be57c550f255be302c9b`;
- GitHub Actions CI run #151: PASS on that exact head;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- independent closure review: no remaining blocking scope/data-governance issue;
- explicit project-owner acceptance on 2026-08-20;
- PR #22 merged on 2026-08-20;
- merge commit: `668e91937d27dc9c70760301b92ce0ded41abb2f`.

Research policy was:

```text
broad independent web research
→ source-linked raw observation/context
→ corroboration/conflict detection
→ post-hoc reference comparison
→ benchmark classification/measurement
→ persistence requirements derived from evidence
```

SailboatData remained outcome-only QA/reference comparison after independent research: no reference field value became HullQ FieldEvidence/ResearchObservation, no missing value was filled from it, and it did not resolve conflicts.

Six waves covered 50 deliberately difficult designs. The retained exact pre-contract Wave 01/02 exports remain under `research/benchmark/legacy-observations/` as migration fixtures only.

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

These values are stress-corpus incidences, not population prevalence estimates.

## Benchmark-derived architecture decision

The 50-design corpus validates most accepted domain foundations and identifies four concrete lossless-data gaps that should be closed **before** freezing PostgreSQL tables:

1. **pre-canonical observation:** accepted `ResearchJob.target` is deliberately only raw `manufacturer/model/first_built` and may not yet have a stable HullQ subject, while FieldEvidence requires a typed canonical `ProvenanceSubject`; web research therefore needs a pre-canonical `ResearchObservation` boundary;
2. **claim semantics:** existing `EvidenceType` describes source/document class but does not distinguish nominal design values, factory option values, operating-state values, individual-hull values, class-rule constraints, measurement-certificate values, published calculations or identity/chronology claims;
3. **observation/evidence applicability:** structured year/hull/variant/option/state/individual-hull scope is needed where known rather than hiding critical applicability in free-text notes;
4. **research handoff + promotion:** master research needs a versioned machine-ingestible `ResearchEvidenceBundle`; promotion from ResearchObservation to successor FieldEvidence must require an explicit caller-supplied stable canonical subject after identity resolution and must not itself perform identity resolution or FieldResolution.

The existing identity model, FieldResolution states, independent appendage axes and raw/normalized separation remain directionally correct and should not be redesigned wholesale.

## Current operational position — SLICE-0012 READY

`docs/slices/SLICE-0012-evidence-applicability-research-bundle.md` is the only current READY implementation slice.

It is intentionally limited to:

- pre-canonical immutable ResearchObservation;
- observation claim semantics separate from source/document EvidenceType;
- structured applicability/scope;
- successor FieldEvidence without mutating v0.2;
- explicit deterministic promotion only after caller supplies stable `ProvenanceSubject`;
- versioned ResearchEvidenceBundle that supports partial/identity-ambiguous research;
- structurally separate non-provenance reference-crosscheck entries;
- deterministic runtime/value-object/validation support and benchmark-derived fixtures.

It explicitly excludes PostgreSQL, ORM/migrations, web acquisition/crawling, fuzzy identity resolution, authority ranking, automatic conflict resolution, broad taxonomy expansion, query/API/frontend work and SailboatData ingestion.

SLICE-0012 may be started only through the normal `START_SLICE.bat` isolated worktree workflow. Claude Code implements exactly this slice and must return the mandatory completion report. The implementation agent must not mark it `DONE`; normal successful handoff is `REVIEW`.

## Near-term path

```text
SLICE-0011  controlled 50-design benchmark + analysis        DONE
      ↓
SLICE-0012  ResearchObservation + applicability/bundle       READY
      ↓
SLICE-0013  PostgreSQL persistence + deterministic importer  LATER / NOT READY
      ↓
identity/promotion + same benchmark through importer/DB      LATER
      ↓
measure automation/review/idempotency/cost                   LATER
      ↓
1,000-design broad bootstrap                                 NOT AUTHORIZED YET
```

The benchmark corpus should not be expanded merely to reach a higher count. Additional designs are justified only if later importer execution exposes a materially missing problem class.

## AI repository workflow — ACTIVE

Implementation slices use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated worktree/branch and copies Claude's assignment. It must refuse slices whose own slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned implementation branch. The master/architect does not write Claude's active implementation branch. No later slice begins automatically.

## Do not start yet

- SLICE-0013 / PostgreSQL persistence before SLICE-0012 acceptance;
- broad production ingestion;
- unbounded crawler work;
- query-engine implementation;
- public FastAPI API;
- Astro frontend;
- account/auth;
- marketplace adapters;
- alerts/monitoring execution;
- multi-source listing deduplication.
