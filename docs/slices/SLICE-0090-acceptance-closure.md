# SLICE-0090 — Owner Acceptance Closure

**Status:** OWNER_ACCEPTED — docs-only DESIGN_RESEARCH; Owner-local FINISH pending  
**Capability:** Sail+Power technical-search architecture and source-rights feasibility decision pack  
**Research implementation PR:** [#379](https://github.com/StradaDelSole/HullQ/pull/379)  
**Independently reviewed and Owner-accepted branch HEAD:** `847c56cde1c48ea285da87ac70c72a6cfdfde5b8`  
**Implementation squash merge on main:** `0e78f2c64c2d21e0b2fd5d8a97213b49cbdedeb8`  
**Owner acceptance:** Explicit “ok akzeptiert, weiter bitte” on 2026-10-26 (Europe/Vienna), after independent exact-HEAD review, subject to successful CI; this condition was subsequently verified PASS before merge.  
**Controlling contract:** `docs/slices/SLICE-0090-sail-power-architecture-source-rights.md`; binding Sail+Power direction [#366](https://github.com/StradaDelSole/HullQ/issues/366), requirements tracker [#372](https://github.com/StradaDelSole/HullQ/issues/372), external-data STOP [#355](https://github.com/StradaDelSole/HullQ/issues/355).

## Accepted research deliverables — NOT product implementation

- `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md`: independently rechecked as-is Sail Search architecture, unified MUST/AND nine-criterion kernel, D29 eligibility and claim provenance; clearly labeled **draft/non-accepted** to-be category, qualified design-unresolved candidate path, Power criterion reuse, temporal installed-equipment evidence, conditional operating-point model and proposed bounded future dependency map A–H.
- `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`: nine distinct **external source families** (1, 2, 3a, 3b, 5, 6, 7, 8, 9), plus separate first-party broker claims (4), with source-specific evidence quality, date, reuse condition and absence of actual operational ingestion authorization; some sources remain INDIRECT/UNKNOWN or inaccessible. Summary classes external: GREEN 3 (including scope-limited commercial fishing reference), AMBER 2, RED/RED-UNKNOWN 2, UNKNOWN 2. This research does not independently license or clear commercial source acquisition.
- `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md`: 13 labeled **synthetic tabletop** hard cases, covering multihulls, motorsailer, planing/displacement, generation variants, refits, unknown/conflicting categories, design-unresolved current qualified claims, revisions/retractions, conditional speed/consumption/range and real NautiX round-trip loss. These are **not executable tests**.
- Code-verified constraints for future slices: `inventory_search.py` requires `boat_design_ref IS NOT NULL`; NautiX import accepts Sail only; NautiX export emits a fixed, unguarded `sail-yacht` tag. Directly inspected pinned NautiX 1.4 XSD already supports **33 `power-*` tokens**, 14 Sail tokens and `sail-motorsailer` — no unsupported claim that the schema inherently excludes Power.

No code, migrations, provider credentials, external broker files, production data, real Sail+Power search, new feature, public product pilot or authorization to ingest any external source was added.

## Independent review and exact-HEAD verification

Independent findings A–K were corrected on the same slice implementation branch across reviewed commits:
- Initial `2a33b6ad774a4188e80ef89b72827d1deba18935`: findings A–G exposed unverified rights families/overstated clearance, incomplete evidence qualification, refit precedence, unsupported NautiX assumptions and range inference.
- `254919b3f6489775dc437fa489adfb3ba8199903`: A–G corrected; H–J remaining category token count, external-family totals and CC0 bulk reuse distinction.
- `bf44512255e19a8ff4797b0c1b54d63e7f83d25e`: H–J corrected; K remaining summary disposition reconciliation.
- Accepted `847c56cde1c48ea285da87ac70c72a6cfdfde5b8`: K corrected; independent review PASS and only docs files changed.

| Exact accepted-head gate | Verified |
|---|---|
| [CI run 40365750259](https://github.com/StradaDelSole/HullQ/actions/runs/40365750259) | **SUCCESS** — six jobs: web quality, dependency audit, Ubuntu/Windows quality, PostgreSQL 18 DB integration, historical PostgreSQL 18 replay |
| [Manufacturer reproducibility 40365750376](https://github.com/StradaDelSole/HullQ/actions/runs/40365750376) | **SUCCESS** |
| [Deploy workflow 40365750273](https://github.com/StradaDelSole/HullQ/actions/runs/40365750273) | **SUCCESS** workflow, **not** evidence of real production deployment |
| Local repository governance validation | Implementer reports `uv run python scripts/validate_repository.py` PASS; not independently rerun locally |
| Runtime proof of Power Search/rights ingestion | **NOT PERFORMED / NOT APPLICABLE** in docs-only research |

Research [PR #379](https://github.com/StradaDelSole/HullQ/pull/379) squash-merged **after Owner acceptance** and all exact-HEAD remote gates turned green. Tracking-only comment posted to open [#372](https://github.com/StradaDelSole/HullQ/issues/372) — issue stays OPEN for future implementation.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED (before this slice; preserved):** current nine Sail native technical criteria; common Search evaluator with retained evidence, existing publisher claim revisions, D29 eligibility; 0083 multiformat broker import, 0088 seven-format export, 0089 nonproduction periodic reporting.

**ACCEPTED AS RESEARCH ONLY:** reviewed feasible shared Sail+Power extension pattern, auditable source-rights gaps and negative fixture specification. Future A–H architecture rows are proposals, **not Owner-approved implementation designs, source rights or selected subsequent slices**.

**GENUINELY OPEN / NOT YET IMPLEMENTED:** explicit Sail/Power/motorsailer/unknown/conflict policy and suitable Power field vocabulary; qualified design-unresolved listing search, source-aware installed/refit/operating claims; Power criteria and Buyer/Broker Search-fit parity; per-source legal clearance and production ingestion; category-aware import/export; five-locale buyer/broker product completeness, local browser check [#363](https://github.com/StradaDelSole/HullQ/issues/363).

**EXPLICITLY DEFERRED / STOP:** full joint Sail+Power specialist offering before first external product pilot [#366](https://github.com/StradaDelSole/HullQ/issues/366); [#355](https://github.com/StradaDelSole/HullQ/issues/355) production hardening before real external broker uploads, production provider/operations/rights; Production Launch Pack NOT_STARTED, production readiness IN_PROGRESS; buyer Saved Search/alerts, owner-direct trust and scaled onboarding; XLSB export [#362](https://github.com/StradaDelSole/HullQ/issues/362).

## State transition and Owner action

```text
PROJECT_STATE_ACCEPTED_SLICE: 0090
PROJECT_STATE_QUEUE_SLICE: 0091 — NOT SELECTED / NOT READY
SLICE_0090_TYPE: DESIGN_RESEARCH
SLICE_0090_RESULT: OWNER_ACCEPTED_RESEARCH_ONLY
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

This is the **separate docs-only acceptance closure** for research, not a Power implementation declaration. Independently review the closure exact HEAD, correct status markers and CI/manufacturer gates and merge this closure PR. **Only after that merge** does the Owner execute the unchanged local `FINISH_SLICE.bat`, entering `0090`. No subsequent slice starts automatically.
