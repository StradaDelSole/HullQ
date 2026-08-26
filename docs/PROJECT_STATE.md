# HullQ — Current Project State

**Updated:** 2026-08-26  
**Current stage:** Stage 3.2 — canonical identity breadth / bounded discovery and admission proof (remains open; SLICE-0025 additionally permits a later bounded Stage-3.3 pilot in parallel)  
**Accepted slices:** SLICE-0001 through SLICE-0024 are owner-accepted / `DONE`  
**Current queue:** SLICE-0025 reproduced the accepted SLICE-0018/0020/0021/0022/0023/0024 evidence boundary and mechanically derived recommendation `BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL`; it is handed off `REVIEW`, not yet independently reviewed or project-owner accepted. No later slice is authorized.

This is a **compact current-state document**. Historical implementation/review detail belongs in slice contracts, acceptance closures, retained research packages and Git history. Do not use this file as a substitute for normative specs or accepted ADRs.

## Current project direction

HullQ is building an independent, provenance-aware sailboat design universe for technical search/discovery, later market integration and reproducible derived metrics.

Primary product loop:

```text
FIND DESIGN -> FIND BOAT FOR SALE -> COMPARE / SAVE -> ALERT
```

HullQ is not intended to become a generic boating super-app.

## Current accepted identity boundary

Accepted canonical identity state remains:

```text
retained direct Wikidata discovery candidates   1,829 QIDs
accepted canonical BoatModels                   1,770
retained historical QID -> HullQ-ID mappings    1,772
SLICE-0021 alternative-route union                  57 QIDs
SLICE-0022 new canonical admissions                  0
SLICE-0023 incremental Wikimedia QID leads          409
SLICE-0024 threshold-set independently-supported     11  (>=12 required -- NOT MET)
```

SLICE-0023 did **not** admit any of its 409 leads, and SLICE-0024's bounded 30-candidate verification pilot did not meet its independent-support threshold. Canonical BoatModels therefore remain exactly **1,770** and the historical crosswalk exactly **1,772**.

## Latest accepted result — SLICE-0023

SLICE-0023 performed one bounded English-Wikipedia category research-lead pilot over exactly:

- `Category:Keelboats`;
- `Category:Catamarans`;
- `Category:Trimarans`.

Accepted measurement:

```text
category memberships before dedup       1,132
unique pages                             1,131
accepted-direct QID overlap                717
retained-alternative QID overlap             4
incremental QID leads                      409
no Wikidata QID                              1

quality sample                              150
plausible_model_or_class_lead               102  (68.00%)
obvious_out_of_scope                         19  (12.67%)
ambiguous                                    29  (19.33%)

recommendation   FOLLOWUP_VERIFICATION_CANDIDATE
```

The recommendation is research-only. It authorizes neither production Wikipedia/Wikimedia discovery nor canonical admission.

Source/request boundary:

```text
Wikipedia requests       27 / 75
  category requests       4
  pageprops requests     23 = ceil(1,131 / 50)
Wikidata requests         3 / 10
total requests           30 / 85
```

Wikipedia article prose, infobox values, tables, images and references remained outside HullQ evidence. Wikidata CC0 context was limited to the deterministic <=150-QID quality sample.

Acceptance evidence:

- implementation PR #61;
- final reviewed implementation head `92dc0320e995542226199509fc7236f29a75a254`;
- exact-head CI `32867281346`: SUCCESS;
- manufacturer reproducibility `32867282317`: SUCCESS;
- implementation merge `ac2868d978f33f42ccc7e9cc2b1885bfa86b23bb`;
- independent-review verdict **ACCEPT**;
- owner acceptance 2026-08-25;
- closure: `docs/slices/SLICE-0023-acceptance-closure.md`.

## Stage interpretation

Stage 3.3 has **not** begun.

The project is still completing breadth/verification rationale for the canonical sailboat identity universe. SLICE-0023 establishes that the bounded Wikimedia path has useful incremental research-lead yield, but any verification/admission campaign over those 409 leads requires separately accepted evidence and governance.

Do not infer that `FOLLOWUP_VERIFICATION_CANDIDATE` means:

- production-source approval;
- identity admission;
- review-queue resolution;
- Tier-1/Tier-2 technical enrichment;
- query-engine/API/frontend authorization.

SLICE-0024 is accepted / `DONE` (see below); it remains only a bounded verification-source pilot over 30 deterministic candidates and its corrected `LOW_INDEPENDENT_VERIFICATION_YIELD` recommendation is research-only and authorizes nothing. SLICE-0025 (see below) additionally permits a later, separately readied slice to pilot a bounded Stage-3.3 Tier-1/basic enrichment subset in parallel with continued Stage-3.2 breadth work; it does not itself perform or authorize that enrichment.

## Accepted foundation

