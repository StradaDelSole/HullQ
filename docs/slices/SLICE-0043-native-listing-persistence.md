# SLICE-0043 — NativeListing persistence

**ID:** SLICE-0043  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** Native Marketplace Foundation — first durable professional NativeListing  
**Depends on:** SLICE-0040 owner-accepted / DONE; SLICE-0041 owner-accepted / DONE; SLICE-0042 owner-accepted / DONE; 2026-09-02 Architecture Rebaseline accepted/merged  
**Blocks:** later physical/listing fact contract, broker listing workspace, public broker/profile surfaces, listing read/search, lifecycle/freshness, media, scalable intake

## Objective

Deliver exactly one inspectable durable marketplace capability:

> **Given an explicit HullQ Account, candidate professional Organization, relevant OrganizationMembership and a minimal NativeListing creation request, evaluate the accepted SLICE-0041 publishing-eligibility boundary and, only when ALLOWED, create one immutable NativeListing creation envelope in PostgreSQL through the post-SLICE-0042 Alembic schema; identical retries are idempotent, identity-content collisions fail closed, denied creation writes nothing, and exact readback preserves the accepted identity relationships without inventing physical-vessel or listing truth.**

This is HullQ's first durable native professional listing path.

It deliberately does **not** define the full yacht/listing field catalog, publish a listing publicly, implement lifecycle/freshness, expose FastAPI/UI, persist marketplace actors, add media, or start broker-workspace implementation.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: authorized durable creation + exact readback of the smallest NativeListing creation envelope.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one PostgreSQL-backed command and visibly prove: an eligible professional publisher creates one NativeListing, exact readback succeeds, an identical retry is idempotent, a conflicting reuse of the same NativeListingId fails closed, and denied/cross-Organization attempts write zero rows.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted post-0039 reconciliation places `create/persist one native professional listing end-to-end` after the marketplace identity boundary and professional publishing eligibility. SLICE-0042 established Alembic as the authoritative post-baseline migration mechanism, so SLICE-0043 may now add the first marketplace application table as one bounded Alembic revision.

## Why this slice exists

Accepted prior boundaries now provide:

```text
SLICE-0040
NativeListingId / NativeListing
+ optional typed MarketEpisodeId link
+ strict truth-scope separation

SLICE-0041
AccountId
+ MarketplaceOrganization
+ OrganizationMembership
→ ALLOWED or DENIED(reason)

SLICE-0042
legacy 001/002 frozen
→ Alembic baseline 6f1c2a9d0001
→ all future schema evolution via Alembic
```

What does not yet exist is the smallest durable composition of those accepted boundaries:

```text
eligible professional actor
        +
minimal NativeListing request
        ↓
authorized persistence
        ↓
PostgreSQL row
        ↓
exact typed readback
```

This slice proves that composition without prematurely defining the complete listing product.

## Controlling artifacts

Apply the post-SLICE-0039 precedence where relevant:

