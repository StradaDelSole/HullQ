# SLICE-0045 — NativeListing offer-facts persistence

**ID:** SLICE-0045  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** Native professional supply — first durable offer state  
**Depends on:** SLICE-0041, SLICE-0042, SLICE-0043, SLICE-0044  
**Blocks:** broker listing workspace / later publication, PhysicalBoat-fact persistence

## Objective

Given an already-persisted, authorized `NativeListing`, durably create and revise the listing-offer state defined by the nine `LISTING_OFFER` fields in `MARKETPLACE_FIELD_REGISTRY.v0.1`, preserving immutable revision history, exact broker-claim semantics and cross-Organization isolation.

This slice turns the accepted Gate-1 field contract into the first real mutable broker-listing data path. It does **not** create a generic marketplace fact framework and does **not** persist `PHYSICAL_BOAT` facts.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: persist and revise the offer-specific facts of an existing NativeListing.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one inspection command against PostgreSQL 18 that creates an authorized NativeListing, writes an initial offer revision, reads it back, performs a second price/location/text revision, proves the previous revision still exists, and proves an unauthorized/cross-Organization write changes nothing.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The 2026-09-02 Architecture Rebaseline and execution reconciliation supersede the older "do not build a native marketplace" language. Native professional listings are now the strategic market foundation, and supply must progress through bounded real capabilities. This slice is the smallest useful post-SLICE-0044 persistence step and avoids a generic 38-field framework.

## Why this slice exists

SLICE-0043 persists only the immutable NativeListing creation envelope. SLICE-0044 locks the marketplace field/claim semantics but intentionally adds no runtime persistence. HullQ still cannot durably store the actual offer a broker is publishing: asking price/POA, currency, location and broker narrative.

The next useful build step is therefore the `LISTING_OFFER` half of the accepted contract. These facts already have a durable subject (`NativeListingId`) and do not require inventing `PhysicalBoat` or `MarketEpisode` identity. Persisting PhysicalBoat technical facts before their subject/episode backbone exists would either collapse identity boundaries or force a generic framework first.

## Controlling artifacts

- Specifications:
  - `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
  - `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
  - `specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json`
- Accepted slice closures:
  - `docs/slices/SLICE-0043-acceptance-closure.md`
  - `docs/slices/SLICE-0044-acceptance-closure.md`
- Marketplace claim architecture:
  - `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md`
- Migration authority:
  - SLICE-0042 Alembic lineage; current accepted Alembic head is `1bb00df4a018`
