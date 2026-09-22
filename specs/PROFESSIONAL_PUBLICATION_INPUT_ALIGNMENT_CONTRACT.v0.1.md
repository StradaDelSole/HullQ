# HullQ Professional Publication Input Alignment Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0064 — Professional Publication Input Alignment  
**Depends on:** SLICE-0050 PhysicalBoat claims; SLICE-0054 shared seller draft payload; SLICE-0061 professional drafts; SLICE-0062 draft recovery  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This contract closes the two repository-proven data-shape gaps that currently prevent a later professional draft promotion from being specified losslessly:

1. `listing_offer.broker_description` is required by a real NativeListing offer but cannot currently be stored in the shared draft payload;
2. `physical_boat.boat_name` is already accepted in the shared draft payload but has no current PhysicalBoat claim persistence destination.

This contract does not implement promotion or publication.

## 2. Hard boundary

```text
draft alignment != marketplace promotion
draft alignment != NativeListing creation
draft alignment != publication
```

No SLICE-0064 API/UI action may create or mutate:

- PhysicalBoat from a draft;
- MarketEpisode from a draft;
- NativeListing from a draft;
- NativeListingOfferRevision from a draft;
- PhysicalBoatClaimRevision from a draft automatically;
- publication/freshness lifecycle;
- Search eligibility/results.

The new claim writer capability may be tested directly against explicit claim input, exactly like existing claim-writer tests.

## 3. Shared draft vocabulary

The accepted shared seller draft payload key set expands from nine to ten common keys by adding:

```text
listing_offer.broker_description
```

The field is common LISTING_OFFER input, not professional-only metadata.

Professional `broker_listing_reference` remains separate and professional-only.

### 3.1 Draft description validation

When present, `listing_offer.broker_description` MUST:

- be a string;
- be trimmed at the durable draft write boundary;
- remain non-empty after trimming;
- be treated as plain untrusted text;
- preserve internal punctuation/capitalization/newlines except where an existing shared draft text rule explicitly says otherwise.

Omission remains valid because drafts may be incomplete.

No synthetic/default description may be created.

### 3.2 Shared-channel behavior

Both current draft channels MUST round-trip the same common key with the same parser/serializer semantics:

- OwnerDirectListingDraft;
- ProfessionalListingDraft.

Adding this field MUST NOT weaken either channel's ownership/authorization/concurrency rules.

## 4. Professional draft UI and recovery

The existing professional edit surface MUST allow the broker to edit `listing_offer.broker_description`.

The existing browser-local recovery layer MUST treat its current unsaved form string exactly like the other bounded editable fields:

- exact unsaved string capture, including temporary empty string and whitespace while editing;
- same Account + Organization + ProfessionalListingDraft + server-version scope;
- same 24h expiry;
- same same-version restore;
- same stale-server conflict behavior;
- same storage-unavailable behavior;
- successful durable save clears matching recovery.

Server validation remains authoritative on explicit Save.

## 5. Owner-direct non-regression

Because the common draft payload is shared, OwnerDirectListingDraft persistence/API MUST accept and round-trip the same description field.

If the existing owner-direct browser edit form exposes all common fields, it MUST expose the description there too. If its UI intentionally remains a narrower accepted subset, the API/persistence still MUST NOT reject or drop the shared common field.

No owner-direct promotion/publication is introduced.

## 6. PhysicalBoat boat-name claim semantics

Extend the accepted PhysicalBoat claim domain/persistence with:

```text
physical_boat.boat_name
```

according to `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`.

Allowed assertion kinds:

```text
VALUE_ASSERTION
ABSENT
UNKNOWN
```

### 6.1 Value rules

For VALUE_ASSERTION:

- value MUST be a string;
- value MUST be non-empty/non-whitespace-only;
- persisted/read value MUST preserve the accepted text exactly unless an existing PhysicalBoat claim normalization rule applies.

For ABSENT or UNKNOWN:

- value MUST be null/None.

An omitted boat-name claim in a snapshot remains mechanically distinct from an explicit ABSENT or UNKNOWN claim.

### 6.2 Truth scope

Boat name is:

- PHYSICAL_BOAT truth;
- Organization-attributed broker claim;
- PUBLIC presentation;
- DISPLAY_ONLY;
- never BoatDesign/reference truth;
- never a Search criterion.

A BoatDesign name/model MUST NOT auto-fill the concrete boat name.

## 7. PhysicalBoat claim revision persistence

The existing immutable claim-revision model MUST remain one model.

Do not create a parallel boat-name claim table.

The current revision/head system MUST extend to carry optional:

```text
boat_name_assertion_kind
boat_name_value
```

or a mechanically equivalent representation.

Required preservation:

