# HullQ — Current Project State

**Updated:** 2026-08-18  
**Current stage:** Stage 2.3 complete — SLICE-0004 DONE; next implementation slice not yet READY  
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
- bounded implementation-slice workflow established under `docs/slices/`.

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

Auth remains deliberately deferred under OQ-014. OQ-006 still controls alert cadence/freshness; OQ-015 controls the stable HTTP API/versioning boundary; OQ-018 controls exact public SEO URL/index/rendering/canonicalization/structured-data behavior.

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

SLICE-0004 was implemented by Claude Code, independently reviewed, explicitly accepted by the project owner and merged through PR #4 on 2026-08-18.

Final merge commit: `ec6ceabbc45970be286adac68cc0095aa2f1f9d1`.

Acceptance evidence:

- accepted implementation head: `a473c4778ad134df8ba9f8f803a5f71c5f031132`;
- final implementation-agent report: 85/85 tests PASS;
- `measurements.py` 100% branch coverage; total coverage 99.38%;
- Ruff, strict mypy and pip-audit clean;
- GitHub Actions run #65: Ubuntu quality PASS, Windows quality PASS, dependency audit PASS;
- independent review: ACCEPT, no blocking findings;
- explicit project-owner acceptance received on 2026-08-18.

The merged boundary provides deterministic exact conversion for explicit length/mass/area measurements using accepted unit tokens, preserves raw text/semantic labels, keeps ratio-input basis vocabularies aligned with the normative schema, rejects non-finite values and performs no free-text semantic inference or derived-metric rounding.

## Current operational position

No later implementation slice is `READY` yet.

Before Claude starts the next slice:

1. close the new AI single-writer/worktree automation workflow;
2. refine the rolling-wave backlog using accepted ADR-0011 Brand/Builder identity semantics;
3. move exactly one next slice to `READY`;
4. start it from synchronized `origin/main` through the isolated worktree workflow.

The current preferred near-term sequence is to bring real rights-cleared web data earlier than the old backlog order, while preserving the minimum prerequisites for identity, provenance/raw observations and source-rights gating.

## Downstream gates

- broad ingestion is not yet authorized;
- OQ-009 is required before query-engine implementation;
- OQ-018 is required before the public search/SEO surface;
- OQ-014 is required before account/auth implementation;
- OQ-015 is required before exposing the stable public HTTP API;
- OQ-006 is required before automated alert cadence/freshness is frozen.

## Repository working convention

GitHub `origin/main` is canonical truth. Implementation agents work only on assigned slice branches/worktrees; accepted work reaches `main` through review/CI/project-owner acceptance. The dedicated one-click Windows workflow automation is being introduced separately so the project owner does not need to manage routine Git branching manually.

## Retention / freemium direction

Accepted strategic direction remains in `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`: core technical search stays open in the preferred freemium thesis; subscription value attaches primarily to monitoring capacity/frequency and advanced market intelligence. Exact pricing/limits remain OQ-016.

## Do not start yet

- SLICE-0005 or later implementation until explicitly prepared/READY;
- production broad ingestion;
- PostgreSQL production schema/application persistence;
- FastAPI public API;
- Astro frontend implementation;
- account/auth implementation;
- production marketplace adapters;
- automated alerts;
- multi-source listing deduplication.