| Slice | Accepted result |
|---|---|
| 0001 | repository bootstrap, locked toolchain, Linux/Windows CI |
| 0002 | independent sailboat-source research + seed evidence |
| 0003 | canonical JSON-Schema contract runtime |
| 0004 | measurement observation + deterministic normalization |
| 0005 | Brand/Organization + BoatModel/BoatDesign identity contracts |
| 0006 | FieldEvidence/FieldResolution provenance boundary |
| 0007 | ResearchJob + deterministic source-rights gate |
| 0008 | rights-gated Wikidata CC0 adapter |
| 0009 | appendage/configuration normalization |
| 0010 | versioned HullQ derived metrics |
| 0011 | controlled 50-design real-web stress benchmark |
| 0012 | pre-canonical observations + explicit promotion + ResearchEvidenceBundle |
| 0013 | PostgreSQL 18 research persistence + deterministic importer |
| 0014 | retained benchmark through real PostgreSQL persistence |
| 0015 | negative-path hardening + Stage-2 G3 PASS |
| 0016 | canonical identity persistence + Tier-0 admission boundary |
| 0017 | controlled Wikidata Tier-0 identity bootstrap |
| 0018 | baseline-preserving direct-discovery expansion; 1,829/1,770/1,772 boundary |
| 0019 | global manufacturer/yard universe + source-yield research |
| 0020 | archive-source clearance pilot; 0 adapter-ready in fixed sample |
| 0021 | alternative Wikidata routes; +57 discovery signals |
| 0022 | admission-safety proof; 0 auto-admissions from the 57 alternatives |
| 0023 | Wikimedia category lead pilot; +409 research leads, follow-up candidate |
| 0024 | independent verification pilot over 30 candidates; 11/24 independently supported (below required 12), accepted `LOW_INDEPENDENT_VERIFICATION_YIELD` |

For exact amendments, hashes, CI runs and acceptance reasoning, read the corresponding `docs/slices/SLICE-XXXX-acceptance-closure.md` and retained package instead of expanding this document.

## Accepted product/data principles

- broad coverage with progressive verification depth;
- breadth and verification depth are independent;
- unknown/conflict is preferable to fabricated completeness;
- source observations, normalized candidates, canonical resolutions and derived values remain distinct;
- provenance is mandatory for accepted production values;
- one model string is not a reliable technical identity boundary;
- configuration/option/year/state-sensitive values must not be flattened into one scalar baseline;
- Brand and builder/manufacturer Organization remain distinct identity concepts;
- keel, rudder and skeg remain independent dimensions;
- monohulls, catamarans and trimarans are first-class;
- SailboatData remains outcome-only post-hoc QA/reference material, never invisible production evidence;
- source access and source reuse rights are separate and fail closed when production/bulk use is not cleared;
- GitHub `main` is canonical shared repository truth;
- bounded slice/PR review + explicit owner acceptance remains mandatory.

## Search, SEO and growth direction

Search architecture and SEO are **product architecture**, not later marketing.

Product-Led SEO is the primary zero-budget acquisition strategy. Binding strategic inputs:

- `docs/PRODUCT_LED_SEO_STRATEGY.md`;
- `docs/research/OQ-018_PRODUCT_LED_SEO_RESEARCH_2026-08-25.md`;
- `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`;
- ADR-0007;
- OQ-018 remains the detailed implementation gate.

Key rule: **indexability is a promoted product state**. Arbitrary faceted-search combinations are not automatically SEO pages. Canonical entity, intentional technical-discovery, comparison, methodology and original-data pages must pass explicit quality/indexability gates.

Search Console is intended as both SEO telemetry and a product/data-enrichment feedback source.

## Mandatory public languages

HullQ's public product must support:

- English;
- German;
- French;
- Portuguese;
- Spanish.

Canonical IDs, technical values, provenance and query semantics remain language-neutral. UI/content/metadata are localized. Exact locale/URL/hreflang/fallback mechanics remain an OQ-018 implementation decision.

Binding requirement: `docs/PRODUCT_LANGUAGE_AND_I18N_REQUIREMENT.md`.

## Monetization direction

Search remains broadly open. Persistence/monitoring/intelligence are preferred monetization surfaces.

Current strategic framing:

```text
HullQ Free — Search everything. Save 5 searches.
```

Potential Pro value includes saved-search expansion, monitoring/alerts and, subject to rights/technical feasibility, listing-price history, price-change alerts, model/generation/configuration market trends, Days-on-Market and price-reduction signals.

## Accepted application/deployment architecture

```text
Cloudflare edge
      |
      v
portable Linux VPS baseline (initial provider: Contabo)
      |
      +-- Astro + TypeScript web
      |     \-- React islands only where justified
      +-- FastAPI / CPython 3.14
      +-- PostgreSQL
      +-- scheduled/background Python worker when justified
      \-- simple VPS deployment / Caddy baseline

Off-VPS backup/artifact direction: Cloudflare R2 when introduced
Later native mobile: Flutter Android/iOS via the same accepted API boundary
```

Do not introduce a client-only SPA, second business-logic backend, dedicated search engine, Kubernetes/distributed infrastructure or paid managed dependency without measured need + accepted decision.

Important deferred boundaries:

- OQ-009: technical query-engine semantics;
- OQ-014: auth/session/provider mechanics;
- OQ-015: stable public HTTP/API/versioning boundary;
- OQ-018: detailed public Search/SEO URL/index/rendering/canonical/i18n behavior;
- OQ-006: alert cadence/freshness.

