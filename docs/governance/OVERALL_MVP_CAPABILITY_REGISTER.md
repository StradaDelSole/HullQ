# HullQ — Overall MVP Capability Register

**Status:** OWNER-ACCEPTED / OPEN  
**Accepted:** 2026-09-30  
**Scope:** complete HullQ MVP readiness excluding visual UI/UX polish  
**Purpose:** prevent cross-cutting product, trust, support, legal, privacy and operations capabilities from disappearing from post-slice planning.

<!-- OVERALL_MVP_CAPABILITY_REGISTER_STATUS: OPEN -->

## Completion boundary

HullQ may be described as **overall MVP ready** only when every capability applicable to the accepted launch boundary is one of:

~~~text
IMPLEMENTED
NOT_APPLICABLE_WITH_OWNER_ACCEPTED_EVIDENCE
SUPERSEDED_BY_OWNER_ACCEPTED_DECISION
~~~

PENDING, DUE, PARTIAL, NOT_STARTED and prose-only intention do not satisfy completion.

This register does not require every future/scale-only idea to block MVP. Each item has a timing class. Triggered requirements remain governed by their existing canonical gates. A capability may be deliberately excluded from the first launch boundary only through an explicit owner-accepted decision; omission by silence is not allowed.

Visual styling/polish is outside this register. Functional accessibility, trust, privacy, support, operability and error/recovery behavior are not "polish" and remain in scope.

## Mandatory post-slice rule

Every post-SLICE-0072 capability reassessment MUST inspect this register before selecting the next primary slice.

The reassessment must state:

- which entries changed status;
- which entries are now DUE;
- whether the proposed next capability closes one of these gaps;
- why any higher-risk/higher-leverage due gap is deferred;
- whether the candidate would make a still-open capability harder to implement correctly later.

No post-SLICE-0072 readiness may claim repository reconciliation PASS without accounting for this register where applicable.

## Status vocabulary

~~~text
IMPLEMENTED
PARTIAL
PENDING
DUE
NOT_STARTED
NOT_APPLICABLE_WITH_OWNER_ACCEPTED_EVIDENCE
SUPERSEDED_BY_OWNER_ACCEPTED_DECISION
~~~

## A. Buyer discovery and decision

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-BUY-001 | deterministic technical Direct Search | core MVP | IMPLEMENTED/PARTIAL — 2 accepted hard criteria |
| MVP-BUY-002 | factual Search explainability / sensitivity | core MVP | PARTIAL |
| MVP-BUY-003 | anonymous Shortlist | core MVP | IMPLEMENTED |
| MVP-BUY-004 | factual Compare | core MVP | IMPLEMENTED |
| MVP-BUY-005 | BuyerRequirements persistence / account continuity | overall MVP | PENDING |
| MVP-BUY-006 | persistent account Shortlist + anonymous-to-account migration | overall MVP | PENDING |
| MVP-BUY-007 | Saved Search / Monitor / Alert | overall MVP | PENDING |
| MVP-BUY-008 | price-change alert capability when price history exists | overall MVP / monetization-value | PENDING |
| MVP-BUY-009 | buyer-contact email verification | before real external production buyer-contact | PENDING |
| MVP-BUY-010 | buyer-side spam/bot/fake-lead abuse controls | before public buyer-contact exposure | PENDING |
| MVP-BUY-011 | buyer transaction-safety guidance for owner-direct flows | before owner-direct public contact/transaction use | PENDING |
| MVP-BUY-012 | privacy-bounded sharing of buyer decision views | later unless launch boundary includes sharing | PENDING |

## B. Professional Broker Workspace

