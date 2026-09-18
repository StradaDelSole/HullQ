"""Shared BoatDesign/configuration production bridge mechanics — SLICE-0055.

SLICE-0055 contract §6 (criterion #2 abstraction requirement) requires that
the production responsibilities already embedded in the SLICE-0051
`draft_max` path -- canonical subject lookup; FieldResolution
qualification/current-snapshot agreement; baseline + safely resolvable
NamedVariant projection; and design eligibility feeding concrete native
inventory evaluation -- are identified and reused/generalized rather than
copied a second time for `keel_configuration`. This module is that shared
boundary: it knows nothing about `draft_max` or `keel_configuration`
specifically. Criterion-specific field pointers, decoding, taxonomy mapping
and value construction stay in each criterion's own adapter module
(`hullq.search.draft_max_design_bridge`, `hullq.search.keel_design_bridge`),
expressed as a `FieldProjectionSpec`.

Does not implement: any BoatDesign/FieldResolution mutation, automatic
option-combination expansion, or a query/HTTP boundary of its own.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from hullq.domain.provenance import FieldResolution, ResolutionState, SubjectKind
from hullq.persistence.field_resolution import (
    CanonicalLookupResult,
    CanonicalLookupStatus,
    FetchCanonicalValue,
    fetch_current_field_resolution,
)
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import ConfigurationSearchOutcome, run_configuration_query
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue

__all__ = [
    "BoatDesignConfigurationQueryResult",
    "FieldProjectionSpec",
    "build_boat_design_configuration_set",
    "compatible_boat_design_ids_for_query",
    "decode_categorical_string_for_qualification",
    "decode_decimal_for_qualification",
    "lookup_boat_design_baseline_snapshot",
    "lookup_named_variant_canonical_snapshot",
    "make_bounded_canonical_value_lookup",
    "qualify_canonical_field",
    "run_boat_design_configuration_query",
]

_RESOLVED_STATES: Final = frozenset(
    {ResolutionState.RESOLVED, ResolutionState.RESOLVED_WITH_CONFLICT}
)

_SELECT_DESIGNS_CONTAINING_VARIANT = (
    "SELECT id, named_variants FROM canonical_boat_designs WHERE named_variants @> %s::jsonb"
)


# ---------------------------------------------------------------------------
# Shared decode helpers — the only per-value-type-shaped knowledge here
# ---------------------------------------------------------------------------


def decode_decimal_for_qualification(value: object) -> Decimal:
    """Decode a raw canonical value or FieldResolution snapshot as an exact `Decimal`.

    Used for both sides of `qualify_canonical_field`'s agreement check: a raw
    canonical numeric field pointer value is an ordinary JSON number
    (`int`/`float`) once read back through JSONB, while a durable
    `FieldResolution.canonical_value_snapshot` is always the exact-Decimal
    string encoding (`hullq.persistence.field_resolution.
    encode_canonical_decimal_snapshot`) -- `Decimal(str(value))` normalizes
    both representations to the same comparable exact value.
    """
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"cannot decode {value!r} as an exact Decimal") from exc


def decode_categorical_string_for_qualification(value: object) -> str:
    """Decode a raw canonical value or FieldResolution snapshot as a plain string.

    A categorical BoatDesign field (e.g. `appendages.keel_type`) is already
    the same plain JSON string on both sides -- no Decimal-vs-JSON-number
    representation asymmetry exists for it, so no further decoding is
    required beyond rejecting a non-string value.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"expected a non-empty string categorical value; got {value!r}")
    return value


# ---------------------------------------------------------------------------
# Shared canonical subject lookup — "canonical subject lookup" (contract §6)
# ---------------------------------------------------------------------------


def lookup_boat_design_baseline_snapshot(conn: Any, design_id: str) -> CanonicalLookupResult:
    """Resolve a BoatDesign id to its durable `{"baseline": {...}}` snapshot.

    The entire `baseline` subtree is returned (not narrowed to one leaf
    field) so that `resolution.field_pointer.lookup(...)` can retrieve
    *any* `/baseline/...` field pointer -- this one lookup already serves
    every criterion adapter's baseline field, never only `draft_max`.
    """
    design = fetch_boat_design(conn, design_id)
    if design is None:
        return CanonicalLookupResult(status=CanonicalLookupStatus.SUBJECT_NOT_FOUND)
    return CanonicalLookupResult(
        status=CanonicalLookupStatus.FOUND,
        canonical_subject_snapshot={"baseline": design.get("baseline") or {}},
    )


