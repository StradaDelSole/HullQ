"""Deterministic transactional ResearchEvidenceBundle importer — SLICE-0013.

Entry point: import_research_evidence_bundle(conn, bundle) -> ImportResult

Importer guarantees:
- bundle must already be valid (caller is responsible for schema validation);
- one deterministic content fingerprint per bundle, observation and evidence;
- one database transaction; rollback on any conflict or persistence error;
- idempotent: exact repeated import returns ALREADY_IMPORTED, no duplicates;
- fail-closed: same identity with different content returns CONFLICT;
- race-safe: INSERT ... ON CONFLICT ... DO NOTHING eliminates check-then-insert races;
- no identity resolution, no automatic promotion, no FieldResolution.
"""

from __future__ import annotations

from typing import Any

from hullq.domain.provenance import FieldEvidenceV3
from hullq.persistence._types import ImportResult, ImportStatus, PersistenceConflictError
from hullq.persistence.fingerprint import (
    fingerprint_bundle,
    fingerprint_evidence,
    fingerprint_observation,
)
from hullq.persistence.schema import (
    crosscheck_row_params,
    evidence_row_params,
    finding_row_params,
    observation_row_params,
    target_to_jsonb,
)
from hullq.research.observations import ResearchEvidenceBundle, ResearchObservation

# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

_INSERT_BUNDLE = """
INSERT INTO research_bundles
    (bundle_id, bundle_version, content_hash, research_target, research_job_id, activity_id)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (bundle_id, bundle_version) DO NOTHING
"""

_SELECT_BUNDLE_HASH = """
SELECT content_hash
FROM research_bundles
WHERE bundle_id = %s AND bundle_version = %s
"""

_SELECT_OBSERVATION_HASH = """
SELECT content_hash
FROM research_observations
WHERE observation_id = %s
"""

_INSERT_OBSERVATION = """
INSERT INTO research_observations (
    observation_id, content_hash, research_target, source_id,
    source_locator, raw_observation, normalized_candidate,
    evidence_type, claim_semantics, applicability,
    producer, research_context, observed_at, confidence,
    supersedes_observation_id, intended_subject_kind_hint,
    intended_field_pointer, notes
) VALUES (
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s,
    %s, %s
)
ON CONFLICT (observation_id) DO NOTHING
"""

_INSERT_MEMBERSHIP = """
INSERT INTO bundle_observation_members (bundle_id, bundle_version, observation_id)
VALUES (%s, %s, %s)
ON CONFLICT DO NOTHING
"""

_INSERT_FINDING = """
INSERT INTO bundle_unresolved_findings
    (finding_id, bundle_id, bundle_version, topic, description, severity, related_observation_ids)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_INSERT_CROSSCHECK = """
INSERT INTO bundle_reference_crosschecks
    (crosscheck_id, bundle_id, bundle_version, reference_source_id, topic_or_field, outcome, notes)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_SELECT_EVIDENCE_HASH = """
SELECT content_hash
FROM research_evidence
WHERE evidence_id = %s
"""

_INSERT_EVIDENCE = """
INSERT INTO research_evidence (
    evidence_id, content_hash,
    subject_kind, subject_id, field_pointer, source_id,
    source_locator, raw_observation, normalized_candidate,
    evidence_type, claim_semantics, applicability,
    producer, research_context, observed_at, confidence,
    supersedes_evidence_id, notes
) VALUES (
    %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s
)
ON CONFLICT (evidence_id) DO NOTHING
"""

_INSERT_EVIDENCE_MEMBERSHIP = """
INSERT INTO bundle_evidence_members (bundle_id, bundle_version, evidence_id)
VALUES (%s, %s, %s)
ON CONFLICT DO NOTHING
"""


# ---------------------------------------------------------------------------
# Internal helpers (pure-logic / DB interaction)
# ---------------------------------------------------------------------------


def _check_existing_bundle(
    cur: Any,
    bundle_id: str,
    bundle_version: str,
    content_hash: str,
) -> ImportResult | None:
    """Return a terminal ImportResult if the bundle already exists, else None.

    Called only when the bundle INSERT triggered DO NOTHING (rowcount == 0),
    meaning a row for this (bundle_id, bundle_version) already exists.
    """
    cur.execute(_SELECT_BUNDLE_HASH, [bundle_id, bundle_version])
    row = cur.fetchone()
    if row is None:
        return None
    existing_hash: str = row[0]
    if existing_hash == content_hash:
        return ImportResult(
            status=ImportStatus.ALREADY_IMPORTED,
            bundle_id=bundle_id,
            bundle_version=bundle_version,
            content_hash=content_hash,
        )
    return ImportResult(
        status=ImportStatus.CONFLICT,
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        content_hash=content_hash,
        detail=(
            f"Bundle ({bundle_id!r}, {bundle_version!r}) already persisted "
            f"with a different content hash."
        ),
    )


def _insert_observation(
    cur: Any,
    obs: ResearchObservation,
    obs_hash: str,
) -> None:
    """Race-safe insert of one observation row.

    Uses INSERT ... ON CONFLICT DO NOTHING to avoid check-then-insert races.
    If the row already existed (rowcount == 0), verifies the content hash;
    raises PersistenceConflictError on hash mismatch.
    """
    from psycopg.types.json import Jsonb

    params = observation_row_params(obs, obs_hash)
    adapted = [Jsonb(p) if isinstance(p, dict) else p for p in params]
    cur.execute(_INSERT_OBSERVATION, adapted)
    if cur.rowcount == 0:
        # ON CONFLICT DO NOTHING fired: observation already existed; verify hash.
        cur.execute(_SELECT_OBSERVATION_HASH, [obs.observation_id])
        existing = cur.fetchone()
        if existing is None or existing[0] != obs_hash:
            raise PersistenceConflictError(
                f"Observation {obs.observation_id!r} already persisted "
                "with a different semantic content hash."
            )
        # Same hash: reuse the existing global row without duplicate insert.