Existing broker governance remains controlling in docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md and docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md. This register mirrors only the overall-MVP view and does not weaken those records.

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-BROKER-001 | auth / Organization / Membership / MFA boundary | broker MVP | IMPLEMENTED |
| MVP-BROKER-002 | draft authoring + recovery | broker MVP | IMPLEMENTED |
| MVP-BROKER-003 | promotion / publication / lifecycle / freshness | broker MVP | IMPLEMENTED |
| MVP-BROKER-004 | mixed-media management | broker MVP | IMPLEMENTED |
| MVP-BROKER-005 | post-promotion inventory edit / price / yacht facts | broker MVP | IMPLEMENTED by SLICE-0072 |
| MVP-BROKER-006 | durable Lead + mini-CRM operations | broker MVP | IMPLEMENTED |
| MVP-BROKER-007 | explicit sale/outcome workflow | before paid/broad public broker launch | IMPLEMENTED by SLICE-0074 |
| MVP-BROKER-008 | source-to-outcome / response / engagement reporting | before paid/broad public broker launch | PARTIAL — factual snapshot implemented by SLICE-0075; periodic delivery remains pending |
| MVP-BROKER-009 | inventory portability/export | before paid/broad public broker launch | PENDING |
| MVP-BROKER-010 | pre-publication Search-fit diagnostics | before paid/broad public broker launch | PENDING |
| MVP-BROKER-011 | structured bulk onboarding/import | before scaled broker onboarding | PENDING |
| MVP-BROKER-012 | Search exclusion / aggregate demand insights | volume-triggered | PENDING |
| MVP-BROKER-013 | usability evidence + competitive benchmark | before first external self-service pilot | IMPLEMENTED by SLICE-0076; blocking Lead-assignment finding closed by SLICE-0077; Broker Workspace Launch Gate evidence supports PASS |

## C. Owner-Direct Marketplace

Existing normative source: specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md.

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-OWNER-001 | owner-direct private draft workspace | core foundation | IMPLEMENTED |
| MVP-OWNER-002 | owner-direct admission / promotion / publication path | overall mixed-supply MVP | PENDING |
| MVP-OWNER-003 | owner-direct media path/reuse of accepted media semantics | overall mixed-supply MVP | PENDING |
| MVP-OWNER-004 | owner-direct enquiries/lead handling | overall mixed-supply MVP | PENDING |
| MVP-OWNER-005 | owner-direct listing maintenance / lifecycle / outcome | overall mixed-supply MVP | PENDING |
| MVP-OWNER-006 | genuine seller choice: direct vs voluntary broker referral | overall mixed-supply MVP | PENDING |
| MVP-OWNER-007 | broker-referral workflow with commercial neutrality | when referral enabled | PENDING |

## D. Trust, Verification, Safety and Fraud

Trust scopes remain separate: PHONE_VERIFIED != IDENTITY_VERIFIED != RIGHT_TO_LIST_ATTESTED != SALE_AUTHORITY_VERIFIED.

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-TRUST-001 | phone/SMS reachability verification | before normal owner-direct publication | PENDING |
| MVP-TRUST-002 | explicit right-to-list attestation | before normal owner-direct publication | PENDING |
| MVP-TRUST-003 | baseline owner-direct anti-abuse/rate/risk controls | before owner-direct public use | PENDING |
| MVP-TRUST-004 | risk escalation/manual review responsibility | before owner-direct public use | PENDING |
| MVP-TRUST-005 | strong identity verification provider boundary | before feature is relied on / risk policy requires it | PENDING |
| MVP-TRUST-006 | documentary Sale Authority Verification | risk-triggered / before claims are represented as verified | PENDING |
| MVP-TRUST-007 | representation conflict handling | before conflicting mixed-supply cases may occur in production | PENDING |
| MVP-TRUST-008 | duplicate/same-boat reconciliation without naïve destructive merge | overall mixed-supply operations | PENDING |
| MVP-TRUST-009 | user/listing fraud/scam reporting | before public mixed-supply launch | PENDING |
| MVP-TRUST-010 | authoritative TrustSafetyCase model | before support tickets are relied on for safety adjudication | PENDING |
| MVP-TRUST-011 | protective actions / suppression + reason + audit | before public mixed-supply launch | PENDING |
| MVP-TRUST-012 | appeal/dispute/review path | before user-affecting safety enforcement is relied on | PENDING |
| MVP-TRUST-013 | evidence-bounded verification badges/copy | before verification badges are public | PENDING |

Zammad tickets may link to Trust & Safety cases but MUST NOT be authoritative for these states.

## E. Help & Support