def lookup_named_variant_canonical_snapshot(conn: Any, variant_id: str) -> CanonicalLookupResult:
    """Resolve one NamedVariant id to its durable `{"overrides": {...}}` snapshot.

    `named_variants` is opaque JSONB embedded inside `canonical_boat_designs`
    (SLICE-0016), not a separate durable row -- the only way to dereference a
    NamedVariant id is a JSONB containment search across every
    `canonical_boat_designs.named_variants` array. More than one design
    containing a variant with this exact id is a data integrity condition
    this bounded lookup refuses to silently pick a winner from -- fails
    closed as `AMBIGUOUS_SUBJECT`. Returns the entire `overrides` subtree,
    serving any criterion adapter's override field pointer.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_DESIGNS_CONTAINING_VARIANT, [json.dumps([{"id": variant_id}])])
        rows = cur.fetchall()
    matches = [
        variant
        for _design_id, named_variants in rows
        for variant in (named_variants or [])
        if variant.get("id") == variant_id
    ]
    if not matches:
        return CanonicalLookupResult(status=CanonicalLookupStatus.SUBJECT_NOT_FOUND)
    if len(matches) > 1:
        return CanonicalLookupResult(status=CanonicalLookupStatus.AMBIGUOUS_SUBJECT)
    return CanonicalLookupResult(
        status=CanonicalLookupStatus.FOUND,
        canonical_subject_snapshot={"overrides": matches[0].get("overrides") or {}},
    )


def make_bounded_canonical_value_lookup(
    accepted_pointers: Mapping[SubjectKind, frozenset[str]],
) -> FetchCanonicalValue:
    """Build a `FetchCanonicalValue` hard-bounded to *accepted_pointers*.

    Mirrors the SLICE-0051 `lookup_draft_max_canonical_value` bounding
    discipline generically: any `(subject_kind, field_pointer)` combination
    not explicitly listed in *accepted_pointers* fails closed as
    `SUBJECT_NOT_FOUND` rather than falling back to a generic all-field
    resolution mechanism this module deliberately does not implement. Each
    criterion adapter constructs its own bounded lookup naming only its own
    accepted field pointers.
    """

    def _lookup(conn: Any, resolution: FieldResolution) -> CanonicalLookupResult:
        subject = resolution.subject
        pointer = resolution.field_pointer.raw
        if pointer not in accepted_pointers.get(subject.kind, frozenset()):
            return CanonicalLookupResult(status=CanonicalLookupStatus.SUBJECT_NOT_FOUND)
        if subject.kind is SubjectKind.BOAT_DESIGN:
            return lookup_boat_design_baseline_snapshot(conn, subject.id)
        if subject.kind is SubjectKind.NAMED_VARIANT:
            return lookup_named_variant_canonical_snapshot(conn, subject.id)
        return CanonicalLookupResult(status=CanonicalLookupStatus.SUBJECT_NOT_FOUND)

    return _lookup


# ---------------------------------------------------------------------------
# Shared FieldResolution qualification — "FieldResolution qualification/
# current-snapshot agreement" (contract §6)
# ---------------------------------------------------------------------------


def qualify_canonical_field[T](
    conn: Any,
    *,
    subject_kind: SubjectKind,
    subject_id: str,
    field_pointer: str,
    raw_canonical_value: Any,
    decode: Callable[[Any], T],
) -> tuple[ValueQualification, T | None]:
    """Qualify one raw canonical value against its active FieldResolution.

    Fails closed to `MISSING` for every case except an active
    `resolved`/`resolved_with_conflict` resolution whose decoded snapshot
    agrees with *raw_canonical_value* decoded the same way -- never treats
    mere JSONB presence as confirmation (SLICE-0051 Finding 3). *decode* is
    the one piece of type-specific knowledge this generic function needs;
    everything else (fetching the active resolution, checking its state,
    comparing decoded values) is identical for a numeric or categorical
    field.
    """
    if raw_canonical_value is None:
        return (ValueQualification.MISSING, None)

    record = fetch_current_field_resolution(conn, subject_kind, subject_id, field_pointer)
    if record is None or record.state not in _RESOLVED_STATES:
        return (ValueQualification.MISSING, None)

    try:
        snapshot_value = decode(record.canonical_value_snapshot)
        canonical_value = decode(raw_canonical_value)
    except ValueError:
        return (ValueQualification.MISSING, None)

    if snapshot_value != canonical_value:
        # Canonical-value <-> active-resolution snapshot mismatch
        # (PROVENANCE_MODEL.v0.1.md §6): the resolution has gone stale
        # relative to the canonical record it is supposed to qualify.
        return (ValueQualification.MISSING, None)

    return (ValueQualification.CONFIRMED, snapshot_value)


# ---------------------------------------------------------------------------
# Shared baseline + NamedVariant projection — "baseline + safely resolvable
# NamedVariant projection" (contract §6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldProjectionSpec:
    """One criterion's field-projection contract for the shared configuration bridge.

    `section_key`/`field_key` address the field within a BoatDesign
    `baseline`/NamedVariant `overrides` document (e.g. `"dimensions"` +
    `"draft_max_m"`, or `"appendages"` + `"keel_type"`).
    `baseline_pointer`/`override_pointer` are the exact JSON Pointers this
    field's FieldResolution subjects are qualified against.  `decode`
    normalizes a raw/snapshot value for the agreement check
    (`qualify_canonical_field`). `is_numeric` selects whether the qualified
    value is projected into `ConfigurationProjection.numeric_values` or
    `.categorical_values`. `taxonomy_map`, when supplied, is applied to an
    otherwise-`CONFIRMED` decoded value; a value with no entry in the map
    fails closed to `MISSING` rather than being coerced into a category by
    inference (SLICE-0055 contract §4) -- `None` means no criterion-specific
    remapping is needed (the decoded value is used as-is, e.g. `draft_max`).
    """

    projection_field: str
    section_key: str
    field_key: str
    baseline_pointer: str
    override_pointer: str
    decode: Callable[[Any], Any]
    is_numeric: bool
    taxonomy_map: Mapping[str, str] | None = None


def _qualify_and_map(
    conn: Any,
    spec: FieldProjectionSpec,
    *,
    subject_kind: SubjectKind,
    subject_id: str,
    field_pointer: str,
    raw_value: Any,
) -> tuple[ValueQualification, Any]:
    qualification, decoded = qualify_canonical_field(
        conn,
        subject_kind=subject_kind,
        subject_id=subject_id,
        field_pointer=field_pointer,
        raw_canonical_value=raw_value,
        decode=spec.decode,
    )
    if qualification is not ValueQualification.CONFIRMED:
        return (qualification, None)
    if spec.taxonomy_map is None:
        return (ValueQualification.CONFIRMED, decoded)
    assert isinstance(decoded, str)  # taxonomy_map is only ever paired with a string decode
    mapped = spec.taxonomy_map.get(decoded)
    if mapped is None:
        # Unsupported/unauthorized taxonomy value (contract §4): fails
        # closed to MISSING/UNKNOWN rather than guessing a broader category.
        return (ValueQualification.MISSING, None)
    return (ValueQualification.CONFIRMED, mapped)


def _make_projection(
    specs: Sequence[FieldProjectionSpec],
    results: Mapping[str, tuple[ValueQualification, Any]],
) -> ConfigurationProjection:
    numeric_values: dict[str, QualifiedNumericValue] = {}
    categorical_values: dict[str, QualifiedCategoricalValue] = {}
    for spec in specs:
        qualification, value = results[spec.projection_field]
        confirmed_value = value if qualification is ValueQualification.CONFIRMED else None
        if spec.is_numeric:
            numeric_values[spec.projection_field] = QualifiedNumericValue(
                value=confirmed_value, qualification=qualification
            )
        else:
            categorical_values[spec.projection_field] = QualifiedCategoricalValue(
                value=confirmed_value, qualification=qualification
            )
    return ConfigurationProjection(
        numeric_values=numeric_values, categorical_values=categorical_values
    )


def build_boat_design_configuration_set(
    conn: Any, boat_design: Mapping[str, Any], specs: Sequence[FieldProjectionSpec]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting every field in *specs* for *boat_design*.

    One `ResolvedConfiguration` is emitted for the unmodified baseline plus
    one per `named_variants[]` entry this bounded adapter can validly
    resolve on its own -- never a `design_options` combination (a variant
    with a non-empty `requires_option_ids` is excluded entirely, mirroring
    SLICE-0051 amendment Finding 4). Each configuration's projection carries
    every field named by *specs*, numeric and categorical alike, so a single
    `MixedAndQuery` combining criteria across multiple specs (e.g.
    `draft_max AND keel_configuration`) can be evaluated against the exact
    same configuration identity -- this is what lets criterion #2 combine
    with criterion #1 without a second, parallel per-field evaluation path.

    A NamedVariant with no own override key for a field inherits the
    already-qualified baseline qualification for that field (never a
    fabricated second FieldResolution merely to represent inheritance). An
    explicit `null` override clears that field to `MISSING` regardless of
    the baseline (a deliberate authored "this variant's value is not the
    baseline's" signal, distinct from silence).
    """
    design_id = boat_design["id"]
    baseline = boat_design.get("baseline") or {}

    baseline_results: dict[str, tuple[ValueQualification, Any]] = {}
    for spec in specs:
        section = (baseline.get(spec.section_key)) or {}
        raw_value = section.get(spec.field_key)
        baseline_results[spec.projection_field] = _qualify_and_map(
            conn,
            spec,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer=spec.baseline_pointer,
            raw_value=raw_value,
        )

    configurations = [
        ResolvedConfiguration(
            identity=ConfigurationIdentity(
                configuration_id=f"{design_id}::baseline", boat_design_id=design_id
            ),
            projection=_make_projection(specs, baseline_results),
        )
    ]

    for variant in boat_design.get("named_variants") or []:
        if variant.get("requires_option_ids"):
            # Unresolved DesignOption dependency this adapter cannot
            # establish -- exclude the variant entirely rather than
            # represent an unresolved dependency as an ordinary resolved
            # configuration.
            continue
        variant_id = variant["id"]
        overrides = variant.get("overrides") or {}

        variant_results: dict[str, tuple[ValueQualification, Any]] = {}
        for spec in specs:
            override_section = (overrides.get(spec.section_key)) or {}
            if spec.field_key not in override_section:
                variant_results[spec.projection_field] = baseline_results[spec.projection_field]
                continue
            override_raw_value = override_section[spec.field_key]
            if override_raw_value is None:
                variant_results[spec.projection_field] = (ValueQualification.MISSING, None)
                continue
            variant_results[spec.projection_field] = _qualify_and_map(
                conn,
                spec,
                subject_kind=SubjectKind.NAMED_VARIANT,
                subject_id=variant_id,
                field_pointer=spec.override_pointer,
                raw_value=override_raw_value,
            )

        configurations.append(
            ResolvedConfiguration(
                identity=ConfigurationIdentity(
                    configuration_id=f"{design_id}::{variant_id}",
                    boat_design_id=design_id,
                    named_variant_id=variant_id,
                ),
                projection=_make_projection(specs, variant_results),
            )
        )

    return DesignConfigurationSet(
        design_id=design_id,
        configurations=tuple(configurations),
        configuration_space_complete=False,
        is_fixture=False,
    )


