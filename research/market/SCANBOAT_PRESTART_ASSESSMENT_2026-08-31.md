# Scanboat pre-start assessment — 2026-08-31

**Status:** research note; non-authorizing for automated market access

## Purpose

This note records the Project Owner-requested pre-start assessment of Scanboat before SLICE-0038. It is not a source-access authorization and does not add Scanboat as a live SLICE-0038 source.

## Operator and marketplace position

Scanboat is operated by Open Marine SLU, C/ Conde de Altea 64, 4A, 03590 Altea (Alicante), Spain, company registration ES B54535935. Scanboat states that it originated as Boat4You.dk in 1997 and operates as a European boat marketplace for private and professional sellers.

Current observed inventory on 2026-08-31 was about 16,200 advertisements. The public product exposes direct private listings, professional dealer/broker listings, saved searches/search agents, dealer inventory pages, seller-website links and multilingual listing pages.

## Strong evidence of broker/MLS feed syndication

The useful architectural finding is that Scanboat appears to participate in the marine broker listing-syndication ecosystem rather than merely scraping other marketplaces.

Public third-party broker/MLS products observed during this assessment explicitly list Scanboat as a distribution/export destination:

- NautiX / AYB describes Scanboat as `XML Direct Parsing` from NautiX XML files.
- BoatFace describes automated publishing to Scanboat and other portals, with synchronized updates.
- Yacht Broker Pro lists Scanboat among supported external feeds.
- EasyMLS lists Scanboat among the portals to which a broker can distribute a listing.

This is consistent with direct observation of the same broker-owned physical listing appearing on the broker's own website and on several portals. Therefore the likely provenance shape for much professional inventory is:

```text
broker/dealer canonical listing
-> broker CRM / MLS / XML or API feed
-> Scanboat and other portals
```

rather than:

```text
other public marketplace page
-> Scanboat crawler
```

This distinction matters for HullQ. A future legally cleaner coverage strategy may be to partner with broker/MLS/feed systems or with Scanboat itself instead of individually scraping public marketplaces.

## Public technical surface

Observed public URL and rendering behavior is strongly consistent with a server-rendered MVC application:

- routes such as `/en/BoatMarket/Home/Impressum` and `/de/Account/Register`;
- GET-bound search fields such as `SearchCriteria.BoatModelText`, `SearchCriteria.BoatTypeID`, `SearchCriteria.CountryIds`, `SearchCriteria.ExtendedSearch`, `SearchCriteria.Length`, `SearchCriteria.LengthWidthUnitID`, `SearchCriteria.Price`, `SearchCriteria.Searched`, `SearchCriteria.SimilarSearch`, `SearchCriteria.Year`, `DisplayCurrency`, `SortBy` and `page`;
- server-rendered result pages expose their own query execution time in milliseconds;
- listing detail URLs use SEO slugs plus a Scanboat numeric listing identifier, e.g. `/sailingboat-beneteau-oceanis-301-17539803`;
- detail pages render without requiring a client-side application and expose discrete specifications in HTML;
- the sitemap index partitions `ads`, `models`, `dealers` and `charters` by language and also references update-URL and image sitemaps.

Third-party technology detectors have reported Microsoft-IIS/10.0 and Cloudflare-related hosting/edge signals. These are secondary observations, not controlling evidence of the private implementation. No server-side source code is publicly available and none was sought through bypass or unauthorized access.

## Listing data observed

Scanboat detail pages can expose a relatively rich market record:

- Scanboat listing ID / SEO URL;
- original and converted asking price/currency;
- year;
- country / location;
- dealer/broker name, address and phone;
- seller website link;
- multilingual description;
- hull/material;
- length;
- beam;
- displacement;
- depth/draft;
- engine make/model;
- power;
- engine count;
- engine placement;
- fuel;
- engine hours and speed where supplied;
- dealer's other listings.

The public sitemaps make ads/models/dealers highly discoverable for search engines, but sitemap discoverability is not permission for HullQ commercial crawling.

## Oceanis 30.1 case study and critical quality finding

Scanboat currently exposes multiple BENETEAU Oceanis 30.1 listings. One exact 2019 Chichester listing is particularly instructive:

Scanboat:
`https://www.scanboat.com/en/boat-market/boats/sailingboat-beneteau-oceanis-301-17539803`