Controlling decision: docs/HULLQ_HELP_SUPPORT_ZAMMAD_DECISION_2026-09-30.md.

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-SUP-001 | Zammad Hosted Professional v2 provisioned | before external support launch | PENDING |
| MVP-SUP-002 | end-to-end HullQ custom branding validation | before customer exposure | PENDING |
| MVP-SUP-003 | support.hullq.com / accepted support domain | before customer exposure | PENDING |
| MVP-SUP-004 | support email routing / sender identity | before customer exposure | PENDING |
| MVP-SUP-005 | Help Center / Knowledge Base taxonomy and baseline content | overall MVP | PENDING |
| MVP-SUP-006 | secure minimal HullQ entity-context integration | overall MVP | PENDING |
| MVP-SUP-007 | support retention/deletion policy + DPA/vendor record | before production personal support data | PENDING |
| MVP-SUP-008 | least-privilege support-agent roles | before multiple/real agents | PENDING |
| MVP-SUP-009 | provider exit/export/termination procedure | before production dependency is relied upon | PENDING |

## F. Internal Admin, Moderation and Operations

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-OPS-001 | bounded internal admin/backoffice surface | before routine production operations require direct DB intervention | PENDING |
| MVP-OPS-002 | account / Organization / listing / lead lookup with authorization | overall production MVP | PENDING |
| MVP-OPS-003 | Trust & Safety review/actions through auditable HullQ operations | before safety enforcement | PENDING |
| MVP-OPS-004 | content moderation policy and reason taxonomy | before broad user-generated public content | PENDING |
| MVP-OPS-005 | content takedown/correction workflow | before broad public production | PENDING |
| MVP-OPS-006 | factual yacht/data correction/challenge workflow | overall MVP / truth operations | PENDING |
| MVP-OPS-007 | moderation/support actions do not require routine manual SQL | before external production support load | PENDING |

## G. Account Lifecycle, Privacy and Legal

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-PRIV-001 | account deactivate/delete lifecycle | before public account launch is considered complete | PENDING |
| MVP-PRIV-002 | session/security recovery and credential-contact changes | overall account MVP | PENDING |
| MVP-PRIV-003 | Organization membership offboarding/removal lifecycle | broker production | PENDING/PARTIAL |
| MVP-PRIV-004 | user data export/access request process | before broad public production | PENDING |
| MVP-PRIV-005 | data deletion/anonymization/retention matrix by domain object | before broad public production | PENDING |
| MVP-PRIV-006 | privacy policy | before public production | PENDING |
| MVP-PRIV-007 | terms of service | before public production | PENDING |
| MVP-PRIV-008 | Austrian/EU imprint/legal notices as applicable | before commercial/public launch | PENDING |
| MVP-PRIV-009 | cookie/consent policy and implementation where non-essential tracking requires it | before such tracking | PENDING |
| MVP-PRIV-010 | broker terms / private seller terms / listing-content rules | before corresponding external supply path | PENDING |
| MVP-PRIV-011 | verification/trust disclaimers and complaint/dispute wording | before public trust features | PENDING |
| MVP-PRIV-012 | targeted legal review of source/data rights and commercial use before launch | before commercial launch where relevant | PENDING |

## H. Communications and Notification Operations

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-COMMS-001 | production email provider activation | before real external email dependency | PENDING |
| MVP-COMMS-002 | SPF/DKIM/DMARC and sender-domain configuration | before production email | PENDING |
| MVP-COMMS-003 | bounce / complaint / suppression handling | before scaled production email | PENDING |
| MVP-COMMS-004 | user notification preferences / unsubscribe model | before optional recurring alerts/marketing | PENDING |
| MVP-COMMS-005 | transactional-vs-optional notification classification | before recurring notification features | PENDING |
| MVP-COMMS-006 | SMS provider, delivery/failure semantics, normalization and resend/rate protection | before phone verification | PENDING |
| MVP-COMMS-007 | provider outage/retry/observability behavior | before provider is production-critical | PENDING |

## I. Monetization, Billing and Entitlements

