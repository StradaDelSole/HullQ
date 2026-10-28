"""BoatDesign/configuration `power_engine_count` eligibility bridge — SLICE-0094.

The Power-domain criterion-#2 adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (canonical
subject lookup, FieldResolution qualification, baseline/NamedVariant
projection, design eligibility) — see that module's docstring for the
mandatory second-criterion abstraction rationale this bridge reuses
unchanged (identical to `hullq.search.power_drive_design_bridge`'s own
reuse for criterion #1). This module owns only what is genuinely
`power_engine_count`-specific: the two bounded BoatDesign field pointers it
qualifies.

    BoatDesign      /baseline/propulsion/engine_count
    NamedVariant    /overrides/propulsion/engine_count

Design-side source is BoatDesign v0.6 `propulsion.engine_count`
(`specs/BOAT_DESIGN_SCHEMA.v0.6.json` `$defs.propulsion_shape.engine_count`:
integer or null, minimum 0). Unlike `power_drive_design_bridge`'s taxonomy
mapping, `engine_count` needs no `taxonomy_map` -- it is an exact `Decimal`
comparison, never a categorical remap. A raw `engine_count` of `null` or an
unresolved/stale FieldResolution already fails closed to `MISSING` via the
shared `qualify_canonical_field` mechanism (never guessed).

Independent review amendment Finding E: `0` is schema-*valid* (v0.6 permits
`minimum: 0`) but is never a plausible factory fact this criterion treats
as confirmed truth -- "zero principal propulsion engines" is not a genuine
installed-engine-count assertion, and letting an ordinary `CONFIRMED`
numeric qualification carry it through would manufacture a *confirmed*
non-match (`0 != requested token`) for every one of the eight public
tokens, which looks identical to a genuine, trustworthy factory
disagreement even though `0` was never a real fact in the first place. This
module's own `decode_engine_count_for_qualification` therefore rejects `0`
(raising `ValueError`, which `qualify_canonical_field`'s existing
`except ValueError: return (MISSING, None)` path already turns into a
`MISSING` qualification -- the identical fail-closed mechanism every other
decode failure already uses here, not a new branch) -- `0` becomes
`INSUFFICIENT_DATA`, never a misleading confirmed exclusion. Deliberately
bounded to only this one unsupported value: a factory count above the
public 1-8 Search whitelist (e.g. `12`) is still a real installed-engine
fact this criterion can confirm and correctly non-match against any
requested token -- this fix never touches that case, and never weakens the
shared generic `decode_decimal_for_qualification` every other numeric
criterion (draft_max, loa, beam) still uses unmodified.

A qualifying factory `engine_count` is never, by itself, a current
*installed* count -- a separately qualified current `PhysicalBoatClaims
.power_engine_count` claim is always required too
(`hullq.application.power_inventory_query`'s own concrete-claim
classification, reused unchanged from the Sail/0093 kernel). This module
answers only "what does BoatDesign/NamedVariant qualify", never "what is
currently installed".

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, any other
propulsion attribute, or any mapping beyond this one exact field.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Final

from hullq.domain.provenance import SubjectKind
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    decode_decimal_for_qualification,
    make_bounded_canonical_value_lookup,
)
from hullq.search.configuration import DesignConfigurationSet

__all__ = [
    "POWER_ENGINE_COUNT_FIELD_PROJECTION_SPEC",
    "POWER_ENGINE_COUNT_PROJECTION_FIELD",
    "PROPULSION_ENGINE_COUNT_FIELD_POINTER",
    "PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER",
    "build_boat_design_power_engine_count_configuration_set",
    "decode_engine_count_for_qualification",
    "lookup_power_engine_count_canonical_value",
]


def decode_engine_count_for_qualification(value: object) -> Decimal:
    """Decode a raw canonical `engine_count` value or FieldResolution
    snapshot as an exact, strictly positive `Decimal` -- SLICE-0094
    independent-review amendment Finding E.

    Reuses the identical shared `decode_decimal_for_qualification` every
    other numeric criterion already uses for the actual Decimal parsing,
    then rejects the one BOAT_DESIGN_SCHEMA.v0.6-valid-but-criterion-
    unsupported value, `0` -- see this module's docstring. Raising
    `ValueError` here (rather than silently clamping or passing it
    through) feeds `qualify_canonical_field`'s own existing
    `except ValueError: return (ValueQualification.MISSING, None)` path,
    so this is not a new fail-closed mechanism, only a narrower input
    boundary for the one already-shared one.
    """
    decoded = decode_decimal_for_qualification(value)
    if decoded <= 0:
        raise ValueError(f"engine_count {decoded!r} is not a supported factory value (must be > 0)")
    return decoded


#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the `NumericLeafCriterion` it is evaluated against.
POWER_ENGINE_COUNT_PROJECTION_FIELD: Final = "power_engine_count"

#: The exact two bounded field meanings SLICE-0094 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
PROPULSION_ENGINE_COUNT_FIELD_POINTER: Final = "/baseline/propulsion/engine_count"
PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER: Final = "/overrides/propulsion/engine_count"

#: This criterion's shared-bridge field-projection contract.
POWER_ENGINE_COUNT_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=POWER_ENGINE_COUNT_PROJECTION_FIELD,
    section_key="propulsion",
    field_key="engine_count",
    baseline_pointer=PROPULSION_ENGINE_COUNT_FIELD_POINTER,
    override_pointer=PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER,
    decode=decode_engine_count_for_qualification,
    is_numeric=True,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0094's `power_engine_count` criterion, hard-
#: bounded to exactly the two field meanings this module's docstring
#: authorizes -- see `hullq.search.boat_design_field_bridge
#: .make_bounded_canonical_value_lookup`.
lookup_power_engine_count_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({PROPULSION_ENGINE_COUNT_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_power_engine_count_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `power_engine_count`
    for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge
    .build_boat_design_configuration_set` -- see that function's docstring
    for the baseline/NamedVariant projection rules.
    """
    return build_boat_design_configuration_set(
        conn, boat_design, (POWER_ENGINE_COUNT_FIELD_PROJECTION_SPEC,)
    )
