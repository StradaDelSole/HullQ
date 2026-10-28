# SLICE-0093 — First Power Drive Criterion: Retained Evidence Table

**Status:** Implementation evidence record, pending independent review and Owner acceptance. Not an acceptance closure.

## 1. Criterion mapping

| Canonical query token | Public filter? | PhysicalBoat claim vocabulary | BoatDesign v0.6 design-side mapping |
|---|---|---|---|
| `SHAFT` | Yes | `PowerDriveConfiguration.SHAFT` | `propulsion.drive_type = "shaft"` (qualified) |
| `STERNDRIVE` | Yes | `PowerDriveConfiguration.STERNDRIVE` | Unavailable — no v0.6 token maps to it |
| `POD` | Yes | `PowerDriveConfiguration.POD` | Unavailable — no v0.6 token maps to it |
| `WATERJET` | Yes | `PowerDriveConfiguration.WATERJET` | Unavailable — no v0.6 token maps to it |
| `OUTBOARD` | Yes | `PowerDriveConfiguration.OUTBOARD` | `propulsion.drive_type = "outboard"` (qualified) |
| `MIXED` | No (claim-only) | `PowerDriveConfiguration.MIXED` | N/A |
| `OTHER` | No (claim-only) | `PowerDriveConfiguration.OTHER` | N/A |
| (explicit `UNKNOWN`) | No | `AssertionKind.UNKNOWN` | N/A |

`saildrive`/`other`/`unknown` BoatDesign v0.6 `propulsion.drive_type` values have no authorized mapping (`hullq.search.power_drive_design_bridge.BOAT_DESIGN_DRIVE_TYPE_TO_SEARCH_POWER_DRIVE`) and fail closed to `MISSING`/`INSUFFICIENT_DATA` — never guessed as POD/STERNDRIVE/WATERJET.

## 2. Candidate planes and sources

| Plane | Enumeration | Category gate | Technical evaluation |
|---|---|---|---|
| Design-unresolved (claim-only) | `list_active_design_unresolved_listings` (unchanged from SLICE-0092) | Publisher-owned explicit `VALUE_ASSERTION(POWER)` (`hullq.application.power_inventory_query._resolve_power_claim_only_admission`) | `classify_claim_only_candidate` (reused, `hullq.application.native_inventory_query`) with `active_definitions=(POWER_DRIVE_CONFIGURATION_DEFINITION,)` |
| Design-linked | `list_active_design_linked_listings` (unchanged) | `resolve_physical_boat_vessel_category(...).resolution is POWER` (design+concrete combined, reused `hullq.application.vessel_category_resolution`) | design: `run_boat_design_configuration_query` with `POWER_DRIVE_CONFIGURATION_FIELD_PROJECTION_SPEC`; concrete: `classify_concrete_candidate` (reused) |

Both planes share: D29 current-public eligibility + freshness (`resolve_current_public_eligibility_for_many`, batched), the current publisher claim-observation reader (`list_current_physical_boat_claim_observations_for_many`, batched), and the identical MUST/AND truth kernel (`evaluate_projection`/`evaluate_configuration`). Source basis for every claim-only match is the fixed `PublisherClaimSourceBasis.PUBLISHER_CLAIM` literal — never serialized as independently verified.

## 3. Result-state matrix

| Scenario | Design-linked result | Claim-only result |
|---|---|---|
| Publisher-owned explicit `POWER` + matching token claim | `CONFIRMED_MATCH` (requires design-side match too) | `CONFIRMED_MATCH` |
| Explicit `SAIL`/`MOTORSAILER`/cross-Org `CONFLICT` category | `CONFIRMED_NON_MATCH` (`category_exclusion` populated) | `CONFIRMED_NON_MATCH` (`category_exclusion` populated) |
| Missing/`UNKNOWN` category, or `POWER` asserted only by a different Organization | `INSUFFICIENT_DATA` | `INSUFFICIENT_DATA` |
| Category admitted, but drive is `MIXED`/`OTHER`/`UNKNOWN`/wrong token | `CONFIRMED_NON_MATCH` | `CONFIRMED_NON_MATCH` |
| BoatDesign `drive_type` is `saildrive`/`other`/`unknown` (design-linked only) | `INSUFFICIENT_DATA` at the design level (never promoted to a concrete check) | N/A |
| D29-suppressed (withdrawn/non-public/stale) | excluded from every result surface | excluded from every result surface |

## 4. Explicit limitations (never silently claimed complete)

- `STERNDRIVE`/`POD`/`WATERJET` have **no design-linked bridge** in this slice: a design-linked PhysicalBoat can never reach `CONFIRMED_MATCH` for those three tokens, only `INSUFFICIENT_DATA` at the design level; they are reachable only through the design-unresolved claim-only path. This is a genuine, deliberate coverage gap (contract: "No v0.7 BoatDesign schema/migration is granted by this criterion"), not an oversight.
- Only one Power criterion exists; engine count/make/model, horsepower, fuel/energy source, speed/range/operating-point, and Power Broker Search-fit remain out of scope (tracked under #372).
- Synthetic 0/40/200 representative population cost was not independently re-measured in this slice beyond reusing the SLICE-0092 batched-read pattern verbatim; the pre-real-data/pilot scaling STOP (#355) is unchanged and still open.
- No real brokers, owner-direct trust, public pilot, or SEO/indexable exposure is introduced; both the API route and the five Astro pages are noindex.
