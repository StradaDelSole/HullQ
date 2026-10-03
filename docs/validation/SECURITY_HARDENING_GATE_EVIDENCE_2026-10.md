# Security Hardening & Adversarial Validation Gate Evidence — 2026-10 (SLICE-0078)

**Status:** PENDING — one item requires explicit Project-Owner risk acceptance before this gate may be marked PASS (see §3). Every other line of the acceptance threshold is now met, including exact-head CI.
**Canonical basis:** `bceed86` on `slice/0078-security-hardening-adversarial-validation` (PR #305).
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
exact-head CI = SUCCESS                                              -> PASS — all 8 GitHub Actions checks green
                                                                          at HEAD `bceed86` (see §5)
Manufacturer artifact reproducibility = SUCCESS                      -> NOT APPLICABLE to this slice (no manufacturer
                                                                          artifact/scrape pipeline touched)
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

## 4. Repository validation referenced by this gate

```text
tests/unit/test_rate_limit_unit.py .......................... 6 passed
tests/persistence/test_security_hardening_adversarial_api.py . 28 passed  (34 total with the unit file)
affected-surface regression (12 pre-existing test files) ..... 261 passed (0 failed after the SEC-0078-05/08a fixes)
scripts/inspect_broker_workspace_access.py (real multi-process
  HTTP vertical proof, 15 contract steps) ...................... PASS (0 failed after the SEC-0078-08b fix)
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
Remote CI (GitHub Actions, PR #305) = SUCCESS at exact HEAD bceed86
```

```text
db integration (PostgreSQL 18)                        pass   5m0s
dependency audit                                       pass   17s
historical research/bootstrap replay (PostgreSQL 18)   pass   39s
quality (ubuntu-latest)                                pass   36s
quality (windows-latest)                                pass   1m21s
reproduce (ubuntu-latest)                              pass   12s
reproduce (windows-latest)                             pass   25s
web quality (Astro/Node)                               pass   29s
```

The first two pushes to this PR (`37e8778`, `1ef4f29`) each surfaced one real `db integration` failure — a full-suite job this slice's local validation deliberately does not re-run in full. Both were genuine test/harness defects exposed by the new product behavior (not product-code defects; see SEC-0078-05 and SEC-0078-08 in the findings register), fixed and re-pushed. The third push (`bceed86`) is green on every job. Per `CLAUDE.md`, this status reflects actually-observed GitHub Actions results, not local inference.
