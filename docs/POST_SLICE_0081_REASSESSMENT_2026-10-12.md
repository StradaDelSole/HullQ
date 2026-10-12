# Post-SLICE-0081 Reassessment — 2026-10-12

**Status:** REVIEWED RECONCILIATION / OWNER-SELECTED NEXT CAPABILITY  
**Canonical base checked:** `origin/main` at `1eb136c81c69f6de61c0840fcd6df1edab75a52d`  
**Last owner-accepted slice:** SLICE-0081 — completed and locally `FINISH_SLICE.bat` returned DONE.  
**Next numeric queue:** SLICE-0082 — Owner expressly authorized its readiness with “ok go”; no implementation started.  
**Scope:** second-opinion code-review triage, source-to-search end-to-end coverage, production/pilot blockers and prioritization.

## What changed since the last reassessment

The Owner supplied an external technical review dated 2026-10-12. It made a critical end-to-end observation: accepted professional Draft Promotion creates `PhysicalBoat(boat_design_ref=None)` (`src/hullq/persistence/professional_listing_promotion.py`), while accepted technical native Search enumerates only active listings with `pb.boat_design_ref IS NOT NULL` (`src/hullq/persistence/inventory_search.py`). The ordinary broker Draft/Promotion/Inventory paths have no authorized BoatDesign association action. Separate pre-existing preview/intake scripts can seed a design-linked chain but do not exercise normal broker workflow.

This is an accepted-but-unimplemented *integration capability*, **not** a SLICE-0081 regression and **not** permission to weaken fail-closed Search. SLICE-0067 expressly scoped the initial fresh-identity promotion to unlinked physical boats; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D07 already allows a **confirmed** BoatDesignRef but does not require it for promotion. `src/hullq/persistence/physical_boat.py` deliberately makes *create* immutable/idempotent and exposes no update; a separate explicit and auditable, authorized, race-safe NULL→existing-canonical-design association is the distinct remaining capability. No vague model-name inference is permitted.

### Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` (D01, D07, D08, D09, D11, D22/D29); `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `docs/DATABASE_COVERAGE_STRATEGY.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; SLICE-0067, -0069, -0072, -0081 accepted records.

**Production code inspected:** `professional_listing_promotion.py`, `persistence/physical_boat.py`, `persistence/inventory_search.py`, `application/native_inventory_query.py`, `identity_readback.py`, `application/inventory_editing.py`, professional draft payload/SSR, native listing lifecycle/current-public eligibility, API routing; for additional review findings `api/app.py`, `security/rate_limit.py`, `Dockerfile`, `Caddyfile`, `docker-compose.prod.yml`, `persistence/connection.py`, `application/lead_notification_delivery.py`, `persistence/broker_identity.py`.

- **DECIDED_AND_IMPLEMENTED:** Canonical BoatDesign FK, distinct PhysicalBoat/MarketEpisode/NativeListing identities, broker-owned draft→fresh-boat promotion, source-truthful concrete claims, publication/current-public eligibility and exactly two deterministic technical Search criteria. Secure Organization/MFA/PUBLISHER inventory access exists; an actual design association action does not. Broker dashboard (0081) is DONE.
- **DECIDED_NOT_YET_IMPLEMENTED:** An explicitly confirmed, durable association of broker marketplace inventory to an existing canonical BoatDesign; missing conventional broker onboarding; actual production notification runner/provider; future export, pre-publication Search-fit, import, periodic reports, buyer saved-search/account continuity, owner-direct, trust/privacy and relevant operational capabilities.
- **EXPLICITLY_DEFERRED:** Early SLICE-0067 design linking and existing-PhysicalBoat reuse; broad corpus ingestion, fuzzy identity resolution, fully automated classification, existing-link replacement/detach, Search-fit benchmarking, provider-console Phase 1, volume-triggered broker insights; all remain governed by respective accepted gates.
- **GENUINELY_OPEN:** Later dedicated repair/correction policy for an already established *wrong* BoatDesignRef and pilot catalog coverage threshold. Neither is guessed or implicitly implemented by one-way initial association. A review must stop rather than silently create a correction policy if one is needed.
- **CONFLICT_OR_REGRESSION:** Functional gap between normal professional-supply path and buyer technical Search; not a violation of the implementation's accepted 0067 contract. Separate production topology and operational issues below are gate evidence gaps, not a reason to retroactively invalidate accepted slice tests.

