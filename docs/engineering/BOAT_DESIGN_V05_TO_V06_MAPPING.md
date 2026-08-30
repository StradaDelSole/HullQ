# BoatDesign v0.5 → v0.6 Technical-Shape Mapping

**Status:** informational, non-normative compatibility note for SLICE-0034.
**Normative contract:** `specs/BOAT_DESIGN_SCHEMA.v0.6.json`.

**Amendment (post-review):** §3 was corrected after independent review found
the original `rig_type`/`rudder_type` decomposition tables asserted several
decomposed facts (e.g. `ketch → masthead_fractional: not_applicable`,
`spade → rudder_balance: balanced`, `twin → rudder_position: underhull`) that
the v0.5 token did not actually prove. §3 now states and mechanically enforces
a strict "only what the predecessor token logically guarantees" rule; see §3.3.

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

**Governing rule for this section (amended after independent review):** a
mapping row may only assert a concrete v0.6 value when that value is *logically
guaranteed* by the v0.5 token itself — either because the v0.6 word is literally
the v0.5 token's own word (e.g. `masthead_sloop` contains "masthead"), or
because the v0.6 concept is part of the plain dictionary definition of the v0.5
term (e.g. a "spade" rudder is by definition free-standing/unsupported). Where
a decomposed v0.6 dimension was simply never recorded by any v0.5 token —
including where it would be *typical* or *conventional* for that token — the
honest projection is `unknown`, not a plausible guess. This is a compatibility
note for translating existing v0.5-shaped data by hand, not a mechanical
production migration; §3.3 links the regression test that keeps this table and
the actual conservativity rule from silently drifting apart.

### 3.1 `rig_type` → `rig.sailplan` + `rig.masthead_fractional`

v0.5's single `configuration.rig_type` enum conflated sailplan and masthead/
fractional character.

| v0.5 `rig_type` | v0.6 `rig.sailplan` | v0.6 `rig.masthead_fractional` | Why |
|---|---|---|---|
| `masthead_sloop` | `sloop` | `masthead` | both words are literally present in the v0.5 token |
| `fractional_sloop` | `sloop` | `fractional` | both words are literally present in the v0.5 token |
| `cutter` | `cutter` | `unknown` | v0.5 never recorded masthead/fractional character for cutters; `not_applicable` would assert cutters can never be described that way, which is not true and not something the v0.5 token proves |
| `ketch` | `ketch` | `unknown` | v0.5 never recorded this dimension for ketches; **not** `not_applicable` (a prior draft of this table wrongly asserted `not_applicable` here — corrected after independent review, see §3.3) |
| `yawl` | `yawl` | `unknown` | same correction as `ketch` |
| `schooner` | `schooner` | `unknown` | same correction as `ketch` |
| `cat_rig` | `cat` | `unknown` | same correction as `ketch`; a cat rig's single-sail/no-forestay definition is a reasonable basis for `not_applicable`, but that basis lives outside `TECHNICAL_PROFILE_SPEC.v0.1.md`/the v0.5 token itself, so this note does not assert it |
| `other` | `other` | `unknown` | an opaque escape token proves nothing about the decomposed dimension |
| `unknown` | `unknown` | `unknown` | no information |

The `not_applicable` enum value remains legitimate for freshly-researched v0.6
data where a primary source genuinely establishes that the distinction does not
apply (e.g. a documented unstayed cat rig); it is simply never asserted by this
*mapping table*, because no v0.5 token proves it.

### 3.2 `rudder_type` → `rudder_position` + `rudder_support` + `rudder_balance`

