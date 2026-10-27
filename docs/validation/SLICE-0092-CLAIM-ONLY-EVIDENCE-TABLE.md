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
| Amendment (Finding D): batched read + measured bounded population performance | `tests/persistence/test_native_inventory_query_claim_only_performance_slice_0092.py::test_claim_only_candidate_population_performance` |

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

`hullq.persistence.physical_boat_claims.list_current_physical_boat_claim_observations_for_many`
batches the claim-observation read this slice's own claim-only funnel owns
across every currently-eligible candidate into exactly **one** SQL
statement, regardless of population size (proven deterministically by a
call-count spy, not a timing heuristic --
`tests/persistence/test_native_inventory_query_claim_only_performance_slice_0092.py::test_claim_only_candidate_population_performance`).

Measured, real evidence against a representative 40-candidate synthetic
population (16 publisher-owned-SAIL matching, 8 publisher-owned-SAIL
non-matching, 8 explicit POWER, 4 no-category, 4 SAIL-claimed-by-a-
different-Organization-only): **523 total SQL statements, 0.243s elapsed,
~13.1 statements/candidate**, all 40 candidates correctly classified (none
silently dropped by the batching change). The per-candidate D29 eligibility/
freshness cost (~12-13 statements/candidate) is pre-existing shared
architecture (`hullq.application.current_public_eligibility`,
`hullq.application.native_listing_freshness`), reused unchanged by both the
design-linked and claim-only funnels; batching it would require rewriting
those shared resolvers for every other caller, out of this slice's scope.
This slice's own additive claim-observation read is exactly 1 statement for
the whole population rather than 1 per candidate -- the part of the new
path this slice fully owns is bounded to O(1), not O(N).

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
