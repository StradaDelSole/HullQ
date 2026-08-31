# SLICE-0038 pre-start aggregator assessment — Scanboat + Listings Port

**Date:** 2026-08-31  
**Status:** research note; non-authorizing for automated market access

## Executive conclusion

Scanboat and Listings Port are useful to HullQ in different ways, but neither is added as a live SLICE-0038 source.

- **Scanboat** is a long-running European marketplace and strong broker-feed distribution endpoint. It is strategically interesting as a future partner/feed node, but its published terms expressly prohibit commercial crawling/copying without permission.
- **Listings Port** is a close product/architecture benchmark. It aggregates 20+ marketplaces, canonicalizes sailboat models, normalizes listings, groups duplicates, tracks market history/price reductions and offers saved searches/alerts. No public HullQ-usable API or positive automated-access grant was established in this bounded assessment.

The implementation consequence for SLICE-0038 is stricter fail-closed listing evidence handling: model-level facts must never become physical-listing truth; placeholder/nonphysical draft values must never produce a confirmed match; contradictory listing evidence must become UNKNOWN; and upstream source attribution must remain provenance rather than authorization to fetch the upstream portal.

---

# 1. Scanboat

## Operator and market role

Scanboat is operated by Open Marine SLU, C/ Conde de Altea 64, 4A, 03590 Altea (Alicante), Spain, company registration ES B54535935. Scanboat states that it began as Boat4You.dk in 1997. On 2026-08-31 the public site exposed roughly 16,200 current ads and supported private sellers, professional dealers/brokers, dealer pages, paid promotions and saved-search agents.

## Broker/MLS syndication evidence

Several public broker/MLS products explicitly name Scanboat as an export/distribution target:

- EasyMLS: brokers can import/add inventory and distribute to Scanboat and other portals; EasyMLS also exposes its own API.
- BoatFace: publishes broker inventory to Scanboat, Boat24, TheYachtMarket and other portals with synchronized updates.
- Yacht Broker Pro: lists Scanboat among supported external feeds.
- NautiX/AYB material describes Scanboat in an XML/direct-parsing distribution context.

The likely professional-inventory provenance shape is therefore often:

```text
physical boat
-> broker/dealer canonical listing
-> broker CRM / MLS / XML/API feed
-> Scanboat and other portal copies
```

rather than assuming Scanboat crawls other public marketplaces.

### HullQ consequence

Future coverage should investigate broker/MLS/feed partnerships and Scanboat partnership/API rights before considering marketplace crawling. The upstream broker record may be more authoritative than a syndicated portal copy.

## Public technical surface

Public behavior is consistent with a server-rendered MVC-style application:

- controller-like route shapes such as `/en/BoatMarket/Home/Impressum`;
- structured GET-bound search state;
- server-rendered search/listing pages;
- result pages exposing query execution time in milliseconds;
- SEO detail routes using slug + numeric Scanboat ad ID;
- discrete specs rendered in HTML;
- sitemap partitions for ads, models, dealers and charters across languages, plus update-URL and image sitemaps;
- Google Tag Manager / analytics and advertising integrations.

No private/server-side source code was publicly available and none was sought through bypass or unauthorized access.

## Oceanis 30.1 quality-control case

A current 2019 BENETEAU Oceanis 30.1 listing provided a useful data-quality case.

Scanboat:
`https://www.scanboat.com/en/boat-market/boats/sailingboat-beneteau-oceanis-301-17539803`

Original broker:
`https://www.networkyachtbrokers.com/boats_for_sale/Beneteau_Oceanis_30_1-031346.html/`

The broker page identifies a 2019 Oceanis 30.1 with approximately LOA 9.53 m, beam 2.99 m, draft 1.88 m and `Deep cast keel` wording. The syndicated Scanboat page carries the same broker-origin identity/description but its structured fields were observed with conflicting values, including `depth = 0.00` and different length/beam values.

For the SLICE-0038 query `Draft <= 1.60 m`, passing `0.00` directly to the numeric comparator would manufacture a false TRUE.

Therefore, for this pilot:

- non-positive physical draft is placeholder/nonphysical and must be UNKNOWN, never TRUE;
- structured portal values cannot silently override contradictory listing evidence;
- materially conflicting listing observations must fail closed;
- physical-listing truth must remain separate from model-level truth and portal normalization.

## Rights/access disposition

Scanboat's Impressum states that no website part/content may be reproduced, republished, copied, crawled or distributed for commercial use without permission from Open Marine SLU.

