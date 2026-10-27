# SLICE-0092 — Claim-only threshold/evidence table and admitted-category status

Deliverables 4/5 of `docs/slices/SLICE-0092-qualified-design-unresolved-search.md`:
a compact retained record of (a) exactly what qualifies each existing Sail
criterion's threshold for the new design-unresolved claim-only path, and (b)
which categories are internally admitted vs. not-yet-technically-searchable
after this slice.

## 1. Per-criterion threshold/qualification decision (field-proof policy §C)

All nine existing Sail `CriterionDefinition`s are reused unchanged
(`src/hullq/search/criteria_registry.py`). For the claim-only path, exactly
the same fail-closed per-field qualification `classify_concrete_candidate`
already used for the design-linked path is reused via the shared
`_qualify_claims_against_definitions` helper
(`src/hullq/application/native_inventory_query.py`) — no second comparator.

| Criterion | Projection field | Internal unit / vocabulary | Qualifies iff |
|---|---|---|---|
| draft_max | `draft_max_m` | metres, Decimal | publisher's own current `DraftClaim` is `VALUE_ASSERTION`, no cross-Org value conflict |
| keel_configuration | `keel_configuration` | `KeelConfiguration` enum | publisher's own current `KeelConfigurationClaim` is `VALUE_ASSERTION`, no cross-Org conflict |
| loa (min/max) | `loa_m` | metres, Decimal | publisher's own current `LoaLengthClaim` is `VALUE_ASSERTION`, no cross-Org conflict |
| rudder_configuration | `rudder_configuration` | `RudderConfiguration` enum | publisher's own current `RudderConfigurationClaim` is `VALUE_ASSERTION`, no cross-Org conflict |
| hull_configuration | `hull_configuration` | `HullConfiguration` enum | publisher's own current `HullConfigurationClaim` is `VALUE_ASSERTION`, no cross-Org conflict |
| cockpit_position | `cockpit_position` | `CockpitPosition` enum | publisher's own current `CockpitPositionClaim` is `VALUE_ASSERTION`, no cross-Org conflict |
| deck_saloon | `deck_saloon` | `DeckSaloon` enum | publisher's own current `DeckSaloonClaim` is `VALUE_ASSERTION`, no cross-Org conflict |
| beam (min/max) | `beam_m` | metres, Decimal | publisher's own current `BeamClaim` is `VALUE_ASSERTION`, no cross-Org conflict |
| hull_material | `hull_material` | `HullMaterial` enum | publisher's own current `HullMaterialClaim` is `VALUE_ASSERTION`, no cross-Org conflict |

