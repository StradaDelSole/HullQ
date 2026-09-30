# Professional Inventory Editing & Maintenance Contract v0.1

**Status:** READY CANDIDATE  
**Owner:** SLICE-0072

## 1. Purpose

Expose the already-accepted revisioned marketplace truth stores as a safe Broker Workspace maintenance workflow for existing professional inventory.

```text
Organization-owned NativeListing
→ current offer + current Organization PhysicalBoat claim
→ authorized broker edits
→ immutable new revision(s)
→ explicit current head(s)
→ authoritative re-read
```

This is post-promotion maintenance, not draft editing and not a second truth pipeline.

## 2. Authorization and tenancy

Every read/mutation requires:

- valid HullQ session;
- fresh current ACTIVE OrganizationMembership;
- accepted privileged professional publishing role/MFA boundary;
- target NativeListing persisted as owned by the exact MarketplaceOrganization in the route.

Unknown and foreign Organization/listing combinations must remain non-enumerating.

Auth0 remains authentication-only. HullQ PostgreSQL membership/listing ownership remains authorization truth.

## 3. Editable truth scopes

### NativeListing offer

The editor may expose the already-accepted current `NativeListingOfferSnapshot` fields, including asking-price mode/amount/currency and the existing bounded listing-offer claims/narrative fields.

A save creates a new immutable offer revision through the existing authoritative offer persistence path and advances the explicit offer head.

### Organization PhysicalBoat claim

The editor may expose the already-accepted current Organization claim snapshot for the concrete PhysicalBoat reached through the NativeListing → MarketEpisode → PhysicalBoat chain, including the existing bounded claim fields and assertion semantics.

A save creates a new immutable PhysicalBoat claim revision for the same claiming Organization through the existing authoritative claim persistence path and advances the explicit claim head.

No design/configuration baseline value may silently become a concrete-yacht assertion.

## 4. Price change

A price change is an ordinary offer revision, not a special mutable column.

It must preserve:

- asking-price mode semantics;
- Decimal/currency validation;
- immutable revision history;
- recorded actor/provenance;
- optimistic concurrency;
- current-head truth.

Price change does not itself alter lifecycle, freshness, sale/outcome or buyer Lead state.

Buyer price-change alerts are not part of 0072.

## 5. Optimistic concurrency / idempotency

Every offer mutation must include the exact current offer revision identity it was edited from.

Every PhysicalBoat claim mutation must include the exact current claim revision identity it was edited from.

A stale expectation must fail closed with zero new current state.

A retry-safe client/server operation/revision identity must preserve the existing persistence semantics:

- identical retry → deterministic already-applied/success-equivalent outcome;
- reused identity with different immutable content → conflict;
- no silent overwrite.

After any mutation outcome, the browser must re-read authoritative current state.

## 6. Lifecycle interaction

0072 adds no lifecycle state and does not replace the accepted SLICE-0064 Publish/Withdraw/Reconfirm controls.

Editing is allowed only where the existing accepted truth model permits it.

PhysicalBoat claim persistence already permits authorized corrections while DRAFT, ACTIVE or later non-public; 0072 must preserve that behavior unless a stricter accepted invariant applies to a specific field.

Offer editing must not invent sale/commercial-outcome state.

WITHDRAWN remains non-public and is not implicitly republished by editing.

## 7. ACTIVE listing safety and D29

For an ACTIVE listing, a broker-controlled edit must not knowingly commit a broken hard current-public invariant.

The application mutation boundary must re-evaluate the accepted publication/current-public requirements as appropriate to the candidate resulting current heads.

If a candidate mutation would violate a hard ACTIVE public invariant, the mutation must fail atomically or use an accepted atomic replacement pattern. It must not leave an ACTIVE listing with a knowingly invalid current required state.

A valid technical claim change may legitimately change Search match/non-match/insufficient-data outcomes. That is not a lifecycle mutation and must be reflected through the existing deterministic Search truth.

## 8. Read model / browser surface

