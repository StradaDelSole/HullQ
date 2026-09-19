# SLICE-0059 — Acceptance Closure

**ID:** SLICE-0059  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #221  
**Accepted implementation HEAD:** `ac06173187ef79fae4075762620359a254b2f884`  
**Implementation merge commit:** `c5eeaa6317db05f476d58d02295d7affa7bcac35`  
**Independent exact-head ACCEPT review:** 2026-09-19  
**Owner acceptance:** explicitly recorded 2026-09-19

## Accepted capability

SLICE-0059 adds one bounded anonymous buyer decision-support capability:

```text
existing browser-local Shortlist
→ load exactly the buyer-authored saved NativeListingId order
→ re-resolve current public listing truth
→ render one factual side-by-side matrix
→ preserve unavailable/service-error entries neutrally
→ do not mutate Shortlist membership
```

Compare uses the whole current anonymous Shortlist as its set. It does not create a second compare-selection store or durable compare object.

The accepted surface remains factual only. It does not select a winner, compute fit, rank boats, normalize prices or infer buyer preference.

## Accepted implementation behavior

The accepted implementation includes:

- localized `/{locale}/shortlist/compare` routes for `en`, `de`, `fr`, `pt` and `es`;
- `noindex` plus `private, no-store` on personalized Compare routes;
- zero-id empty state, one-id “save one more” state and two-plus factual Compare state;
- Compare set derived only from the accepted versioned browser-local Shortlist store;
- buyer-authored Shortlist order preserved as matrix column order;
- current truth resolved through the unchanged SLICE-0058 same-origin shortlist resolver and existing FastAPI public listing read;
- one aligned HTML table with shortlisted entries as columns and a fixed factual row vocabulary;
- current listing identity/navigation, asking price/POA in original currency, location, build year, LOA, draft, keel, rudder and freshness/last-confirmed disclosure where available;
- preserved `VALUE_ASSERTION`, `UNKNOWN`, omitted/not-supplied, unavailable and service-error semantics;
- no BoatDesign baseline fallback into missing concrete PhysicalBoat claims;
- unavailable and service-error entries retained as their own neutral columns without suppressing resolvable entries;
- localized freshness status and an explicit localized “last confirmed” label for the raw `last_confirmed_at` timestamp;
- horizontal overflow for narrow screens while retaining the aligned table;
- safe DOM construction via `document.createElement` / `textContent`, never raw untrusted HTML;
- no Compare database table, account link, compare history, persisted subset, telemetry or new migration;
- no Search criterion, score, winner, recommendation, price conversion or market-value inference.

## Independent review and amendments

Initial implementation exact head:

```text
584eddf28f58b29212a504210e3bb005668cdb9e
```

Independent exact-head review found four blocking issues:

1. the shipped UI rendered independent vertical cards rather than the required aligned side-by-side matrix;
2. freshness prose reused an English-only helper on non-English routes;
3. retained proof did not prove real shortlist-store sourcing, local membership immutability or later current-truth re-resolution after offer/claim revision;
4. the active slice branch was behind then-current canonical `main`.

Targeted amendment exact head:

```text
405c180e83e450b548e777f98c7824cd7c2f512f
```

That amendment introduced the aligned table, five-locale freshness status presentation, a real store/resolver Node harness over real HTTP and normal non-force integration of then-current `main`.

Delta-first re-review found three narrow residuals:

1. `last_confirmed_at` was displayed without an explicit “last confirmed” label and could be misread as a due timestamp;
2. the post-revision proof regenerated an equivalent local shortlist payload instead of carrying the exact retained payload bytes across the server-side truth change;
3. canonical `main` had advanced again because of an unrelated Claude/GitHub permission-autonomy fix.

Final accepted amendment exact head:

```text
ac06173187ef79fae4075762620359a254b2f884
```

The final amendment:

- added localized `lastConfirmedLabel` text for all five locales;
- renders freshness as `<localized status> · <localized last-confirmed label>: <ISO timestamp>`;
- retains the exact raw shortlist payload from the first proof run and reuses those exact bytes in the second post-revision run without calling `addToShortlist()` again;
- normally merged current `origin/main` with no rebase or force-push.

Independent exact-head re-review returned **ACCEPT** with no unresolved blocking finding.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- anonymous browser-local whole-Shortlist factual Compare
- current public truth re-resolution through the accepted SLICE-0058 boundary
- aligned factual matrix in buyer-authored order
- claim-scope UNKNOWN/not-supplied/unavailable/service-error preservation
- localized freshness plus explicit last-confirmed disclosure
- no score/winner/recommendation/FX conversion
- no Compare persistence

DECIDED_NOT_YET_IMPLEMENTED
- account/database Shortlist continuity
- cross-device continuity and anonymous-to-account migration
- BuyerRequirements overlay/persisted evaluation
- persisted Compare subset, independent reorder/pinning
- sharing/share tokens
- monitoring/contact/alerts
- FX and market-value methodology

