# HullQ — Post-SLICE-0053 / Post-Pivot Reassessment

**Date:** 2026-09-14  
**Status:** READY FOR INDEPENDENT REVIEW  
**Canonical base inspected:** `f80e8d870e01c15484342ffdd3e464420ad45769`  
**Purpose:** select the smallest highest-leverage capability after the owner-direct marketplace rebaseline without weakening accepted Broker Workspace, Search, identity, truth or production gates.

## 1. Reassessment result

Select **SLICE-0054 — Authenticated Owner-Direct Listing Draft Workspace**.

The capability is:

```text
authenticated HullQ Account
→ create private owner-direct draft
→ save bounded seller-entered draft data
→ list/reopen own drafts
→ update with stale-write protection
→ remain private and non-marketplace
```

The draft is deliberately **not** a `NativeListing` and is not yet publishable.

No owner-direct publication, phone verification, right-to-list attestation, fraud/risk escalation, representation-conflict resolution, media, broker referral, Search exposure or transaction flow is selected by this reassessment.

## 2. Controlling product direction inspected

The reassessment checked the accepted owner-direct pivot:

- `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`;
- `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`;
- `docs/PRODUCT_EXECUTION_PLAN_OWNER_DIRECT_RECONCILIATION_2026-09-14.md`;
- `docs/PROJECT_STATE.md`;
- current architecture and Search/SEO architecture.

Controlling consequences:

1. HullQ is broker-first mixed supply, not broker-only.
2. Existing professional write boundaries remain intact until a distinct owner-direct capability exists (`REQ-PRIVATE-022`).
3. Current market identities remain distinct (`REQ-PRIVATE-023`).
4. Organic Search remains commercially independent (`REQ-PRIVATE-003`).
5. The normal future **publication** gate remains account + verified phone + right-to-list attestation + baseline anti-abuse checks (`REQ-PRIVATE-006`); those checks are not prerequisites for a private unpublished draft.
6. Seller verification does not establish technical vessel truth (`REQ-PRIVATE-012`).

## 3. Trigger gates inspected

Canonical records:

- `docs/governance/POST_0051_TRIGGER_GATES.md`;
- `docs/governance/PRODUCTION_READINESS_GATE.md`;
- `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`;
- `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`.

Current state on the inspected base:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 1
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: NOT_DUE

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
```

No Broker Workspace mandatory commitment is currently `DUE`. `REQ-BROKER-023` and `REQ-BROKER-024` remain `PENDING` and mandatory before the later Broker Workspace Launch Gate can pass, but current governance does not require either to be the immediate next slice.

SLICE-0054 stores only synthetic/local-development draft data under the current execution boundary and does not activate real external marketplace production data, a production pilot or public production launch. Therefore Production Readiness remains `NOT_TRIGGERED`.

The slice adds no technical native Search criterion.

## 4. Repository reconciliation

### 4.1 Authentication is reusable without Organization membership

SLICE-0053's signed browser session carries a durable HullQ `AccountId` and authentication evidence only. It deliberately contains no Organization, membership or role claims.

That makes the accepted authentication/session primitive suitable for an owner-direct account even when that account belongs to zero professional Organizations.

The existing `/api/broker/...` endpoints continue to apply professional tenant authorization separately. SLICE-0054 must not weaken that separation.

One bounded adaptation is required: the accepted login-state `next` allowlist currently accepts only `/broker...`. SLICE-0054 may add the exact owner-direct route prefix selected by its contract while preserving internal-path allowlisting and open-redirect protection. Broad arbitrary redirect support is not authorized.

### 4.2 Existing NativeListing persistence is intentionally professional

Current `src/hullq/persistence/native_listing.py` and the SLICE-0043 contract bind `NativeListing` creation to:

```text
AccountId
+ exact eligible professional MarketplaceOrganization
+ exact ACTIVE publishing-capable OrganizationMembership
```

The persisted envelope includes non-null `publishing_organization_id`, and current lifecycle/offer paths continue to assume that professional principal.

Therefore this reassessment rejects a shortcut such as:

```text
private seller
→ publishing_organization_id = NULL
→ reuse professional NativeListing writer
```

It would silently change accepted persistence, authorization, lifecycle and public/Search semantics in one step.

### 4.3 A mutable pre-market draft is the safer boundary

SLICE-0054 instead introduces a dedicated private work object:

```text
OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

