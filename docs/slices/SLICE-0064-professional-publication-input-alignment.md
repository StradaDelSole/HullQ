# SLICE-0064 — Professional Publication Input Alignment

**ID:** SLICE-0064  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace — publication-input alignment before promotion  
**Depends on:** SLICE-0050 PhysicalBoat claims; SLICE-0054 shared seller draft payload; SLICE-0061 professional drafts; SLICE-0062 recovery; SLICE-0063 accepted current state  
**Blocks:** later professional draft promotion specification/implementation only; no later slice is automatically authorized

## Objective

Deliver exactly one capability:

> Close the two repository-proven input/destination mismatches that currently make later professional draft promotion lossy: add required `listing_offer.broker_description` to the shared draft vocabulary and add `physical_boat.boat_name` to the existing PhysicalBoat claim revision model.

No promotion or publication occurs in this slice.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: align accepted pre-market draft input with existing marketplace field destinations needed for later lossless promotion.

**VISIBLE-RESULT CHECK:** PASS  
A broker can enter, save, reopen and recover a listing description in the existing professional draft UI; the concrete-yacht claim layer can durably represent the already-accepted boat-name field without creating any NativeListing.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Launch Gate §2 requires a low-friction create/publish inventory path. The accepted post-0061 reconciliation explicitly blocks immediate promotion until the boat-name writer and required broker-description draft input mismatch are resolved.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Shared draft parser/persistence, professional and owner-direct draft APIs/forms, recovery module, NativeListingOffer required fields, MARKETPLACE_FIELD_REGISTRY, PhysicalBoat claim domain/persistence/migration/public read, Launch Gate and broker requirements were inspected.

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0063-acceptance-closure.md`; `docs/POST_SLICE_0061_REASSESSMENT_2026-09-21.md`; `docs/POST_SLICE_0062_REASSESSMENT_2026-09-21.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`; professional/owner-direct draft contracts and recovery contract.

**Production implementation checked:** `src/hullq/domain/listing_draft_payload.py`; professional/owner-direct draft domain/application/persistence; `src/hullq/domain/native_listing_offer.py`; `src/hullq/domain/physical_boat_claims.py`; `src/hullq/persistence/physical_boat_claims.py`; professional recovery module; FastAPI routes; relevant Astro forms; PhysicalBoat/public-read serializers; migrations/tests/retained proofs.

**Already implemented / not re-decided:** shared seller draft payload foundation; private draft ownership/concurrency; professional PUBLISHER/MFA/CSRF/recovery boundary; existing seven-field PhysicalBoat immutable claim revision/head model; NativeListingOffer required broker_description semantics; marketplace identity/lifecycle/Search truth.

**Exact remaining gap:** the shared draft cannot carry required offer broker_description, and accepted draft boat_name has no PhysicalBoat claim persistence destination.

**Accepted-but-unimplemented obligations:** later lossless professional promotion and Launch Gate §2 inventory workflow. 0064 closes only the named data-shape prerequisite.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` current draft/auth/claim/offer boundaries; `DECIDED_NOT_YET_IMPLEMENTED` input alignment selected here plus later promotion; `EXPLICITLY_DEFERRED` promotion/publication/media/leads/analytics/Search; `GENUINELY_OPEN` exact promotion transaction/preflight and required UNKNOWN/ABSENT capture; `CONFLICT_OR_REGRESSION` none.

**TRIGGER GATES CHECK:** PASS  
0064 adds no Search criterion, external production data, pilot, paid plan or public launch.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Broker Workspace Launch Gate:** NOT_READY  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

Current later-promotion mapping has two explicit holes:

```text
draft physical_boat.boat_name
→ X no accepted current claim persistence field

NativeListingOfferSnapshot.broker_description REQUIRED
← X shared draft has no broker_description
```

Immediate promotion would therefore drop accepted user input or invent required marketplace content.

0064 closes those two holes without creating marketplace truth from a draft.

## Controlling artifacts

