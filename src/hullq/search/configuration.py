"""Persistence-neutral resolved-configuration projection boundary — SLICE-0035
(+ REVIEW amendments: runtime-closed hardening, NamedVariant constraints,
explicit applicability, and identifier-collection runtime closure).

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
respects them (REVIEW Finding 3), and let a caller that DOES have an explicit
applicability qualification for that option/variant declare it via the
already-accepted `hullq.search.types.ValueQualification` vocabulary — the
same three-valued (confirmed / not-applicable / unresolved) fail-closed
vocabulary this package already uses for field values, reused here rather
than inventing a new enum (REVIEW Finding 1, second round). A `CONFIRMED`
declared option/variant participates normally. A `NOT_APPLICABLE` or any
unresolved (`MISSING`/`UNRESOLVED_CONFLICT`/`PROVISIONAL`/
`APPLICABILITY_UNKNOWN`) declared option/variant can never be referenced by
an accepted `ResolvedConfiguration` — the input is rejected at construction
rather than silently entering the trusted resolved set — and an unresolved
(not `NOT_APPLICABLE`, which is a confirmed negative) declaration additionally
forbids `configuration_space_complete=True` anywhere on the same set, so a
caller cannot simultaneously admit genuine applicability uncertainty and
claim a truth-authorizing complete configuration space. An option/variant
with no supplied constraint at all remains fully unconstrained, exactly as
before — no applicability state is ever inferred merely from a constraint's
absence, a fixture's presence, requires/excludes, or completeness.

Every collection accepted at this boundary (`configurations`, applied option
ID collections, `requires_option_ids`, `excludes_option_ids`) is validated as
a genuine collection of non-empty string identifiers and defensively
materialized to an immutable type *before* validation runs. A bare `str`/
`bytes` is rejected rather than silently iterated character-by-character
(REVIEW Finding 2, second round), and `configuration_space_complete` — which
directly licenses `CONFIRMED_NON_MATCH` — is type-checked as an actual
`bool`, so the truth-authorizing input this module grants downstream
evaluation authority over cannot be mutated, aliased or type-coerced out from
under that authority after construction (REVIEW Finding 2).

Does not implement: any BoatDesign/FieldResolution mutation, persistence,
automatic option-combination expansion, or applicability inference from
model-year/hull-number/source data — applicability is always caller-supplied,
explicit, and validated, never resolved by this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

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

#: Applicability qualifications other than CONFIRMED/NOT_APPLICABLE: the
#: option/variant's own applicability is not yet known/resolved one way or
#: the other. A constraint declaring one of these forbids
#: `configuration_space_complete=True` on the same `DesignConfigurationSet`
#: (REVIEW Finding 1, second round, point 4/7).
_UNRESOLVED_APPLICABILITY: Final[frozenset[ValueQualification]] = frozenset(
    {
        ValueQualification.MISSING,
        ValueQualification.UNRESOLVED_CONFLICT,
        ValueQualification.PROVISIONAL,
        ValueQualification.APPLICABILITY_UNKNOWN,
    }
)


# ---------------------------------------------------------------------------
# Shared runtime-closed identifier validation (REVIEW Finding 2, second round)
# ---------------------------------------------------------------------------


def _validate_non_empty_str(label: str, value: object) -> str:
    """Reject anything that is not an actual non-empty `str`.

    A merely-truthy check (`if not value`) would silently accept a non-`str`
    truthy object; this requires the genuine type.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be non-empty; got {value!r} ({type(value).__name__})")
    return value


def _validate_optional_non_empty_str(label: str, value: object) -> str | None:
    if value is None:
        return None
    return _validate_non_empty_str(label, value)