Reviewed controlling surface:
`https://www.scanboat.com/en/BoatMarket/Home/Impressum`

Therefore this assessment does **not** authorize a HullQ Scanboat crawler or SLICE-0038 adapter. Preferred future paths are written permission, official API/feed, partner/deep-link agreement or an authorized broker/feed relationship.

---

# 2. Listings Port

## Why it matters

Listings Port is not merely another marketplace; its current public product is very close to the high-level HullQ thesis.

Observed public claims/features include:

- about 58,945 live listings indexed;
- 20+ marketplace sources;
- roughly 9,459 to 10,238 canonical sailboat models depending on served page/deploy snapshot;
- aggregation from YachtWorld, Boat24, Apollo Duck, Yachtr and other sources;
- canonical model matching;
- normalized prices/specs/locations;
- duplicate grouping;
- technical search using LOA, draft, keel, SA/D, comfort ratio, capsize and other specs;
- natural-language/goal-based research;
- collections/shortlists;
- daily alerts;
- original-source click-through;
- asking-price history, volume trends and price-reduction statistics.

Listings Port explicitly describes itself as a research/aggregation layer above marketplaces rather than a marketplace taking the sale.

This is competitive validation that the problem HullQ addresses is real, but it also means HullQ cannot differentiate merely as `all listings + better filters`.

## Product/data flow

Listings Port says it repeatedly scans multiple unaffiliated marketplaces, standardizes observations and points users back to original sources. Its public flow is broadly:

```text
20+ marketplace observations
-> normalized listing records
-> canonical sailboat-model match
-> duplicate grouping
-> model/market analytics
-> search / collections / alerts
-> original-source click-through
```

Public pages say listings are refreshed hourly; the FAQ says new listings typically enter the index within a day and delisted boats are removed.

## Capabilities directly relevant to HullQ roadmap

Listings Port already exposes product surfaces corresponding to HullQ later-stage questions:

- multi-market search;
- canonical model matching;
- cross-market duplicate grouping;
- saved searches/alerts;
- currency/location normalization;
- 12/18-month asking-price history;
- price trends and reductions;
- geographic market views;
- comparable models.

For the Oceanis 30.1 it currently reports on the order of 80+ live offers and 120+ observations over 12 months. This validates the customer value behind HullQ OQ-005/OQ-006/OQ-017 but does not bypass their source-rights/governance gates.

## Oceanis terminology confirmation

Listings Port's current Oceanis 30.1 buyer-guide wording distinguishes:

- a **standard** 1.88 m cast-iron bulb keel;
- a 1.3 m **shoal-draught** alternative;
- a lifting keel around 0.95–2.33 m.

This independently supports the Project Owner's concern that SLICE-0037's compatibility label `deep-keel` should not be treated as final canonical marine terminology. It is not controlling evidence for changing HullQ data and no terminology change belongs in SLICE-0038.

## Potential HullQ differentiation

Listings Port's public surface combines canonical **model/design specifications** with individual **physical listings**. The Oceanis 30.1 page displays a model-level baseline while narrative text acknowledges multiple keel/draft arrangements and the market page aggregates many physical boats.

Nothing observed publicly demonstrates a strict per-listing configuration-proof boundary equivalent to HullQ's intended invariant:

```text
a design has a shallow configuration
!=
this physical listing is that shallow configuration
```

That can be a material HullQ differentiator: a physical listing should be TRUE/FALSE for a technical criterion only when listing-specific admissible evidence proves the relevant value/configuration.

## Data-quality / deploy signals

Some indexed Listings Port pages expose localization keys such as `components.marketTable.view` and `sailboatModel.seo.titleForSale` instead of translated text. Public model-count figures also vary between page/deploy snapshots. These are not necessarily substantive data errors, but they reinforce that rendered aggregator output is a timestamped observation rather than timeless canonical truth.

## Public technical surface

Observed public architecture includes:

- main SEO/research pages on `www.listingsport.com`;
- an interactive product on `app.listingsport.com`;
- server-rendered/indexable model, market, geography and comparison pages;
- many locale routes;
- Cloudflare DNS/edge for `listingsport.com`;
- extensive search-engine-visible structured model/market content;
- occasional raw localization message keys indicating a shared i18n component/template layer.

No public official Listings Port data API or server-side source repository was discovered during this bounded assessment. Browser-delivered client code was not treated as permission to reverse engineer private endpoints. The site links Terms of Use and Privacy Policy pages, but their current content could not be reliably retrieved through the available research path, so no positive automated-access/commercial-use decision is made.

