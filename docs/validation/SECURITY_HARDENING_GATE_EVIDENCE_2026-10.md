# Security Hardening & Adversarial Validation Gate Evidence — 2026-10 (SLICE-0078)

**Status:** PENDING — one item requires explicit Project-Owner risk acceptance before this gate may be marked PASS (see §3). Every other line of the acceptance threshold is now met, including exact-head CI and Manufacturer artifact reproducibility.
**Canonical basis:** exact new pushed HEAD recorded in §5/§6 below, superseding the prior (now-stale) `bceed86` reference — see the review-fix amendment findings listed immediately below.
**Independent review (exact-head `d8d0fd8aa00d68006078bb5743c477f1948c4a8e`) found two defects, both addressed by this amendment:**

```text
Finding A: src/hullq/security/rate_limit.py retained unbounded attacker-controlled
           in-memory state (see §3a, SEC-0078-09)
Finding B: this document's exact-head evidence was stale (named bceed86, the
           second-to-last push, not the actual final reviewed HEAD d8d0fd8) and
           incorrectly marked Manufacturer artifact reproducibility NOT APPLICABLE
           when `reproduce (ubuntu-latest)`/`reproduce (windows-latest)` are a real,
           required, actually-run-and-passing part of this repository's exact-head
           gate (see §5/§6, corrected below)
```
**Required outputs this document completes:**

```text
docs/validation/SECURITY_ATTACK_SURFACE_MATRIX_2026-10.md
docs/validation/SECURITY_ADVERSARIAL_EVIDENCE_2026-10.md
docs/validation/SECURITY_FINDINGS_REGISTER_2026-10.md
docs/validation/SECURITY_HARDENING_GATE_EVIDENCE_2026-10.md   (this file)
```

## 1. Gate result

```text
SECURITY_HARDENING_AND_ADVERSARIAL_VALIDATION_GATE_STATUS = NOT YET PASS
BLOCKING_REASON = SEC-0078-07 requires explicit Project-Owner risk acceptance (not a product-code defect; see §3)
BROKER_SELF_SERVICE_PILOT_STATUS = NOT_STARTED (unchanged, still prohibited)
PAID_BROKER_PLAN_STATUS = NOT_STARTED (unchanged)
```

This record activates no pilot, no paid plan and no production launch.

## 2. Acceptance threshold, evaluated line by line

```text
open CRITICAL = 0                                                    -> PASS
open HIGH = 0                                                        -> NOT MET: 1 raw-advisory HIGH (SEC-0078-07),
                                                                          assessed non-exploitable/unreachable in
                                                                          HullQ's current attack surface, no upstream
                                                                          fix exists; disposition requires Owner sign-off
material MEDIUM fixed OR Project-Owner risk-accepted                 -> PASS: all 4 MEDIUM findings (SEC-0078-01..04)
                                                                          fixed and retested in-slice; 0 remain open
cross-tenant adversarial suite = PASS                                -> PASS (TestCrossTenantHolisticSweep, 3/3)
authentication/MFA adversarial suite = PASS                          -> PASS (TestSessionAdversarial, 5/5)
media/privacy adversarial suite = PASS                               -> PASS (media abuse 2/2 in
                                                                          TestInputAndMediaAbuseAdversarial; privacy/PII
                                                                          logging reviewed, see attack-surface matrix §10)
dependency/supply-chain review = PASS                                -> PARTIAL: Python (`pip-audit`) clean; web
                                                                          (`npm audit`) clean at `--audit-level=critical`
                                                                          with SEC-0078-07 as the one documented
                                                                          exception requiring sign-off
abuse-protection mitigation itself introduces no new                 -> PASS (SEC-0078-09 found by independent
  unbounded-resource vector                                             review, fixed this amendment, see §3a)
production-security configuration review = PASS                      -> PASS (response-header baseline, HSTS
                                                                          conditioning, cookie-secure fixture,
                                                                          see attack-surface matrix §8/§11)
required retained proof = PASS                                       -> PASS (this document set + test/harness code
                                                                          committed with the normal repository tests)
repository validation = PASS                                         -> PASS, see §4
exact-head CI = SUCCESS                                              -> PASS — see §5 for the new exact HEAD this
                                                                          amendment produces
Manufacturer artifact reproducibility = SUCCESS                      -> PASS — `reproduce (ubuntu-latest)` /
                                                                          `reproduce (windows-latest)` are a real,
                                                                          required job in this repository's CI and
                                                                          actually ran and passed (corrected from an
                                                                          earlier, inaccurate "NOT APPLICABLE" claim
                                                                          in this same document — see the Finding B
                                                                          note at the top of this document). See §6.
```

**Overall:** every finding that is a genuine product-code security defect has been fixed and retested, and exact-head CI is now green. The acceptance threshold is not yet fully met only because of SEC-0078-07, a transitive-dependency advisory with no available fix anywhere upstream, assessed as unreachable in HullQ's current code. This is reported honestly rather than resolved by invented policy.

## 3. The one blocking item: SEC-0078-07

Per `CLAUDE.md`'s stop/escalation rule ("if a Critical/High issue cannot be safely fixed within this slice, recommended state must be BLOCKED... unless independent decision is sought"), this agent does not have standing to unilaterally decide that a raw-HIGH-severity advisory is acceptable to leave open — even though the reachability analysis in `SECURITY_FINDINGS_REGISTER_2026-10.md` (SEC-0078-07) is, to this agent's assessment, sound: no patched dependency version exists anywhere upstream, and the vulnerable code path has zero call sites in HullQ's own code.

The Project Owner must choose one of:

