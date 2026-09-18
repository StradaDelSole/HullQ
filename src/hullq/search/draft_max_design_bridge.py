"""BoatDesign/configuration `draft_max` eligibility bridge — SLICE-0051 (+ FieldResolution amendment).

The smallest bounded adapter from a persisted canonical BoatDesign record
(BOAT_DESIGN_SCHEMA.v0.5/v0.6-shaped, as returned by
`hullq.persistence.identity_readback.fetch_boat_design`) to the existing,
unchanged `hullq.search.configuration` / `hullq.search.configuration_engine`
kernel, projecting exactly one numeric field: the design/configuration's own
`baseline.dimensions.draft_max_m` (optionally overridden per
`named_variants[].overrides.dimensions.draft_max_m`).

This module answers only "which designs/configurations could satisfy
`draft <= draft_max`" (slice Required Behavior §D: "design/configuration
evaluation alone never confirms a concrete listed yacht"). It never expands
`design_options` combinations (SLICE-0035's configuration boundary
deliberately does not invent option-combination expansion) and never claims
`configuration_space_complete=True`.

## FieldResolution-aware qualification (post-blocker-resolution)

Per `docs/SLICE_0051_FIELD_RESOLUTION_BLOCKER_RECONCILIATION_2026-09-12.md`,
a raw value merely present in `canonical_boat_designs` JSONB is schema
validity, not accepted/current resolution
(`specs/SEARCH_QUERY_SEMANTICS.v0.1.md` §3; `specs/PROVENANCE_MODEL.v0.1.md`
§6). Qualification for exactly the two SLICE-0051 field meanings --

    BoatDesign      /baseline/dimensions/draft_max_m
    NamedVariant    /overrides/dimensions/draft_max_m

-- now consults `hullq.persistence.field_resolution.fetch_current_field_resolution`
and requires all of:

    an active resolution exists for that exact (subject_kind, subject_id, field_pointer)
    AND its state is `resolved` or `resolved_with_conflict`
    AND its exact Decimal snapshot equals the current raw canonical JSON value

before the raw value may become `ValueQualification.CONFIRMED`. An absent
resolution, an `unknown`/`needs_review`/`conflict` state, or a
snapshot/canonical-value mismatch (the resolution has gone stale relative to
the canonical record it qualifies) all fail closed to `MISSING` -- never a
fabricated confirmed/non-match. Source-rights/evidence admission for a
`resolved`/`resolved_with_conflict` resolution is enforced once, at
`hullq.persistence.field_resolution.write_field_resolution` time, not
re-verified per read.

## Canonical-value consistency is now also enforced at admission (Finding 7)

`lookup_draft_max_canonical_value` is this slice's one accepted
`FetchCanonicalValue` implementation, passed to every SLICE-0051
`write_field_resolution` call so that a resolution disagreeing with the
durable canonical record it qualifies is rejected at write time, not merely
caught defensively when Search later reads it. The shared
`hullq.search.boat_design_field_bridge.qualify_canonical_field` this module's
own `build_boat_design_draft_configuration_set` delegates to performs its own
independent read-time comparison regardless -- this is deliberate
defense-in-depth, not redundant: it protects Search consumption even against
a future write path that forgets to pass a `fetch_canonical_value` callback,
or a resolution admitted before this bridge's canonical record was updated.

A NamedVariant with no own `draft_max_m` override key inherits the
already-qualified BoatDesign baseline qualification at this
configuration-evaluation step, per the blocker resolution: "Do not fabricate
another direct FieldResolution merely to represent inheritance." An explicit
`null` override clears to `MISSING` regardless of the baseline (an
authored, deliberate "this variant's draft is not the baseline's" signal,
distinct from silence).

A `named_variants[]` entry whose own `requires_option_ids` is non-empty
remains excluded from the resolved configuration set entirely (amendment
review Finding 4): this adapter never applies any `DesignOption`, so such a
dependency can never be validly established.

## SLICE-0055 criterion #2 abstraction

Per the accepted second-criterion bridge comparison, every production
responsibility above that is not specific to `draft_max`'s own field
pointers/decoding now lives in `hullq.search.boat_design_field_bridge` and is
shared with `hullq.search.keel_design_bridge`'s `keel_configuration`
criterion: canonical subject lookup, FieldResolution qualification, and
baseline/NamedVariant projection. This module keeps only what is genuinely
`draft_max`-specific: its two field pointers, its exact-Decimal
`FetchCanonicalValue` bounding, and the public
`build_boat_design_draft_configuration_set`/`compatible_boat_design_ids`
names and behavior SLICE-0051's retained tests depend on -- both are now
thin adapters over the shared bridge, not a second parallel lifecycle.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any, Final

from hullq.domain.provenance import SubjectKind
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    compatible_boat_design_ids_for_query,
    decode_decimal_for_qualification,
    make_bounded_canonical_value_lookup,
)
from hullq.search.configuration import DesignConfigurationSet
from hullq.search.criteria import NumericLeafCriterion
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import NumericComparisonKind

__all__ = [
    "DRAFT_MAX_FIELD_POINTER",
    "DRAFT_MAX_FIELD_PROJECTION_SPEC",
    "DRAFT_MAX_OVERRIDE_FIELD_POINTER",
    "DRAFT_MAX_PROJECTION_FIELD",
    "build_boat_design_draft_configuration_set",
    "compatible_boat_design_ids",
    "lookup_draft_max_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the single `NumericLeafCriterion` it evaluates against.
DRAFT_MAX_PROJECTION_FIELD: Final = "draft_max_m"

#: The exact two bounded field meanings SLICE-0051 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
DRAFT_MAX_FIELD_POINTER: Final = "/baseline/dimensions/draft_max_m"
DRAFT_MAX_OVERRIDE_FIELD_POINTER: Final = "/overrides/dimensions/draft_max_m"

#: This criterion's shared-bridge field-projection contract (SLICE-0055
#: §6) -- the one piece of draft_max-specific knowledge the shared
#: `hullq.search.boat_design_field_bridge` needs. Exported so the SLICE-0055
#: mixed native-inventory application funnel can combine it with
#: `hullq.search.keel_design_bridge`'s own spec in one query without
#: reaching into this module's private internals.
DRAFT_MAX_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=DRAFT_MAX_PROJECTION_FIELD,
    section_key="dimensions",
    field_key="draft_max_m",
    baseline_pointer=DRAFT_MAX_FIELD_POINTER,
    override_pointer=DRAFT_MAX_OVERRIDE_FIELD_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0051 (amendment review Finding 7), hard-bounded to
#: exactly the two field meanings this module's docstring authorizes -- see
#: `hullq.search.boat_design_field_bridge.make_bounded_canonical_value_lookup`.
lookup_draft_max_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({DRAFT_MAX_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({DRAFT_MAX_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_draft_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `draft_max_m` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge.
    build_boat_design_configuration_set` -- see that function's docstring
    for the baseline/NamedVariant projection rules (Finding 4 required-option
    exclusion, inheritance, explicit-null-clears-to-MISSING).
    """
    return build_boat_design_configuration_set(
        conn, boat_design, (DRAFT_MAX_FIELD_PROJECTION_SPEC,)
    )


def compatible_boat_design_ids(
    conn: Any, draft_max: Decimal, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for `draft_max`.

    *draft_max* is the caller's already-parsed exact positive finite
    `Decimal` public requirement -- never converted to `float` here
    (amendment review Finding 2). `NumericLeafCriterion` and
    `QualifiedNumericValue` both preserve a `Decimal` operand exactly rather
    than coercing it to `float`, so this comparison stays exact end to end,
    from the durable `FieldResolution` snapshot through this criterion
    evaluation.

    A `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA` design-level result is
    simply not included -- neither ever admits a design's PhysicalBoats to
    the concrete evaluation funnel.
    """
    if not isinstance(draft_max, Decimal):
        raise TypeError(f"draft_max must be a Decimal, got {type(draft_max).__name__}")

    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field=DRAFT_MAX_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=draft_max,
            ),
        )
    )
    return compatible_boat_design_ids_for_query(
        conn, query, boat_designs, (DRAFT_MAX_FIELD_PROJECTION_SPEC,)
    )
