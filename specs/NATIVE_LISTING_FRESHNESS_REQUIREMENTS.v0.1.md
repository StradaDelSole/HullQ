# HullQ — NativeListing Freshness Requirements v0.1

**Status:** READY normative requirement package for SLICE-0052  
**Controlling contract:** `specs/NATIVE_LISTING_FRESHNESS_CONTRACT.v0.1.md`

These requirements extend the active marketplace requirement set for the bounded manual-native freshness/reconfirmation capability. They do not alter technical Search criteria or alert/monitoring semantics.

### REQ-MARKET-007 — Lifecycle and freshness remain separate
HullQ MUST represent NativeListing freshness separately from lifecycle and MUST NOT infer `WITHDRAWN`, `SOLD` or `ARCHIVED` solely from elapsed confirmation time.

**Acceptance:** an ACTIVE listing can evaluate as STALE while its durable lifecycle remains ACTIVE and no withdrawal/sale transition is created.

### REQ-MARKET-008 — Freshness is evidence-backed
Manual native listing freshness MUST derive from immutable publication/reconfirmation evidence and MUST NOT be reset to current time merely because a migration, deployment or read occurs.

**Acceptance:** a pre-existing ACTIVE listing derives its effective confirmation age from its retained DRAFT→ACTIVE publication timestamp or later immutable reconfirmation evidence; missing admissible evidence yields UNKNOWN.

### REQ-MARKET-009 — Manual freshness policy is deterministic
The `MANUAL_NATIVE_V1` policy MUST classify freshness using an exact 30-day confirmation TTL plus 7-day grace period with timezone-aware UTC boundary semantics.

**Acceptance:** exact +30d evaluates DUE_FOR_CONFIRMATION, exact +37d evaluates STALE, and a future confirmation timestamp relative to `as_of` fails closed to UNKNOWN.

### REQ-MARKET-010 — Current buyer surfaces are freshness-gated
Current public listing and native-inventory Search surfaces MUST admit only ACTIVE listings whose freshness is CONFIRMED or DUE_FOR_CONFIRMATION; STALE/UNKNOWN inventory MUST NOT be presented as current.

**Acceptance:** an otherwise identical listing disappears from the current public listing/Search surfaces at the STALE boundary without changing lifecycle, and an authorized reconfirmation restores current-market eligibility.

### REQ-MARKET-011 — Reconfirmation is authorized, immutable and retry-safe
Explicit NativeListing reconfirmation MUST use the accepted professional-publisher authorization/Organization boundary, append immutable audit evidence with a system-recorded timestamp, and fail closed on conflicting ID reuse or unauthorized state/principal input.

**Acceptance:** authorized ACTIVE reconfirmation durably appends one event; exact retry is idempotent; cross-Organization, denied, DRAFT/WITHDRAWN and conflicting-ID attempts append no new event and do not mutate listing lifecycle/facts.