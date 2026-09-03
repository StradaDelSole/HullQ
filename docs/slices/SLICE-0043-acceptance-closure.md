# SLICE-0043 — Acceptance closure

**Slice:** SLICE-0043  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #136  
**Accepted implementation HEAD:** `3e9fadf0b54a07d6b8b9926ebaaff65cedd3cddb`  
**Implementation merge commit:** `a4cacd10f1dd7fb387b203e9b2f394195060cc34`  
**Owner acceptance:** explicitly recorded 2026-09-03

## Accepted scope

SLICE-0043 establishes HullQ's first durable native professional listing persistence path by composing the already-accepted marketplace identity and professional publishing-eligibility boundaries with the post-SLICE-0042 Alembic migration authority.

Accepted capability:

```text
explicit Account
+ explicit professional Organization principal
+ explicit OrganizationMembership
+ minimal NativeListing creation request
        ↓
real SLICE-0041 publishing-eligibility evaluation
        ↓
ALLOWED only
        ↓
transaction-safe PostgreSQL persistence
        ↓
exact typed readback
```

Durable creation is not public publication. This slice does not define or imply listing lifecycle, freshness, public visibility, media, full yacht/listing data, FastAPI/UI or broker-workspace behavior.

## Accepted durable creation envelope

The accepted immutable persistence envelope is limited to:

```text
NativeListingId
publishing_organization_id
created_by_account_id
optional MarketEpisodeId
optional broker_listing_reference
internal deterministic content_hash
created_at
```

Hard accepted semantics:

- `NativeListingId` is the accepted SLICE-0040 runtime-distinct listing identity;
- `publishing_organization_id` is derived from the exact candidate Organization that passed the SLICE-0041 eligibility evaluator;
- `created_by_account_id` is derived from the exact Account evaluated by the same authorization boundary;
- duplicate Organization/Account IDs are not trusted from listing payload data;
- `MarketEpisodeId` remains optional and may remain unresolved;
- persisting a typed MarketEpisode link does not infer PhysicalBoat identity, deduplication or configuration truth;
- optional `broker_listing_reference` must contain at least one non-whitespace character when present and is preserved exactly without invented normalization;
- `broker_listing_reference` is not a HullQ identity and does not trigger deduplication;
- `created_at` is database-generated durable creation metadata and is not lifecycle/freshness/publication truth;
- the internal content hash is persistence evidence only, not a broker-facing listing field.

## Accepted authorization boundary

The durable create path calls the real accepted SLICE-0041 evaluator:

```text
evaluate_native_listing_publishing_eligibility(
    account_id,
    candidate_organization,
    membership,
)
```

No caller-supplied authorization boolean substitutes for that decision.

Accepted fail-closed rule:

```text
ALLOWED
→ persistence may proceed

DENIED(reason)
→ zero NativeListing rows written
```

The accepted implementation retains deterministic denial reasons including no membership, Account mismatch, Organization mismatch, inactive membership, missing explicit PUBLISHER role, ineligible Organization and unverified Organization.

Cross-Organization isolation remains strict: publishing authority in Organization A cannot create a NativeListing under Organization B.

## Accepted idempotency and collision semantics

The durable creation boundary is immutable and race-safe.

```text
same NativeListingId
+ same immutable semantic envelope
→ ALREADY_EXISTS
→ exactly one row
→ original created_at preserved
```

```text
same NativeListingId
+ different immutable semantic envelope
→ CONFLICT
→ fail closed
→ existing row unchanged
```

Conflicting immutable content includes a change to:

- publishing Organization;
- creator Account;
- optional MarketEpisode link;
- optional broker listing reference.

The implementation uses an atomic PostgreSQL insert/conflict pattern rather than check-then-insert overwrite behavior. Concurrent identical creations resolve deterministically without duplicate rows; concurrent conflicting creations resolve with one durable creation and one conflict.

## Accepted transaction-ownership boundary

Independent exact-head review found and corrected a material durability defect in the initial implementation.

The final accepted rule is:

> `CREATED` MUST never be returned unless the newly-created NativeListing row is already durably committed, independent of any later caller action on the connection.

Because psycopg `conn.transaction()` becomes a nested savepoint when the supplied connection already has an open transaction, the accepted implementation requires the supplied connection to be `TransactionStatus.IDLE` before an authorized create may enter its owned transaction.

If the connection is already `ACTIVE`, `INTRANS` or `INERROR`, creation fails closed before opening a cursor/transaction or writing any NativeListing row.

The implementation does not silently commit, roll back or otherwise dispose of unrelated caller transaction work merely to make listing creation succeed.

Accepted operational pattern:

```text
IDLE connection
→ create_native_listing owns top-level transaction
→ CREATED only after durable commit

non-IDLE connection
→ NativeListingTransactionOwnershipError
→ zero NativeListing writes
→ caller retains responsibility for its pre-existing transaction
```

A real PostgreSQL regression proves that a prior readback/SELECT opens an implicit transaction and causes the following create attempt on that same connection to be rejected before write. A separate real PostgreSQL test proves that a normal `CREATED` result is immediately visible from a different fresh connection without any explicit caller `commit()`.

## Alembic schema authority

SLICE-0042 remains controlling.

SLICE-0043 adds one post-baseline Alembic revision:

