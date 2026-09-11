"""BoatDesign/configuration `draft_max` eligibility bridge — SLICE-0051.

STATUS (post-amendment-review, Finding 3): **structurally present but
intentionally inert pending an accepted production qualification source.**
See "Why every design currently qualifies as MISSING" below before assuming
this module admits any design as design-level compatible in production.

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
`configuration_space_complete=True`: this bridge has not established that
every materially possible configuration is represented, only that the
baseline plus every declared, dependency-free NamedVariant is. That
conservative `False` only ever costs a design a `CONFIRMED_NON_MATCH`
classification it does not need here -- SLICE-0051 only ever consumes a
design-level `CONFIRMED_MATCH` result (see `compatible_boat_design_ids`), so
`CONFIRMED_NON_MATCH` vs `INSUFFICIENT_DATA` at the design level makes no
difference to the bounded vertical this slice ships.

## Why every design currently qualifies as MISSING (Finding 3)

`specs/SEARCH_QUERY_SEMANTICS.v0.1.md` §3 requires "a source-backed canonical
value with accepted/current resolution" before Search may treat it as
`CONFIRMED`. `specs/PROVENANCE_AND_QUALITY.md` states the same requirement
even more directly: "A source-backed canonical field MUST agree with its
current active FieldResolution snapshot or be null while unresolved."

`hullq.domain.provenance.FieldResolution` is the accepted per-field
resolution-state record this requires. As of this amendment, the repository
has **no durable persistence for `FieldResolution`** (no `field_resolutions`
table or equivalent exists in `src/hullq/persistence/sql/` or any accepted
Alembic revision) and `hullq.persistence.identity_importer` performs "no
identity resolution" (its own docstring) -- it writes whatever schema-valid
`baseline`/`named_variants` JSON it is given straight into
`canonical_boat_designs`, with no per-field resolution-state tracking
attached. The whole-record `quality.status`/`quality.confidence` pair is a
single design-wide self-reported descriptor, not a per-field resolution and
not wired to any accepted Search qualification adapter.

The only place a real `hullq.search.configuration.DesignConfigurationSet` has
ever been built for genuinely CONFIRMED Search truth is the SLICE-0037
pilot (`scripts/search_oceanis_30_1.py`), which sources a hand-curated,
individually-reviewed JSON artifact through a hardcoded, single-design
admission oracle (`validate_oceanis_30_1_projection`) -- explicitly "not a
generic ingestion/admission framework" per that module's own docstring, and
never reads `canonical_boat_designs` at all.

Given no accepted production qualification/resolution source exists for
`canonical_boat_designs` fields, `_qualify_draft_max` below MUST NOT (and
does not) treat a merely-present persisted JSON number as `CONFIRMED`: doing
so would be exactly the invented "persisted canonical means CONFIRMED"
shortcut the amendment review forbids, and copying the SLICE-0037 one-design
oracle into a fake generic authority is equally forbidden. It therefore
always returns `ValueQualification.MISSING`, regardless of the raw JSON
value -- fail-closed, never a fabricated confirmed/non-match. This makes
`compatible_boat_design_ids` always return an empty set against real
persisted BoatDesign data until a Project-Owner-accepted production
BoatDesign field-qualification/resolution source is decided and wired in
here; see the SLICE-0051 completion report for this exact BLOCKED
prerequisite.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any, Final

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
    "DRAFT_MAX_PROJECTION_FIELD",
    "build_boat_design_draft_configuration_set",
    "compatible_boat_design_ids",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the single `NumericLeafCriterion` it evaluates against.
DRAFT_MAX_PROJECTION_FIELD: Final = "draft_max_m"

_MISSING_DRAFT_MAX = QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING)


def _qualify_draft_max(_raw_value: Any) -> QualifiedNumericValue:
    """Always `MISSING` -- see this module's docstring, Finding 3.

    No accepted production per-field qualification/resolution source exists
    for `canonical_boat_designs` fields (no `FieldResolution` persistence, no
    resolution-aware import path). A merely-present raw JSON number is
    schema validity, not accepted/current resolution
    (`SEARCH_QUERY_SEMANTICS.v0.1.md` §3; `PROVENANCE_AND_QUALITY.md`), so it
    is never treated as `CONFIRMED` here. The parameter is intentionally
    unused (prefixed `_`) -- this function's job is exactly to *not* look at
    it until an accepted qualification source exists to consult instead.
    """
    return _MISSING_DRAFT_MAX


def build_boat_design_draft_configuration_set(
    boat_design: Mapping[str, Any],
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `draft_max_m` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. One
    `ResolvedConfiguration` is emitted for the unmodified baseline plus one
    per `named_variants[]` entry that this bounded adapter can validly
    resolve on its own -- using that variant's own
    `overrides.dimensions.draft_max_m` when explicitly present, else
    inheriting the baseline value -- never a `design_options` combination.

    Amendment review Finding 4: a `named_variants[]` entry whose own
    `requires_option_ids` is non-empty depends on at least one
    `DesignOption` this adapter never applies (it always emits
    `applied_option_ids=()`, deliberately never expanding option
    combinations). Such a variant's dependency cannot be established from
    the information this bounded adapter has, so it is excluded entirely
    from the resolved configuration set rather than being represented as an
    ordinary (and silently dependency-violating) resolved configuration --
    it must never be able to authorize a confirmed design match on its own.
    `excludes_option_ids` needs no equivalent check: with zero applied
    options on every configuration this adapter builds, an exclusion can
    never be violated.
    """
    design_id = boat_design["id"]
    baseline_dimensions = ((boat_design.get("baseline") or {}).get("dimensions")) or {}
    baseline_draft_max = baseline_dimensions.get("draft_max_m")

    configurations = [
        ResolvedConfiguration(
            identity=ConfigurationIdentity(
                configuration_id=f"{design_id}::baseline",
                boat_design_id=design_id,
            ),
            projection=ConfigurationProjection(
                numeric_values={DRAFT_MAX_PROJECTION_FIELD: _qualify_draft_max(baseline_draft_max)}
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
        raw_value = override_dimensions.get("draft_max_m", baseline_draft_max)
        configurations.append(
            ResolvedConfiguration(
                identity=ConfigurationIdentity(
                    configuration_id=f"{design_id}::{variant_id}",
                    boat_design_id=design_id,
                    named_variant_id=variant_id,
                ),
                projection=ConfigurationProjection(
                    numeric_values={DRAFT_MAX_PROJECTION_FIELD: _qualify_draft_max(raw_value)}
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
    draft_max: Decimal, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for `draft_max`.

    *draft_max* is the caller's already-parsed exact positive finite
    `Decimal` public requirement -- never converted to `float` here
    (amendment review Finding 2: doing so could silently change an accepted
    exact buyer threshold, or overflow/underflow for an otherwise-valid
    accepted arbitrary-precision Decimal spelling). `NumericLeafCriterion`
    and `QualifiedNumericValue` (`hullq.search.criteria` /
    `hullq.search.values`) both preserve a `Decimal` operand exactly rather
    than coercing it to `float`, so this comparison stays exact end to end.

    A `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA` design-level result is
    simply not included -- neither ever admits a design's PhysicalBoats to
    the concrete evaluation funnel. As of this amendment (Finding 3), this
    always returns an empty set against real persisted BoatDesign data: see
    this module's docstring for the exact missing production qualification
    prerequisite.
    """
    if not isinstance(draft_max, Decimal):
        raise TypeError(f"draft_max must be a Decimal, got {type(draft_max).__name__}")

    boat_designs = tuple(boat_designs)
    if not boat_designs:
        return frozenset()

    configuration_sets = tuple(build_boat_design_draft_configuration_set(bd) for bd in boat_designs)
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