Accepted strategy includes Free / Plus / Pro buyer direction and future paid broker plans, but final packaging/pricing remains open.

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-PAY-001 | SubscriptionEntitlement domain boundary | before paid feature enforcement | PENDING |
| MVP-PAY-002 | payment provider + subscription lifecycle | before paid launch | PENDING |
| MVP-PAY-003 | upgrade/downgrade/cancel/grace/failed-payment semantics | before paid launch | PENDING |
| MVP-PAY-004 | invoices/VAT/tax handling appropriate to seller entity/markets | before charging customers | PENDING |
| MVP-PAY-005 | refund/cancellation policy and operational handling | before paid launch | PENDING |
| MVP-PAY-006 | payment state cannot affect organic Search truth/ranking | invariant | DECIDED — implementation proof due with monetization |

If the owner explicitly defines the first overall MVP as non-paid, these may be NOT_APPLICABLE_WITH_OWNER_ACCEPTED_EVIDENCE for that launch boundary, but may not disappear from the product roadmap.

## J. Internationalization, Accessibility and SEO

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-I18N-001 | one language-neutral canonical domain/data layer | architecture invariant | PARTIAL/IMPLEMENTED foundation |
| MVP-I18N-002 | EN/DE/FR/PT/ES product-language support | accepted product requirement | PENDING/PARTIAL |
| MVP-I18N-003 | controlled technical terminology glossary | before five-language production quality claim | PENDING |
| MVP-I18N-004 | locale routing / fallback / formatting | public multilingual launch | PARTIAL |
| MVP-I18N-005 | hreflang/localized sitemap/canonical/indexation behavior | public multilingual SEO launch | PARTIAL/PENDING |
| MVP-A11Y-001 | functional accessibility baseline: keyboard, semantic forms, errors, focus, screen-reader path, contrast | before overall MVP ready claim | PENDING |
| MVP-SEO-001 | intentional public indexability/canonical/sitemap/structured data baseline | before broad organic public launch | PARTIAL |
| MVP-SEO-002 | no accidental combinatorial Search indexation | invariant | DECIDED / proof with public release |

Five-language completeness is an accepted product obligation. Rollout sequencing may be staged only where existing product-language governance permits it; architecture may never assume English-only.

## K. Production, Security and Reliability

Controlling gate: docs/governance/PRODUCTION_READINESS_GATE.md.

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-PROD-001 | immutable CI-built production deploy + rollback | before production gate PASS | PARTIAL — mechanism implemented + locally proven by SLICE-0079; real GHCR push/VPS deploy not yet observed (`docs/validation/PRODUCTION_READINESS_EVIDENCE_2026-10.md` §1/§9) |
| MVP-PROD-002 | production PostgreSQL target and controlled migrations | before production gate PASS | PARTIAL — migration CLI implemented + real-executed by SLICE-0079; no real DO Managed PostgreSQL instance provisioned yet (evidence §2/§8/§9) |
| MVP-PROD-003 | automatic failover/standby before real buyer exposure to external inventory | hard trigger | PENDING — `POSTGRESQL_HA_STATUS = NOT_ACTIVE`, explicitly recorded by SLICE-0079 (evidence §2) |
| MVP-PROD-004 | independent encrypted backup + tested restore | before production gate PASS | IMPLEMENTED by SLICE-0079 — real destroy-then-restore proof against disposable PostgreSQL (evidence §2) |
| MVP-PROD-005 | explicit RTO/RPO + recovery runbook | before production gate PASS | IMPLEMENTED by SLICE-0079 (`docs/operations/PRODUCTION_BACKUP_RESTORE_RUNBOOK.md`) |
| MVP-PROD-006 | structured logs/error tracking/health/alerting | before production gate PASS | IMPLEMENTED by SLICE-0079 — structured JSON logs, exception capture, health/readiness, alert-webhook mechanism, all real-proven (evidence §3) |
| MVP-PROD-007 | edge bot/abuse protection and endpoint rate controls | before pilot/public exposure | PARTIAL — endpoint rate controls implemented by SLICE-0078; Cloudflare/Caddy edge config written by SLICE-0079 but not yet deployed (no VPS exists) (evidence §4) |
| MVP-PROD-008 | secrets storage/rotation/recovery + least privilege | before production gate PASS | IMPLEMENTED by SLICE-0079 (evidence §5; `docs/operations/PRODUCTION_INCIDENT_OBSERVABILITY_RUNBOOK.md` §4) |
| MVP-PROD-009 | smoke checks / migration verification / release runbook | before production gate PASS | IMPLEMENTED by SLICE-0079 — real CLI executions (evidence §8) |
| MVP-PROD-010 | incident communication/status path | before broad public production | PENDING |
| MVP-PROD-011 | incident-response/post-incident operating procedure | overall production MVP | PENDING |
| MVP-PROD-012 | holistic Security Hardening & Adversarial Validation gate | before first external broker self-service pilot | IMPLEMENTED by SLICE-0078 — gate PASS; SEC-0078-07 Owner-risk-accepted with retained re-review triggers |