Every row above reads the identical typed storage the design-linked path
already uses — no parallel free-text unit, no new enum vocabulary. Any other
state (missing field, `UNKNOWN` assertion, cross-Organization disagreement on
the publisher's own value) fails closed to `MISSING` qualification, which
`evaluate_projection`'s leaf evaluators turn into `TruthState.UNKNOWN` — never
`TRUE`. All nine criteria compared in one `MixedAndQuery` on one coherent
per-PhysicalBoat observation set (`list_current_physical_boat_claim_observations`,
one SQL statement) combine via the unmodified `and_reduce` MUST/AND rule: one
confirmed `FALSE` anywhere wins; otherwise one `UNKNOWN` anywhere wins;
otherwise `TRUE`.

Conditions/operating-point comparisons do not exist among these nine
criteria, so "basis mismatch" is `NOT_APPLICABLE` here, never silently
"passed" — consistent with the design-linked path.

## 2. Category admission state after this slice (contract §A)

| Resolved category / admission state | Design-unresolved Sail technical Search |
|---|---|
| `SAIL`, publisher's own current `VALUE_ASSERTION(SAIL)` | **Admitted** — the new claim-only candidate path runs the nine-criterion kernel |
| `SAIL` via a *different* Organization's claim only (publisher missing/UNKNOWN) | **Not admitted** — `INSUFFICIENT_DATA`, never confirmed (contract §A: "Another Organization's category assertion cannot lend the publisher its Sail eligibility") |
| `UNKNOWN` (no claim anywhere, or explicit `UNKNOWN`) | **Not admitted** — `INSUFFICIENT_DATA`. Unlike the pre-existing **design-linked** legacy compatibility path, `UNKNOWN` is never treated as Sail here |
| `POWER` | **Explicitly excluded** — `CONFIRMED_NON_MATCH` with `VesselCategoryExclusionEvidence`. No Power `CriterionDefinition` exists; this slice does not make Power technical Search real |
| `MOTORSAILER` | **Explicitly excluded** — same as `POWER`. Motorsailer dual-domain Sail/Power matching policy remains `GENUINELY_OPEN` (unchanged by this slice) |
| `CONFLICT` (design/concrete or cross-Organization disagreement) | **Explicitly excluded** — `CONFIRMED_NON_MATCH` with `VesselCategoryExclusionEvidence`; never resolved toward either side |

The design plane never contributes evidence for a design-unresolved
PhysicalBoat (`resolve_physical_boat_vessel_category` is always called with
`boat_design_ref=None`), so every claim-only admission decision rests
entirely on the concrete per-Organization `VesselCategoryClaim` plane.

## 3. Source/trust status

Every claim-only match's evidence is `source_basis = PUBLISHER_CLAIM`: the
publishing Organization's own current, authenticated claim-revision
statement — never independently design-verified, never serialized as
`DESIGN_CONFIRMED`/"verified". Public API/SSR rendering (`publisher_claim_matches`
in `/api/search/{locale}`, the "publisher claim matches" section in
`web/src/components/SearchPageBody.astro`) carries this distinction through
to the buyer in all five required locales (en/de/fr/pt/es), alongside an
explicit, non-misleading disclaimer string
(`searchText.ts`'s `publisherClaimDisclaimer`).

## 4. Explicitly NOT made real by this slice (untouched obligations)

- **#372 — Power technical criterion family.** No Power `CriterionDefinition`,
  no numeric/conditional Power fields, no engine/propulsion/range model, no
  Power Buyer Search or Broker Power Search-fit. The category-neutral
  candidate enumerator (`list_active_design_unresolved_listings`) makes a
  POWER-categorized design-unresolved PhysicalBoat internally representable
  without a BoatDesign link, but it is never offered through the Sail
  criterion family and no Power UI/dimension exists.
- **#355 — pre-real-upload/pilot hardening.** This feature is strictly
  synthetic/internal; no real external broker data, pilot, or production
  exposure is introduced or implied. #355 remains a separate before-real-data
  STOP, not superseded by this Search-side progress.
- **Motorsailer cross-domain policy** remains `GENUINELY_OPEN`: a
  `MOTORSAILER` resolution is excluded from the Sail claim-only path exactly
  like `POWER`, never assumed equivalent to Sail.
- **Owner-direct/private-seller claim-only admission** is not introduced.
  This slice's publisher-claim path is reachable only through the existing
  authorized broker/dealer claim-write boundary (`write_physical_boat_claim_revision`,
  requiring the claiming Organization to equal the listing's own publishing
  Organization) — no new source/trust scope for unverified private sellers.
- **Source rights/status**: unchanged. No new external source feed, scrape,
  or paid provider acquisition is introduced; the claim-only path reads only
  already-durable, already-authorized first-party `PhysicalBoatClaimRevision`
  data.

## 5. Executable adversarial proof — where each case lives

| Named case | Test |
|---|---|
| FIX-0090-08 analog (design-unresolved, publisher-owned, complete claims) | `tests/persistence/test_native_inventory_query_claim_only_slice_0092.py::test_design_unresolved_sail_claim_confirms_via_mixed_keel_criterion`, `::test_design_unresolved_sail_claim_confirms_via_pure_draft_max`, `::test_design_unresolved_sail_claim_api_serialization` |
| FIX-0090-09 / FIX-0090-13 analog (current-snapshot authority, retraction) | `::test_design_unresolved_retraction_removes_confirmed_match` |
| FIX-0090-11a analog (missing/UNKNOWN category) | `::test_design_unresolved_missing_category_is_insufficient_never_confirmed`, `::test_design_unresolved_explicit_unknown_category_is_insufficient` |
| FIX-0090-11b analog (category conflict) | `::test_design_unresolved_power_category_is_confirmed_non_match`, `::test_design_unresolved_cross_organization_category_conflict_excluded` |
| Contract §A publisher-ownership rule | `::test_design_unresolved_other_organization_sail_claim_not_enough` |
| Regression boundary (design-linked unaffected) | `::test_design_linked_confirmed_match_unaffected_by_claim_only_candidate` |
| Shared kernel non-regression (`evaluate_projection` extraction) | `tests/unit/test_search_configuration_engine_evaluate_projection_slice_0092.py` |
| Existing SLICE-0091 category/claims regression (unchanged) | `tests/persistence/test_native_inventory_query_vessel_category_slice_0091.py`, `tests/persistence/test_search_read_vessel_category_slice_0091.py`, `tests/persistence/test_vessel_category_coherent_read_slice_0091.py` (rerun, unmodified, all passing) |
| Amendment (Finding B): genuine multi-leaf MUST/AND (TRUE/FALSE/UNKNOWN) on one current revision | `::test_claim_only_multi_leaf_and_true_true_confirms`, `::test_claim_only_multi_leaf_and_true_false_is_non_match`, `::test_claim_only_multi_leaf_and_false_wins_over_unknown`, `::test_claim_only_multi_leaf_and_true_unknown_is_insufficient` |
| Amendment (Finding B): all nine Sail fields, parametrized (correct/wrong/omitted) | `::test_all_nine_sail_fields_claim_only_threshold_proof[draft_max\|keel_configuration\|loa\|rudder_configuration\|hull_configuration\|cockpit_position\|deck_saloon\|beam\|hull_material]` |
| Amendment (Finding B): D29 suppression for the claim-only path | `::test_claim_only_d29_suppressed_organization_excludes_entirely` |
| Amendment (Finding B): two real PG connections, concurrent revision, no torn hybrid | `::test_claim_only_two_connection_concurrent_revision_never_sees_hybrid_state` |
| Amendment (Finding C): internal provenance retained + public non-leakage | `::test_source_evidence_retains_publisher_revision_provenance`, `::test_public_api_never_leaks_internal_source_evidence` |
| Amendment (Finding D, round 1): batched claim-observation read + measured population performance | `tests/persistence/test_native_inventory_query_claim_only_performance_slice_0092.py::test_claim_only_candidate_population_performance` (parametrized 0/40/200) |
| Amendment (Finding D, round 2): batched D29 eligibility+freshness, proven equivalent to the single-id resolver | `tests/persistence/test_current_public_eligibility_for_many_slice_0092.py` |

## 6. Amendment (independent review PR #387) — internal provenance (Finding C)

`hullq.application.native_inventory_query.PublisherClaimCandidateEvaluation`
now additionally carries:

- `source_basis: PublisherClaimSourceBasis` — a one-member typed enum
  (`PUBLISHER_CLAIM`) the public serializer (`hullq.api.app.
  _serialize_claim_only_match`) reads directly (`match.source_basis.value`)
  instead of writing an independent literal that could silently drift from
  the internal type.
- `source_evidence: PublisherClaimSourceEvidence | None` — the publishing
  Organization's own current claim-revision `revision_id`/
  `recorded_by_account_id`/`recorded_at`/`category_claim`, drawn from the
  identical single-query observation set (§E) every criterion evaluation
  and the category admission decision both use. `None` only when the
  publisher has no current claim-observation row at all.

Internal-only: the public API/SSR never serializes `source_evidence`'s
revision id or account id — only the fixed `source_basis` literal, exactly
as before. See `tests/persistence/test_native_inventory_query_claim_only_slice_0092.py::test_source_evidence_retains_publisher_revision_provenance`
and `::test_public_api_never_leaks_internal_source_evidence`.

## 7. Amendment (independent review PR #387) — candidate performance (Finding D)

### Round 1 (claim-observation read)

`hullq.persistence.physical_boat_claims.list_current_physical_boat_claim_observations_for_many`
batches the claim-observation read this slice's own claim-only funnel owns
across every currently-eligible candidate into exactly **one** SQL
statement, regardless of population size (proven deterministically by a
call-count spy, not a timing heuristic --
`tests/persistence/test_native_inventory_query_claim_only_performance_slice_0092.py::test_claim_only_candidate_population_performance`).

Round-1 measured evidence against a representative 40-candidate synthetic
population: 523 total SQL statements, 0.243s elapsed, ~13.1
statements/candidate. The reviewer's follow-up round correctly identified
that this left the *remaining* per-candidate D29 eligibility/freshness cost
(~12-13 of those ~13.1 statements/candidate) still unbounded in population
size — addressed below.

### Round 2 (D29 eligibility + freshness, the remaining gap)

`hullq.application.current_public_eligibility.resolve_current_public_eligibility_for_many`
(new) resolves D29 current-public eligibility AND freshness for the
**entire** candidate population through a small constant number of batched
`= ANY(%s)` statements covering every candidate's *cheap* facts (lifecycle,
organization publishing eligibility, market-episode/physical-boat existence,
freshness evidence). Any candidate failing one of these cheap checks is
returned immediately as an authoritative `SUPPRESSED` result with zero
further reads (`evaluate_current_public_eligibility`'s own rule: `status`
is `SUPPRESSED` iff *any* reason fired, so a cheap reason alone already
decides it). Only "survivor" candidates that pass every cheap check reach
the expensive, **unchanged** per-candidate reads
(`fetch_current_native_listing_offer`, `fetch_current_physical_boat_claim`,
`resolve_cover_state_and_image_presence`) and the identical, unmodified pure
`evaluate_current_public_eligibility` evaluator — byte-for-byte the same
decision the pre-existing single-id `resolve_current_public_eligibility`
would reach for that listing. That single-id function itself is completely
untouched, so every other caller (`public_listing_read`,
`broker_inventory_read`, the existing accepted design-linked Search path)
is unaffected; only `evaluate_claim_only_candidates`
(`hullq.application.native_inventory_query`) now calls the batched sibling.

**D29-equivalence proof** (bulk resolver vs. the pre-existing single-id
resolver, for every suppression state reachable through this repository's
accepted write paths —
`tests/persistence/test_current_public_eligibility_for_many_slice_0092.py`,
7 tests): fully-eligible control, `LIFECYCLE_NOT_ACTIVE`,
`FRESHNESS_NOT_CURRENT`, `ORGANIZATION_NOT_ELIGIBLE` (each proven to produce
an identical `status`, and for cheap-suppressed cases a provably truthful
subset of the full reason set), a `DRAFT`-only `MARKET_EPISODE_UNRESOLVED`
case, a mixed-population single-call proof (four different axes resolved
together, never cross-contaminating), and a direct proof that
`publish_native_listing`'s own readiness gate makes `OFFER_MISSING`/
`PHYSICAL_BOAT_CLAIM_MISSING`/`COVER_MISSING`/`NO_PUBLIC_USABLE_IMAGE`/
`PHYSICAL_BOAT_MISSING` unreachable for an `ACTIVE` listing in the first
place (a listing missing any of them never leaves `INCOMPLETE_LISTING`,
so neither resolver can ever observe those states post-`ACTIVE`) — see that
test module's docstring for the full architectural rationale.

**Round-2 measured evidence** (`tests/persistence/
test_native_inventory_query_claim_only_performance_slice_0092.py::test_claim_only_candidate_population_performance`,
parametrized at the reviewer's requested 0/40/200 sizes, same representative
40%/20%/20%/10%/10% category mix scaled to each size):

| Population | Total SQL statements | Elapsed | Statements/candidate |
|---|---|---|---|
| 0 | 2 | 0.001s | — (no candidates) |
| 40 | 169 | 0.091s | 4.22 |
| 200 | 809 | 0.389s | 4.04 |

This is a real, measured ~3.2x reduction in statements/candidate (13.1 →
~4.1) at the same 40-candidate size, and the near-constant ~4.0-4.2
statements/candidate from 40→200 is itself the evidence that the batched
cheap-fact cost is now genuinely O(1) against population size — the
remaining per-candidate cost is only the offer + cover/media-gallery reads
for survivors (claim observations remain the round-1 O(1) batched read).
No valid candidate is dropped at any size (asserted exactly against the
expected per-category classification at each size). The design-linked
Search path's own `resolve_current_public_eligibility`/
`resolve_current_freshness` calls are untouched.

## 8. Amendment (independent review PR #387) — buyer sensitivity truth (Finding A)

Two real bugs were fixed, both stemming from the claim-only path running
unconditionally for every Search (including every pure `draft_max`/
`keel_configuration` request SLICE-0057 sensitivity already serves):

1. **Sensitivity silently ignored claim-only matches.** `hullq.application.
   search_sensitivity.SensitivityResult` now additionally carries
   `current_claim_only_match_count`/`alternative_claim_only_match_count`/
   `newly_claim_only_match_count`/`no_longer_claim_only_match_count` — the
   entirely separate, truth-source-labeled design-unresolved delta for the
   identical current/alternative requirement pair, computed from the same
   coherent `REPEATABLE READ` evaluation the design-linked delta already
   uses. Never merged into the pre-existing `*_confirmed_match_count`
   fields, which stay byte-for-byte unchanged in value whenever zero
   claim-only matches are involved (non-regression for the original
   SLICE-0057 contract; the pre-existing `seeded`-fixture tests in
   `tests/persistence/test_search_sensitivity_api.py` continue to pass
   unmodified). The public `POST /api/search/{locale}/sensitivity` route
   and `SearchSensitivityBody.astro` both surface the new fields with
   dedicated, visibly distinct locale strings
   (`sensitivityCurrentPublisherClaimLabel` etc., all five locales) — so a
   direct API/POST caller is never told a misleading total that silently
   drops this result family (contract §F's explicit requirement either for
   full parity or a disclosed limitation; this slice chose full parity).
2. **"No confirmed matches" read as a totally empty result.**
   `SearchPageBody.astro`'s zero-design-matches branch now renders the new
   `noDesignConfirmedMatchesButPublisherClaimsExist` string (all five
   locales) instead of the plain `noConfirmedMatches`/
   `noConfirmedMatchesGeneric` text whenever one or more publisher-claim
   matches are shown in the separate section below — never two mutually
   contradictory no-results claims on the same page.

Evidence:

| Case | Proof |
|---|---|
| Claim-only delta appears/disappears alongside the pre-existing design-linked swap | `tests/persistence/test_search_sensitivity_api.py::test_sensitivity_separate_claim_only_delta_appears_with_criterion_change` |
| Exact reviewer-named scenario: 0 design matches + 1 publisher-claim match, never collapsed | `::test_sensitivity_zero_design_matches_still_reports_claim_only_count_accurately` |
| All five locales carry the new fields | `::test_sensitivity_claim_only_fields_present_in_every_supported_locale[en\|de\|fr\|pt\|es]` |
| Real PG + FastAPI + built Astro SSR: the exact zero-design-matches-with-claim-only-match page renders the unambiguous disclosure | `scripts/inspect_slice_0092_claim_only_search.py` step 6 (`NL-0092-INSP-CLAIM-TWIN`) |
| Locale text exists/interpolates/stays visibly distinct from the design-confirmed labels | `web/src/lib/__tests__/searchSensitivityText.test.ts`, `web/src/lib/__tests__/searchText.test.ts` |
| Decision-neutral tone preserved for the new copy | `searchSensitivityText.test.ts`'s existing banned-word check, extended to the new strings |

## 9. Amendment (independent review PR #387, round 2) — dependency security gate (Finding E)

Exact-HEAD CI reported `msgpack==1.2.1`, `CVE-2026-114613`, fixed in
`1.2.3`. `uv lock --upgrade-package msgpack` bumped the lockfile's resolved
`msgpack` to `1.2.4` (the next available patched version) — a minimal,
locked resolver update, no audit ignore/exception/suppression, no other
package's resolved version changed (confirmed by diffing `uv.lock`). `uv
sync --locked --all-groups` installed the new lock cleanly; `uv run
pip-audit` reports no known vulnerabilities.
