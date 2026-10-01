# HullQ — Security Hardening & Adversarial Validation Gate

**Status:** OWNER_ACCEPTED DIRECTION  
**Accepted:** 2026-10-01  
**Purpose:** require a dedicated security-hardening and adversarial-validation pass before any real external broker self-service pilot.

## Controlling rule

HullQ MUST NOT begin a real external broker self-service production pilot until a dedicated Security Hardening & Adversarial Validation capability has been completed, independently reviewed, and owner-accepted.

This is a hard pre-pilot gate. It is not satisfied by ordinary slice-level security tests alone.

The owning capability may be scheduled after the Broker Workspace launch-readiness / usability / competitive-benchmark work, but it MUST complete before:

```text
BROKER_SELF_SERVICE_PILOT_STATUS = ACTIVE
```

and therefore before any later paid broker activation or broad public production launch.

## Required scope

The hardening pass must cover at least:

### Authentication / session / authorization

- Auth0 authentication boundary;
- session forgery/tampering;
- session fixation/replay where applicable;
- MFA / step-up bypass attempts;
- stale or revoked membership;
- role escalation;
- privilege-boundary confusion;
- logout/session invalidation behavior.

### Multi-tenant / object authorization

Adversarial proof must attempt unauthorized cross-Organization access to:

- listings;
- drafts;
- PhysicalBoat / MarketEpisode-linked broker surfaces;
- media;
- Leads;
- Lead notes/timeline/follow-up/assignment;
- SaleOutcome;
- performance/analytics;
- Organization configuration.

Include IDOR/enumeration testing and confirm non-enumerating behavior where required.

### Request / browser security

- CSRF and Origin enforcement;
- redirect validation / open redirect;
- Host/header trust boundaries where applicable;
- secure cookie attributes;
- XSS / HTML/script injection;
- CSP;
- HSTS;
- Referrer-Policy;
- Permissions-Policy;
- clickjacking / framing controls;
- private/no-store/noindex enforcement on broker surfaces.

### API / input hardening

- malformed payloads;
- oversized payloads;
- parser edge cases;
- mass-assignment attempts;
- SQL/injection attempts;
- unsafe URL input;
- error/stack/internal-ID leakage;
- expensive-request abuse.

### PostgreSQL / concurrency / transaction safety

- database constraints;
- race conditions;
- optimistic-concurrency bypass attempts;
- idempotency collisions;
- transaction rollback/atomicity;
- partial-write failure;
- cross-tenant query scoping.

### Media / object storage

- MIME/content-type spoofing;
- malicious/corrupt image input;
- decompression/resource-exhaustion attacks;
- object-key/path manipulation;
- private-original/quarantine leakage;
- processed/public derivative boundary;
- signed/public object access;
- YouTube/URL normalization abuse;
- rights/privacy metadata boundary.

### Abuse / rate protection

Review and, where required, implement bounded protection for:

- authentication-sensitive routes;
- buyer contact / Lead creation;
- broker mutations;
- upload endpoints;
- expensive public/broker reads;
- abuse patterns that can create unbounded storage or notification load.

### Secrets / configuration / supply chain

- GitHub Actions permissions/secrets;
- Auth0 secrets/config;
- R2 credentials/policies;
- PostgreSQL credentials;
- environment-variable leakage;
- logging/redaction;
- Python and npm dependency vulnerabilities;
- lockfiles;
- pinned/reviewed GitHub Actions;
- reproducible build controls.

### Privacy

- PII minimization;
- Lead/buyer data exposure;
- logs and exception telemetry;
- analytics/event data;
- raw IP / fingerprinting prohibitions;
- retention and access boundaries.

### Deployment / infrastructure

- container user/privilege;
- minimal exposed services/ports;
- immutable image/deploy expectations;
- secret injection;
- rollback;
- production network boundaries;
- backup/restore security;
- R2 backup access.

## Threat model requirement

The owning capability must retain an explicit attack-surface matrix in the repository:

```text
asset
→ attacker / trust level
→ attack path
→ expected control
→ adversarial test / retained proof
→ finding / disposition
```

The matrix must cover buyer/public, authenticated ordinary Account, broker member, privileged broker publisher/admin/owner, cross-Organization attacker, compromised/hostile browser input, and infrastructure/supply-chain boundaries where applicable.

## Required adversarial E2E proof

Testing must exercise the actual accepted buyer/broker flows rather than isolated helper functions only.

At minimum:

```text
public listing
buyer contact / Lead
broker login / Organization access
listing create/edit/publish/withdraw/reconfirm
media
Lead handling
SaleOutcome close-out
broker performance snapshot
```

Negative tests must prove unauthorized or malformed operations fail with zero unintended mutation/leakage.

## Acceptance threshold

The gate cannot pass unless:

```text
open CRITICAL findings = 0
open HIGH findings = 0

material MEDIUM findings =
  fixed
  OR explicitly documented, risk-assessed and Project-Owner accepted

cross-tenant adversarial suite = PASS
authentication / MFA adversarial suite = PASS
media / privacy adversarial suite = PASS
dependency / supply-chain security review = PASS
production-security configuration review = PASS
required retained proof = PASS
independent exact-head review = ACCEPT
Project Owner acceptance = RECORDED
```

A scanner-only pass is insufficient.

## Relationship to normal development

Normal slices must continue to enforce their own security/auth/privacy boundaries.

This gate adds a dedicated holistic adversarial pass after the coherent broker product exists. It does not justify deferring obvious security defects discovered earlier.

Any Critical/High security finding discovered before the dedicated hardening capability must be treated as an immediate blocker and not intentionally carried forward.

## Current scheduling direction

As of 2026-10-01:

- SLICE-0075 remains the active Broker Performance & Funnel Snapshot slice;
- no future slice number is preassigned here;
- post-0075 / launch-readiness reassessment should preserve this gate as mandatory;
- the dedicated hardening capability should occur after the broker product is coherent enough for full attack-surface testing and no later than immediately before the first real external broker self-service pilot.
