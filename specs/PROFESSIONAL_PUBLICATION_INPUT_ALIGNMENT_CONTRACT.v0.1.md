# HullQ Professional Publication Input Alignment Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0065 — Professional Publication Input Alignment  
**Depends on:** SLICE-0050 PhysicalBoat claims; SLICE-0061 ProfessionalListingDraft; SLICE-0062 professional recovery; SLICE-0064 professional inventory lifecycle controls  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This contract closes the two repository-proven data-shape gaps that currently prevent a later professional draft promotion from being specified losslessly:

1. `listing_offer.broker_description` is required by a real NativeListing offer but cannot currently be stored in ProfessionalListingDraft;
2. `physical_boat.boat_name` is already accepted in ProfessionalListingDraft's common payload but has no current PhysicalBoat claim persistence destination.

This contract does not implement promotion or publication.

## 2. Hard boundary

```text
publication-input alignment != marketplace promotion
publication-input alignment != NativeListing creation
publication-input alignment != publication
```

No SLICE-0065 draft API/UI action may create or mutate marketplace truth from a draft.

## 3. Shared seller vocabulary remains unchanged

The nine common owner-direct/professional draft keys remain exactly the current shared set.

SLICE-0065 MUST NOT add `listing_offer.broker_description` to OwnerDirectListingDraft.

The accepted Owner-Direct v0.1 rule that broker-specific narrative fields are not repurposed for private sellers remains in force.

## 4. Professional-only offer input

ProfessionalListingDraft gains one additional bounded pre-market offer input:

```text
listing_offer.broker_description
```

This field is distinct from:

- the nine shared common draft keys;
- professional-only metadata `broker_listing_reference`;
- accepted marketplace truth.

It is professional-only because the existing owner-direct contract explicitly does not reuse broker-specific narrative fields.

### 4.1 Validation

When durably present, broker_description MUST:

- be a string;
- be trimmed at the professional-draft write boundary;
- remain non-empty after trimming;
- contain at most 10,000 Unicode code points;
- reject Unicode control characters in category `Cc`;
- be treated as untrusted plain text.

Omission remains valid for an incomplete draft.

No synthetic/default/derived description may be created.

### 4.2 Persistence and API

Professional create/read/update MUST round-trip the field.

The wire key MUST remain exactly:

```text
listing_offer.broker_description
```

Implementation may use a dedicated nullable column or equivalent professional-only bounded persistence representation.

Owner-direct persistence/API MUST remain unchanged.

## 5. Professional draft UI and recovery

The existing professional edit surface MUST allow editing broker_description.

The existing SLICE-0062 browser-local recovery layer MUST include its unsaved form string under exactly the same:

- Account + Organization + ProfessionalListingDraft scope;
- server base-version semantics;
- 24h maximum age;
- same-version restore;
- stale-server conflict behavior;
- storage availability/write failure behavior;
- successful-save clearing behavior.

Recovery may temporarily preserve empty/whitespace form strings before server validation, exactly like other editable controls.

## 6. PhysicalBoat boat-name claim semantics

Extend the accepted PhysicalBoat claim domain/persistence with:

```text
physical_boat.boat_name
```

Allowed assertion kinds, matching the field registry:

```text
VALUE_ASSERTION
ABSENT
UNKNOWN
```

### 6.1 Value rules

For VALUE_ASSERTION:

- value MUST be a string;
- value MUST be non-empty/non-whitespace-only.

For ABSENT or UNKNOWN:

- value MUST be null/None.

An omitted boat-name claim remains mechanically distinct from explicit ABSENT or UNKNOWN.

The implementation MAY extend the existing shared `AssertionKind` vocabulary with `ABSENT` rather than create an incompatible parallel assertion-kind concept. If it does, every pre-existing per-field allowed-kind set MUST remain authoritative: adding the enum token MUST NOT make `ABSENT` valid for any existing LISTING_OFFER or PhysicalBoat field whose registry semantics do not allow it.

### 6.2 Truth scope

Boat name is:

- PHYSICAL_BOAT truth;
- Organization-attributed broker claim;
- PUBLIC presentation;
- DISPLAY_ONLY;
- never BoatDesign/reference truth;
- never a Search criterion.

A BoatDesign model/name MUST NOT auto-fill the concrete boat name.

## 7. PhysicalBoat claim revision persistence

The existing immutable claim-revision model MUST remain one model.

Do not create a parallel boat-name table.

The current revision/head system MUST extend to carry optional boat-name assertion kind/value or a mechanically equivalent representation.

Required preservation:

- immutable revisions;
- explicit current head per PhysicalBoat + claiming Organization;
- expected-current-head concurrency;
- content-hash/idempotency/conflict detection;
- predecessor link integrity;
- Organization isolation;
- existing seven claim fields unchanged.

Migration MUST preserve all existing claim revisions and heads.

### 7.1 Pre-0065 idempotency compatibility

Existing `content_hash` values are durable idempotency evidence. Adding an optional boat-name field MUST NOT make an exact retry of a pre-0065 revision appear to be different content merely because the newer runtime snapshot has `boat_name = None`.

