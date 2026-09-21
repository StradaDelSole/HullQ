# HullQ — Post-SLICE-0062 Product / Repository Reassessment

**Date:** 2026-09-21  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `8a937a5cb3357a7258493446e827717cdbd4cbd1`  
**Selected next slice:** SLICE-0063 — Publishing Organization Public Identity

## 1. Reassessment result

Select **SLICE-0063 — Publishing Organization Public Identity**.

SLICE-0062 closed the bounded connectivity-resilient professional draft requirement and advanced:

```text
REQ_BROKER_024_STATUS: IMPLEMENTED
```

The remaining launch/pilot-baseline commitment in the Mandatory Capability Register is:

```text
REQ_BROKER_023_STATUS: PENDING
```

The current public listing surface does not satisfy that commitment cleanly:

- FastAPI exposes only `publishing_organization_id`, not a human-readable Organization display identity;
- the Astro public listing page renders that ID only inside the optional VAT/tax block;
- therefore an otherwise valid public listing with no VAT/tax claim can render with **no visible publishing Organization identity at all**;
- the private Broker Workspace also renders opaque Organization IDs rather than a human-readable Organization identity.

0063 closes that exact gap without creating a second Organization identity system or pulling media/profile administration into the slice.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already accepted and implemented; do not reopen:

- Auth0-compatible authentication is authentication-only;
- HullQ Account, MarketplaceOrganization, OrganizationMembership, roles and authorization are PostgreSQL/domain truth;
- `MarketplaceOrganizationId` is the professional publishing principal identity used by NativeListing ownership/publication;
- Organization publishing eligibility is separate from membership and MFA;
- NativeListing public read already exposes the publishing Organization ID;
- public listing truth comes only through FastAPI, never direct Astro/DB access;
- public NativeListing page identity remains `/listings/{NativeListingId}`, ACTIVE/current-market eligible only, deliberately noindex;
- private Broker Workspace Organization context is explicit and current-membership authorized;
- professional draft ownership remains exact `owner_organization_id`;
- REQ-BROKER-024 connectivity recovery is implemented;
- technical native Search criterion count remains exactly two;
- organic Search commercial independence remains mandatory.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted requirements still require:

- REQ-BROKER-023 clear publishing broker/Organization identity and preservation of legitimate broker branding;
- professional draft-to-marketplace promotion/publication;
- broker media workflow;
- leads/contact/CRM and attribution;
- sale/outcome workflow;
- broker analytics;
- export/import and other mandatory later capabilities.

The selected 0063 subset is:

> attach one bounded human-readable public display name to the existing authoritative MarketplaceOrganization row and surface that current identity consistently on authorized Broker Workspace pages and every public NativeListing page, independent of optional listing claims.

### EXPLICITLY_DEFERRED

Remain outside SLICE-0063:

- logo/image upload;
- logo asset storage or CDN pipeline;
- listing media/gallery upload/order/cover selection;
- EXIF/re-encode/quarantine/media moderation implementation;
- broker watermark creation/removal tooling;
- Organization self-service profile editing;
- legal-name/KYB verification;
- office/team profile hierarchy;
- address/phone/email/website/social profile fields;
- slug/public broker profile pages;
- professional draft promotion/publication;
- leads/CRM/outcomes/analytics;
- payments;
- Search changes;
- SEO/indexation expansion;
- production pilot/public launch.

### GENUINELY_OPEN

Remain open after 0063:

- exact future Organization self-service/admin model;
- whether later Organization identity includes legal name separately from public display name;
- future logo/media asset model and rights pipeline;
- eventual public broker profile URL/slug architecture;
- exact professional draft-to-marketplace promotion transaction;
- buyer Free/Pro continuity semantics.

### CONFLICT_OR_REGRESSION

No blocking conflict exists on canonical main.

A material repository constraint is explicit:

- `specs/ORGANIZATION_SCHEMA.v0.1.json` defines a broader generic Organization identity shape but there is no accepted durable mapping from that ontology object to `MarketplaceOrganizationId`;
- `marketplace_organizations` is already the authoritative professional publishing principal used by memberships, drafts and NativeListings.

Therefore 0063 MUST NOT silently collapse the generic Organization ontology into the marketplace publishing principal or create a parallel broker-identity entity. The public display name is bounded presentation metadata attached to the existing MarketplaceOrganization row.

## 3. Existing implementation foundation

Current broker actor directory:

```text
marketplace_organizations
- organization_id
- professional_category
- publishing_eligibility
```

Current public listing projection:

```text
publishing_organization_id
```

Current public Astro behavior:

```text
publishing organization ID is shown only inside optional VAT/tax markup
```

This means Publisher identity presentation depends incorrectly on an unrelated optional tax claim.

## 4. Selected v0.1 architecture

### 4.1 One existing Organization identity

The accepted identity remains:

```text
MarketplaceOrganizationId
```

0063 MUST NOT create a second broker/publisher Organization identifier.

### 4.2 Public display name

Add bounded presentation metadata on the existing `marketplace_organizations` row:

```text
public_display_name
```

Semantics:

