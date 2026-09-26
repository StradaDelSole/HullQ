# HullQ — Listing Draft Assertion Response Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Selected capability:** SLICE-0066 — Required-Response / Assertion Input Alignment  
**Applies to:** shared OwnerDirectListingDraft / ProfessionalListingDraft common payload  
**Primary field:** `physical_boat.build_year`

## 1. Purpose

This contract adds one truthful required-response representation to the existing shared nine-key draft payload without creating marketplace truth or a generalized assertion framework for unrelated fields.

The exact problem is:

```text
Marketplace registry:
physical_boat.build_year
= REQUIRED_RESPONSE
= VALUE_ASSERTION(year) | UNKNOWN

Current draft layer:
physical_boat.build_year
= integer | omitted
```

Draft omission must remain different from an explicit UNKNOWN response.

## 2. Key-set invariant

The shared common draft key set remains exactly nine keys.

No key is added, removed or renamed.

`physical_boat.build_year` remains the exact wire key. Only its accepted/canonical value shape changes.

## 3. Three mechanically distinct draft states

The shared draft layer MUST preserve:

```text
OMITTED
!= UNKNOWN
!= VALUE_ASSERTION(year)
```

### 3.1 Omitted

The key is absent:

```json
{}
```

Meaning: no build-year response has yet been supplied in this incomplete draft.

Omission MUST NOT be interpreted, persisted or promoted as UNKNOWN.

### 3.2 Explicit UNKNOWN

Canonical form:

```json
{
  "physical_boat.build_year": {
    "assertion_kind": "UNKNOWN"
  }
}
```

Meaning: the draft author explicitly answered that the build year is unknown.

The object MUST NOT contain a `value` member.

### 3.3 VALUE_ASSERTION

Canonical form:

```json
{
  "physical_boat.build_year": {
    "assertion_kind": "VALUE_ASSERTION",
    "value": 1987
  }
}
```

The value uses the already-accepted build-year integer semantics. Boolean remains invalid. SLICE-0066 does not invent a new calendar-year range constraint.

## 4. Strict object shape

For the canonical structured response:

- `assertion_kind` is required;
- accepted kinds are exactly `VALUE_ASSERTION` and `UNKNOWN`;
- unknown assertion kinds fail closed;
- extra object keys fail closed;
- VALUE_ASSERTION requires exactly one `value` member satisfying the existing integer/not-bool rule;
- UNKNOWN forbids `value`, including `"value": null`;
- a JSON null build-year response is invalid; omission is represented only by absence of the field key.

This is draft-input assertion-response syntax. It does not itself create a PhysicalBoatClaimSnapshot.

## 5. Legacy integer compatibility

Pre-SLICE-0066 drafts and callers may contain the historical form:

```json
{
  "physical_boat.build_year": 1987
}
```

The shared parser MUST continue to accept this exact legacy integer value and normalize it internally to the same semantic state as:

```json
{
  "physical_boat.build_year": {
    "assertion_kind": "VALUE_ASSERTION",
    "value": 1987
  }
}
```

Legacy integer compatibility is read/ingress compatibility, not the canonical future representation.

New canonical serialization emitted by the shared draft serializer MUST use the structured object.

A legacy persisted JSONB row does not require a bulk data migration merely to remain readable. A normal successful draft write may naturally persist the canonical structured serialization.

## 6. Shared implementation primitive

OwnerDirectListingDraft and ProfessionalListingDraft MUST continue to use one channel-neutral parser/serializer for the common nine-key payload.

Implementation should introduce one small reusable draft assertion-response type sufficient for build_year semantics.

It MUST NOT generalize every common draft field into assertion objects in this slice.

The shared build-year type should expose enough typed state that code cannot confuse omitted, UNKNOWN and VALUE_ASSERTION.

## 7. API and persistence behavior

Both owner-direct and professional create/read/update paths inherit identical build-year behavior from the shared primitive.

Required behavior:

- existing persisted legacy integer drafts remain readable;
- existing API requests using legacy integer build year remain accepted for compatibility;
- API responses use canonical structured build-year representation;
- new/updated JSONB payload serialization uses canonical structured form;
- optimistic draft versioning remains unchanged;
- no database schema/Alembic migration is required solely for this JSON value-shape evolution;
- unknown top-level draft keys still fail closed;
- all non-build-year common field semantics remain unchanged.

## 8. Browser UX

Both owner-direct and professional draft editors MUST let the user represent all three states without ambiguity:

```text
not answered
known year
explicitly unknown
```

The UI MUST NOT convert a blank year field into UNKNOWN.

The UI MUST NOT require a guessed year.

When UNKNOWN is selected, no year value may be submitted as part of that response.

When a concrete year is selected/entered, canonical request semantics are VALUE_ASSERTION(year).

Exact visual control choice is implementation detail as long as these states are clear and keyboard/mobile usable.

## 9. Professional local recovery

The existing professional recovery envelope remains a browser-local form recovery mechanism, not draft truth.

Recovery MUST preserve enough form state to distinguish:

- unanswered build year;
- explicit UNKNOWN;
- concrete entered year.

Same-version/stale/expiry/isolation rules from `PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md` remain unchanged.

Recovery MUST NOT infer UNKNOWN from an empty recovered year string.

## 10. Marketplace alignment

The canonical draft states map later as follows, but SLICE-0066 performs no promotion:

```text
draft VALUE_ASSERTION(year)
→ later promotion may construct BuildYearClaim(VALUE_ASSERTION, year)

draft UNKNOWN
→ later promotion may construct BuildYearClaim(UNKNOWN)

draft OMITTED
→ not promotion-ready for required build-year response
→ must not infer UNKNOWN
```

That later materialization belongs to the owning promotion slice.

## 11. Non-goals

SLICE-0066 does not:

- create PhysicalBoat, MarketEpisode or NativeListing;
- create PhysicalBoat claim revisions;
- create NativeListing offer revisions;
- implement PROMOTION_READY;
- implement promotion;
- publish listings;
- change Marketplace field-registry requiredness/assertion kinds;
- modify `physical_boat.boat_name` semantics;
- convert asking-price/location/string fields to assertion objects;
- add Search criteria;
- add media, leads, outcomes, analytics, import/export or alerts.

## 12. Compatibility invariant

After implementation:

```text
shared common key count = 9

legacy integer build year
→ readable

canonical structured VALUE_ASSERTION
→ readable + writable

canonical structured UNKNOWN
→ readable + writable

omitted build year
→ still omitted

OMITTED != UNKNOWN != VALUE_ASSERTION
```

No accepted owner-direct/professional ownership, authorization, concurrency or recovery isolation rule changes.
