# SLICE-0089 — Broker Factual Periodic Performance Reports

**ID:** SLICE-0089  
**Type:** IMPLEMENTATION  
**Status:** READY CANDIDATE — **NOT OPERATIVE** until this separate docs-only readiness PR receives independent exact-HEAD ACCEPT, successful GitHub CI and manufacturer reproducibility, and is merged into canonical main; the Owner must subsequently execute normal START_SLICE.bat 0089.  
**Risk:** HIGH_RISK — durable telemetry accuracy, time-bound snapshots, broker organization/MFA rights, scheduled delivery ownership, PII minimization, cross-tenant isolation and on-demand artifact privacy.  
**Owner choice:** Post-0088 Owner explicitly agreed to SLICE-0089 factual periodic broker reporting; recorded under issue #357.  
**Depends on:** Owner accepted/fully locally FINISHED SLICE-0088, accepted SLICE-0075 factual broker performance snapshot, current security baseline, issue #357, governing broker requirement REQ-BROKER-028 / MVP-BROKER-008.  
**Governing decision:** docs/POST_SLICE_0088_BROKER_REPORTING_REASSESSMENT_2026-10-24.md; earlier Sail+Power decision #366 and technical finding tracker #372 remain independent and are NOT implemented here.  

## One capability / visible broker outcome

An authorized broker opens its own Organization's performance page, reviews a clearly dated, source-defined factual portfolio and per-listing report, prints or downloads a shareable broker-branded representation, and opts in/out of periodic delivery. A deterministic, durable bounded dispatcher records which report period was due, generated and delivered/failed, including zero-lead windows. Repeated scheduler ticks do not double send. A failed attempt is visible/retryable without silently pretending delivery succeeded. This builds on the existing SLICE-0075 read model, not a new general analytics platform.

**ONE-CAPABILITY CHECK:** PASS — one factual report as view/print/download and opt-in periodic delivery variants, with shared metric projection, not separate new statistics products. No paid ranking, Search-demand insights or external YachtWorld measurement.
**VISIBLE-RESULT CHECK:** PASS only on disposable PostgreSQL18/FastAPI/built Astro SSR + Playwright: Organization A prints/downloads its own accurately branded report, selects a bounded schedule, a deterministic worker tick records one expected period and one delivery, replay is idempotent, Organization B cannot see A's report; a genuinely zero-lead period is represented, not omitted.
**MVP / BROKER GATE:** REQ-BROKER-028 and MVP-BROKER-008 stay PENDING until independently reviewed implementation + separate formal Owner acceptance closure. BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS remains OPEN; Production Readiness IN_PROGRESS, Launch Pack NOT_STARTED.

## Existing code/reuse contract

- Reuse src/hullq/application/broker_performance_read.py and src/hullq/persistence/broker_performance.py, whose accepted LAST_7_DAYS/LAST_30_DAYS/LAST_90_DAYS/ALL_TIME windows anchor at explicit as_of and [start,end) boundaries; public listing views are accepted first-party PUBLIC_LISTING_VIEW durable events, NOT distinct measured search result impressions.
- Current web/src/pages/broker/organizations/[organization_id]/performance.astro already renders current bounded views/Lead/contact/SOLD/source factual snapshot. Extend the same Organization auth/MFA and response/denied semantics; no duplicated read model, no N+1 unbounded report query.
- Reuse current lead-notification-delivery port/outbox patterns as design examples, but do NOT mix report subscription jobs with Lead notifications' independent semantics, recipient consent or event identity. A report delivery job must have its own idempotency key, state and retention.
- Brand only with legitimately authorized published Organization identity and available safe logo; never disclose private buyer identities, email addresses, buyer behavioral journeys, Lead note contents, or other-Organization inventory. Organization branding is not verified certification.

## Report truth contract — mandatory

1. Show report generation time, explicit start/end (UTC or clearly labeled), Organization, actual observed telemetry population and metric definitions; zero is numerically 0 only when an instrumented/complete applicable observation supports it. Missing/not-measured is N/A with explanation. No invented conversions, impressions, visit counts, leads from other portals or causal marketing uplift.
2. Minimum actual metrics from accepted 0075: PUBLIC_LISTING_VIEW observed count, Leads received, contacted and operationally CLOSED, explicit SOLD outcomes separately, first broker CONTACT_ATTEMPT timing population-known/unknown, acquisition source and discovery source separately. Never count notification delivery or OPEN as human response; SOLD does not derive from lead CLOSED. A valid period with zero Leads must still produce a report and safe customer-facing prose.
3. Per-listing rows must have exact Organization-owned NativeListing identities and current rights; include currently offered zero-activity inventory only where a consistent source-authoritative inventory projection can demonstrate zero; otherwise avoid suggesting the absence of a row means the listing did not exist. Document observable coverage and no-data gaps.
4. Use deterministic as-of snapshots: job's explicit immutable [window_start,window_end) and generation time, consistent read-only DB snapshot, stored source-window fingerprint/report identity, tenant boundary, no mismatched live-versus-cached overview. No assignment of external reporting accuracy where source coverage is absent.
5. Preserve the correct view/Lead/SOLD temporal population and source breakdown semantics previously independently fixed in SLICE-0075; code and tests remain the authority. No unofficial Search impressions feature.

## Bounded one-screen broker UI and portable reporting

