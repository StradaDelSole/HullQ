# SLICE-0064 — Professional Draft Publication Readiness

**ID:** SLICE-0064  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace inventory creation bridge  
**Depends on:** SLICE-0061 draft workspace; SLICE-0062 recovery; SLICE-0050 PhysicalBoat claims; NativeListing offer/lifecycle foundations

## Objective

Deliver exactly one capability:

> An authorized professional draft has one deterministic server-side READY/BLOCKED publication-readiness evaluation that maps every currently supported publication-relevant draft value losslessly into accepted PhysicalBoat-claim / NativeListing-offer candidate values, while creating zero marketplace truth.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: professional-draft publication readiness/mapping.

**VISIBLE-RESULT CHECK:** PASS  
The broker draft page shows actionable BLOCKED reasons or READY while still explicitly remaining a private not-public draft.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
After recovery and publisher identity, the immediate launch-gate inventory gap is draft → marketplace publication. Repository inspection proves raw draft state is not yet losslessly mappable; 0064 closes that prerequisite instead of hiding field/model expansion inside the future promotion transaction.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current draft vocabulary, PhysicalBoat claims, NativeListing offers, publishing eligibility, lifecycle/public-read and launch-gate boundaries were inspected on canonical main.

**TRIGGER GATES CHECK:** PASS  
0064 creates no marketplace listing, Search criterion, external production data, pilot, paid plan or public launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0063-acceptance-closure.md`; `docs/slices/SLICE-0061-authenticated-professional-listing-draft-workspace.md`; `docs/slices/SLICE-0050-first-buyer-critical-physical-boat-truth.md`; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`.

**Production implementation checked:** `src/hullq/domain/listing_draft_payload.py`; `src/hullq/domain/professional_listing_draft.py`; `src/hullq/application/professional_listing_draft.py`; `src/hullq/persistence/professional_listing_draft.py`; `src/hullq/domain/physical_boat_claims.py`; `src/hullq/persistence/physical_boat_claims.py`; `src/hullq/domain/native_listing_offer.py`; `src/hullq/persistence/native_listing_offer.py`; `src/hullq/persistence/physical_boat.py`; `src/hullq/persistence/market_episode.py`; `src/hullq/persistence/native_listing.py`; `src/hullq/persistence/native_listing_lifecycle.py`; professional draft/recovery Astro surfaces/tests/proofs.

**DECIDED_AND_IMPLEMENTED:** current draft identity/ownership/auth/recovery; MarketplaceOrganization/publishing eligibility; PhysicalBoat/MarketEpisode/NativeListing identity boundaries; seven-field PhysicalBoat claim revision semantics; NativeListing offer semantics; lifecycle/public-read boundaries; Search count two.

**DECIDED_NOT_YET_IMPLEMENTED:** lossless draft publication mapping; actual promotion; publish/withdraw/reconfirm broker controls; media; leads/CRM; analytics/outcomes/export/import/Search-fit and later obligations.

**EXPLICITLY_DEFERRED:** all marketplace mutation from draft; promotion ID allocation/transaction composition; media; leads; analytics; payments; Search; owner-direct publication; pilot/launch.

**GENUINELY_OPEN:** exact future atomic promotion strategy; ID allocation; post-promotion draft retention/provenance; later edit/clone/relist semantics.

**CONFLICT_OR_REGRESSION:** none. Explicit gap: current draft has `physical_boat.boat_name` that current PhysicalBoat claim snapshot excludes, while current NativeListingOfferSnapshot requires `broker_description` that current professional draft lacks.

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

## Controlling artifacts

