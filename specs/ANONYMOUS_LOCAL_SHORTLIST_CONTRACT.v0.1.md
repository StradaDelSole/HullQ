# HullQ — Anonymous Local Shortlist Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0058 — Anonymous Local Shortlist  
**Controlling product direction:** `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`  
**Marketplace identity foundation:** accepted SLICE-0043/0049/0050/0052  
**Public UX baseline:** `docs/PRODUCT_UX_PRINCIPLES.md`

## 1. Purpose

This contract adds one anonymous buyer-interest capability:

> The buyer explicitly saves/removes current NativeListing identities in one browser-local shortlist and may revisit that shortlist without an account.

The shortlist is an interest collection. It is not Search truth, BuyerRequirements truth, a recommendation, a ranking or server-owned buyer persistence.

## 2. Hard semantic boundary

The controlling invariant is:

```text
shortlist membership = explicit buyer interest
```

Never:

```text
shortlist membership = HullQ says this boat fits
```

Therefore HullQ MUST NOT automatically add or remove a listing because:

- Search criteria changed;
- Requirement Sensitivity changed;
- a listing matches or stops matching a technical criterion;
- evidence becomes UNKNOWN/INSUFFICIENT;
- another boat appears to fit better;
- the listing becomes temporarily unavailable.

Only an explicit buyer add/remove action mutates membership in v0.1.

## 3. Identity and local persistence

The only persisted browser-domain value per entry is the stable `NativeListingId`.

The browser MUST NOT persist as shortlist truth:

- asking price;
- currency;
- location;
- broker/seller text;
- PhysicalBoat claims;
- freshness status;
- last-confirmed timestamp;
- Search result class/evidence;
- recommendation/fit score.

The local representation MUST be versioned and bounded, conceptually:

```json
{
  "version": 1,
  "listing_ids": ["<NativeListingId>", "..."]
}
```

An equivalent representation is acceptable if it preserves the same semantics.

The storage key is implementation-owned but MUST be versioned (for example `hullq.shortlist.v1`) and must not collide with future authenticated/server persistence.

Client-controlled storage is untrusted input. Malformed JSON, wrong version, non-string IDs, duplicates and pathological size MUST fail safely without executing script/HTML or corrupting the page.

A technical safety cap is allowed to bound browser/API work. Such a cap is **not** a Free/Pro/account entitlement and MUST NOT be presented as the accepted commercial shortlist limit.

## 4. Membership and order

Add is idempotent:

```text
add(existing ID) -> membership unchanged
```

Remove is idempotent:

```text
remove(absent ID) -> membership unchanged
```

The list has set-like membership plus stable buyer-authored presentation order.

v0.1 SHOULD use insertion order (or equivalent deterministic buyer-authored order) and MUST NOT reorder entries by:

- HullQ fit;
- Search match;
- seller payment;
- broker status;
- price desirability;
- inferred preference;
- expected revenue.

No drag/reorder capability is required.

## 5. Current truth re-resolution

Opening the shortlist MUST re-resolve saved IDs against the accepted current public listing-read boundary.

The authoritative current public semantics remain:

```text
NativeListingId
→ ACTIVE
→ complete durable listing chain
→ current-market eligible freshness
→ PublicListingReadModel
```

The shortlist MUST NOT treat stale locally cached listing content as current truth.

Implementation may reuse `GET /api/listings/{native_listing_id}` per saved ID or introduce a bounded batch read transport, but any batch transport MUST delegate to the same accepted public listing read model and preserve the identical unavailable boundary.

Astro/TypeScript MUST NOT independently infer listing lifecycle/freshness/publication eligibility.

## 6. Unavailable saved IDs

A saved ID that does not resolve through the current public listing read model is shown only as a neutral state such as:

```text
This saved listing is not currently available.
```

The UI MUST NOT distinguish whether the underlying cause is:

- missing;
- DRAFT;
- WITHDRAWN;
- incomplete chain;
- STALE;
- freshness UNKNOWN;
- another internal/non-public state.

This preserves the existing non-enumeration/public-read boundary.

Unavailable membership is **not automatically deleted**.

The buyer may remove it explicitly. If it later becomes publicly readable again, the same saved ID may resolve again on a future visit.

This behavior is not monitoring/alerting; no background notification is created.

## 7. Anonymous/browser-local boundary

v0.1 requires no HullQ account.

No shortlist rows, buyer profile, anonymous durable intent object, cookie-backed server list or account association are created.

Browser-local storage is the source of shortlist membership in 0058.

Consequences are explicit:

- another browser/device does not see the shortlist;
- clearing site storage removes it;
- private/incognito behavior follows the browser's own storage policy;
- server logs must not be treated as a substitute shortlist store.

## 8. Public web surfaces

The canonical localized shortlist page is:

```text
/{locale}/shortlist
```

for the existing public locales:

```text
en
de
fr
pt
es
```

It is a user-specific browser-local surface and MUST be `noindex`; it must not enter sitemap/hreflang discovery as indexable content.

The page must visibly support:

- empty shortlist;
- current available saved listings;
- neutral unavailable saved entries;
- explicit remove;
- navigation to an available listing.

Search result surfaces for all five locales must expose an explicit add/remove shortlist control for confirmed match listings.

The existing non-localized public listing page may expose the same add/remove control without forcing a locale-routing redesign; adding localized public listing URL architecture is out of scope.

## 9. Client interaction boundary

Client-side code is justified because browser-local storage is inherently client-owned.

The client may:

- read/write the versioned shortlist ID representation;
- perform idempotent add/remove;
- update button state/count;
- request current listing projections;
- render transport results safely.

The client MUST NOT:

