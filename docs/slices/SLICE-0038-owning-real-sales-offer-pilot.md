# SLICE-0038 — Owning.pro real sales-offer pilot

**ID:** SLICE-0038  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** P0 Market/Search vertical — first real sales offers from a confirmed real-design Search result  
**Depends on:** SLICE-0037 owner-accepted / DONE; OQ-013 remains RESEARCHING globally  
**Blocks:** first end-to-end HullQ proof from technical Search result to current sales offers and the evidence-based decision on the next market/API architecture slice

## Product objective

Prove, locally and fail-closed, the first real HullQ product loop:

```text
technical Search input
→ matching real BoatDesign / resolved configuration
→ one explicitly permitted market-data API
→ current real sales listings
→ BoatDesign identity match
→ listing-level configuration assessment
→ visible sales-offer output
```

The locked vertical for this slice is the already accepted SLICE-0037 Oceanis 30.1 Q10 proof:

```text
Draft <= 1.60 m
→ beneteau-oceanis-30-1
→ matching design configuration: oceanis-30-1-shallow-keel
```

SLICE-0038 must not hardcode that conclusion instead of invoking the accepted Search path. The owner-test command must load the real SLICE-0037 projection, run the existing Q10 query through the unchanged configuration-aware Search kernel, obtain the matching BoatDesign/configuration result, and only then search the market source for current offers.

## Locked first market source

The only market source authorized for this pilot is:

**Owning.pro public read API** — `https://api.owning.pro`

Current readiness evidence indicates that Owning explicitly documents:

- public REST read endpoints for listings;
- no authentication required for public reads;
- JSON and Markdown machine-readable listing representations;
- OpenAPI / machine schema / agent discovery;
- public read rate limiting;
- developer/agent/integration use, including search/comparison-style workflows.

Relevant current surfaces to re-check during implementation include at least:

- `https://owning.pro/en/docs/api-reference`
- `https://owning.pro/en/blog/developer-api-guide-building-with-owning`
- `https://owning.pro/en/docs/mcp`
- the current Owning help/policy/terms surfaces discoverable from the site;
- `https://api.owning.pro/api/openapi.json` or equivalent current schema/discovery surface.

This readiness decision authorizes only a bounded **local pilot** after the implementation agent re-checks the current access terms and documents the disposition. It does not globally resolve OQ-013 for all market sources and does not authorize recurring/bulk market ingestion or longitudinal storage.

### No fallback scraping

Do not scrape or automate YachtWorld, Boat24, boats.com, Yachtall, TheYachtMarket or another marketplace in this slice.

If Owning is unavailable, its current access terms no longer support this bounded API use, its API cannot be technically consumed as documented, or it returns no current Oceanis 30.1 offer after the bounded query described below, report `BLOCKED`.

Do not start a source hunt and do not silently fall back to HTML scraping.

Any upstream portal/source attribution returned by Owning is metadata reported by Owning. SLICE-0038 must not independently fetch the attributed upstream portal merely to enrich the listing.

## Hard time/scope caps

This slice is intentionally smaller than SLICE-0037.

- One BoatDesign only: BENETEAU Oceanis 30.1.
- One Search input only: locked Q10 (`Draft <= 1.60 m`).
- One market source only: Owning.pro public read API.
- Maximum 15 live Owning API requests for the complete implementation/owner-test investigation, excluding static developer/terms documentation retrieval.
- Maximum 8 distinct Owning access/rights/documentation surfaces retained or cited for the source-access decision.
- At most 20 returned candidate listings need to be considered.
- No source fallback campaign.

If those bounds are insufficient to establish the required proof, stop and report `BLOCKED` or the exact unresolved limitation.

## Required source-access disposition

Before using live listing data as an acceptance proof, retain a compact source-access record for Owning covering at least:

- source/operator identity if discoverable;
- API base URL and endpoint(s) used;
- access date/time;
- authentication requirement;
- documented public-read status;
- rate-limit status;
- terms/policy URLs reviewed, or explicit bounded negative finding if no separate formal terms surface is discoverable;
- permission/disposition for this one non-recurring local read/search pilot;
- caching/storage/display disposition;
- explicit statement that recurring polling, bulk bootstrap, full-market mirroring, longitudinal price history and redistribution of source descriptions/images are **not** authorized by this slice unless an explicit source term independently establishes them.

