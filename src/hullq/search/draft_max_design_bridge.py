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
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any, Final

from hullq.domain.provenance import ResolutionState, SubjectKind
from hullq.persistence.field_resolution import (
    decode_canonical_decimal_snapshot,
    fetch_current_field_resolution,
)
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import run_configuration_query
from hullq.search.criteria import NumericLeafCriterion
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import NumericComparisonKind, ValueQualification
from hullq.search.values import QualifiedNumericValue

__all__ = [
    "DRAFT_MAX_FIELD_POINTER",
    "DRAFT_MAX_PROJECTION_FIELD",
    "build_boat_design_draft_configuration_set",
    "compatible_boat_design_ids",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the single `NumericLeafCriterion` it evaluates against.
DRAFT_MAX_PROJECTION_FIELD: Final = "draft_max_m"

#: The exact two bounded field meanings SLICE-0051 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
DRAFT_MAX_FIELD_POINTER: Final = "/baseline/dimensions/draft_max_m"
DRAFT_MAX_OVERRIDE_FIELD_POINTER: Final = "/overrides/dimensions/draft_max_m"

_RESOLVED_STATES: Final = frozenset(
    {ResolutionState.RESOLVED, ResolutionState.RESOLVED_WITH_CONFLICT}
)
_MISSING = QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING)


def _qualify_via_field_resolution(
    conn: Any,
    *,
    subject_kind: SubjectKind,
    subject_id: str,
    field_pointer: str,
    raw_canonical_value: Any,
) -> QualifiedNumericValue:
    """Qualify one raw canonical numeric value against its active FieldResolution.

    Fails closed to `MISSING` for every case except an active
    `resolved`/`resolved_with_conflict` resolution whose exact Decimal
    snapshot agrees with *raw_canonical_value* -- never treats mere JSONB
    presence as confirmation (Finding 3 / blocker-resolution §4/§6).
    """
    if raw_canonical_value is None:
        return _MISSING

    record = fetch_current_field_resolution(conn, subject_kind, subject_id, field_pointer)
    if record is None or record.state not in _RESOLVED_STATES:
        return _MISSING

    try:
        snapshot_value = decode_canonical_decimal_snapshot(record.canonical_value_snapshot)
    except ValueError:
        # A resolution whose snapshot cannot even be decoded as the exact
        # Decimal representation this bounded field requires is not usable
        # here -- fail closed rather than guess at its meaning.
        return _MISSING

    canonical_value = Decimal(str(raw_canonical_value))
    if snapshot_value != canonical_value:
        # Canonical-value <-> active-resolution snapshot mismatch
        # (PROVENANCE_MODEL.v0.1.md §6): the resolution has gone stale
        # relative to the canonical record it is supposed to qualify.
        return _MISSING

    return QualifiedNumericValue(value=snapshot_value, qualification=ValueQualification.CONFIRMED)


def build_boat_design_draft_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `draft_max_m` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. One
    `ResolvedConfiguration` is emitted for the unmodified baseline plus one
    per `named_variants[]` entry that this bounded adapter can validly
    resolve on its own -- never a `design_options` combination (Finding 4:
    a variant with a non-empty `requires_option_ids` is excluded entirely).
    """
    design_id = boat_design["id"]
    baseline_dimensions = ((boat_design.get("baseline") or {}).get("dimensions")) or {}
    baseline_raw_value = baseline_dimensions.get("draft_max_m")

    baseline_qualified = _qualify_via_field_resolution(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        raw_canonical_value=baseline_raw_value,
    )

    configurations = [
        ResolvedConfiguration(
            identity=ConfigurationIdentity(
                configuration_id=f"{design_id}::baseline",
                boat_design_id=design_id,
            ),
            projection=ConfigurationProjection(
                numeric_values={DRAFT_MAX_PROJECTION_FIELD: baseline_qualified}
            ),
        )
    ]

    for variant in boat_design.get("named_variants") or []:
        if variant.get("requires_option_ids"):
            # Unresolved DesignOption dependency this adapter cannot
            # establish (Finding 4) -- exclude the variant entirely rather
            # than represent an unresolved dependency as an ordinary
            # resolved configuration.
            continue
        variant_id = variant["id"]
        override_dimensions = ((variant.get("overrides") or {}).get("dimensions")) or {}

        if "draft_max_m" not in override_dimensions:
            # No own override at all: inherit the already-qualified
            # baseline qualification -- never a fabricated direct
            # FieldResolution merely to represent inheritance (blocker
            # resolution §4).
            variant_qualified = baseline_qualified
        else:
            override_raw_value = override_dimensions["draft_max_m"]
            if override_raw_value is None:
                # An explicit null override is a deliberate "not the
                # baseline's value" signal, distinct from silence -- clears
                # to MISSING regardless of the baseline's own qualification.
                variant_qualified = _MISSING
            else:
                variant_qualified = _qualify_via_field_resolution(
                    conn,
                    subject_kind=SubjectKind.NAMED_VARIANT,
                    subject_id=variant_id,
                    field_pointer=DRAFT_MAX_OVERRIDE_FIELD_POINTER,
                    raw_canonical_value=override_raw_value,
                )

        configurations.append(
            ResolvedConfiguration(
                identity=ConfigurationIdentity(
                    configuration_id=f"{design_id}::{variant_id}",
                    boat_design_id=design_id,
                    named_variant_id=variant_id,
                ),
                projection=ConfigurationProjection(
                    numeric_values={DRAFT_MAX_PROJECTION_FIELD: variant_qualified}
                ),
            )
        )

    return DesignConfigurationSet(
        design_id=design_id,
        configurations=tuple(configurations),
        configuration_space_complete=False,
        is_fixture=False,
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

    boat_designs = tuple(boat_designs)
    if not boat_designs:
        return frozenset()

    configuration_sets = tuple(
        build_boat_design_draft_configuration_set(conn, bd) for bd in boat_designs
    )
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field=DRAFT_MAX_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=draft_max,
            ),
        )
    )
    outcome = run_configuration_query(query, configuration_sets)
    return frozenset(evaluation.design_id for evaluation in outcome.confirmed_matches)