- The current organization performance page gains one accessible clearly named Download/Print report control, visible range/definitions and the next period scheduling settings. Support EN/DE/FR/PT/ES UI without misleading translations, appropriate accessible labels/keyboard/status and mobile width.
- Produce a genuine, self-contained, broker-branded, printable/downloadable report artifact with identical metrics to the browser: standalone sanitized HTML (print-to-PDF supported by the browser) is the permitted low-cost baseline; a deterministic, vetted server-side PDF is optional, NOT a blocker or excuse to add commercial dependencies. No arbitrary remote logos, scripts, active third-party content, buyer PII, or injected formula/template text.
- Download access is scoped to currently MFA-validated authorized Organization membership, never a predictable world-readable historical report URL. Print/downloads containing brand identity and factual aggregated counts need safe cache headers and scope-appropriate expiry; if a broker loses access, later historical reports must not remain fetchable to it.

## Periodic delivery / operability

- Bounded recurrence: explicit opt-in, active/inactive, verified recipient address belonging to currently authorized Organization delivery config, timezone-aware weekly OR monthly periods (period close and catch-up semantics precisely specified; no arbitrary cron/execution frequencies), unsubscribe/disable/change audited. NO automatic opt-in or mass sending.
- Durable persisted Subscription, due report/run identity and delivery outbox state with idempotent unique (Org, subscription, period, recipient/config revision) key, transactional snapshot/admission, row-level permissions and bounded worker batch. Repeat/concurrent worker ticks may claim one due job only. No hidden infinite retry, exponential backlog, duplicate sending or suppressed terminal failures.
- Testable deterministic local delivery adapter with success, retryable, permanent reject, revoked membership, recipient change, disable, crash/retry and suppressed stale report; no third-party email credentials in tests or repository. Real email provider, supervised timer/worker, observability and delivery SLA must be tested in separate Production Readiness operational evidence before any real external dispatch/pilot; 0089 does NOT claim production email activation.
- Consent/data minimization and retention: limit stored aggregates and artifacts, do not persist arbitrary buyer PII; future deletion, account/member revocation and broker offboarding must prevent future delivery/continued report access. Safe expiry/purge test proof.

## Failure modes / adversarial acceptance tests

- AUTH/MFA: Org A/B cross-tenant, no membership, revoked role, MFA not satisfied, missing CSRF on write, stale session during download, direct API replay, recipient hijack, report ID enumeration, reflected XLS/HTML injection, template escaping/unsafe remote URL, impersonated branding.
- TIME/COUNTS: month-end, DST/timezone transition, half-open boundary event, event exactly at closing timestamp, zero Leads, zero Views, historical SOLD outside range, unknown first-contact times, distinct source breakdown, no measured impression metrics, withdrawn/listing publication eligibility, lead CLOSED not SOLD, unknown source.
- SCHEDULER: repeated tick/concurrent claimed job, delivery retry/backoff cap, delayed worker, restart, due period idempotency, opt-out/revoke before send, delivery provider rejects, no-email-configured, empty portfolio, maximum listing count/byte size, bounded archival/purge.
- PERFORMANCE: bounded SQL query/rows and bytes, no report serializer work on API event loop if CPU-heavy, ensure Search/health concurrently responsive. No claims from fabricated production telemetry. Real PG18/FastAPI + built Astro SSR and at least one true browser print/download artifact proof.

## Out of scope

Power-specific technical Search, category classification, future source-qualified design-unresolved Search (#372), shared Search Demand or buyer tracking, benchmark/soldboat vendor metrics, separate price history/SEO work, broad broker optimizer (#358), unlicensed YachtWorld/BoatWizard feeds (#359), external broker live data, real third-party emails, Production Readiness PASS or public launch. Existing 0088 export must remain unchanged; no XLSB outbound (#362).

## Deliverables / required implementation report

1. Source-of-truth read model reuse + bounded factual print/download projection, auth/RBAC/MFA/Org cross-tenant and escaping protections.
2. Migration for persisted report-subscription/schedule/report-run/outbox identities and retention, deterministic bounded worker callable from an operator-owned future supervisor, no third-party provider activation.
3. Broker performance SSR UI update, download/print, subscription controls and five locales; synthetic fixture with zero-Lead report and visible Last-generated/delivery status.
4. Focused unit/DB/API/web/adversarial tests; retained disposable PG18/FastAPI/built Astro/Playwright inspector proving positive and negative paths. Provide exact commands/fixtures and count of real browser flows; never claim a run not executed.
5. Ruff, mypy, relevant focused local tests; complete authoritative GitHub CI dependency audit/PG18 integration + manufacturer Ubuntu/Windows reproducibility on exact HEAD. Do not needlessly rerun full local Python suite when authoritative CI already runs it.
6. Independent Exact-HEAD review; material Finding -> same slice branch amendment, repeat CI as needed. Owner expressly accepts implementation before merge; separate acceptance-closure PR updates REQ-BROKER-028 / MVP-BROKER-008 ONLY after proof, then normal Owner FINISH_SLICE.bat 0089.

## Hard STOP

No START_SLICE.bat 0089 before independently ACCEPTED and merged docs READY, canonical main and security gate all green, explicit owner handoff. No code in docs-ready PR, no changed 0088 or existing security gates. Open Security Issue #373 is a prereq; this candidate PR is intentionally based on the security-fix commit but cannot be merged ahead of Owner-accepted security PR #374. Further required Owner decisions on provider costs, vendor agreements, privacy or architecture policy must be escalated; do not choose or purchase them autonomously.