## Overall MVP / mandatory broker register reconciliation

A new explicitly tracked product obligation, `MVP-BROKER-014`, is proposed for current selection: confirmed broker `NativeListing → PhysicalBoat → BoatDesignRef` association. It is **DUE** for a genuinely useful broker-to-technical-Search vertical and is owned by SLICE-0082 readiness; do not claim IMPLEMENTED before independent implementation review and Owner acceptance. `MVP-BROKER-010` / `REQ-BROKER-026` pre-publication diagnostic remains PENDING, distinct. `MVP-BROKER-011` / `REQ-BROKER-027` bulk import remains PENDING until scaled broker onboarding; work on import must reuse the future confirmed association boundary. `MVP-BROKER-009` / `REQ-BROKER-022` export, `MVP-BROKER-008` / `REQ-BROKER-028` periodic reporting and all other due-at-launch requirements retain their existing trigger status.

**Register entries changed:** new `MVP-BROKER-014 = DUE (SLICE-0082 readiness)`; no already-accepted `IMPLEMENTED` or production/pilot gate marker changes. Search criterion count remains **2**; this is an association input to accepted Search, not a third criterion.

## External review findings retained for follow-up (separate capabilities)

The external review is evidence of potential implementation gaps, not proof of remote production behavior. Its most consequential code claims were checked against the above canonical files:

| Finding | Classification / current evidence | Required follow-up boundary |
|---|---|---|
| CR-15 design association missing | **DUE**, selected as SLICE-0082. Broker promotion writes NULL; Search excludes NULL. | Implement and real E2E prove normal broker→listing→canonical design→public Search. |
| CR-01 proxy/client-IP trust | **DECIDED_NOT_YET_OPERATIONALLY_PROVEN**. `request.client.host`; current Caddy/Uvicorn files do not explicitly configure Cloudflare→Caddy→Uvicorn client-IP trust. | Before external pilot: topology spoof-resistance and two-real-client rate-limit proof; no unrestricted forwarded-header trust. |
| CR-02 blocking I/O in `async` routes | **DECIDED_NOT_YET_IMPLEMENTED** bounded runtime execution: synchronous psycopg/Pillow/S3 in asynchronous upload/contact paths; `open_connection` connects per call. | Before external pilot: bounded concurrency/timeouts and independent liveness under slow dependencies; evaluate pooling only with explicit lifecycle/timeouts. |
| CR-03 actual email worker/provider | **EXPLICITLY_DEFERRED** by SLICE-0071's accepted notification spec; only claim/deliver once and deterministic local adapter exist. | Before external email reliance/pilot workflow needing email: durable supervised runner, delivery provider, retry/backlog observability, protection against abuse. |
| CR-16 operator broker onboarding | **DECIDED_NOT_YET_IMPLEMENTED**. Seeding helpers only, no bounded auditable operator CLI/route; broker account alone cannot create Organization/role access. | Before external pilot: auditable, least-privilege operator Organization/Membership/eligibility lifecycle without routine direct SQL. |
| CR-07 rate-limit concurrency | **REVIEW FINDING TO VERIFY**. Fixed-window `OrderedDict` has no lock; concurrent thread callers are reachable. | Couple with CR-01; adversarial concurrent tests, no lost increments or exceptions; preserve per-process and capacity semantics. |
| CR-05 Search N+1/unbounded; CR-17 public image caching | **SCALE RISKS**, current candidate read is not paginated, media endpoint fetches bytes per hit and has no explicit long-lived cache. | Before scaled traffic/import: bounded query and delivery proof; preservation of availability/withdrawal/access revocation. |
| CR-06 startup configuration, CR-09 buyer anti-abuse, CR-10 media orphan cleanup | **PENDING / TRIGGERED** as applicable; runtime/config/deletion semantics need focused review. | Before applicable production data/email/traffic triggers; do not silently apply unsafe TTL or cache policies. |
| CR-04 giant API router / CR-11 typing / CR-13 image hygiene | **TECHNICAL DEBT**, not gating currently authorized internal/synthetic product work. | Incremental isolated refactoring, not an unrelated mandatory prerequisite to 0082. |