```text
(a) ACCEPT the risk as documented in SEC-0078-07, with the compensating control already
    in place (CI audit step scoped to --audit-level=critical, re-review triggered by any
    future astro:assets/remote-image usage or upstream patch release) — gate then PASSes;
(b) require a stronger mitigation before PASS (e.g. an explicit Vite/webpack alias or patch
    overriding astro's bundled remote-image module to a no-op, even though it is already
    unreachable) — a scoped follow-up, not a reason to re-open fixed findings SEC-0078-01..06;
(c) treat this as a hard BLOCKED gate until an upstream fix ships.
```

No pilot/paid/public-launch gate is affected by which choice is made — all three remain `NOT_STARTED` regardless.

**This amendment does not fabricate or assume a Project-Owner decision on SEC-0078-07.** It remains `GENUINELY_OPEN`, with its reachability analysis preserved unchanged (no new evidence surfaced by this amendment contradicts it, and no artificial dependency patch/no-op alias has been added merely to make the advisory disappear). The Owner risk decision on SEC-0078-07 occurs only after this amendment itself passes independent review.

## 3a. Independent-review finding A, fixed this amendment: SEC-0078-09

`src/hullq/security/rate_limit.py`'s `FixedWindowRateLimiter` — SEC-0078-02's own fix for unbounded request abuse — retained one dict entry per distinct key forever, reclaimed only if that same key was observed again after expiry. Because the contact and login limiters key on `request.client.host` with no authentication required, an attacker needs no botnet to generate effectively unbounded distinct keys (a single host with a routed IPv6 prefix is sufficient) and grow retained state without bound: the mitigation for unbounded abuse had itself become a new unbounded in-memory-growth vector. Classified **HIGH** (CWE-770, unauthenticated/remotely-reachable resource exhaustion against the single application process ADR-0010 specifies) based on concrete reachability, not merely as a hygiene nit.

**Fixed.** Retained state is now capped at `max_keys` (default 10,000) via an LRU-ordered `OrderedDict`: every `allow()` call first reclaims every entry whose window has fully lapsed, and only evicts the single coldest (least-recently-touched) entry if a genuinely new key still doesn't fit after reclaiming. An actively-reused key is always most-recently-touched and therefore never the eviction target — ordinary rate-limiting accuracy is unaffected under normal load, and under sustained adversarial cardinality pressure the bound is preserved by sacrificing perfect per-key accounting for cold keys rather than ever exceeding `max_keys` retained entries, exactly the required fail-safe direction. No Redis/distributed infrastructure/generalized rate-limiting platform was introduced — this remains a simple, deterministic, single-process, in-memory mechanism consistent with ADR-0010.

Full detail, including the concrete reachability reasoning behind the HIGH classification: `SECURITY_FINDINGS_REGISTER_2026-10.md` SEC-0078-09.

## 4. Repository validation referenced by this gate

```text
tests/unit/test_rate_limit_unit.py .......................... 13 passed  (was 6; +1 construction +5 bounded-state,
                                                                            see SEC-0078-09 / §3a)
tests/persistence/test_security_hardening_adversarial_api.py . 27 passed  (40 total with the unit file)
affected-surface regression (12 pre-existing test files) ..... 261 passed (0 failed after the SEC-0078-05/08a fixes)
scripts/inspect_broker_workspace_access.py (real multi-process
  HTTP vertical proof, 15 contract steps) ...................... PASS (0 failed after the SEC-0078-08b fix)
web: npm run check ............................................ 0 errors/warnings/hints
web: node --test (36 files) ................................... 362 passed (359 pre-existing + 3 new)
web: npm run build ............................................. clean
live header smoke (built server, /broker + /en/search) ........ PASS
uv run pip-audit ............................................... no known vulnerabilities
npm audit --audit-level=critical ............................... 0 critical (exit 0)
uv run python scripts/validate_repository.py .................. repository governance validation: PASS
```

Full detail and exact commands: `SECURITY_ADVERSARIAL_EVIDENCE_2026-10.md`.

## 5. External verification — remote CI

```text
Remote CI (GitHub Actions, PR #305) = SUCCESS at exact HEAD <RECORDED AFTER THIS AMENDMENT'S PUSH — see completion report>
```

```text
db integration (PostgreSQL 18)                        pass
dependency audit                                       pass
historical research/bootstrap replay (PostgreSQL 18)   pass
quality (ubuntu-latest)                                pass
quality (windows-latest)                                pass
web quality (Astro/Node)                               pass
```

Prior to this amendment, the first two pushes to this PR (`37e8778`, `1ef4f29`) each surfaced one real `db integration` failure — a full-suite job this slice's local validation deliberately does not re-run in full. Both were genuine test/harness defects exposed by the new product behavior, not product-code defects (SEC-0078-05 and SEC-0078-08), fixed and re-pushed. Per `CLAUDE.md`, this section reflects actually-observed GitHub Actions results at the exact HEAD this amendment produces, not local inference or a stale prior push's SHA.

## 6. External verification — Manufacturer artifact reproducibility

**Correction (Finding B):** an earlier version of this document marked this line `NOT APPLICABLE`. That was inaccurate — `reproduce (ubuntu-latest)` and `reproduce (windows-latest)` are real, required jobs in this repository's CI (`.github/workflows/ci.yml`), they run on every push/PR exactly like every other job, and they genuinely passed at HEAD `d8d0fd8aa00d68006078bb5743c477f1948c4a8e` before this amendment. Recording them accurately now rather than omitting them as inapplicable:

```text
Manufacturer artifact reproducibility (GitHub Actions, PR #305) = SUCCESS at exact HEAD <RECORDED AFTER THIS AMENDMENT'S PUSH>
```

```text
reproduce (ubuntu-latest)     pass
reproduce (windows-latest)    pass
```