Provide a private/no-store/noindex Organization-scoped inventory-detail editor reachable from Broker Workspace inventory.

Minimum visible context:

- NativeListingId and publishing Organization;
- lifecycle/freshness/current-public state;
- current offer revision identity + editable accepted offer fields;
- current PhysicalBoat claim revision identity + editable accepted claim fields;
- publication readiness/current-public suppression context where applicable;
- links to existing media and lifecycle controls rather than duplicating them.

The page must distinguish:

- saved;
- invalid input;
- stale-version conflict;
- unauthorized/not found;
- MFA required;
- current-public/readiness blocking mutation;
- service failure.

## 9. Revision history / auditability

0072 need not build a polished revision-history browser, but accepted history must remain durable and queryable.

Every new revision preserves existing recorded actor/time/predecessor semantics.

The implementation must not update prior immutable revisions in place.

## 10. Draft separation

ProfessionalListingDraft remains a pre-market authoring object.

After promotion, the broker edits marketplace truth through the NativeListing offer / Organization PhysicalBoat claim revision paths.

0072 must not "unpromote" a draft, write edits back into the frozen promoted draft, or make the draft the current marketplace truth.

## 11. Media separation

Media operations remain owned by the accepted mixed-media gallery capability.

0072 may link to Manage Media but must not create a second upload/order/cover model.

## 12. Sale/outcome separation

A price/status/details edit must never infer SOLD, WON/LOST, achieved price or canonical MarketEpisode outcome.

Withdrawal remains lifecycle only.

Sale/outcome remains a later explicit capability.

## 13. Search/public truth

0072 adds no Search criterion.

Current Search and public listing reads must consume the newly current accepted offer/claim heads through the existing truth paths.

No edit endpoint may directly manipulate Search results, cached match flags or public projection rows as a substitute for updating authoritative truth.

Technical native Search criteria remain exactly:

1. `draft_max`
2. `keel_configuration`

## 14. CSRF / request safety

Browser mutations reuse the accepted same-origin + non-simple-header CSRF pattern.

Payloads are bounded and validated before mutation.

No browser-supplied Organization ownership, actor authorization, PhysicalBoat identity or current-public truth is trusted.

## 15. Concurrency proofs

Tests must prove at minimum:

- stale offer edit cannot overwrite a newer offer revision;
- stale PhysicalBoat claim edit cannot overwrite a newer claim revision;
- identical retry does not create duplicate current revisions;
- reused revision/operation identity with different content conflicts;
- foreign Organization cannot read/edit;
- revoked/inactive membership is observed fresh;
- ACTIVE hard-invariant failure leaves prior heads unchanged;
- concurrent edits produce one accepted current head and deterministic conflict for stale competitors.

## 16. Required retained proof

Real PostgreSQL + FastAPI + built Astro proof must demonstrate:

1. authorized broker opens existing promoted listing editor;
2. current offer/claim fields and revision identities are read from authoritative current heads;
3. broker changes asking price and saves a new offer revision;
4. public listing reflects the new current offer without lifecycle rewrite;
5. broker changes at least one concrete-yacht claim and saves a new claim revision;
6. Search/public truth reads the new claim through existing paths;
7. stale offer mutation is rejected without overwrite;
8. stale claim mutation is rejected without overwrite;
9. foreign Organization remains non-enumerating;
10. DRAFT/ACTIVE/WITHDRAWN lifecycle remains mechanically separate;
11. an ACTIVE edit that would violate a hard current-public requirement is rejected atomically;
12. existing media state is unchanged;
13. existing Lead state is unchanged;
14. technical Search criterion count remains exactly 2.

## 17. Non-goals

- new lifecycle states;
- sale/outcome workflow;
- MarketEpisode correction/reassignment;
- PhysicalBoat identity merge/replacement;
- media upload/order/cover implementation;
- duplicate/relist/clone;
- owner-direct marketplace editing/publication;
- bulk import/export/edit;
- buyer price-change alerts;
- production analytics/reporting;
- new Search criteria.
