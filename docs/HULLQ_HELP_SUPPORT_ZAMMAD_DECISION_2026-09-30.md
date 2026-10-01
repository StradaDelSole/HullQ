# HullQ — Help & Support Platform Decision

**Date:** 2026-09-30  
**Status:** OWNER-ACCEPTED  
**Decision:** Use **Zammad Hosted Professional v2** as HullQ's external helpdesk / support platform.

## Decision

HullQ will use Zammad Hosted Professional v2 for commodity support operations rather than building a proprietary ticketing/helpdesk stack.

Target customer-facing support identity:

```text
support.hullq.com
HullQ Support
HullQ branding / logo / colors / sender identity
```

Custom branding is a hard requirement. Before production activation, the hosted instance must be verified to avoid prominent customer-facing Zammad branding on the surfaces HullQ exposes.

## Why Hosted

Hosted is preferred over self-hosted even though self-hosted can reduce direct license cost.

The controlling reasons are:

- reduce HullQ-operated infrastructure containing support-related personal data;
- avoid a second self-managed database/search/attachment/backup stack for support;
- shift helpdesk patching, platform maintenance, backup operations and service availability to the provider;
- retain a DPA / processor relationship rather than voluntarily operating an additional support-data platform;
- preserve engineering focus for HullQ-specific marketplace, trust and safety capabilities.

HullQ remains responsible for lawful processing, minimization, retention, access control and its controller obligations.

## Why Professional v2

Professional v2 is the accepted target because the intended HullQ support layer needs more than a basic mailbox. The target capability set includes:

- custom branding;
- Knowledge Base / Help Center;
- chat where later enabled;
- SLA support;
- custom roles;
- custom ticket objects / fields;
- structured support queues and ordinary ticket workflows.

Exact commercial pricing is not a domain invariant and may change. Plan eligibility and pricing must be re-verified with Zammad before purchase/renewal.

## Boundary: Zammad is NOT HullQ domain authority

Zammad owns commodity support workflow only:

- customer support conversations;
- tickets;
- agent queues;
- internal support notes;
- macros / canned responses;
- ordinary routing / SLA;
- Help Center / Knowledge Base delivery where used.

Zammad MUST NOT become authoritative for HullQ marketplace or Trust & Safety state.

HullQ remains authoritative for:

- Account / Organization / Membership identity and authorization;
- NativeListing / PhysicalBoat / MarketEpisode truth;
- Lead truth;
- verification status;
- TrustSafetyCase;
- scam/fraud reports and adjudication;
- listing/user protective actions or suppression;
- identity verification;
- right-to-list and sale-authority verification;
- representation conflicts;
- duplicate / same-boat reconciliation;
- appeals / dispute state;
- immutable audit history for HullQ-domain decisions.

A Zammad ticket may carry a stable reference to HullQ entities, but a ticket field must never silently replace HullQ-domain state.

## Integration direction

Preferred pattern:

```text
HullQ
  |
  +-- contextual Help / Contact Support
  |
  +-- stable HullQ entity references
  |     AccountId
  |     OrganizationId
  |     NativeListingId
  |     LeadId
  |     TrustSafetyCaseId where applicable
  |
  +-- Zammad Hosted Professional v2
        ticket / conversation / agent workflow
```

Use data minimization:

- send only support context required to service the case;
- prefer stable opaque HullQ IDs over copied domain payloads;
- do not copy identity documents, biometric/selfie material or unnecessary verification evidence into Zammad;
- do not use Zammad as a second marketplace data store;
- attachments require explicit retention/security rules before production use.

## Support vs Trust & Safety

Normal customer support and Trust & Safety remain distinct bounded concerns.

Normal support examples:

- account access help;
- listing workflow help;
- broker workspace help;
- buyer contact/support questions;
- billing/help-center questions when payments exist.

Trust & Safety examples:

- suspected scam/fraud;
- fake seller/broker;
- unauthorized sale representation;
- duplicate/conflicting representation of a PhysicalBoat;
- verification dispute;
- abusive buyer/seller behavior;
- appeals against protective actions.

A Trust & Safety matter may open/link a Zammad ticket for communication, but the authoritative case and all protective/adjudication actions remain in HullQ.

## Required preparation before launch

The following is DECIDED_NOT_YET_IMPLEMENTED:

1. provision Zammad Hosted Professional v2;
2. validate custom branding end to end;
3. configure `support.hullq.com` or the accepted HullQ support subdomain;
4. configure HullQ sender identities and support mail routing;
5. execute/retain DPA and privacy/vendor records;
6. define retention/deletion policy for tickets and attachments;
7. define least-privilege agent roles;
8. configure Help Center taxonomy;
9. define bounded custom ticket fields for HullQ context;
10. implement secure HullQ→Zammad integration;
11. ensure support links/context exist across Buyer, Broker and Owner-Direct surfaces;
12. implement HullQ-native TrustSafetyCase / escalation authority before relying on support tickets for scam/safety handling;
13. add production monitoring for integration failures without leaking ticket/customer content;
14. document incident/export/termination procedure so HullQ can leave the provider without losing required support records.

## Classification

### DECIDED_AND_IMPLEMENTED

- None of the Zammad integration itself yet.

### DECIDED_NOT_YET_IMPLEMENTED

- Hosted Professional v2 provisioning and configuration;
- branding validation;
- Help Center/support entry points;
- bounded entity-context integration;
- retention/privacy/agent-role configuration;
- Trust & Safety linkage.

### EXPLICITLY NOT AUTHORIZED

- self-hosted Zammad as the current target;
- Zammad as marketplace/domain authority;
- storage of raw identity/biometric evidence in Zammad by default;
- automatic listing suppression or verification changes based solely on Zammad ticket state;
- bespoke HullQ ticketing/agent inbox when Zammad already provides the commodity capability.

## Slice interaction

This decision does **not** modify or expand active SLICE-0072.

Help & Support must be included in future post-slice reconciliation as a separate overall-MVP capability. Exact slice numbering and sequencing remain subject to canonical post-slice reassessment.
