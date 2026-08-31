# SLICE-0038 — Owning.pro real sales-offer pilot — REPORT

**Date:** 2026-08-31
**Locked vertical:** SLICE-0037 Q10 (`Draft <= 1.60 m`) -> `beneteau-oceanis-30-1` -> `oceanis-30-1-shallow-keel` -> Owning.pro live search -> listing-level assessment.

## 1. What this pilot proves

Running `uv run python scripts/search_oceanis_30_1_sales.py --live` on 2026-08-31:

1. Loads the unchanged, real (`is_fixture=False`) SLICE-0037 Oceanis 30.1 projection and runs the locked `Q10` query through the unchanged `hullq.search.configuration_engine` kernel (no BoatDesign ID is set directly).
2. `Q10` still returns `CONFIRMED_MATCH`, `matching_configuration_ids=(oceanis-30-1-shallow-keel,)`, deep-keel `FALSE`, retractable-keel `UNKNOWN` -- byte-for-byte the accepted SLICE-0037 result. No regression.
3. Queries Owning.pro's public read API (`GET /api/listings?category=sailboats&q=Oceanis%2030.1&limit=20`) with no authentication.
4. Received **10** candidate listings (bounded well under the 20-candidate cap; `pagination.total=10`, `has_more=false` -- this is Owning's complete result set for this exact bounded query, not a truncated page).
5. Independently admits **7** of the 10 as `matched_boat_design_id=beneteau-oceanis-30-1` via a small closed structured-field identity oracle; the remaining **3** are left `matched_boat_design_id=null` (identity genuinely unresolved -- see §4).
6. Every one of the 7 admitted offers is normalized to the `MARKET_LISTING_SCHEMA.v0.1.json` shape and independently assessed for the Q10 draft criterion. **All 7 are `UNKNOWN`**: none of the 10 live candidates carried a structured `draft` attribute or `boat_specs.specs.dimensions` draft value on the access date. This is a genuine, fail-closed result, not a fabricated one -- see §5.

Acceptance criterion "at least one current real Oceanis 30.1 sales offer is returned from Owning and admitted as a confirmed BoatDesign identity" is satisfied by the 7 admitted offers (e.g. the representative offer in §6). The pilot does **not** produce a `TRUE`/`FALSE` listing-level draft match on 2026-08-31's live data; §5 explains why that is the correct fail-closed outcome rather than a defect, and the offline test suite exercises real `TRUE`/`FALSE`/conflict/malformed paths against synthetic listings built in the same schema shape (Required Tests, `tests/unit/test_search_oceanis_30_1_sales.py`).

## 2. Owning.pro source-access disposition (re-checked 2026-08-31)

Full structured record: `owning_source_access_record.json` (validates against `specs/SOURCE_SCHEMA.v0.2.json`).

Summary:

- Base API: `https://api.owning.pro`. `GET /api/listings` (search), `GET /api/listings/{slug}` (detail) are documented public, no-authentication-required read endpoints.
- Owning explicitly documents and encourages automated/agent read access: dedicated "Owning for AI Agents" help article, an MCP server at `mcp.owning.pro`, machine-readable agent discovery at `/.well-known/ai.json`, and `robots.txt` returning `User-agent: * / Allow: /` with an `AI-Discovery` pointer to that file.
- Rate limits: documented and empirically observed as 100 req/min per IP for unauthenticated reads (`X-RateLimit-Limit: 100` observed on this pilot's own live response; two other doc pages state 200/min and 100/min respectively -- a minor internal inconsistency in Owning's own documentation, not something this slice resolves).
- **No formal Terms of Service or Privacy Policy page was discoverable** on `owning.pro` as of 2026-08-31 (`/legal`, `/en/legal`, `/privacy`, `/en/privacy` all 404; footer links surfaced Help/About/Safety/Press/Status/Docs only). The access disposition therefore rests on Owning's own affirmative developer/API/agent documentation and machine-readable discovery surfaces, not a separate legal ToS.
- **Owning is itself an aggregator.** Every one of this pilot's 10 candidates carries a `boat_specs.source.portals` field naming an upstream origin (`yachtworld.com`, `boat24.com`, or `ancasta.com`), and several also included the exact upstream listing URL. Per the binding pre-start addendum, **no upstream portal was fetched**; those names/URLs are retained (where retained at all) purely as provenance metadata. The retained compact sample in this directory keeps only the upstream portal *name* (`boat_specs.source.portals`), not the upstream URL, to further reduce any incentive to follow it.
- Disposition: this bounded, non-recurring, <=15-live-request, single-BoatDesign local pilot read is supported (`research_reference`/`research_lead`: allowed; `production_value`/`automated_ingestion` for this exact pilot: conditional). Recurring polling, bulk bootstrap, full-market mirroring, longitudinal price history, redistribution of source descriptions/images, and any production/canonical persistence beyond this pilot's own retained research artifact are **not** authorized by this disposition.
- 8 distinct Owning documentation/access surfaces were reviewed and cited (within the slice's 8-surface cap): `/en/docs/api-reference`, `/en/blog/developer-api-guide-building-with-owning`, `/en/docs/mcp`, `/api/openapi.json`, `/.well-known/ai.json`, `/robots.txt`, `/en/about`, `/en/help`.

## 3. Live request accounting

Exact live requests against `api.owning.pro` (the slice's 15-request cap covers exactly these; `/api/openapi.json` and `/api/asset-types/boats` are schema/documentation discovery surfaces, listed here for full transparency but not counted as listing queries):

1. `GET /api/openapi.json` -- schema discovery (not a listing query).
2. `GET /api/asset-types/boats` -- asset-type attribute schema discovery (not a listing query; identified `draft`/`brand`/`model`/`length`/`beam` as the structured boat attributes).
3. `GET /api/listings?category=sailboats&q=Oceanis%2030.1&limit=20` -- **live candidate search #1** (10 results, `pagination.total=10`).
4. `GET /api/listings/beneteau-oceanis-30-1-2023` -- **live detail fetch #1** (exploratory; confirmed the search-list response already embeds full `boat_specs`, so no further per-listing detail fetches were needed).
5. `GET /api/listings/beneteau-oceanis-30-1-492PPP` -- **live detail fetch #2** (same confirmation).
6. `GET /api/listings?category=sailboats&q=Oceanis%2030.1&limit=20` -- **live candidate search #2**, the actual `--live` owner-test run recorded for this report (identical 10 results, confirming reproducibility).

**Total live listing/data requests: 4** (well within the 15-request cap); plus 2 schema-discovery requests. A handful of plain `HEAD`-equivalent status probes against `owning.pro` (not `api.owning.pro`) were also made to confirm the public listing page URL pattern (`https://owning.pro/en/listings/{slug}` -> 200); these are page-existence checks, not API listing queries.

## 4. Identity admission (Required Behavior D)

`admit_boat_design_identity()` in `scripts/search_oceanis_30_1_sales.py` normalizes case/accents/punctuation and requires the normalized brand token to equal `beneteau` and the normalized model token (after stripping one leading duplicated brand prefix) to equal `oceanis301` -- exact string equality only, no fuzzy matching, no generic entity resolution.

Real 2026-08-31 result on the 10 live candidates:

- **7 admitted** (`matched_boat_design_id=beneteau-oceanis-30-1`): structured `boat_specs.model` values observed were `"Oceanis 30.1"`, `"Oceanis 30 1"`, `"Beneteau Oceanis 301"` and `"Beneteau OCEANIS 301"` -- all correctly normalize to the same identity despite three different raw spellings/casings/prefixes.
- **3 unresolved** (`matched_boat_design_id=null`): these three candidates are native Owning listings with no `boat_specs` upstream-scrape mirror and no `attributes.model` value at all (only `attributes.brand="beneteau"` was present). Their free-text `title` field does visibly say "OCEANIS 30.1" / "Oceanis 30.1", but this pilot deliberately does **not** parse `title`/description text for identity -- doing so would edge into generic free-text entity resolution, which neither the primary slice nor the addendum authorizes. This is a real, observed fail-closed outcome, not a synthetic test case.

Adversarial near-neighbor coverage (`Oceanis 30`, `Oceanis 31`, `Oceanis 300`, `Oceanis 34.1`, `Oceanis 38.1`, `First 30`, right-model/wrong-brand) is exercised in `tests/unit/test_search_oceanis_30_1_sales.py` and all correctly rejected.

## 5. Listing-level configuration evidence (Required Behavior E + addendum)

None of the 10 live 2026-08-31 candidates carried a structured `attributes.draft` value or a `boat_specs.specs.dimensions.draft_m`/`draft` value. `qualify_listing_draft()` reads only these two structured locations -- never free text -- so every one of the 7 identity-admitted offers correctly qualifies as `ValueQualification.MISSING` -> `TruthState.UNKNOWN` (`ReasonCode.VALUE_MISSING`), even though the confirmed design-level Q10 match (shallow-keel, draft 1.30 m) exists for the *design*. The output makes this separation explicit for every admitted offer:

```text
DESIGN MATCH: Oceanis 30.1 has a Q10-matching factory configuration (oceanis-30-1-shallow-keel)
LISTING CONFIG: independently assessed from this physical listing only
listing_config_truth=UNKNOWN reason=VALUE_MISSING evidence=no structured listing-specific draft attribute is present on this listing
```

No live candidate exposed a zero/negative/placeholder draft value, and no live candidate exposed conflicting listing-specific draft observations (both would require a structured draft field to be present at all, which none were). No model-level fact was in any danger of leaking into listing-level truth here, because `qualify_listing_draft()` never reads the SLICE-0037 design/configuration facts at all -- it only ever inspects the raw Owning listing dict. Owning did expose upstream source attribution (`boat_specs.source.portals`: `yachtworld.com`, `boat24.com`, `ancasta.com`); no upstream source was fetched.

Because real 2026-08-31 data happened not to exercise the `TRUE`/`FALSE`/conflict/malformed paths, `tests/unit/test_search_oceanis_30_1_sales.py` additionally exercises all of them against small synthetic listing dicts built in the identical Owning response shape (unambiguous shallow draft -> `TRUE`; unambiguous deep-side draft -> `FALSE`; `0`/negative/boolean/NaN/Infinity/string/list draft -> `UNKNOWN`; two conflicting observations straddling 1.60 m -> `UNKNOWN`; a placeholder `0` alongside one valid remaining observation -> the valid observation still evaluates normally, `TRUE`/`FALSE` as appropriate; two identical observations -> normal evaluation; free-text words `deep`/`standard`/`shoal`/`shallow`/`lifting`/`swing` in the title -> never consulted, still `UNKNOWN`).

## 6. Representative real offer

```text
Beneteau Oceanis 30.1 2023
Owning URL: https://owning.pro/en/listings/beneteau-oceanis-30-1-2023
Year: 2023 (from boat_specs, not directly on this record's attributes)
Price: 189,950 USD
Location: Seattle, US
matched_boat_design_id: beneteau-oceanis-30-1
LISTING CONFIG: UNKNOWN (reason=VALUE_MISSING) -- no structured listing-specific draft attribute present
Upstream portal attribution (not fetched): yachtworld.com
```

## 7. Counts

- Candidates received: 10 (both live pulls, reproducible).
- Identity-admitted offers: 7.
- Identity-unresolved candidates: 3.
- Listing-level `TRUE`: 0 (real data). `FALSE`: 0 (real data). `UNKNOWN`: 7 (real data).
- Offline/synthetic adversarial coverage (tests only): `TRUE`, `FALSE`, `UNRESOLVED_CONFLICT` (-> `UNKNOWN`), and multiple `MISSING` (-> `UNKNOWN`) variants all independently exercised.

## 8. Seller field decision

All 10 real candidates share one literal seller account (`id=usr_01KX6SQGZYHSBDCC3D6GSBNFV8`, `name="Owning Marketplace"`, `type="agent"`) -- an aggregation-pipeline placeholder, not a genuine identifiable seller. `_map_seller()` therefore drops that specific name to `null` rather than presenting an automated aggregator as if it were the boat's actual seller/broker, and always reports canonical `seller.type="unknown"` because Owning's own vocabulary (`agent`/`human`) has no member that maps onto the canonical schema's `broker`/`dealer`/`private`/`unknown` enum. This is a data-quality judgment call, documented here as an unresolved finding rather than silently guessed.

## 9. Unresolved findings / limitations / scope deviations

- Owning's own documentation is internally inconsistent about the exact unauthenticated rate limit (100 vs 200 req/min across different pages); not material at this pilot's request volume, not resolved here.
- No formal Owning Terms of Service was discoverable; the access disposition rests on affirmative developer/agent documentation only, per §2.
- 3 of 10 real candidates have visibly correct free-text titles but no structured model attribute, and are therefore left identity-unresolved by design; a future slice could revisit whether Owning's Markdown listing representation (`GET /api/listings/{slug}.md`) or another structured surface fills this gap, but that is out of this slice's scope.
- No live candidate happened to carry a structured draft value, so the live owner-test's real result distribution is 100% `UNKNOWN` at the listing-configuration level; `TRUE`/`FALSE`/conflict paths are proven correct only via the offline synthetic tests, not live data, on this access date.
- No scope deviation from the primary slice or the binding addendum was required; no fallback source was used; no upstream portal was fetched.