The draft records user-entered work-in-progress only. It creates none of the market identities above and creates no canonical marketplace claim/evidence row.

A later separately selected capability may admit/transform an eligible draft into marketplace identities only after the appropriate owner-direct publication/trust boundary has been implemented. That later admission must preserve provenance and mint/use the correct distinct market identities; it may not reinterpret a draft ID as a NativeListing ID.

### 4.4 Existing field semantics provide a bounded useful draft

`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` already defines neutral structured topics sufficient for a useful initial seller draft:

- `physical_boat.marketed_brand_claim`;
- `physical_boat.model_designation_claim`;
- `physical_boat.build_year`;
- `physical_boat.boat_name`;
- `listing_offer.asking_price_mode`;
- `listing_offer.asking_price_amount`;
- `listing_offer.currency`;
- `listing_offer.location_country`;
- `listing_offer.location_region`.

SLICE-0054 may reuse those identifiers as **draft input keys**, with syntax/conditional validation when values are present. Draft storage does not promote them to marketplace facts or claims.

The broker-specific narrative keys (`broker_summary`, `broker_description`) are not repurposed for a private seller in this slice.

Requiredness in the marketplace registry is an eventual admission/completeness concern. A draft must remain savable while incomplete; otherwise it is not a useful draft.

## 5. Alternatives considered

### A. Generalize `NativeListing` principal now

**Rejected for SLICE-0054.**

A tagged professional-Organization/owner-Account principal may become appropriate later, but doing it now would touch NativeListing persistence, lifecycle, offer revisions, public reads, Search assumptions and transition audit semantics before owner publication is even available.

That is too much structural change for the first owner-direct capability and risks weakening the proven professional lane.

### B. Pure owner-direct eligibility function

**Rejected as the next capability.**

It would be safe but mostly internal and would not give a seller a usable product surface.

### C. Seller-choice landing page only

**Rejected as too thin.**

The pivot already establishes self-list vs voluntary broker referral. A page that merely repeats that choice but cannot preserve seller work creates a dead-end rather than proving the new lane.

### D. Broker Workspace `REQ-BROKER-023` or `REQ-BROKER-024`

**Deferred, not dropped.**

Both remain mandatory for the Broker Workspace Launch Gate. Neither is currently due, and the just-accepted marketplace pivot creates a higher-leverage immediate need to establish the distinct owner-direct write boundary required by `REQ-PRIVATE-022`.

## 6. Selected capability boundary

SLICE-0054 should provide exactly one visible capability:

> **An authenticated private seller can create, save, list, reopen and update their own private owner-direct sale draft in a browser, and no other account can read or modify it.**

The seller sees an explicit `DRAFT — NOT PUBLIC` state. No publish action exists in this slice.

The minimal draft payload is bounded by `specs/OWNER_DIRECT_DRAFT_CONTRACT.v0.1.md`.

## 7. Security boundary

The capability uses the existing signed HullQ session and durable `AccountId`.

Hard requirements for the new write surface:

- unauthenticated draft access fails closed;
- draft ownership is enforced server-side by FastAPI/PostgreSQL, never by hidden UI fields;
- a foreign/unknown draft identifier is non-enumerating on read/update;
- state-changing browser requests have an explicit CSRF defense in addition to authentication;
- Astro remains presentation/proxy only and may not become a second authorization or validation backend;
- no session token or sensitive auth material is exposed to browser JavaScript or rendered HTML;
- private draft pages/API responses are `private, no-store` and `noindex` where applicable.

## 8. Concurrency / recovery boundary

SLICE-0054 is not the full connectivity-resilient draft system described by Broker `REQ-BROKER-024` and does not promise offline recovery/autosave.

It does, however, prevent silent same-draft overwrite:

```text
create -> version 1
update(expected_version=N) -> version N+1
stale expected_version -> conflict, no write
```

This is bounded optimistic concurrency for correctness, not a generic draft framework.

## 9. Explicit non-effects

Acceptance of SLICE-0054 must not change any of these states:

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 1
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
REQ_BROKER_023_STATUS = PENDING
REQ_BROKER_024_STATUS = PENDING
```

It also must not make owner-direct inventory public or Search-eligible.

## 10. Decision

**Selected next capability:** `SLICE-0054 — Authenticated Owner-Direct Listing Draft Workspace`.

Readiness may proceed against the dedicated draft contract. No implementation work or next-slice start is authorized merely by this reassessment document.