## PostgreSQL environment separation

Development/database environments stay separate:

```text
permanent local PostgreSQL 18
→ durable HullQ development environment / DBeaver / later local data

temporary Claude/test PostgreSQL
→ isolated destructive/replay/integration work, optionally on another port

GitHub Actions PostgreSQL 18
→ ephemeral CI-only service, unrelated to the local development DB
```

Tests/replays should not unnecessarily mutate the permanent local development DB.

## AI-assisted development workflow

Current workflow is token-efficient and slice-first:

- one Claude conversation per slice;
- fresh conversation or `/clear` at a new-slice boundary;
- read the slice contract first;
- load only explicitly required dependencies/sections;
- use `/context` to diagnose context growth;
- use `/compact` for a long same-slice continuation/amendment when directed;
- concise but complete handoff reports;
- full validation only at the required handoff boundary rather than repeatedly without reason.

Binding files:

- `CLAUDE.md`;
- `docs/engineering/AI_TOKEN_EFFICIENCY.md`;
- `docs/engineering/AI_SLICE_WORKFLOW.md`;
- `scripts/workflow/start-slice.ps1`.

The project master/reviewer should explicitly direct the operator with `NOW: /clear` or `NOW: /compact` when appropriate.

## Accepted result — SLICE-0024

SLICE-0024 performed a deterministic **30-QID independent identity-verification/source-cost pilot** over the final accepted SLICE-0023 quality sample. The project owner explicitly accepted its **corrected blocked finding** as `DONE`: the primary contract correctly retains historical status `BLOCKED` because two candidates (`Q119855214`, `Q30681833`) truly exceeded the fixed per-candidate search-query ceiling during original execution, but the bounded research slice is complete and its negative/blocked outcome is the accepted final result.

Accepted corrected result: 11 `in_scope_identity` / 8 `out_of_scope` / 0 `conflict` / 11 `unresolved`; among the 24 prior plausible+ambiguous threshold candidates, only 11 were independently supported `in_scope_identity` (**below** the required >=12); global totals 50 searches / 71 evaluations / 121 combined actions (within global ceilings 60/120/180). The precommitted mechanical recommendation rule yields **`LOW_INDEPENDENT_VERIFICATION_YIELD`** — a research-only signal, not an authorization of anything.

SLICE-0024 performed zero canonical admission, minted no HullQ ID, changed no historical crosswalk and began no Stage-3.3 enrichment.

Retained package: `research/bootstrap/wikimedia/sl0024-independent-verification/`. Primary contract: `docs/slices/SLICE-0024-wikimedia-lead-independent-identity-verification-pilot.md`. Closure: `docs/slices/SLICE-0024-acceptance-closure.md` (owner acceptance 2026-08-25).

## Current queue — SLICE-0025 `REVIEW`

SLICE-0025 is a bounded `VALIDATION` slice: using only the already-accepted SLICE-0018/0020/0021/0022/0023/0024 evidence above (no new external research, no canonical mutation), it reproduces the fixed accepted evidence boundary directly from retained artifacts and mechanically applies a precommitted decision rule to choose between remaining Stage-3.2-only and beginning a bounded Stage-3.3 pilot in parallel.

None of the four known Stage-3.2 breadth mechanisms (a larger SLICE-0018 direct-discovery limit, SLICE-0020 manufacturer/archive bulk bootstrap, the SLICE-0021/0022 alternative Wikidata route, or a full SLICE-0023/0024 Wikimedia-lead campaign) qualifies as an unexecuted, already-cleared, materially-different, >=100-yield route. All accepted parallel-readiness conditions (zero-tolerance identity foundation, >=1,000 and >=1,770 canonical BoatModels, SLICE-0022's zero auto-admissions, SLICE-0024's below-threshold yield, a boundable deterministic subset) are met, so the mechanically derived recommendation is:

```text
BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL
```

This does **not** declare Stage 3.2 complete, does not declare G4 passed, and does not itself perform or authorize any enrichment, canonical admission, query-engine, API, frontend or other implementation work. Stage 3.2 breadth work remains explicitly open. It permits only a later, separately readied slice to pilot a bounded Stage-3.3 Tier-1/basic-enrichment subset of already-canonical BoatModels.

Retained package: `research/stage3/sl0025-breadth-enrichment-entry/` (`decision_input.json`, `decision_result.json`, `REPORT.md`, `ARTIFACT-DIGESTS.json` plus their JSON schemas), reproducible offline via `scripts/bootstrap/sl0025_breadth_enrichment_entry_decision_runner.py --verify`.

Primary contract: `docs/slices/SLICE-0025-stage-3-2-breadth-sufficiency-stage-3-3-parallel-entry-decision.md`.

This entry records the implementation agent's own measurement and does not constitute independent review or project-owner acceptance. SLICE-0025 is `REVIEW`; it is not `DONE`. No SLICE-0026 or later slice is currently `READY` or authorized.

Operational queue: `docs/slices/INDEX.md`.

No later slice starts automatically.
