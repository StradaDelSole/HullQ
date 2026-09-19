# HullQ — Anonymous Factual Shortlist Compare Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0059 — Anonymous Factual Shortlist Compare  
**Controlling product direction:** `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`  
**Shortlist foundation:** `specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md`  
**Public listing truth foundation:** accepted SLICE-0049/0050/0052  
**Public UX baseline:** `docs/PRODUCT_UX_PRINCIPLES.md`

## 1. Purpose

This contract adds one anonymous buyer decision-tool capability:

> Compare the buyer's current browser-local Shortlist factually, side-by-side, using current accepted public listing truth.

It does not create a recommendation engine, a second shortlist, a persisted compare set or account state.

## 2. Compare-set semantics

The compare set in v0.1 is exactly the current local Shortlist membership.

```text
compare set = shortlistStore listing_ids
```

The existing buyer-authored Shortlist order is preserved.

No second browser key/object is introduced for compare selection.

No listing is added to or removed from the Shortlist by opening/using Compare.

A future explicit subset-selection/reorder capability is deferred.

## 3. Minimum-state behavior

If the local Shortlist contains:

- zero saved IDs: render a factual empty state;
- one saved ID: render a bounded "save at least one more listing to compare" state;
- two or more saved IDs: resolve and render the comparison set.

The compare route may exist regardless of current local membership.

## 4. Current truth only

Every saved ID MUST be re-resolved through the accepted current public listing-read boundary, using the existing shortlist resolution transport or an equivalent smaller reuse of the same truth boundary.

Authoritative semantics remain:

```text
NativeListingId
→ accepted current public read eligibility
→ PublicListingReadModel
```

The browser MUST NOT persist or treat previously resolved offer/claim/freshness values as compare truth.

Astro/TypeScript MUST NOT infer lifecycle, freshness or publication eligibility.

## 5. Factual comparison fields

v0.1 may compare only fields already present in the accepted current public listing projection.

The core comparison matrix MUST include where available:

- listing identity / current navigable listing;
- marketed brand claim;
- model designation claim;
- build year claim;
- LOA claim;
- draft claim;
- keel configuration claim;
- rudder configuration claim;
- asking price / POA with original currency;
- location country and bounded location-region claim;
- freshness status and last-confirmed disclosure.

Additional existing public projection fields may be displayed only if they remain factual/current and do not make the matrix unreadably broad.

No new technical yacht fact is invented by this slice.

## 6. Claim-scope and UNKNOWN semantics

Concrete PhysicalBoat claim semantics remain authoritative.

Never replace a missing/UNKNOWN concrete-yacht field with BoatDesign baseline truth merely to fill a comparison cell.

The UI must preserve at least these distinctions where present:

```text
VALUE_ASSERTION
UNKNOWN
not supplied / omitted
unavailable listing
service error
```

Presentation wording may be localized and concise, but those truth states must not collapse into a guessed value.

## 7. Price semantics

Price comparison is factual only.

The UI may display:

- exact asking amount;
- exact stored currency;
- POA.

v0.1 MUST NOT:

- convert currencies;
- normalize prices;
- sort by price desirability;
- label cheapest/best value;
- infer negotiation room;
- compute price-per-unit or market-value scores.

Future currency/market-comparison methodology requires a separate accepted decision.

## 8. Difference / neutrality semantics

Compare may align differing values visually.

It MUST NOT, absent a separate explicit buyer requirement:

- label one value better/worse;
- declare a winner;
- compute overall fit/match percentages;
- apply hidden weighting;
- auto-sort by inferred desirability;
- recommend which boat to choose.

A factual difference is not an evaluative conclusion.

## 9. Available / unavailable / service-error behavior

Per saved ID:

- accepted current public read resolves → available factual column/card;
- accepted non-public/non-current boundary → neutral unavailable state;
- infrastructure/transport failure → distinct service-error state.

Unavailable MUST NOT disclose whether the cause is missing, DRAFT, WITHDRAWN, incomplete, STALE, freshness UNKNOWN or another internal cause.

Unavailable saved IDs remain members of the Shortlist and remain represented in the compare set until explicit buyer removal occurs elsewhere.

A service failure MUST NOT be represented as ordinary unavailable or silently omitted.

One unavailable/service-error item MUST NOT suppress other successfully resolved items.

## 10. Public web / SEO boundary

Canonical localized compare surface:

```text
/{locale}/shortlist/compare
```

for:

```text
en
de
fr
pt
es
```

The page is personalized browser-local state and MUST be:

- `noindex`;
- `private, no-store`;
- absent from indexable sitemap/hreflang discovery;
- free of saved listing IDs in URL/query/canonical metadata;
- non-shareable by token in this slice.