Original broker:
`https://www.networkyachtbrokers.com/boats_for_sale/Beneteau_Oceanis_30_1-031346.html/`

The broker's own listing states:

- manufacturer/model: Beneteau Oceanis 30.1;
- year: 2019;
- LOA: 9.53 m;
- beam: 2.99 m;
- draft: 1.88 m;
- `Deep cast keel`;
- broker reference: `031346`.

Scanboat reproduces the same broker description and the `Deep Cast Keel` wording, but its structured specifications for that page currently show:

- length: 9.61;
- beam: 2.79;
- depth: 0.00.

The same physical broker listing is also discoverable on TheYachtMarket and other portal surfaces.

This is direct evidence of two market problems HullQ must handle:

1. cross-portal duplicates can represent one physical boat and one broker-owned listing;
2. syndicated structured fields can be missing, placeholder-valued or inconsistent with the underlying broker record and even with text carried on the same portal page.

A particularly dangerous example for HullQ is `draft/depth = 0.00`. Feeding that number directly into `Draft <= 1.60 m` would manufacture a false `TRUE`. A non-positive physical draft must therefore never authorize a confirmed listing-level match.

## Rights / access disposition

Scanboat's own Impressum states that no website part/content may be reproduced, republished, copied, crawled or distributed for commercial use without permission from Open Marine SLU.

Observed controlling surface:
`https://www.scanboat.com/en/BoatMarket/Home/Impressum`

The site also tells professional dealers/brokers to contact Scanboat to arrange advertising. The sitemap and normal browser accessibility do not override the explicit commercial-use restriction.

Therefore this assessment does **not** authorize HullQ to crawl Scanboat for SLICE-0038 or production use.

No Scanboat scraping/crawling adapter should be implemented without a later positive source-access decision, preferably one of:

- direct written permission from Open Marine SLU;
- an official API;
- a partner/deep-link arrangement;
- an authorized dealer/feed relationship whose terms expressly allow HullQ's use.

## Consequences for SLICE-0038

Scanboat remains outside SLICE-0038's live-source set. Owning.pro remains the one locked live pilot source.

However this research sharpens the pilot's fail-closed listing logic:

- a draft value `<= 0` is nonphysical/placeholder for this sailboat use case and MUST resolve to listing-level `UNKNOWN`, never `TRUE`;
- source values must be sanity-gated before reuse of the accepted numeric leaf comparator;
- if multiple listing-level observations conflict materially, the assessment MUST be `UNKNOWN` unless one independently controlling observation resolves the conflict;
- aggregator/search-return membership must never establish BoatDesign identity or configuration truth;
- upstream/source attribution should be preserved when Owning supplies it, but SLICE-0038 must not fetch that upstream portal merely to enrich the listing.

## Strategic follow-up after the pilot

Scanboat is strategically interesting, but mainly as a **potential partner/feed node**, not as a crawl target.

Recommended OQ-013 follow-up after the current one-source pilot:

1. contact Open Marine SLU / Scanboat and ask specifically about API, XML/feed, partner/deep-link and commercial search-display rights;
2. investigate broker/MLS distribution systems that already feed Scanboat (NautiX, EasyMLS, BoatFace, Yacht Broker Pro and comparable systems) as possible upstream acquisition channels;
3. define provenance as `physical boat -> broker listing -> feed/portal copies`, not merely `marketplace listing`;
4. resolve cross-platform physical-listing dedup only before multi-source normalized UI, consistent with OQ-005;
5. keep price-history/longitudinal observation separately gated by OQ-017 and per-source retention rights.

## Sources reviewed

Primary/current Scanboat surfaces:

- `https://www.scanboat.com/`
- `https://www.scanboat.com/en/boat-market/boats`
- `https://www.scanboat.com/en/BoatMarket/Home/Impressum`
- `https://www.scanboat.com/sitemap.xml`
- `https://www.scanboat.com/en/boat-market/boats/sailingboat-beneteau-oceanis-301-17539803`

Original/corroborating listing:

- `https://www.networkyachtbrokers.com/boats_for_sale/Beneteau_Oceanis_30_1-031346.html/`

Syndication ecosystem evidence:

- `https://ayb.yachts/nautix/`
- `https://boatface.pro/`
- `https://yachtbrokerpro.com/dashboard/`
- `https://www.easymls.com/en`

This note intentionally does not reproduce Scanboat expressive listing descriptions or images.
