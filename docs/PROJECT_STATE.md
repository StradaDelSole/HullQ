# HullQ — Current Project State

**Updated:** 2026-08-20  
**Current stage:** Stage 2.10–2.11 — SLICE-0011 controlled real-web benchmark research IN_PROGRESS  
**Execution plan:** `docs/EXECUTION_PLAN.md`  
**Operational work queue:** `docs/slices/INDEX.md`

## Completed foundation

- canonical project context established;
- broad-coverage / progressive-depth data strategy accepted;
- 50–100 design corpus defined as research benchmark only;
- single-repository rule accepted (ADR-0001);
- docs-to-code method accepted (ADR-0002);
- broad-coverage strategy captured as ADR-0003;
- BoatModel / BoatDesign generation / NamedVariant / DesignOption identity accepted (OQ-003 / ADR-0004);
- Brand/Marque and Organization/Builder identity separation accepted (ADR-0011 / `IDENTITY_MODEL.v0.2.md`);
- source-rights/clearance model accepted (OQ-007 / ADR-0005);
- field-level provenance accepted (OQ-004 / ADR-0006);
- search/SEO as first-class product architecture accepted (ADR-0007);
- derived metrics methodology accepted (OQ-001 / ADR-0008);
- Python research toolchain accepted (OQ-010 / ADR-0009);
- initial application/deployment stack accepted (OQ-008/OQ-011/OQ-012 / ADR-0010);
- requirements/test/governance baseline established;
- bounded implementation-slice workflow established under `docs/slices/`;
- isolated AI worktree/single-writer Windows workflow merged and active.

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

Auth remains deferred under OQ-014. OQ-006 controls alert cadence/freshness; OQ-015 controls the stable HTTP API/versioning boundary; OQ-018 controls exact public SEO URL/index/rendering/canonicalization/structured-data behavior.

## Completed evidence gate — SLICE-0002

SLICE-0002 is `DONE`. Main retained findings:

1. Wikidata CC0 is the strongest current broad bootstrap candidate.
2. No single SailboatData replacement exists; HullQ needs broad open bootstrap plus progressive primary-source enrichment.
3. Common scalar fields are widely obtainable, but appendage/configuration depth is substantially harder.
4. Displacement/sail-area basis and option-sensitive values must remain explicit.
5. Primary sources can conflict; resolution remains field-specific and auditable.
6. ORC remains blocked for systematic commercial ingestion under reviewed terms absent separate permission/licence.
7. Rudder/skeg classification is expected to drive disproportionate review cost.

The reviewed source landscape also established that official manufacturer material frequently exposes appendage/configuration semantics in brochures, manuals, parts pages or factory-option descriptions rather than one flat model record.

## Completed implementation — SLICE-0003

### Canonical JSON-Schema Contract Runtime — DONE

Merged through PR #3 after green Ubuntu/Windows/dependency-audit CI and independent review.

Final merge commit: `b927a6b17e204de43773c8682e36a29db037ab8a`.

## Completed implementation — SLICE-0004

### Measurement Observation and Deterministic Unit/Basis Normalization — DONE

Merged through PR #4 on 2026-08-18.

Acceptance evidence:

- accepted implementation head: `a473c4778ad134df8ba9f8f803a5f71c5f031132`;
- GitHub Actions run #65: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- independent review: ACCEPT, no blocking findings;
- final merge commit: `ec6ceabbc45970be286adac68cc0095aa2f1f9d1`.

## Completed implementation — SLICE-0005

### Identity Contracts and Deterministic Search Labels — DONE

Merged through PR #10 on 2026-08-18 after independent amendment review.

Acceptance evidence:

- accepted implementation head: `38520ce0ed12ec4d33f747fe1121c229d3df5279`;
- GitHub Actions run #77: PASS;
- final merge commit: `e46857ab9d76a2e83f0ceef9e6878db7f2f66022`.

The accepted boundary establishes separate first-class Brand and Organization identities, stable entity-scoped aliases, versioned BoatModel/BoatDesign identity contracts, independently addressable Brand↔BoatModel and Organization↔BoatDesign relationships, shared relationship applicability and deterministic non-destructive search-label projections.

## Completed implementation — SLICE-0006

### Provenance and Raw Observation Boundary — DONE

Merged through PR #14 on 2026-08-19 after multiple precision amendments.

