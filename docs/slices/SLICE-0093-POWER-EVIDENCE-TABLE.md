# SLICE-0093 — First Power Drive Criterion: Retained Evidence Table

**Status:** Implementation evidence record, pending independent review and Owner acceptance. Not an acceptance closure. Updated for the PR #390 review amendment (Findings A–F).

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
| Category admitted, but drive is `OTHER`/`UNKNOWN`/wrong single token | `CONFIRMED_NON_MATCH` | `CONFIRMED_NON_MATCH` |
| Category admitted, but drive is `MIXED` (review amendment Finding A) | `INSUFFICIENT_DATA` for every one of the five tokens — `MIXED` never proves the absence of any single accepted drive, so it is read as `UNKNOWN` at the Power-specific claim-qualification boundary (`hullq.search.power_criteria_registry._read_power_drive_configuration_claim`), never a confirmed categorical scalar | `INSUFFICIENT_DATA` for every one of the five tokens, identical reasoning |
| Cross-Organization conflicting current drive values (same PhysicalBoat, same POWER category) | `INSUFFICIENT_DATA` for every disputed token — same-PhysicalBoat cross-Organization contradiction guard (`_qualify_claim_field`) | `INSUFFICIENT_DATA`, identical reasoning |
| BoatDesign `drive_type` is `saildrive`/`other`/`unknown` (design-linked only) | `INSUFFICIENT_DATA` at the design level (never promoted to a concrete check) | N/A |
| D29-suppressed (withdrawn/non-public/stale) | excluded from every result surface | excluded from every result surface |

**`OTHER` vs `MIXED` (review amendment Finding A, resolved):** `OTHER` denotes a confirmed single (if uncatalogued) drive — the publisher would have used the real token if the boat had one of the five, so `OTHER` genuinely is not any of them; ordinary categorical equality already yields the correct `CONFIRMED_NON_MATCH`, identical treatment to `HullMaterial.OTHER`/`KeelConfiguration.OTHER` elsewhere in this codebase. `MIXED` denotes unlike drive types that may include one of the five accepted tokens (contract: "even if the vessel uses one of the types"), so it can never be read as a proven exclusion — it is reinterpreted as `UNKNOWN` at the Power-specific read boundary only, never touching the shared Sail categorical-equality semantics.

## 4. NautiX export guard (review amendment Finding B, resolved)

`hullq.application.inventory_export._claim_physical_boat_facts` now populates `ExportRow.vessel_category` from the **resolved** current category (`hullq.domain.vessel_category.resolve_vessel_category`: design plane + this Organization's own claim + every other current claiming Organization) rather than only the exporting Organization's own raw claim. `hullq.domain.inventory_export._nautix_preflight` rejects the row closed whenever the resolved state is explicitly `POWER`/`MOTORSAILER`/`CONFLICT` (`_NAUTIX_EXCLUDED_VESSEL_CATEGORIES`); `None`/`SAIL`/`UNKNOWN` all preserve the pre-0093 default-SAIL NautiX assumption unchanged. Proven with real PostgreSQL 18 (`tests/persistence/test_inventory_export_category_slice_0093.py`, 6 tests): a design-only-POWER BoatDesign with no publisher category claim at all now fails closed (the exact gap the review named — the pre-amendment guard, reading only the publisher's own claim, would have let this row through as a default `sail-yacht`); a publisher-SAIL-vs-design-POWER disagreement resolves to `CONFLICT` and also fails closed; ordinary agreeing SAIL and legacy no-category-evidence listings keep exporting unchanged; the other six accepted formats are never affected.

## 5. Measured adversarial and performance evidence (review amendment Finding D, resolved)

- **Cross-Organization conflicting current drive** (`test_cross_organization_conflicting_current_drive_fails_closed`): two Organizations both assert current `POWER` category for the same PhysicalBoat but disagree on the drive (SHAFT vs POD) — neither token is confirmed or excluded; both fail closed to `INSUFFICIENT_DATA`.
- **True two-connection concurrent revision** (`test_two_connection_concurrent_revision_never_sees_hybrid_state`): a writer connection holds an uncommitted new revision (category SAIL + drive POD) open while a separate reader connection evaluates Search — the reader sees only the old, fully-committed revision (POWER + SHAFT matches), never a torn hybrid; after commit the new revision is visible atomically.
- **Representative real PostgreSQL 18 measurements** (`tests/persistence/test_power_inventory_query_performance_slice_0093.py`), total SQL statements / elapsed / statements-per-candidate:

  | Plane | Population | Total SQL statements | Elapsed | Per-candidate |
  |---|---|---|---|---|
  | Claim-only (design-unresolved) | 0 | 2 | 0.002s | — |
  | Claim-only | 40 | 169 | 0.064s | 4.22 |
  | Claim-only | 200 | 809 | 0.405s | 4.04 |
  | Design-linked | 0 | 2 | 0.007s | — |
  | Design-linked | 10 | 98 | 0.072s | 9.80 |

  The claim-only plane reuses SLICE-0092's batched D29/claim-observation reads verbatim and stays bounded independent of population size (proven by a call-count spy, not only the numbers above). The design-linked plane is explicitly **not** batched — `resolve_physical_boat_vessel_category` + `classify_concrete_candidate` run once per design-level-`CONFIRMED_MATCH` candidate, identical cost shape to the already-accepted SLICE-0091 Sail design-linked funnel (not a new regression). A full 0/40/200 design-linked population was not attempted (each candidate requires a real admitted BoatDesign FieldResolution, making 200 such candidates prohibitively slow to seed for this bounded internal synthetic proof); the smaller 0/10 measurement is reported honestly instead of a fabricated extrapolation. Issue #355's pre-real-data/pilot production-scale STOP remains explicitly **OPEN** regardless of either measurement.

## 6. Explicit limitations (never silently claimed complete)

- `STERNDRIVE`/`POD`/`WATERJET` have **no design-linked bridge** in this slice: a design-linked PhysicalBoat can never reach `CONFIRMED_MATCH` for those three tokens, only `INSUFFICIENT_DATA` at the design level; they are reachable only through the design-unresolved claim-only path. This is a genuine, deliberate coverage gap (contract: "No v0.7 BoatDesign schema/migration is granted by this criterion"), not an oversight.
- Only one Power criterion exists; engine count/make/model, horsepower, fuel/energy source, speed/range/operating-point, and Power Broker Search-fit remain out of scope (tracked under #372).
- The design-linked plane's per-candidate (O(N)) cost is measured and documented (§5) but not newly optimized in this amendment; the pre-real-data/pilot scaling STOP (#355) is unchanged and still open.
- No real brokers, owner-direct trust, public pilot, or SEO/indexable exposure is introduced; both the API route and the five Astro pages are noindex.
- The retained inspector (`scripts/inspect_slice_0093_power_drive_search.py`) uses `urllib` plus a standards-compliant cookie jar for real HTTP/form-POST evidence against a real local OIDC test issuer, FastAPI backend and built Astro/Node SSR server — this is HTTP-level automation, explicitly not a genuine browser (no JS execution, no DOM rendering, no Playwright/Selenium-style page automation).
