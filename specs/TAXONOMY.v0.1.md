# HullQ Taxonomy v0.1

**Status: DRAFT — starting taxonomy to be refined against real source data.**

Keep these dimensions independent. Never compress hull, keel, rudder and skeg into one legacy source string.

## Hull configuration

- `monohull`
- `catamaran`
- `trimaran`
- `other`
- `unknown`

Potential multihull-specific fields include `hull_count`, `beam_overall`, `bridgedeck_clearance`, `rudder_count`, `daggerboard_count` and `centerboard_count`.

## Keel type

- `full`
- `modified_full`
- `long_fin`
- `fin`
- `wing`
- `bulb`
- `twin`
- `bilge`
- `centerboard`
- `daggerboard`
- `swing`
- `lifting`
- `shoal`
- `other`
- `unknown`

Use `keel_subtype` to preserve additional normalized detail where justified. Preserve raw source wording in evidence.

## Rudder type

- `keel_hung`
- `skeg_hung`
- `partial_skeg`
- `spade`
- `transom_hung`
- `twin`
- `other`
- `unknown`

## Skeg type

- `full`
- `partial`
- `none`
- `unknown`

## Rig type

- `masthead_sloop`
- `fractional_sloop`
- `cutter`
- `ketch`
- `yawl`
- `schooner`
- `cat_rig`
- `other`
- `unknown`

Raw source wording should remain available via evidence/provenance.

## Hull material

- `grp_fiberglass`
- `aluminium`
- `steel`
- `wood`
- `wood_composite`
- `carbon`
- `other`
- `unknown`

`construction_method` remains free-form/nullable for now. Do not over-normalize before real source data has been evaluated.

## Taxonomy mapping rule

A source phrase may map to multiple independent canonical fields. Example:

```text
source: "Fin with rudder on skeg"
→ keel_type: fin
→ rudder_type: skeg_hung
→ skeg_type: full OR partial only if evidence supports which
```

If the source does not distinguish full versus partial skeg, use `unknown` and flag for review rather than guessing.
