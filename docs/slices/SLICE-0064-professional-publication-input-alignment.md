# SLICE-0064 — Professional Publication Input Alignment

**ID:** SLICE-0064  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace — publication-input alignment before promotion  
**Depends on:** SLICE-0050 PhysicalBoat claims; SLICE-0061 professional drafts; SLICE-0062 recovery; SLICE-0063 accepted state  
**Blocks:** later professional draft promotion specification/implementation only; no later slice is automatically authorized

## Objective

Deliver exactly one capability:

> Close the two repository-proven input/destination mismatches that currently make later professional draft promotion lossy: add required `listing_offer.broker_description` as a professional-only draft offer input and add `physical_boat.boat_name` to the existing PhysicalBoat claim revision model.

No promotion or publication occurs.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: align professional pre-market input with truthful marketplace destinations needed for later lossless promotion.

**VISIBLE-RESULT CHECK:** PASS  
A broker can enter, save, reopen and recover a listing description in the existing professional draft UI; the concrete-yacht claim layer can durably represent boat-name claims without creating a NativeListing.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Launch Gate §2 requires low-friction create/publish inventory. The accepted post-0061 reconciliation explicitly blocks immediate promotion until boat-name persistence and required broker-description input are resolved.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Professional/owner-direct contracts, professional recovery contract, draft domain/persistence/API/web, NativeListingOffer required fields, MARKETPLACE_FIELD_REGISTRY, PhysicalBoat claim domain/persistence/migration/read projection, Launch Gate and broker requirements were inspected.

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0063-acceptance-closure.md`; `docs/POST_SLICE_0061_REASSESSMENT_2026-09-21.md`; `docs/POST_SLICE_0062_REASSESSMENT_2026-09-21.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`.

**Production implementation checked:** `src/hullq/domain/listing_draft_payload.py`; professional/owner-direct draft domain/application/persistence; `src/hullq/domain/native_listing_offer.py`; `src/hullq/domain/physical_boat_claims.py`; `src/hullq/persistence/physical_boat_claims.py`; professional recovery module; FastAPI routes; relevant Astro forms; claim/public-read serializers; migrations/tests/retained proofs.

**Already implemented / not re-decided:** nine-key shared seller payload; owner-direct rule against broker-specific narrative reuse; private draft ownership/concurrency; professional PUBLISHER/MFA/CSRF/recovery; seven-field PhysicalBoat immutable claim revision/head model; NativeListingOffer required broker_description; marketplace identity/lifecycle/Search truth.

**Exact remaining gap:** ProfessionalListingDraft cannot carry required offer broker_description, and accepted professional/common draft boat_name has no PhysicalBoat claim persistence destination.

**Accepted-but-unimplemented obligations:** later lossless professional promotion and Launch Gate §2 inventory workflow. 0064 closes only the named data-shape prerequisite.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` current auth/draft/owner-direct/claim/offer boundaries; `DECIDED_NOT_YET_IMPLEMENTED` professional-only broker_description + boat-name claim destination selected here and later promotion; `EXPLICITLY_DEFERRED` promotion/publication/media/leads/analytics/Search and owner-direct narrative changes; `GENUINELY_OPEN` exact promotion transaction/preflight and UNKNOWN/ABSENT capture; `CONFLICT_OR_REGRESSION` none after resolving the initial readiness conflict with OwnerDirect narrative semantics.

**TRIGGER GATES CHECK:** PASS  
0064 adds no Search criterion, external production data, pilot, paid plan or launch.

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

```text
professional draft physical_boat.boat_name
→ X no current accepted claim persistence field

NativeListingOfferSnapshot.broker_description REQUIRED
← X ProfessionalListingDraft has no broker_description
```

Immediate promotion would drop accepted input or invent required content.

0064 closes those holes without creating marketplace truth from a draft.

## Controlling artifacts

- Normative contract: `specs/PROFESSIONAL_PUBLICATION_INPUT_ALIGNMENT_CONTRACT.v0.1.md`
- Professional draft contract: `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- Professional recovery: `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`
- Owner-direct non-regression: `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- Marketplace fields: `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- Marketplace fact contract: `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
- Broker requirements / launch gate / reconciliation governance.

## In scope

- professional-only `listing_offer.broker_description` draft input;
- professional draft domain/request/persistence/API/web support;
- professional local recovery capture/restore for the new form field;
- normative amendment to current ProfessionalListingDraft/Recovery contracts;
- OwnerDirectListingDraft non-regression with no vocabulary change;
- BoatNameClaim VALUE_ASSERTION/ABSENT/UNKNOWN;
- extend existing PhysicalBoatClaimSnapshot/revision persistence/head/hash/readback with optional boat name;
- migration preserving existing claim revisions/heads;
- relevant current claim serialization/read projection;
- focused tests;
- retained PostgreSQL 18 + FastAPI + built Astro proof;
- CI execution;
- REVIEW handoff only.