- `docs/POST_SLICE_0063_REASSESSMENT_2026-09-22.md`
- `specs/PROFESSIONAL_PUBLICATION_READINESS_CONTRACT.v0.1.md`
- `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
- `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`

## In scope

- professional-only `listing_offer.broker_description` draft field;
- persistence/API/web/recovery support;
- boat-name assertion wrapper and exact eighth-field extension of current bounded PhysicalBoat claim snapshot;
- migration/persistence/public-read compatibility for boat-name claim state;
- deterministic server-side publication-readiness evaluator;
- typed READY candidate mapping;
- structured BLOCKED reason codes;
- draft-page readiness UI;
- retained PostgreSQL/FastAPI/built-Astro proof;
- owner-direct, recovery, claim, public-listing and Search non-regression.

## Explicitly out of scope

- draft promotion or creation/mutation of PhysicalBoat/MarketEpisode/NativeListing;
- publication lifecycle;
- promoted NativeListing ID;
- Publish/Withdraw/Reconfirm UI;
- explicit UNKNOWN build-year draft input;
- explicit ABSENT/UNKNOWN boat-name draft input;
- new PhysicalBoat fields other than boat name;
- media;
- leads/CRM;
- sale/outcome;
- analytics;
- export/import;
- Search changes;
- payments;
- pilot/public launch.

## Required behavior

### A. Broker description

Professional draft may persist/recover bounded plain-text broker description; optional while incomplete, required for READY.

### B. Boat-name claim

PhysicalBoat claim snapshot extends exactly from seven to eight fields by adding boat name with omitted / VALUE_ASSERTION / ABSENT / UNKNOWN semantics.

### C. Historic compatibility

Existing seven-field revisions migrate/read boat name as omitted; no value is invented.

### D. Readiness mapping

Complete draft maps deterministically to typed candidate PhysicalBoat/offer values.

### E. Blockers

Missing required inputs produce deterministic structured blocker codes.

### F. No mutation

Readiness changes no marketplace identity/truth/lifecycle/Search state.

### G. Broker UI

Draft page shows READY or actionable blockers but remains clearly `Draft — not public`. No Publish button.

## Deliverables

1. broker-description draft support;
2. eight-field PhysicalBoat claim representation/persistence/public projection;
3. publication-readiness application boundary;
4. blocker response;
5. draft readiness UI;
6. focused Python/web tests;
7. retained PostgreSQL/FastAPI/built-Astro proof;
8. CI wiring if needed;
9. REVIEW handoff, never DONE.

## Acceptance criteria

- [ ] broker_description persists/reads and may be absent in incomplete draft.
- [ ] provided broker_description is bounded, trimmed, non-empty plain text.
- [ ] broker_description control characters/over-limit invalid.
- [ ] owner-direct common draft API unchanged.
- [ ] recovery captures/restores broker_description.
- [ ] PhysicalBoat claim snapshot contains exactly eight fields after extension.
- [ ] boat name preserves omitted vs VALUE_ASSERTION vs ABSENT vs UNKNOWN.
- [ ] historic claim revisions read boat name as omitted.
- [ ] claim revision/current-head/concurrency/Organization semantics unchanged.
- [ ] public claim projection renders boat name safely.
- [ ] complete AMOUNT draft -> READY.
- [ ] complete POA draft -> READY.
- [ ] missing required inputs -> deterministic blocker codes.
- [ ] absent build year never becomes UNKNOWN automatically.
- [ ] draft boat name -> VALUE_ASSERTION; omission -> omitted.
- [ ] draft region -> LocationRegionClaim(VALUE_ASSERTION).
- [ ] no synthetic broker description/summary/history/VAT.
- [ ] Decimal price remains lossless.
- [ ] readiness evaluation mutates zero marketplace rows/state.
- [ ] foreign/unknown draft non-enumeration unchanged.
- [ ] draft page displays server-driven READY/BLOCKED.
- [ ] READY still says not public.
- [ ] no Publish endpoint/button.
- [ ] private/no-store/noindex/CSRF unchanged.
- [ ] REQ-BROKER-023/024 remain IMPLEMENTED.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] Search criteria remain exactly two.
- [ ] validation/lint/type-check/Python/web tests/check/build pass.
- [ ] exact implementation HEAD gets independent review + explicit Owner Acceptance.

## Expected touch points

- professional draft domain/application/persistence;
- focused readiness module;
- PhysicalBoat claims domain/persistence;
- one Alembic migration as needed;
- public listing read projection;
- FastAPI;
- broker API client;
- professional draft Astro page;
- professionalDraftRecovery;
- focused tests and retained proof.

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

Run/report retained real PostgreSQL/FastAPI/built-Astro proof.

## Stop conditions

Stop instead of inventing policy if readiness requires marketplace mutation, mapping drops a current draft field, owner-direct common semantics must change, boat name becomes BoatDesign truth, historic claim revisions cannot migrate as omission, missing build year would be guessed/UNKNOWN, authorization would be bypassed, IDs must be allocated, or scope expands into promotion/lifecycle/media/leads/Search.

## Status handoff rule

Claude may set `REVIEW` or `BLOCKED`, never `DONE`.

A clean implementation still requires exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md`. Do not propose/start SLICE-0065.
