"""Persistence-agnostic provenance boundary: source observations and canonical decisions.

Implements the accepted ADR-0006 / SLICE-0006 provenance primitives:

- ProvenanceSubject: stable typed identity for any first-class HullQ subject
- FieldEvidence: immutable snapshot-safe source observation record
- FieldResolution: immutable versioned canonical-resolution decision
- JsonPointer: RFC 6901 JSON Pointer parsing, decoding and lookup
- Pure collection-level validators for evidence and resolution invariants
- Reverse source-impact lookup (source_id → evidence → resolutions)

Does not implement: persistence, ORM, ResearchJob state machine, source-rights
enforcement, source-authority ranking, derived-value calculation, network
acquisition, or fuzzy identity matching.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# RFC 6901 §4: array-index tokens must be "0" or a non-zero digit followed by
# zero or more digits.  Negative indices, leading zeros (e.g. "01"), explicit
# plus signs and the append sentinel "-" are all rejected during lookup.
_ARRAY_INDEX_RE = re.compile(r"^(0|[1-9][0-9]*)$")

__all__ = [
    "ConfidenceLevel",
    "EvidenceType",
    "FieldEvidence",
    "FieldResolution",
    "JsonPointer",
    "JsonPointerError",
    "NormalizedCandidate",
    "ProducerKind",
    "ProducerMetadata",
    "ProvenanceSubject",
    "RawObservation",
    "RawObservationKind",
    "ResearchContext",
    "ResolutionMethod",
    "ResolutionState",
    "ResolverKind",
    "ResolverMetadata",
    "SourceLocator",
    "SubjectKind",
    "check_canonical_consistency",
    "source_impact_lookup",
    "validate_evidence_invariants",
    "validate_resolution_history",
    "validate_resolution_invariants",
]


# ---------------------------------------------------------------------------
# Subject kind vocabulary — single source of truth matching
# PROVENANCE_SUBJECT_SCHEMA.v0.1.json. Tests enforce parity.
# ---------------------------------------------------------------------------


class SubjectKind(StrEnum):
    BOAT_MODEL = "boat_model"
    BOAT_DESIGN = "boat_design"
    NAMED_VARIANT = "named_variant"
    DESIGN_OPTION = "design_option"
    BRAND = "brand"
    ORGANIZATION = "organization"
    IDENTITY_ALIAS = "identity_alias"
    BRAND_MODEL_RELATIONSHIP = "brand_model_relationship"
    ORGANIZATION_DESIGN_RELATIONSHIP = "organization_design_relationship"


# ---------------------------------------------------------------------------
# Resolution vocabulary
# ---------------------------------------------------------------------------


class ResolutionState(StrEnum):
    RESOLVED = "resolved"
    RESOLVED_WITH_CONFLICT = "resolved_with_conflict"
    UNKNOWN = "unknown"
    NEEDS_REVIEW = "needs_review"
    CONFLICT = "conflict"


class ResolutionMethod(StrEnum):
    UNANIMOUS_EVIDENCE = "unanimous_evidence"
    SOURCE_PRIORITY_RULE = "source_priority_rule"
    DETERMINISTIC_VALIDATION = "deterministic_validation"
    MANUAL_ADJUDICATION = "manual_adjudication"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Observation vocabulary
# ---------------------------------------------------------------------------


class RawObservationKind(StrEnum):
    LITERAL = "literal"
    TEXT_FRAGMENT = "text_fragment"
    VISUAL_CLASSIFICATION = "visual_classification"
    STRUCTURED_RECORD = "structured_record"
    OTHER = "other"


class EvidenceType(StrEnum):
    MANUFACTURER_SPECIFICATION = "manufacturer_specification"
    BROCHURE = "brochure"
    MANUAL = "manual"
    TECHNICAL_DRAWING = "technical_drawing"
    CLASS_OR_OWNER_ASSOCIATION = "class_or_owner_association"
    STRUCTURED_DATASET = "structured_dataset"
    API_RECORD = "api_record"
    NARRATIVE_TEXT = "narrative_text"
    VISUAL_CLASSIFICATION = "visual_classification"
    USER_SUBMISSION = "user_submission"
    OTHER = "other"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class ProducerKind(StrEnum):
    HUMAN = "human"
    DETERMINISTIC_TOOL = "deterministic_tool"
    LLM = "llm"
    IMPORTER = "importer"


class ResolverKind(StrEnum):
    HUMAN = "human"
    DETERMINISTIC_TOOL = "deterministic_tool"
    LLM = "llm"


# ---------------------------------------------------------------------------
# RFC 6901 JSON Pointer
# ---------------------------------------------------------------------------


class JsonPointerError(ValueError):
    """Raised for syntactically invalid RFC 6901 JSON Pointer strings."""


def _decode_pointer_token(token: str) -> str:
    """Decode one RFC 6901 reference token: ~1 → /, ~0 → ~.

    Decoding order is defined by RFC 6901 §3: first ~1, then ~0.
    Any bare ~ not followed by 0 or 1 is a syntax error.
    """
    i = 0
    while i < len(token):
        if token[i] == "~":
            if i + 1 >= len(token) or token[i + 1] not in ("0", "1"):
                raise JsonPointerError(
                    f"Invalid escape in JSON Pointer token {token!r}: "
                    f"'~' must be followed by '0' or '1'"
                )
            i += 2
        else:
            i += 1
    return token.replace("~1", "/").replace("~0", "~")


class JsonPointer:
    """RFC 6901 JSON Pointer (must start with '/').

    Parses and validates the pointer on construction. Tokens are decoded
    (~1 → /, ~0 → ~) and exposed as an immutable tuple. The raw string is
    preserved for round-trip identity.

    No dot-path aliases are supported.
    """

    __slots__ = ("_raw", "_tokens")

    def __init__(self, raw: str) -> None:
        if not raw.startswith("/"):
            raise JsonPointerError(f"JSON Pointer must start with '/'; got {raw!r}")
        self._raw: str = raw
        self._tokens: tuple[str, ...] = tuple(
            _decode_pointer_token(tok) for tok in raw[1:].split("/")
        )

    @property
    def raw(self) -> str:
        """The original unparsed pointer string."""
        return self._raw

    @property
    def tokens(self) -> tuple[str, ...]:
        """Decoded reference tokens (empty tuple for root '/')."""
        return self._tokens

    def lookup(self, obj: object) -> object:
        """Navigate *obj* following this pointer's token sequence.

        Raises ``KeyError`` for missing dict keys, ``IndexError`` for
        out-of-range list positions, and ``TypeError`` for non-navigable
        types.
        """
        current: object = obj
        for token in self._tokens:
            if isinstance(current, dict):
                mapping: dict[str, object] = current
                if token not in mapping:
                    raise KeyError(f"Key {token!r} not found in object at pointer {self._raw!r}")
                current = mapping[token]
            elif isinstance(current, list):
                seq: list[object] = current
                if not _ARRAY_INDEX_RE.fullmatch(token):
                    raise KeyError(
                        f"Invalid RFC 6901 array index {token!r}: must be '0' or a "
                        f"non-zero digit followed by zero or more digits (no leading zeros, "
                        f"no sign prefix, no '-' sentinel)"
                    )
                current = seq[int(token)]
            else:
                raise TypeError(
                    f"Cannot traverse {type(current).__name__!r} "
                    f"with token {token!r} at pointer {self._raw!r}"
                )
        return current

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, JsonPointer):
            return NotImplemented
        return self._raw == other._raw

    def __hash__(self) -> int:
        return hash(self._raw)

    def __repr__(self) -> str:
        return f"JsonPointer({self._raw!r})"

    def __str__(self) -> str:
        return self._raw


# ---------------------------------------------------------------------------
# Provenance subject
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProvenanceSubject:
    """Stable typed identity address for a HullQ provenance subject.

    Matching the shared PROVENANCE_SUBJECT_SCHEMA.v0.1.json vocabulary.
    """

    kind: SubjectKind
    id: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("ProvenanceSubject.id must be non-empty")


# ---------------------------------------------------------------------------
# Source locator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceLocator:
    """Location within a source document where the observation was found."""

    page: int | str | None
    section: str | None
    anchor: str | None
    table: str | None
    figure: str | None
    record_key: str | None


# ---------------------------------------------------------------------------
# Raw observation and normalized candidate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RawObservation:
    """Immutable snapshot of the source value exactly as observed.

    ``value`` is deep-copied on construction so that later mutation of the
    caller-supplied object does not alter the captured snapshot.
    ``unit`` and ``excerpt`` are preserved unchanged.
    """

    kind: RawObservationKind
    value: object
    unit: str | None
    excerpt: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", copy.deepcopy(self.value))


@dataclass(frozen=True)
class NormalizedCandidate:
    """Normalized form of a raw observation, kept separate from the raw value.

    ``value`` is deep-copied on construction. The raw observation's ``unit``
    and ``excerpt`` are NOT stored here; they remain on ``RawObservation``
    where they are always accessible regardless of normalization outcome.
    """

    value: object
    unit: str | None
    method_id: str | None
    method_version: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", copy.deepcopy(self.value))


# ---------------------------------------------------------------------------
# Producer and research-context metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProducerMetadata:
    """Identity and versioning of the agent that produced a FieldEvidence record."""

    kind: ProducerKind
    identifier: str
    version: str | None
    model: str | None
    prompt_or_rule_version: str | None

    def __post_init__(self) -> None:
        if not self.identifier:
            raise ValueError("ProducerMetadata.identifier must be non-empty")


@dataclass(frozen=True)
class ResearchContext:
    """Optional research job and activity IDs linking evidence to a research run."""

    research_job_id: str | None
    activity_id: str | None


# ---------------------------------------------------------------------------
# FieldEvidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldEvidence:
    """Immutable source observation for one field on one stable HullQ subject.

    Records are append/supersede oriented: correcting an observation creates
    a new record linked via ``supersedes_evidence_id``; the prior record is
    never destructively rewritten.

    The ``raw`` observation and ``normalized_candidate`` are stored as
    independent, snapshot-safe value objects so normalization can never
    overwrite or erase source information.
    """

    evidence_id: str
    subject: ProvenanceSubject
    field_pointer: JsonPointer
    source_id: str
    source_locator: SourceLocator
    raw: RawObservation
    normalized_candidate: NormalizedCandidate | None
    evidence_type: EvidenceType
    producer: ProducerMetadata
    research_context: ResearchContext
    observed_at: str
    confidence: ConfidenceLevel
    supersedes_evidence_id: str | None
    notes: str | None

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("FieldEvidence.evidence_id must be non-empty")
        if not self.source_id:
            raise ValueError("FieldEvidence.source_id must be non-empty")


# ---------------------------------------------------------------------------
# Resolver metadata and FieldResolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolverMetadata:
    """Identity and versioning of the agent that produced a FieldResolution."""

    kind: ResolverKind
    identifier: str
    version: str | None

    def __post_init__(self) -> None:
        if not self.identifier:
            raise ValueError("ResolverMetadata.identifier must be non-empty")


@dataclass(frozen=True)
class FieldResolution:
    """Immutable versioned canonical decision for one field on one stable HullQ subject.

    At most one current (unsuperseded) resolution may exist per
    ``(subject.kind, subject.id, field_pointer.raw)`` — enforced by
    ``validate_resolution_history`` at the collection level.

    ``canonical_value_snapshot`` is deep-copied on construction to prevent
    caller mutation from altering the stored snapshot.
    """

    resolution_id: str
    subject: ProvenanceSubject
    field_pointer: JsonPointer
    state: ResolutionState
    canonical_value_snapshot: object
    supporting_evidence_ids: frozenset[str]
    contradicting_evidence_ids: frozenset[str]
    considered_evidence_ids: frozenset[str]
    resolution_method: ResolutionMethod
    policy_version: str
    resolver: ResolverMetadata
    resolved_at: str
    supersedes_resolution_id: str | None
    notes: str | None

    def __post_init__(self) -> None:
        if not self.resolution_id:
            raise ValueError("FieldResolution.resolution_id must be non-empty")
        if not self.policy_version:
            raise ValueError("FieldResolution.policy_version must be non-empty")
        object.__setattr__(
            self,
            "canonical_value_snapshot",
            copy.deepcopy(self.canonical_value_snapshot),
        )


# ---------------------------------------------------------------------------
# FieldEvidence invariant validation
# ---------------------------------------------------------------------------


def validate_evidence_invariants(
    evidence: FieldEvidence,
    all_evidence: dict[str, FieldEvidence] | None = None,
) -> list[str]:
    """Validate ADR-0006 invariants for a single FieldEvidence record.

    When *all_evidence* is supplied, supersession consistency is also checked:
    the superseded record must exist, belong to the same subject and field
    pointer, and must not create a self-reference.

    Returns a list of error message strings (empty = valid).
    No exception is raised for expected validation failures.
    """
    errors: list[str] = []

    # supersession consistency
    sup_id = evidence.supersedes_evidence_id
    if sup_id is not None:
        if sup_id == evidence.evidence_id:
            errors.append(f"Evidence {evidence.evidence_id!r} cannot supersede itself")
        elif all_evidence is not None:
            if sup_id not in all_evidence:
                errors.append(f"Superseded evidence {sup_id!r} not found in supplied collection")
            else:
                sup = all_evidence[sup_id]
                if sup.subject != evidence.subject:
                    errors.append(
                        f"Supersession crosses subject boundary: "
                        f"{evidence.evidence_id!r} subject {evidence.subject} "
                        f"vs superseded {sup_id!r} subject {sup.subject}"
                    )
                if sup.field_pointer != evidence.field_pointer:
                    errors.append(
                        f"Supersession crosses field boundary: "
                        f"{evidence.evidence_id!r} pointer {evidence.field_pointer} "
                        f"vs superseded {sup_id!r} pointer {sup.field_pointer}"
                    )

    return errors


# ---------------------------------------------------------------------------
# FieldResolution invariant validation
# ---------------------------------------------------------------------------


def validate_resolution_invariants(
    resolution: FieldResolution,
    all_evidence: dict[str, FieldEvidence],
) -> list[str]:
    """Validate ADR-0006 invariants for a single FieldResolution record.

    Checks that all referenced evidence IDs exist, belong to the same
    subject/field, that set containment and disjointness rules hold, and
    that state-specific snapshot/support/contradiction requirements are met.

    Returns a list of error message strings (empty = valid).
    """
    errors: list[str] = []
    rid = resolution.resolution_id
    sup_ids = resolution.supporting_evidence_ids
    con_ids = resolution.contradicting_evidence_ids
    con_sids = resolution.considered_evidence_ids
    state = resolution.state

    # All referenced evidence IDs must exist and belong to same subject/field
    all_referenced = sup_ids | con_ids | con_sids
    for eid in sorted(all_referenced):
        if eid not in all_evidence:
            errors.append(f"Resolution {rid!r}: evidence {eid!r} not found in collection")
            continue
        ev = all_evidence[eid]
        if ev.subject != resolution.subject:
            errors.append(
                f"Resolution {rid!r}: evidence {eid!r} belongs to subject "
                f"{ev.subject} not {resolution.subject}"
            )
        if ev.field_pointer != resolution.field_pointer:
            errors.append(
                f"Resolution {rid!r}: evidence {eid!r} has field pointer "
                f"{ev.field_pointer} not {resolution.field_pointer}"
            )

    # supporting and contradicting must be subsets of considered
    if not sup_ids <= con_sids:
        extras = sorted(sup_ids - con_sids)
        errors.append(
            f"Resolution {rid!r}: supporting evidence {extras} "
            f"not present in considered_evidence_ids"
        )
    if not con_ids <= con_sids:
        extras = sorted(con_ids - con_sids)
        errors.append(
            f"Resolution {rid!r}: contradicting evidence {extras} "
            f"not present in considered_evidence_ids"
        )

    # supporting and contradicting must be disjoint
    overlap = sorted(sup_ids & con_ids)
    if overlap:
        errors.append(
            f"Resolution {rid!r}: evidence IDs {overlap} appear in both "
            f"supporting and contradicting sets"
        )

    # state-specific constraints
    resolved_states = {ResolutionState.RESOLVED, ResolutionState.RESOLVED_WITH_CONFLICT}
    null_snapshot_states = {
        ResolutionState.UNKNOWN,
        ResolutionState.NEEDS_REVIEW,
        ResolutionState.CONFLICT,
    }

    if state in resolved_states:
        if resolution.canonical_value_snapshot is None:
            errors.append(
                f"Resolution {rid!r}: state {state!r} requires non-null canonical_value_snapshot"
            )
        if not sup_ids:
            errors.append(
                f"Resolution {rid!r}: state {state!r} requires at least one supporting evidence ID"
            )

    if state in null_snapshot_states and resolution.canonical_value_snapshot is not None:
        errors.append(f"Resolution {rid!r}: state {state!r} requires null canonical_value_snapshot")

    if state == ResolutionState.RESOLVED_WITH_CONFLICT and not con_ids:
        errors.append(
            f"Resolution {rid!r}: resolved_with_conflict requires at least one "
            f"contradicting evidence ID"
        )

    if state == ResolutionState.CONFLICT and not con_ids:
        errors.append(
            f"Resolution {rid!r}: unresolved conflict requires at least one "
            f"contradicting evidence ID"
        )

    return errors


# ---------------------------------------------------------------------------
# Resolution-history / current-state validation
# ---------------------------------------------------------------------------


def validate_resolution_history(
    resolutions: list[FieldResolution],
) -> list[str]:
    """Validate collection-level resolution-history invariants without persistence.

    Detects:
    - two unsuperseded (current) resolutions for the same subject/field;
    - a supersession link referencing a different subject or field pointer;
    - missing superseded resolution IDs (when the superseded ID is absent from
      the supplied collection and therefore the history is known to be incomplete);
    - self-supersession;
    - cycles in supersession chains.

    Returns a list of error message strings (empty = valid).
    """
    errors: list[str] = []
    by_id: dict[str, FieldResolution] = {r.resolution_id: r for r in resolutions}

    # Detect duplicate resolution_ids in the supplied collection
    seen_ids: set[str] = set()
    for r in resolutions:
        if r.resolution_id in seen_ids:
            errors.append(f"Duplicate resolution_id {r.resolution_id!r} in collection")
        seen_ids.add(r.resolution_id)

    # IDs that are referenced as superseded by some resolution
    superseded_ids: set[str] = set()
    for r in resolutions:
        if r.supersedes_resolution_id is not None:
            superseded_ids.add(r.supersedes_resolution_id)

    # Validate each supersession link
    for r in resolutions:
        sup_id = r.supersedes_resolution_id
        if sup_id is None:
            continue
        if sup_id == r.resolution_id:
            errors.append(f"Resolution {r.resolution_id!r} cannot supersede itself")
            continue
        if sup_id not in by_id:
            errors.append(
                f"Resolution {r.resolution_id!r} supersedes {sup_id!r} "
                f"which is absent from the supplied collection"
            )
            continue
        sup = by_id[sup_id]
        if sup.subject != r.subject:
            errors.append(
                f"Resolution {r.resolution_id!r} supersedes {sup_id!r} "
                f"which belongs to a different subject ({sup.subject} vs {r.subject})"
            )
        if sup.field_pointer != r.field_pointer:
            errors.append(
                f"Resolution {r.resolution_id!r} supersedes {sup_id!r} "
                f"which has a different field pointer "
                f"({sup.field_pointer} vs {r.field_pointer})"
            )

    # Detect cycles via DFS over the supersession graph
    _detect_cycles(by_id, errors)

    # Detect multiple current (unsuperseded) resolutions per subject/field
    # A current resolution is one whose resolution_id is not referenced as superseded
    # by any other resolution in the collection
    current_by_key: dict[tuple[str, str, str], list[str]] = {}
    for r in resolutions:
        if r.resolution_id not in superseded_ids:
            key = (str(r.subject.kind), r.subject.id, r.field_pointer.raw)
            current_by_key.setdefault(key, []).append(r.resolution_id)

    for key, ids in current_by_key.items():
        if len(ids) > 1:
            kind, sid, fp = key
            errors.append(
                f"Multiple current resolutions for subject ({kind}, {sid!r}) "
                f"field {fp!r}: {sorted(ids)}"
            )

    return errors


def _detect_cycles(
    by_id: dict[str, FieldResolution],
    errors: list[str],
) -> None:
    """Append cycle-detection errors to *errors* via iterative DFS."""
    # Build forward supersession graph: child → parent (what each resolution supersedes)
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(start: str) -> None:
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                in_stack.discard(node)
                continue
            if node in in_stack:
                errors.append(f"Cycle detected in resolution supersession chain involving {node!r}")
                return
            if node in visited:
                continue
            visited.add(node)
            in_stack.add(node)
            stack.append((node, True))
            r = by_id.get(node)
            if r is not None and r.supersedes_resolution_id is not None:
                nxt = r.supersedes_resolution_id
                if nxt in by_id:
                    stack.append((nxt, False))

    for rid in by_id:
        if rid not in visited:
            dfs(rid)


# ---------------------------------------------------------------------------
# Canonical-value consistency check
# ---------------------------------------------------------------------------


def check_canonical_consistency(
    canonical_subject_snapshot: dict[str, Any],
    resolution: FieldResolution,
) -> list[str]:
    """Check REQ-PROV-005: canonical field value matches the active resolution snapshot.

    For a non-null ``canonical_value_snapshot`` (resolved / resolved_with_conflict
    state), retrieves the value at ``resolution.field_pointer`` from
    *canonical_subject_snapshot* and compares it with the resolution snapshot.

    Returns a list of error message strings (empty = consistent).
    This helper is read-only; it never mutates the supplied snapshot.
    """
    errors: list[str] = []
    state = resolution.state
    resolved_states = {ResolutionState.RESOLVED, ResolutionState.RESOLVED_WITH_CONFLICT}

    if state not in resolved_states:
        # Non-resolved states must have null snapshot (REQ-PROV-008).
        if resolution.canonical_value_snapshot is not None:
            errors.append(
                f"Resolution {resolution.resolution_id!r} state {state!r} "
                f"must have null canonical_value_snapshot"
            )
            return errors
        # REQ-PROV-005 / REQ-PROV-008: an unresolved resolution must not coexist with
        # a non-null canonical production value at the same field.  A missing field or
        # an explicit null value in the canonical snapshot is acceptable.
        try:
            canonical_value = resolution.field_pointer.lookup(canonical_subject_snapshot)
            if canonical_value is not None:
                errors.append(
                    f"Resolution {resolution.resolution_id!r} state {state!r}: "
                    f"canonical subject has non-null value {canonical_value!r} at "
                    f"{resolution.field_pointer} but resolution has null "
                    f"canonical_value_snapshot"
                )
        except KeyError, IndexError, TypeError:
            pass  # field absent from canonical snapshot — acceptable for unresolved
        return errors

    if resolution.canonical_value_snapshot is None:
        errors.append(
            f"Resolution {resolution.resolution_id!r} state {state!r} "
            f"requires non-null canonical_value_snapshot"
        )
        return errors

    try:
        canonical_value = resolution.field_pointer.lookup(canonical_subject_snapshot)
    except (KeyError, IndexError, TypeError) as exc:
        errors.append(
            f"Resolution {resolution.resolution_id!r}: field pointer "
            f"{resolution.field_pointer} not found in canonical snapshot: {exc}"
        )
        return errors

    if canonical_value != resolution.canonical_value_snapshot:
        errors.append(
            f"Resolution {resolution.resolution_id!r}: canonical value at "
            f"{resolution.field_pointer} is {canonical_value!r} but resolution "
            f"snapshot is {resolution.canonical_value_snapshot!r}"
        )

    return errors


# ---------------------------------------------------------------------------
# Reverse source-impact lookup
# ---------------------------------------------------------------------------


def source_impact_lookup(
    source_id: str,
    evidence_collection: list[FieldEvidence],
    resolution_collection: list[FieldResolution],
) -> tuple[list[FieldEvidence], list[FieldResolution]]:
    """Enumerate all evidence and resolutions affected by *source_id*.

    Returns ``(affected_evidence, affected_resolutions)`` where:

    - *affected_evidence*: all ``FieldEvidence`` records with
      ``evidence.source_id == source_id``;
    - *affected_resolutions*: all ``FieldResolution`` records that reference
      at least one affected evidence ID in their ``considered_evidence_ids``.

    Implements the logical requirement behind REQ-PROV-007. No rights-change
    workflow is applied here; that belongs to SLICE-0007.
    """
    affected_evidence = [e for e in evidence_collection if e.source_id == source_id]
    affected_ids = frozenset(e.evidence_id for e in affected_evidence)
    affected_resolutions = [
        r for r in resolution_collection if not affected_ids.isdisjoint(r.considered_evidence_ids)
    ]
    return affected_evidence, affected_resolutions
