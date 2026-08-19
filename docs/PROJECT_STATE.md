# HullQ — Current Project State

**Updated:** 2026-08-19  
**Current stage:** Stage 2.7 — SLICE-0008 Wikidata rights-gated adapter REVIEW  
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

## Completed implementation — SLICE-0003

### Canonical JSON-Schema Contract Runtime — DONE

Merged through PR #3 after green Ubuntu/Windows/dependency-audit CI, independent review and explicit project-owner acceptance.

Final merge commit: `b927a6b17e204de43773c8682e36a29db037ab8a`.

## Completed implementation — SLICE-0004

### Measurement Observation and Deterministic Unit/Basis Normalization — DONE

SLICE-0004 was independently reviewed, explicitly accepted and merged through PR #4 on 2026-08-18.

Final merge commit: `ec6ceabbc45970be286adac68cc0095aa2f1f9d1`.

Acceptance evidence:

- accepted implementation head: `a473c4778ad134df8ba9f8f803a5f71c5f031132`;
- GitHub Actions run #65: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- independent review: ACCEPT, no blocking findings.

The accepted boundary provides deterministic exact conversion for explicit length/mass/area measurements, preserves raw source representation and semantic labels, keeps ratio-input basis vocabularies aligned with normative schemas, rejects non-finite values and performs no free-text inference or derived-metric rounding.

## Completed implementation — SLICE-0005

### Identity Contracts and Deterministic Search Labels — DONE

SLICE-0005 was independently reviewed through multiple amendment rounds, explicitly accepted and merged through PR #10 on 2026-08-18.

Final merge commit: `e46857ab9d76a2e83f0ceef9e6878db7f2f66022`.

Acceptance evidence:

- accepted implementation head: `38520ce0ed12ec4d33f747fe1121c229d3df5279`;
- GitHub Actions run #77: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- independent review: ACCEPT, no remaining blockers.

The accepted boundary establishes separate first-class Brand and Organization identities, stable entity-scoped aliases, versioned BoatModel/BoatDesign identity contracts, independently addressable Brand↔BoatModel and Organization↔BoatDesign relationships, a shared relationship applicability core and deterministic non-destructive search-label projections.

## Completed implementation — SLICE-0006

### Provenance and Raw Observation Boundary — DONE

SLICE-0006 was implemented on `slice/0006-provenance-raw-observation-boundary`, independently reviewed through multiple precision amendments, explicitly accepted by the project owner on 2026-08-19 and merged through PR #14.

Acceptance evidence:

- accepted implementation head: `c934dc615d306ef8d8ad11a5024925e650933c27`;
- GitHub Actions run #86: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- final independent review: no remaining blockers;
- implementation merge commit: `c0163795df3c4efb27102163770da0f7ff8cedbb`.

The accepted boundary establishes:

- one shared provenance-subject vocabulary covering BoatModel, BoatDesign, NamedVariant, DesignOption, Brand, Organization, IdentityAlias and both relationship identities;
- successor FieldEvidence/FieldResolution contracts while keeping legacy v0.1 contracts loadable;
- immutable/snapshot-safe raw source observations separate from normalized candidates;
- strict RFC 6901 field addressing, including exact array-index handling;
- append-oriented evidence/resolution supersession and current-resolution history validation;
- explicit conflict/unknown semantics and canonical-value consistency checks;
- Source → FieldEvidence → current/past FieldResolution reverse-impact lookup.

No source-rights gate, network acquisition, persistence, derivation engine or search behavior was introduced in SLICE-0006.

## AI repository workflow — ACTIVE

The project owner normally starts and finishes implementation slices with:

```text
START_SLICE.bat
FINISH_SLICE.bat
```

`START_SLICE.bat` synchronizes `main`, creates/reuses an isolated slice worktree/branch and copies Claude's instruction to the clipboard. It refuses any slice that is not explicitly `READY`.

