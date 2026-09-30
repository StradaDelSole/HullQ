# SLICE-0072 — Post-Promotion Inventory Editing & Maintenance

**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker launch path — broker edits / maintains inventory  
**Depends on:** SLICE-0071 owner-accepted / DONE  
**Normative contract:** `specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md`

## Capability

Deliver one coherent recurring broker outcome:

```text
existing Organization-owned NativeListing
→ open inventory detail editor
→ revise offer / price
→ revise concrete-yacht claims
→ immutable revision history + current heads
→ authoritative readiness/public/Search re-read
```

No second listing truth store is introduced.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One recurring broker job: maintain an existing professional listing.

**VISIBLE-RESULT CHECK:** PASS  
The broker can change price/details safely and immediately see the authoritative result.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Directly advances Broker Workspace Launch Gate §2 after creation/media/publication/leads are already implemented.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Existing revisioned NativeListing offer and Organization PhysicalBoat claim persistence are reused. Lifecycle/media/draft paths remain separate.

**TRIGGER GATES CHECK:** PASS  
No production pilot/provider/payment activation and no Search criterion are introduced.

## Decision / implementation reconciliation

**Accepted records checked:** docs/PROJECT_STATE.md; docs/slices/SLICE-0071-acceptance-closure.md; docs/POST_SLICE_0071_REASSESSMENT_2026-09-30.md; specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md; docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md; docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md; docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md; docs/governance/POST_0051_TRIGGER_GATES.md; current NativeListing offer / PhysicalBoat claim / lifecycle / publication-readiness contracts.  
**Production implementation checked:** current revisioned NativeListing offer persistence; current revisioned Organization PhysicalBoat claim persistence; Broker Workspace inventory read/lifecycle/media surfaces; professional promotion application path; D22 PublicationReadiness / D29 CurrentPublicEligibility evaluators; current Search/public listing read paths.  
**Already implemented / not re-decided:** marketplace identities; Organization ownership; Broker Workspace auth/current-membership/MFA; immutable revision history + explicit heads; publish/withdraw/reconfirm; media; promotion; current-public eligibility; Lead operations.  
**Exact remaining gap:** existing promoted inventory can be viewed and lifecycle/media-managed but current offer/price and current Organization PhysicalBoat claims cannot be maintained through an authorized Broker Workspace editor.  
**Accepted-but-unimplemented obligations:** REQ-BROKER-003/004 recurring edit workflow; Broker Workspace Launch Gate §2 edit price/status/details job; later usability/competitive benchmark evidence; buyer-contact email verification and production-provider work remain separate later obligations.  
**Material classifications:** DECIDED_AND_IMPLEMENTED foundations; DECIDED_NOT_YET_IMPLEMENTED 0072 editing surface + later launch commitments; EXPLICITLY_DEFERRED sale/outcome/bulk/alerts/analytics/owner-direct; GENUINELY_OPEN implementation-local factoring; CONFLICT_OR_REGRESSION none.

### DECIDED_AND_IMPLEMENTED foundations

- professional inventory ownership/auth/MFA;
- revisioned current NativeListing offer truth;
- revisioned current Organization PhysicalBoat claim truth;
- draft promotion;
- lifecycle/freshness controls;
- publication readiness/current-public eligibility;
- media management;
- Lead operations.

### DECIDED_NOT_YET_IMPLEMENTED — owned by 0072

- private existing-inventory detail editor;
- current offer read/edit through existing offer revisions;
- asking-price change workflow;
- current Organization PhysicalBoat claim read/edit through existing claim revisions;
- optimistic-concurrency browser/API handling;
- ACTIVE hard-invariant protection;
- authoritative post-save readiness/public/Search re-read;
- retained end-to-end edit proof.

### DECIDED_NOT_YET_IMPLEMENTED — mandatory later

- buyer-contact email verification;
- production email provider;
- sale/outcome;
- broker engagement/performance reporting;
- portability/export;
- Search-fit diagnostics;
- bulk onboarding/import;
- usability and competitive benchmark evidence.

### EXPLICITLY DEFERRED

- media redesign;
- lifecycle redesign;
- MarketEpisode correction/reassignment;
- duplicate/relist/clone;
- owner-direct publication/editing;
- bulk editing/import/export;
- price alerts;
- generalized analytics;
- new Search criteria.

### GENUINELY_OPEN

Implementation-local route/module names, form grouping, exact mutation DTOs, bounded page composition and revision-id minting details.

### CONFLICT_OR_REGRESSION

None found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Buyer contact email verification:** PENDING  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** NOT_READY

## Mandatory invariants

1. Existing revision stores remain authoritative.
2. Prior revisions remain immutable.
3. Current heads are explicit, never inferred from row order.
4. Cross-Organization access/mutation remains non-enumerating.
5. Current membership/MFA truth is checked fresh.
6. Draft truth is not rewritten after promotion.
7. Offer edits do not mutate PhysicalBoat claims and vice versa except through explicit separate accepted writes.
8. Price change does not alter lifecycle/freshness/sale outcome.
9. WITHDRAWN is not republished by editing.
10. ACTIVE edits may not knowingly leave a broken hard current-public invariant.
11. Valid technical claim edits may legitimately change deterministic Search results.
12. Media truth remains untouched.
13. Lead truth remains untouched.
14. Technical native Search criterion count remains exactly 2.

