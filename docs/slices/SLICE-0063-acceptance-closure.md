# SLICE-0063 — Acceptance Closure

**ID:** SLICE-0063  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #238  
**Accepted implementation HEAD:** `32077952b3b921c95b506615e1c1a947fbec7ef9`  
**Implementation merge commit:** `7f009564fd8acdbd1e4da1545deb1bde49632fff`  
**Independent exact-head ACCEPT review:** 2026-09-22  
**Owner acceptance:** explicitly recorded 2026-09-22

## Accepted capability

SLICE-0063 closes the bounded v0.1 form of REQ-BROKER-023 for explicit publishing Organization identity and textual branding preservation:

```text
existing MarketplaceOrganizationId
+ bounded current public_display_name
→ clear publisher identity in authorized Broker Workspace context
→ clear publisher identity on every readable public NativeListing
→ publisher visibility independent of optional VAT/tax claims
→ no second Organization identity
```

`MarketplaceOrganizationId` remains the sole professional publishing-principal identity. `public_display_name` is mutable presentation metadata only: it is not legal/KYB verification, not a Brand/Marque identity and never an authorization key.

## Accepted implementation behavior

The accepted implementation includes:

- one `public_display_name` column on the existing `marketplace_organizations` row;
- no second publisher/Organization identity table;
- deterministic migration of existing rows to exact `organization_id` display fallback;
- non-null persistence after migration;
- bounded display-name validation with a 200-character post-normalization maximum;
- leading/trailing whitespace normalization at the accepted write boundary;
- preservation of legitimate internal spacing, punctuation, capitalization and corporate suffixes;
- rejection of empty/whitespace-only names;
- rejection of over-limit names after normalization;
- Unicode-aware rejection of control characters through Unicode category `Cc`, covering ASCII C0, DEL and Unicode C1 controls;
- ordinary accented/international Unicode Organization names remain accepted;
- normalized display names are stored back on the domain object and therefore persisted consistently rather than merely validated;
- internal/test Organization provisioning supports explicit human-readable display names;
- a dedicated display-name update helper changes only current presentation metadata;
- Broker Workspace context/list surfaces expose the current display name while authorization remains exact Organization ID + current membership/roles/MFA;
- public NativeListing read projection exposes exact publishing Organization ID plus current display name;
- public publisher identity is visible independently of VAT/tax and PhysicalBoat optional claims;
- built Astro public listing visibly renders `Listed by {display name}` outside optional VAT markup;
- publisher display name is escaped plain text and never trusted raw HTML;
- current actor-directory display name is reflected without mutating the NativeListing;
- legacy/unresolved publishing Organization IDs remain publicly readable through exact-ID display fallback;
- display-name-only updates do not change NativeListing ID, canonical URL, immutable content, offer revision, lifecycle, freshness or Search truth;
- public listing canonical/noindex behavior remains unchanged;
- DRAFT/WITHDRAWN/stale/missing/incomplete public-read behavior remains unchanged;
- no logo/media upload, public broker profile, Organization self-service admin, promotion, leads, analytics, payments or Search expansion.

## Independent review and amendment

Initial implementation exact head:

```text
5a361af6cc0312becdfd64d516fc7e9de4ed8d08
```

Independent exact-head review found two blocking validation/persistence gaps:

1. `MarketplaceOrganization.__post_init__()` validated the normalized display name but discarded the returned normalized value, allowing the raw pre-normalization string to reach persistence;
2. display-name control-character validation rejected only ASCII C0 + DEL and therefore allowed Unicode C1 controls such as U+0085/U+009F.

The amendment exact head:

```text
32077952b3b921c95b506615e1c1a947fbec7ef9
```

closed both findings by:

- storing the normalized display name back on the frozen MarketplaceOrganization domain object through `object.__setattr__`;
- making all downstream readers/persistence paths observe exactly the bounded normalized value that was validated;
- rejecting Unicode category `Cc` control characters rather than only ASCII ranges;
- adding focused unit/domain/persistence tests for boundary whitespace, exact 200-character persistence, 201-character rejection, punctuation/corporate suffix preservation, C0/DEL/C1 rejection and ordinary accented Unicode acceptance.

