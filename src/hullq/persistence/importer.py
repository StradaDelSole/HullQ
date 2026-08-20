"""Deterministic transactional ResearchEvidenceBundle importer — SLICE-0013.

Entry point: import_research_evidence_bundle(conn, bundle) -> ImportResult

Importer guarantees:
- bundle must already be valid (caller is responsible for schema validation);
- one deterministic content fingerprint per bundle, observation and evidence;
- one database transaction; rollback on any conflict or persistence error;
- idempotent: exact repeated import returns ALREADY_IMPORTED, no duplicates;
- fail-closed: same identity with different content returns CONFLICT;
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
FROM bundle_promoted_evidence
WHERE evidence_id = %s AND bundle_id = %s AND bundle_version = %s
"""

_INSERT_EVIDENCE = """
INSERT INTO bundle_promoted_evidence (
    evidence_id, bundle_id, bundle_version, content_hash,
    subject_kind, subject_id, field_pointer, source_id,
    source_locator, raw_observation, normalized_candidate,
    evidence_type, claim_semantics, applicability,
    producer, research_context, observed_at, confidence,
    supersedes_evidence_id, notes
) VALUES (
    %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s
)
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
    """Return a terminal ImportResult if the bundle already exists, else None."""
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
    """Insert one observation row; raise PersistenceConflictError on hash mismatch."""
    cur.execute(_SELECT_OBSERVATION_HASH, [obs.observation_id])
    existing = cur.fetchone()
    if existing is not None:
        if existing[0] != obs_hash:
            raise PersistenceConflictError(
                f"Observation {obs.observation_id!r} already persisted "
                "with a different semantic content hash."
            )
        # Same hash → reuse the existing row without inserting.
        return
    params = observation_row_params(obs, obs_hash)
    from psycopg.types.json import Jsonb

    adapted = [Jsonb(p) if isinstance(p, dict) else p for p in params]
    cur.execute(_INSERT_OBSERVATION, adapted)


def _insert_evidence(
    cur: Any,
    ev: FieldEvidenceV3,
    bundle: ResearchEvidenceBundle,
    ev_hash: str,
) -> None:
    """Insert one promoted evidence row; raise PersistenceConflictError on hash mismatch."""
    cur.execute(_SELECT_EVIDENCE_HASH, [ev.evidence_id, bundle.bundle_id, bundle.bundle_version])
    existing = cur.fetchone()
    if existing is not None:
        if existing[0] != ev_hash:
            raise PersistenceConflictError(
                f"Promoted evidence {ev.evidence_id!r} in bundle "
                f"({bundle.bundle_id!r}, {bundle.bundle_version!r}) "
                "already persisted with a different content hash."
            )
        return
    params = evidence_row_params(ev, bundle, ev_hash)
    from psycopg.types.json import Jsonb

    adapted = [Jsonb(p) if isinstance(p, dict) else p for p in params]
    cur.execute(_INSERT_EVIDENCE, adapted)


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

    Does not perform identity resolution, automatic promotion, or FieldResolution.
    Does not modify existing immutable records.
    """
    from psycopg.types.json import Jsonb

    bundle_hash = fingerprint_bundle(bundle)

    # Attempt atomic import inside a single transaction.
    try:
        with conn.transaction(), conn.cursor() as cur:
            # 1. Check existing bundle.
            early = _check_existing_bundle(
                cur, bundle.bundle_id, bundle.bundle_version, bundle_hash
            )
            if early is not None:
                # ALREADY_IMPORTED or CONFLICT detected before any writes.
                # Raise to abort the transaction block cleanly.
                raise _EarlyReturn(early)

            # 2. Insert bundle row.
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

            # 3. Observations: insert (or verify existing) + membership.
            for obs in bundle.observations:
                obs_hash = fingerprint_observation(obs)
                _insert_observation(cur, obs, obs_hash)
                cur.execute(
                    _INSERT_MEMBERSHIP,
                    [bundle.bundle_id, bundle.bundle_version, obs.observation_id],
                )

            # 4. Unresolved findings.
            for finding in bundle.unresolved_findings:
                params = finding_row_params(finding, bundle)
                adapted = [Jsonb(p) if isinstance(p, list) else p for p in params]
                cur.execute(_INSERT_FINDING, adapted)

            # 5. Reference crosschecks (structurally outside evidence).
            for cc in bundle.reference_crosschecks:
                cur.execute(_INSERT_CROSSCHECK, list(crosscheck_row_params(cc, bundle)))

            # 6. Promoted FieldEvidence v0.3 (optional).
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
