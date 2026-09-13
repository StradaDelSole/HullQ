# HullQ — Broker Workspace Requirements v0.1

**Status:** ACCEPTED OWNER DIRECTION — normative product requirements when merged  
**Product direction:** `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`  
**Launch gate:** `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`

These requirements define the minimum architecture/product obligations for HullQ's professional broker workspace. They do not prescribe visual styling or authorize one oversized implementation slice.

### REQ-BROKER-001 — Broker workspace is a core product surface
HullQ MUST treat the professional broker workspace as a primary product surface rather than an internal/admin CRUD interface.

**Acceptance:** launch-readiness evidence covers broker inventory, lead and sales/outcome workflows and usability quality; public launch cannot pass the Broker Workspace Launch Gate with only operator/admin tooling.

### REQ-BROKER-002 — Known information is reused without collapsing truth scopes
HullQ MUST minimize duplicate broker input by reusing accepted Organization, BoatDesign/configuration and prior-workflow context wherever semantically safe, while preserving the distinction between design/configuration truth and concrete-yacht/listing truth.

**Acceptance:** representative create/edit flows demonstrate that known context is prefilled/referenced rather than retyped, while concrete-yacht facts requiring broker assertion remain explicit claims.

### REQ-BROKER-003 — Listing workflow is resumable and low-friction
Professional listing creation/editing MUST support a resumable, failure-safe workflow suitable for frequent broker use and MUST NOT require one monolithic all-or-nothing form.

**Acceptance:** usability proof demonstrates autosave/resume or equivalent loss prevention, bounded validation/recovery, efficient editing, and completion of a representative listing without unnecessary repeated entry.

### REQ-BROKER-004 — Inventory operations support repeated broker work
The broker workspace MUST support efficient recurring inventory operations including create, edit, publish, freshness/reconfirmation, status/price change and later safe duplicate/relist/bulk workflows as their owning capabilities are implemented.

**Acceptance:** the launch gate records which required operations are implemented and usability-tested; unsupported future operations remain explicit rather than being simulated through unsafe copying or status overloading.

### REQ-BROKER-005 — Publication, freshness, commercial state and sale outcome are distinct
HullQ MUST NOT collapse publication lifecycle, freshness/reconfirmation state, commercial/deal pipeline state and sale/outcome state into one ambiguous status value.

**Acceptance:** domain/specification artifacts represent these concepts separately, and a listing can be stale without being sold/withdrawn and can later carry an explicit commercial/sale outcome without rewriting historical publication truth.

### REQ-BROKER-006 — Sale/outcome information remains explicit and auditable
HullQ MUST support explicit professional sale/outcome recording as a separate bounded capability and MUST NOT infer a sale solely from withdrawal, disappearance or staleness.

**Acceptance:** eventual sale/outcome fixtures can retain explicit close date/outcome plus optional achieved price/source linkage where available; missing sale information remains unknown.

### REQ-BROKER-007 — Lead/contact requests are durable first-class objects
A broker lead/contact request MUST be durably representable independently of an email notification and MUST retain enough context for assignment, attribution, timeline/state and later outcome analysis.

**Acceptance:** a persisted lead can be related to the relevant NativeListing, publishing Organization, captured source context and current lead state without reconstructing those facts from an email inbox.

### REQ-BROKER-008 — Lead source attribution is preserved at capture time
HullQ MUST retain acquisition/source context for each supported lead channel at lead creation rather than attempting to reconstruct source attribution later from aggregate analytics.

**Acceptance:** lead fixtures can preserve listing/source/channel and applicable search/referrer/campaign context, with immutable captured facts distinguishable from later derived reporting.

### REQ-BROKER-009 — Broker can identify where a lead came from
The broker product MUST make lead origin understandable without requiring external spreadsheet or analytics-tool reconciliation.

**Acceptance:** the lead detail/reporting surface can answer which listing generated the lead and the available source/channel/campaign/search context for that lead.

### REQ-BROKER-010 — Lead workflow supports assignment and follow-up
HullQ MUST provide sufficient lead-workflow state to prevent generated leads from becoming untracked notifications.