v0.5's single `configuration.rudder_type` enum conflated where the rudder is
mounted, what structurally supports it, and its balance style — the exact
compression `TECHNICAL_PROFILE_SPEC.v0.1.md` §4.3 identifies as unacceptable
("A compound label such as `long keel with transom-hung rudder` MUST NOT force
HullQ to collapse independent keel/rudder/support facts into one opaque string").

`rudder_balance` was corrected after independent review: **no v0.5
`rudder_type` token encodes balance at all**, so every row now maps to
`unknown`. The previous draft of this table inferred `unbalanced` for
`keel_hung`/`skeg_hung`/`transom_hung`, `semi_balanced` for `partial_skeg` and
`balanced` for `spade` — those are common real-world correlations, not facts
the v0.5 token proves, and independent review correctly rejected them as
invented.

`rudder_position` is asserted only for `transom_hung`, where "transom" is the
v0.5 token's own word. It is **not** asserted as `underhull` for any other
token: although `keel_hung`/`skeg_hung`/`partial_skeg`/`spade` are typically
mounted away from the transom, v0.6 explicitly allows a transom-positioned
rudder to carry keel/skeg-support semantics (§ Required schema semantics B; see
`fixtures/technical_profile/valid/01_classic_aft_cockpit_masthead_sloop.json`),
which proves position and support are not interchangeable — so support-implies-
position is exactly the kind of inference this table must not make.

| v0.5 `rudder_type` | `rudder_position` | `rudder_support` | `rudder_balance` | Why |
|---|---|---|---|---|
| `keel_hung` | `unknown` | `keel` | `unknown` | "keel" is the v0.5 token's own word for what supports the rudder; position/balance are not recorded |
| `skeg_hung` | `unknown` | `skeg` | `unknown` | same reasoning, "skeg" |
| `partial_skeg` | `unknown` | `skeg` | `unknown` | "partial" qualifies the skeg's extent, not the rudder's position or balance; still skeg-supported |
| `spade` | `unknown` | `free` | `unknown` | a spade rudder is by definition a free-standing/unsupported blade; position/balance are not recorded |
| `transom_hung` | `transom` | `transom` | `unknown` | "transom" is the v0.5 token's own word for both position and support; balance is not recorded |
| `twin` | `unknown` | `unknown` | `unknown` | "twin" describes rudder count, not position/support/balance for either rudder — see the `rudder_count` note below |
| `other` | `unknown` | `unknown` | `unknown` | an opaque escape token proves nothing about any individual decomposed dimension (corrected — a prior draft wrongly cascaded `other` into every field) |
| `unknown` | `unknown` | `unknown` | `unknown` | no information |

**`rudder_count` and `twin` (corrected):** `baseline.appendages.rudder_count` is
a straight-moved field (§2), copied verbatim from v0.5 independently of
`rudder_type`. This mapping table does **not** synthesize `rudder_count = 2`
from `rudder_type = twin`. A valid v0.5 payload can have `rudder_type: "twin"`
and `rudder_count: null` (the count was simply never recorded even though the
type was); in that case the "there are two rudders" fact has no home in v0.6
beyond `rudder_count`, and this compatibility note leaves it as the source
recorded it — `null` — rather than inventing `2`. Asserting a count from a type
label would be exactly the kind of invented fact this section exists to
prevent. A production migration that wants to backfill `rudder_count` from
`rudder_type = twin` is a deliberate policy decision outside this note's scope,
not a mechanical consequence of the schema shapes.

Because `rudder_position` and `rudder_support` are independent fields, v0.6 can
represent combinations v0.5 could not, e.g. a transom-positioned rudder that is
also skeg-supported (`rudder_position: "transom"`, `rudder_support: "skeg"`) — see
`fixtures/technical_profile/valid/01_classic_aft_cockpit_masthead_sloop.json` and
`tests/contract/test_boat_design_v06_contract.py::test_transom_rudder_can_carry_keel_or_skeg_support_without_contradiction`.

### 3.3 Mechanical conservativity check

`tests/contract/test_boat_design_v05_to_v06_mapping_conservatism.py` transcribes
the two tables above as literal Python data and mechanically enforces the
governing rule, independently of the table's own content:

- `rig.masthead_fractional` is asserted as non-`unknown` for **only**
  `masthead_sloop`/`fractional_sloop`, for every other value of v0.5
  `configuration.rig_type` (the full enum is read directly from
  `specs/BOAT_DESIGN_SCHEMA.v0.5.json` itself, so the test cannot silently go
  stale if that enum ever changes);
- `appendages.rudder_balance` is asserted as `unknown` for **every** v0.5
  `rudder_type` value, with no exception;
- `appendages.rudder_position` is asserted as non-`unknown` for **only**
  `transom_hung`;
- the mapping's `rudder_count` handling is a straight passthrough, never a
  function of `rudder_type` (checked by asserting the mapping table has no
  `rudder_count` column/key at all).

This makes it structurally impossible for a future edit to silently reintroduce
an invented decomposed fact (e.g. re-adding `balanced` for `spade`) without an
explicit, reviewable change to the enforcement rule itself, not just the table.

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

## 6. Bounded cross-field invariants (amendment)

v0.6 additionally enforces a small set of `allOf`/`if`/`then` cross-field
invariants, using the same pattern already established by
`FIELD_RESOLUTION_SCHEMA.v0.1/v0.2` (`const`/`enum`-conditioned `if`/`then`, no
`$data`, no custom keywords). Each is a definitional or mathematical certainty,
not a domain-taxonomy judgment call, and each is scoped so it only fires when
every property it depends on is actually present with a concrete (non-null)
value — so a partial `NamedVariant`/`DesignOption` override that does not touch
the relevant sibling fields is never forced to restate them:

- `baseline.configuration`: `hull_configuration` must agree with `hull_count`
  when both are concrete (`monohull`↔`1`, `catamaran`↔`2`, `trimaran`↔`3`);
  `other`/`unknown` configurations are unconstrained.
- `baseline.appendages`: `skeg_type = "none"` cannot coexist with
  `rudder_support = "skeg"`; `centerboard_count = 0` cannot coexist with a
  concrete (non-null) `centerboard_type`; `daggerboard_count = 0` cannot
  coexist with a concrete `daggerboard_type`; `rudder_count = 0` forces
  `rudder_position`/`rudder_support`/`rudder_balance` to all be `unknown`.
- `baseline.deck`: `cockpit_count = 0` forces `cockpit_position = "unknown"`;
  `helm_count = 0` forces `helm_type = "unknown"`.

All are covered by paired reject/accept/partial-override tests in
`tests/contract/test_boat_design_v06_contract.py`.

**Deliberately left unresolved:** `draft_min_m > draft_max_m` is a genuine
contradiction but cannot be expressed in standard JSON Schema without
comparing two sibling numeric properties — a capability the non-standard
`$data` proposal would provide but which this repo's `jsonschema` package does
not implement, and for which there is no existing precedent anywhere in this
repo's schemas (`FIELD_RESOLUTION_SCHEMA` and the invariants above are all
`const`/`enum`-conditioned, never a numeric A-vs-B comparison). Adding a custom
keyword or format-checker solely for this one field pair would introduce a new
validation mechanism disproportionate to a bounded schema-shape amendment, so
per the slice's own stop-condition guidance this is reported rather than
worked around. `tests/contract/test_boat_design_v06_contract.py::test_draft_min_exceeds_draft_max_is_a_known_unenforceable_gap`
documents this as a regression-visible, explained gap rather than a silent one.

## 7. Explicitly not changed by this note

- OQ-009 search truth/fail-closed semantics (`SEARCH_QUERY_SEMANTICS.v0.1.md`).
- `FIELD_RESOLUTION_SCHEMA` / `FIELD_EVIDENCE_SCHEMA` provenance boundary.
- `DERIVED_METRICS_SPEC.v1.0.md` methodology or its `ratio_input_basis` field paths.
- The canonical persistence importer/readback path (`src/hullq/persistence/
  identity_importer.py`, `identity_readback.py`), which still targets
  `BOAT_DESIGN_SCHEMA.v0.5.json`. Wiring v0.6 into persistence, the categorical
  search evaluator, or a real-world canonical corpus is out of scope for
  SLICE-0034 and is left for a later slice.