```text
6f1c2a9d0001  legacy 001/002 baseline marker
        ↓
1bb00df4a018  native listing persistence
```

The new revision creates only the minimal `native_listings` persistence table required by this capability.

Legacy `001_initial_schema.sql` and `002_canonical_identity_schema.sql` remain unchanged and no `003_*.sql` legacy migration was added.

No SQLAlchemy ORM domain model, generic repository or Unit-of-Work framework was introduced.

The migration deliberately does not create false foreign keys to Account, MarketplaceOrganization or MarketEpisode tables that do not yet exist.

## Exact typed readback

Accepted readback by `NativeListingId` reconstructs the existing runtime-distinct identity values:

```text
NativeListingId
MarketEpisodeId | None
MarketplaceOrganizationId
AccountId
```

plus the exact broker listing reference and durable creation timestamp.

A missing listing returns not-found/`None` rather than inventing a record.

No BoatDesign/configuration facts are projected into PhysicalBoat/listing truth.

## Independent exact-head review

Independent review was repeated whenever the implementation HEAD changed.

Initial implementation HEAD:

```text
fea5ea71c7cd9e21da8429654bf7e7872252a859
```

Verdict: **AMEND**.

Material finding:

`create_native_listing()` used `conn.transaction()` on a caller-supplied psycopg connection without first proving transaction ownership. If a prior SELECT/readback had already opened an implicit transaction, the create block became only a nested savepoint. The function could return `CREATED` even though the row remained dependent on the caller later committing the outer transaction; closing the connection without that commit could lose the row.

That violated the locked durable-creation guarantee.

Final amended HEAD:

```text
3e9fadf0b54a07d6b8b9926ebaaff65cedd3cddb
```

Final verdict: **ACCEPT**.

The amendment added the explicit IDLE transaction-ownership guard, a dedicated fail-closed exception, real PostgreSQL regression coverage for the implicit-transaction scenario, and an independent-connection durability proof for the normal CREATED path.

No blocker, high or medium finding remained on the accepted exact HEAD.

## Exact-head validation gates

On accepted HEAD `3e9fadf0b54a07d6b8b9926ebaaff65cedd3cddb`:

- owner inspection: `NATIVE LISTING RESULT: PASS`;
- owner inspection includes implicit-transaction rejection and separate-connection durability proof;
- full local suite: `3765 passed / 2 skipped`;
- project coverage: `93.11%`;
- `src/hullq/persistence/native_listing.py` coverage: `100%`;
- ruff format/check: PASS;
- mypy: PASS;
- repository validation: PASS;
- `uv lock --check`: PASS;
- dependency audit / `pip-audit`: no known vulnerabilities;
- CI run `33784316127`: SUCCESS;
  - PostgreSQL 18 DB integration: SUCCESS;
  - quality / Ubuntu: SUCCESS;
  - quality / Windows: SUCCESS;
  - dependency audit: SUCCESS;
- Manufacturer artifact reproducibility run `33784316251`: SUCCESS;
  - Ubuntu reproduction: SUCCESS;
  - Windows reproduction: SUCCESS.

## Merge verification

PR #136 was merged with expected-head protection against accepted implementation HEAD:

```text
3e9fadf0b54a07d6b8b9926ebaaff65cedd3cddb
```

Canonical implementation merge commit:

```text
a4cacd10f1dd7fb387b203e9b2f394195060cc34
```

## Retained scope boundaries

SLICE-0043 does **not** implement or authorize:

- the complete PhysicalBoat / NativeListing field catalog;
- price, currency, POA, location, title/description or technical/equipment/refit/tax/registration/HIN/CIN fields;
- Account/MarketplaceOrganization/OrganizationMembership persistence;
- PhysicalBoat persistence;
- MarketEpisode persistence or continuity resolution;
- listing lifecycle/status;
- listing freshness/reconfirmation;
- public listing pages or search/read API surfaces;
- FastAPI endpoints;
- Astro/React UI;
- broker listing creation/management GUI;
- broker public profile/contact surface;
- media ingestion/storage;
- Saved Search/monitoring/alerts;
- leads/ContactRequest;
- BrokerageRequest/private-owner referral;
- bulk/CSV/feed/API inventory intake;
- physical-vessel dedup/identity resolution;
- Auth0/AuthIdentity/MFA/session/step-up implementation;
- pricing/entitlements;
- transaction/escrow/closing;
- SLICE-0044 or later implementation.

## Retained follow-on product contracts

The following product requirements remain explicitly retained for separate readiness and implementation rather than being silently absorbed into SLICE-0043:

```text
PhysicalBoat + Listing Field Contract
Broker Listing Workspace Contract
Professional Organization / Broker Public Profile Contract
```

The future Broker Listing Workspace requirement includes broker-facing listing creation and inventory management capabilities such as a guided Create Listing flow, inventory dashboard, design matching, physical/listing fact editing, validation/completeness feedback, public preview, agent assignment and audit/history, with media/bulk intake/leads added only through their own bounded dependencies. HullQ is not intended to become a generic broker CRM.

## Operational result

SLICE-0043 is owner-accepted and operationally complete under the HullQ slice workflow.

This closure does not create, authorize or start SLICE-0044. Any next marketplace capability requires separate readiness under the controlling Architecture Rebaseline, ONE-CAPABILITY and VISIBLE-RESULT rules.