**Acceptance:** a lead can be assigned, moved through a bounded status/stage model, carry notes/timeline evidence and expose whether follow-up/response has occurred; exact full-CRM scope remains bounded by owning slices.

### REQ-BROKER-011 — Response performance is measurable
HullQ MUST preserve timestamps/events required to measure broker response performance without fabricating activity.

**Acceptance:** for supported contact workflows the system can derive lead-created and first-valid-response timing, including explicit unknown/not-observed when response evidence is unavailable.

### REQ-BROKER-012 — Source-to-outcome linkage is possible
The data model MUST support later analysis from captured lead source through broker handling to offer/sale outcome where explicit evidence exists.

**Acceptance:** an eventual closed outcome can reference or be analytically joined to its originating lead/listing/source context without relying on mutable display strings.

### REQ-BROKER-013 — Broker analytics distinguish facts from derived metrics
Broker performance analytics MUST be built from explicit events/state and MUST clearly distinguish captured facts from derived funnel/conversion metrics.

**Acceptance:** a metric such as listing-view-to-lead conversion or source-to-sale conversion identifies the underlying event population and does not treat missing outcome evidence as a sale or failure.

### REQ-BROKER-014 — Organization/team context is first-class
The broker workspace MUST support the accepted HullQ Account/Organization/Membership/role model and MUST NOT assume one user account equals one brokerage.

**Acceptance:** authorization and broker-workspace fixtures can represent multiple members in one Organization with server-side role/ownership enforcement.

### REQ-BROKER-015 — Authentication does not own authorization truth
Auth0 MUST remain authentication-only; HullQ MUST enforce Organization membership, roles, listing ownership and broker-workspace authorization from HullQ-controlled domain/persistence state.

**Acceptance:** an authenticated external identity alone cannot publish/edit/assign/close broker records without matching HullQ authorization state.

### REQ-BROKER-016 — Media workflow is optimized for inventory operations
When broker media is implemented, the broker workspace MUST support practical multi-file upload/ordering/cover selection while preserving the accepted quarantine, validation, rights, privacy and durability boundaries.

**Acceptance:** representative media workflow supports bulk selection/upload and ordering without bypassing quarantine/re-encode/EXIF-removal and storage requirements.

### REQ-BROKER-017 — Core broker tasks require usability evidence
Broker-workspace launch readiness MUST include measured usability evidence for representative recurring tasks rather than code-completeness claims alone.

**Acceptance:** the launch-gate evidence records task definitions, participant/test context, task time/interaction observations, material friction findings and corrective disposition for create listing, edit/status change, lead-source inspection, lead handling and sale/outcome close-out.

### REQ-BROKER-018 — Incumbent benchmark is explicit
Before Broker Workspace Launch Gate PASS, HullQ MUST document a current comparison of the core broker workflow against at least two relevant incumbent/alternative broker systems or equivalent market workflows available for evaluation.

**Acceptance:** the benchmark names the compared systems/workflows and records where HullQ is better, equivalent or still deficient for the launch-critical tasks; unresolved material deficiency blocks PASS.

### REQ-BROKER-019 — Paid broker activation requires product readiness
HullQ MUST NOT activate a paid broker plan/subscription before the Broker Workspace Launch Gate is PASS.

**Acceptance:** repository governance rejects a state declaring paid broker plans ACTIVE while the gate is not PASS.

### REQ-BROKER-020 — Public launch requires broker product readiness
HullQ MUST NOT enter public production launch with professional broker supply while the Broker Workspace Launch Gate is not PASS.

**Acceptance:** repository governance rejects public production launch ACTIVE while the Broker Workspace Launch Gate is not PASS.

### REQ-BROKER-021 — External broker self-service pilot requires broker product readiness
HullQ MUST NOT start a real external broker self-service production pilot before the Broker Workspace Launch Gate is PASS.

**Acceptance:** repository governance rejects broker self-service pilot ACTIVE while the Broker Workspace Launch Gate is not PASS.