def _insert_evidence(
    cur: Any,
    ev: FieldEvidenceV3,
    bundle: ResearchEvidenceBundle,
    ev_hash: str,
) -> None:
    """Race-safe insert of one global evidence row + bundle membership.

    Uses INSERT ... ON CONFLICT DO NOTHING for the global research_evidence row.
    If the evidence already existed (rowcount == 0), verifies the global hash;
    raises PersistenceConflictError on hash mismatch.
    Membership is always recorded (idempotent ON CONFLICT DO NOTHING).
    """
    from psycopg.types.json import Jsonb

    params = evidence_row_params(ev, ev_hash)
    adapted = [Jsonb(p) if isinstance(p, dict) else p for p in params]
    cur.execute(_INSERT_EVIDENCE, adapted)
    if cur.rowcount == 0:
        # ON CONFLICT DO NOTHING fired: evidence already existed; verify global hash.
        cur.execute(_SELECT_EVIDENCE_HASH, [ev.evidence_id])
        existing = cur.fetchone()
        if existing is None or existing[0] != ev_hash:
            raise PersistenceConflictError(
                f"Evidence {ev.evidence_id!r} already persisted "
                "with a different semantic content hash."
            )
        # Same hash: reuse the existing global row.
    # Always add bundle membership (idempotent).
    cur.execute(
        _INSERT_EVIDENCE_MEMBERSHIP, [bundle.bundle_id, bundle.bundle_version, ev.evidence_id]
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def import_research_evidence_bundle(
    conn: Any,
    bundle: ResearchEvidenceBundle,
) -> ImportResult:
    """Atomically import a ResearchEvidenceBundle into PostgreSQL.

    Returns ImportResult with status IMPORTED, ALREADY_IMPORTED, or CONFLICT.

    - IMPORTED: the bundle and all children were persisted successfully.
    - ALREADY_IMPORTED: the exact same (bundle_id, bundle_version, content) was
      already present; the import is a no-op and no duplicates were created.
    - CONFLICT: the same (bundle_id, bundle_version) exists with different content,
      or an observation/evidence identity collision was detected. The full import
      attempt is rolled back.

    All INSERT paths use ON CONFLICT DO NOTHING to eliminate check-then-insert
    races. Concurrent identical imports resolve deterministically without leaking
    raw PostgreSQL unique-violation errors. Conflicting immutable identities fail
    closed as CONFLICT.

    Does not perform identity resolution, automatic promotion, or FieldResolution.
    Does not modify existing immutable records.
    """
    from psycopg.types.json import Jsonb

    bundle_hash = fingerprint_bundle(bundle)

    # Attempt atomic import inside a single transaction.
    try:
        with conn.transaction(), conn.cursor() as cur:
            # 1. Insert bundle row (race-safe: ON CONFLICT DO NOTHING).
            cur.execute(
                _INSERT_BUNDLE,
                [
                    bundle.bundle_id,
                    bundle.bundle_version,
                    bundle_hash,
                    Jsonb(target_to_jsonb(bundle.research_target)),
                    bundle.research_job_id,
                    bundle.activity_id,
                ],
            )
            if cur.rowcount == 0:
                # Another import already committed this (bundle_id, bundle_version).
                # Check whether it is the same content (idempotent) or a conflict.
                early = _check_existing_bundle(
                    cur, bundle.bundle_id, bundle.bundle_version, bundle_hash
                )
                if early is None:
                    raise PersistenceConflictError(
                        f"Bundle ({bundle.bundle_id!r}, {bundle.bundle_version!r}) "
                        "disappeared after insert conflict."
                    )
                raise _EarlyReturn(early)

            # 2. Observations: race-safe insert + membership.
            for obs in bundle.observations:
                obs_hash = fingerprint_observation(obs)
                _insert_observation(cur, obs, obs_hash)
                cur.execute(
                    _INSERT_MEMBERSHIP,
                    [bundle.bundle_id, bundle.bundle_version, obs.observation_id],
                )

            # 3. Unresolved findings.
            for finding in bundle.unresolved_findings:
                params = finding_row_params(finding, bundle)
                adapted = [Jsonb(p) if isinstance(p, list) else p for p in params]
                cur.execute(_INSERT_FINDING, adapted)

            # 4. Reference crosschecks (structurally outside evidence).
            for cc in bundle.reference_crosschecks:
                cur.execute(_INSERT_CROSSCHECK, list(crosscheck_row_params(cc, bundle)))

            # 5. Promoted FieldEvidence v0.3 (global identity; optional).
            for ev in bundle.promoted_evidence:
                ev_hash = fingerprint_evidence(ev)
                _insert_evidence(cur, ev, bundle, ev_hash)

    except _EarlyReturn as exc:
        return exc.result
    except PersistenceConflictError as exc:
        return ImportResult(
            status=ImportStatus.CONFLICT,
            bundle_id=bundle.bundle_id,
            bundle_version=bundle.bundle_version,
            content_hash=bundle_hash,
            detail=str(exc),
        )

    return ImportResult(
        status=ImportStatus.IMPORTED,
        bundle_id=bundle.bundle_id,
        bundle_version=bundle.bundle_version,
        content_hash=bundle_hash,
    )


class _EarlyReturn(Exception):
    """Internal sentinel to exit conn.transaction() before writes without an error."""

    def __init__(self, result: ImportResult) -> None:
        self.result = result