- Normative contract: `specs/PROFESSIONAL_PUBLICATION_INPUT_ALIGNMENT_CONTRACT.v0.1.md`
- Shared seller draft: `src/hullq/domain/listing_draft_payload.py` and accepted owner-direct/professional draft contracts
- Marketplace fields: `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- Marketplace fact contract: `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
- Broker requirements: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`
- Launch gate: `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- Decision reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`

## In scope

- add `listing_offer.broker_description` to shared common draft payload;
- professional draft API/persistence/web support;
- owner-direct draft API/persistence non-regression/support for shared field;
- professional recovery capture/restore for the new form field;
- add BoatNameClaim with VALUE_ASSERTION/ABSENT/UNKNOWN semantics;
- extend existing PhysicalBoatClaimSnapshot/revision persistence/head/hash/readback with optional boat name;
- migration preserving all existing claim revisions/heads;
- relevant current claim serialization/read projection;
- focused unit/persistence/API/web tests;
- retained PostgreSQL 18 + FastAPI + built Astro proof;
- CI execution of retained proof;
- handoff to REVIEW, never DONE.

## Explicitly out of scope

- draft→PhysicalBoat/MarketEpisode/NativeListing promotion;
- automatic claim/offer write from draft;
- NativeListing creation/publication;
- publish/withdraw/reconfirm UI;
- marketplace-ID generation/mapping for drafts;
- promotion transaction/idempotency design;
- media;
- leads/CRM;
- outcomes/analytics;
- Search changes/Search-fit diagnostics;
- export/import;
- Organization admin/profile;
- payments;
- owner-direct publication;
- production pilot/public launch.

## Required behavior

### A. Common description field

Shared parser/serializer and both server draft channels round-trip `listing_offer.broker_description` with one validation rule.

### B. Professional UI/recovery

Professional edit form exposes description and local recovery protects unsaved description with existing 0062 semantics.

### C. No synthetic required content

Blank/omitted description may remain in incomplete draft form but later marketplace offer construction cannot synthesize a placeholder.

### D. Boat-name claim semantics

Existing PhysicalBoat claim model adds optional BoatNameClaim with exact registry assertion kinds VALUE_ASSERTION/ABSENT/UNKNOWN.

### E. One claim revision model

No new boat-name table. Existing revision/head/idempotency/concurrency/Organization-isolation rules continue.

### F. No omission inference

Missing draft boat_name is not automatically ABSENT or UNKNOWN.

### G. No promotion

Saving either draft channel remains private pre-market state and creates zero marketplace identities/facts/lifecycle mutations.

## Deliverables

1. shared draft-domain/parser/serializer expansion;
2. professional and owner-direct persistence/API compatibility;
3. professional Astro/recovery support;
4. PhysicalBoat boat-name claim domain + migration + persistence/readback;
5. focused tests;
6. retained real PostgreSQL 18 + FastAPI + built Astro proof;
7. CI wiring if a new retained proof is added;
8. REVIEW handoff only.

## Acceptance criteria

- [ ] Shared accepted common draft key count becomes exactly 10.
- [ ] broker_description is one of those common keys, not professional-only metadata.
- [ ] Durable draft value is trimmed/non-empty when present.
- [ ] No placeholder/default broker_description is generated.
- [ ] Professional create/read/update round-trips broker_description.
- [ ] Owner-direct create/read/update round-trips broker_description.
- [ ] Professional edit UI renders/edits it.
- [ ] Professional local recovery includes it with existing same-version/stale/unavailable behavior.
- [ ] Existing draft ownership/auth/MFA/CSRF/concurrency behavior is unchanged.
- [ ] BoatNameClaim supports VALUE_ASSERTION/ABSENT/UNKNOWN exactly.
- [ ] Invalid assertion/value combinations fail closed.
- [ ] PhysicalBoatClaimSnapshot carries optional boat-name claim.
- [ ] Existing claim revision table/model is extended rather than duplicated.
- [ ] Existing revision history/head/predecessor/hash/idempotency/concurrency semantics remain unchanged.
- [ ] Existing rows/revisions migrate without data loss.
- [ ] Organization claim isolation remains unchanged.
- [ ] Omitted boat name remains distinct from explicit ABSENT/UNKNOWN.
- [ ] No Search criterion/ranking behavior changes.
- [ ] No draft save creates PhysicalBoat/MarketEpisode/NativeListing/offer/claim/publication truth.
- [ ] Current seven PhysicalBoat claim fields remain behaviorally unchanged.
- [ ] NativeListingOffer semantics remain unchanged.
- [ ] REQ-BROKER-023/024 markers remain IMPLEMENTED; no other register marker advances.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] Repository validation/lint/type-check/Python tests/web tests/check/build pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if a smaller equivalent implementation proves the contract:

- `src/hullq/domain/listing_draft_payload.py`;
- owner-direct/professional draft tests and web forms;
- `web/src/lib/professionalDraftRecovery.ts`;
- `src/hullq/domain/physical_boat_claims.py`;
- `src/hullq/persistence/physical_boat_claims.py`;
- one Alembic migration after current head `1a6de411f835`;
- claim API/read serialization tests;
- retained professional/owner-direct/claim proof scripts;
- CI only when needed for retained proof.

## Validation

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python -m pytest
npm test --prefix web
npm run check --prefix web
npm run build --prefix web
```

Run/report the retained real PostgreSQL/FastAPI/built-Astro proofs covering the modified verticals.

## Stop conditions

Stop and report rather than inventing policy if:

- implementation requires creating marketplace identities from a draft;
- promotion transaction design is required to finish 0064;
- boat name requires a parallel persistence model;
- broker_description would become professional-only despite being common LISTING_OFFER truth;
- missing boat_name would be silently converted to ABSENT/UNKNOWN;
- a placeholder broker description would be generated;
- Search semantics would change;
- scope expands into media/leads/outcomes/analytics/publication.

## Status handoff rule

Claude may set `REVIEW` or `BLOCKED`, never `DONE`.

Clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md` structure.

Do not include a next-slice proposal.

Do not start SLICE-0065.
