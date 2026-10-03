# SLICE-0078 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / SECURITY HARDENING  
**Implementation PR:** #305  
**Accepted exact branch HEAD:** `294a22274b06d1a8006ab587e43819146ffe8fe0`  
**Merge commit:** `50243c5e4fd5d5b98ae391d90e4cb498869d567c`  
**Independent exact-head review:** ACCEPT on 2026-10-03  
**Project Owner acceptance:** explicitly recorded on 2026-10-03

## Accepted capability

SLICE-0078 completes the dedicated holistic Security Hardening & Adversarial Validation gate required before any real external broker self-service pilot.

Accepted scope includes:

- cross-tenant / IDOR / authorization adversarial validation;
- session / authentication / MFA boundary validation;
- CSRF hardening, including broker logout;
- bounded abuse-rate protection for buyer contact, login initiation and media upload;
- baseline FastAPI and Astro security response headers;
- malformed / oversized input and SQL-injection-path validation;
- media decode / decompression-bomb and forged-image rejection;
- privacy / PII / logging review;
- dependency / supply-chain review;
- production-security configuration review;
- retained attack-surface, findings and gate evidence;
- exact-head CI and Manufacturer artifact reproducibility.

## Accepted implementation and findings

Product/security findings discovered and resolved in-slice:

- SEC-0078-01 — logout CSRF discipline: FIXED;
- SEC-0078-02 — missing bounded abuse-rate protection: FIXED;
- SEC-0078-03 — missing backend baseline security headers: FIXED;
- SEC-0078-04 — missing Astro baseline security headers: FIXED;
- SEC-0078-09 — independent-review finding: attacker-controlled unbounded rate-limiter retained state: FIXED with explicit hard `max_keys` bound, expiry reclaim and deterministic LRU eviction.

Test/harness defects SEC-0078-05, SEC-0078-06 and SEC-0078-08 were also fixed and revalidated.

One upstream dependency advisory remained without an available upstream patch:

`SEC-0078-07`

The Project Owner explicitly accepted the documented residual risk with disposition:

`OWNER_RISK_ACCEPTED — CURRENTLY UNREACHABLE; RE-REVIEW TRIGGERS RETAINED`

Accepted basis:

- the HIGH rating originates from the upstream `http-cache-semantics` advisory;
- the affected Astro remote-image cache path is not currently reachable in HullQ;
- HullQ currently does not use `astro:assets`, remote `<Image>`, or `getImage()` paths that exercise the vulnerable code;
- no patched upstream dependency release was available at acceptance time;
- introducing a HullQ-specific fork / artificial no-op alias / vendored patch for an unreachable path was disproportionate.

Mandatory re-review triggers:

1. a patched upstream dependency release becomes available; or
2. HullQ introduces Astro remote-image / `astro:assets` usage that makes the affected path reachable.

## Validation result

Accepted retained proof:

```text
docs/validation/SECURITY_ATTACK_SURFACE_MATRIX_2026-10.md
docs/validation/SECURITY_ADVERSARIAL_EVIDENCE_2026-10.md
docs/validation/SECURITY_FINDINGS_REGISTER_2026-10.md
docs/validation/SECURITY_HARDENING_GATE_EVIDENCE_2026-10.md
```

Accepted exact-head repository verification at `294a22274b06d1a8006ab587e43819146ffe8fe0`:

```text
GitHub Actions CI: SUCCESS
Manufacturer artifact reproducibility: SUCCESS
repository governance validation: PASS
```

The accepted validation set includes the dedicated adversarial suite, focused rate-limiter unit coverage, affected-surface regression, real multi-process broker-workspace proof, Astro check/build, web unit tests, Python dependency audit and web dependency audit.

## Independent-review amendment history

Initial implementation candidate was independently reviewed and amended multiple times before acceptance.

Material independent-review finding:

- the first in-process rate limiter introduced attacker-controlled unbounded retained key state;
- this was classified HIGH because unauthenticated remote cardinality pressure could exhaust memory in the accepted single-process deployment;
- the implementation was corrected to a hard-bounded `OrderedDict`/LRU model with expiry reclamation and explicit `max_keys`.

Evidence terminology was also corrected so historical implementation/evidence heads are not incorrectly described as self-referential final PR heads.

Final independently accepted branch head:

`294a22274b06d1a8006ab587e43819146ffe8fe0`

No unresolved independent-review findings remain.

## Gate consequence

After explicit Owner acceptance:

```text
SECURITY_HARDENING_AND_ADVERSARIAL_VALIDATION_GATE_STATUS = PASS
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = PASS
BROKER_SELF_SERVICE_PILOT_STATUS = NOT_STARTED
PAID_BROKER_PLAN_STATUS = NOT_STARTED
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
```

Passing SLICE-0078 removes the dedicated pre-pilot Security Hardening gate blocker.

It does **not** start a broker pilot, paid plan, production pilot or public launch. Any future pilot still requires an explicit later workflow decision and any other then-triggered production-readiness obligations.

## Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

- holistic pre-pilot Security Hardening & Adversarial Validation gate;
- cross-tenant/auth/MFA/media/privacy/supply-chain/configuration adversarial validation;
- logout CSRF hardening;
- bounded abuse-rate protection;
- backend and Astro baseline security headers;
- bounded rate-limiter retained state;
- retained security evidence and findings register;
- Security Hardening gate PASS after explicit Owner risk acceptance.

### DECIDED_NOT_YET_IMPLEMENTED

- actual external broker self-service pilot;
- paid broker-plan activation;
- production pilot / public production launch;
- remaining Overall MVP obligations including export, periodic engagement reporting, Search-fit diagnostics, structured bulk onboarding and other trigger-bound capabilities.

### EXPLICITLY_DEFERRED

- distributed rate limiting / Redis or equivalent multi-instance coordination while the accepted deployment remains single-process;
- speculative dependency vendoring / no-op patching for the currently unreachable SEC-0078-07 path;
- any broad security-platform redesign not required by the accepted findings.

### GENUINELY_OPEN

- selection of SLICE-0079 after fresh post-SLICE-0078 Decision/Implementation Reconciliation and workflow reassessment;
- timing and exact scope of any future real external broker pilot.

### CONFLICT_OR_REGRESSION

None.

## Project-state closure

After this acceptance closure:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0078
PROJECT_STATE_QUEUE_SLICE: 0079
SLICE-0079: UNSELECTED
```

SLICE-0079 must be selected only after fresh post-SLICE-0078 Decision/Implementation Reconciliation and workflow reassessment.

Before SLICE-0079 readiness is created, the Project Owner must first receive the required short plain-language description of what the proposed slice would build/change and why.

`FINISH_SLICE.bat` for 0078 is permitted only after this closure PR passes independent exact-head closure review, required remote gates and merge to `main`.