1. `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
2. `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`;
3. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
4. `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`;
5. `specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md`;
6. SLICE-0042 Alembic migration authority / acceptance closure;
7. non-conflicting older artifacts.

Retain strict truth, provenance, explicit `UNKNOWN`, fail-closed authorization, tenant isolation, ONE-CAPABILITY, VISIBLE-RESULT, slice isolation, exact-head review and PostgreSQL integration rules.

## Locked semantic boundary

### 1. Creation is durable creation, not public publication

In SLICE-0043:

```text
create NativeListing
=
persist a durable HullQ-hosted listing creation envelope
```

It does **not** mean:

```text
publish public page
make ACTIVE
mark fresh/current
send alerts
accept buyer leads
```

Do not introduce `DRAFT`, `ACTIVE`, `PUBLISHED`, `WITHDRAWN`, `SOLD`, `ARCHIVED`, freshness states, visibility states or public URLs merely to represent creation.

There is no implicit lifecycle state in this slice.

### 2. Minimal persisted creation envelope

The durable NativeListing envelope is intentionally small.

Required semantic values:

```text
NativeListingId
publishing_organization_id
created_by_account_id
optional MarketEpisodeId
optional broker_listing_reference
created_at
```

Persistence may additionally store an internal deterministic semantic fingerprint/content hash needed for idempotency/collision safety. That hash is persistence evidence, not a broker-facing listing field.

#### NativeListingId

- must use the accepted runtime-distinct `NativeListingId` from SLICE-0040;
- is the sole HullQ identity key for this NativeListing row;
- must never be minted from broker reference, Organization ID, MarketEpisodeId, price, title or other visible data;
- empty/wrong-kind IDs fail closed under the accepted domain rules.

#### publishing_organization_id

This is the professional Organization principal under which the listing is created.

Hard anti-confusion rule:

> The persisted `publishing_organization_id` MUST be derived from the exact `candidate_organization.id` that passed the SLICE-0041 eligibility evaluator.

Do not trust a second Organization ID copied from a listing payload/client claim.

SLICE-0043 does not implement Organization persistence, Organization ownership transfer or Organization-profile fields. Because no durable marketplace-Organization table exists yet, this field must not pretend to have a database foreign key that cannot be truthfully enforced.

#### created_by_account_id

This records the HullQ Account that performed the accepted creation action.

Hard anti-confusion rule:

> The persisted `created_by_account_id` MUST be derived from the exact `account_id` evaluated by the SLICE-0041 eligibility boundary.

Do not trust a creator/account ID copied from the listing payload.

SLICE-0043 does not implement Account persistence, AuthIdentity or Auth0. Therefore no database FK to a nonexistent marketplace Account table is required or authorized.

`created_by_account_id` is immutable creation provenance for this slice, not a general ownership/current-editor model.

#### optional MarketEpisodeId

The accepted SLICE-0040 NativeListing may remain MarketEpisode-unresolved or carry an explicit typed `MarketEpisodeId`.

SLICE-0043 must preserve both states:

```text
NativeListing(id, market_episode_id=None)
→ durable unresolved listing appearance

NativeListing(id, market_episode_id=<typed MarketEpisodeId>)
→ durable explicitly linked appearance
```

No MarketEpisode persistence exists yet, so no database FK may falsely claim durable referential verification.

Persisting an explicitly supplied typed link is **not** permission to infer, resolve, deduplicate or validate physical-vessel identity. No HIN/CIN/name/year/location heuristic is introduced.

#### optional broker_listing_reference

This is an optional broker/dealer-side inventory/reference token useful for later portability/import workflows.

Rules:

- `None` is allowed;
- when supplied, it must be non-empty after the contract's chosen validation rule;
- it is not a HullQ identity;
- it must not mint `NativeListingId`;
- it must not trigger deduplication or MarketEpisode resolution;
- no global uniqueness is required in this slice;
- do not infer broker identity or professional status from its format.

#### created_at

- generated by the durable persistence boundary/database at first creation;
- stored as timezone-aware PostgreSQL time (`TIMESTAMPTZ` or equivalent accepted representation);
- not supplied as trusted client truth;
- remains unchanged on an idempotent retry;
- is metadata about HullQ creation time, not evidence of listing freshness, publication time, sale start time or MarketEpisode start time.

### 3. Full listing/yacht field catalog is explicitly deferred

SLICE-0043 must **not** choose the complete NativeListing / PhysicalBoat fact model by convenience.

Do not add fields for:

- asking price / currency / POA;
- location/geography;
- public description/title;
- builder/model/year beyond the existing optional identity link;
- dimensions, displacement, draft;
- keel/rudder/rig;
- engine/power/hours;
- tanks;
- accommodation;
- sails/equipment/navigation/electrical;
- refits/upgrades/damage/repairs;
- VAT/tax/registration/flag;
- HIN/CIN;
- media/documents;
- broker public profile/contact details.

Those fields require a separate normative **PhysicalBoat + Listing Field Contract** so HullQ can explicitly decide per field whether it is required/optional, public/internal, broker-claimed/HullQ-derived/verified, searchable/filterable and whether `UNKNOWN` is allowed.

Hard retained rule:

```text
BoatDesign/configuration truth
!=
this PhysicalBoat / this NativeListing truth
```

No design facts are projected into the durable listing row.

### 4. Authorization is part of the real creation path

The creation entry point must evaluate the real accepted SLICE-0041 function:

```text
evaluate_native_listing_publishing_eligibility(
    account_id,
    candidate_organization,
    membership,
)
```

Do not accept a caller-supplied boolean such as `authorized=True` as a substitute.

Required creation gate:

```text
PublishingEligibilityDecision == ALLOWED
→ persistence may proceed