The access record must distinguish Owning's own API-use authorization from any claims Owning makes about its upstream inventory sources. Do not treat an upstream source name returned by Owning as direct HullQ rights clearance against that upstream platform.

## Existing contracts to preserve

Use, do not silently redefine:

- `architecture/MARKET_ADAPTER_CONTRACT.md`
- `specs/MARKET_LISTING_SCHEMA.v0.1.json`
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`
- `specs/SOURCE_SCHEMA.v0.2.json`
- accepted SLICE-0037 real Oceanis projection and owner-test boundary
- existing `hullq.search` Q10 semantics and `TruthState` / qualified-value behavior.

`MARKET_ADAPTER_CONTRACT.md` and `MARKET_LISTING_SCHEMA.v0.1.json` remain DRAFT. This slice is an evidence-generating local pilot and must not silently promote them to accepted production contracts.

## Required behavior A — run the real design Search first

The owner-test must begin by invoking the accepted SLICE-0037 path, not by setting a BoatDesign ID directly.

Required proof before any market request:

- Q10 is the unchanged locked query;
- real Oceanis projection is `is_fixture=False`;
- Search result is `CONFIRMED_MATCH`;
- exact matching design configuration remains `oceanis-30-1-shallow-keel`;
- deep fixed-draft configuration remains FALSE for Q10;
- hydraulic/retractable configuration remains UNKNOWN for Q10.

If SLICE-0037 no longer produces this accepted result on the implementation HEAD, stop and report the regression rather than implementing around it.

## Required behavior B — live Owning query

Use Owning's documented public read/search API to query current listings for the confirmed BoatDesign identity.

Prefer the structured API search surface, for example the documented full-text listing query form, rather than downloading a full catalog.

The market query should be narrowly targeted to BENETEAU Oceanis 30.1 and bounded to at most 20 returned candidates.

At least one current real offer must be returned and retained in the live owner-test result for the slice to complete successfully.

Zero current offers is not a software defect, but it means this specific product proof has not been demonstrated; report `BLOCKED` rather than manufacturing a listing fixture and calling the slice complete.

## Required behavior C — canonical listing normalization

Normalize each admitted candidate into the existing `MARKET_LISTING_SCHEMA.v0.1.json` shape where the source supplies the necessary data.

At minimum preserve:

- platform = Owning;
- Owning listing ID / slug if supplied;
- Owning listing URL;
- title;
- observed_at;
- raw manufacturer/model/variant identity;
- year;
- asking price amount/currency;
- location text/country where supplied;
- seller name/type only if present and appropriate to retain;
- `matched_boat_design_id` only after independent identity admission.

Do not retain source images, full long descriptions, personal contact details or unnecessary expressive listing text merely because the API returns them.

A compact retained observation/sample may contain only the discrete fields needed for deterministic offline tests and audit.

## Required behavior D — BoatDesign identity must fail closed

A market listing must not receive:

```text
matched_boat_design_id = beneteau-oceanis-30-1
```

merely because Owning's search query returned it.

Independently verify listing identity from structured listing data where available.

For this pilot a small closed normalizer/identity oracle is preferred over fuzzy matching. It may normalize case, accents and punctuation for exact identity comparison, but must distinguish Oceanis 30.1 from Oceanis 30, Oceanis 31, Oceanis 300, Oceanis 34.1, etc.

No generic fuzzy entity-resolution subsystem is authorized.

If listing identity is ambiguous, leave `matched_boat_design_id=null` / classify as unresolved and do not use the listing as an Oceanis offer proof.

Add adversarial identity tests for near-neighbor model strings.

## Required behavior E — listing-level configuration assessment

The design-level statement:

```text
Oceanis 30.1 has a Q10-matching shallow-draft configuration
```

must never be promoted into:

```text
this particular Oceanis 30.1 listing satisfies Q10
```

without listing-level evidence.

For each confirmed BoatDesign listing, produce a pilot-only three-valued configuration assessment using existing `TruthState` semantics:

- `TRUE` — listing-specific admissible evidence proves the offered boat satisfies the locked Q10 draft criterion;
- `FALSE` — listing-specific admissible evidence proves it contradicts the locked Q10 draft criterion;
- `UNKNOWN` — listing identifies the BoatDesign but does not establish the offered boat's relevant draft/configuration precisely enough.

Presentation may label these as:

- `CONFIRMED_MATCH`
- `CONFIRMED_NON_MATCH`
- `CONFIGURATION_UNKNOWN`

but do not introduce a new production-wide market truth enum solely for this pilot.

Where a single unambiguous listing-specific numeric draft is admissible, reuse the existing `NumericLeafCriterion` / `evaluate_numeric_leaf` machinery with a qualified listing observation rather than duplicating threshold comparison logic.

If the source gives an adjustable/swing/lifting-keel range, a shallow endpoint, contradictory draft values, or otherwise unclear semantics, fail closed to `UNKNOWN` unless the source evidence establishes exactly what value the offered physical boat has for the criterion being evaluated.

### Terminology guardrail from Project Owner

Do not treat the SLICE-0037 identifier/wording `deep-keel` as final canonical marine terminology.

The Project Owner has flagged that the practical factory terminology may instead be a standard keel plus a shorter/shallow variant. That data-model terminology will be checked in a later data-quality pass.

For SLICE-0038:

- preserve existing SLICE-0037 configuration IDs unchanged for compatibility;
- do not rename the accepted 0037 data;
- do not use the words `deep`, `standard`, `short`, `shallow` as an automatic synonym/inference table for listing classification;
- prefer unambiguous listing-specific numeric draft evidence for TRUE/FALSE;
- otherwise return `UNKNOWN`.

This note is a deferred data-quality concern, not permission to rewrite SLICE-0037.

## Required behavior F — provenance/explainability

Every displayed listing assessment must identify:

- Owning listing ID/URL;
- observed timestamp;
- admitted BoatDesign identity basis;
- listing-level draft/configuration evidence actually used, if any;
- resulting `TruthState`;
- reason when `UNKNOWN`;
- the confirmed design configuration(s) produced by the original design Search, separately from the offered boat's own listing-level evidence.

The output must make this distinction visible:

```text
DESIGN MATCH: Oceanis 30.1 has a matching factory configuration
LISTING CONFIG: unknown unless this particular offer establishes it
```

## Minimal owner-test surface

Provide one deterministic local command, normally:

```text
uv run python scripts/search_oceanis_30_1_sales.py --live
```

It must visibly print:

1. original technical Search input / Q10;
2. design Search result and exact matching configuration ID;
3. live market source and access mode;
4. number of Owning candidate listings received;
5. normalized current Oceanis 30.1 offers;
6. for each admitted listing: title/year/price/location/URL plus listing-level `TRUE`/`FALSE`/`UNKNOWN` configuration assessment and evidence/reason;
7. summary counts.

A separate offline mode/sample may be used for deterministic CI tests. CI must not depend on live network availability.

## Required tests

Focused tests must cover at least:

- SLICE-0037 Q10 path is actually invoked and still yields the accepted real design/configuration result;
- live-source parsing/normalization logic using a compact retained Owning sample;
- canonical listing JSON validates against `MARKET_LISTING_SCHEMA.v0.1.json`;
- exact BoatDesign identity positive controls;
- near-neighbor model false positives rejected;
- search-return membership alone cannot self-authorize `matched_boat_design_id`;
- listing with no configuration/draft evidence -> `UNKNOWN`;
- unambiguous listing draft <= 1.60 -> `TRUE`;
- unambiguous listing draft > 1.60 -> `FALSE`;
- adjustable/range/ambiguous draft semantics -> `UNKNOWN`;
- malformed/non-finite/boolean numeric values fail closed;
- source description/image/contact data is not required to materialize the canonical retained sample;
- zero live results causes a clear non-success/BLOCKED owner-test outcome rather than a fabricated match.

## Deliverables

Expected bounded deliverables:

1. `research/market/sl0038-owning-oceanis-30-1/` with compact source-access record, REPORT and minimal retained discrete listing sample used for offline tests;
2. `scripts/search_oceanis_30_1_sales.py`;
3. focused tests, normally `tests/unit/test_search_oceanis_30_1_sales.py`;
4. only the smallest helper code needed for the pilot. Prefer script/test-local code; production `src/hullq/market/**` is not required and must not be introduced merely to make the pilot look architectural;
5. this slice document moved to REVIEW on successful handoff.

## Explicitly out of scope

- any market source other than Owning.pro;
- direct YachtWorld/Boat24/boats.com/Yachtall/TheYachtMarket crawling or scraping;
- multi-source orchestration;
- cross-platform physical-listing deduplication / OQ-005;
- recurring polling, monitoring or alerts / OQ-006;
- historical price observation/storage / OQ-017;
- PostgreSQL market persistence;
- FastAPI/public HTTP API;
- frontend/search UI/SEO;
- user accounts/auth;
- geography/radius search beyond whatever location facts the listing already provides;
- generic fuzzy BoatDesign entity resolution;
- generic configuration extraction NLP;
- new marine taxonomy/schema fields;
- correction/renaming of the Oceanis 30.1 keel terminology flagged by the Project Owner;
- a generic production market-adapter framework;
- resolving OQ-013 for any source other than the bounded Owning pilot disposition.

## Acceptance criteria

- [ ] Only Owning.pro was used as the live market source.
- [ ] Current Owning API/access documentation was re-checked and the bounded source-access disposition is retained.
- [ ] No upstream marketplace was scraped/fetched as an enrichment source.
- [ ] Live API request count stayed within the 15-request cap.
- [ ] SLICE-0037 Q10 real Search is invoked unchanged before market lookup.
- [ ] Q10 still returns the accepted Oceanis 30.1 design/configuration result.
- [ ] At least one current real Oceanis 30.1 sales offer is returned from Owning and admitted as a confirmed BoatDesign identity; otherwise slice is BLOCKED.
- [ ] Every admitted listing is normalized to the existing market-listing contract or an explicitly documented compatible bounded representation.
- [ ] `matched_boat_design_id` is independently authorized; market search-return membership is insufficient.
- [ ] Every admitted offer carries a listing-level `TRUE`/`FALSE`/`UNKNOWN` configuration assessment with evidence/reason.
- [ ] Design-level configuration existence is never used as listing-level configuration truth.
- [ ] Numeric listing evidence reuses existing Search leaf comparison semantics where applicable.
- [ ] Ambiguous/adjustable/missing listing configuration evidence remains UNKNOWN.
- [ ] Existing 0037 `deep-keel` identifier is not renamed or treated as authoritative final terminology.
- [ ] No known false confirmed listing match/non-match exists.
- [ ] Offline tests are deterministic and do not require network access.
- [ ] Live owner-test visibly prints current sales offers and their assessment.
- [ ] Repository validation, ruff, mypy and full tests pass; coverage remains >=90%.
- [ ] Existing Search production code/semantics remain unchanged unless an independently demonstrated bug blocks the slice, in which case STOP and report before widening scope.
- [ ] Exact-head CI and Manufacturer artifact reproducibility are green before review acceptance.

## Completion report

Leave the slice in `REVIEW` or `BLOCKED`; never mark DONE or merge.

Report at minimum:

- exact final HEAD;
- changed files;
- Owning source-access disposition and reviewed URLs;
- exact live API request count;
- exact live endpoint/query used;
- live candidate count and admitted Oceanis listing count;
- retained sample fields and why no expressive/personal excess data was stored;
- identity admission rule;
- listing-level configuration evidence rule;
- count/list of TRUE, FALSE and UNKNOWN offers;
- at least one representative real offer with Owning URL, year, price/location and assessment;
- proof that Q10 was run through existing Search first and its exact matching configuration ID;
- local validation and coverage;
- exact-head CI and Manufacturer reproducibility;
- unresolved findings / source-access limitations / scope deviations.

After the final handoff, STOP.
