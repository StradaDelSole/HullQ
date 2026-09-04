# SLICE-0045 — Acceptance closure

**Slice:** SLICE-0045  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #143  
**Accepted implementation HEAD:** `2b2027136ad739a0e2b6c6fe02b1c72b9d024287`  
**Implementation merge commit:** `cf21f5c97237ff8b4abc0c0025d67b98c0945423`  
**Independent final ACCEPT review:** `5118754934`  
**Owner acceptance:** explicitly recorded 2026-09-05

## Accepted capability

SLICE-0045 is the first durable mutable offer-state path for HullQ native professional inventory.

Given an already-persisted and authorized SLICE-0043 `NativeListing`, the accepted implementation can durably create and revise exactly the nine accepted `LISTING_OFFER` fields from `MARKETPLACE_FIELD_REGISTRY.v0.1` while preserving immutable revision history, exact broker-claim semantics, optimistic concurrency and cross-Organization isolation.

Accepted capability:

```text
existing authorized NativeListing
        ↓
write bounded offer revision
        ↓
PostgreSQL durable immutable revision
        ↓
explicit current/head pointer
        ↓
typed exact readback + immutable history
```

This slice deliberately does not persist `PHYSICAL_BOAT` facts and does not create a generic marketplace fact/EAV/JSON framework.

## Accepted nine-field scope

The accepted durable offer snapshot is bounded to exactly:

```text
listing_offer.asking_price_mode
listing_offer.asking_price_amount
listing_offer.currency
listing_offer.location_country
listing_offer.location_region
listing_offer.broker_summary
listing_offer.broker_description
listing_offer.known_history_narrative
listing_offer.vat_tax_status_claim
```

No PhysicalBoat specifications, lifecycle/freshness, media, contact data, public publication state, buyer search integration or generic marketplace-fact substrate were added.

## Authorization and Organization boundary

Every write uses the accepted SLICE-0041 publishing-eligibility evaluator and the persisted SLICE-0043 NativeListing publishing principal.

Hard accepted behavior:

```text
eligible publisher in Org A
+ NativeListing owned by Org A
-> may write offer revision

eligible publisher in Org B
+ NativeListing owned by Org A
-> denied
-> zero offer mutation
```

A caller-supplied boolean authorization shortcut is not accepted.

Missing listings, ineligible memberships and cross-Organization writes fail closed before durable offer mutation.

## Immutable revision model

Offer state is revisioned rather than overwritten in place.

Each successful write creates one immutable `native_listing_offer_revisions` row. The database separately stores an explicit current/head pointer per NativeListing in `native_listing_offer_heads`.

Hard accepted rule:

```text
current offer != MAX(recorded_at)
current offer != latest timestamp guess
current offer = explicit durable head relationship
```

Every accepted revision also persists its exact predecessor relationship:

```text
first revision A:
A.previous_offer_revision_id = NULL

second revision B:
B.previous_offer_revision_id = A

third revision C:
C.previous_offer_revision_id = B
```

The predecessor chain is durable audit history and is never reconstructed from timestamps.

## Same-listing database integrity

The accepted migration enforces same-NativeListing identity for both current-head and predecessor references.

Composite database constraints ensure that a valid row cannot express:

```text
NativeListing A
-> current head points to revision of NativeListing B
```

or:

```text
revision for NativeListing A
-> predecessor points to revision of NativeListing B
```

This invariant is enforced in PostgreSQL, not merely assumed from application behavior.

## Optimistic concurrency

Every revision write carries an `expected_current_revision_id`.

Accepted behavior:

```text
first revision:
expected current = NONE

later revision:
expected current = exact durable head
```

If durable current state differs from the expectation:

```text
-> CONFLICT
-> no new current state
-> existing head unchanged
```

There is no silent last-write-wins behavior.

The implementation locks the always-existing parent NativeListing row before head/revision mutation so two concurrent first-time writers for the same listing cannot both succeed.

## Revision-ID retry and collision semantics

Client-supplied offer-revision identity is globally collision-safe.

Accepted semantics:

```text
same revision ID
+ same immutable semantic revision envelope
-> ALREADY_EXISTS
-> no duplicate

same revision ID
+ different content
-> CONFLICT

same revision ID
+ different NativeListing
-> CONFLICT
```