## Explicitly out of scope

- changing owner-direct narrative vocabulary;
- draft→PhysicalBoat/MarketEpisode/NativeListing promotion;
- automatic claim/offer write from draft;
- NativeListing creation/publication;
- publish/withdraw/reconfirm UI;
- marketplace-ID generation/mapping;
- promotion transaction/idempotency;
- media;
- leads/CRM;
- outcomes/analytics;
- Search/Search-fit;
- export/import;
- Organization admin/profile;
- payments;
- owner-direct publication;
- production pilot/public launch.

## Required behavior

### A. Professional description field

Professional parser/serializer/API/persistence round-trip exact wire key `listing_offer.broker_description`. It is not added to the shared common payload.

### B. Professional UI/recovery

Professional edit form exposes it and 0062 local recovery protects unsaved content with unchanged scope/version rules.

### C. Owner-direct unchanged

Owner-direct parser/API/persistence/browser behavior remains unchanged; `broker_description` does not become an accepted owner-direct key.

### D. No synthetic required content

Description omission remains valid for incomplete professional draft save; later marketplace offer construction cannot synthesize a placeholder.

### E. Boat-name claim semantics

Existing PhysicalBoat claim model adds optional BoatNameClaim with registry assertion kinds VALUE_ASSERTION/ABSENT/UNKNOWN.

### F. One claim revision model

No new boat-name table. Existing revision/head/idempotency/concurrency/Organization-isolation rules continue.

### G. No omission inference

Missing draft boat_name is not automatically ABSENT or UNKNOWN.

### H. No promotion

Professional draft save remains private pre-market state and creates zero marketplace identities/facts/lifecycle mutations.

## Acceptance criteria

- [ ] Shared common draft key count remains exactly 9.
- [ ] OwnerDirectListingDraft vocabulary remains unchanged.
- [ ] Professional draft accepts `listing_offer.broker_description` in addition to common payload + broker reference.
- [ ] Durable description is trimmed/non-empty when present.
- [ ] No placeholder/default description is generated.
- [ ] Professional create/read/update round-trips description.
- [ ] Professional edit UI renders/edits it.
- [ ] Professional local recovery includes it with existing same-version/stale/unavailable behavior.
- [ ] Existing professional ownership/auth/MFA/CSRF/concurrency remains unchanged.
- [ ] BoatNameClaim supports VALUE_ASSERTION/ABSENT/UNKNOWN exactly.
- [ ] Invalid assertion/value combinations fail closed.
- [ ] PhysicalBoatClaimSnapshot carries optional boat-name claim.
- [ ] Existing claim revision table/model is extended rather than duplicated.
- [ ] Existing history/head/predecessor/hash/idempotency/concurrency semantics remain unchanged.
- [ ] Existing rows/revisions migrate without data loss.
- [ ] Organization claim isolation remains unchanged.
- [ ] Omitted boat name remains distinct from explicit ABSENT/UNKNOWN.
- [ ] No Search criterion/ranking behavior changes.
- [ ] No draft save creates PhysicalBoat/MarketEpisode/NativeListing/offer/claim/publication truth.
- [ ] Current seven PhysicalBoat claim fields remain behaviorally unchanged.
- [ ] NativeListingOffer semantics remain unchanged.
- [ ] REQ-BROKER-023/024 stay IMPLEMENTED; no register marker advances.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] Repository validation/lint/type-check/Python tests/web tests/check/build pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

- professional draft domain/application/persistence and migration if a dedicated field is used;
- professional draft API/web tests;
- `web/src/lib/professionalDraftRecovery.ts`;
- `src/hullq/domain/physical_boat_claims.py`;
- `src/hullq/persistence/physical_boat_claims.py`;
- one Alembic migration after current head `1a6de411f835`;
- claim serialization/read tests;
- retained professional/owner-direct/claim proofs;
- CI if retained proof wiring changes.

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

Run/report retained real PostgreSQL/FastAPI/built-Astro proofs covering modified verticals.

## Stop conditions

Stop and report rather than invent policy if:

- implementation requires creating marketplace identities from a draft;
- promotion transaction design is required to finish 0064;
- boat name requires a parallel persistence model;
- broker_description would need to be added to OwnerDirectListingDraft;
- missing boat_name would be silently converted to ABSENT/UNKNOWN;
- placeholder broker description would be generated;
- Search semantics would change;
- scope expands into media/leads/outcomes/analytics/publication.

## Status handoff rule

Claude may set `REVIEW` or `BLOCKED`, never `DONE`.

Clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md` structure.

Do not include a next-slice proposal.

Do not start SLICE-0065.
