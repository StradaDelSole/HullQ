# SLICE-0065 — Professional Publication Input Alignment

**ID:** SLICE-0065  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace — publication-input alignment before promotion  
**Depends on:** SLICE-0050 PhysicalBoat claims; SLICE-0061 professional drafts; SLICE-0062 recovery; SLICE-0064 professional inventory lifecycle controls  
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
Launch Gate §2 requires low-friction create/publish inventory. Current `main` proves immediate promotion would either drop accepted boat-name input or invent required broker-description content.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Professional/owner-direct contracts, draft/recovery domain/persistence/API/web, NativeListingOffer required fields, MARKETPLACE_FIELD_REGISTRY, PhysicalBoat claim domain/persistence/read model, SLICE-0064 lifecycle controls, Launch Gate and broker requirements were inspected on canonical `main`.

**TRIGGER GATES CHECK:** PASS  
0065 adds no Search criterion, external production data, pilot, paid plan or launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0064-acceptance-closure.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`; `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`.

**Production implementation checked:** `src/hullq/domain/listing_draft_payload.py`; `src/hullq/domain/professional_listing_draft.py`; professional draft application/persistence/API/web and recovery implementation; `src/hullq/domain/native_listing_offer.py`; `src/hullq/persistence/native_listing_offer.py`; `src/hullq/domain/physical_boat_claims.py`; `src/hullq/persistence/physical_boat_claims.py`; PhysicalBoat/MarketEpisode/NativeListing persistence; current public claim/listing read projection; SLICE-0064 inventory lifecycle implementation/tests/retained proof; relevant migrations/tests.

**Already implemented / not re-decided:** current Account/Organization/Membership/MFA/PUBLISHER draft boundary; exact nine-key shared seller payload; owner-direct vocabulary; professional broker reference; optimistic draft versioning; SLICE-0062 recovery semantics; MarketplaceOrganization publishing eligibility; PhysicalBoat/MarketEpisode/NativeListing identity separation; seven-field PhysicalBoat claim revision/head semantics; nine-field NativeListing offer semantics including required broker_description; lifecycle/freshness/public-read boundaries; existing Publish/Withdraw/Reconfirm controls; technical Search criterion count exactly two.

**Exact remaining gap:** current ProfessionalListingDraft can store `physical_boat.boat_name` but the current PhysicalBoat claim snapshot cannot represent it, while `NativeListingOfferSnapshot` requires `broker_description` but the current ProfessionalListingDraft cannot store it. A later promotion is therefore not yet lossless without dropping accepted input or inventing required content.

**Accepted-but-unimplemented obligations:** later lossless ProfessionalListingDraft→marketplace promotion and Launch Gate §2 create/edit inventory workflow; offer editing; media; durable leads/CRM; analytics/outcomes; inventory portability/export; structured bulk onboarding/import; Search-fit/exclusion/demand-insight obligations and buyer persistent monitoring remain separate later capabilities.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` current auth/draft/owner-direct/recovery/claim/offer/lifecycle/publication-control boundaries; `DECIDED_NOT_YET_IMPLEMENTED` professional-only broker_description input, PhysicalBoat boat-name claim destination and later lossless promotion; `EXPLICITLY_DEFERRED` actual promotion/publication, marketplace-ID generation, offer edit, media, leads/CRM, analytics/outcomes, import/export, Search-fit, buyer Saved Search/price alerts, payments, owner-direct publication and pilot/launch; `GENUINELY_OPEN` future atomic promotion strategy, new-vs-existing PhysicalBoat choice, promoted ID allocation/idempotency, post-promotion draft provenance, future republish/edit/clone semantics, launch media architecture, lead workflow and buyer price-alert subscription/notification mechanics; `CONFLICT_OR_REGRESSION` none found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Broker Workspace Launch Gate:** NOT_READY  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

```text
professional draft physical_boat.boat_name
→ X no current accepted PhysicalBoat claim field

NativeListingOfferSnapshot.broker_description REQUIRED
← X ProfessionalListingDraft has no broker_description
```

Immediate promotion would drop accepted input or invent required content.

SLICE-0065 closes those holes without creating marketplace truth from a draft.

## Controlling artifacts