Independent delta re-review returned **ACCEPT** with no unresolved implementation finding.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- MarketplaceOrganizationId remains the sole professional publishing-principal identity
- marketplace_organizations carries bounded current public_display_name presentation metadata
- existing Organization rows receive deterministic exact-ID display fallback on migration
- explicit display names normalize consistently before persistence
- empty/whitespace-only/over-limit/control-character display names are rejected
- legitimate Unicode names, punctuation and corporate suffixes are preserved
- display name never acts as an authorization selector
- Broker Workspace exposes current human-readable Organization identity
- public NativeListing API exposes exact publisher ID + current display name
- public listing publisher visibility is independent of optional VAT/tax claims
- Astro renders display identity as escaped plain text
- legacy unresolved publisher IDs remain readable through exact-ID display fallback
- display-name changes do not mutate NativeListing identity/content/offer/lifecycle/freshness/Search
- public listing canonical/noindex behavior remains unchanged
- REQ-BROKER-023 is now implemented
- REQ-BROKER-024 remains implemented
- technical native Search criterion count remains exactly 2
- organic Search commercial independence remains mandatory

DECIDED_NOT_YET_IMPLEMENTED
- professional draft → marketplace promotion transaction
- professional NativeListing publication from draft
- publish/withdraw/reconfirm controls in the broker authoring flow
- broker logo/media/gallery workflow
- public broker/Organization profile pages and slugs
- Organization self-service administration / legal-name or KYB workflow
- leads/contact/CRM and attribution
- sale/outcome workflow
- broker analytics / engagement reporting
- inventory portability/export
- bulk onboarding/import
- Search exclusion explainability and pre-publication Search-fit diagnostics
- privacy-safe aggregate demand insights
- payments/entitlements
- owner-direct marketplace publication/admission
- buyer account persistence / persistent Shortlist
- Saved Search / monitoring / alerts
- third technical Search criterion

EXPLICITLY_DEFERRED
- logo upload/storage
- media/gallery pipeline
- broker watermark manipulation
- public broker profile page / Organization slug
- Organization self-service profile editing
- legal-name/KYB verification
- address/phone/email/website/social profile fields
- office hierarchy
- all unrelated promotion/leads/analytics/Search/payment/pilot/public-launch work named by the 0063 contract

GENUINELY_OPEN
- exact future Organization self-service/admin model
- whether later Organization identity includes legal name separately from public display name
- future logo/media asset model and rights pipeline
- eventual public broker profile URL/slug architecture
- exact professional draft-to-marketplace promotion transaction
- buyer Free/Pro durable continuity semantics