## Scope

Implementation may span:

- inventory detail read projection;
- authorized offer revision application path;
- authorized PhysicalBoat claim revision application path;
- ACTIVE candidate/current-public safety evaluation;
- FastAPI private broker routes;
- Astro Broker Workspace inventory detail/editor;
- browser API/CSRF helpers;
- concurrency/idempotency tests;
- retained PostgreSQL + FastAPI + built Astro proof.

## Readiness stop conditions

Stop for reassessment if implementation requires:

- new marketplace truth model;
- lifecycle or sale/outcome redesign;
- MarketEpisode/PhysicalBoat identity reassignment;
- weakening optimistic concurrency;
- bypassing D22/D29;
- direct Search-result mutation;
- owner-direct publication changes;
- a third technical Search criterion.

## Acceptance

Independent exact-head review must verify authorization/tenancy, revision concurrency/idempotency, ACTIVE invariant safety, draft/media/Lead isolation and retained vertical proof.

Owner Acceptance remains mandatory before implementation merge.

Initial implementation prompt must come only from `START_SLICE.bat` after readiness review, remote gates and readiness merge.

## Completion report

### Slice

- Slice ID: `SLICE-0072`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`
- Exact final branch HEAD SHA: `f599e745a90a62f57a183ecc747b26a9519e46dc`

### Product execution checks

- ONE-CAPABILITY CHECK: `PASS`
- VISIBLE-RESULT CHECK: `PASS`
- PRODUCT EXECUTION PLAN ALIGNMENT: `PASS`
- REPOSITORY RECONCILIATION CHECK: `PASS`
- TRIGGER GATES CHECK: `PASS`

### Changes

- Changed files: `src/hullq/domain/inventory_edit_request.py` (new — JSON request parsers), `src/hullq/persistence/inventory_editing.py` (new — atomic offer/claim revision write + narrowed ACTIVE-invariant re-check), `src/hullq/application/inventory_editing.py` (new — read model + auth orchestration), `src/hullq/api/app.py` (new CSRF header + 3 routes: GET `.../edit`, POST `.../offer`, POST `.../claim`), `web/src/lib/inventoryEditingApi.ts` (new), `web/src/pages/.../inventory/[native_listing_id]/edit.astro` (new editor page), `web/src/pages/.../inventory.astro` (added "Edit" link).
- Acceptance work completed: existing offer/claim revisioned truth stores exposed as broker-editable via optimistic concurrency (`expected_current_revision_id`) + client-supplied idempotency (`revision_id`, mirroring SLICE-0064's `confirmation_id` pattern); cross-Organization access non-enumerating (404); ACTIVE listings get an in-transaction atomic hard-invariant re-check (deliberately D29-based, not D22 — D22 unconditionally blocks non-DRAFT listings via `LIFECYCLE_NOT_DRAFT` and would reject every ordinary ACTIVE edit) that rolls back the just-written revision on violation; media/Lead/lifecycle untouched by this slice.
- Tests/fixtures added or updated: 16 PostgreSQL-backed API tests (`test_broker_inventory_editing_api.py`) covering tenancy, CSRF, stale/idempotent/collision concurrency, inactive-membership freshness, and the ACTIVE-invariant atomic-rollback path; 26 pure unit tests for the request parser; 9 Node `node:test` tests for the TypeScript API client.

### Validation

- Local validation: `PASS`
- Commands/results: `ruff check` on all new/changed Python clean; full backend suite `uv run pytest` (via `claude_diag.py run-local-test-db-compact`) — 5854 passed, 3 skipped, 0 failed (39m36s), including the new 42 tests; web `npm run build`/`npm run check` clean; web `npm test` — 354 passed, 0 failed.

### External verification

- Remote CI: `NOT VERIFIED`
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings: none.
- Spec/ADR ambiguities: contract §7 says "re-evaluate the accepted publication/current-public requirements" without naming D22 vs. D29 explicitly; D22 is unusable as-is for an ACTIVE-state re-check (it always blocks non-DRAFT via `LIFECYCLE_NOT_DRAFT`), so this implementation uses D29 narrowed to the offer/claim/chain/org-eligibility dimensions an edit's candidate heads can actually affect, deliberately excluding freshness/cover (out of scope per contract §6/§11) — documented in `inventory_editing.py`'s module docstring.
- Scope deviations: none. The client-supplied `revision_id` field (mirroring SLICE-0064's `confirmation_id`) was added to the wire contract beyond the spec's literal text so genuine network-level retries resolve deterministically per contract §5 — this is an implementation-local wire-shape decision within the slice's "GENUINELY_OPEN" scope, not a policy change.

### Follow-up

- Recommended next action: independent exact-head review per the slice's acceptance criteria (authorization/tenancy, revision concurrency/idempotency, ACTIVE invariant safety, draft/media/Lead isolation, retained vertical proof), then Owner Acceptance.

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.

## Amendment 1 — review findings A/B

### Amendment

- Previous reviewed HEAD: `f599e745a90a62f57a183ecc747b26a9519e46dc`
- Exact new HEAD: `d851efb4b51f649744a864363fb3f34f47d76d59`
- Findings addressed:
  - **Finding A** (missing retained vertical proof): added `scripts/inspect_professional_inventory_editing.py`, a real PostgreSQL + FastAPI + built-Astro retained proof covering all 14 contract §16 items — real MFA-satisfied OIDC login, browser-driven price/claim saves with authoritative-head verification, public-truth propagation of both the new offer and the new claim, stale-mutation rejection for both offer and claim, cross-Organization non-enumeration, DRAFT/ACTIVE/WITHDRAWN mechanical separation under editing, atomic ACTIVE-invariant rollback (chain-broken ACTIVE listing), unchanged media/Lead state, and Search-criterion-count invariance (draft_max/keel_configuration only, third param → 400). Item 6 is demonstrated via the accepted public-listing-read claim projection rather than the Search candidate funnel, since a Search *confirmed-match* proof requires an unrelated BoatDesign/FieldResolution admission fixture (documented in the script).
  - **Finding B** (missing true concurrent-write proof): added `tests/persistence/test_inventory_editing_concurrency.py` — two `threading.Barrier`-synchronized, independent-`psycopg`-connection races (one offer, one claim) driving the actual SLICE-0072 `edit_native_listing_offer`/`edit_physical_boat_claim` entry points from an identical `expected_current_revision_id`; each proves exactly one `REVISED` + one `CONFLICT`, matching final current head, and an immutable-history count of exactly 2 (no lost update, no duplicate head). Optimistic concurrency was not weakened and no artificial application-layer serialization was added.
- Changed files: `scripts/inspect_professional_inventory_editing.py` (new), `tests/persistence/test_inventory_editing_concurrency.py` (new).
- Focused validation: retained proof script run for real (PostgreSQL + FastAPI + built Astro) — `PROFESSIONAL INVENTORY EDITING RESULT -> PASS`; new concurrency tests — `2 passed`.
- Final/full validation state: `PASS` — full backend suite `5856 passed, 3 skipped, 0 failed` (40m34s, includes the 2 new concurrency tests); web `npm run build`/`npm run check` clean; web `npm test` `354 passed, 0 failed`.
- Remote CI: `NOT VERIFIED`
- Remaining unresolved point(s): none.

## Amendment 2 — remote CI gate failures (PR #278)

### Amendment

- Previous reviewed HEAD: `d851efb4b51f649744a864363fb3f34f47d76d59`
- Exact new HEAD: `b22e3c9a37b2216016d1c30b29fe7152648bec8c`
- Ruff-format gate fix: ran `uv run ruff format .` — 7 files reformatted (whitespace/line-wrapping only, no semantic change): the two amendment files plus 5 files from the prior commit (`src/hullq/{application,domain,persistence}/inventory_editing.py` split, `src/hullq/domain/inventory_edit_request.py`, and two test files) that had never been run through the repository-pinned formatter. Formatting surfaced a genuine `mypy` `no-any-return` defect in `_construct` (`hullq/domain/inventory_edit_request.py`) — fixed by giving it a PEP 695 generic parameter (`def _construct[T](ctor: Callable[[], T], label: str) -> T`) instead of returning `Any`; purely a type-annotation fix, no behavior change.
- pip-audit finding: `urllib3` 2.7.0 — CVE-2026-97687, CVE-2026-97688, CVE-2026-97689 — fixed in 2.8.0. A transitive dependency (via `botocore`/`requests`, dev/tooling only), not a direct HullQ product dependency.
- Dependency remediation: `uv lock --upgrade-package urllib3` → 2.7.0 → 2.8.0, no other package changed; `uv lock --check` and `uv sync --locked --all-groups` both clean; `uv run pip-audit` now reports no known vulnerabilities (the `hullq` self-package "not found on PyPI" skip is expected/unrelated).
- Changed files: `scripts/inspect_professional_inventory_editing.py`, `src/hullq/application/inventory_editing.py`, `src/hullq/domain/inventory_edit_request.py`, `src/hullq/persistence/inventory_editing.py`, `tests/persistence/test_broker_inventory_editing_api.py`, `tests/persistence/test_inventory_editing_concurrency.py`, `tests/unit/test_inventory_edit_request_domain.py`, `uv.lock`.
- Focused validation: `ruff format --check .` / `ruff check .` / `mypy src` all clean; `pip-audit` clean.
- Full validation: `uv run python scripts/validate_repository.py` PASS; full backend `pytest` — 5856 passed, 3 skipped, 0 failed (44m49s); web `npm ci` / `npm run check` / `npm run build` clean; web `npm test` — 354 passed, 0 failed.
- Retained proof: `scripts/inspect_professional_inventory_editing.py` run for real (PostgreSQL + FastAPI + built Astro) — `PROFESSIONAL INVENTORY EDITING RESULT -> PASS` (all 14 contract §16 items).
- Remote CI: `NOT VERIFIED`
- Remaining blocker(s): none.