# ---------------------------------------------------------------------------
# Shared design eligibility — "design eligibility feeding concrete native
# inventory evaluation" (contract §6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoatDesignConfigurationQueryResult:
    """SLICE-0055 §7 (second amendment, Finding 1): the complete typed result
    of evaluating one query against a batch of designs' configuration sets.

    `outcome` is the unmodified `ConfigurationSearchOutcome` (confirmed
    matches, confirmed non-matches and insufficient-data designs, each
    carrying its own `matching_configuration_ids`/`configuration_evaluations`
    exactly as `hullq.search.configuration_engine.run_configuration_query`
    produces it -- nothing about that established kernel type is changed).

    `configurations_by_id` is the corresponding resolved
    configuration/projection evidence, keyed by the exact
    `configuration_id` every `ConfigurationEvaluation` in `outcome` already
    references. `evaluate_configuration` computes each configuration's
    truth from `ResolvedConfiguration.projection`'s qualified numeric/
    categorical values but does not itself return them; this mapping is
    what lets a caller recover, for any `(configuration_id, field)` pair
    already referenced by `outcome`, the exact safely-resolved/observed
    canonical value that was actually used for that field's evaluation --
    without re-running or reconstructing Search truth, and without parsing
    `CriterionEvaluation.explanation`.
    """

    outcome: ConfigurationSearchOutcome
    configurations_by_id: Mapping[str, ResolvedConfiguration]


