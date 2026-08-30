"""Persistence-neutral resolved-configuration projection boundary — SLICE-0035
(+ REVIEW amendment: runtime-closed hardening + NamedVariant constraints).

Implements slice In-scope item 5 ("Introduce a persistence-neutral resolved
configuration projection boundary. Search MUST consume already-qualified
technical values; schema-valid raw BoatDesign JSON or raw research evidence
MUST NOT become confirmed truth merely because it can be structurally
projected") and item 6 (configuration identity/explainability).

`DesignConfigurationSet` is the input contract `hullq.search.configuration_engine`
evaluates against. It is deliberately a flat, caller-supplied list of already
resolved `ResolvedConfiguration` entries plus one explicit completeness flag —
this module never expands NamedVariant/DesignOption combinations itself
(slice stop condition: "a generic configuration expansion rule would require
guessing whether options are combinable/applicable" halts the slice, it does
not authorize inventing one). Building that list from a real canonical
BoatDesign plus FieldResolution records is a future ingestion concern.

`OptionConstraint`/`NamedVariantConstraint` let a caller that DOES have
BOAT_DESIGN_SCHEMA.v0.6 `requires_option_ids`/`excludes_option_ids` (present
on both `design_options` and `named_variants`) pass them through so this
module can validate — never invent — that every supplied configuration
respects them (REVIEW Finding 3).

Every collection accepted at this boundary (`configurations`,
`requires_option_ids`, `excludes_option_ids`) is defensively materialized to
an immutable type *before* validation runs, and `configuration_space_complete`
— which directly licenses `CONFIRMED_NON_MATCH` — is type-checked as an
actual `bool`, so the truth-authorizing input this module grants downstream
evaluation authority over cannot be mutated, aliased or type-coerced out from
under that authority after construction (REVIEW Finding 2).

Does not implement: any BoatDesign/FieldResolution mutation, persistence, or
automatic option-combination expansion.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from hullq.search.types import ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue

__all__ = [
    "ConfigurationIdentity",
    "ConfigurationProjection",
    "DesignConfigurationSet",
    "NamedVariantConstraint",
    "OptionConstraint",
    "ResolvedConfiguration",
]

_MISSING_NUMERIC = QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING)
_MISSING_CATEGORICAL = QualifiedCategoricalValue(
    value=None, qualification=ValueQualification.MISSING
)


@dataclass(frozen=True, slots=True)
class ConfigurationProjection:
    """One resolved configuration's qualified field values, numeric + categorical.

    Mirrors `hullq.search.projection.SearchableDesignProjection`'s fail-closed
    `.get()` pattern, split into two mappings because numeric and categorical
    leaves compare against differently-typed qualified values. A field absent
    from either mapping is treated identically to a field present with an
    unqualified/missing status — never as a confirmed non-match.
    """

    numeric_values: Mapping[str, QualifiedNumericValue] = field(default_factory=dict)
    categorical_values: Mapping[str, QualifiedCategoricalValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "numeric_values", dict(self.numeric_values))
        object.__setattr__(self, "categorical_values", dict(self.categorical_values))

    def get_numeric(self, field_name: str) -> QualifiedNumericValue:
        return self.numeric_values.get(field_name, _MISSING_NUMERIC)

    def get_categorical(self, field_name: str) -> QualifiedCategoricalValue:
        return self.categorical_values.get(field_name, _MISSING_CATEGORICAL)


@dataclass(frozen=True, slots=True)
class ConfigurationIdentity:
    """Stable identity for one resolved configuration — slice Required Behavior §D.

    `configuration_id` MUST be unique within its `DesignConfigurationSet`.
    `named_variant_id`/`applied_option_ids` preserve verbatim the BoatDesign
    NamedVariant/DesignOption identifiers that produced this configuration
    (left `None`/`()` for the unmodified baseline) so a confirmed match can
    explain exactly which variant/option(s) produced it — never silently
    discarded (slice acceptance criterion on option/variant identifiers).
    """

    configuration_id: str
    boat_design_id: str
    named_variant_id: str | None = None
    applied_option_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.configuration_id:
            raise ValueError("ConfigurationIdentity.configuration_id must be non-empty")
        if not self.boat_design_id:
            raise ValueError("ConfigurationIdentity.boat_design_id must be non-empty")
        object.__setattr__(self, "applied_option_ids", tuple(self.applied_option_ids))
        if len(set(self.applied_option_ids)) != len(self.applied_option_ids):
            raise ValueError(
                f"ConfigurationIdentity.applied_option_ids must not contain duplicates; "
                f"got {self.applied_option_ids!r}"
            )


@dataclass(frozen=True, slots=True)
class ResolvedConfiguration:
    """One explicit, already-qualified resolved configuration of a BoatDesign."""

    identity: ConfigurationIdentity
    projection: ConfigurationProjection


def _freeze_and_validate_requires_excludes(
    label: str, requires_option_ids: Iterable[str], excludes_option_ids: Iterable[str]
) -> tuple[frozenset[str], frozenset[str]]:
    """Defensively materialize + validate one requires/excludes constraint pair.

    Shared by `OptionConstraint` and `NamedVariantConstraint` (REVIEW Finding
    2/3): the caller's source collections are copied into genuine
    `frozenset`s *before* the overlap check, so a caller mutating its own
    original `set`/`list` after construction cannot alter a validated
    constraint, and a plain mutable `set` passed in cannot later be mutated
    through any reference the caller retained.
    """
    requires = frozenset(requires_option_ids)
    excludes = frozenset(excludes_option_ids)
    overlap = requires & excludes
    if overlap:
        raise ValueError(
            f"{label} cannot both require and exclude the same option id(s): {sorted(overlap)}"
        )
    return requires, excludes


@dataclass(frozen=True, slots=True)
class OptionConstraint:
    """Explicit requires/excludes constraint for one DesignOption identifier.

    Mirrors BOAT_DESIGN_SCHEMA.v0.6 `design_options[].requires_option_ids` /
    `excludes_option_ids`. Supplying these to a `DesignConfigurationSet` lets
    it validate — never invent — that every `ResolvedConfiguration`'s
    `applied_option_ids` respects them (slice in-scope item 9): a
    configuration referencing this option without every required companion,
    or alongside an excluded option, is rejected at construction rather than
    silently accepted.
    """

    option_id: str
    requires_option_ids: frozenset[str] = frozenset()
    excludes_option_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.option_id:
            raise ValueError("OptionConstraint.option_id must be non-empty")
        requires, excludes = _freeze_and_validate_requires_excludes(
            f"OptionConstraint {self.option_id!r}",
            self.requires_option_ids,
            self.excludes_option_ids,
        )
        object.__setattr__(self, "requires_option_ids", requires)
        object.__setattr__(self, "excludes_option_ids", excludes)


@dataclass(frozen=True, slots=True)
class NamedVariantConstraint:
    """Explicit requires/excludes constraint for one NamedVariant identifier.

    Mirrors BOAT_DESIGN_SCHEMA.v0.6 `named_variants[].requires_option_ids` /
    `excludes_option_ids` — the same dependency/applicability shape as
    `OptionConstraint`, scoped to a `ConfigurationIdentity.named_variant_id`
    instead of an entry in `applied_option_ids` (REVIEW Finding 3). Supplying
    these to a `DesignConfigurationSet` lets it validate — never invent —
    that every `ResolvedConfiguration` carrying this variant respects them: a
    configuration whose variant requires a companion option it does not
    apply, or that applies an option the variant excludes, is rejected at
    construction. A variant with no supplied constraint is left unconstrained
    — this module never invents applicability for it.
    """

    variant_id: str
    requires_option_ids: frozenset[str] = frozenset()
    excludes_option_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.variant_id:
            raise ValueError("NamedVariantConstraint.variant_id must be non-empty")
        requires, excludes = _freeze_and_validate_requires_excludes(
            f"NamedVariantConstraint {self.variant_id!r}",
            self.requires_option_ids,
            self.excludes_option_ids,
        )
        object.__setattr__(self, "requires_option_ids", requires)
        object.__setattr__(self, "excludes_option_ids", excludes)


@dataclass(frozen=True, slots=True)
class DesignConfigurationSet:
    """The persistence-neutral configuration-aware search input for one BoatDesign.

    `configurations` is the explicit, bounded set of resolved configurations
    the caller supplies — never expanded/invented by this module.
    `configuration_space_complete` states whether this set is known to
    exhaust every materially possible configuration for the design: `True`
    licenses `CONFIRMED_NON_MATCH` when every listed configuration is a
    confirmed FALSE; `False` means at least one materially possible
    configuration is not represented here (or not yet trustworthy), which —
    absent an existing confirmed match — forces
    `INSUFFICIENT_DATA`/`CONFIGURATION_AMBIGUOUS` rather than a false
    non-match (SEARCH_QUERY_SEMANTICS.v0.1.md §7; slice Required Behavior §C).
    Because this flag directly authorizes `CONFIRMED_NON_MATCH`, it MUST be an
    actual `bool` — an `int`, `str` or other truthy/falsy value is rejected
    rather than coerced (REVIEW Finding 2).

    `option_constraints`/`variant_constraints`, when supplied, are validated
    against every configuration's `applied_option_ids`/`named_variant_id` at
    construction (slice in-scope item 9; REVIEW Finding 3). Each mapping key
    MUST equal the constraint's own `option_id`/`variant_id` — a mismatched
    key is rejected rather than silently ignored (REVIEW Finding 2).

    `configurations` and every constraint's requires/excludes collection are
    defensively materialized to immutable types before any validation runs,
    so mutating a caller-owned source collection after construction cannot
    alter what was validated or what is later evaluated (REVIEW Finding 2).
    """

    design_id: str
    configurations: tuple[ResolvedConfiguration, ...]
    configuration_space_complete: bool
    option_constraints: Mapping[str, OptionConstraint] = field(default_factory=dict)
    variant_constraints: Mapping[str, NamedVariantConstraint] = field(default_factory=dict)
    is_fixture: bool = False

    def __post_init__(self) -> None:
        if not self.design_id:
            raise ValueError("DesignConfigurationSet.design_id must be non-empty")
        if not isinstance(self.configuration_space_complete, bool):
            raise ValueError(
                f"DesignConfigurationSet.configuration_space_complete must be an actual bool; "
                f"got {self.configuration_space_complete!r} "
                f"({type(self.configuration_space_complete).__name__})"
            )
        object.__setattr__(self, "configurations", tuple(self.configurations))
        if not self.configurations:
            raise ValueError("DesignConfigurationSet.configurations must be non-empty")
        object.__setattr__(self, "option_constraints", dict(self.option_constraints))
        object.__setattr__(self, "variant_constraints", dict(self.variant_constraints))

        for key, constraint in self.option_constraints.items():
            if key != constraint.option_id:
                raise ValueError(
                    f"option_constraints key {key!r} does not match "
                    f"OptionConstraint.option_id {constraint.option_id!r}"
                )
        for key, variant_constraint in self.variant_constraints.items():
            if key != variant_constraint.variant_id:
                raise ValueError(
                    f"variant_constraints key {key!r} does not match "
                    f"NamedVariantConstraint.variant_id {variant_constraint.variant_id!r}"
                )

        seen_ids: set[str] = set()
        for configuration in self.configurations:
            identity = configuration.identity
            if identity.boat_design_id != self.design_id:
                raise ValueError(
                    f"ResolvedConfiguration {identity.configuration_id!r} has "
                    f"boat_design_id {identity.boat_design_id!r}, expected {self.design_id!r}"
                )
            if identity.configuration_id in seen_ids:
                raise ValueError(
                    f"Duplicate configuration_id {identity.configuration_id!r} in "
                    f"DesignConfigurationSet for design {self.design_id!r}"
                )
            seen_ids.add(identity.configuration_id)
            self._validate_option_constraints(identity)
            self._validate_variant_constraint(identity)

    def _validate_option_constraints(self, identity: ConfigurationIdentity) -> None:
        applied = set(identity.applied_option_ids)
        for option_id in identity.applied_option_ids:
            constraint = self.option_constraints.get(option_id)
            if constraint is None:
                continue
            missing_required = constraint.requires_option_ids - applied
            if missing_required:
                raise ValueError(
                    f"Configuration {identity.configuration_id!r} applies option "
                    f"{option_id!r} without its required companion option id(s) "
                    f"{sorted(missing_required)}"
                )
            violated_excludes = constraint.excludes_option_ids & applied
            if violated_excludes:
                raise ValueError(
                    f"Configuration {identity.configuration_id!r} applies option "
                    f"{option_id!r} alongside excluded option id(s) "
                    f"{sorted(violated_excludes)}"
                )

    def _validate_variant_constraint(self, identity: ConfigurationIdentity) -> None:
        if identity.named_variant_id is None:
            return
        constraint = self.variant_constraints.get(identity.named_variant_id)
        if constraint is None:
            return
        applied = set(identity.applied_option_ids)
        missing_required = constraint.requires_option_ids - applied
        if missing_required:
            raise ValueError(
                f"Configuration {identity.configuration_id!r} carries variant "
                f"{identity.named_variant_id!r} without its required companion option "
                f"id(s) {sorted(missing_required)}"
            )
        violated_excludes = constraint.excludes_option_ids & applied
        if violated_excludes:
            raise ValueError(
                f"Configuration {identity.configuration_id!r} carries variant "
                f"{identity.named_variant_id!r} alongside excluded option id(s) "
                f"{sorted(violated_excludes)}"
            )