- human-readable public-facing Organization/broker display label;
- not a new ID;
- not automatically a verified legal name;
- not a Brand/Marque identity;
- mutable independently of immutable NativeListing identity;
- changing it MUST NOT change NativeListing IDs, URLs, offer revisions, lifecycle or Search truth.

### 4.3 Backward compatibility

Existing actor-directory rows predate this field. Migration must deterministically backfill a non-empty display value without external lookup.

Allowed migration fallback:

```text
public_display_name := organization_id
```

for pre-existing rows where no human-readable value exists.

That fallback is compatibility metadata, not a claim that an opaque ID is the desired final broker brand name.

Current seeding/internal provisioning must support an explicit human-readable display name for representative and future real broker Organizations.

### 4.4 Public NativeListing projection

The public FastAPI listing read model MUST carry explicit publisher identity independent of VAT/tax claims.

Preferred bounded shape:

```json
"publishing_organization": {
  "organization_id": "...",
  "display_name": "Bluewater Yachts GmbH"
}
```

A flat equivalent is acceptable if mechanically unambiguous.

The current raw `publishing_organization_id` may be retained for compatibility, but the browser must not depend on the optional VAT block to show publisher identity.

### 4.5 Legacy listing compatibility

Accepted historical/synthetic NativeListings may reference a publishing Organization ID that predates or does not resolve in the later actor directory.

0063 MUST NOT silently make such otherwise-readable listings disappear solely because actor-directory metadata is absent.

For that bounded legacy case, public projection MAY fall back to:

```text
display_name = publishing_organization_id
```

while preserving the exact publishing Organization ID.

A current actor-directory row, when present, is authoritative for its current `public_display_name`.

### 4.6 Broker Workspace

Authorized Broker Workspace context should display the current Organization public display name together with the stable Organization ID where useful.

Display name is presentation metadata only. Authorization still uses exact Organization ID and current membership truth.

### 4.7 Branding preservation invariant

REQ-BROKER-023 also forbids deliberately removing legitimate broker branding merely to make HullQ appear unbranded.

0063 establishes and proves that:

- HullQ presents the current publisher name rather than replacing it with a generic "broker" label;
- punctuation/corporate suffixes/legitimate text branding are not normalized away merely for marketplace aesthetics;
- all broker-provided text remains safely escaped at presentation;
- no media transformation is introduced by this slice.

There is currently no listing media pipeline capable of stripping logos/watermarks. A future media capability MUST preserve the already-accepted invariant that compliant broker logos/watermarks are not removed solely because they are broker branding; security, rights, privacy, EXIF and media-normalization rules remain controlling.

0063 does **not** claim to implement media upload or logo asset handling.

## 5. Why 0063 is selected

### A. REQ-BROKER-023 Publishing Organization identity — SELECTED

It is now the only remaining Mandatory Capability Register item classified as a launch/pilot-baseline commitment.

It also fixes a concrete current product defect: publisher visibility depends on the presence of an unrelated optional VAT claim.

### B. Professional draft-to-marketplace promotion

Still strategically important, but current draft-to-marketplace field mapping remains incompletely reconciled and is not required to close the remaining explicit baseline branding commitment.

### C. Media workflow

Launch-critical in practice if launch listings contain media, but it is materially larger than the publisher identity defect and requires its own rights/storage/security contract.

### D. Leads/CRM/attribution

Launch-critical, but 0063 first closes the remaining explicit baseline register commitment.

### E. Broker export/Search-fit/bulk onboarding/analytics

Mandatory later, but their trigger/timing classes do not outrank the still-PENDING launch/pilot-baseline requirement.

## 6. Product success checks

### Broker

An authorized broker sees the human-readable Organization identity in the Broker Workspace rather than operating only against opaque Organization IDs.

### Buyer

Every readable public NativeListing visibly identifies who published it, regardless of whether VAT/tax metadata or other optional claims exist.

### Truth

Display name never changes Organization ownership, NativeListing identity, lifecycle, Search eligibility or verification semantics.

### Branding

A legitimate public Organization display label such as:

```text
Bluewater Yachts GmbH & Co. KG
```

must render as broker identity rather than being stripped down to a generic marketplace label.

## 7. Mandatory Capability Register effect

Before 0063 implementation acceptance:

```text
REQ_BROKER_023_STATUS: PENDING
REQ_BROKER_024_STATUS: IMPLEMENTED
```

Only after exact-head implementation review, required gates, explicit Project Owner acceptance and canonical acceptance closure may the register advance:

```text
REQ_BROKER_023_STATUS: IMPLEMENTED
```

That alone does **not** make the Broker Workspace Launch Gate PASS. The gate still requires the other launch evidence/capabilities defined by `BROKER_WORKSPACE_LAUNCH_GATE.md`.

## 8. Trigger gates

No trigger changes are caused by 0063:

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS
PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

0063 introduces no real external data, pilot, paid plan or public launch.

## 9. Decision

**Selected execution obligation:** `SLICE-0063 — Publishing Organization Public Identity`.

Readiness proceeds on `specs/PUBLISHING_ORGANIZATION_PUBLIC_IDENTITY_CONTRACT.v0.1.md`.

Implementation may not begin until the readiness package is independently exact-head reviewed, required remote gates are green and the readiness PR is merged to canonical `main`.