PublishingEligibilityDecision == DENIED(reason)
→ zero NativeListing rows written
```

Every existing deterministic SLICE-0041 denial reason remains meaningful.

At minimum owner/test evidence must include:

```text
eligible PUBLISHER in Org A + candidate Org A
→ creation allowed

OWNER-only / ADMIN-only / no membership / inactive / unverified / ineligible
→ denied
→ no listing row

PUBLISHER membership for Org A + candidate Org B
→ denied ORGANIZATION_MISMATCH
→ no listing row
```

Do not persist first and validate afterward.

### 5. Authorization result is not authentication/MFA/publication

SLICE-0041 already defines `ALLOWED` as domain eligibility only.

SLICE-0043 composes that domain gate with durable creation, but still does not implement:

- Auth0 sessions;
- MFA / Passkeys / TOTP;
- step-up authentication;
- public publication;
- public visibility.

The controlling architecture's future MFA requirements remain unchanged. This slice must not claim that durable creation satisfies all future runtime security ceremonies.

### 6. Idempotency and identity-content collision handling

Follow HullQ's established durable-persistence pattern rather than inventing overwrite semantics.

For the immutable creation envelope:

```text
same NativeListingId
+ same semantic creation envelope
→ idempotent success / ALREADY_EXISTS-equivalent
→ exactly one row
→ original created_at preserved
```

But:

```text
same NativeListingId
+ different immutable semantic envelope
→ CONFLICT-equivalent
→ fail closed
→ existing row unchanged
```

A conflicting envelope includes a change to any immutable persisted semantic value, including:

- publishing Organization principal;
- creator Account;
- optional MarketEpisode link;
- optional broker listing reference.

Do not implement UPDATE/UPSERT-overwrite behavior merely to make retries convenient.

Persistence should be race-safe. Prefer the existing HullQ pattern of atomic insert/conflict detection (for example `INSERT ... ON CONFLICT DO NOTHING` followed by exact semantic-fingerprint/readback comparison) over a check-then-insert race.

### 7. Deterministic creation result

The creation boundary must return an inspectable structured result rather than `True/False` only.

Minimum mechanically distinct outcomes:

```text
CREATED
ALREADY_EXISTS   # identical idempotent retry
DENIED           # with PublishingEligibilityReason
CONFLICT         # same NativeListingId, different immutable envelope
```

Equivalent concise names are acceptable if these meanings remain distinct.

Rules:

- `DENIED` carries the underlying deterministic SLICE-0041 denial reason;
- `CONFLICT` must not be mislabeled as authorization denial;
- no probability/trust score;
- no lifecycle/visibility status is encoded in this result.

### 8. Exact typed readback

Provide one narrow readback path by `NativeListingId`.

Readback must reconstruct/return values that preserve the accepted runtime identity kinds, normally including:

```text
NativeListing(
  id=NativeListingId(...),
  market_episode_id=MarketEpisodeId(...) | None,
)