## L. Data Operations and Truth Maintenance

| ID | Capability | Timing | Status |
|---|---|---|---|
| MVP-DATA-001 | field-level provenance remains durable | core invariant | IMPLEMENTED/PARTIAL |
| MVP-DATA-002 | controlled correction of canonical/design/listing facts | overall truth MVP | PENDING/PARTIAL |
| MVP-DATA-003 | source-rights/source-removal handling | before reliance on revocable external sources | PENDING |
| MVP-DATA-004 | taxonomy/schema migration and derived-value recomputation procedure | overall data operations | PENDING |
| MVP-DATA-005 | conflict review without silently inventing certainty | invariant + operations | PARTIAL |
| MVP-DATA-006 | source/data ingestion operations that do not bypass canonical truth | before recurring production ingestion | PENDING |
| MVP-DATA-007 | data-quality monitoring / stale-source detection where applicable | production maturity / overall MVP where relied upon | PENDING |

## Cross-cutting non-negotiable invariants

Nothing in this register supersedes existing accepted invariants, including:

- BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId;
- DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH;
- UNKNOWN != NOT_SATISFIED;
- no hidden match score/winner/preference model;
- no paid organic eligibility/classification/ordering;
- payment cannot buy truth;
- professional and owner-direct authorization boundaries remain distinct;
- support/helpdesk state does not replace HullQ domain truth;
- support/verification/trust systems minimize unnecessary personal data.

## Current overall interpretation

As of 2026-10-03:

- the marketplace/truth/search/broker operational loop through factual performance reporting is materially implemented through SLICE-0075;
- broker usability evidence + competitive benchmark is implemented by SLICE-0076; the resulting Lead-assignment blocker was closed by SLICE-0077 and the Broker Workspace Launch Gate now supports PASS;
- the dedicated Security Hardening & Adversarial Validation gate is implemented and PASS through SLICE-0078;
- SLICE-0079 implements and locally proves (against real, non-production resources) every mechanism the Production Readiness Gate requires — deploy/rollback, encrypted backup/restore, observability/alerting, migration/smoke verification, secrets/least-privilege design — but the gate remains `IN_PROGRESS` pending real GHCR/VPS/managed-PostgreSQL provisioning the Project Owner has not yet made (`docs/validation/PRODUCTION_READINESS_EVIDENCE_2026-10.md`);
- the largest remaining overall-MVP workstreams include owner-direct completion, trust/verification/safety, buyer persistence/alerts, periodic reporting/export/Search-fit diagnostics, support/admin/privacy/legal/comms, monetization where included, and production/data operations;
- these remaining workstreams are not permission to reopen already-decided architecture.

## Evidence rule for status changes

A status may move to IMPLEMENTED only when the repository identifies concrete accepted implementation/evidence appropriate to the capability. A narrative claim that a feature "basically exists" is insufficient.

For capabilities primarily consisting of policy/vendor/configuration rather than HullQ code, implementation evidence may be configuration records, runbooks, retained screenshots/exports, contracts/DPA references, production checks or other reviewable artifacts, but must still be independently reviewable and owner-accepted where required.

## Relationship to future slicing

This register does not preassign slice numbers.

Future reassessment should group low-risk related work into coherent vertical capabilities where possible. It must not create artificial micro-slices merely because this register contains multiple rows. Conversely, materially independent identity, privacy, authorization, money, trust/safety or irreversible-data decisions must not be hidden inside unrelated slices.