CONFLICT_OR_REGRESSION
- none found on the accepted exact head
```

The generic `specs/ORGANIZATION_SCHEMA.v0.1.json` remains distinct from the MarketplaceOrganization publishing principal; SLICE-0063 did not silently collapse those identity models.

## Exact-head verification

Remote verification on exact accepted HEAD `32077952b3b921c95b506615e1c1a947fbec7ef9`:

```text
CI run 35691401135 / #855 → SUCCESS
Manufacturer artifact reproducibility run 35691401134 / #577 → SUCCESS
```

All exact-head GitHub gates completed successfully:

- `dependency audit`;
- `web quality (Astro/Node)`;
- `quality (ubuntu-latest)`;
- `quality (windows-latest)`;
- `db integration (PostgreSQL 18)`;
- `reproduce (ubuntu-latest)`;
- `reproduce (windows-latest)`.

The implementation agent's final local report recorded:

```text
repository validation: PASS
ruff format/check: PASS
mypy: PASS (112 files)
non-DB pytest: 4598 passed / 733 skipped
PostgreSQL 18 persistence/full tests: 730 passed / 1 pre-existing unrelated skip
web tests: 216 passed
Astro check/build: PASS
publishing Organization public identity retained proof: PASS
```

The retained proof `scripts/inspect_publishing_organization_public_identity.py` uses a real disposable PostgreSQL 18 schema, real local OIDC/JWKS authorization-code login, FastAPI and built Astro SSR over real HTTP.

It proves:

1. migration/seed of an eligible MarketplaceOrganization with human-readable display name;
2. display name on authorized Broker Workspace surfaces;
3. public ACTIVE current NativeListing for that Organization;
4. representative case with VAT/tax claim absent;
5. FastAPI exact Organization ID + display name;
6. built Astro publisher rendering despite absent VAT claim;
7. malicious script-like display name remains escaped/inert;
8. display-name-only update;
9. same NativeListing ID/URL and unchanged offer/lifecycle transition history after rename;
10. unresolved legacy publishing Organization exact-ID fallback remains readable;
11. DRAFT/unknown/WITHDRAWN public-read behavior remains not-found;
12. ordinary API/web logs do not contain the test client/session secrets.

The exact SLICE-0063 retained real-HTTP vertical proof passed inside CI #855.

PR #238 merged the exact accepted implementation to `main` as:

```text
7f009564fd8acdbd1e4da1545deb1bde49632fff
```

## Broker mandatory-register state after acceptance

SLICE-0063 closes REQ-BROKER-023.

Canonical register state becomes:

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING
SCALED_BROKER_ONBOARDING_STATUS: NOT_STARTED
SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS: NOT_REACHED
POST_PILOT_REAL_BROKER_VALIDATION_STATUS: NOT_STARTED

REQ_BROKER_022_STATUS: PENDING
REQ_BROKER_023_STATUS: IMPLEMENTED
REQ_BROKER_024_STATUS: IMPLEMENTED
REQ_BROKER_025_STATUS: PENDING
REQ_BROKER_026_STATUS: PENDING
REQ_BROKER_027_STATUS: PENDING
REQ_BROKER_028_STATUS: PENDING
REQ_BROKER_029_STATUS: PENDING
REQ_BROKER_030_STATUS: IMPLEMENTED
```

The two addendum launch/pilot-baseline commitment statuses REQ-BROKER-023 and REQ-BROKER-024 are now both implemented.

This does **not** independently make the Broker Workspace Launch Gate `PASS`. The remaining launch-gate capability/evidence checklist in `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md` remains controlling, so the gate stays `NOT_READY` and broker self-service pilot stays `NOT_STARTED`.

## Trigger-gate state after acceptance

SLICE-0063 adds no technical Search criterion and introduces no external production data, pilot, paid plan or public launch.

Canonical trigger state remains:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0063
PROJECT_STATE_QUEUE_SLICE:    0064
```

SLICE-0064 remains **UNSELECTED**.

The queue number does not authorize implementation, readiness, `START_SLICE.bat` or a capability choice. Before any 0064 selection or material product/domain/data/architecture decision, a fresh post-SLICE-0063 repository/product reassessment and Decision / Implementation Reconciliation are required.

## Product execution checkpoint

HullQ's accepted professional provider/public identity path now includes:

```text
Auth0-compatible login
→ durable HullQ Account
→ current Organization/Membership/MFA authorization
→ explicit MarketplaceOrganization
→ current human-readable public_display_name presentation metadata
→ Organization-owned NativeListing inventory
→ private ProfessionalListingDraft workspace
→ resumable create/list/read/update with optimistic concurrency
→ bounded browser-local recovery for recent unsaved edits
→ public NativeListing visibly identifies current publishing Organization
→ explicit Save remains the only durable draft mutation
→ no implicit promotion to marketplace truth
```

The public publisher identity layer improves broker trust/clarity without introducing a second Organization identity, changing authorization, or mutating listing/Search truth.

## Closure decision

```text
SLICE-0063 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0063
PROJECT_STATE_QUEUE_SLICE = 0064
REQ_BROKER_023_STATUS = IMPLEMENTED
REQ_BROKER_024_STATUS = IMPLEMENTED
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