publishing Organization = MarketplaceOrganizationId(...)
created by = AccountId(...)
broker_listing_reference = str | None
created_at = durable timestamp
```

A missing NativeListing may return `None`/not-found-equivalent without inventing a record.

Do not join to nonexistent actor/MarketEpisode tables or synthesize BoatDesign/PhysicalBoat facts.

### 9. PostgreSQL schema boundary

SLICE-0042 is controlling:

```text
legacy 001/002 = frozen historical bootstrap only
Alembic baseline = 6f1c2a9d0001
all new schema evolution = Alembic
```

SLICE-0043 must add exactly the smallest post-baseline Alembic revision required for this capability.

Requirements:

- revision's `down_revision` resolves to the accepted SLICE-0042 baseline/head;
- create the minimal `native_listings`-equivalent table only;
- no `003_*.sql` legacy migration;
- no rewriting legacy 001/002;
- no SQLAlchemy ORM/domain-model adoption;
- Alembic/SQLAlchemy may be used as migration tooling exactly as accepted in SLICE-0042;
- migration upgrade against a baselined PostgreSQL 18 database must preserve all pre-existing accepted rows;
- `alembic upgrade head` on the accepted baseline must create the listing table deterministically;
- repeated `alembic upgrade head` is idempotent under normal Alembic revision semantics.

Minimum table semantics normally include:

```text
native_listing_id            TEXT PRIMARY KEY
publishing_organization_id   TEXT NOT NULL
created_by_account_id        TEXT NOT NULL
market_episode_id             TEXT NULL
broker_listing_reference     TEXT NULL
content_hash                  TEXT NOT NULL
created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

Equivalent naming is acceptable if contract/code/tests agree.

Use database constraints for obvious local invariants where useful, but do not create fake FKs to actor/MarketEpisode tables that do not exist.

### 10. Transaction boundary

One creation attempt must be transactionally coherent:

- authorization is evaluated before any NativeListing write;
- a successful new creation commits exactly one durable row;
- an identical retry produces no duplicate;
- a conflict leaves the existing row unchanged;
- a persistence exception does not leave a partial NativeListing row.

Do not add a generic Unit-of-Work framework for this slice.

## Normative contract deliverable

Add:

```text
specs/NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1.md
```

It must define only the locked semantics above:

- minimal immutable creation envelope;
- derivation of creator/principal IDs from the evaluated authorization context;
- allowed/denied creation gate;
- idempotency/conflict semantics;
- exact typed readback;
- Alembic-only schema authority;
- explicit truth/non-goal boundaries.

Do not expand this contract into the later full listing field model, Broker Workspace, public profile, lifecycle, freshness, media, leads, pricing or API design.

Contract, migration, code and tests must agree atomically.

## Minimal owner-test surface

Provide one deterministic PostgreSQL-backed owner command, normally:

```text
uv run python scripts/inspect_native_listing_persistence.py
```

It must require `HULLQ_TEST_DATABASE_URL`, use disposable PostgreSQL schema isolation consistent with existing integration tests, establish the accepted Alembic baseline, upgrade to the SLICE-0043 head, and exercise the real authorization + persistence/readback path.

Visible result should be equivalent to:

```text
NATIVE LISTING PERSISTENCE

eligible broker PUBLISHER -> CREATED
listing id                 -> NL-0043-001
publishing organization    -> ORG-A
created by                 -> ACCOUNT-A
market episode             -> UNRESOLVED
broker reference           -> BROKER-REF-42
readback                    -> EXACT

identical retry             -> ALREADY_EXISTS
row count after retry       -> 1
created_at preserved        -> YES

same listing id, changed envelope -> CONFLICT
original row unchanged            -> YES

OWNER-only creation        -> DENIED: PUBLISHER_ROLE_REQUIRED
cross-org creation         -> DENIED: ORGANIZATION_MISMATCH
denied attempts wrote rows -> NO

DESIGN FACTS PROJECTED      -> NO
PUBLICATION/LIFECYCLE SET   -> NO
NATIVE LISTING RESULT       -> PASS
```

Exact labels may differ, but these meanings must remain inspectable.

The script must execute the real evaluator, Alembic migration, persistence and readback code. It may not print hard-coded PASS without checking the required invariants.

## Required tests

Focused tests must cover at least:

### Contract/domain composition