Cross-listing races use an `INSERT ... ON CONFLICT DO NOTHING`-style safe path followed by exact comparison so an ordinary uniqueness exception is not exposed as business behavior.

A retry of a superseded historical revision does not silently re-promote that revision as current.

## Price and Decimal semantics

Accepted price conditionality remains exactly:

```text
asking_price_mode = AMOUNT
-> asking_price_amount required
-> currency required

asking_price_mode = POA
-> amount absent
-> currency absent
-> no synthetic price
```

Money is stored using PostgreSQL `NUMERIC` / Python `Decimal`, not binary floating point.

Non-finite values are rejected:

```text
NaN
Infinity
-Infinity
```

The accepted semantic fingerprint canonicalization is lossless and independent of the ambient Decimal context. It is derived from `Decimal.as_tuple()` and removes only semantically irrelevant trailing coefficient zeros while preserving exact value/sign/exponent semantics.

Therefore:

```text
Decimal("125000.00")
Decimal("125000")
Decimal("1.25E+5")
```

are idempotently equivalent, while genuinely distinct high-precision values remain distinct even beyond the default Decimal context precision.

## Assertion-kind and omission semantics

The implementation preserves SLICE-0044 claim semantics for the bounded offer fields.

Omission remains distinct from explicit assertion state.

Representative accepted distinctions:

```text
location_region omitted
!= location_region UNKNOWN

broker_summary omitted
!= broker_summary NOT_APPLICABLE

known_history_narrative omitted
!= NO_KNOWN_HISTORY_DECLARED
!= UNKNOWN
```

The database CHECK constraints explicitly enumerate valid `(assertion_kind, value)` states and close SQL three-valued-logic NULL gaps.

Hard accepted invariant:

```text
kind = NULL
+ hidden non-NULL durable value
-> invalid database state
```

Values are not silently discarded by typed readback.

## DB-valid implies typed-readback-valid for bounded text

The final amendment closes the non-blank text boundary consistently across Python and PostgreSQL.

The domain uses Python `str.strip()` semantics. The database therefore uses an explicit deterministic enumeration of the 29 Unicode code points Python 3.14 treats as whitespace, rather than locale-dependent PostgreSQL POSIX whitespace classes.

This is applied to:

```text
broker_description
location_region_value when VALUE_ASSERTION
broker_summary_value when VALUE_ASSERTION
known_history_narrative_value when VALUE_ASSERTION
```

The accepted invariant is:

```text
every DB-valid persisted offer row
-> reconstructable by the accepted typed domain model
```

Adversarial PostgreSQL tests cover ordinary whitespace, tab/newline-only text, U+00A0 NO-BREAK SPACE, U+001E from the U+001C..U+001F information-separator range, and default-collation vs explicit `COLLATE "C"` agreement.

## Sensitive VAT boundary

`vat_tax_status_claim` remains an attributed broker claim.

Hard accepted rule:

```text
stored VAT_PAID broker claim
!= HullQ legal verification
```

The revision retains publishing Organization, recording Account and durable timestamp attribution.

SLICE-0045 does not add VAT verification, tax certification, evidence adjudication or searchable VAT filtering.

## Transaction ownership and durability

The accepted implementation preserves the SLICE-0043 transaction-ownership rule.

A successful create/revise result means the revision and current-head change are already durably committed as one top-level transaction independent of later caller action.

A caller connection already inside an unrelated transaction fails closed rather than silently nesting work in a savepoint and returning false success.

Hard accepted behavior:

```text
revision insert
+ head update
-> one atomic durable transaction
```

## Accepted readback

Typed persistence APIs support:

```text
fetch current offer revision for a NativeListing
fetch an exact historical offer revision
list immutable offer revisions
```

Readback retains:

- exact offer-revision identity;
- exact predecessor relationship;
- all nine bounded offer fields;
- omitted-vs-explicit assertion distinctions;
- publishing Organization attribution;
- recording Account attribution;
- durable server-side timestamp.

A missing offer returns no invented defaults.

## Migration governance

The accepted implementation adds one Alembic migration:

```text
4d8e1a72c9f0_native_listing_offer_facts
```

It descends from:

```text
1bb00df4a018
```

The repository retains one Alembic head. Legacy SQL migration files were not repurposed.

A pre-existing SLICE-0043 baseline integration test was correctly pinned to the exact `1bb00df4a018` revision so its historical assertion remains stable after this later Alembic head was introduced.