- immutable revisions;
- explicit current head per PhysicalBoat + claiming Organization;
- existing optimistic expected-head behavior;
- content hash/idempotency/conflict detection;
- predecessor link integrity;
- Organization isolation;
- existing seven claim fields unchanged.

Migration MUST preserve every existing claim revision/head.

## 8. Draft-to-claim mapping rule for later promotion

0064 does not execute promotion, but it fixes the later mapping contract:

```text
draft boat_name string present
→ later promotion may create BoatNameClaim(VALUE_ASSERTION, exact draft value)

draft boat_name absent
→ later promotion MUST NOT infer ABSENT or UNKNOWN
```

Explicit ABSENT/UNKNOWN capture remains a later UI/preflight decision.

## 9. Offer mapping rule for later promotion

0064 does not execute promotion, but establishes:

```text
draft listing_offer.broker_description present
→ later promotion may supply NativeListingOfferSnapshot.broker_description

draft listing_offer.broker_description absent
→ later promotion MUST fail preflight/incomplete rather than invent a description
```

Exact later promotion completeness/error UX remains outside this slice.

## 10. Public/read projection

PhysicalBoat claim readback objects MUST preserve boat-name assertion kind/value.

Any existing API serializer representing the full current PhysicalBoat claim snapshot SHOULD include the boat-name field consistently.

No new Search filter, ranking input, canonical URL component or SEO/indexation behavior is authorized.

## 11. Security and text handling

Both description and boat-name values are untrusted text.

They MUST NOT:

- be treated as HTML;
- alter authorization;
- contain or expose session/OIDC/MFA secrets;
- become database identifiers;
- become Search query syntax.

Existing Astro auto-escaping/raw-HTML prohibitions remain controlling.

## 12. Tests

At minimum cover:

### Shared draft

- common parser accepts broker_description;
- trims boundary whitespace for durable value;
- rejects non-string/blank;
- serializer round-trips;
- unknown-key fail-closed behavior remains;
- professional draft create/read/update round-trips description;
- owner-direct draft create/read/update round-trips description;
- optimistic version conflict remains unchanged.

### Recovery

- description participates in bounded capture/restore;
- unsaved empty/whitespace form state can survive recovery without changing server validation;
- storage failure/stale-version behavior remains unchanged.

### Boat-name claims

- VALUE_ASSERTION round-trip;
- ABSENT round-trip;
- UNKNOWN round-trip;
- invalid assertion/value pair rejected;
- omitted remains distinct from ABSENT/UNKNOWN;
- same revision-id/same envelope stays idempotent;
- conflicting same revision ID fails as before;
- expected-head concurrency remains;
- Organization isolation remains;
- migration preserves old revisions with boat-name fields absent.

### Non-regression

- current seven PhysicalBoat claim fields unchanged;
- NativeListingOffer semantics unchanged;
- no draft operation creates marketplace identities/truth;
- no Search behavior changes;
- owner-direct and professional authorization boundaries unchanged.

## 13. Retained proof

Required retained real PostgreSQL 18 + FastAPI + built Astro proof MUST demonstrate at least:

1. create/update/reopen a professional draft containing broker_description;
2. broker edit page visibly renders/reuses the value;
3. local recovery wiring includes the new field without auth leakage;
4. owner-direct API/persistence round-trips the shared field without publication;
5. write/read a PhysicalBoat claim revision with boat-name VALUE_ASSERTION;
6. write/read explicit ABSENT and UNKNOWN cases;
7. prove Organization-isolated current heads remain independent;
8. prove no PhysicalBoat/MarketEpisode/NativeListing/offer/publication state is created from either draft workflow merely by adding/saving the field;
9. run retained owner-direct/professional draft and PhysicalBoat-claim non-regression proofs as applicable.

## 14. Governance effect

SLICE-0064 changes no mandatory-register status and no trigger gate.

It creates repository-backed prerequisites for later lossless professional promotion.

```text
REQ_BROKER_023_STATUS = IMPLEMENTED
REQ_BROKER_024_STATUS = IMPLEMENTED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
```

## 15. Explicitly deferred

- draft→marketplace promotion transaction;
- automatic claim/offer writes from draft;
- generated marketplace IDs;
- publication/withdraw/reconfirm;
- required-response UNKNOWN/ABSENT collection UX beyond this field alignment;
- media;
- leads/CRM;
- outcomes/analytics;
- export/import;
- Search-fit;
- payment;
- production pilot/public launch.

## 16. Acceptance summary

```text
shared draft gains required broker_description
+ current PhysicalBoat claim writer gains boat_name destination
→ named promotion data-shape mismatch is closed
→ later promotion can be specified without dropping these accepted inputs
→ no marketplace promotion occurs in 0064
```
