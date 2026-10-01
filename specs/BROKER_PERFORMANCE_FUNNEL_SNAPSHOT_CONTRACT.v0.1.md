# Broker Performance / Funnel Snapshot Contract v0.1

**Status:** ACCEPTED FOR SLICE-0075 READINESS  
**Scope:** factual Organization-scoped broker performance telemetry and snapshot

## 1. Objective

Provide a factual broker-facing operational snapshot over the accepted marketplace funnel:

```text
listing exposure / views
→ Leads
→ broker handling/contact attempt
→ explicit SaleOutcome
```

and expose measurable first broker-action timing where supported.

This is not a generalized analytics platform.

## 2. Truth rules

1. Only observed events/facts may be counted.
2. Missing evidence remains unknown/not observed.
3. WITHDRAWN is never treated as SOLD.
4. Lead CLOSED is never treated as SOLD.
5. Notification delivery/open/click is not broker response.
6. Contact-attempt evidence proves broker action only, not buyer receipt/interest.
7. Sale conversion exists only where explicit SaleOutcome=SOLD exists.
8. Source-to-outcome attribution uses stable Lead/listing/source identities, never display-string matching.
9. Organization boundaries are strict and server-authoritative.
10. Aggregates must be reproducible from durable underlying facts.

## 3. Listing telemetry vocabulary

v0.1 must support at least:

```text
PUBLIC_LISTING_VIEW
```

If a separate exposure/impression fact is implemented in v0.1, its semantics must be mechanically distinct from a view.

A PUBLIC_LISTING_VIEW means HullQ successfully served/read the current public listing surface for a concrete NativeListing under the accepted public-eligibility boundary.

Do not count:

- broker/private preview reads;
- authenticated broker edit views;
- suppressed/not-public listings;
- failed/404 reads;
- asset/image requests;
- automated internal retained-proof requests when explicitly marked/test-only.

## 4. Privacy boundary

v0.1 telemetry MUST NOT require:

- raw IP persistence;
- browser fingerprinting;
- cross-device stitching;
- third-party tracking identifiers;
- arbitrary full referrer URLs/query strings;
- raw Search query retention for this capability.

A bounded source/discovery classification may be retained only when it comes from already-accepted Lead provenance or a separately accepted bounded first-party context.

No personal visitor identity is required to count a factual listing view.

## 5. Durable event identity / idempotency

Each recorded public listing telemetry fact needs:

- stable event/operation identity;
- NativeListingId;
- publishing OrganizationId;
- occurred_at;
- event kind;
- bounded first-party context if accepted.

Retry of the same operation identity must not double-count.

A reused operation identity with conflicting payload must fail closed.

## 6. Broker performance projection

For an authorized Organization, expose a bounded factual snapshot per listing and/or bounded Organization summary containing at least:

- public listing views observed in the selected bounded period;
- Leads received;
- Leads with at least one broker contact-attempt event;
- Leads CLOSED operationally;
- explicit SOLD outcomes;
- source/discovery breakdown for Leads where captured;
- first broker contact-attempt latency for supported Leads;
- explicit unknown/not-observed counts where appropriate.

Do not label derived ratios as facts without exposing numerator/denominator population.

## 7. Response-time semantics

Launch Gate REQ-BROKER-011 is satisfied only by observed broker workflow evidence.

For v0.1:

```text
first broker response/action timestamp
= earliest authoritative broker CONTACT_ATTEMPT timeline event for that Lead
```

Latency:

```text
first_contact_attempt_at - Lead.received_at
```

If no CONTACT_ATTEMPT exists, latency is UNKNOWN / not observed.

Reading a Lead, assignment, status change, notification delivery, email open/click or note alone is not a response.

## 8. Source-to-outcome semantics

Where an explicit SaleOutcome has an originating Lead:

```text
Lead provenance
→ NativeListing
→ explicit SaleOutcome
```

may be reported as factual source-to-outcome linkage.

A SOLD outcome without originating Lead remains SOLD but source attribution is UNKNOWN.

Do not infer an originating Lead from temporal proximity or same listing.

## 9. Time window

The browser surface may support one bounded default window plus a small bounded set of alternatives.

Exact presets are implementation-local, but arbitrary unbounded analytical queries are not required.

All period boundaries must be explicit and deterministic.

## 10. Authorization

Only authenticated Accounts with current authorized access to the exact MarketplaceOrganization may read broker performance projections.

No cross-Organization counts, event existence or source/outcome facts may leak.

Telemetry ingestion from the public listing surface is separate from broker read authorization and must not expose a public analytics read API.

## 11. UI

Broker Workspace must expose a usable factual performance surface, reachable without operator/admin help.

At minimum the broker can answer:

- How many observed public views did this listing receive?
- How many Leads did it generate?
- How many received Leads have a recorded broker contact attempt?
- What first-contact latency is observed where available?
- Which factual acquisition/discovery sources are represented in Leads?
- Which explicit SOLD outcomes are linked to Leads?
- Which values are unknown/not observed?

No score, hidden ranking or lead-quality label is introduced.

## 12. Required retained proof

Real PostgreSQL + FastAPI + built Astro proof must demonstrate at least:

1. public-readable listing view records one durable event;
2. retry of same telemetry operation does not double-count;
3. private/preview/suppressed listing reads do not create public-view facts;
4. Organization A cannot read Organization B telemetry;
5. observed view count is exact;
6. Lead count is exact;
7. first CONTACT_ATTEMPT latency derives from Lead.received_at and earliest contact attempt;
8. Lead with no contact attempt reports unknown/not observed latency;
9. CLOSED Lead is not counted as SOLD;
10. explicit SOLD without originating Lead remains outcome with unknown source;
11. explicit SOLD with originating Lead joins to factual Lead provenance;
12. cross-Organization same-MarketEpisode listing facts remain isolated;
13. browser snapshot renders observed facts and unknown states without invented zeros/conversions;
14. no raw IP/fingerprint/arbitrary referrer/query-string field is persisted by this capability.

## 13. Future compatibility

The durable facts must permit later REQ-BROKER-028 periodic engagement reporting without replacing the core event identities/projections.

0075 does not itself have to implement email/report scheduling or declare REQ-BROKER-028 complete.

Likewise it must preserve a path for later privacy-safe aggregate demand insights without collecting unnecessary individual Search data now.

## 14. Validation ownership

Local:
- focused affected tests;
- relevant PostgreSQL tests;
- retained vertical proof.

Exact pushed GitHub HEAD:
- authoritative complete regression.

No routine local full-suite run.

## 15. Non-goals

- generalized BI/dashboard builder;
- external analytics vendor integration;
- visitor identity graph;
- cookie-consent platform redesign;
- Search criterion changes;
- Search-fit diagnostics;
- periodic report delivery;
- inventory export/import;
- payment/entitlement;
- predictive scoring.