Additional external-production obligations remain: buyer contact verification/abuse controls (`MVP-BUY-009/010`); operator/privacy retention/deletion/access (`MVP-OPS-001/002/007`, `MVP-PRIV-003/004/005`); communications `MVP-COMMS-001…007`; real provider secrets/edge/HA/B2 and production readiness. **These must not be treated as passed simply because the security gate or CI passed.** Explicitly before the first real personal lead, assess enforceable retention/deletion and permitted access, not merely later public-launch wording.

## Priority and distance to a meaningful first visible listing

- **Next selected outcome:** CR-15 broker confirmed design association to unlock **an actually broker-created and publicly Search-discoverable NativeListing** (SLICE-0082). This is a coherent one-capability bridge.
- **Estimated remaining slice distance for the internal/synthetic end-to-end technical Search listing after 0082:** **0**, if the contract's E2E proof succeeds; otherwise this slice must fail acceptance. Broader model coverage and Search-fit guidance are separate.
- **Estimated remaining slice distance to first real externally exposed broker listing:** not responsibly reducible to one number: actual Phase 1–7 operator/provider readiness, prospective pilot scope, production-data/privacy/mailing gates and provider/HA evidence are incomplete. No exposure authorized until applicable gates PASS.
- **Why not generic infrastructure first?** CR-15 blocks the current *core product* result even with flawless hosting; Owner selected product-first development. Runtime and onboarding repairs are still high-priority before any real external broker activity, and no related pilot gate is waived.
- **Why not bulk import first?** Import without established, evidence-correct design association would create technically undiscoverable professional inventory.
- **Why not Search-fit first?** Preview alone cannot turn a real unlinked physical boat into a technical Search candidate. More complete broker fact entry can follow later without changing Search semantics.
- **Why not refactor first?** No measured blocker requiring a broad API rewrite. Avoid multiplying unchanged security-sensitive paths for no direct product outcome.

## Trigger / production boundary check

`POST_0051_ARCHITECTURE_RECONCILIATION = PASS` remains the canonical marker. `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2`. Broker Launch Gate and prior adversarial-gate status remain PASS as *historical accepted scope*, but production deployment/topology behavior needs real external proof before pilot. `PRODUCTION_READINESS_GATE_STATUS = IN_PROGRESS`; `PRODUCTION_LAUNCH_PACK_PHASE = NOT_STARTED`, real external broker/owner data = NOT_PRESENT, pilot and public launch = NOT_STARTED. No production infrastructure spend or exposure is authorized by selecting SLICE-0082. The selected development feature is executed using disposable local synthetic data.

## Follow-up

Write independently reviewed `SLICE-0082-broker-listing-boatdesign-association.md` readiness on a separate docs branch. Its only owned new domain behavior is explicit first-time one-way association of an **existing** broker-owned `PhysicalBoat` (obtained through the exact NativeListing→MarketEpisode→PhysicalBoat chain) with one existing canonical BoatDesign. Unresolved remains valid; existing linked identity is never silently changed. A later wrong-link correction is separate decision/readiness. Real browser/API/DB/Search proof is mandatory. Merge readiness only after independent review plus exact-head CI; then run `START_SLICE.bat` for 0082. Do not start coding on this docs branch.
