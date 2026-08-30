"""Persistence-neutral resolved-configuration projection boundary — SLICE-0035.

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

`OptionConstraint` lets a caller that DOES have BOAT_DESIGN_SCHEMA.v0.6
`requires_option_ids`/`excludes_option_ids` pass them through so this module
can validate (never invent) that every supplied configuration respects them.

Does not implement: any BoatDesign/FieldResolution mutation, persistence, or
automatic option-combination expansion.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from hullq.search.types import ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue

__all__ = [
    "ConfigurationIdentity",
    "ConfigurationProjection",
    "DesignConfigurationSet",
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
        overlap = self.requires_option_ids & self.excludes_option_ids
        if overlap:
            raise ValueError(
                f"OptionConstraint {self.option_id!r} cannot both require and exclude "
                f"the same option id(s): {sorted(overlap)}"
            )


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

    `option_constraints`, when supplied, is validated against every
    configuration's `applied_option_ids` at construction (slice in-scope item
    9).
    """

    design_id: str
    configurations: tuple[ResolvedConfiguration, ...]
    configuration_space_complete: bool
    option_constraints: Mapping[str, OptionConstraint] = field(default_factory=dict)
    is_fixture: bool = False

    def __post_init__(self) -> None:
        if not self.design_id:
            raise ValueError("DesignConfigurationSet.design_id must be non-empty")
        if not self.configurations:
            raise ValueError("DesignConfigurationSet.configurations must be non-empty")
        object.__setattr__(self, "option_constraints", dict(self.option_constraints))

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
