# HullQ — Professional Listing Promotion Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0067 — Professional Draft → Atomic Marketplace Promotion  
**Controlling decisions:** `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D01–D09 and D18  
**Execution focus:** `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`

## 1. Purpose

This contract defines one professional Broker Workspace capability:

> An authorized professional publisher can promote one exact, promotion-ready `ProfessionalListingDraft` version into exactly one durable marketplace `NativeListing` in lifecycle `DRAFT`, with the required fresh PhysicalBoat, fresh MarketEpisode, initial publishing-Organization PhysicalBoat claim revision and initial NativeListing offer revision, as one atomic and retry-safe transaction.

Promotion is not publication.

```text
private ProfessionalListingDraft
  -- PROMOTION_READY + authorized promotion -->
NativeListing lifecycle DRAFT
```

No promoted listing becomes ACTIVE or public merely because promotion succeeds.

## 2. Fresh-identity scope of v0.1

SLICE-0067 implements only the already-decided D01/D02 default branch where no trusted existing yacht/episode resolution is supplied.

The promotion request MUST NOT accept:

- `PhysicalBoatId`;
- `MarketEpisodeId`;
- `NativeListingId`;
- fuzzy identity candidates;
- broker-reference-based identity hints;
- BoatDesign-derived concrete-yacht identity.

For v0.1:

```text
no safely resolved existing PhysicalBoat input exists
→ server mints new PhysicalBoatId
→ new PhysicalBoat implies new MarketEpisode
→ server mints new MarketEpisodeId
→ server mints new NativeListingId
```

The new PhysicalBoat is created with `boat_design_ref = NULL`.

No BoatDesign fact may be copied into PhysicalBoat claims.

Later existing-PhysicalBoat reuse / same-new-unresolved episode reconciliation remains a separate identity capability.

## 3. PromotionReadiness

PromotionReadiness is a pure deterministic evaluation of the current exact professional draft content.

It is distinct from:

- private draft validity;
- publishing authorization/eligibility;
- PublicationReadiness;
- Search eligibility;
- listing quality guidance.

### 3.1 Required responses

A draft is content-ready only when all accepted D07 requirements are satisfied:

- `physical_boat.marketed_brand_claim` is present;
- `physical_boat.model_designation_claim` is present;
- `physical_boat.build_year` is present as explicit VALUE_ASSERTION(year) or UNKNOWN;
- `listing_offer.asking_price_mode` is present;
- `listing_offer.location_country` is present;
- professional-only `listing_offer.broker_description` is present;
- when mode is `AMOUNT`, both asking-price amount and currency are present.

Not required:

- boat name;
- location region;
- broker listing reference;
- BoatDesignRef;
- Search-fit/technical Search fields;
- media.

### 3.2 Price-state consistency at promotion

The marketplace offer model remains authoritative.

For `AMOUNT`:

```text
amount present
currency present
```

For `POA`:

```text
amount absent
currency absent
```

The draft parser already rejects POA + amount. PromotionReadiness MUST additionally block POA + currency rather than silently dropping the draft value.

### 3.3 Machine reason codes

The evaluator MUST return a deterministic ordered tuple/list of machine-readable reasons in exactly the canonical order below whenever each condition applies:

```text
MISSING_MARKETED_BRAND
MISSING_MODEL_DESIGNATION
MISSING_BUILD_YEAR_RESPONSE
MISSING_ASKING_PRICE_MODE
MISSING_LOCATION_COUNTRY
MISSING_BROKER_DESCRIPTION
MISSING_ASKING_PRICE_AMOUNT
MISSING_CURRENCY
CURRENCY_NOT_ALLOWED_FOR_POA
```

Conditional price reasons are evaluated only when a mode is present:

- mode omitted -> `MISSING_ASKING_PRICE_MODE`; do not additionally invent AMOUNT/POA conditional reasons;
- mode AMOUNT -> add `MISSING_ASKING_PRICE_AMOUNT` and/or `MISSING_CURRENCY` when missing;
- mode POA -> amount is already rejected by the shared draft parser; a present currency adds `CURRENCY_NOT_ALLOWED_FOR_POA`.

A ready result has zero reasons.

The authoritative promotion transaction MUST re-evaluate the same evaluator against the locked current draft version. Browser/preflight display may reuse the same evaluator output but can never replace the mutation-time evaluation.

## 4. Authorization and non-enumeration

Promotion requires all existing professional workspace/auth boundaries plus public-listing publishing eligibility.

Required current state:

1. authenticated HullQ session;
2. selected Organization exists and is accessible under the accepted Broker Workspace boundary;
3. MFA requirement satisfied;
4. exact current matching ACTIVE OrganizationMembership;
5. current membership contains `PUBLISHER`;
6. accepted `evaluate_native_listing_publishing_eligibility()` returns ALLOWED for the exact Account/Organization/Membership used by the promotion.

Private draft authoring remains less restrictive: an ineligible/unverified Organization may still retain drafts, but cannot perform a **new** EDITABLE -> PROMOTED materialization.

Foreign-Organization and unknown draft IDs remain non-enumerating and produce the same not-found-equivalent result after the Organization boundary succeeds.

For every request, current session/Organization/MFA/current ACTIVE PUBLISHER membership authorization is required before draft/result disclosure.

For an EDITABLE draft that may create marketplace state, the promotion transaction MUST revalidate current publishing eligibility before durable marketplace writes.

For an already-PROMOTED own draft, an exact-version retry is a read/idempotency result, not a second marketplace creation attempt: after current workspace/MFA/PUBLISHER authorization succeeds, it returns `ALREADY_PROMOTED` without requiring the Organization still to pass current publishing eligibility and without performing any marketplace write. Later ineligibility affects future publication/current-public behavior, not historical promotion provenance.

## 5. Draft promotion state and provenance

ProfessionalListingDraft gains durable promotion state:

```text
EDITABLE
PROMOTED
```

Existing rows migrate to `EDITABLE`.

A promoted draft stores:

```text
promotion_state = PROMOTED
promoted_native_listing_id = resulting NativeListingId
promoted_at = database-generated promotion timestamp
```

Required invariants:

- EDITABLE => promoted_native_listing_id is NULL and promoted_at is NULL;
- PROMOTED => promoted_native_listing_id is non-NULL and promoted_at is non-NULL;
- one promoted NativeListingId may be linked from at most one ProfessionalListingDraft;
- `promoted_native_listing_id`, when non-null, MUST be a real FK to `native_listings.native_listing_id`;
- PostgreSQL MUST enforce the EDITABLE/PROMOTED nullability pairing with CHECK constraints/equivalent and MUST enforce non-null `promoted_native_listing_id` uniqueness;
- the provenance link is immutable;
- the draft content/version that was promoted is immutable forever;
- promotion MUST NOT increment the content `version`; that frozen version number is the exact promoted draft version;
- a PROMOTED draft can never return to EDITABLE;
- ordinary draft update is allowed only while EDITABLE;
- active draft list operations exclude PROMOTED rows;
- direct read of a known own promoted draft may return immutable provenance so a bookmarked/retried workflow can explain the resulting NativeListing;
- direct edit UI for a PROMOTED draft must not offer Save/mutation controls.

## 6. Promotion request and result

Canonical mutation route:

```text
POST /api/broker/organizations/{organization_id}/drafts/{draft_id}/promote
```

Request body contains exactly one key:

```json
{"expected_version": 7}
```

`expected_version` MUST be a positive JSON integer and MUST reject booleans. Missing/extra keys, null, strings, floats/decimals and non-positive integers are malformed requests and fail with zero mutation.

No marketplace IDs or resolution hints are accepted from the client.

Bounded outcomes:

```text
PROMOTED
ALREADY_PROMOTED
NOT_READY
VERSION_CONFLICT
DRAFT_NOT_FOUND
ORG_NOT_FOUND_OR_DENIED
MFA_REQUIRED
DENIED
DUPLICATE_EPISODE
```

Rules:

- `PROMOTED` carries the resulting NativeListingId;
- `ALREADY_PROMOTED` carries the already persisted resulting NativeListingId;
- `NOT_READY` carries the canonical PromotionReadiness reason codes;
- `DENIED` carries the existing publishing-eligibility denial reason;
- `DUPLICATE_EPISODE` may carry the existing own NativeListingId only when the caller is authorized to know it;
- no unsuccessful outcome mutates draft or marketplace state.

Suggested HTTP mapping:

- unauthenticated: 401;
- Organization/draft non-enumerating not found: 404;
- MFA / eligibility denial: 403;
- malformed request: 400;
- NOT_READY / VERSION_CONFLICT / DUPLICATE_EPISODE: 409;
- PROMOTED: 201;
- ALREADY_PROMOTED exact retry: 200.

## 7. Exact-version idempotency and concurrency

Promotion is keyed primarily by the durable draft state, not a client operation ID.

The authoritative transaction MUST lock the target draft row for update and compare the supplied positive integer `expected_version`.

### 7.1 EDITABLE current draft

If:

```text
promotion_state = EDITABLE
and expected_version = current version
and PromotionReadiness = READY
and authorization/eligibility = ALLOWED
```

the transaction may materialize marketplace state.

### 7.2 Stale expected version

If `expected_version != current version`:

```text
VERSION_CONFLICT
zero mutation
```

### 7.3 Exact retry after promotion

If the draft is already PROMOTED and the supplied expected version equals the frozen promoted version:

```text
ALREADY_PROMOTED
same persisted promoted_native_listing_id
zero additional rows
```

No new IDs are generated and no marketplace write is retried.

If the draft is already PROMOTED but the supplied expected version does **not** equal the frozen promoted version, return `VERSION_CONFLICT` with zero mutation; do not reveal a result for a version the caller did not name.

### 7.4 Concurrent attempts

The draft row lock serializes concurrent promotion attempts.

Exactly one transaction may perform EDITABLE → PROMOTED.

A later concurrent waiter observes PROMOTED and returns ALREADY_PROMOTED for the same exact version.

## 8. Atomic materialization transaction

Promotion MUST be one top-level PostgreSQL transaction.

The transaction owns all writes below:

1. lock/read exact Organization-owned draft;
2. exact-version/state check;
3. revalidate authorization/publishing eligibility;
4. evaluate PromotionReadiness;
5. mint server-owned random marketplace/revision identities;
6. create fresh PhysicalBoat with no BoatDesignRef;
7. create fresh MarketEpisode linked to that PhysicalBoat;
8. create NativeListing linked to that MarketEpisode and publishing Organization;
9. ensure NativeListing initial lifecycle is DRAFT;
10. create the Organization's initial PhysicalBoat claim revision/head;
11. create the NativeListing's initial offer revision/head;
12. mark the exact ProfessionalListingDraft version PROMOTED and persist the NativeListing provenance link;
13. COMMIT.

Any error/conflict/failure before commit MUST roll back **all** writes from the attempt.

No partial state such as "PhysicalBoat exists but draft still EDITABLE" is allowed.

## 9. Transaction-composable persistence

Existing public persistence functions for PhysicalBoat, MarketEpisode, NativeListing, offer revisions and PhysicalBoat claims intentionally own and commit independent top-level transactions.

SLICE-0067 MUST preserve those accepted standalone guarantees.

Promotion MUST NOT satisfy §8 by sequentially invoking those top-level-owning public wrappers.

Implementation MAY factor private/internal transaction-scoped primitives from the existing persistence modules and reuse them from:

- the existing standalone public function inside its own top-level transaction; and
- the new promotion transaction inside the one caller-owned top-level transaction.

Equivalent safe composition is acceptable if it mechanically preserves the exact existing validation, fingerprint/idempotency, FK, head-pointer and Organization-isolation semantics.

Do not introduce a generic repository/Unit-of-Work framework.

## 10. Draft → marketplace truth mapping

### 10.1 PhysicalBoat

New PhysicalBoat:

```text
PhysicalBoatId = server random
boat_design_ref = NULL
```

### 10.2 MarketEpisode

New MarketEpisode:

```text
MarketEpisodeId = server random
physical_boat_id = newly created PhysicalBoatId
```

### 10.3 NativeListing creation envelope

New NativeListing:

```text
NativeListingId = server random
publishing_organization_id = authorized selected Organization
created_by_account_id = authenticated promoting Account
market_episode_id = newly created MarketEpisodeId
broker_listing_reference = exact optional draft broker reference
lifecycle_state = DRAFT
```

The draft broker reference becomes immutable creation provenance only under the existing NativeListing envelope.

D19's separately revisioned **current operational broker reference** remains a later editing capability; no value is lost because immutable creation provenance is retained.

### 10.4 Initial PhysicalBoat claim

Create exactly one first claim revision/head for the publishing Organization:

```text
marketed_brand_claim = draft concrete value
model_designation_claim = draft concrete value
build_year =
  draft VALUE_ASSERTION(year) -> BuildYearClaim(VALUE_ASSERTION, year)
  draft UNKNOWN               -> BuildYearClaim(UNKNOWN)
