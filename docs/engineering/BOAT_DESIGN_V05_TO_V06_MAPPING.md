# BoatDesign v0.5 → v0.6 Technical-Shape Mapping

**Status:** informational, non-normative compatibility note for SLICE-0034.
**Normative contract:** `specs/BOAT_DESIGN_SCHEMA.v0.6.json`.

This is **not** a production data migration. `BOAT_DESIGN_SCHEMA.v0.5.json` is
unchanged and remains valid for existing v0.5 payloads. v0.6 is a new,
independently-registered contract for new BoatDesign payloads. No canonical
BoatDesign record is rewritten, converted or promoted by this note or by
SLICE-0034.

## 1. Unchanged verbatim

`schema_version` id/const aside, the following top-level structures are byte-for-byte
identical in shape between v0.5 and v0.6 — no identity, generation or relationship
rule is redefined:

- `id`, `boat_model_id`
- `generation` (label/sequence/aliases/first_built/last_built/hull_number_from/
  hull_number_to/boundary_confidence)
- `relationships` (builders via `organization_id`+`role`, designers, `number_built`)
- `quality` (status/confidence/notes)
- `baseline.ratio_input_basis` (same `$ref` to `RATIO_INPUT_BASIS_SCHEMA.v0.1`,
  same `displacement_basis`/`sail_area_basis` field paths relied on by
  `DERIVED_METRICS_SPEC.v1.0.md`)
- `baseline.construction` (`hull_material`, `construction_method`)
- `baseline.configuration.hull_configuration`, `baseline.configuration.hull_count`
- `named_variants[]` / `design_options[]` wrapper fields: `id`, `name`, `aliases`,
  `applicability`, `requires_option_ids`, `excludes_option_ids`

## 2. Straight moves (same semantics, new location)

| v0.5 path | v0.6 path | Notes |
|---|---|---|
| `baseline.dimensions.loa_m` | `baseline.dimensions.loa_m` | unchanged |
| `baseline.dimensions.lwl_m` | `baseline.dimensions.lwl_m` | unchanged |
| `baseline.dimensions.beam_m` | `baseline.dimensions.beam_m` | unchanged |
| `baseline.dimensions.draft_min_m` / `draft_max_m` | same | unchanged |
| `baseline.dimensions.displacement_kg` | same | unchanged |
| `baseline.dimensions.ballast_kg` | same | unchanged |
| `baseline.dimensions.sail_area_m2` | same | unchanged; richer reported/component/calculated breakdown is additionally available at `baseline.rig.sail_area_*` |
| `baseline.configuration.keel_type` | `baseline.appendages.keel_type` | same enum, moved into the new appendages family |
| `baseline.configuration.keel_subtype` | `baseline.appendages.keel_subtype` | moved |
| `baseline.configuration.rudder_count` | `baseline.appendages.rudder_count` | moved |
| `baseline.configuration.skeg_type` | `baseline.appendages.skeg_type` | same enum, moved |
| `baseline.configuration.daggerboard_count` | `baseline.appendages.daggerboard_count` | moved |
| `baseline.configuration.centerboard_count` | `baseline.appendages.centerboard_count` | moved |
| `baseline.cruising.engine_make/engine_model/engine_type/engine_power_hp` | `baseline.propulsion.*` | moved |
| `baseline.cruising.fuel_capacity_l` / `water_capacity_l` | `baseline.propulsion.*` | moved |
| `baseline.cruising.headroom_m` | `baseline.accommodation.headroom_m` | moved |
| `baseline.cruising.bridgedeck_clearance_m` | `baseline.accommodation.bridgedeck_clearance_m` | moved |

`baseline.cruising` itself does not exist in v0.6; it splits into `propulsion`
(engine/drive/fuel/water) and `accommodation` (headroom/bridgedeck/cabin/berth/head),
matching `TECHNICAL_PROFILE_SPEC.v0.1.md` §4.6/§4.7. Every v0.5 `cruising` fact
remains representable in v0.6, just regrouped.

## 3. Decomposed fields (the primary evolution)

### 3.1 `rig_type` → `rig.sailplan` + `rig.masthead_fractional`

v0.5's single `configuration.rig_type` enum conflated sailplan and masthead/
fractional character. Deterministic decomposition used when mapping historical
v0.5-shaped data by hand:

| v0.5 `rig_type` | v0.6 `rig.sailplan` | v0.6 `rig.masthead_fractional` |
|---|---|---|
| `masthead_sloop` | `sloop` | `masthead` |
| `fractional_sloop` | `sloop` | `fractional` |
| `cutter` | `cutter` | `unknown` (v0.5 did not distinguish; `unknown` is honest, not `not_applicable`) |
| `ketch` | `ketch` | `not_applicable` |
| `yawl` | `yawl` | `not_applicable` |
| `schooner` | `schooner` | `not_applicable` |
| `cat_rig` | `cat` | `not_applicable` |
| `other` | `other` | `unknown` |
| `unknown` | `unknown` | `unknown` |