Acceptance evidence:

- accepted implementation head: `c934dc615d306ef8d8ad11a5024925e650933c27`;
- GitHub Actions run #86: PASS;
- final merge commit: `c0163795df3c4efb27102163770da0f7ff8cedbb`.

The accepted boundary provides shared provenance subjects, successor FieldEvidence/FieldResolution contracts, immutable raw source observations separate from normalized candidates, strict RFC 6901 field addressing, append-oriented supersession/current-resolution validation and reverse-impact lookup.

## Completed implementation — SLICE-0007

### ResearchJob and Source-Rights Gate — DONE

Merged through PR #17 on 2026-08-19.

Acceptance evidence:

- accepted implementation head: `8bf3347c7751be1bbf9b364f3d1f44635dd98eef`;
- GitHub Actions run #96: PASS;
- final merge commit: `ca5ac38d5d402aa9e1b5d366d30d2ce0b2cdee53`.

The accepted boundary provides deterministic use-specific rights decisions, fail-closed overall assessment, independent automated-access checks, machine-visible obligations, source-bound cumulative extraction telemetry, projected-usage limits and ResearchJob/provenance integration.

## Completed implementation — SLICE-0008

### First Rights-Gated Real Adapter: Wikidata — DONE

SLICE-0008 was independently reviewed through four precision amendment rounds and merged through PR #19 on 2026-08-19.

Acceptance evidence:

- accepted final PR head: `491a2db310c75dd6768b15cc1e0dcba57f1a8fc9`;
- GitHub Actions CI run #108: PASS;
- final local implementation report: 606 tests PASS, 90.42% branch coverage, Ruff/format clean, strict mypy clean on SLICE-0008 files, pip-audit clean;
- independent final review: no remaining blockers;
- merge commit: `e7129cd61145a5a33613a08df5c008555ff569c4`.

The accepted boundary provides a reviewed Wikidata CC0 source record, rights gate before external requests, bounded sailboat-class discovery/entity acquisition, qualifier-aware FieldEvidence, strict physical-dimension guards, exact P1092 dimensionless handling, deterministic language fallback and source-quality reporting. It does not create canonical FieldResolution, mutate BoatDesign/BoatModel, perform broad ingestion or solve configuration taxonomy.

## Completed implementation — SLICE-0009

### Appendage / Configuration Normalization — DONE

SLICE-0009 was implemented on `slice/0009-appendage-configuration-normalization`, independently reviewed, amended for scope-safe projection and snapshot-safe raw observations, and merged through PR #20 on 2026-08-19.

Acceptance evidence:

- accepted final PR head: `9da6a579881b0451a028426b80a8a7281e6f6a0b`;
- GitHub Actions CI run #114: PASS;
- final local implementation report: 792 tests PASS, 91.20% total branch coverage, `configuration.py` 98.88% branch coverage, repository validator PASS, Ruff/format clean, strict mypy clean, pip-audit clean;
- independent final review: no remaining blockers;
- merge commit: `001ca87817f37553b463ca01270c64a26b7716b6`.

The accepted boundary provides deterministic exact/explicit-alias configuration normalization, independent keel/rudder/skeg/hull/board axes, strict count handling, option/variant/state scope preservation, snapshot-safe raw observations and fail-closed baseline projection. It does not perform canonical conflict resolution, source acquisition, persistence or derived calculations.

## Completed implementation — SLICE-0010

### Derived Metrics Engine — DONE

SLICE-0010 implemented methodology `hullq-derived-1.0.0` and was independently reviewed, amended and merged through PR #21 on 2026-08-19.

Acceptance evidence:

- accepted final implementation/PR head: `601af0e859a8c771640f473394b78efa32bf918c`;
- GitHub Actions run #120: PASS on the exact accepted head;
- final local implementation report: 915 tests PASS, 92.62% branch coverage, `derived_metrics.py` 99.50% branch coverage, repository validator PASS, Ruff/format clean, strict mypy clean, pip-audit clean;
- independent review found four precision issues; all four were amended and rechecked with no remaining blockers;
- merge commit: `8f9a5ab07f454d6dfbfcb2f133c80c48b14dcc4a`.

The accepted runtime computes the six approved metrics only from explicit effective inputs, preserves status/basis/applicability semantics, exposes exact six-decimal canonical output and emits DerivationRecord lineage without creating fake source evidence. It does not implement configuration resolution, source conflict resolution, persistence, query semantics, API/frontend behavior or safety/seaworthiness scoring.

