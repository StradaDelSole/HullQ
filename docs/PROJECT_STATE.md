# HullQ — Current Project State

**Updated:** 2026-08-19  
**Current stage:** Stage 2.8 — SLICE-0009 appendage/configuration normalization READY  
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

The reviewed source landscape also established that official manufacturer material frequently exposes appendage/configuration semantics in brochures, manuals, parts pages or factory-option descriptions rather than one flat model record. Representative source shapes include long/full/fin/bulb/shoal/lifting/centerboard configurations, twin rudders, keel-hung/skeg-hung/partial-skeg arrangements and explicit option/state axes.

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

SLICE-0008 was implemented on `slice/0008-wikidata-rights-gated-adapter`, independently reviewed through four precision amendment rounds and merged through PR #19 on 2026-08-19.

Acceptance evidence:

- accepted final PR head: `491a2db310c75dd6768b15cc1e0dcba57f1a8fc9`;
- GitHub Actions CI run #108: PASS;
- final local implementation report: 606 tests PASS, 90.42% branch coverage, Ruff/format clean, strict mypy clean on SLICE-0008 files, pip-audit clean;
- independent final review: no remaining blockers;
- merge commit: `e7129cd61145a5a33613a08df5c008555ff569c4`.

The accepted boundary provides:

- reviewed Wikidata CC0 source record;
- rights gate before every external request;
- bounded direct sailboat-class WDQS discovery and `wbgetentities` acquisition;
- descriptive contact-bearing User-Agent enforcement and deterministic throttling/error behavior;
- qualifier-aware extraction for manufacturer/designer and common dimensions/mass/count fields;
- FieldEvidence with raw quantity/unit/qualifier semantics preserved;
- strict length-vs-mass dimension guards;
- exact P1092 dimensionless-sentinel handling;
- preferred-language → English fallback;
- deterministic requested/fetched/field-presence/malformed/unsupported/retrieval quality reporting;
- offline deterministic normal CI and explicit opt-in live smoke tests.

SLICE-0008 does **not** write canonical FieldResolution, mutate BoatDesign/BoatModel records, perform broad ingestion, or solve appendage/configuration taxonomy.

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

## Current operational position — SLICE-0009 READY

`docs/slices/SLICE-0009-appendage-configuration-normalization.md` is the only `READY` implementation slice.

The existing BoatDesign schema already defines the target configuration axes and vocabulary: hull configuration/count, keel type/subtype, rudder type/count, skeg type, daggerboard count and centerboard count. SLICE-0009 must reuse these semantics rather than create a second hidden taxonomy.

SLICE-0009 is intentionally conservative and source-agnostic:

- normalize explicit source-backed appendage/configuration observations only;
- preserve raw representation separately from normalized output;
- deterministic exact/alias rules only, no fuzzy/LLM naval-architecture inference;
- fail closed on unknown, proprietary, ambiguous or wrong-axis terms;
- keep keel, rudder, skeg, board and hull axes independent;
- preserve baseline vs named-variant / design-option / state applicability;
- strict non-negative integer count normalization;
- do not create accepted FieldResolution or mutate canonical BoatDesign records;
- no new network adapter, crawler, persistence or derived metric.

The difficult semantic shapes to cover with synthetic repository-safe tests are derived from the reviewed source research: full/long keel with keel-hung rudder, fin/bulb/wing/shoal wording, centerboard and board-state handling, lifting/swing keel options, twin rudders, skeg-hung and partial-skeg rudders, twin rudders with separately explicit skeg protection, multihull configuration/count and proprietary manufacturer terminology routed to review.

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
SLICE-0009  appendage/configuration normalization            READY
      ↓
SLICE-0010  derived metrics                                  BACKLOG
```

This sequencing avoids pretending that sparse/irregular appendage terminology can be solved by a generic scraper. First make explicit configuration evidence safe and deterministic; then build metrics and later source-specific enrichment on top of that boundary.

## Downstream gates

- broad ingestion is not yet authorized;
- OQ-009 is required before technical query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-014 is required before account/auth implementation;
- OQ-015 is required before exposing the stable public HTTP API;
- OQ-006 is required before automated alert cadence/freshness is frozen.

## Do not start yet

- SLICE-0010 or later implementation;
- production broad ingestion;
- PostgreSQL production schema/application persistence;
- FastAPI public API;
- Astro frontend implementation;
- account/auth implementation;
- production marketplace adapters;
- automated alerts;
- multi-source listing deduplication.
