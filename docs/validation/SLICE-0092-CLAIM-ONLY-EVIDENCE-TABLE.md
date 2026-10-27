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