- Publishing authorization:
  - accepted SLICE-0041 eligibility evaluator
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Post-SLICE-0039 execution reconciliation / precedence: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`
- Private-owner / public-supply policy: `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`

## In scope

- Typed runtime representation for one complete NativeListing offer revision covering exactly the nine v0.1 `LISTING_OFFER` fields:
  - `listing_offer.asking_price_mode`
  - `listing_offer.asking_price_amount`
  - `listing_offer.currency`
  - `listing_offer.location_country`
  - `listing_offer.location_region`
  - `listing_offer.broker_summary`
  - `listing_offer.broker_description`
  - `listing_offer.known_history_narrative`
  - `listing_offer.vat_tax_status_claim`
- PostgreSQL persistence through one new Alembic revision descended from `1bb00df4a018`.
- Immutable offer revisions linked to an existing `NativeListingId`.
- Exact current-revision pointer/state so a read does not depend on timestamps or "latest row wins" guessing.
- Optimistic concurrency for revision writes: a writer must name the expected current revision (or explicitly expect none for the first revision); stale writers fail closed with `CONFLICT` and write no new current state.
- Same-Organization publishing authorization using the real accepted SLICE-0041 eligibility boundary plus the persisted NativeListing publishing principal from SLICE-0043.
- Explicit writer Account attribution and durable server-side timestamp per revision.
- Idempotent retry/collision semantics for a client-supplied offer-revision identity.
- Typed readback of current offer revision and immutable revision history for owner inspection/audit.
- Validation of assertion-kind/value combinations and price conditionality required by SLICE-0044.
- Real PostgreSQL 18 integration tests.
- Owner inspection script proving the capability end-to-end.

## Explicitly out of scope

- any `PHYSICAL_BOAT` field persistence;
- PhysicalBoat creation/dedup/identity resolution;
- MarketEpisode persistence or continuity resolution;
- generic EAV / generic JSON marketplace-fact store;
- generic fact-resolution runtime for all 38 fields;
- public publication/lifecycle/freshness;
- buyer Search integration or ranking;
- buyer-facing price history or premium market analytics;
- FastAPI endpoint;
- Astro/React UI or broker workspace;
- media/photo/document upload;
- document verification;
- LLM extraction;
- bulk/CSV/XML/JSON/API/feed ingestion;
- VAT/legal verification or tax advice;
- Auth0/MFA/session implementation;
- Saved Search, monitoring, alerts or leads;
- SLICE-0046+ work.

## Required behavior

### 1. Subject and authorization boundary

The write target MUST already exist as a persisted SLICE-0043 NativeListing.

The writer request supplies the same authorization inputs used by the accepted publishing boundary:

```text
AccountId
candidate professional Organization
OrganizationMembership
NativeListingId
```

The real accepted SLICE-0041 evaluator MUST be called. A caller-supplied `authorized=true` or equivalent is forbidden.

In addition, the candidate Organization MUST equal the NativeListing's persisted `publishing_organization_id`.

Hard:

```text
eligible in Org A
+ NativeListing owned by Org B
-> DENIED / zero offer writes
```

A denied or missing-listing request writes zero revision/head rows.

### 2. Revision identity and immutable history

Introduce a runtime-distinct offer revision identity (name may vary, e.g. `NativeListingOfferRevisionId`). It MUST NOT be interchangeable with `NativeListingId`, `MarketEpisodeId`, `PhysicalBoatId` or other accepted marketplace identities.

Each successful revision is immutable business/audit history. Updating the current offer creates a new revision; prior revisions remain unchanged.

The database MUST have an explicit current/head relationship for each NativeListing. Current state MUST NOT be inferred solely by `MAX(created_at)`, row order or wall-clock timestamps.

This internal revision history exists for correctness/audit. It does not authorize a buyer-facing price-history product.

### 3. Optimistic concurrency

A revision write MUST carry an `expected_current_revision_id`:

```text
first revision:
expected_current_revision_id = NONE

later revision:
expected_current_revision_id = exact current revision id
```

If the expectation does not match durable current state:

```text
-> CONFLICT
-> zero new current state
-> existing current revision unchanged
```

No silent last-write-wins behavior.

### 4. Retry / collision semantics

The request supplies an explicit new offer-revision ID.

Same revision ID + same immutable semantic revision envelope:

```text
-> ALREADY_EXISTS
-> no duplicate revision
```

Same revision ID + different immutable semantic content or different NativeListing:

```text
-> CONFLICT
-> existing revision unchanged
```

The implementation must define deterministic handling when an idempotent retry arrives after the revision is no longer current; it may return `ALREADY_EXISTS` with current/head information, but MUST NOT silently recreate or re-promote the old revision.

### 5. Exact nine-field scope

The persisted offer snapshot is bounded to the nine `LISTING_OFFER` registry fields. Do not add convenience yacht specs, lifecycle, freshness or contact data.

Required fields/conditionality remain exactly as accepted in SLICE-0044:

```text
asking_price_mode = AMOUNT
-> asking_price_amount required
-> currency required

asking_price_mode = POA
-> no synthetic asking_price_amount
```

`broker_description` and `location_country` remain required responses.

Optional fields may be omitted. Omission MUST remain distinguishable from an explicit assertion such as `UNKNOWN`, `NOT_APPLICABLE` or `NO_KNOWN_HISTORY_DECLARED` where that assertion is permitted by the registry.

### 6. Assertion/value validity

Every supplied field claim MUST use only assertion kinds allowed by `MARKETPLACE_FIELD_REGISTRY.v0.1` and a value compatible with that field's `value_type`.

Examples:

```text
location_region UNKNOWN
-> valid, no invented region text

broker_summary NOT_APPLICABLE
-> valid, no fabricated summary

known_history_narrative NO_KNOWN_HISTORY_DECLARED
-> valid, but not equivalent to proven no history