After PR #15, `START_SLICE` deliberately does **not** open, close, reload or switch any VS Code window. The project owner explicitly opens the sibling `HullQ-slice-XXXX` worktree in the desired VS Code window before pasting the prompt.

`FINISH_SLICE.bat` synchronizes local `main` and removes the old clean worktree/local branch only after merged-PR confirmation when GitHub CLI is available.

GitHub `origin/main` remains canonical truth. Claude owns only its assigned `slice/...` branch. The master/architect does not write Claude's active slice branch. No later implementation slice begins automatically.

## Current operational position — SLICE-0008 REVIEW

`docs/slices/SLICE-0008-wikidata-rights-gated-adapter.md` is the current implementation slice, now in `REVIEW`.

The Wikidata CC0 rights-gated adapter provides:

- reviewed Wikidata Source record (`fixtures/sources/wikidata_source.json`) validated against `SOURCE_SCHEMA.v0.2.json`, CC0-1.0, all HullQ use-clearances allowed;
- `WikidataAdapterConfig` immutable bounded configuration with validated user_agent, request timeout, item limit (capped at `SLICE_0008_ITEM_CEILING = 100`) and language preference;
- SLICE-0007 automated-ingestion rights gate enforced before every HTTP call;
- SPARQL discovery probe (`SELECT ?item WHERE { ?item wdt:P31 wd:Q106179098 }`) bounded to caller limit;
- entity acquisition via `wbgetentities` API in batches of ≤50 QIDs;
- qualifier-aware field extraction for manufacturer (P176), designer (P287), LOA/LWL (P2043 + P642 qualifiers), beam (P2049), draft (P2048 + Q244777), displacement/ballast (P2067 + Q5636358/Q5461048), and number built (P1092);
- SLICE-0006 FieldEvidence with preserved raw observations and SLICE-0004 normalization reused for supported quantity units;
- deterministic `WikidataQualityReport` covering requested/fetched/field-presence/malformed/unsupported/attributed counts;
- explicit typed errors for rights-blocked, throttled (429/Retry-After), HTTP error, timeout, and malformed response;
- 70 offline unit tests, 17 contract tests, 2 opt-in live integration smoke tests;
- 567 total tests PASS, 90.13% branch coverage (≥90% required), ruff lint/format clean, strict mypy clean on new files, no known vulnerabilities.

SLICE-0008 does **not** write canonical FieldResolution, modify BoatDesign/BoatModel records, perform broad ingestion, introduce appendage taxonomy, or implement persistence.

Branch `slice/0008-wikidata-rights-gated-adapter` is pushed to GitHub. Independent review and project-owner acceptance are required before `DONE`.

SLICE-0009 must not start automatically.

## Revised near-term path to real data

```text
SLICE-0005  identity contracts/search labels                 DONE
      ↓
SLICE-0006  provenance/raw-observation boundary              DONE
      ↓
SLICE-0007  ResearchJob + source-rights clearance gate       DONE
      ↓
SLICE-0008  FIRST RIGHTS-GATED REAL DATA — Wikidata CC0     REVIEW
      ↓
inspect actual source quality
      ↓
SLICE-0009  appendage/configuration normalization
      ↓
SLICE-0010  derived metrics
```

This avoids over-designing the hardest appendage/configuration layer from imagined source formats. Broad ingestion remains gated by controlled real-data inspection and the 50–100 difficult-design benchmark.

## Downstream gates

- broad ingestion is not yet authorized;
- OQ-009 is required before technical query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-014 is required before account/auth implementation;
- OQ-015 is required before exposing the stable public HTTP API;
- OQ-006 is required before automated alert cadence/freshness is frozen.

## Do not start yet

- SLICE-0009 or later implementation (SLICE-0008 must complete review/acceptance first);
- production broad ingestion;
- PostgreSQL production schema/application persistence;
- FastAPI public API;
- Astro frontend implementation;
- account/auth implementation;
- production marketplace adapters;
- automated alerts;
- multi-source listing deduplication.
