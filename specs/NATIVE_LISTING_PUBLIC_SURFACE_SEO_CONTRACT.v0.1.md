# HullQ — NativeListing Public Surface SEO Contract v0.1

**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Date:** 2026-09-06  
**Applies to:** SLICE-0049 first production-public `NativeListing` page class only  
**Related:** ADR-0007, `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, OQ-018, `docs/slices/SLICE-0049-first-production-public-native-listing.md`

## Purpose

ADR-0007 and `architecture/SEARCH_AND_SEO_ARCHITECTURE.md` require public URL, canonicalization and indexation semantics to be defined before public frontend implementation rather than invented by routing code.

SLICE-0049 is the first production-public `NativeListing` frontend surface. This contract resolves the OQ-018 implementation gate only for that single page class. It does not resolve BoatModel, BoatDesign, technical landing-page, comparison, faceted-search or multilingual organic-distribution URL architecture.

The bounded product decision is intentionally conservative:

```text
public NativeListing identity
→ /listings/{NativeListingId}
→ ACTIVE only
→ stable ID-based canonical
→ deliberately noindex
```

Public availability is not equivalent to organic indexation.

## Requirements

### REQ-SEO-001 — Stable NativeListing public URL grammar

The only production-public `NativeListing` web-page grammar authorized by SLICE-0049 is:

```text
/listings/{NativeListingId}
```

`NativeListingId` is the stable HullQ domain identity anchor for this page class.

SLICE-0049 MUST NOT introduce a second public NativeListing route grammar, title/model/location route variant or human-readable slug route.

### REQ-SEO-002 — Identity, slug and rename behavior

The canonical page identity is the immutable `NativeListingId`, not listing title, yacht name, model, location, broker reference or other mutable display data.

For SLICE-0049:

```text
slug = NONE
```

Therefore changes to any mutable listing/display field MUST NOT change the public URL.

There is no slug-rename redirect problem in this page class because no slug exists. A later decision may add human-readable URL material only if the stable domain identity remains preserved and migration/redirect behavior is explicitly accepted before implementation.

### REQ-SEO-003 — Lifecycle-to-public-route behavior

Public route availability is determined only by the accepted SLICE-0049 publication predicate:

```text
complete durable listing + lifecycle == ACTIVE
→ public page may resolve