vat_tax_status_claim UNKNOWN
-> valid, not VAT_PAID/VAT_NOT_PAID
```

Invalid assertion/value pairings fail before durable write.

Do not parse free text into structured facts.

### 7. Sensitive VAT claim boundary

`vat_tax_status_claim` remains a broker claim, `SENSITIVE`, and `DISPLAY_ONLY` in v0.1.

Persistence/readback MUST retain enough attribution to state that the claim came from the publishing Organization and was recorded by a specific Account at a specific time.

Hard:

```text
stored VAT_PAID broker claim
!= HullQ legal verification
```

This slice MUST NOT introduce `verified=true`, tax certification, evidence adjudication or searchable VAT filtering.

### 8. Typed values; no generic canonical blob

Use typed domain/persistence fields appropriate to this bounded offer snapshot. A generic canonical EAV/JSON blob for the nine facts is not acceptable merely for future extensibility.

JSON may be used only for non-authoritative diagnostics/inspection if needed; it must not become the durable canonical truth representation.

Money MUST avoid binary floating-point canonical storage/round-tripping.

Country/currency values must obey the accepted normalized code semantics; do not silently accept arbitrary free-text country names or lowercase/invalid code-shaped data as canonical values.

### 9. Transaction ownership / durability

Retain the SLICE-0043 durability invariant:

> a successful CREATED/UPDATED result must mean the new current offer revision is already durably committed independent of later caller action.

Do not repeat the pre-amendment SLICE-0043 nested-savepoint defect.

If using the same caller-supplied psycopg connection style, require a safely owned top-level transaction or fail closed before write. Do not silently commit/rollback unrelated caller work.

The revision row and current/head change MUST commit atomically.

### 10. Readback

Provide typed readback sufficient to retrieve:

- current offer revision for one NativeListing;
- exact revision identity;
- previous/current relationship;
- nine-field offer state with omitted-vs-explicit assertion distinctions preserved;
- publishing Organization attribution;
- writer Account attribution;
- durable recorded timestamp.

A missing NativeListing/current offer returns a typed not-found/none result; it must not invent default offer data.

### 11. Migration governance

Add exactly one Alembic revision descended from `1bb00df4a018`.

Do not modify legacy `001_initial_schema.sql` / `002_canonical_identity_schema.sql` and do not add a legacy `003_*.sql` migration.

Migration validation MUST assert the repository still has exactly one Alembic head and that an upgraded PostgreSQL 18 database reaches that head.

### 12. Owner-visible end-to-end proof

Provide one inspection command that uses a real PostgreSQL 18 database and demonstrates at minimum:

```text
eligible Org A + persisted NativeListing A
-> initial AMOUNT offer created
-> exact readback

same revision retry
-> ALREADY_EXISTS

second revision with expected current
-> current state changes
-> first revision still exists unchanged

stale expected revision
-> CONFLICT
-> current state unchanged

eligible Account/Org B attempting to edit listing A
-> DENIED
-> zero offer changes

POA revision
-> amount absent, no invented price

explicit UNKNOWN / NO_KNOWN_HISTORY_DECLARED examples
-> survive exact readback distinctly from omission