- creation accepts the accepted SLICE-0040 `NativeListing` / `NativeListingId` types rather than introducing an interchangeable plain-string listing identity;
- optional MarketEpisode link accepts only the accepted `MarketEpisodeId` type through the existing domain object;
- optional broker listing reference accepts `None` and rejects an invalid empty value under the chosen contract;
- publisher Organization and creator Account persisted values are derived from the evaluated candidate Organization/account inputs, not independently trusted payload fields;
- no full yacht/listing fact fields are introduced.

### Authorization before write

- eligible active PUBLISHER for eligible Organization A can create;
- no membership is denied and writes zero rows;
- OWNER-only is denied and writes zero rows;
- ADMIN-only is denied and writes zero rows;
- inactive PUBLISHER is denied and writes zero rows;
- UNVERIFIED Organization is denied and writes zero rows;
- INELIGIBLE Organization is denied and writes zero rows;
- membership for another Account is denied and writes zero rows;
- PUBLISHER for Organization A cannot create on behalf of Organization B and writes zero rows;
- denial exposes the exact SLICE-0041 denial reason.

### Durable creation/readback

- Alembic migration upgrades accepted baseline to the new single head on PostgreSQL 18;
- migration creates the expected minimal listing table without modifying legacy 001/002 artifacts;
- new eligible creation persists exactly one row;
- exact readback reconstructs typed NativeListingId, optional typed MarketEpisodeId, MarketplaceOrganizationId and AccountId;
- unresolved NativeListing round-trips with `market_episode_id=None`;
- explicitly linked NativeListing round-trips the supplied MarketEpisodeId without any resolution inference;
- broker listing reference round-trips exactly;
- created_at is database-generated/non-null and remains stable across idempotent retry;
- identical retry returns ALREADY_EXISTS-equivalent and leaves one row;
- same NativeListingId with changed broker reference conflicts;
- same NativeListingId with changed MarketEpisode link conflicts;
- same NativeListingId created under another otherwise-eligible Organization conflicts rather than overwriting the original;
- same NativeListingId created by another otherwise-eligible Account conflicts rather than overwriting immutable creation provenance;
- conflict leaves original persisted row unchanged;
- persistence implementation is race-safe against duplicate identity insertion at the SQL boundary;
- persistence exception rolls back the attempted row.

### Scope/truth regression

- no automatic BoatDesign/configuration fact projection exists;
- no PhysicalBoat/MarketEpisode resolution/dedup inference is introduced;
- no lifecycle/freshness/publication fields are introduced;
- no Account/Organization/Membership persistence tables are introduced;
- no FastAPI/Astro/React/Auth0/media/lead/referral work is started;
- legacy migration runner gains no post-002 SQL migration;
- full existing test suite remains green.

## In scope

- compact normative NativeListing persistence contract;
- exactly one minimal post-baseline Alembic application-schema revision;
- smallest persistence module/creation command/result/readback needed for authorized NativeListing creation;
- reuse/composition of accepted SLICE-0040 identity objects and SLICE-0041 eligibility evaluator;
- deterministic semantic fingerprint/content-hash mechanism if needed for idempotency/conflict safety;
- transactional/race-safe insert behavior;
- deterministic PostgreSQL-backed owner inspection;
- focused unit/persistence/contract tests;
- minimal package exports only if existing conventions require them.

## Explicitly out of scope

- public listing publication/visibility;
- FastAPI endpoints;
- Astro/React UI;
- full listing/yacht/PhysicalBoat field catalog;
- price/currency/POA;
- listing location;
- public title/description;
- equipment/refit/engine/rig/tank/accommodation fields;
- HIN/CIN/registration/flag/VAT/tax fields;
- Account persistence;
- MarketplaceOrganization persistence;
- OrganizationMembership persistence;
- AuthIdentity/Auth0/session/MFA/passkey/TOTP implementation;
- professional Organization verification workflow/KYB/KYC;
- Organization ownership transfer;
- generic RBAC;
- listing lifecycle/status;
- freshness/reconfirmation;
- ListingSnapshot/ListingEvent/price history/Days-on-Market;
- physical-vessel identity resolution/dedup;
- MarketEpisode continuity inference;
- media upload/storage/quarantine;
- broker public profile/contact fields;
- Broker Listing Workspace GUI/management tools;
- bulk/CSV/feed/API/CRM/DMS intake;
- leads/ContactRequest;
- BrokerageRequest/referral;
- Saved Search/monitoring/alerts;
- pricing/entitlements;
- SEO/public pages;
- transaction/escrow/closing;
- SLICE-0044 or later work.