## Owner-visible proof

The standalone owner inspection script is:

```text
uv run python scripts/inspect_native_listing_offer_facts.py
```

The script was actually executed against PostgreSQL 18 during the implementation review process on intermediate runtime HEAD:

```text
4fa6da10de87568defa3502bc4ac846bb059aaeb
```

GitHub Actions run:

```text
33926347812
```

Observed terminal result:

```text
NATIVE LISTING OFFER FACTS RESULT -> PASS
```

This proof remains valid for the final accepted implementation because subsequent changes after that runtime proof only hardened scenarios outside the script's ordinary inputs or removed the temporary CI invocation/documented the result; the reviewer explicitly examined this reuse before final acceptance.

## Exact-head external verification

Final accepted implementation HEAD:

```text
2b2027136ad739a0e2b6c6fe02b1c72b9d024287
```

GitHub Actions on this exact HEAD:

```text
CI run                         33930446119     SUCCESS
Manufacturer reproducibility  33930446223     SUCCESS
```

The CI PostgreSQL 18 integration job executed:

```text
293 passed
```

including the final adversarial persistence cases.

Ubuntu and Windows quality jobs passed. Dependency audit passed. Manufacturer-artifact reproducibility passed on Ubuntu and Windows.

## Independent review history

SLICE-0045 was not accepted on implementer report alone.

Independent review materially hardened the implementation before acceptance.

### Review round 1 — AMEND

Review:

```text
5118027715
```

Material findings closed:

1. Persist exact predecessor relationship rather than discarding expected-current after OCC validation.
2. Enforce same-NativeListing current-head/revision and predecessor/revision integrity in PostgreSQL.
3. Make cross-listing global revision-ID collision handling race-safe and return deterministic `CONFLICT` rather than exposing uniqueness exceptions.
4. Close SQL assertion-kind/value NULL holes caused by three-valued logic.
5. Canonicalize numerically equivalent Decimal prices before fingerprinting.
6. Reject non-finite money.

### Review round 2 — AMEND

Review:

```text
5118438973
```

Material findings closed:

1. Replace context-sensitive `Decimal.normalize()` canonicalization with lossless/context-independent semantic canonicalization.
2. Align database non-blank text semantics with typed domain readback rather than allowing DB-valid whitespace-only rows the domain rejects.

### Review round 3 — AMEND

Review:

```text
5118553409
```

Material finding closed:

- Replace locale-dependent PostgreSQL POSIX `\S` classification with deterministic explicit Python-whitespace codepoint semantics so the DB/domain invariant does not change with collation/`LC_CTYPE`.

### Final exact-head review — ACCEPT

Final independent ACCEPT review:

```text
5118754934
```

Exact reviewed HEAD:

```text
2b2027136ad739a0e2b6c6fe02b1c72b9d024287
```

No unresolved material issue remained.

## Owner acceptance

The Project Owner explicitly accepted SLICE-0045 on 2026-09-05 after the final independent exact-head ACCEPT.

The implementation PR was then merged with expected-head protection, so the accepted reviewed commit could not silently move before merge.

Implementation merge commit:

```text
cf21f5c97237ff8b4abc0c0025d67b98c0945423
```

## Explicitly still out of scope after closure

Acceptance of SLICE-0045 does not imply implementation of:

- `PHYSICAL_BOAT` creation or fact persistence;
- MarketEpisode persistence/continuity;
- listing lifecycle/freshness/publication;
- FastAPI listing endpoints;
- Astro/React broker workspace;
- media/photo/document upload;
- buyer search/ranking over native inventory;
- buyer-facing price-history analytics;
- generic marketplace-fact EAV/JSON infrastructure;
- LLM extraction;
- feed/syndication ingestion;
- Saved Search, monitoring, alerts or leads;
- SLICE-0046+ work.

## Closure decision

```text
SLICE-0045
= exact implementation reviewed
= material findings amended on same branch
= final exact-head CI/repro green
= PostgreSQL 18 persistence proof green
= owner inspection PASS evidence accepted
= independent exact-head ACCEPT
= explicit Project Owner Acceptance
= implementation merged with expected-head protection
= OWNER_ACCEPTED
```

SLICE-0045 is ready for formal closure merge. The next slice must be selected only after the normal post-slice architecture/product reassessment; no later slice is implicitly authorized by this closure.
