# SLICE-0090 — Sail+Power Hard-Case Evidence Corpus v0.1

**Status:** DESIGN_RESEARCH fixture specification — synthetic/tabletop only, no code executes these fixtures in this slice  
**Date:** 2026-10-26  
**Purpose:** reproducible, labeled hard cases proving the design proposal in `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md` §2 handles the adversarial scenarios the slice contract's "Mechanical invariants / failure modes" section names, before any future slice writes code against them.

All vessels, Organizations, hull identifiers and claim values below are **synthetic**. No real buyer, broker or vessel PII is used. Each case states: setup, the exact invariant it exercises, and the expected classification outcome under the **proposed** (not yet implemented) design from the architecture pack. Where a case exercises already-implemented Sail behavior, the expected outcome is the **currently accepted, already-tested** behavior (cited to its owning slice), not a new claim.

Case IDs are stable identifiers for future test naming (`FIX-0090-NN`); they are not pytest node IDs.

---

## FIX-0090-01 — Mono-hull Sail baseline (control case, already implemented)

- **Setup:** Design-linked monohull sailing yacht, fully qualified keel/rudder/hull-config/deck-saloon/draft/beam/loa/hull-material claims, all `VALUE_ASSERTION`, no conflicts.
- **Invariant exercised:** the existing nine-criterion MUST/AND kernel produces `CONFIRMED_MATCH` for a request naming any subset of the nine criteria.
- **Expected outcome:** `CONFIRMED_MATCH` — already covered by accepted SLICE-0051/0055/0086/0087 tests; this fixture is the corpus's control, not new scope.

## FIX-0090-02 — Sail multihull (catamaran)

- **Setup:** Design-linked catamaran, `hull_configuration = CATAMARAN`, all other sail criteria qualified.
- **Invariant exercised:** monohull/catamaran/trimaran are independent first-class dimensions (core data guardrail); a request for `keel_configuration = FIN` against a catamaran must not spuriously match or crash.
- **Expected outcome:** `CONFIRMED_NON_MATCH` for a fin-keel request (catamarans have a structurally different keel/hull relationship, captured via existing `HullConfiguration`/`KeelConfiguration` enums) — or `INSUFFICIENT_DATA` if the design's keel dimension genuinely does not apply to its hull configuration; never a fabricated match. Already testable under current accepted code; included here to anchor the corpus's baseline before Power cases are layered on.

## FIX-0090-03 — Motorsailer (category ambiguity by design, not data gap)

- **Setup:** A vessel whose design is genuinely dual-propulsion (auxiliary sail + significant engine), category claim `MOTORSAILER` (proposed `VesselCategory` value, §2.1 of the architecture pack).
- **Invariant exercised:** motorsailer must not be guessed from hull/model-name text (Owner decision §1 "Nicht entschieden"); it must not silently fall into either pure-Sail or pure-Power criterion evaluation.
- **Expected outcome (proposed design):** excluded from both the Sail-only and Power-only candidate sets unless/until a future slice defines an explicit motorsailer criterion policy; visible as `MOTORSAILER` category, `INSUFFICIENT_DATA` for any category-specific technical criterion until that policy exists — never defaulted to Sail.

## FIX-0090-04 — Power, planing hull

- **Setup:** Design-linked (hypothetically, under a future Power BoatDesign schema) planing-hull motor yacht, single/twin inboard diesel, qualified engine count/power/fuel-type claims.
- **Invariant exercised:** Power's own `CriterionDefinition` family (proposed §2.2) reuses `evaluate_configuration` with no fork; a planing-hull request must not be evaluated by any Sail criterion.
- **Expected outcome (proposed design):** `CONFIRMED_MATCH` on a correctly specified propulsion-configuration request, through the same MUST/AND kernel Sail already uses — proving "same engine, new instances," not "new engine."

## FIX-0090-05 — Power, displacement hull (same family contrast case)

- **Setup:** Design-linked full-displacement motor yacht, single engine, low-power-to-weight configuration.
- **Invariant exercised:** hull-performance classification (planing vs. displacement vs. semi-displacement) is itself a claimed/sourced dimension, not inferred from length or engine count alone.
- **Expected outcome (proposed design):** `CONFIRMED_NON_MATCH` against a planing-hull-specific request; `INSUFFICIENT_DATA` if the design record has no qualified hull-performance claim at all — never a guessed classification from LOA/engine-count heuristics.