def run_boat_design_configuration_query(
    conn: Any,
    query: MixedAndQuery,
    boat_designs: Iterable[Mapping[str, Any]],
    specs: Sequence[FieldProjectionSpec],
) -> BoatDesignConfigurationQueryResult:
    """Evaluate *query* against every design's configuration set, preserving
    both the complete typed `ConfigurationSearchOutcome` and the resolved
    configuration/projection evidence it was computed from.

    *specs* must cover every projection field *query.criteria* addresses
    (draft-only, keel-only, or both together) -- each design's
    `DesignConfigurationSet` is built once via
    `build_boat_design_configuration_set`, carrying every field the active
    query needs on the same configuration identity, then evaluated through
    the unchanged `hullq.search.configuration_engine.run_configuration_query`
    kernel.

    SLICE-0055 amendment (Finding 1, first pass): returns the complete
    `ConfigurationSearchOutcome` -- confirmed matches, confirmed non-matches
    and insufficient-data designs alike -- rather than collapsing it to a
    bare set of confirmed design ids.

    SLICE-0055 amendment (Finding 1, second pass): also returns
    `configurations_by_id`, the exact `ResolvedConfiguration` objects
    `build_boat_design_configuration_set` built and `run_configuration_query`
    evaluated, so the safely resolved/observed canonical value behind each
    `outcome` criterion evaluation remains recoverable -- `outcome` alone,
    once the corresponding `DesignConfigurationSet`s go out of scope, cannot
    answer "what BoatDesign/NamedVariant value was actually evaluated here."

    A caller that only needs the confirmed id set (SLICE-0051's/SLICE-0055's
    own single-criterion bridges, whose established public contracts predate
    or are bounded to that shape) should use
    `compatible_boat_design_ids_for_query`, a thin wrapper over this function
    that discards both; a caller building production application evidence
    (`hullq.application.native_inventory_query`) should call this function
    directly and preserve the full result.
    """
    boat_designs = tuple(boat_designs)
    if not boat_designs:
        return BoatDesignConfigurationQueryResult(
            outcome=ConfigurationSearchOutcome(
                confirmed_matches=(), confirmed_non_matches=(), insufficient_data=()
            ),
            configurations_by_id={},
        )
    configuration_sets = tuple(
        build_boat_design_configuration_set(conn, bd, specs) for bd in boat_designs
    )
    configurations_by_id = {
        configuration.identity.configuration_id: configuration
        for configuration_set in configuration_sets
        for configuration in configuration_set.configurations
    }
    outcome = run_configuration_query(query, configuration_sets)
    return BoatDesignConfigurationQueryResult(
        outcome=outcome, configurations_by_id=configurations_by_id
    )


def compatible_boat_design_ids_for_query(
    conn: Any,
    query: MixedAndQuery,
    boat_designs: Iterable[Mapping[str, Any]],
    specs: Sequence[FieldProjectionSpec],
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for *query*.

    A CONFIRMED_NON_MATCH or INSUFFICIENT_DATA design-level result is simply
    not included -- neither ever admits a design's PhysicalBoats to the
    concrete evaluation funnel. Thin wrapper over
    `run_boat_design_configuration_query` for callers (SLICE-0051's
    `draft_max_design_bridge.compatible_boat_design_ids`, SLICE-0055's
    `keel_design_bridge.compatible_boat_design_ids_for_keel`) whose own
    established public contract is bounded to a bare id set -- see that
    function's docstring (Finding 1) for the fuller-evidence alternative.
    """
    result = run_boat_design_configuration_query(conn, query, boat_designs, specs)
    return frozenset(evaluation.design_id for evaluation in result.outcome.confirmed_matches)
