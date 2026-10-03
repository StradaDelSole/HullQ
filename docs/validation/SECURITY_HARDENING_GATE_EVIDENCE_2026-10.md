# Security Hardening & Adversarial Validation Gate Evidence — 2026-10 (SLICE-0078)

**Status:** PENDING — one item requires explicit Project-Owner risk acceptance before this gate may be marked PASS (see §3).
**Canonical basis:** uncommitted-at-time-of-writing working tree on `slice/0078-security-hardening-adversarial-validation`; exact HEAD SHA recorded in the slice completion report once committed.
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
production-security configuration review = PASS                      -> PASS (response-header baseline, HSTS
                                                                          conditioning, cookie-secure fixture,
                                                                          see attack-surface matrix §8/§11)
required retained proof = PASS                                       -> PASS (this document set + test/harness code
                                                                          committed with the normal repository tests)
repository validation = PASS                                         -> PASS, see §4
exact-head CI = SUCCESS                                              -> NOT VERIFIED — not yet pushed/observed on
                                                                          GitHub Actions (see §5)
Manufacturer artifact reproducibility = SUCCESS                      -> NOT APPLICABLE to this slice (no manufacturer
                                                                          artifact/scrape pipeline touched)
```

**Overall:** every finding that is a genuine product-code security defect has been fixed and retested; the acceptance threshold is not yet fully met only because of SEC-0078-07, which is a transitive-dependency advisory with no available fix, assessed as unreachable in HullQ's current code, and because exact-head CI has not yet been observed. Both are reported honestly rather than resolved by invented policy.

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

## 4. Repository validation referenced by this gate

```text
tests/unit/test_rate_limit_unit.py .......................... 6 passed
tests/persistence/test_security_hardening_adversarial_api.py . 28 passed  (34 total with the unit file)
affected-surface regression (11 pre-existing test files) ..... 249 passed (0 failed after the SEC-0078-05 fix)
web: npm run check ............................................ 0 errors/warnings/hints
web: node --test (36 files) ................................... 362 passed (359 pre-existing + 3 new)
web: npm run build ............................................. clean
live header smoke (built server, /broker + /en/search) ........ PASS
uv run pip-audit ............................................... no known vulnerabilities
npm audit --audit-level=critical ............................... 0 critical (exit 0)
```

Full detail and exact commands: `SECURITY_ADVERSARIAL_EVIDENCE_2026-10.md`.

## 5. External verification

```text
Remote CI (GitHub Actions, exact pushed HEAD) = NOT VERIFIED
```

The branch has not been pushed for this slice's changes at the time of writing. Per `CLAUDE.md`, local green tests are never treated as proof of remote CI; this status must be updated only after the exact HEAD is actually observed to pass on GitHub Actions.