VAT claim
-> retained as broker-attributed unverified claim, not HullQ verification
```

The inspection ends with a single explicit PASS/FAIL result.

## Deliverables

- typed domain/runtime representation for the bounded NativeListing offer revision;
- one Alembic migration;
- PostgreSQL persistence create/revise/readback implementation;
- unit/contract tests;
- real PostgreSQL 18 integration/adversarial tests;
- owner inspection script;
- updated SLICE-0045 document status/handoff only.

## Acceptance criteria

- [x] Exactly the nine accepted `LISTING_OFFER` fields are persistable; no `PHYSICAL_BOAT` or unrelated marketplace field is added.
- [x] Writes require the real accepted SLICE-0041 eligibility decision and exact persisted NativeListing publishing Organization match.
- [x] Cross-Organization writes fail closed with zero durable offer changes.
- [x] Offer revisions are immutable and current/head state is explicit rather than timestamp-inferred.
- [x] Expected-current optimistic concurrency prevents silent lost updates.
- [x] Same revision ID/same content is idempotent; same ID/different content fails closed.
- [x] Price AMOUNT/POA conditionality is mechanically enforced with no synthetic price.
- [x] Optional omission remains distinct from explicit `UNKNOWN`, `NOT_APPLICABLE` and `NO_KNOWN_HISTORY_DECLARED` where allowed.
- [x] Assertion kinds/value types are validated against the locked v0.1 contract semantics.
- [x] Free text remains narrative and cannot auto-promote structured facts.
- [x] VAT/tax state remains attributed broker claim with no HullQ-verification implication and no search behavior.
- [x] Durable canonical representation is typed and not a generic EAV/JSON fact blob.
- [x] Successful writes are durably committed atomically with head changes; pre-existing caller transactions do not create nested-savepoint false success.
- [x] Exact typed readback preserves values, assertion states, revision identity, Organization/Account attribution and timestamps.
- [x] One Alembic migration descends from `1bb00df4a018`; repository/database each have exactly one resulting Alembic head.
- [x] Real PostgreSQL 18 tests cover first write, revision, immutable history, stale-write conflict, retry collision (same-listing and cross-listing) and cross-Organization isolation, plus the exact predecessor chain, composite-FK same-listing integrity, NULL-hole/non-finite CHECK-constraint adversarial cases, equivalent-Decimal-representation idempotency, distinct-high-precision-Decimal CONFLICT, and (this amendment) locale-independent non-blank text rejection (tab/newline, U+00A0 NO-BREAK SPACE, U+001C-U+001F information separators) plus a direct COLLATE "C" vs. default-collation agreement proof. — NOT executed locally in this session (local `postgres` superuser credentials unavailable — `pg_hba.conf` requires `scram-sha-256`, and this session confirmed it cannot reload PostgreSQL config without Windows service-control/admin rights, so this is a structural block, not merely an unknown password). Verified instead by observing the pushed branch's GitHub Actions `db-integration` job on the exact final HEAD (see completion report for the exact run link).
- [x] Owner inspection ends `PASS` and demonstrates the required end-to-end cases. — Actually executed against real PostgreSQL 18 and observed ending `NATIVE LISTING OFFER FACTS RESULT -> PASS` on intermediate runtime HEAD `4fa6da1` (CI run https://github.com/StradaDelSole/HullQ/actions/runs/33926347812). This third amendment (locale-independent non-blank-text predicate) does not touch any scenario the script exercises — it uses only ordinary, unambiguously non-blank text throughout — so per explicit reviewer direction that evidence remains valid and was not repeated.
- [x] Full repository test/quality/security gates pass. (full suite locally: 4033 passed/295 skipped; ruff format/check; mypy; repository validation; `uv lock --check`; `pip-audit`; CI `quality`/`dependency audit` jobs)
- [x] GitHub Actions CI passes on the exact final implementation HEAD.
- [x] Manufacturer artifact reproducibility passes on the exact final implementation HEAD.
- [ ] Independent exact-head review finds no unresolved material issue.
- [ ] Project Owner explicitly accepts the exact reviewed HEAD before merge.

## Expected touch points

Expected only where needed:

- `src/hullq/domain/...` for the bounded typed offer revision/value representation;
- `src/hullq/persistence/...` for NativeListing offer persistence;
- `alembic/versions/<new>_native_listing_offer_facts.py`;
- `tests/unit/...` / `tests/contract/...` / `tests/integration/...`;
- `scripts/inspect_native_listing_offer_facts.py`;
- this slice document.

No FastAPI, Astro/React, media or PhysicalBoat files are expected.

## Validation

```bash
uv run python scripts/inspect_native_listing_offer_facts.py
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
uv lock --check
uv run pip-audit
```

PostgreSQL integration/inspection requires `HULLQ_TEST_DATABASE_URL` and PostgreSQL 18.

Remote exact-head gates:

```text
CI
Manufacturer artifact reproducibility
```

## Stop conditions

Stop and report instead of inventing a solution when:

- implementation requires `PHYSICAL_BOAT` or MarketEpisode persistence;
- the nine-field registry contract cannot be represented without changing accepted 0044 semantics;
- authorization would require bypassing/replacing the accepted SLICE-0041 evaluator;
- existing NativeListing persistence cannot be safely composed without weakening SLICE-0043 transaction/durability guarantees;
- a generic marketplace EAV/JSON framework becomes necessary merely to make this slice work;
- a new external service/dependency is required;
- VAT/legal verification or other sensitive-claim adjudication would be needed;
- public lifecycle/freshness/API/UI must be added to make the capability pass.

## Status handoff rule

The implementation agent may recommend `REVIEW` or `BLOCKED`, but MUST NOT mark the slice `DONE`.

Any implementation HEAD change after review resets exact-head acceptance and remote-gate verification.

`DONE` requires independent exact-head review, explicit Project Owner acceptance, protected merge, acceptance closure, closure merge and successful local `FINISH_SLICE.bat`.

## Required completion report

Use the exact completion-report structure in `docs/slices/SLICE_TEMPLATE.md`. Keep it concise and report the exact final branch HEAD SHA. Do not merge, mark `DONE`, or start SLICE-0046 automatically.
