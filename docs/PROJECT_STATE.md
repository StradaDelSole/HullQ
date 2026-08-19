# HullQ — Current Project State

**Updated:** 2026-08-19  
**Current stage:** Stage 2.9 — SLICE-0010 derived metrics engine READY  
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

The accepted boundary provides:

- runtime vocabularies matching the existing BoatDesign configuration enums;
- deterministic exact/explicit-alias normalization for keel, rudder, skeg and hull configuration;
- strict count normalization for hull/rudder/centerboard/daggerboard counts;
- explicit unsupported/ambiguous/malformed outcomes rather than guessed mappings;
- independent configuration axes with no twin-rudder/skeg/keel inference;
- baseline/named-variant/design-option/board-state scope preservation;
- required scope identity for named variants/design options;
- fail-closed `baseline_projection()` so non-baseline observations cannot silently become baseline canonical facts;
- snapshot-safe raw configuration observations;
- generic `NormalizedCandidate` integration without changing the SLICE-0006 provenance contract.

SLICE-0009 does **not** create accepted FieldResolution, mutate BoatDesign, perform source acquisition, persist data or calculate derived metrics.

## AI repository workflow — ACTIVE

The project owner normally starts and finishes implementation slices with:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated slice worktree/branch and copies Claude's instruction to the clipboard. It refuses any slice whose own slice document is not explicitly `READY`.

`START_SLICE` deliberately does **not** open, close, reload or switch any VS Code window. The project owner explicitly opens the sibling `HullQ-slice-XXXX` worktree in the desired VS Code window before pasting the prompt.

`FINISH_SLICE.bat` synchronizes local `main` and removes the old clean worktree/local branch only after merged-PR confirmation when GitHub CLI is available.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned `slice/...` branch. The master/architect does not write Claude's active implementation branch. No later implementation slice begins automatically.

## Current operational position — SLICE-0010 READY

`docs/slices/SLICE-0010-derived-metrics-engine.md` is the only `READY` implementation slice.

OQ-001 / ADR-0008 already froze methodology `hullq-derived-1.0.0`. SLICE-0010 is therefore an execution slice, not a research slice. It must implement exactly:

- Sail Area / Displacement (`sa_displ`);
- Ballast / Displacement % (`ballast_displ_pct`);
- Displacement / Length (`displ_length`);
- Brewer Comfort Ratio (`comfort_ratio`);
- Capsize Screening Formula (`capsize_screening_formula`);
- legacy/theoretical Hull Speed (`hull_speed_kn`).

The accepted method already specifies exact Imperial conversion constants, hull applicability, displacement/sail-area basis semantics, status precedence, six-decimal round-half-even canonical precision, and DerivationRecord lineage. `fixtures/ratios/golden_metrics.v0.1.json` and `fixtures/ratios/status_cases.v0.2.json` are compatibility fixtures and must be executed by the runtime tests rather than silently rewritten.

SLICE-0010 must remain bounded:

- consume an explicit caller-supplied effective input snapshot corresponding to accepted `/effective/...` ResolvedConfiguration fields;
- preserve explicit unresolved-field markers and optional input FieldResolution IDs;
- do not implement full BoatDesign + NamedVariant + DesignOption configuration resolution;
- do not resolve source conflicts or choose canonical evidence;
- produce null values for all noncomputed statuses;
- produce schema-valid DerivationRecord lineage for every populated metric;
- do not create fake FieldEvidence for HullQ-calculated outputs;
- no search/filter semantics, persistence, API/frontend behavior or safety/bluewater scoring.

## Revised near-term path to real data

```text
SLICE-0005  identity contracts/search labels                 DONE
      ↓
SLICE-0006  provenance/raw-observation boundary              DONE
      ↓
SLICE-0007  ResearchJob + source-rights clearance gate       DONE
      ↓
SLICE-0008  first rights-gated real data — Wikidata CC0      DONE
      ↓
SLICE-0009  appendage/configuration normalization            DONE
      ↓
SLICE-0010  derived metrics                                  READY
      ↓
controlled benchmark                                        NOT AUTHORIZED YET
```

SLICE-0010 closes the last already-accepted pure calculation boundary needed before the next controlled benchmark wave is refined. The benchmark remains a later slice and must not be started automatically.

## Downstream gates

- broad ingestion is not yet authorized;
- OQ-009 is required before technical query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-014 is required before account/auth implementation;
- OQ-015 is required before exposing the stable public HTTP API;
- OQ-006 is required before automated alert cadence/freshness is frozen.

## Do not start yet

- controlled benchmark implementation beyond the prepared SLICE-0010 boundary;
- production broad ingestion;
- PostgreSQL production schema/application persistence;
- FastAPI public API;
- Astro frontend implementation;
- account/auth implementation;
- production marketplace adapters;
- automated alerts;
- multi-source listing deduplication.
