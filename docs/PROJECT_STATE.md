# HullQ — Current Project State

**Updated:** 2026-08-25  
**Current stage:** Stage 3.2 — canonical identity breadth / bounded discovery and admission proof  
**Accepted slices:** SLICE-0001 through SLICE-0023 are owner-accepted / `DONE`  
**Current queue:** SLICE-0024 implementation is complete and handed off as `REVIEW`; it is not yet accepted/`DONE`. No later slice is authorized.

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
```

SLICE-0023 did **not** admit any of its 409 leads. Canonical BoatModels therefore remain exactly **1,770** and the historical crosswalk exactly **1,772**.

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

SLICE-0024's implementation is complete and handed off as `REVIEW` (not yet accepted/`DONE`); it remains only a bounded verification-source pilot over 30 deterministic candidates and its `FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE` recommendation does not itself authorize a full campaign.

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

## Current next boundary — SLICE-0024 implementation complete, `REVIEW`

SLICE-0024 performed a deterministic **30-QID independent identity-verification/source-cost pilot** over the final accepted SLICE-0023 quality sample:

```text
prior plausible   18
prior ambiguous    6
prior out-of-scope 6
```

The prior tags were used only as calibration metadata, never as new-outcome evidence. Each of the 30 candidates was researched under the strict per-candidate (<=2 search / <=4 source-page-eval / <=6 combined) and global (<=60 / <=120 / <=180) action ceilings. Qualifying evidence came only from the accepted strong source hierarchy (manufacturer/shipyard, brochure, owner's/technical manual, designer/naval architect, class association, owners' association, museum/archive) or, secondarily, two genuinely independent high-quality specialist sources. Wikipedia/Wikidata context, search snippets and SailboatData were used only as discovery, never as qualifying verification evidence.

Measured result: 13 `in_scope_identity` / 6 `out_of_scope` / 0 `conflict` / 11 `unresolved`; among the 24 prior plausible+ambiguous threshold candidates, 13 were independently supported `in_scope_identity` (>=12 required) and 12 of those were `strong_source` (>=8 required); median combined research actions among independently-supported in-scope candidates was 2.0 (<=4 required); global totals 48 searches / 71 evaluations / 119 combined actions, all within ceiling. The precommitted mechanical recommendation rule yields **`FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE`** — a research-only signal that does not itself authorize a full campaign, canonical admission or Stage-3.3 enrichment.

SLICE-0024 did not:

- create any canonical identity;
- mint any HullQ ID;
- change the historical crosswalk;
- grant any new production source clearance;
- begin Stage-3.3 enrichment;
- create/start SLICE-0025.

Two self-corrected process deviations are retained: for two candidates (`Q119855214`, `Q30681833`) a third discovery-search query was issued before the 2-query-per-candidate cap was noticed; the resulting lead was discarded and not relied upon in that candidate's retained determination, which uses only the first two queries.

Retained package: `research/bootstrap/wikimedia/sl0024-independent-verification/` (`verification_sample.json`, `verification_results.json`, `REPORT.md`, `ARTIFACT-DIGESTS.json` plus their JSON schemas). The retained package passes its own strict offline `--verify` recompute/tamper-check with zero mismatches.

Primary contract: `docs/slices/SLICE-0024-wikimedia-lead-independent-identity-verification-pilot.md`.

This entry records the implementation agent's own measurement and does not constitute independent review or project-owner acceptance. SLICE-0024 is handed off as `REVIEW`; independent review, explicit owner acceptance and closure are required before `DONE`. No SLICE-0025 or later slice is currently `READY` or authorized.

Operational queue: `docs/slices/INDEX.md`.

No later slice starts automatically.