## FIX-0090-06 — Two model generations / engine variants of the same design family

- **Setup:** One `BoatDesign` family with two `NamedVariant` generations, differing only in engine package (Gen 1: single 300hp diesel; Gen 2: twin 250hp diesel), both design-linked.
- **Invariant exercised:** generation-aware `design_set_builder` resolution (the same mechanism already proven for Sail's `rudder_configuration` derived-value case) must keep the two generations' engine claims from merging into one false composite configuration.
- **Expected outcome:** a request for "twin engine" matches only Gen 2 listings; Gen 1 listings classify `CONFIRMED_NON_MATCH`, never `CONFIRMED_MATCH` through generation conflation.

## FIX-0090-07 — Re-powered used boat (refit engine vs. original brochure) — explicitly named in the slice contract

- **Setup:** `BoatDesign` brochure specifies a single original engine model; the concrete `PhysicalBoat`'s current publisher claim asserts a different, replaced engine (documented refit, dated claim, source = broker attestation).
- **Invariant exercised:** **"A model/generation/spec-sheet fact never silently proves installed equipment on a particular offered boat"** (slice contract's must-never-change invariant, verbatim). The concrete claim must win for *this* PhysicalBoat's engine field; the brochure fact must never override or silently merge with it.
- **Expected outcome:** the listing's effective engine evidence is the **concrete claim** (refit engine), tagged `source_basis: PUBLISHER_CLAIM`, with the original brochure engine retained as design-level evidence but explicitly not used to classify this listing's current engine criterion. A request matching the *original* brochure engine and not the refit engine classifies `CONFIRMED_NON_MATCH` for this listing.

## FIX-0090-08 — Design-unresolved but typed, issuer-owned current claim

- **Setup:** `PhysicalBoat.boat_design_ref = None` (no matched BoatDesign record exists), but the publishing Organization has asserted a complete, dated, typed claim set for every criterion a buyer's request constrains (e.g. propulsion configuration, LOA, hull material).
- **Invariant exercised:** the proposed qualified-concrete-claim candidate path (§2.3) must admit this listing to Search results without inventing a BoatDesign match; the existing design-linked path must remain completely unaffected (regression boundary).
- **Expected outcome (proposed design):** `CONFIRMED_MATCH` via the new path only, `source_basis: PUBLISHER_CLAIM`, visibly distinguished from a design-confirmed match; absent the new path (i.e. on current HEAD), this listing is **invisible** to native technical Search today — this fixture is also the regression baseline proving today's gap.

## FIX-0090-09 — Disputed engine hours / retracted value

- **Setup:** Publisher initially claims `engine_hours = 450`; a subsequent revision retracts/corrects to `engine_hours = 1450` (a typo-scale correction), with both revisions timestamped.
- **Invariant exercised:** claim-revision history is preserved (not overwritten); the **current** revision is authoritative for live Search classification; a retracted value must not continue silently backing an already-cached match.
- **Expected outcome:** any Search evaluation performed after the correction uses `1450`; the `450` revision remains in the audit/revision history but is not re-surfaced as current; a request for "engine_hours <= 500" classifies `CONFIRMED_NON_MATCH` after the correction, even if it had classified `CONFIRMED_MATCH` before the correction was recorded.

## FIX-0090-10 — Operating-condition-dependent speed/fuel/range

- **Setup:** Publisher claims `range_nm = 400` with no recorded speed/load/sea-state/measurement-basis; a second, better-documented claim from an engine-manufacturer technical sheet (Family 8 of the source-rights matrix) states `fuel_consumption` at a specific RPM/load with an explicit test standard.
- **Invariant exercised:** a bare scalar range claim with no basis must not satisfy a condition-specific Search criterion (e.g. "range >= 350nm at cruise speed"); tank-capacity ÷ burn-rate arithmetic is at most a labeled derived estimate, never a confirmed operating-point fact (slice contract, post-0088 contract §3 point 5).
- **Expected outcome (proposed `OperatingPointClaim` design, §2.4):** the bare `range_nm=400` claim alone yields `INSUFFICIENT_DATA` for any condition-qualified range criterion; only the manufacturer-sheet-sourced, basis-tagged claim can back a `CONFIRMED_MATCH`, and only when the request's stated condition is compatible with the claim's recorded basis.

## FIX-0090-11 — Unknown category and category conflict

- **Setup (two sub-cases):**
  - **11a — unknown:** no category claim recorded at all for the design or the concrete boat.
  - **11b — conflict:** the design-level category claim says `SAIL`; the concrete `PhysicalBoat`'s own publisher claim says `POWER` (e.g. a data-entry error or a genuinely re-classified vessel), with no revision resolving the contradiction.
- **Invariant exercised:** **"UNKNOWN and CONFLICT never become verified matches"** (slice contract, verbatim) and cross-category exclusion must not silently pick a side.
- **Expected outcome:** 11a classifies `UNKNOWN`/`INSUFFICIENT_DATA` for every category-specific criterion (excluded from both Sail-only and Power-only technical result sets, visible in a general/unclassified bucket if one exists, never silently defaulted to Sail); 11b surfaces an explicit `CONFLICT` state to any consumer and is excluded from both category-specific confirmed-match sets until a publisher/reviewer resolves it — never resolved automatically toward either category.

## FIX-0090-12 — Import→export category loss (round-trip)

- **Setup:** A Power-category listing (post-future-category-model) is exported through the existing NautiX writer, whose pinned XSD enumeration has no Power-appropriate boat-type token.
- **Invariant exercised:** export must disclose the category-fidelity loss rather than silently writing an incorrect `sail-yacht` tag (or any other nearest-fit guess) for a non-Sail vessel (§2.5 of the architecture pack; post-0088 contract §2 row "Export 0088 NautiX category").
- **Expected outcome (proposed design):** the exporter either omits/flags the unsupported field with an explicit warning in its result object, or (if a future NautiX version is adopted) emits the correct token — but under the *current* pinned schema, writing `sail-yacht` for a Power listing is a defect the future export slice must prevent, not a tolerated default. This fixture is the explicit negative case that future slice (`E` in the decision map) must pass before any Power listing is allowed through that writer.

## FIX-0090-13 — Publisher retraction after publication

- **Setup:** A listing is `ACTIVE` and D29-eligible with a `CONFIRMED_MATCH` evidence set; the publisher then retracts the Organization's qualifying claim (e.g. corrects a propulsion-configuration claim that no longer satisfies a previously matching request) without changing lifecycle state.
- **Invariant exercised:** Search evidence must be re-derived from the **current** claim snapshot on every evaluation, never cached as permanently true from a prior snapshot (mirrors FIX-0090-09's revision-authority invariant, at the listing-eligibility level rather than the single-field level).
- **Expected outcome:** the listing immediately classifies against the new claim snapshot; a request that matched before retraction may now classify `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA` — the architecture must not have any code path that treats "once matched" as a durable fact independent of current claims.

---

## Coverage check against the slice contract's named adversarial cases

| Slice contract case | Fixture(s) |
|---|---|
| refit engine vs. original brochure | FIX-0090-07 |
| two Power variants | FIX-0090-04, FIX-0090-05 (hull-performance contrast) and FIX-0090-06 (same-family generation/engine variant) |
| missing design reference | FIX-0090-08 |
| UNKNOWN and conflict category | FIX-0090-11a, FIX-0090-11b |
| publisher retraction | FIX-0090-13 (listing-level), FIX-0090-09 (field-level disputed/retracted value) |
| conditional consumption/range | FIX-0090-10 |
| rights-denied source | see `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md` Family 5 (RED) and Family 7 (UNKNOWN) — no separate listing fixture needed, this is a source-registry-level case, not a claim-evaluation case |
| import→export category loss | FIX-0090-12 |

Thirteen cases are specified, exceeding the slice contract's eight-case minimum, and every named adversarial scenario in the contract's "Executable adversarial proof" line is mapped to at least one fixture.

## Status of execution

**No pytest/runtime execution occurred against these fixtures in this slice.** This is a tabletop/documentation-only traceability inspection, matching the slice contract's explicit instruction to mark future PostgreSQL/API/browser runtime assertions as `FUTURE`, never `PASS`, in a DESIGN_RESEARCH slice. Each future implementation slice named in the decision map (`docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md` §4) must convert its relevant fixtures into real executable tests as part of its own acceptance criteria.
