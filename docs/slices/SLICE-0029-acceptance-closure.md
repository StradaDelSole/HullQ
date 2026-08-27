# SLICE-0029 — Acceptance Closure

**ID:** SLICE-0029  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Independent-review verdict:** ACCEPT — no blocking or material findings remain after two bounded amendments  
**Implementation PR:** #83 — "SLICE-0029: primary-source BoatDesign applicability & conditional-clearance pilot"  
**Final reviewed implementation head:** `7b3493329ff2390000650aadddf03ae4f96895c6`  
**Implementation merge commit:** `cdf34e9431a01cbd5b02bf0dc149756cc944f919`  
**Exact-head PR CI:** run `33101958093`, SUCCESS  
**Exact-head PR manufacturer reproducibility:** run `33101958108`, SUCCESS  
**Final independent-review comment:** PR #83 issue comment `5443410435`

## Independent review result

Independent review accepts the SLICE-0029 implementation for Project Owner acceptance. The slice is **not `DONE` yet**; explicit Project Owner acceptance is still required under the normal workflow.

SLICE-0029 tested whether tightly bounded official Catalina primary-source research could both satisfy the accepted SR-6.6 source-rights path for manually curated discrete factual use and positively establish enough BoatDesign/applicability scope to justify a later canonical technical-promotion pilot. The accepted result is deliberately conservative: the rights condition is cleared for the exact bounded manual pilot, but the retained primary-source evidence is still insufficient to scope any of the reused SLICE-0028 technical candidates safely to a BoatDesign generation/configuration.

The deterministic result is therefore:

```text
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

This is an explicitly permitted SLICE-0029 negative-path outcome. No threshold or applicability rule was weakened to force a positive promotion result.

## Fixed identity and research boundary

The fixed pilot remained exactly:

```text
Q5051252  Catalina 22  -> BM_WDT0_6c94b5bc9e79402bb07309289905913e
Q5051253  Catalina 30  -> BM_WDT0_3fdd058699d145c6a1b044fc90b65201
```

The accepted identity boundary remains unchanged:

```text
canonical BoatModels            1,770
historical QID -> HullQ mappings 1,772
```

No discovery, fuzzy matching, identity expansion or canonical admission occurred.

External Catalina research remained bounded to official `catalinayachts.com` surfaces:

```text
retrieval ceiling    25
actual retrievals    13
```

Retrievals 12–13 were added during the second amendment as a bounded positive-path check for additional Catalina 30 dating evidence. Both official brochure-listing URLs resolved to lead-generation form pages with zero PDF links, so no further positively dated Catalina 30 technical document was found within the permitted source-surface classes.

No Catalina PDF, image, screenshot or page HTML was vendored into the repository; the retained package contains only the permitted audit facts, locators, measured values and fingerprints.

## Source-rights result

The accepted SR-6.6 result is limited to:

```text
bounded manually curated discrete factual use only
```

For the exact two-model / five-field pilot scope, `identity_seed` and `production_value` are positively cleared. The broader uses remain non-allow:

```text
automated_ingestion      unknown_unassessed
bulk_bootstrap           legal_review_required
artifact_redistribution  legal_review_required
```

The first independent review found that the initial implementation did not mechanically couple the six SR-6.6 conditions to the positive use clearance. Amendment 1 closed that blocker by deriving `identity_seed` / `production_value` through `derive_sr_6_6_use_clearance()`, validating an exact machine-readable `bounded_scope`, and enforcing `validate_permissions_bounded()` so broader permissions cannot silently become unscoped grants. Negative/tamper regressions cover the coupling, and `hullq.sources.rights.check_source_use` remains unchanged.

Amendment 2 did not alter this closed rights logic or the retained clearance assessment.

## BoatDesign / applicability result

### Catalina 22 — Q5051252

Positive primary evidence establishes a dated manufacturer redesign in January 1995 (`Catalina 22 markII`) and a later Catalina 22 Sport variant. However, the bounded pass did not recover markII-specific numeric specifications sufficient to determine which BoatDesign generation the reused SLICE-0028 technical candidates describe.

The retained pilot therefore correctly keeps `generation_boundary_established_for_this_pilot = false` in the specific sense required for canonical modeling of these technical fields: the redesign itself is real, but the candidate values cannot yet be positively scoped to the relevant generation.

Field outcomes:

```text
LOA            GENERATION_AMBIGUOUS
LWL            GENERATION_AMBIGUOUS
beam           GENERATION_AMBIGUOUS
draft_min      OPTION_SENSITIVE
displacement   NO_NORMALIZED_WIKIDATA_CANDIDATE
```

### Catalina 30 — Q5051253

The official archive exposes a `Catalina 30 MKI` label and two retrieved specification brochures, but the bounded evidence does not positively establish a BoatDesign generation boundary or a closed technical-value applicability range. The December 1974 introduction date is a BoatModel identity/production fact, not proof that the technical values in the undated brochure applied from 1974; the only positively dated technical document recovered is the 1990-09 MKI brochure print run.

Amendment 1 had incorrectly represented the half-open range `first_year: 1974`, `last_year: null` as bounded. Amendment 2 fixes the exact issue: production-year applicability requires both bounds positively known, unless a genuinely independent non-year scope supplies the relevant bound. Catalina 30 is therefore retained with `generation_boundary_established_for_this_pilot = false` and `unknown_or_unbounded = true`.

Field outcomes:

```text
LOA            INSUFFICIENT_EVIDENCE
LWL            INSUFFICIENT_EVIDENCE
beam           INSUFFICIENT_EVIDENCE
draft_min      NO_NORMALIZED_WIKIDATA_CANDIDATE
displacement   NO_NORMALIZED_WIKIDATA_CANDIDATE
```

No field for either BoatModel is retained as `SAFE_FOR_LATER_DESIGN_PROMOTION`.

The retained Catalina 30 shoal-draft disagreement is correctly recorded as:

```text
3'10" vs 4'4"  -> 6-inch disagreement, unresolved
```

The earlier `rudder` DesignOption claim was removed because it relied on cross-document non-mention. Retained keel/draft/transom/layout option findings rely on positive within-document evidence.

## Deterministic fail-closed behavior

The final implementation enforces the principal review boundaries mechanically:

- SR-6.6 positive use clearance is derived from the retained condition set rather than separately asserted;
- exact bounded rights scope is validated against the two fixed QIDs/HullQ IDs, five field pointers and two permitted use kinds;
- broader unscoped permissions cannot become `allowed`;
- half-open production-year ranges are rejected as genuinely bounded;
- a SAFE field requires a non-unknown/non-unbounded applicability scope;
- recommendation READY requires an established BoatDesign/applicability boundary and a SAFE field on the same BoatModel;
- the retained package recomputes to `APPLICABILITY_EVIDENCE_INSUFFICIENT`.

Focused regressions include both known-start/unknown-end and unknown-start/known-end year ranges plus recommendation defense-in-depth.

## Canonical mutation boundary

SLICE-0029 created or mutated zero canonical production identities or technical values. It did not:

- mint a BoatDesign ID;
- create/update a canonical BoatDesign row;
- modify a BoatModel row;
- create a DesignOption or NamedVariant canonical entity;
- create a FieldResolution;
- write a canonical technical baseline value;
- alter the accepted 1,770 / 1,772 identity boundary;
- implement Search, API, frontend or query behavior;
- start SLICE-0030.

## Validation evidence

Final reviewed implementation head:

`7b3493329ff2390000650aadddf03ae4f96895c6`

Implementation-agent local validation reported:

- offline SLICE-0029 retained-package verify: PASS;
- repository validator: PASS;
- Ruff format/lint: PASS;
- mypy: PASS, 43 source files;
- local full test run: **2,078 passed / 215 skipped**;
- local total coverage: **90.60%** (>=90% gate).

Independent exact-head remote verification confirmed:

- CI run `33101958093`: SUCCESS;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
  - dependency audit: SUCCESS;
  - db integration PostgreSQL 18: SUCCESS;
  - Ubuntu quality run independently reported repository governance PASS, Ruff PASS, mypy 43 files PASS, **2,078 passed / 215 skipped**, total coverage **90.60%**;
- Manufacturer artifact reproducibility run `33101958108`: SUCCESS on Ubuntu and Windows.

Implementation PR #83 was merged as:

`cdf34e9431a01cbd5b02bf0dc149756cc944f919`

## Review amendment trail

- initial reviewed head `9227fe9199d9451f56470fe326254c2ef04dff94`: **CHANGES REQUIRED**, PR #83 issue comment `5440610470` — SR-6.6 fail-closed coupling and Catalina 30 applicability overclaim;
- first amended head `cd0b2a72d527d4dd5badc08af8c5880acb03a83b`: SR-6.6 blocker **CLOSED**, Catalina 30 blocker still open; **STILL CHANGES REQUIRED**, issue comment `5442131521`;
- final reviewed head `7b3493329ff2390000650aadddf03ae4f96895c6`: Catalina 30 half-open-range overclaim closed through the permitted negative path; **ACCEPT**, issue comment `5443410435`.

## Preserved unresolved findings

The following remain unresolved by design and must not be silently promoted later:

- Catalina 30 shoal-draft discrepancy: `3'10"` vs `4'4"`;
- Catalina 30 true production end and the first/last applicability years of the retained technical values;
- whether the archive label `MKI` reflects a real second Catalina 30 BoatDesign generation;
- Catalina 22 markII-specific numeric values needed to associate the reused SLICE-0028 candidates with a technical generation.

These unresolved items are exactly why the accepted deterministic recommendation is `APPLICABILITY_EVIDENCE_INSUFFICIENT`.

## Evidence trail

- controlling contract: `docs/slices/SLICE-0029-primary-source-boatdesign-applicability-clearance-pilot.md`;
- retained package: `research/stage3/sl0029-primary-source-boatdesign-applicability/`;
- implementation PR: #83;
- final reviewed implementation head: `7b3493329ff2390000650aadddf03ae4f96895c6`;
- implementation merge commit: `cdf34e9431a01cbd5b02bf0dc149756cc944f919`;
- exact-head PR CI run `33101958093`, SUCCESS;
- exact-head PR manufacturer reproducibility run `33101958108`, SUCCESS;
- final independent-review comment: PR #83 issue comment `5443410435`;
- independent-review verdict: **ACCEPT — no blocking or material findings remain**;
- Project Owner acceptance: **PENDING**.

## Next boundary

This closure records independent acceptance of the implementation but does not itself mark SLICE-0029 `DONE` and does not authorize SLICE-0030. Explicit Project Owner acceptance is required next. After that acceptance, the normal `FINISH_SLICE` → independent readiness → `START_SLICE` workflow may continue.