- `docs/POST_SLICE_0064_REASSESSMENT_2026-09-23.md`
- `specs/PROFESSIONAL_PUBLICATION_INPUT_ALIGNMENT_CONTRACT.v0.1.md`
- `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`
- `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
- `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`

## In scope

- professional-only `listing_offer.broker_description` draft input;
- professional draft domain/request/persistence/API/web support;
- professional local recovery capture/restore for the new form field;
- normative amendment to current ProfessionalListingDraft/Recovery contracts where required;
- OwnerDirectListingDraft non-regression with no vocabulary change;
- BoatNameClaim VALUE_ASSERTION/ABSENT/UNKNOWN;
- extend existing PhysicalBoatClaimSnapshot/revision persistence/head/hash/readback with optional boat name;
- migration preserving existing claim revisions/heads and historic idempotency;
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
- marketplace-ID generation/mapping;
- promotion transaction/idempotency;
- offer editing;
- media;
- leads/CRM;
- outcomes/analytics;
- Search/Search-fit;
- export/import;
- buyer Saved Search / price-change alert implementation;
- Organization admin/profile;
- payments;
- owner-direct publication;
- production pilot/public launch.

## Required behavior

### A. Professional description field

Professional parser/serializer/API/persistence round-trip exact wire key `listing_offer.broker_description`. It is not added to the shared common payload.

### B. Professional UI/recovery

Professional edit form exposes it and SLICE-0062 local recovery protects unsaved content with unchanged scope/version rules.

### C. Owner-direct unchanged

Owner-direct parser/API/persistence/browser behavior remains unchanged; `broker_description` does not become an accepted owner-direct key.

### D. No synthetic required content

Description omission remains valid for incomplete professional draft save; later marketplace offer construction cannot synthesize a placeholder.

### E. Boat-name claim semantics

Existing PhysicalBoat claim model adds optional BoatNameClaim with registry assertion kinds VALUE_ASSERTION/ABSENT/UNKNOWN.

### F. One claim revision model

No new boat-name table. Existing revision/head/idempotency/concurrency/Organization-isolation rules continue.

### G. Historic retry compatibility

An exact retry of a historic seven-field claim revision remains idempotent and MUST NOT become CONFLICT merely because the runtime/schema now understands optional boat-name state.

### H. No omission inference

Missing draft boat_name is not automatically ABSENT or UNKNOWN.

### I. No promotion

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
- [ ] Omitted boat name remains distinct from ABSENT/UNKNOWN.
- [ ] Existing PhysicalBoat revision/head/concurrency/Organization semantics remain unchanged.
- [ ] Existing seven-field historic claim revisions remain readable with boat name omitted.
- [ ] Exact retry of a pre-0065 seven-field claim revision remains idempotent.
- [ ] New boat-name content participates in immutable conflict/idempotency fingerprinting.
- [ ] Public/read projection safely preserves boat-name assertion state.
- [ ] Boat name remains DISPLAY_ONLY and never becomes BoatDesign truth/Search criterion.
- [ ] Professional draft save creates zero marketplace truth rows/state.
- [ ] SLICE-0064 lifecycle controls remain unchanged.
- [ ] REQ-BROKER-023/024 remain IMPLEMENTED.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] Search criteria remain exactly two.
- [ ] validation/lint/type-check/Python/web tests/check/build pass.
- [ ] retained PostgreSQL 18 + FastAPI + built Astro proof passes.
- [ ] exact implementation HEAD gets independent review + explicit Owner Acceptance.

## Expected touch points

Expected, not mandatory if a smaller equivalent proves the contract:

- `src/hullq/domain/professional_listing_draft.py`;
- professional draft application/persistence;
- `src/hullq/domain/physical_boat_claims.py`;
- `src/hullq/persistence/physical_boat_claims.py`;
- one Alembic migration;
- current claim/public read serializers as applicable;
- `src/hullq/api/app.py`;
- broker web client + professional draft Astro page;
- professional draft recovery;
- focused tests and retained proof;
- CI retained-proof wiring.

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

Run/report the exact retained SLICE-0065 publication-input alignment proof.

## Stop conditions

Stop and report rather than inventing policy if:

- implementation needs draft→marketplace promotion;
- implementation needs PhysicalBoat/MarketEpisode/NativeListing identity allocation;
- owner-direct common vocabulary would change;
- boat name would become BoatDesign truth;
- historic claim exact-retry semantics cannot be preserved;
- missing boat name would be inferred as ABSENT/UNKNOWN;
- required broker description would be synthesized;
- authorization or recovery isolation would be weakened;
- Search semantics would change;
- scope expands into offer edit, media, leads, outcomes, analytics, import/export, buyer alerts or publication.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, successful remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0066.