EXPLICITLY_DEFERRED
- all additional items listed by the SLICE-0059 readiness contract

GENUINELY_OPEN
- none required to accept this slice

CONFLICT_OR_REGRESSION
- none found on the accepted exact head
```

## Exact-head verification

Remote verification on exact accepted HEAD `ac06173187ef79fae4075762620359a254b2f884`:

```text
CI run 35469721369 → SUCCESS
Manufacturer artifact reproducibility run 35469721348 → SUCCESS
```

All seven exact-head GitHub checks completed successfully:

- `db integration (PostgreSQL 18)`;
- `web quality (Astro/Node)`;
- `quality (ubuntu-latest)`;
- `quality (windows-latest)`;
- `reproduce (ubuntu-latest)`;
- `reproduce (windows-latest)`;
- `dependency audit`.

The PostgreSQL-18 integration job `105968353577` explicitly executed:

```text
SLICE-0059 anonymous factual shortlist compare real HTTP vertical proof → SUCCESS
```

The amended retained proof log included:

```text
12. compare set is sourced from the real shortlist store in buyer order; resolving through Compare's own seam leaves local membership byte-identical -> OK
13. the exact same retained shortlist payload (not regenerated) is carried through a later server-side offer/claim revision, and the next resolution reflects both new current values -> OK
ANONYMOUS FACTUAL SHORTLIST COMPARE RESULT -> PASS
```

The implementation agent's final local report recorded:

```text
repository validation: PASS
ruff format/check: PASS
mypy: PASS (105 files)
pytest: 5205 passed / 3 pre-existing skips
web tests: 116 passed
Astro check: 0 errors
web build: PASS
retained PostgreSQL/FastAPI/Astro proof: PASS
```

PR #221 merged the exact accepted implementation to `main` as:

```text
c5eeaa6317db05f476d58d02295d7affa7bcac35
```

## Verification-depth disclosure retained

The accepted retained proof does not execute a real headless browser DOM.

It verifies real PostgreSQL 18 + real FastAPI + built Astro HTTP behavior and imports the shipped TypeScript shortlist store/resolution/runtime modules under Node. Matrix row/column alignment and localized field derivation are covered by focused TypeScript unit tests, while the real-HTTP retained proof verifies truth transport, store sourcing, exact-payload non-mutation and later current-truth re-resolution.

This is a transparent verification-depth limit, not a claim that every browser interaction was driven end-to-end by a browser automation framework.

## Scope retained / explicitly deferred

SLICE-0059 does **not** add:

- database-backed or authenticated Shortlist persistence;
- cross-device continuity;
- anonymous-to-account migration;
- multiple or named Shortlists;
- persisted Compare subset selection;
- independent Compare reorder/pinning;
- sharing/share tokens;
- private notes;
- BuyerRequirements persistence or fit overlay;
- match scoring, winner, best-fit or recommendation;
- FX conversion, normalized price or market-value inference;
- Saved Search / Monitor / alerts;
- background availability monitoring;
- seller/broker contact or lead creation;
- telemetry-based preference inference;
- a third Search criterion;
- owner-direct publication/admission;
- Broker Workspace expansion;
- real external marketplace production data, production pilot or public launch.

The accepted technical native Search criterion count therefore remains exactly `2`.

## Trigger-gate state after acceptance

SLICE-0059 adds no technical Search criterion and uses internal/synthetic retained proof only.

Canonical trigger state remains:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

The accepted post-SLICE-0056 workflow reassessment remains `PASS`. SLICE-0059 acceptance does not create another workflow-reassessment transition.

Production Readiness remains `NOT_TRIGGERED`: no real external marketplace production data was introduced, no production pilot started and no public production launch occurred.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0059
PROJECT_STATE_QUEUE_SLICE:    0060
```

The queue number does **not** select or authorize a SLICE-0060 capability.

SLICE-0060 requires fresh post-SLICE-0059 repository/product reassessment and the normal Decision / Implementation Reconciliation before capability selection/readiness. No SLICE-0060 readiness or `START_SLICE.bat` action is authorized by this closure.

## Product execution checkpoint

HullQ's accepted anonymous buyer path now includes factual decision support after explicit save:

```text
Direct Search / public listing
→ explicit buyer Save
→ one local personal Shortlist
→ current public truth re-resolved
→ whole-Shortlist factual side-by-side Compare
→ unavailable/service-error kept neutral
→ no score/winner/recommendation
```

Shortlist membership remains buyer interest rather than HullQ fit, and Compare remains a projection over current accepted truth rather than a second truth model.

## Closure decision

```text
SLICE-0059 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0059
PROJECT_STATE_QUEUE_SLICE = 0060
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
