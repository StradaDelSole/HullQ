# HullQ Professional Draft Publication Readiness Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0064 — Professional Draft Publication Readiness  
**Depends on:** accepted ProfessionalListingDraft workspace/recovery; accepted PhysicalBoat claim model; NativeListing creation/offer/lifecycle contracts  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This contract defines one capability:

> deterministically evaluate whether the exact current ProfessionalListingDraft can be mapped losslessly into the already-accepted marketplace input models required by a later promotion, while performing zero marketplace promotion.

0064 is not the promotion transaction.

## 2. Hard boundaries

```text
publication readiness != publication
draft mapping != marketplace truth
candidate target values != persisted marketplace facts
```

Readiness MUST NOT create or mutate PhysicalBoat, MarketEpisode, NativeListing, claim/offer revisions, lifecycle, freshness, public listing state or Search state.

## 3. Professional draft vocabulary extension

Add exactly one professional-only draft input:

```text
listing_offer.broker_description
```

Semantics:

- optional while incomplete;
- when present: trimmed non-empty string;
- maximum 10,000 Unicode code points;
- Unicode control characters category `Cc` rejected;
- plain text only;
- safely escaped;
- included in professional draft create/read/update/recovery;
- NOT added to the channel-neutral owner-direct/common nine-field vocabulary.

## 4. PhysicalBoat boat-name claim extension

The accepted registry field `physical_boat.boat_name` becomes representable in the bounded PhysicalBoat broker-claim model.

Accepted states:

```text
omitted
VALUE_ASSERTION(non-blank string)
ABSENT
UNKNOWN
```

The current snapshot extends from seven to exactly eight fields by adding boat name. No other registry field enters 0064.

Existing claim revisions predate boat-name storage. Migration/readback MUST preserve them as boat-name omitted, never ABSENT/UNKNOWN/value.

All accepted SLICE-0050 revision/current-head/Organization attribution/concurrency/no-BoatDesign-fallback semantics remain unchanged.

## 5. Professional draft → candidate mapping

Evaluator result:

```text
READY
BLOCKED
```

READY carries typed candidate target values sufficient for a later promotion to construct required PhysicalBoat claim and NativeListing offer inputs without reinterpreting raw strings.

### 5.1 Required inputs

READY requires:

```text
physical_boat.marketed_brand_claim
physical_boat.model_designation_claim
physical_boat.build_year
listing_offer.asking_price_mode
listing_offer.location_country
listing_offer.broker_description
```

Price condition:

```text
AMOUNT -> asking_price_amount + currency required
POA    -> asking_price_amount absent + currency absent
```

Missing values yield BLOCKED. No guessing/synthesis.

### 5.2 Build year

Current draft supports integer or omission only:

```text
present integer -> BuildYearClaim(VALUE_ASSERTION)
omitted -> MISSING_BUILD_YEAR
```

Omission MUST NOT become UNKNOWN.

### 5.3 Boat name

```text
draft concrete boat_name -> BoatNameClaim(VALUE_ASSERTION)
draft omission -> boat_name omitted
```

No fabricated ABSENT/UNKNOWN.

### 5.4 Location region

Concrete draft region maps to `LocationRegionClaim(VALUE_ASSERTION)`. Omission remains omission.

### 5.5 Offer

Map directly to existing NativeListingOfferSnapshot semantics. Decimal remains Decimal/lossless. Do not synthesize broker summary, description, history or VAT values.

## 6. Structured blockers

Minimum machine-readable blocker codes:

```text
MISSING_MARKETED_BRAND
MISSING_MODEL_DESIGNATION
MISSING_BUILD_YEAR
MISSING_ASKING_PRICE_MODE
MISSING_ASKING_PRICE_AMOUNT
MISSING_CURRENCY
MISSING_LOCATION_COUNTRY
MISSING_BROKER_DESCRIPTION
```

Blocker order MUST be deterministic.

## 7. Authorization

Readiness reuses current ProfessionalListingDraft Organization/Membership/MFA/PUBLISHER authorization and non-enumeration.

READY means mapping-ready, not publishing-authorized and not public.

The future promotion transaction MUST re-apply actual public NativeListing publishing eligibility at mutation time.

## 8. Browser behavior

Existing draft page exposes server-authoritative readiness.

READY must still show `Draft — not public`. BLOCKED lists actionable missing inputs.

No Publish button or promotion mutation endpoint is authorized.

## 9. Recovery

`listing_offer.broker_description` participates in accepted SLICE-0062 local recovery exactly like other bounded editable fields: exact browser form string, same scope/version/24h/stale semantics, no auth/session secret storage.

## 10. Public PhysicalBoat presentation

Current public PhysicalBoat claim projection may expose boat-name assertion state after the eight-field extension.

Hard:

```text
omitted != ABSENT != UNKNOWN != VALUE_ASSERTION
```

Concrete boat name is broker-declared PhysicalBoat truth, never BoatDesign truth. No listing becomes non-public because boat name is omitted.

## 11. Tests

Cover professional broker-description validation/persistence/rendering/recovery, owner-direct non-regression, boat-name claim states/migration/revision semantics, readiness READY/BLOCKED mapping, deterministic blocker order, lossless Decimal/region/name mapping, zero marketplace mutation, auth/non-enumeration and draft UI no-public/no-publish behavior.

## 12. Retained proof

Required real PostgreSQL 18 + FastAPI + built Astro proof demonstrates:

1. incomplete professional draft -> deterministic BLOCKED;
2. add required values including broker_description;
3. save/reload/recovery wiring for description;
4. draft -> READY;
5. exact typed candidate mapping;
6. present boat name -> VALUE_ASSERTION;
7. omitted boat name -> omitted;
8. marketplace truth row/state counts unchanged by readiness evaluation;
9. current claim path can persist/read/render boat-name VALUE_ASSERTION;
10. migrated historic seven-field claim reads boat name omitted;
11. wrong Organization cannot read another draft readiness;
12. owner-direct/draft-recovery retained behavior unchanged;
13. exact finish:

```text
PROFESSIONAL DRAFT PUBLICATION READINESS RESULT -> PASS
```

## 13. Explicitly out of scope

No draft promotion, PhysicalBoat/MarketEpisode/NativeListing creation, offer write caused by promotion, lifecycle transition, freshness, promoted ID, draft consumption, Publish/Withdraw/Reconfirm controls, explicit UNKNOWN build-year draft authoring, explicit ABSENT/UNKNOWN boat-name draft authoring, additional PhysicalBoat fields, media, leads/CRM, analytics, sale/outcome, Search changes, payments, owner-direct publication or pilot/public launch.

## 14. Trigger effects

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS = NOT_STARTED
PAID_BROKER_PLAN_STATUS = NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS = NOT_STARTED
```

No Mandatory Capability Register item changes state merely because 0064 is accepted.

## 15. Acceptance summary

```text
authorized ProfessionalListingDraft
+ complete bounded publication inputs
→ deterministic READY candidate mapping

incomplete draft
→ deterministic BLOCKED + actionable codes

both
→ zero marketplace promotion/mutation
```