## Rights/access disposition

Listings Port has at least two rights layers: its own normalization/database/analytics layer and underlying marketplace/broker observations. No explicit permission sufficient for HullQ production ingestion was established here.

Therefore Listings Port is **not** a SLICE-0038 live source. A future partnership/API inquiry may still be worthwhile.

---

# 3. Strategic comparison

| Dimension | Scanboat | Listings Port | HullQ implication |
|---|---|---|---|
| Role | marketplace + private/dealer ads + feed endpoint | aggregation/research layer | HullQ resembles Listings Port more closely |
| Inventory source | direct sellers + strong broker/MLS-feed evidence | scans/aggregates 20+ marketplaces | preserve provenance chain |
| Canonical model layer | model pages exist | strong canonical model layer | model identity is necessary but not listing configuration truth |
| Dedup | not observed as core promise | explicitly groups duplicates | OQ-005 remains important |
| Price history | not core observed surface | explicit trends/reductions | validates OQ-017 value |
| Alerts | search agent | daily cross-source alerts | validates OQ-006 value |
| Technical search | marketplace filters | technical/ratio search | direct competitor/benchmark |
| Listing-specific configuration proof | not observed | not established publicly | possible HullQ differentiation |
| Automated access for HullQ | commercial crawling expressly restricted | not positively cleared | neither is a SLICE-0038 source |

## Strategic takeaway

Listings Port means HullQ should not position merely as `all sailboat listings plus better filters`. A stronger defensible direction is:

- evidence-backed field truth;
- explicit UNKNOWN rather than guessed values;
- configuration-sensitive design search;
- physical-listing configuration proof rather than model-level inheritance;
- auditable provenance/source applicability;
- fail-closed conflict handling;
- stronger marine technical semantics.

At the same time, Listings Port validates that aggregation, dedup, alerts, market history and price intelligence are worthwhile customer-facing features after source-access and architecture gates are satisfied.

---

# 4. Binding consequences proposed for SLICE-0038

The live source remains **Owning.pro only**. Neither Scanboat nor Listings Port is added as an implementation source.

The pilot should enforce:

1. For this Oceanis 30.1 use case, numeric listing draft `<= 0` is nonphysical/placeholder and yields `UNKNOWN`, never TRUE.
2. Design/model-level draft, keel or configuration facts never authorize a physical listing's TRUE/FALSE result.
3. Materially conflicting listing-specific draft observations yield `UNKNOWN` / unresolved conflict unless independently resolved.
4. Listing-level numeric evidence must be explicitly attributable to the concrete listing observation used for classification.
5. If Owning supplies upstream platform/reference metadata, retain only discrete provenance needed for audit; do not fetch the upstream portal in SLICE-0038.
6. Words such as `standard`, `deep`, `short`, `shoal`, `shallow`, `lifting` are not an automatic configuration inference table.
7. Dedup remains out of scope; duplicate signals may be reported but not resolved into a production dedup system.

Focused adversarial additions should cover:

- draft `0` -> UNKNOWN;
- negative draft -> UNKNOWN;
- model/design-level draft only -> UNKNOWN at listing level;
- conflicting listing-specific numeric drafts on opposite sides of 1.60 m -> UNKNOWN;
- multiple identical unambiguous listing-specific observations may remain eligible for normal numeric evaluation;
- upstream source name alone does not authorize direct upstream fetch or stronger truth.

---

# Sources reviewed

## Scanboat
- `https://www.scanboat.com/`
- `https://www.scanboat.com/en/boat-market/boats`
- `https://www.scanboat.com/en/BoatMarket/Home/Impressum`
- `https://www.scanboat.com/sitemap.xml`
- current Scanboat Oceanis 30.1 listing pages
- `https://www.easymls.com/en`
- `https://boatface.pro/`
- `https://yachtbrokerpro.com/dashboard/`
- NautiX/AYB public product material

## Listings Port
- `https://www.listingsport.com/`
- `https://www.listingsport.com/how-it-works`
- `https://www.listingsport.com/faq`
- `https://www.listingsport.com/compare`
- `https://www.listingsport.com/sailboats/beneteau/oceanis-30-1/for-sale`
- representative indexed model/market pages
- public DNS/edge records for `listingsport.com`

This note intentionally does not retain third-party images, full listing descriptions or personal contact details.