### 3.2 `rudder_type` → `rudder_position` + `rudder_support` + `rudder_balance`

v0.5's single `configuration.rudder_type` enum conflated where the rudder is
mounted, what structurally supports it, and its balance style — the exact
compression `TECHNICAL_PROFILE_SPEC.v0.1.md` §4.3 identifies as unacceptable
("A compound label such as `long keel with transom-hung rudder` MUST NOT force
HullQ to collapse independent keel/rudder/support facts into one opaque string").

| v0.5 `rudder_type` | `rudder_position` | `rudder_support` | `rudder_balance` |
|---|---|---|---|
| `keel_hung` | `underhull` | `keel` | `unbalanced` |
| `skeg_hung` | `underhull` | `skeg` | `unbalanced` |
| `partial_skeg` | `underhull` | `skeg` | `semi_balanced` |
| `spade` | `underhull` | `free` | `balanced` |
| `transom_hung` | `transom` | `transom` | `unbalanced` |
| `twin` | `underhull` | `free` | `unknown` (twin-ness is carried by `rudder_count = 2`, not by position/support) |
| `other` | `other` | `other` | `other` |
| `unknown` | `unknown` | `unknown` | `unknown` |

Because `rudder_position` and `rudder_support` are independent fields, v0.6 can
represent combinations v0.5 could not, e.g. a transom-positioned rudder that is
also skeg-supported (`rudder_position: "transom"`, `rudder_support: "skeg"`) — see
`fixtures/technical_profile/valid/01_classic_aft_cockpit_masthead_sloop.json` and
`tests/contract/test_boat_design_v06_contract.py::test_transom_rudder_can_carry_keel_or_skeg_support_without_contradiction`.

## 4. New in v0.6 (no v0.5 predecessor)

- `baseline.dimensions`: `lod_m`, `beam_waterline_m`, `ballast_type`, `ballast_material`
  (both free-text, not a closed vocabulary — `TECHNICAL_PROFILE_SPEC.v0.1.md` does
  not enumerate ballast type/material values, and no predecessor vocabulary exists
  to bound one; a closed enum would be an unbounded taxonomy decision this slice
  does not make)
- `baseline.appendages`: `centerboard_type`, `daggerboard_type` (free-text, same
  reasoning), `rudder_position`, `rudder_support`, `rudder_balance`
- `baseline.rig` (new family): `sailplan`, `masthead_fractional`, `mast_count`,
  `mast_step`, `rig_variant`, `mast_height_m`, `mast_height_basis`, `i_m`, `j_m`,
  `p_m`, `e_m`, `py_m`, `ey_m`, `isp_m`, `jp_m`, `spl_or_tps_m`,
  `forestay_length_m`, `forestay_length_basis`, `sail_area_reported_m2`,
  `sail_area_main_m2`, `sail_area_foretriangle_m2`, `sail_area_calculated_m2`,
  `sail_area_calculated_notes`
- `baseline.deck` (new family): `cockpit_position`, `cockpit_count`, `helm_type`,
  `helm_count`, `deck_saloon`
- `baseline.propulsion`: `engine_count`, `drive_type`, `propeller_configuration`
  (alongside the moved v0.5 `cruising` engine/fuel/water fields)
- `baseline.accommodation`: `cabin_count`, `berth_count`, `head_count` (alongside
  the moved v0.5 `cruising.headroom_m`/`bridgedeck_clearance_m`)
- `baseline.compliance` (new family): `ce_design_category` (free-text, not a
  closed enum — no controlling artifact enumerates CE/RCD category letters for
  this slice to bind to)
- `design_options[].axis` enum gains `cockpit`, `helm`, `propulsion`,
  `accommodation` alongside the unchanged v0.5 axis values

## 5. Override symmetry

Every `baseline` family (`dimensions`, `ratio_input_basis`, `configuration`,
`appendages`, `rig`, `deck`, `construction`, `propulsion`, `accommodation`,
`compliance`) has a matching override-capable shape reused identically by both
`named_variants[].overrides` and `design_options[].overrides` (a single shared
`$defs/overrides` definition — see `test_every_baseline_family_is_override_capable_in_both_mechanisms`
in `tests/contract/test_boat_design_v06_contract.py`). No newly added
search-significant family is baseline-only.

## 6. Explicitly not changed by this note

- OQ-009 search truth/fail-closed semantics (`SEARCH_QUERY_SEMANTICS.v0.1.md`).
- `FIELD_RESOLUTION_SCHEMA` / `FIELD_EVIDENCE_SCHEMA` provenance boundary.
- `DERIVED_METRICS_SPEC.v1.0.md` methodology or its `ratio_input_basis` field paths.
- The canonical persistence importer/readback path (`src/hullq/persistence/
  identity_importer.py`, `identity_readback.py`), which still targets
  `BOAT_DESIGN_SCHEMA.v0.5.json`. Wiring v0.6 into persistence, the categorical
  search evaluator, or a real-world canonical corpus is out of scope for
  SLICE-0034 and is left for a later slice.