DRAFT | WITHDRAWN | missing | incomplete
→ ordinary external not-found
```

The public route MUST NOT reveal whether a non-public identifier is DRAFT, WITHDRAWN, missing or incomplete.

Lifecycle and freshness remain separate. `WITHDRAWN` MUST NOT be represented as `SOLD`, and no freshness state is introduced by this contract.

### REQ-SEO-004 — Query-parameter and canonicalization behavior

Query parameters are not part of NativeListing identity in SLICE-0049.

For an exact supported path:

```text
/listings/{NativeListingId}?anything=...
```

query parameters MUST NOT select a different NativeListing, create a second content identity, alter lifecycle/publication truth or appear in the canonical URL.

If the application accepts a query-bearing request, the page canonical MUST still be the clean path:

```text
/listings/{NativeListingId}
```

A redirect solely to remove query parameters is not required by SLICE-0049. Unknown query parameters may be ignored at this page boundary, but they MUST NOT create canonical/indexable variants.

The clean ACTIVE page MUST emit a self-canonical URL for the exact stable ID-based path.

### REQ-SEO-005 — Redirect and migration policy for this page class

SLICE-0049 has no accepted legacy public NativeListing URL grammar and no slug grammar. Therefore it MUST NOT invent legacy aliases or migration redirects.

Unsupported alternate route forms are not separate public identities and may resolve as ordinary not-found according to the router contract.

If a future accepted architecture changes the NativeListing public grammar, adds locale prefixes/slugs or replaces this route, that future change MUST define the redirect/migration mapping from `/listings/{NativeListingId}` before deployment. It MUST NOT silently orphan or multiply the stable public identity introduced here.

### REQ-SEO-006 — Crawl/index class

The SLICE-0049 NativeListing page class is:

```text
publicly retrievable when ACTIVE
AND
intentionally NOT indexable
```

Every successfully rendered ACTIVE page MUST carry an explicit `noindex` directive through the accepted web/HTTP presentation boundary. The implementation may use the mechanisms required by the slice contract, including robots metadata and/or `X-Robots-Tag`, but acceptance MUST mechanically prove that the page is intentionally non-indexable.

`noindex` is a deliberate product state, not a temporary omission of SEO work.

DRAFT, WITHDRAWN, missing and incomplete listings remain ordinary not-found and MUST NOT expose a public status page for indexing.

### REQ-SEO-007 — No sitemap or organic-discovery promotion in SLICE-0049

SLICE-0049 MUST NOT:

- add NativeListing URLs to XML sitemaps;
- create a sitemap registry for this page class;
- create SEO landing pages that link to listings for crawl discovery;
- add faceted listing URL classes;
- add structured-data claims solely to seek search appearance;
- treat public publication as authorization for organic indexation.

A later capability may promote the page class to indexable only through an explicit accepted SEO/indexation decision with truthful metadata, sitemap/internal-linking behavior and any required schema/i18n rules.

### REQ-SEO-008 — Preview URLs remain outside public canonical identity

The accepted SLICE-0048 preview surface remains a separate finite bearer-capability surface.

Hard:

```text
PREVIEWABLE != PUBLISHED
PREVIEW URL != canonical public listing URL
```

Preview URLs MUST remain non-canonical, non-indexable and capability-gated. They MUST NOT redirect to, alias or become canonical variants of `/listings/{NativeListingId}` merely because a corresponding listing becomes ACTIVE.

### REQ-SEO-009 — Language scope

The SLICE-0049 route grammar is language-neutral and contains no locale prefix:

```text
/listings/{NativeListingId}
```

SLICE-0049 does not establish the final multilingual URL matrix, hreflang architecture or translated organic landing-page system.

The absence of locale prefixes in 0049 MUST NOT be interpreted as rejection of HullQ's accepted future public-language requirements. If later multilingual architecture changes the route grammar or introduces localized variants, it MUST preserve stable `NativeListingId` identity and define canonical/redirect/hreflang behavior before deployment.

### REQ-SEO-010 — OQ-018 remains gated for all other public page classes

This contract resolves the pre-public implementation gate only for the first NativeListing page class.

It does NOT authorize public implementation or indexation policy for:

- BoatModel pages;
- BoatDesign/generation pages;
- technical-category/search landing pages;
- comparison pages;
- arbitrary faceted/filter combinations;
- search result pages;
- pagination/sort variants;
- multilingual organic page trees;
- structured-data mappings;
- sitemap architecture beyond the explicit 0049 exclusion.

Those remain subject to the broader OQ-018 decision process and ADR-0007.

## Truth and implementation invariants

This page-class contract does not weaken the marketplace truth model.

Hard:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
BROKER_CLAIM != VERIFIED_FACT
PUBLIC != INDEXABLE
ACTIVE != FRESHNESS CONFIRMED
```

Frontend/Astro routing MUST consume the accepted FastAPI public read boundary and MUST NOT create its own publication or truth semantics.

The canonical URL MUST never be used as evidence that a listing, broker claim, tax claim, physical-boat fact or freshness claim has been independently verified by HullQ.

## Acceptance trace for SLICE-0049

SLICE-0049 implementation acceptance MUST prove at least:

1. ACTIVE complete listing resolves at `/listings/{NativeListingId}` without preview credentials;
2. DRAFT/WITHDRAWN/missing/incomplete are externally not-found-equivalent;
3. the rendered ACTIVE page uses the clean ID-based self-canonical URL;
4. query parameters do not create a second canonical identity;
5. the page is deliberately `noindex`;
6. no listing sitemap/hreflang/faceted SEO expansion is introduced;
7. SLICE-0048 preview remains non-canonical and protected;
8. no title/model/location rename changes the page identity because no slug participates in the route.

## Deferred decision boundary

Promotion of public NativeListing pages from `noindex` to an indexable organic-distribution surface is a later explicit architecture/product decision. That decision must address, as applicable, current search-engine guidance, sitemap/internal-linking discovery, truthful metadata/structured data, language/hreflang behavior, withdrawal/removal semantics and measurement.

SLICE-0049 therefore creates the first stable production-public listing identity without prematurely launching HullQ's full SEO distribution system.
