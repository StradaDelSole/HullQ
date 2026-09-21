# SLICE-0063 — Publishing Organization Public Identity

**ID:** SLICE-0063  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace / public marketplace publisher identity  
**Depends on:** SLICE-0049 public NativeListing; SLICE-0053 MarketplaceOrganization actor directory; SLICE-0062 accepted broker baseline state  
**Blocks:** no later slice automatically; may close REQ-BROKER-023 only after accepted implementation closure

## Objective

Deliver exactly one capability:

> Give the existing authoritative publishing MarketplaceOrganization a bounded human-readable public display identity and show it consistently on authorized Broker Workspace surfaces and every public NativeListing, independent of optional claims.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: explicit current publishing Organization identity.

**VISIBLE-RESULT CHECK:** PASS  
A broker sees the Organization's human-readable name in its workspace, and a buyer sees "Listed by {Organization}" on every public listing even when VAT/tax metadata is absent.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
REQ-BROKER-023 is the only remaining Mandatory Capability Register item classified as a launch/pilot-baseline commitment after SLICE-0062 implemented REQ-BROKER-024.

**REPOSITORY RECONCILIATION CHECK:** PASS  
MarketplaceOrganization persistence/domain, broker workspace context, NativeListing public read model/API, Astro public listing page, 0049 SEO/public behavior, Mandatory Capability Register and Broker Workspace Launch Gate were inspected.

**TRIGGER GATES CHECK:** PASS  
0063 adds no Search criterion, external production data, broker pilot, paid plan or public launch. Production Readiness remains NOT_TRIGGERED and Broker Workspace Launch Gate remains NOT_READY.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED:** existing MarketplaceOrganization ID/authorization/publishing eligibility; current public listing publisher ID; public listing FastAPI boundary; Broker Workspace current membership/MFA authorization; 0062 recovery; Search criteria count 2.

**DECIDED_NOT_YET_IMPLEMENTED:** REQ-BROKER-023 clear human-readable publisher identity/text branding preservation; media workflow; promotion/publication; leads/CRM/outcomes/analytics; export/import and other later commitments.

**EXPLICITLY_DEFERRED:** logo/media assets; Organization self-service/profile admin; legal-name/KYB; public broker profile URLs; contact/website/social fields; media watermark processing; all unrelated marketplace/Search/lead work.

**GENUINELY_OPEN:** future legal-name/profile model; logo/media asset architecture; broker profile URL/slug; professional promotion transaction; later Organization administration.

**CONFLICT_OR_REGRESSION:** none. The generic `ORGANIZATION_SCHEMA.v0.1.json` is not silently collapsed into MarketplaceOrganization because no accepted durable mapping exists.

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0062_REASSESSMENT_2026-09-21.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/slices/SLICE-0062-acceptance-closure.md`; `specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`; `specs/ORGANIZATION_SCHEMA.v0.1.json`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`.

**Production implementation checked:** `src/hullq/domain/publishing_eligibility.py`; `src/hullq/persistence/broker_identity.py`; `src/hullq/application/broker_workspace_read.py`; `src/hullq/application/public_listing_read.py`; `src/hullq/api/app.py`; `web/src/lib/brokerApi.ts`; `web/src/lib/publicListingApi.ts`; `web/src/pages/broker/index.astro`; `web/src/pages/broker/organizations/[organization_id].astro`; `web/src/pages/listings/[native_listing_id].astro`; broker/public-listing persistence/API/web tests and retained proofs.

**Already implemented / not re-decided:** exact MarketplaceOrganizationId publishing identity; actor-directory Organization/membership persistence; current membership/MFA authorization; NativeListing publisher ownership; public read lifecycle/freshness gates; FastAPI-only public read boundary; 0049 canonical/noindex route semantics; Search criterion count exactly two.

**Exact remaining gap:** public publisher presentation currently exposes only an opaque Organization ID, and Astro renders that ID only inside optional VAT/tax markup, so an otherwise valid public listing may show no publisher identity at all.

**Accepted-but-unimplemented obligations:** REQ-BROKER-023 requires explicit publisher identity and preservation of legitimate broker branding. 0063 implements only bounded current textual Organization identity/branding presentation; media/logo asset handling remains deferred.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` current MarketplaceOrganization identity/auth/public-listing boundaries; `DECIDED_NOT_YET_IMPLEMENTED` REQ-BROKER-023 current publisher display identity; `EXPLICITLY_DEFERRED` media/logo/profile-admin/promotion/leads/analytics; `GENUINELY_OPEN` future legal-name/profile/media asset model and public broker profile URL; `CONFLICT_OR_REGRESSION` none found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Broker Workspace Launch Gate:** NOT_READY  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

Current public listing behavior can omit publisher identity entirely when `vat_tax_status_claim` is absent because the Astro page renders `publishing_organization_id` only inside that optional block.

Opaque IDs also dominate the Broker Workspace Organization chooser/context.

REQ-BROKER-023 explicitly requires visible publisher identity.

## Controlling artifacts

- Normative contract: `specs/PUBLISHING_ORGANIZATION_PUBLIC_IDENTITY_CONTRACT.v0.1.md`
- Broker requirements: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`
- Broker product direction: `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`
- Mandatory register: `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`
- Launch gate: `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- Public listing SEO contract: `specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`
- Decision reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`

## In scope