## Reserved follow-on product contracts — not part of this slice

The following requirements are intentionally retained for later separate readiness and must not be lost or silently implemented inside SLICE-0043.

### PhysicalBoat + Listing Field Contract

Before building the complete listing editor/search/detail model, explicitly define which fields HullQ requires/offers for a specific boat/listing and classify each field by dimensions including:

```text
required vs optional
public vs internal
broker claim vs HullQ-derived vs verified
PhysicalBoat-specific vs BoatDesign/configuration-derived
UNKNOWN permitted
searchable/filterable
```

This is where price, location, technical/equipment/refit/tax/registration and other specific-vessel listing details are defined.

### Broker Listing Workspace Contract

Define the broker-facing creation/management product before implementing the broad GUI.

Retained target capabilities include:

- inventory dashboard with own-listing search/filter/sort;
- guided Create Listing wizard rather than one undifferentiated large form;
- BoatDesign/configuration matching assistance without projecting design truth onto the physical boat;
- PhysicalBoat fact editor with explicit unknown/claim semantics;
- completeness/validation panel showing required, optional, unknown and contradiction states;
- buyer-view preview before later publication;
- listing management/edit workflows under future lifecycle rules;
- agent/contact assignment under an Organization principal;
- audit/activity history;
- later media manager only after the accepted quarantine/storage pipeline exists;
- later bulk/feed management;
- later lead inbox and broker analytics as separate capabilities.

Hard product boundary:

> HullQ's broker workspace is an inventory-quality, listing-management and qualified-buyer-interest tool — not a generic CRM/ERP/accounting/contract-management suite.

### Professional Organization / Broker Public Profile Contract

Separately define what buyers see about the publishing Organization and, where applicable, the named broker/agent. Organization and individual agent remain distinct concepts.

Potential fields/capabilities are not locked by SLICE-0043 and require their own contract before persistence/UI implementation.

## Deliverables

Expected bounded deliverables:

1. `specs/NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1.md`;
2. one Alembic revision directly after the accepted SLICE-0042 baseline;
3. normally one narrow module such as `src/hullq/persistence/native_listing.py`;
4. focused tests, normally `tests/persistence/test_native_listing_persistence.py` plus only narrowly necessary unit/contract tests;
5. `scripts/inspect_native_listing_persistence.py`;
6. this slice document updated to `REVIEW` on successful handoff.

Do not create API/frontend/lifecycle/full-listing-field scaffolding as placeholders.

## Expected touch points

Expected implementation paths are limited to:

- `docs/slices/SLICE-0043-native-listing-persistence.md`;
- `specs/NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1.md`;
- `alembic/versions/<revision>_native_listing_persistence.py` or equivalent single bounded revision;
- `src/hullq/persistence/native_listing.py` or equivalent narrow module;
- `tests/persistence/test_native_listing_persistence.py` and narrowly necessary contract/unit tests;
- `scripts/inspect_native_listing_persistence.py`;
- `src/hullq/persistence/__init__.py` only if existing conventions require a minimal export.

Changes to `src/hullq/domain/market_identity.py` or `src/hullq/domain/publishing_eligibility.py` should normally be unnecessary. If implementation needs to change their already-accepted semantics, STOP before widening scope.

Do not modify legacy `src/hullq/persistence/sql/001_initial_schema.sql`, `002_canonical_identity_schema.sql` or add `003_*.sql`.

## Acceptance criteria