boat_name =
  draft present -> BoatNameClaim(VALUE_ASSERTION, text)
  draft omitted -> claim omitted
loa_length = omitted
draft = omitted
keel_configuration = omitted
rudder_configuration = omitted
```

No BoatDesign baseline value is copied.

### 10.5 Initial offer

Create exactly one first offer revision/head:

```text
asking_price_mode = draft mode
asking_price_amount = draft amount only for AMOUNT
currency = draft currency only for AMOUNT
location_country = draft country
location_region =
  draft present -> LocationRegionClaim(VALUE_ASSERTION, text)
  draft omitted -> omitted
broker_description = professional draft description
broker_summary = omitted
known_history_narrative = omitted
vat_tax_status_claim = omitted
```

## 11. Resolved NativeListing uniqueness

Accepted D09 is now enforced at the database boundary:

```text
for market_episode_id IS NOT NULL:
UNIQUE (publishing_organization_id, market_episode_id)
```

Different Organizations may each reference the same resolved MarketEpisode.

The same Organization may not hold two NativeListings for the same resolved MarketEpisode.

A migration introducing this invariant MUST validate existing data and fail closed if historical rows violate it; it MUST NOT silently delete, relink or merge rows.

The low-level NativeListing creation boundary must classify this unique violation as a deterministic Organization+MarketEpisode conflict rather than leaking an unhandled database exception.

The promotion boundary maps that case to `DUPLICATE_EPISODE` and leaves the source draft EDITABLE with zero marketplace mutation from that attempt.

Broker listing reference MUST NOT participate in this uniqueness rule.

## 12. Browser behavior

The professional draft editor exposes the promotion state without creating a second client-side readiness authority.

For an EDITABLE draft:

- display PromotionReadiness missing reasons from the server-owned evaluator;
- retain ordinary Save behavior;
- when ready, expose a clear "Create listing" / "Promote to inventory" action;
- action posts the exact current draft version;
- visible errors distinguish incomplete, stale/version conflict, MFA/eligibility denial and generic service failure.

On PROMOTED success:

- clear any recovery envelope for that exact draft/version;
- navigate to or link to the Organization inventory surface and identify the resulting NativeListing;
- do not claim the listing is public;
- inventory must show it as lifecycle DRAFT.

For a directly reopened PROMOTED draft:

- show immutable promoted provenance/result;
- do not show editable Save/Promote controls;
- do not apply browser-local recovery, even if a pre-promotion recovery envelope carries the same frozen draft version;
- best-effort remove/clear any recovery envelope for that promoted draft so stale private form input cannot reappear over immutable provenance.

Because promotion intentionally does not increment the draft content version, promotion state MUST be an explicit recovery applicability guard; version equality alone is insufficient after SLICE-0067.

## 13. Browser write security

Promotion is a state-changing cookie-authenticated browser action and MUST reuse the accepted professional draft same-origin CSRF boundary.

The browser/FastAPI route MUST require:

- exact normalized trusted HullQ `Origin`;
- header `X-HullQ-Requested-With: professional-listing-draft-v1`, reusing the accepted professional draft CSRF boundary exactly;
- no permissive credentialed CORS.

Missing/foreign Origin or missing/wrong fixed header fails closed before promotion mutation.

If Astro proxies the promotion request it must preserve the browser Origin under the same accepted rule; it must not replace an untrusted Origin with a trusted one.

## 14. Publication / public visibility

Promotion creates no publication transition and no freshness confirmation.

A promoted NativeListing remains:

```text
lifecycle_state = DRAFT
public listing eligibility = false
```

The accepted public listing surface must not expose the new DRAFT listing as public/current inventory.

Media and D22 PublicationReadiness remain later capabilities.

## 15. Non-goals

SLICE-0067 does not:

- accept or infer an existing PhysicalBoatId;
- resolve same/new/unresolved MarketEpisode continuity for an existing PhysicalBoat;
- merge/deduplicate fuzzy yacht candidates;
- link BoatDesignRef;
- implement D19 editable/current operational broker-reference revisions;
- implement D20 NativeListingEpisodeResolution revision history;
- republish/relist/clone/duplicate drafts;
- add media/gallery;
- publish or activate a listing;
- create freshness confirmation;
- implement PublicationReadiness;
- edit marketplace offer/claim truth after promotion;
- implement leads/CRM/outcomes/analytics/import/export/alerts;
- add Search criteria or change Search ranking/eligibility;
- touch owner-direct publication.

## 16. Compatibility invariants

After implementation:

```text
ProfessionalListingDraft save remains private while EDITABLE
PROMOTION_READY != PUBLICATION_READY
promotion success -> one NativeListing DRAFT
promotion success -> one fresh PhysicalBoat
promotion success -> one fresh MarketEpisode
promotion success -> one initial Organization PhysicalBoat claim head
promotion success -> one initial NativeListing offer head
promotion success -> source draft PROMOTED + immutable result link
exact retry -> same NativeListingId + zero additional writes
any failure -> zero partial marketplace state
different Organizations may list same resolved MarketEpisode
same Organization may not create a second listing for same resolved MarketEpisode
technical Search criteria count remains 2
```