- one bounded `public_display_name` on existing `marketplace_organizations`;
- migration/backfill for existing actor-directory rows;
- bounded validation;
- internal/test provisioning support for explicit human-readable names;
- current broker context read models expose display name;
- Broker Workspace chooser/context visibly render display name;
- public listing read model/API exposes publisher ID + current display name;
- public Astro listing always renders publisher identity independently of VAT/other optional claims;
- legacy/unresolved publisher ID compatibility fallback;
- safe HTML escaping/inert presentation;
- proof that display-name change does not mutate listing identity/lifecycle/offer/Search;
- retained PostgreSQL/FastAPI/built-Astro proof;
- preservation of all existing auth, lifecycle, freshness and Search behavior.

## Explicitly out of scope

- logo upload/storage;
- media/gallery pipeline;
- media watermark manipulation;
- Organization self-service profile editing;
- public Organization/broker profile page;
- broker slug;
- legal-name/KYB verification;
- address/phone/email/website/social fields;
- office hierarchy;
- draft promotion/publication;
- leads/contact/CRM;
- analytics/outcomes;
- export/import;
- payments;
- Search changes;
- SEO/indexation expansion;
- production pilot/public launch.

## Required behavior

### A. Same Organization identity

Display name is metadata on the existing MarketplaceOrganization row; no second broker Organization identity.

### B. Bounded display name

Non-empty, bounded, safe plain text. Preserve legitimate punctuation/corporate suffixes.

### C. Existing-row migration

Deterministic local backfill; no network lookup.

### D. Broker Workspace visibility

Authorized Organization choices/context include current display name while exact Organization ID remains the authorization selector.

### E. Public listing visibility

Every successfully rendered public listing visibly identifies its publishing Organization outside any optional VAT/tax block.

### F. Legacy compatibility

A public listing whose accepted publishing Organization ID has no actor-directory row remains readable and uses exact ID as display fallback rather than becoming 404.

### G. Mutable presentation only

Changing Organization display name changes current presentation only. It must not mutate/revise/re-identify the NativeListing.

### H. Safe rendering

Display name remains escaped plain text; no raw HTML.

### I. Branding invariant

Specific available Organization identity is not replaced by a generic broker label. No media transformation is added; future media remains bound by the accepted no-branding-erasure rule.

## Deliverables

1. migration/schema support for MarketplaceOrganization public display name;
2. persistence helpers/read projection;
3. Broker Workspace read model/API/web updates;
4. public NativeListing read model/API/web updates;
5. focused unit/persistence/API/web tests;
6. retained real PostgreSQL 18 + FastAPI + built Astro proof;
7. CI execution of the retained proof;
8. handoff to REVIEW, never DONE.

## Acceptance criteria

- [ ] Existing MarketplaceOrganization ID/category/eligibility behavior is unchanged.
- [ ] Existing rows receive a deterministic non-empty display-name backfill.
- [ ] Explicit human-readable display name can be persisted/re-read.
- [ ] Empty/whitespace-only/control-character/over-limit names are rejected.
- [ ] Legitimate punctuation/corporate suffixes are preserved.
- [ ] No second Organization identity/table is introduced for publisher identity.
- [ ] Broker context API includes current display name.
- [ ] Broker Workspace chooser visibly renders display name.
- [ ] Explicit Organization workspace visibly renders display name.
- [ ] Authorization remains keyed by exact Organization ID/current membership/MFA.
- [ ] Public listing API exposes exact publisher ID + display name.
- [ ] Public listing identity is present when VAT claim is absent.
- [ ] Public Astro listing visibly renders publisher identity outside optional VAT markup.
- [ ] Malicious HTML/script-like name is inert/escaped.
- [ ] Legacy unresolved publisher ID falls back without making listing unavailable.
- [ ] Display-name update changes presentation without NativeListing mutation/revision/lifecycle change.
- [ ] Public route canonical/noindex behavior remains unchanged.
- [ ] DRAFT/WITHDRAWN/stale/missing/incomplete behavior remains unchanged.
- [ ] Professional draft/recovery behavior remains unchanged.
- [ ] Search result semantics and criterion count remain unchanged.
- [ ] No logo/media/profile-admin/promotion/lead work is introduced.
- [ ] REQ-BROKER-023 remains PENDING until Owner Acceptance closure.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] Repository validation/lint/type-check/Python tests/web tests/check/build pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if a smaller equivalent implementation proves the contract:

- one Alembic migration after current head `a05c7e9b1f34`;
- `src/hullq/persistence/broker_identity.py`;
- bounded Organization display-name validation/helper module if useful;
- `src/hullq/application/broker_workspace_read.py`;
- `src/hullq/application/public_listing_read.py`;
- FastAPI serialization through existing routes;
- `web/src/lib/brokerApi.ts`;
- `web/src/lib/publicListingApi.ts`;
- `web/src/pages/broker/index.astro`;
- `web/src/pages/broker/organizations/[organization_id].astro`;
- `web/src/pages/listings/[native_listing_id].astro`;
- relevant persistence/API/web tests;
- retained public-listing or broker-workspace proof extension;
- CI only if needed to wire a retained proof.

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

Run/report the retained real PostgreSQL/FastAPI/built-Astro proof selected by implementation.

## Stop conditions

Stop and report rather than inventing policy if:

- implementation requires a second Organization ID/entity;
- generic Organization ontology must be silently collapsed into MarketplaceOrganization;
- display name would become an authorization key;
- public listing would need to become unavailable solely because legacy actor-directory metadata is absent;
- implementation requires media/logo storage;
- raw broker display text would be trusted as HTML;
- NativeListing immutable identity/content must change when Organization name changes;
- scope expands into profile admin, promotion, leads, analytics or Search.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, successful remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0064.