def _validate_id_collection(label: str, value: object) -> tuple[str, ...]:
    """Validate *value* is a genuine collection of non-empty string identifiers.

    Rejects a bare `str`/`bytes` outright: both are themselves iterable over
    characters/bytes and would otherwise silently explode into a
    per-character "collection" (e.g. `frozenset("OPT-B")` ->
    `{"O", "P", "T", "-", "B"}`), which could let a forbidden option
    combination bypass requires/excludes validation entirely. Rejects any
    non-string or empty element. Rejects duplicate elements outright rather
    than silently deduplicating them via later `set`/`frozenset`
    materialization. Returns an order-preserving tuple; callers needing set
    semantics build a `frozenset` from this already-validated tuple.
    """
    if isinstance(value, (str, bytes)):
        raise ValueError(
            f"{label} must be a collection of individual string identifiers, not a bare "
            f"{type(value).__name__} (which would be iterated character-by-character); "
            f"got {value!r}"
        )
    if not isinstance(value, Iterable):
        raise ValueError(f"{label} must be an iterable of string identifiers; got {value!r}")
    items = tuple(value)
    for item in items:
        if not isinstance(item, str) or not item:
            raise ValueError(
                f"{label} elements must be non-empty strings; got {item!r} ({type(item).__name__})"
            )
    if len(set(items)) != len(items):
        raise ValueError(f"{label} must not contain duplicates; got {items!r}")
    return items


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
    Every identifier is runtime-validated as an actual non-empty `str` (or
    collection thereof); a bare `str`/`bytes` is never accepted in place of
    `applied_option_ids` (REVIEW Finding 2, second round).
    """

    configuration_id: str
    boat_design_id: str
    named_variant_id: str | None = None
    applied_option_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "configuration_id",
            _validate_non_empty_str(
                "ConfigurationIdentity.configuration_id", self.configuration_id
            ),
        )
        object.__setattr__(
            self,
            "boat_design_id",
            _validate_non_empty_str("ConfigurationIdentity.boat_design_id", self.boat_design_id),
        )
        object.__setattr__(
            self,
            "named_variant_id",
            _validate_optional_non_empty_str(
                "ConfigurationIdentity.named_variant_id", self.named_variant_id
            ),
        )
        object.__setattr__(
            self,
            "applied_option_ids",
            _validate_id_collection(
                "ConfigurationIdentity.applied_option_ids", self.applied_option_ids
            ),
        )


@dataclass(frozen=True, slots=True)
class ResolvedConfiguration:
    """One explicit, already-qualified resolved configuration of a BoatDesign."""

    identity: ConfigurationIdentity
    projection: ConfigurationProjection


def _freeze_and_validate_requires_excludes(
    label: str, requires_option_ids: object, excludes_option_ids: object
) -> tuple[frozenset[str], frozenset[str]]:
    """Validate + defensively materialize one requires/excludes constraint pair.

    Shared by `OptionConstraint` and `NamedVariantConstraint` (REVIEW Finding
    2/3): every element is validated as a genuine non-empty string identifier
    (rejecting a bare `str`/`bytes` collection and rejecting duplicates) via
    `_validate_id_collection` *before* being frozen into a `frozenset`, so a
    caller mutating its own original `set`/`list` after construction cannot
    alter a validated constraint.
    """
    requires = frozenset(
        _validate_id_collection(f"{label}.requires_option_ids", requires_option_ids)
    )
    excludes = frozenset(
        _validate_id_collection(f"{label}.excludes_option_ids", excludes_option_ids)
    )
    overlap = requires & excludes
    if overlap:
        raise ValueError(
            f"{label} cannot both require and exclude the same option id(s): {sorted(overlap)}"
        )
    return requires, excludes


def _validate_applicability(label: str, value: object) -> ValueQualification:
    if not isinstance(value, ValueQualification):
        raise ValueError(
            f"{label}.applicability must be a ValueQualification member; got {value!r}"
        )
    return value


@dataclass(frozen=True, slots=True)
class OptionConstraint:
    """Explicit requires/excludes/applicability constraint for one DesignOption.

    Mirrors BOAT_DESIGN_SCHEMA.v0.6 `design_options[].requires_option_ids` /
    `excludes_option_ids`. Supplying these to a `DesignConfigurationSet` lets
    it validate — never invent — that every `ResolvedConfiguration`'s
    `applied_option_ids` respects them (slice in-scope item 9): a
    configuration referencing this option without every required companion,
    or alongside an excluded option, is rejected at construction rather than
    silently accepted.

    `applicability` reuses the already-accepted `ValueQualification`
    three-valued vocabulary (REVIEW Finding 1, second round) rather than
    inventing a new enum: `CONFIRMED` (the default) means this option is
    known-applicable and participates normally; `NOT_APPLICABLE` means a
    `ResolvedConfiguration` referencing this option MUST NOT be accepted at
    all; any other member (`MISSING`/`UNRESOLVED_CONFLICT`/`PROVISIONAL`/
    `APPLICABILITY_UNKNOWN`) means the same — the configuration is rejected —
    *and* additionally forbids `configuration_space_complete=True` anywhere
    on the same `DesignConfigurationSet`, because a materially possible but
    applicability-unresolved option must not be silently excluded from a
    claimed-complete configuration space.
    """

    option_id: str
    requires_option_ids: frozenset[str] = frozenset()
    excludes_option_ids: frozenset[str] = frozenset()
    applicability: ValueQualification = ValueQualification.CONFIRMED

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "option_id", _validate_non_empty_str("OptionConstraint.option_id", self.option_id)
        )
        requires, excludes = _freeze_and_validate_requires_excludes(
            f"OptionConstraint {self.option_id!r}",
            self.requires_option_ids,
            self.excludes_option_ids,
        )
        object.__setattr__(self, "requires_option_ids", requires)
        object.__setattr__(self, "excludes_option_ids", excludes)
        object.__setattr__(
            self,
            "applicability",
            _validate_applicability(f"OptionConstraint {self.option_id!r}", self.applicability),
        )


@dataclass(frozen=True, slots=True)
class NamedVariantConstraint:
    """Explicit requires/excludes/applicability constraint for one NamedVariant.

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

    `applicability` behaves identically to `OptionConstraint.applicability`
    (REVIEW Finding 1, second round): `CONFIRMED` (default) participates
    normally; `NOT_APPLICABLE` or any unresolved member rejects any
    `ResolvedConfiguration` carrying this variant, and an unresolved member
    additionally forbids `configuration_space_complete=True` on the same set.
    """

    variant_id: str
    requires_option_ids: frozenset[str] = frozenset()
    excludes_option_ids: frozenset[str] = frozenset()
    applicability: ValueQualification = ValueQualification.CONFIRMED

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "variant_id",
            _validate_non_empty_str("NamedVariantConstraint.variant_id", self.variant_id),
        )
        requires, excludes = _freeze_and_validate_requires_excludes(
            f"NamedVariantConstraint {self.variant_id!r}",
            self.requires_option_ids,
            self.excludes_option_ids,
        )
        object.__setattr__(self, "requires_option_ids", requires)
        object.__setattr__(self, "excludes_option_ids", excludes)
        object.__setattr__(
            self,
            "applicability",
            _validate_applicability(
                f"NamedVariantConstraint {self.variant_id!r}", self.applicability
            ),
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
    Because this flag directly authorizes `CONFIRMED_NON_MATCH`, it MUST be an
    actual `bool` — an `int`, `str` or other truthy/falsy value is rejected
    rather than coerced (REVIEW Finding 2).

    `option_constraints`/`variant_constraints`, when supplied, are validated
    against every configuration's `applied_option_ids`/`named_variant_id` at
    construction (slice in-scope item 9; REVIEW Finding 3). Each mapping key
    MUST equal the constraint's own `option_id`/`variant_id` — a mismatched
    key is rejected rather than silently ignored (REVIEW Finding 2). A
    constraint whose `applicability` is not `CONFIRMED` rejects any
    configuration that references it, and an unresolved (non-`NOT_APPLICABLE`)
    applicability additionally rejects `configuration_space_complete=True` on
    this whole set (REVIEW Finding 1, second round).

    `configurations` and every identifier collection are validated as genuine
    non-empty-string collections and defensively materialized to immutable
    types before any validation runs, so mutating a caller-owned source
    collection after construction cannot alter what was validated or what is
    later evaluated, and a bare `str`/`bytes` can never stand in for an
    identifier collection (REVIEW Finding 2, second round).
    """

    design_id: str
    configurations: tuple[ResolvedConfiguration, ...]
    configuration_space_complete: bool
    option_constraints: Mapping[str, OptionConstraint] = field(default_factory=dict)
    variant_constraints: Mapping[str, NamedVariantConstraint] = field(default_factory=dict)
    is_fixture: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "design_id",
            _validate_non_empty_str("DesignConfigurationSet.design_id", self.design_id),
        )
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

        self._validate_applicability_vs_completeness()

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

    def _validate_applicability_vs_completeness(self) -> None:
        """REVIEW Finding 1 (second round), points 4 and 7.

        A caller must not be able to simultaneously supply an unresolved
        (non-`CONFIRMED`, non-`NOT_APPLICABLE`) option/variant applicability
        and claim `configuration_space_complete=True`: that combination would
        let a materially possible but applicability-unresolved configuration
        be silently excluded from a claimed-complete space, enabling a false
        `CONFIRMED_NON_MATCH`. `NOT_APPLICABLE` is a *confirmed* negative and
        does not trigger this — it is definitionally excluded, not uncertain.
        """
        if not self.configuration_space_complete:
            return
        unresolved = [
            c.option_id
            for c in self.option_constraints.values()
            if c.applicability in _UNRESOLVED_APPLICABILITY
        ] + [
            c.variant_id
            for c in self.variant_constraints.values()
            if c.applicability in _UNRESOLVED_APPLICABILITY
        ]
        if unresolved:
            raise ValueError(
                f"DesignConfigurationSet.configuration_space_complete cannot be True while "
                f"option_constraints/variant_constraints declares unresolved applicability for "
                f"{sorted(unresolved)}; a materially possible but unresolved configuration would "
                f"be silently excluded from a claimed-complete configuration space"
            )

    def _validate_option_constraints(self, identity: ConfigurationIdentity) -> None:
        applied = set(identity.applied_option_ids)
        for option_id in identity.applied_option_ids:
            constraint = self.option_constraints.get(option_id)
            if constraint is None:
                continue
            if constraint.applicability is not ValueQualification.CONFIRMED:
                raise ValueError(
                    f"Configuration {identity.configuration_id!r} applies option {option_id!r} "
                    f"whose declared applicability is {constraint.applicability.value!r}, not "
                    f"CONFIRMED; a not-applicable or applicability-unresolved option must not be "
                    f"represented as an ordinary resolved configuration"
                )
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
        if constraint.applicability is not ValueQualification.CONFIRMED:
            raise ValueError(
                f"Configuration {identity.configuration_id!r} carries variant "
                f"{identity.named_variant_id!r} whose declared applicability is "
                f"{constraint.applicability.value!r}, not CONFIRMED; a not-applicable or "
                f"applicability-unresolved variant must not be represented as an ordinary "
                f"resolved configuration"
            )
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
