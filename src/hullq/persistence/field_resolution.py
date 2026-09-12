"""Durable PostgreSQL persistence for versioned `FieldResolution` — SLICE-0051 amendment.

Implements the minimum production persistence prerequisite identified by
`docs/SLICE_0051_FIELD_RESOLUTION_BLOCKER_RECONCILIATION_2026-09-12.md`:
OQ-004 / ADR-0006 already accepts `hullq.domain.provenance.FieldResolution`
as the canonical field-qualification model, but production PostgreSQL did
not yet durably persist it. This module gives that existing domain type an
immutable-revision + explicit-current-head home, mirroring
`hullq.persistence.physical_boat_claims`'s proven shape, and reuses
`hullq.domain.provenance.validate_resolution_invariants` plus
`hullq.sources.rights.check_source_use` for the invariants that need actual
referenced records rather than reimplementing them as SQL or inventing a
Search-specific quality/resolution type.

## Concurrency: advisory lock, not a row lock

Every other immutable-revision-plus-head table in this codebase
(`physical_boat_claim_revisions`, `native_listing_offer_revisions`) locks a
pre-existing parent row (`physical_boats`, `native_listings`) for the
duration of the write transaction, serializing concurrent writers for that
parent. `FieldResolution` has no equivalent fixed parent: `subject_kind`
ranges over BoatModel/BoatDesign/NamedVariant/DesignOption, and
NamedVariant/DesignOption are not separate durable rows at all (opaque
JSONB inside `canonical_boat_designs`, SLICE-0016). This module instead
takes a PostgreSQL advisory transaction lock
(`pg_advisory_xact_lock(hashtextextended(...))`) keyed by the exact logical
`(subject_kind, subject_id, field_pointer)` tuple, released automatically at
transaction end. This serializes every concurrent writer for the same
logical subject field exactly as a row lock would, including the very first
write for a subject field (where no row yet exists to lock).

## Canonical-value consistency is enforced here, at the write boundary

Amendment review Finding 7: verifying "canonical subject value == resolution
snapshot" (`PROVENANCE_MODEL.v0.1.md` §6) only at Search read-time left a
window where a resolution could be durably admitted while already
disagreeing with the canonical record it claims to qualify -- a defensive
Search-side check catches that *for readers*, but does not stop the write
itself from being accepted. This module is generic over `subject_kind` /
`field_pointer` and has no way on its own to dereference an arbitrary
subject's canonical document, so the caller supplies a bounded
`fetch_canonical_value` callback (required, no default) that resolves
*resolution.subject* to its durable canonical snapshot; this module then
checks it against `resolution` (REQ-PROV-005) for every state, not only
`resolved`/`resolved_with_conflict`. This comparison is Decimal-value-aware,
not a generic structural `!=` on the two raw representations
(`hullq.domain.provenance.check_canonical_consistency` is *not* reused here
for exactly this reason -- see `_check_canonical_value_consistency`'s
docstring): `canonical_value_snapshot` at this module's boundary is always
the exact-Decimal string encoding (`encode_canonical_decimal_snapshot`),
while the durable canonical document stores an ordinary JSON number, so a
literal string/type comparison would spuriously mismatch equal values
formatted differently (e.g. `"1.3"` vs `"1.30"`) or crash comparing a
`float` to a `str`. A callback returning anything other than
`CanonicalLookupStatus.FOUND` (subject does not durably exist, or resolves to
more than one candidate) fails the write closed as
`CANONICAL_SUBJECT_UNRESOLVABLE`; a `FOUND` snapshot that disagrees with the
resolution fails closed as `CANONICAL_VALUE_MISMATCH`. The only accepted
production implementation, `hullq.search.draft_max_design_bridge.lookup_draft_max_canonical_value`,
is itself hard-bounded to SLICE-0051's exact two field meanings -- this
module does not invent global all-field resolution semantics; it only
mandates that *some* bounded, subject-aware lookup is consulted before any
write is admitted. `hullq.search.draft_max_design_bridge`'s own
read-time consistency check (`_qualify_via_field_resolution`) is retained as
defense-in-depth, not superseded by this write-time gate.

## Evidence and source-rights admission

For a `resolved`/`resolved_with_conflict` resolution, every id in
`considered_evidence_ids` (a superset of `supporting_evidence_ids` and
`contradicting_evidence_ids` -- VAL-PROV-004) must resolve to a durable
`research_evidence` row via `hullq.persistence.readback.fetch_evidence`; a
missing id fails closed as `EVIDENCE_NOT_FOUND`. The reconstructed evidence
collection is then passed to
`hullq.domain.provenance.validate_resolution_invariants`, which enforces
subject/field compatibility and the supporting/contradicting/considered set
relationships (VAL-PROV-004) using the exact accepted domain rule, not a
reimplementation.

For every id in `supporting_evidence_ids` specifically (the evidence that
actually legitimizes the confirmed value -- contradicting evidence is
retained for audit, not admission), this module resolves that evidence's
`source_id` against a caller-supplied `available_sources` mapping and calls
`hullq.sources.rights.check_source_use(source, SourceUse.PRODUCTION_VALUE)`.
A `source_id` absent from `available_sources` fails closed as
`SOURCE_NOT_AVAILABLE` (never "not found means allowed"); any non-`ALLOWED`
gate outcome fails closed as `SOURCE_USE_DENIED`. `available_sources` is a
bounded, caller-supplied mechanism consuming existing schema-valid
`SOURCE_SCHEMA.v0.2` Source records (e.g. `fixtures/sources/*.json`) -- this
module never invents a universal Source-registry table, and the SLICE-0037
Oceanis pilot's own conditional/non-recurring clearance is never treated as
a generic production permission.

Amendment review Finding 9: before `check_source_use` is ever called, the
resolved `available_sources[source_id]` record must itself declare that same
`source_id` (never trust a caller-supplied mapping key over the record's own
identity) and must validate against `specs/SOURCE_SCHEMA.v0.2.json`. Either
failure fails closed as `SOURCE_RECORD_INVALID` -- a malformed or
mismatched-identity Source record can never silently authorize a resolution.

## Supersession identity (Finding 8)

`resolution.supersedes_resolution_id` -- the resolution's own declared
predecessor -- must equal the caller's `expected_current_resolution_id`
before any other check runs; a mismatch fails closed as
`SUPERSESSION_MISMATCH`, checked before the advisory lock is even acquired
since it depends on nothing durable. The resolution's own
`supersedes_resolution_id` (not `expected_current_resolution_id`) is what is
persisted into the `field_resolutions.supersedes_resolution_id` column and
what is fingerprinted for idempotency -- the two are guaranteed equal by this
gate, but the column always reflects what the resolution itself asserts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import jsonschema

from hullq.domain.provenance import (
    FieldEvidence,
    FieldResolution,
    JsonPointer,
    ProvenanceSubject,
    ResolutionMethod,
    ResolutionState,
    ResolverKind,
    ResolverMetadata,
    SubjectKind,
    validate_resolution_invariants,
)
from hullq.persistence.fingerprint import fingerprint_dict
from hullq.persistence.readback import fetch_evidence
from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use

__all__ = [
    "CanonicalLookupResult",
    "CanonicalLookupStatus",
    "FetchCanonicalValue",
    "FieldResolutionWriteResult",
    "FieldResolutionWriteStatus",
    "encode_canonical_decimal_snapshot",
    "fetch_current_field_resolution",
    "fetch_field_resolution",
    "list_field_resolution_history",
    "write_field_resolution",
]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SOURCE_SCHEMA_PATH = _REPO_ROOT / "specs" / "SOURCE_SCHEMA.v0.2.json"


def _load_source_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(_SOURCE_SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema


class FieldResolutionTransactionOwnershipError(RuntimeError):
    """write_field_resolution cannot safely own a top-level transaction on *conn*.

    Mirrors `hullq.persistence.physical_boat_claims.PhysicalBoatClaimTransactionOwnershipError`:
    a CREATED/REVISED result must always mean the new current resolution is
    already durably committed, independent of later caller action. Requires
    an IDLE connection so it can safely own and commit its own top-level
    transaction.
    """


class FieldResolutionWriteStatus(StrEnum):
    """Mechanically distinct write outcomes. Never a bare boolean."""

    CREATED = "created"
    REVISED = "revised"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    SUPERSESSION_MISMATCH = "supersession_mismatch"
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    INVARIANTS_VIOLATED = "invariants_violated"
    CANONICAL_SUBJECT_UNRESOLVABLE = "canonical_subject_unresolvable"
    CANONICAL_VALUE_MISMATCH = "canonical_value_mismatch"
    SOURCE_NOT_AVAILABLE = "source_not_available"
    SOURCE_RECORD_INVALID = "source_record_invalid"
    SOURCE_USE_DENIED = "source_use_denied"


_STATUSES_REQUIRING_CURRENT = frozenset(
    {
        FieldResolutionWriteStatus.CREATED,
        FieldResolutionWriteStatus.REVISED,
        FieldResolutionWriteStatus.ALREADY_EXISTS,
    }
)
# CONFLICT is deliberately exempt from both checks below (mirrors
# hullq.persistence.physical_boat_claims.PhysicalBoatClaimWriteResult): it
# may carry the real pre-existing current_resolution_id (a revision attempt
# against a stale/forged predecessor), or None (a first-ever-write attempt
# against a subject field that turns out to already be occupied by a
# different resolution_id, or a caller-forged non-null expectation when
# nothing exists yet -- see test_first_write_with_nonnull_expected_fails_closed).
_STATUSES_FORBIDDING_CURRENT = frozenset(
    {
        FieldResolutionWriteStatus.SUPERSESSION_MISMATCH,
        FieldResolutionWriteStatus.EVIDENCE_NOT_FOUND,
        FieldResolutionWriteStatus.INVARIANTS_VIOLATED,
        FieldResolutionWriteStatus.CANONICAL_SUBJECT_UNRESOLVABLE,
        FieldResolutionWriteStatus.CANONICAL_VALUE_MISMATCH,
        FieldResolutionWriteStatus.SOURCE_NOT_AVAILABLE,
        FieldResolutionWriteStatus.SOURCE_RECORD_INVALID,
        FieldResolutionWriteStatus.SOURCE_USE_DENIED,
    }
)


@dataclass(frozen=True)
class FieldResolutionWriteResult:
    """Deterministic result of one write_field_resolution call.

    `current_resolution_id` reflects the real durable current head of this
    `(subject_kind, subject_id, field_pointer)` after this call, and is only
    populated for the statuses that reach/preserve a current head.
    `detail` carries a human-readable diagnostic for a rejected write
    (evidence/invariant/source-rights failures); it is never populated for a
    successful write.
    """

    status: FieldResolutionWriteStatus
    current_resolution_id: str | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.status in _STATUSES_REQUIRING_CURRENT and self.current_resolution_id is None:
            raise ValueError(
                f"A {self.status.value.upper()} write result must carry current_resolution_id"
            )
        if self.status in _STATUSES_FORBIDDING_CURRENT and self.current_resolution_id is not None:
            raise ValueError(
                f"A {self.status.value.upper()} write result must not carry current_resolution_id"
            )


# ---------------------------------------------------------------------------
# Canonical-value consistency lookup contract (Finding 7)
# ---------------------------------------------------------------------------


class CanonicalLookupStatus(StrEnum):
    """Outcome of a bounded `fetch_canonical_value` lookup."""

    FOUND = "found"
    SUBJECT_NOT_FOUND = "subject_not_found"
    AMBIGUOUS_SUBJECT = "ambiguous_subject"


@dataclass(frozen=True)
class CanonicalLookupResult:
    """Result of resolving one FieldResolution's subject to its durable canonical snapshot.

    `canonical_subject_snapshot` must be shaped so that
    `resolution.field_pointer.lookup(canonical_subject_snapshot)` retrieves
    the exact durable canonical value the resolution is required to agree
    with (`hullq.domain.provenance.check_canonical_consistency`,
    REQ-PROV-005). Only populated for `FOUND`; every other status means
    `write_field_resolution` fails the write closed without attempting a
    value comparison at all.
    """

    status: CanonicalLookupStatus
    canonical_subject_snapshot: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status is CanonicalLookupStatus.FOUND:
            if self.canonical_subject_snapshot is None:
                raise ValueError(
                    "a FOUND CanonicalLookupResult must carry canonical_subject_snapshot"
                )
        elif self.canonical_subject_snapshot is not None:
            raise ValueError(
                f"a {self.status.value.upper()} CanonicalLookupResult must not carry "
                "canonical_subject_snapshot"
            )


#: Resolves *resolution*'s subject to its durable canonical snapshot. Required
#: (no default) on every `write_field_resolution` call -- see Finding 7 in the
#: module docstring for why this cannot be optional or Search-side-only.
FetchCanonicalValue = Callable[[Any, FieldResolution], CanonicalLookupResult]


# ---------------------------------------------------------------------------
# Canonical-value snapshot encoding — exact Decimal, never a JSON number
# ---------------------------------------------------------------------------


def encode_canonical_decimal_snapshot(value: Decimal) -> str:
    """Canonical lossless string encoding for a Decimal `canonical_value_snapshot`.

    Stored as a JSON *string*, never a JSON number: PostgreSQL JSONB (and
    every ordinary JSON decoder) represents JSON numbers as binary
    double-precision floats on read, which could silently change an exact
    Decimal value. Reuses the exact canonicalization already accepted for
    SLICE-0051's own public `draft_max` boundary
    (`hullq.search.draft_max_request.canonical_draft_max_str`) is
    deliberately NOT reused here bit-for-bit, because that function rejects
    non-positive values and this snapshot encoder must remain a faithful,
    lossless encoding of whatever finite Decimal it is given.
    """
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(
            f"encode_canonical_decimal_snapshot requires a finite Decimal; got {value!r}"
        )
    return str(value)


def decode_canonical_decimal_snapshot(raw: object) -> Decimal:
    """Inverse of `encode_canonical_decimal_snapshot`. Raises on any non-string payload."""
    if not isinstance(raw, str):
        raise ValueError(
            f"expected a JSON string canonical_value_snapshot for a Decimal field; got {raw!r} "
            f"({type(raw).__name__})"
        )
    return Decimal(raw)


# ---------------------------------------------------------------------------
# Envelope fingerprint (idempotency)
# ---------------------------------------------------------------------------


def _envelope_dict(resolution: FieldResolution) -> dict[str, Any]:
    return {
        "subject_kind": resolution.subject.kind.value,
        "subject_id": resolution.subject.id,
        "field_pointer": resolution.field_pointer.raw,
        "state": resolution.state.value,
        "canonical_value_snapshot": resolution.canonical_value_snapshot,
        "supporting_evidence_ids": sorted(resolution.supporting_evidence_ids),
        "contradicting_evidence_ids": sorted(resolution.contradicting_evidence_ids),
        "considered_evidence_ids": sorted(resolution.considered_evidence_ids),
        "resolution_method": resolution.resolution_method.value,
        "policy_version": resolution.policy_version,
        "resolver_kind": resolution.resolver.kind.value,
        "resolver_identifier": resolution.resolver.identifier,
        "resolver_version": resolution.resolver.version,
        "resolved_at": resolution.resolved_at,
        "supersedes_resolution_id": resolution.supersedes_resolution_id,
        "notes": resolution.notes,
    }


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_ADVISORY_LOCK = "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))"

_SELECT_HEAD = (
    "SELECT current_resolution_id FROM field_resolution_heads "
    "WHERE subject_kind = %s AND subject_id = %s AND field_pointer = %s"
)

_SELECT_RESOLUTION_BY_ID = (
    "SELECT subject_kind, subject_id, field_pointer, supersedes_resolution_id, content_hash "
    "FROM field_resolutions WHERE resolution_id = %s"
)

_INSERT_RESOLUTION = """
INSERT INTO field_resolutions (
    resolution_id, subject_kind, subject_id, field_pointer, state,
    canonical_value_snapshot, supporting_evidence_ids, contradicting_evidence_ids,
    considered_evidence_ids, resolution_method, policy_version,
    resolver_kind, resolver_identifier, resolver_version, resolved_at,
    supersedes_resolution_id, notes, content_hash
) VALUES (
    %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (resolution_id) DO NOTHING
"""

_UPSERT_HEAD = """
INSERT INTO field_resolution_heads (
    subject_kind, subject_id, field_pointer, current_resolution_id
) VALUES (%s, %s, %s, %s)
ON CONFLICT (subject_kind, subject_id, field_pointer)
DO UPDATE SET current_resolution_id = EXCLUDED.current_resolution_id,
              updated_at = NOW()
"""

_RESOLUTION_COLUMNS = """
    r.resolution_id, r.subject_kind, r.subject_id, r.field_pointer, r.state,
    r.canonical_value_snapshot, r.supporting_evidence_ids, r.contradicting_evidence_ids,
    r.considered_evidence_ids, r.resolution_method, r.policy_version,
    r.resolver_kind, r.resolver_identifier, r.resolver_version, r.resolved_at,
    r.supersedes_resolution_id, r.notes
"""

_SELECT_CURRENT_RESOLUTION = f"""
SELECT {_RESOLUTION_COLUMNS}
FROM field_resolution_heads h
JOIN field_resolutions r ON r.resolution_id = h.current_resolution_id
WHERE h.subject_kind = %s AND h.subject_id = %s AND h.field_pointer = %s
"""

_SELECT_RESOLUTION_RECORD = f"""
SELECT {_RESOLUTION_COLUMNS} FROM field_resolutions r WHERE r.resolution_id = %s
"""

_SELECT_HISTORY = f"""
SELECT {_RESOLUTION_COLUMNS} FROM field_resolutions r
WHERE r.subject_kind = %s AND r.subject_id = %s AND r.field_pointer = %s
ORDER BY r.recorded_at ASC, r.resolution_id ASC
"""


def _row_to_resolution(row: tuple[Any, ...]) -> FieldResolution:
    (
        resolution_id,
        subject_kind,
        subject_id,
        field_pointer,
        state,
        canonical_value_snapshot,
        supporting_evidence_ids,
        contradicting_evidence_ids,
        considered_evidence_ids,
        resolution_method,
        policy_version,
        resolver_kind,
        resolver_identifier,
        resolver_version,
        resolved_at,
        supersedes_resolution_id,
        notes,
    ) = row
    resolved_at_str = resolved_at.isoformat() if isinstance(resolved_at, datetime) else resolved_at
    return FieldResolution(
        resolution_id=resolution_id,
        subject=ProvenanceSubject(kind=SubjectKind(subject_kind), id=subject_id),
        field_pointer=JsonPointer(field_pointer),
        state=ResolutionState(state),
        canonical_value_snapshot=canonical_value_snapshot,
        supporting_evidence_ids=frozenset(supporting_evidence_ids),
        contradicting_evidence_ids=frozenset(contradicting_evidence_ids),
        considered_evidence_ids=frozenset(considered_evidence_ids),
        resolution_method=ResolutionMethod(resolution_method),
        policy_version=policy_version,
        resolver=ResolverMetadata(
            kind=ResolverKind(resolver_kind),
            identifier=resolver_identifier,
            version=resolver_version,
        ),
        resolved_at=resolved_at_str,
        supersedes_resolution_id=supersedes_resolution_id,
        notes=notes,
    )


def _check_canonical_value_consistency(
    resolution: FieldResolution, canonical_subject_snapshot: dict[str, Any]
) -> str | None:
    """Finding 7: verify *resolution* agrees with its durable canonical subject.

    Deliberately does not reuse `hullq.domain.provenance.check_canonical_consistency`
    verbatim: that function compares the raw canonical value and
    `resolution.canonical_value_snapshot` with a plain `!=`, which is correct
    only when both sides share the same representation. In this module,
    `canonical_value_snapshot` is always the exact-Decimal string encoding
    (`encode_canonical_decimal_snapshot`), while the durable canonical
    document (`canonical_boat_designs.baseline`/`named_variants`) stores an
    ordinary JSON number -- a literal `!=` would spuriously mismatch equal
    values formatted differently (`"1.3"` vs `"1.30"`) or simply crash
    comparing a `float` to a `str`. Both sides are decoded to `Decimal` and
    compared by value instead, exactly mirroring the accepted read-time
    comparison in `hullq.search.draft_max_design_bridge._qualify_via_field_resolution`.

    Returns a human-readable diagnostic string on mismatch, or `None` if
    consistent.
    """
    try:
        raw_canonical_value = resolution.field_pointer.lookup(canonical_subject_snapshot)
    except KeyError, IndexError, TypeError:
        raw_canonical_value = None

    if resolution.canonical_value_snapshot is None:
        if raw_canonical_value is not None:
            return (
                "resolution has a null canonical_value_snapshot but the durable canonical "
                f"subject has non-null value {raw_canonical_value!r} at "
                f"{resolution.field_pointer.raw}"
            )
        return None

    if raw_canonical_value is None:
        return (
            f"resolution asserts canonical_value_snapshot={resolution.canonical_value_snapshot!r} "
            f"but the durable canonical subject has no value at {resolution.field_pointer.raw}"
        )

    try:
        canonical_decimal = Decimal(str(raw_canonical_value))
        snapshot_decimal = decode_canonical_decimal_snapshot(resolution.canonical_value_snapshot)
    except (ArithmeticError, ValueError) as exc:
        return f"could not compare durable canonical value to resolution snapshot: {exc}"

    if canonical_decimal != snapshot_decimal:
        return (
            f"durable canonical value at {resolution.field_pointer.raw} is {canonical_decimal!r} "
            f"but resolution snapshot is {snapshot_decimal!r}"
        )
    return None


def _validate_source_record(source: dict[str, Any], expected_source_id: str) -> str | None:
    """Validate *source* before it is ever passed to `check_source_use` (Finding 9).

    Returns a human-readable diagnostic string on failure, or `None` when the
    record passes both checks:

    1. `source["source_id"]` must equal `expected_source_id` -- the id the
       supporting evidence itself declares. A caller-supplied
       `available_sources` mapping key is never trusted over the record's
       own declared identity; a mismatch means the wrong Source record could
       otherwise silently authorize a resolution.
    2. `source` must validate against `specs/SOURCE_SCHEMA.v0.2.json`. Never
       lets a `jsonschema.ValidationError` escape -- always converted to a
       deterministic rejected-write status by the caller.
    """
    declared_source_id = source.get("source_id")
    if declared_source_id != expected_source_id:
        return (
            f"available_sources entry resolved via source_id {expected_source_id!r} declares "
            f"its own source_id as {declared_source_id!r} -- refusing to trust a mismatched "
            "Source record"
        )
    try:
        jsonschema.validate(instance=source, schema=_load_source_schema())
    except jsonschema.ValidationError as exc:
        return f"source {expected_source_id!r} failed SOURCE_SCHEMA.v0.2 validation: {exc.message}"
    return None


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_field_resolution(
    conn: Any,
    *,
    resolution: FieldResolution,
    expected_current_resolution_id: str | None,
    fetch_canonical_value: FetchCanonicalValue,
    available_sources: dict[str, dict[str, Any]],
) -> FieldResolutionWriteResult:
    """Durably write *resolution* as the new current head iff every accepted
    invariant and admission check passes.

    `resolution.supersedes_resolution_id` must equal
    `expected_current_resolution_id` (Finding 8) -- checked before anything
    else, since it depends on nothing durable.

    `fetch_canonical_value` (required, no default) resolves *resolution*'s
    subject to its durable canonical snapshot; the result is checked against
    `resolution` via `_check_canonical_value_consistency` (REQ-PROV-005) for
    every state, not only resolved ones (Finding 7).

    Evidence existence/subject-field-compatibility/set-relationship checks
    (VAL-PROV-004) always run, regardless of state, using the exact
    considered evidence set. Source-rights admission
    (`SOURCE_RIGHTS_POLICY.v0.1.md`, `check_source_use(..., PRODUCTION_VALUE)`)
    runs only when `resolution.state` is `resolved`/`resolved_with_conflict`
    and only against `supporting_evidence_ids` -- an unresolved state
    (`unknown`/`needs_review`/`conflict`) carries no supporting evidence to
    admit (VAL-PROV-005/007) and is written once its evidence-set invariants
    pass. Each supporting evidence's Source record is bound to its own
    declared `source_id` and schema-validated before `check_source_use` is
    ever called (Finding 9).

    Raises FieldResolutionTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(resolution, FieldResolution):
        raise TypeError(f"resolution must be a FieldResolution, got {type(resolution).__name__}")

    # Checked before any statement runs on *conn* at all: fetch_evidence()
    # below issues plain SELECTs that would otherwise silently leave the
    # connection non-IDLE (psycopg's default autocommit=False mode opens an
    # implicit transaction on the first statement), defeating this exact
    # ownership guarantee if checked any later.
    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise FieldResolutionTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); write_field_resolution() requires an IDLE "
            "connection so it can safely own and commit its own top-level transaction. Call "
            "conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    # Finding 8: a resolution's own declared predecessor must agree with what
    # the caller expects the current head to be. Checked before the advisory
    # lock is even acquired -- a pure comparison of two supplied parameters,
    # nothing durable to consult yet.
    if resolution.supersedes_resolution_id != expected_current_resolution_id:
        return FieldResolutionWriteResult(
            status=FieldResolutionWriteStatus.SUPERSESSION_MISMATCH,
            detail=(
                f"resolution.supersedes_resolution_id={resolution.supersedes_resolution_id!r} "
                f"does not match expected_current_resolution_id={expected_current_resolution_id!r}"
            ),
        )

    subject_kind = resolution.subject.kind.value
    subject_id = resolution.subject.id
    field_pointer = resolution.field_pointer.raw
    lock_key = f"{subject_kind}|{subject_id}|{field_pointer}"

    with conn.transaction(), conn.cursor() as cur:
        # Serializes every concurrent writer for this exact logical subject
        # field -- see module docstring for why an advisory lock is used
        # instead of a row lock. Held for the rest of this transaction, so
        # every read below (including fetch_evidence's own reads) is
        # already serialized against concurrent writers for this subject
        # field.
        cur.execute(_ADVISORY_LOCK, [lock_key])

        considered_ids = sorted(resolution.considered_evidence_ids)
        all_evidence: dict[str, FieldEvidence] = {}
        for evidence_id in considered_ids:
            record = fetch_evidence(conn, evidence_id)
            if record is None:
                return FieldResolutionWriteResult(
                    status=FieldResolutionWriteStatus.EVIDENCE_NOT_FOUND,
                    detail=f"considered evidence id {evidence_id!r} does not exist durably",
                )
            all_evidence[evidence_id] = record

        invariant_errors = validate_resolution_invariants(resolution, all_evidence)
        if invariant_errors:
            return FieldResolutionWriteResult(
                status=FieldResolutionWriteStatus.INVARIANTS_VIOLATED,
                detail="; ".join(invariant_errors),
            )

        # Finding 7: the resolution must agree with the durable canonical
        # subject it claims to qualify -- enforced here, at admission, not
        # only defensively re-checked by Search at read time.
        lookup = fetch_canonical_value(conn, resolution)
        if lookup.status is not CanonicalLookupStatus.FOUND:
            return FieldResolutionWriteResult(
                status=FieldResolutionWriteStatus.CANONICAL_SUBJECT_UNRESOLVABLE,
                detail=(
                    f"fetch_canonical_value could not resolve subject "
                    f"{resolution.subject.kind.value}:{resolution.subject.id} at "
                    f"{field_pointer} to a unique durable canonical snapshot "
                    f"(status={lookup.status.value})"
                ),
            )
        assert lookup.canonical_subject_snapshot is not None  # FOUND guarantees this
        mismatch_detail = _check_canonical_value_consistency(
            resolution, lookup.canonical_subject_snapshot
        )
        if mismatch_detail is not None:
            return FieldResolutionWriteResult(
                status=FieldResolutionWriteStatus.CANONICAL_VALUE_MISMATCH,
                detail=mismatch_detail,
            )

        if resolution.state in (ResolutionState.RESOLVED, ResolutionState.RESOLVED_WITH_CONFLICT):
            for evidence_id in sorted(resolution.supporting_evidence_ids):
                source_id = all_evidence[evidence_id].source_id
                source = available_sources.get(source_id)
                if source is None:
                    return FieldResolutionWriteResult(
                        status=FieldResolutionWriteStatus.SOURCE_NOT_AVAILABLE,
                        detail=(
                            f"supporting evidence {evidence_id!r} references source {source_id!r}, "
                            "which is not among the sources supplied to this admission path"
                        ),
                    )
                invalid_reason = _validate_source_record(source, source_id)
                if invalid_reason is not None:
                    return FieldResolutionWriteResult(
                        status=FieldResolutionWriteStatus.SOURCE_RECORD_INVALID,
                        detail=(
                            f"supporting evidence {evidence_id!r} references source "
                            f"{source_id!r}: {invalid_reason}"
                        ),
                    )
                decision = check_source_use(source, SourceUse.PRODUCTION_VALUE)
                if decision.outcome is not DecisionOutcome.ALLOWED:
                    return FieldResolutionWriteResult(
                        status=FieldResolutionWriteStatus.SOURCE_USE_DENIED,
                        detail=(
                            f"supporting evidence {evidence_id!r} source {source_id!r} "
                            f"production_value use is {decision.outcome.value!r}, "
                            f"reasons={sorted(r.value for r in decision.reasons)}"
                        ),
                    )

        cur.execute(_SELECT_HEAD, [subject_kind, subject_id, field_pointer])
        head_row = cur.fetchone()
        actual_current_id: str | None = head_row[0] if head_row is not None else None

        content_hash = fingerprint_dict(_envelope_dict(resolution))

        cur.execute(_SELECT_RESOLUTION_BY_ID, [resolution.resolution_id])
        existing = cur.fetchone()
        if existing is not None:
            (
                existing_subject_kind,
                existing_subject_id,
                existing_field_pointer,
                existing_supersedes,
                existing_hash,
            ) = existing
            if (
                existing_subject_kind == subject_kind
                and existing_subject_id == subject_id
                and existing_field_pointer == field_pointer
                and existing_supersedes == resolution.supersedes_resolution_id
                and existing_hash == content_hash
            ):
                return FieldResolutionWriteResult(
                    status=FieldResolutionWriteStatus.ALREADY_EXISTS,
                    current_resolution_id=actual_current_id,
                )
            return FieldResolutionWriteResult(
                status=FieldResolutionWriteStatus.CONFLICT, current_resolution_id=actual_current_id
            )

        if expected_current_resolution_id != actual_current_id:
            return FieldResolutionWriteResult(
                status=FieldResolutionWriteStatus.CONFLICT, current_resolution_id=actual_current_id
            )

        canonical_value_snapshot_param = (
            None
            if resolution.canonical_value_snapshot is None
            else json.dumps(resolution.canonical_value_snapshot)
        )
        cur.execute(
            _INSERT_RESOLUTION,
            (
                resolution.resolution_id,
                subject_kind,
                subject_id,
                field_pointer,
                resolution.state.value,
                canonical_value_snapshot_param,
                json.dumps(sorted(resolution.supporting_evidence_ids)),
                json.dumps(sorted(resolution.contradicting_evidence_ids)),
                json.dumps(sorted(resolution.considered_evidence_ids)),
                resolution.resolution_method.value,
                resolution.policy_version,
                resolution.resolver.kind.value,
                resolution.resolver.identifier,
                resolution.resolver.version,
                resolution.resolved_at,
                resolution.supersedes_resolution_id,
                resolution.notes,
                content_hash,
            ),
        )
        if cur.rowcount == 0:
            # Lost the race against a different resolution_id collision --
            # can never be a match for our own subject/field (fully
            # serialized by the advisory lock above), so always CONFLICT.
            return FieldResolutionWriteResult(
                status=FieldResolutionWriteStatus.CONFLICT, current_resolution_id=actual_current_id
            )

        cur.execute(
            _UPSERT_HEAD, (subject_kind, subject_id, field_pointer, resolution.resolution_id)
        )

        status = (
            FieldResolutionWriteStatus.CREATED
            if actual_current_id is None
            else FieldResolutionWriteStatus.REVISED
        )
        return FieldResolutionWriteResult(
            status=status, current_resolution_id=resolution.resolution_id
        )


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_current_field_resolution(
    conn: Any, subject_kind: SubjectKind, subject_id: str, field_pointer: str
) -> FieldResolution | None:
    """Exact typed readback of the current resolution for one subject field.

    Reads the explicit current/head pointer -- never insertion order or a
    timestamp. Returns `None` when no resolution has ever been recorded for
    this subject field.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_CURRENT_RESOLUTION, [subject_kind.value, subject_id, field_pointer])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_resolution(row)


def fetch_field_resolution(conn: Any, resolution_id: str) -> FieldResolution | None:
    """Exact typed readback of one immutable resolution by its own id,
    regardless of whether it is still the current head."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_RESOLUTION_RECORD, [resolution_id])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_resolution(row)


def list_field_resolution_history(
    conn: Any, subject_kind: SubjectKind, subject_id: str, field_pointer: str
) -> list[FieldResolution]:
    """Exact typed readback of the immutable resolution history for one
    subject field. Ordered by `recorded_at` for display/audit convenience
    only; use `fetch_current_field_resolution` to learn which is current."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_HISTORY, [subject_kind.value, subject_id, field_pointer])
        rows = cur.fetchall()
    return [_row_to_resolution(row) for row in rows]
