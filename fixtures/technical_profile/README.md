# Technical Profile Fixtures (SLICE-0034)

Synthetic `BOAT_DESIGN_SCHEMA.v0.6.json` instances. None represent real-world boat
facts; no real BoatDesign is admitted or promoted by these fixtures.

`valid/` holds the four required structural archetypes:

- `01_classic_aft_cockpit_masthead_sloop.json` — full keel, masthead sloop, and a
  transom-positioned rudder that independently carries skeg-support semantics
  (`appendages.rudder_position = "transom"`, `appendages.rudder_support = "skeg"`).
- `02_center_cockpit_cruiser.json` — demonstrates `deck.cockpit_position = "center"`
  as independently filterable data.
- `03_modern_production_cruiser_shallow_draft_twin_helm_options.json` — a standard
  baseline plus two independent `design_options` (axis `draft`, axis `helm`)
  showing standard-vs-shallow-draft and single-vs-twin-helm without averaging.
- `04_standard_vs_performance_rig_keel_variant.json` — a standard baseline plus a
  `named_variants` entry overriding rig dimensions and keel type, demonstrating the
  NamedVariant override mechanism (as distinct from DesignOption, used in `03`).

Invalid-shape fail-closed cases (unknown extra properties, malformed enums, negative
counts, incomplete override family sets) are constructed by mutating these valid
fixtures in `tests/contract/test_boat_design_v06_contract.py` rather than as
standalone files, to avoid fixture sprawl.