## AI repository workflow — ACTIVE

Implementation slices normally use:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated slice worktree/branch and copies Claude's instruction to the clipboard. It refuses implementation slices whose own slice document is not explicitly `READY`.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned `slice/...` branch. The master/architect does not write Claude's active implementation branch. No later implementation slice begins automatically.

SLICE-0011 is deliberately different: it is a master-led DESIGN_RESEARCH slice. ChatGPT/master research performs the real-web evidence work; Claude Code is not used as the autonomous web-research agent. Research updates are prepared on `research/0011-controlled-benchmark` and go through a PR before becoming canonical.

## Current operational position — SLICE-0011 IN_PROGRESS

The project owner explicitly authorized the controlled real-data benchmark after SLICE-0010 acceptance.

Research method:

```text
selected difficult design
      ↓
broad independent web research
      ↓
source ranking + raw evidence/context capture
      ↓
corroboration / conflict detection
      ↓
post-hoc reference comparison
      ↓
structured benchmark evidence
      ↓
measured ambiguity/completeness/review findings
```

The active source policy is deliberately broad: manufacturer/shipyard material, brochures/manuals, designers, class/owners associations, archives, specialist publications/databases, brokers where appropriate, forums/owner communities, refit/restoration material and other useful web leads may all contribute. Evidence confidence remains source- and field-specific.

**Source breadth is intentionally broad; canonical confidence is intentionally strict.**

SailboatData is used only as a post-hoc reference comparison after independent research. Its field values are not HullQ evidence, are not used as fallbacks and do not resolve conflicts. The benchmark records only comparison outcomes/anomaly triggers.

### Wave 01

- 5 designs;
- 58 structured observations;
- Hallberg-Rassy 36, Westerly Centaur, RM 1180, Najad 34, J/24.

### Wave 02

- 12 designs;
- 138 structured observations;
- Dragonfly 32, OVNI 370, Garcia Exploration 45, Boréal 44.2, Island Packet 349, Corsair 880, Lagoon 42 (2016), Nauticat 33→331, Catalina 316, Jeanneau Sun Odyssey 410, CATANA Ocean Class, Pogo 1.

Current actively re-researched benchmark count: **17 designs** toward the 50–100 target.

Early recurring problem classes already include model-name reuse, named variants, option-sensitive mass/draft, board-state geometry, folded multihull geometry, proprietary appendage vocabulary, rudder↔skeg relationships, primary-source internal contradiction, cross-source appendage conflict, design-vs-individual-boat values and displacement/sail-area basis differences.

See:

- `docs/slices/SLICE-0011-controlled-benchmark-research.md`;
- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`;
- `research/benchmark/waves/WAVE-01-summary.md`;
- `research/benchmark/waves/WAVE-02-summary.md`.

## Revised near-term path to real data

```text
SLICE-0005  identity contracts/search labels                 DONE
      ↓
SLICE-0006  provenance/raw-observation boundary              DONE
      ↓
SLICE-0007  ResearchJob + source-rights clearance gate       DONE
      ↓
SLICE-0008  first rights-gated real adapter — Wikidata       DONE
      ↓
SLICE-0009  appendage/configuration normalization            DONE
      ↓
SLICE-0010  derived metrics                                  DONE
      ↓
SLICE-0011  controlled real-web benchmark                    IN PROGRESS
      ↓
next persistence/import implementation slice                TO BE REFINED FROM BENCHMARK
      ↓
broad design-universe ingestion                             NOT AUTHORIZED YET
```

## Downstream gates

- broad production ingestion is not yet authorized;
- production PostgreSQL schema/application persistence remains deferred until the benchmark justifies the exact boundary;
- OQ-009 is required before technical query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-014 is required before account/auth implementation;
- OQ-015 is required before exposing the stable public HTTP API;
- OQ-006 is required before automated alert cadence/freshness is frozen.

## Do not start yet

- broad production ingestion;
- unbounded crawler work;
- PostgreSQL production persistence implementation before the benchmark-derived slice is specified;
- FastAPI public API;
- Astro frontend implementation;
- account/auth implementation;
- production marketplace adapters;
- automated alerts;
- multi-source listing deduplication.