After migration:

```text
pre-0065 stored revision
+ exact same revision ID
+ exact same predecessor
+ exact same original seven-field content
+ boat_name omitted
→ ALREADY_EXISTS / exact-retry outcome
→ never CONFLICT solely because the schema gained boat_name
```

Implementation may preserve the old fingerprint envelope for omitted boat name or use another mechanically proven compatible strategy, but MUST NOT silently invalidate historical retry semantics.

A revision that actually asserts a boat-name value/ABSENT/UNKNOWN MUST participate in the immutable content fingerprint so a same revision ID with different boat-name content conflicts normally.

## 8. Later draft-to-claim mapping rule

SLICE-0065 does not execute promotion.

It establishes only:

```text
professional draft boat_name string present
→ later promotion may create BoatNameClaim(VALUE_ASSERTION, exact accepted draft value)

professional draft boat_name absent
→ later promotion MUST NOT infer ABSENT or UNKNOWN
```

Explicit ABSENT/UNKNOWN capture remains a later publication/preflight decision.

## 9. Later offer mapping rule

SLICE-0065 does not execute promotion.

It establishes:

```text
professional draft broker_description present
→ later promotion may supply NativeListingOfferSnapshot.broker_description

professional draft broker_description absent
→ later promotion MUST fail preflight/incomplete rather than invent a description
```

## 10. Public/read projection

PhysicalBoat claim readback objects MUST preserve boat-name assertion kind/value.

Any current API serializer representing the complete accepted current PhysicalBoat claim snapshot SHOULD include boat-name state consistently.

No Search filter/ranking, canonical URL or indexation change is authorized.

## 11. Security and text handling

Description and boat-name values are untrusted text.

They MUST NOT:

- be treated as HTML;
- alter authorization;
- contain/expose session/OIDC/MFA secrets;
- become database identity;
- become Search query syntax.

## 12. Tests

At minimum cover:

### Professional draft

- broker_description accepted under exact wire key;
- trims boundary whitespace;
- rejects non-string/blank/control-character/over-limit content;
- create/read/update round-trip;
- stale version remains zero-mutation conflict;
- unknown keys still fail closed;
- broker_listing_reference semantics unchanged;
- owner-direct rejects/accepts no new field exactly as before and its retained proof remains green.

### Recovery

- broker_description participates in capture/restore;
- temporary unsaved empty/whitespace state can be recovered before authoritative Save validation;
- stale-version/storage-failure behavior remains unchanged.

### Boat-name claims

- VALUE_ASSERTION round-trip;
- ABSENT round-trip;
- UNKNOWN round-trip;
- invalid assertion/value combinations rejected;
- omitted remains distinct from ABSENT/UNKNOWN;
- same revision-id/same envelope idempotency remains;
- conflicting same revision ID remains conflict;
- expected-head concurrency remains;
- Organization isolation remains;
- migration preserves old revisions with boat-name fields absent;
- exact retry of a pre-0065 revision after migration still returns the existing idempotent/already-exists outcome;
- a new revision's boat-name assertion participates in conflict/idempotency fingerprinting.

### Non-regression

- existing seven PhysicalBoat claim fields unchanged;
- NativeListingOffer semantics unchanged;
- no professional draft operation creates marketplace identities/truth;
- owner-direct behavior unchanged;
- Search behavior unchanged;
- SLICE-0064 Publish/Withdraw/Reconfirm behavior unchanged.

## 13. Retained proof

Required retained real PostgreSQL 18 + FastAPI + built Astro proof MUST demonstrate at least:

1. create/update/reopen a professional draft containing broker_description;
2. broker edit page visibly renders/reuses the value;
3. local recovery wiring includes the new field without auth leakage;
4. owner-direct retained proof remains unchanged/green;
5. write/read a PhysicalBoat claim revision with boat-name VALUE_ASSERTION;
6. write/read explicit ABSENT and UNKNOWN cases;
7. prove Organization-isolated current heads remain independent;
8. prove professional draft saves create no PhysicalBoat/MarketEpisode/NativeListing/offer/claim/publication state;
9. exact retry compatibility for a pre-migration seven-field claim revision;
10. run retained professional draft, PhysicalBoat-claim and SLICE-0064 lifecycle non-regression proofs;
11. exact finish:

```text
PROFESSIONAL PUBLICATION INPUT ALIGNMENT RESULT -> PASS
```

## 14. Governance effect

SLICE-0065 changes no mandatory-register status and no trigger gate.

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
- publication;
- owner-direct narrative vocabulary changes;
- required-response UNKNOWN/ABSENT collection UX beyond this field alignment;
- media;
- leads/CRM;
- outcomes/analytics;
- export/import;
- Search-fit;
- buyer Saved Search / price-change alert implementation;
- payment;
- production pilot/public launch.

## 16. Acceptance summary

```text
professional draft gains required broker_description input
+ current PhysicalBoat claim writer gains boat_name destination
→ named professional promotion data-shape mismatch is closed
→ OwnerDirectListingDraft remains unchanged
→ no marketplace promotion occurs in SLICE-0065
```