- evaluate Search truth;
- classify listing freshness/lifecycle;
- invent current price/claim data;
- generate fit/recommendation scores;
- infer interest from clicks/searches;
- add entries without the explicit buyer action.

Any HTML rendering of stored IDs or returned text must use safe DOM/text rendering, never raw untrusted HTML injection.

## 10. Current-listing transport

A bounded browser-to-server transport may be introduced solely to resolve saved IDs efficiently/currently.

If added, it must:

- accept only a bounded collection of candidate NativeListingId strings;
- treat input as untrusted;
- de-duplicate deterministically;
- never accept caller-supplied listing truth;
- resolve each ID via the accepted public listing read model;
- return available current public projections and an indistinguishable unavailable state for non-resolving IDs;
- preserve requested/buyer-authored order;
- have no persistence side effect;
- fail unavailable/5xx on backend failure rather than returning fabricated empty current results.

A per-ID reuse of the existing public endpoint is equally valid if the browser/server topology is proven usable and bounded.

FastAPI remains the sole application/domain truth boundary. An Astro same-origin proxy may transport IDs/results but may not become a second listing truth layer.

## 11. Privacy and telemetry

SLICE-0058 does not introduce shortlist analytics/telemetry.

The server may necessarily receive saved IDs when the shortlist resolves current public data, but those requests MUST NOT create a durable buyer-interest profile or be interpreted as an accepted behavioral-preference model.

No advertising, seller payment, verification fee or referral economics affect shortlist order or membership.

## 12. Copy / decision neutrality

Shortlist copy may use factual terms such as:

- Save to shortlist;
- Saved;
- Remove;
- Your shortlist;
- Not currently available.

It MUST NOT label shortlist membership as:

- recommended;
- best fit;
- matched for you;
- top choice;
- HullQ selected.

## 13. Error behavior

At minimum:

- corrupted local storage -> recoverable empty/valid subset state; page remains usable;
- unsupported locale -> existing locale routing behavior / 404 as appropriate;
- invalid/tampered ID collection -> bounded invalid/recovery behavior, never server error from unchecked input;
- listing resolver/API outage -> visible unavailable/service-error state, not silent deletion and not fabricated "no saved listings";
- one unavailable listing -> does not prevent rendering other resolvable entries.

An upstream outage must be distinguishable from a normal per-listing unavailable result at the transport level so the UI does not convert infrastructure failure into listing-state truth.

## 14. No automatic cleanup

v0.1 MUST NOT silently remove an ID solely because the listing is currently unavailable.

Optional explicit "Remove" remains the only membership deletion.

A future product may add buyer-controlled cleanup, archival history or monitoring, but none is authorized here.

## 15. SEO boundary

The shortlist is user-specific browser-local state.

Therefore:

- `/{locale}/shortlist` is `noindex`;
- no saved IDs appear in query strings or canonical URLs;
- no one-URL-per-shortlist scheme is introduced;
- no public share token is created;
- no sitemap entry is created for personalized shortlist content.

This slice does not change public listing indexability or Direct Search URL semantics.

## 16. Tests and retained proof

At minimum cover:

### Local store

- empty/missing store;
- valid v1 store;
- idempotent add;
- idempotent remove;
- insertion order preservation;
- duplicate normalization;
- malformed JSON;
- wrong version;
- non-string/empty IDs;
- pathological oversize handling;
- no listing truth fields stored.

### Current truth resolution

- available saved ID resolves current public projection;
- stale/withdrawn/missing/incomplete all use the same unavailable browser semantics;
- unavailable ID remains stored until buyer removes it;
- multiple IDs preserve buyer-authored order;
- one unavailable entry does not hide valid entries;
- backend failure is not converted to normal unavailable/empty truth;
- no persistence side effects.

### Web

- all five locale Search result surfaces offer add/remove;
- `/{locale}/shortlist` empty/available/unavailable states;
- current add/remove state updates from local storage;
- public listing page can add/remove without creating account state;
- no raw HTML injection from local storage;
- shortlist page is noindex;
- no saved IDs in URL/canonical metadata;
- no recommendation/ranking language.

### Retained vertical proof

A deterministic built-web proof must demonstrate at minimum:

1. a current public listing/search result;
2. explicit anonymous add;
3. browser-local ID-only persistence;
4. shortlist page resolves current listing data;
5. current offer/claim/freshness is not read from stored browser payload;
6. explicit remove;
7. unavailable saved ID remains visible as neutral unavailable and remains saved;
8. ordinary Search/public listing behavior remains unchanged;
9. no account/database shortlist persistence appears;
10. finish with:

```text
ANONYMOUS LOCAL SHORTLIST RESULT -> PASS
```

CI must execute the retained proof in an appropriate normal web/PostgreSQL integration path.

## 17. Explicitly deferred

Not part of v0.1 / SLICE-0058:

- database-backed Shortlist;
- authenticated Shortlist;
- cross-device sync;
- anonymous-to-account migration;
- multiple/named shortlists;
- Free/Pro shortlist entitlement limits;
- Compare;
- BuyerRequirements evaluation over shortlist;
- private notes;
- sharing;
- monitoring/alerts;
- background availability checks;
- seller/broker contact;
- lead attribution;
- telemetry-based preference inference;
- recommendation/ranking;
- third Search criterion;
- owner-direct publication;
- broker workspace expansion.

## 18. Acceptance summary

Accepted v0.1 boundary:

```text
explicit buyer add/remove
→ browser stores NativeListingId only
→ one anonymous local shortlist
→ current public listing truth re-resolved when viewed
→ unavailable stays neutral + locally retained
→ no fit/recommendation semantics
```

Never:

```text
browser stores stale listing truth
or
Search/Requirements mutate membership
or
HullQ ranks shortlist by inferred fit
or
0058 creates a server buyer profile
```