The existing `/{locale}/shortlist` surface SHOULD expose a clear factual Compare action/link.

## 11. Client/presentation boundary

Client-side code may:

- read the accepted local shortlist IDs;
- request current resolution through the accepted shortlist resolver;
- render the comparison matrix/cards;
- localize labels;
- provide navigation back to shortlist/listing pages.

Client-side code MUST NOT:

- create listing truth;
- mutate shortlist membership automatically;
- evaluate Search or BuyerRequirements;
- generate a recommendation/score;
- interpret seller payment/revenue as a comparison factor;
- inject untrusted raw HTML.

Stored IDs and returned text MUST use safe DOM/text rendering.

## 12. Whole-Shortlist v0.1 boundary

v0.1 intentionally compares the whole current Shortlist rather than adding another compare-selection state.

This is a scope reduction, not a permanent product rule.

If real usage demonstrates a need to compare only a subset, pin columns, reorder independently or persist multiple compare sets, that requires later explicit product/readiness work.

## 13. International presentation

The Compare surface follows `docs/PRODUCT_UX_PRINCIPLES.md` and existing i18n rules.

It must not assume:

- one currency;
- U.S.-only units/date conventions;
- desktop-only width.

Current canonical stored values remain unchanged. Presentation may use existing accepted helpers; no new unit/currency conversion methodology is introduced by this slice.

## 14. No persistence / telemetry side effects

SLICE-0059 creates no:

- database Compare row;
- buyer profile;
- account linkage;
- compare-history record;
- anonymous durable intent object;
- behavioral-preference model;
- shortlist analytics/telemetry.

Resolver requests may necessarily carry saved IDs exactly as 0058 already permits, but they do not become durable buyer-interest state.

## 15. Tests and retained proof

At minimum cover:

### Compare-set behavior

- zero saved IDs;
- one saved ID;
- two or more IDs;
- buyer-authored order preserved;
- Compare does not mutate Shortlist membership;
- no second compare-selection persistence object appears.

### Current truth / states

- current available listing values come from accepted resolver/public projection;
- current offer/claim change is reflected on later Compare resolution without changing stored shortlist data;
- missing/withdrawn/stale/non-public causes remain indistinguishable neutral unavailable;
- unavailable remains saved;
- service failure is distinct from unavailable;
- one failed/unavailable item does not hide other available items.

### Truth-safe presentation

- concrete claim VALUE_ASSERTION shown factually;
- explicit UNKNOWN remains UNKNOWN;
- omitted/not-supplied remains distinct;
- no BoatDesign fallback fills concrete-yacht gaps;
- price/currency displayed without conversion or value judgment;
- no winner/best-fit/recommended/score language;
- no unsafe HTML injection.

### Web / localization

- all five locale compare routes exist;
- compare page is `noindex` and `private, no-store`;
- no IDs appear in route/query/canonical metadata;
- shortlist exposes Compare navigation;
- available entries link to current public listing pages;
- responsive rendering remains usable for multiple entries.

### Retained vertical proof

A deterministic built-web proof must demonstrate at minimum:

1. at least two saved local `NativeListingId` values;
2. the Compare surface derives its set from the existing shortlist store;
3. current public data is resolved, not loaded from stored listing truth;
4. concrete claim/offer fields render for available items;
5. UNKNOWN/not-supplied semantics remain explicit;
6. an unavailable saved ID remains neutral and retained;
7. a resolver/API outage is distinct from unavailable;
8. no shortlist mutation occurs from Compare;
9. no account/database Compare persistence appears;
10. finish with:

```text
ANONYMOUS FACTUAL SHORTLIST COMPARE RESULT -> PASS
```

CI must execute the retained proof in the normal appropriate web/PostgreSQL integration path.

## 16. Explicitly deferred

Not part of v0.1 / SLICE-0059:

- account/database Shortlist;
- cross-device continuity;
- anonymous-to-account migration;
- named/multiple Shortlists;
- persisted compare-selection subsets;
- compare share links/tokens;
- private notes;
- BuyerRequirements overlay;
- Search-fit scoring/ranking;
- currency conversion;
- derived market-value/performance metrics;
- monitoring/alerts;
- seller/broker contact/leads;
- telemetry-based preference inference;
- third Search criterion;
- owner-direct publication/admission;
- Broker Workspace expansion.

## 17. Acceptance summary

Accepted v0.1 boundary:

```text
current local Shortlist
→ current public re-resolution
→ factual side-by-side current offer + concrete-yacht claims
→ UNKNOWN/not-supplied/unavailable/service-error preserved
→ no winner/score/recommendation
→ no new persistence
```