- [x] Product execution checks remain `PASS` with no scope widening.
- [x] Compact normative NativeListing persistence contract exists and matches implementation/tests.
- [x] One post-baseline Alembic revision adds only the minimal NativeListing persistence table needed by this capability.
- [x] The revision descends from the accepted SLICE-0042 Alembic baseline/head and no post-002 legacy SQL migration is added.
- [x] Legacy 001/002 artifacts remain unchanged.
- [x] Creation uses the accepted SLICE-0040 NativeListing identity model and does not create a competing listing identity type.
- [x] Publishing Organization and creator Account persisted IDs are derived from the exact authorization context, not independently trusted request fields.
- [x] Real SLICE-0041 publishing eligibility is evaluated before any NativeListing DB write.
- [x] Eligible professional PUBLISHER can create one durable NativeListing.
- [x] Every tested denied eligibility path writes zero NativeListing rows and preserves deterministic denial reason.
- [x] Cross-Organization authorization fails closed and writes zero rows.
- [x] Unresolved NativeListing can be persisted/read back without inventing MarketEpisode/PhysicalBoat identity.
- [x] Explicit typed MarketEpisodeId can be preserved without automatic identity resolution or false FK semantics.
- [x] Optional broker listing reference is preserved but is not treated as HullQ identity/dedup authority.
- [x] `created_at` is durable creation metadata, database-generated/non-client-trusted and stable on idempotent retry.
- [x] Identical repeat creation is idempotent and produces exactly one row.
- [x] Same NativeListingId with a different immutable creation envelope fails closed as CONFLICT-equivalent and never overwrites the original row.
- [x] Persistence is transactionally coherent and race-safe at the SQL identity boundary.
- [x] Exact readback preserves runtime-distinct NativeListingId, MarketEpisodeId where present, MarketplaceOrganizationId and AccountId types.
- [x] No complete yacht/listing field catalog is invented.
- [x] No BoatDesign/configuration facts are projected into physical/listing truth.
- [x] No lifecycle/freshness/publication/media/lead/referral/API/UI/actor-persistence scope is introduced.
- [x] Owner command executes real PostgreSQL 18 + Alembic + authorization + persistence/readback and reports `NATIVE LISTING RESULT: PASS` only when all required scenarios pass.
- [x] Repository validation, ruff, mypy and full test suite pass; project coverage remains >=90%.
- [ ] Exact-head CI, including PostgreSQL 18 integration, and Manufacturer artifact reproducibility are green before review acceptance where applicable.
- [ ] No SLICE-0044 or later work starts automatically.

## Validation

```text
uv run python scripts/inspect_native_listing_persistence.py
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
uv lock --check
uv run pip-audit
```

Use the repository's existing PostgreSQL 18 integration configuration through `HULLQ_TEST_DATABASE_URL`.

Remote exact-head verification must include the existing required CI and Manufacturer artifact reproducibility workflows.

## Stop conditions

Stop and report rather than widen scope when:

- a higher-precedence accepted artifact materially contradicts this boundary;
- the implementation would require changing accepted SLICE-0040 market identity semantics;
- the implementation would require weakening/bypassing SLICE-0041 authorization;
- the first listing table cannot be added through the accepted Alembic chain;
- actor persistence/FKs are claimed to be required merely to prove this capability;
- PhysicalBoat/MarketEpisode resolution would have to be invented to persist an unresolved NativeListing;
- correct implementation appears to require the complete listing field catalog;
- scope pressure pulls lifecycle, freshness, public publication, media, leads, feeds, Auth0/MFA or broker GUI into this slice;
- tests could pass only by overwriting a conflicting NativeListingId or projecting BoatDesign facts into listing truth.

## Status handoff rule

The implementation agent may recommend/set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required external checks, independent exact-head review, explicit Project Owner acceptance and normal closure under `CLAUDE.md` / `AI_SLICE_WORKFLOW.md`.

Any amendment changes HEAD and resets independent exact-head review.

## Required completion report

Use the exact structure in `docs/slices/SLICE_TEMPLATE.md`.

Include:

- exact final branch HEAD SHA;
- actual changed files;
- exact owner-command result;
- full local validation results;
- exact remote CI/reproducibility evidence on the final HEAD;
- unresolved findings/ambiguities/scope deviations;
- explicit declaration that no later slice was started.

Do not start the next slice automatically.