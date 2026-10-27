"""Durable BoatDesign category assertion persistence -- SLICE-0091.

Gives `hullq.domain.vessel_category.DesignVesselCategoryAssertion` an
immutable-revision + explicit-current-head home, mirroring
`hullq.persistence.physical_boat_claims`'s proven shape (and, at a smaller
scope, `hullq.persistence.field_resolution`'s). Deliberately does **not**
reuse the generalized `hullq.domain.provenance.FieldResolution`/
`hullq.persistence.field_resolution` kernel: that kernel's job is
source-rights-gated admission of physical/technical BoatDesign facts
sourced from external research evidence, and requires the asserted value to
already durably exist elsewhere (`canonical_boat_designs.baseline`) for its
write-time canonical-consistency check. A BoatDesign's Sail/Power/
Motorsailer *category* is a type/admission foundation, not a physical fact
with an external-evidence-quality gate -- introducing that entanglement
here would be a second truth kernel wearing the first one's clothes, not a
reuse of it. This module is instead a small, single-purpose revision+head
table scoped to exactly one field, reusing only the proven *shape*
(immutable append-only revisions, an explicit current-head pointer, a
content-hash idempotency envelope, a locked parent row for concurrency)
that every other revision table in this codebase already uses.

`canonical_boat_designs` is a real pre-existing parent row for every
BoatDesign, unlike `FieldResolution`'s `subject_kind`-polymorphic subject --
so, exactly like `hullq.persistence.physical_boat_claims`, this module locks
that parent row (`SELECT ... FOR UPDATE`) for the duration of the write
transaction rather than taking a PostgreSQL advisory lock.

No source-rights/evidence-quality admission (as `FieldResolution` performs
for externally-sourced physical facts) is performed here -- category is a
type/admission foundation, not a physical fact with a source-rights gate.

## Admission secret vs. issuer metadata (amendment review Finding G)

Amendment review Finding D first closed the "any caller, any issuer" gap by
checking `issuer` against a fixed allowlist constant -- but Finding G then
observed that the allowlisted *value* was itself just an ordinary string
literal inside this publicly importable module: any caller could read it
from source and trivially supply it, so it was not a real authorization
boundary, only a typo/accident guard. `issuer`
(`hullq.domain.provenance.ResolverMetadata`, the same type
`FieldResolution.resolver` already uses) is retained as audit/provenance
metadata -- *who/what claims to have asserted this* -- but it is no longer
what decides authorization.

The actual admission gate is now `admission_secret`: a caller-supplied
string compared, in constant time (`hmac.compare_digest`), against the
value of the `HULLQ_CATALOG_ADMISSION_SECRET` environment variable. This
mirrors the exact pattern this codebase already uses for every other
capability only a privileged backend process should hold (e.g.
`HULLQ_PREVIEW_SIGNING_SECRET`, `HULLQ_SESSION_SIGNING_SECRET`): the value
that actually grants the capability lives in deployment configuration, not
in source code that any importer of this module can read. An unset or
empty environment variable fails every write closed (there is deliberately
no default/placeholder secret that would silently authorize every caller);
a caller-supplied secret that does not match fails closed the same way.
Neither case touches any row. This is still a single bounded secret
comparison -- not a generalized actor/rights registry, not a reuse of
`FieldResolution`'s source-rights machinery, and it invents no third-party
rights. A genuinely stronger boundary (e.g. a dedicated authenticated
catalog-admission service/role) remains a future decision, not silently
assumed here.
"""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Final

from hullq.domain.physical_boat_claims import AssertionKind, VesselCategory
from hullq.domain.provenance import ResolverKind, ResolverMetadata
from hullq.domain.vessel_category import (
    BoatDesignCategoryAssertionId,
    DesignVesselCategoryAssertion,
)
from hullq.persistence.fingerprint import fingerprint_dict

__all__ = [
    "CATALOG_ADMISSION_SECRET_ENV_VAR",
    "BoatDesignCategoryAssertionRecord",
    "BoatDesignCategoryAssertionWriteResult",
    "BoatDesignCategoryAssertionWriteStatus",
    "BoatDesignCategoryTransactionOwnershipError",
    "fetch_boat_design_category_assertion",
    "fetch_current_boat_design_category_assertion",
    "list_boat_design_category_assertion_revisions",
    "write_boat_design_category_assertion",
]

#: The deployment-configuration secret that actually authorizes a design
#: category write -- amendment Finding G. Never hardcoded/defaulted in
#: source; absent/empty means no caller can ever be admitted, fail closed.
CATALOG_ADMISSION_SECRET_ENV_VAR: Final = "HULLQ_CATALOG_ADMISSION_SECRET"


def _admission_secret_is_valid(admission_secret: str) -> bool:
    configured = os.environ.get(CATALOG_ADMISSION_SECRET_ENV_VAR, "")
    if not configured:
        # Fail closed: a deployment that has never configured a real
        # catalog-admission secret admits nobody -- never treat an empty/
        # unset value as a wildcard or default-allow.
        return False
    if not isinstance(admission_secret, str) or not admission_secret:
        return False
    return hmac.compare_digest(admission_secret.encode("utf-8"), configured.encode("utf-8"))


class BoatDesignCategoryTransactionOwnershipError(RuntimeError):
    """write_boat_design_category_assertion cannot safely own a top-level
    transaction on *conn*.

    Mirrors `hullq.persistence.physical_boat_claims.PhysicalBoatClaimTransactionOwnershipError`:
    a CREATED/REVISED result must always mean the new current assertion is
    already durably committed, independent of later caller action. Requires
    an IDLE connection. Call ``conn.commit()``/``conn.rollback()`` first, or
    pass a freshly opened connection.
    """


class BoatDesignCategoryAssertionWriteStatus(StrEnum):
    """Mechanically distinct write outcomes. Never a bare boolean."""

    CREATED = "created"
    REVISED = "revised"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    BOAT_DESIGN_NOT_FOUND = "boat_design_not_found"
    ADMISSION_NOT_AUTHORIZED = "admission_not_authorized"


_STATUSES_REQUIRING_CURRENT = frozenset(
    {
        BoatDesignCategoryAssertionWriteStatus.CREATED,
        BoatDesignCategoryAssertionWriteStatus.REVISED,
        BoatDesignCategoryAssertionWriteStatus.ALREADY_EXISTS,
    }
)
_STATUSES_FORBIDDING_CURRENT = frozenset(
    {
        BoatDesignCategoryAssertionWriteStatus.BOAT_DESIGN_NOT_FOUND,
        BoatDesignCategoryAssertionWriteStatus.ADMISSION_NOT_AUTHORIZED,
    }
)


@dataclass(frozen=True)
class BoatDesignCategoryAssertionWriteResult:
    """Deterministic result of one write_boat_design_category_assertion call."""

    status: BoatDesignCategoryAssertionWriteStatus
    current_assertion_id: BoatDesignCategoryAssertionId | None = None

    def __post_init__(self) -> None:
        if self.status in _STATUSES_REQUIRING_CURRENT and self.current_assertion_id is None:
            raise ValueError(
                f"A {self.status.value.upper()} write result must carry current_assertion_id"
            )
        if self.status in _STATUSES_FORBIDDING_CURRENT and self.current_assertion_id is not None:
            raise ValueError(
                f"A {self.status.value.upper()} write result must not carry current_assertion_id"
            )


@dataclass(frozen=True)
class BoatDesignCategoryAssertionRecord:
    """Exact typed readback of one persisted BoatDesign category assertion."""

    assertion_id: BoatDesignCategoryAssertionId
    boat_design_id: str
    assertion: DesignVesselCategoryAssertion
    issuer: ResolverMetadata
    previous_assertion_id: BoatDesignCategoryAssertionId | None
    recorded_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SELECT_AND_LOCK_BOAT_DESIGN = "SELECT id FROM canonical_boat_designs WHERE id = %s FOR UPDATE"

_SELECT_HEAD = (
    "SELECT current_assertion_id FROM boat_design_category_assertion_heads "
    "WHERE boat_design_id = %s"
)

_SELECT_ASSERTION_BY_ID = (
    "SELECT boat_design_id, previous_assertion_id, content_hash "
    "FROM boat_design_category_assertions WHERE assertion_id = %s"
)

_INSERT_ASSERTION = """
INSERT INTO boat_design_category_assertions (
    assertion_id, boat_design_id, assertion_kind, category_value,
    issuer_kind, issuer_identifier, issuer_version,
    previous_assertion_id, content_hash
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (assertion_id) DO NOTHING
"""

_UPSERT_HEAD = """
INSERT INTO boat_design_category_assertion_heads (
    boat_design_id, current_assertion_id
) VALUES (%s, %s)
ON CONFLICT (boat_design_id)
DO UPDATE SET current_assertion_id = EXCLUDED.current_assertion_id,
              updated_at = NOW()
"""

_ASSERTION_COLUMNS = """
    a.assertion_id, a.boat_design_id, a.assertion_kind, a.category_value,
    a.issuer_kind, a.issuer_identifier, a.issuer_version,
    a.previous_assertion_id, a.recorded_at
"""

_SELECT_CURRENT_ASSERTION = f"""
SELECT {_ASSERTION_COLUMNS}
FROM boat_design_category_assertion_heads h
JOIN boat_design_category_assertions a ON a.assertion_id = h.current_assertion_id
WHERE h.boat_design_id = %s
"""

_SELECT_ASSERTION_RECORD = f"""
SELECT {_ASSERTION_COLUMNS} FROM boat_design_category_assertions a WHERE a.assertion_id = %s
"""

_SELECT_HISTORY = f"""
SELECT {_ASSERTION_COLUMNS} FROM boat_design_category_assertions a
WHERE a.boat_design_id = %s
ORDER BY a.recorded_at ASC, a.assertion_id ASC
"""


def _envelope_dict(
    boat_design_id: str, assertion: DesignVesselCategoryAssertion, issuer: ResolverMetadata
) -> dict[str, Any]:
    return {
        "boat_design_id": boat_design_id,
        "assertion_kind": assertion.assertion_kind.value,
        "category_value": assertion.value.value if assertion.value is not None else None,
        "issuer_kind": issuer.kind.value,
        "issuer_identifier": issuer.identifier,
        "issuer_version": issuer.version,
    }


def _row_to_record(row: tuple[Any, ...]) -> BoatDesignCategoryAssertionRecord:
    (
        assertion_id,
        boat_design_id,
        assertion_kind,
        category_value,
        issuer_kind,
        issuer_identifier,
        issuer_version,
        previous_assertion_id,
        recorded_at,
    ) = row
    return BoatDesignCategoryAssertionRecord(
        assertion_id=BoatDesignCategoryAssertionId(assertion_id),
        boat_design_id=boat_design_id,
        assertion=DesignVesselCategoryAssertion(
            assertion_kind=AssertionKind(assertion_kind),
            value=VesselCategory(category_value) if category_value is not None else None,
        ),
        issuer=ResolverMetadata(
            kind=ResolverKind(issuer_kind), identifier=issuer_identifier, version=issuer_version
        ),
        previous_assertion_id=(
            BoatDesignCategoryAssertionId(previous_assertion_id)
            if previous_assertion_id is not None
            else None
        ),
        recorded_at=recorded_at,
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_boat_design_category_assertion(
    conn: Any,
    *,
    boat_design_id: str,
    assertion_id: BoatDesignCategoryAssertionId,
    expected_current_assertion_id: BoatDesignCategoryAssertionId | None,
    assertion: DesignVesselCategoryAssertion,
    issuer: ResolverMetadata,
    admission_secret: str,
) -> BoatDesignCategoryAssertionWriteResult:
    """Durably write *assertion* as the new current head for *boat_design_id*
    iff the BoatDesign exists, *admission_secret* is authorized (see this
    module's docstring, amendment Finding G), and the expected predecessor
    matches the real durable current head.

    *issuer* is retained as audit/provenance metadata only -- it does not
    decide authorization; see this module's docstring for why a
    self-declared identifier cannot be a real authorization boundary.

    Immutable-revision + explicit-current-head shape, identical idempotency
    rule to `hullq.persistence.physical_boat_claims.write_physical_boat_claim_revision_row`:
    a client-supplied *assertion_id* that already exists resolves
    deterministically against the full immutable envelope (same
    `boat_design_id`, same recorded predecessor, identical content) as
    `ALREADY_EXISTS`; any difference is `CONFLICT`. Neither ever silently
    overwrites or re-promotes a prior assertion -- a legitimate category
    change (including a retraction back to `UNKNOWN`) requires a new,
    explicitly superseding assertion.

    Raises BoatDesignCategoryTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(assertion_id, BoatDesignCategoryAssertionId):
        raise TypeError(
            f"assertion_id must be a BoatDesignCategoryAssertionId, got {type(assertion_id).__name__}"
        )
    if expected_current_assertion_id is not None and not isinstance(
        expected_current_assertion_id, BoatDesignCategoryAssertionId
    ):
        raise TypeError(
            "expected_current_assertion_id must be a BoatDesignCategoryAssertionId or None, got "
            f"{type(expected_current_assertion_id).__name__}"
        )
    if not isinstance(assertion, DesignVesselCategoryAssertion):
        raise TypeError(
            f"assertion must be a DesignVesselCategoryAssertion, got {type(assertion).__name__}"
        )
    if not isinstance(issuer, ResolverMetadata):
        raise TypeError(f"issuer must be a ResolverMetadata, got {type(issuer).__name__}")

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise BoatDesignCategoryTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); write_boat_design_category_assertion() "
            "requires an IDLE connection so it can safely own and commit its own top-level "
            "transaction. Call conn.commit()/conn.rollback() first, or pass a freshly opened "
            "connection."
        )

    # Amendment Finding G: checked before any statement runs -- a pure,
    # constant-time secret comparison, nothing durable to consult yet. An
    # unauthorized caller must never reach the lock/insert below, and the
    # BoatDesign row's current state (if any) must be provably untouched.
    if not _admission_secret_is_valid(admission_secret):
        return BoatDesignCategoryAssertionWriteResult(
            status=BoatDesignCategoryAssertionWriteStatus.ADMISSION_NOT_AUTHORIZED
        )

    with conn.transaction(), conn.cursor() as cur:
        cur.execute(_SELECT_AND_LOCK_BOAT_DESIGN, [boat_design_id])
        if cur.fetchone() is None:
            return BoatDesignCategoryAssertionWriteResult(
                status=BoatDesignCategoryAssertionWriteStatus.BOAT_DESIGN_NOT_FOUND
            )

        content_hash = fingerprint_dict(_envelope_dict(boat_design_id, assertion, issuer))

        cur.execute(_SELECT_HEAD, [boat_design_id])
        head_row = cur.fetchone()
        actual_current_id: str | None = head_row[0] if head_row is not None else None

        def _current_wrapped() -> BoatDesignCategoryAssertionId | None:
            return (
                BoatDesignCategoryAssertionId(actual_current_id)
                if actual_current_id is not None
                else None
            )

        expected_value = (
            expected_current_assertion_id.value
            if expected_current_assertion_id is not None
            else None
        )

        cur.execute(_SELECT_ASSERTION_BY_ID, [assertion_id.value])
        existing = cur.fetchone()
        if existing is not None:
            existing_boat_design_id, existing_previous_id, existing_hash = existing
            if (
                existing_boat_design_id == boat_design_id
                and existing_previous_id == expected_value
                and existing_hash == content_hash
            ):
                return BoatDesignCategoryAssertionWriteResult(
                    status=BoatDesignCategoryAssertionWriteStatus.ALREADY_EXISTS,
                    current_assertion_id=_current_wrapped(),
                )
            return BoatDesignCategoryAssertionWriteResult(
                status=BoatDesignCategoryAssertionWriteStatus.CONFLICT,
                current_assertion_id=_current_wrapped(),
            )

        if expected_value != actual_current_id:
            return BoatDesignCategoryAssertionWriteResult(
                status=BoatDesignCategoryAssertionWriteStatus.CONFLICT,
                current_assertion_id=_current_wrapped(),
            )

        category_value = assertion.value.value if assertion.value is not None else None
        cur.execute(
            _INSERT_ASSERTION,
            (
                assertion_id.value,
                boat_design_id,
                assertion.assertion_kind.value,
                category_value,
                issuer.kind.value,
                issuer.identifier,
                issuer.version,
                actual_current_id,
                content_hash,
            ),
        )
        if cur.rowcount == 0:
            # Lost the race against a different boat_design_id concurrently
            # claiming this exact assertion_id (a global PRIMARY KEY, not
            # scoped to boat_design_id) -- can never be a match for our own
            # boat_design_id (fully serialized by the row lock above), so
            # always CONFLICT.
            return BoatDesignCategoryAssertionWriteResult(
                status=BoatDesignCategoryAssertionWriteStatus.CONFLICT,
                current_assertion_id=_current_wrapped(),
            )

        cur.execute(_UPSERT_HEAD, (boat_design_id, assertion_id.value))

        status = (
            BoatDesignCategoryAssertionWriteStatus.CREATED
            if actual_current_id is None
            else BoatDesignCategoryAssertionWriteStatus.REVISED
        )
        return BoatDesignCategoryAssertionWriteResult(
            status=status, current_assertion_id=assertion_id
        )


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_current_boat_design_category_assertion(
    conn: Any, boat_design_id: str
) -> BoatDesignCategoryAssertionRecord | None:
    """Exact typed readback of the current category assertion for one
    BoatDesign, or `None` when no assertion has ever been recorded.

    Reads the explicit current/head pointer -- never insertion order or a
    timestamp.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_CURRENT_ASSERTION, [boat_design_id])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def fetch_boat_design_category_assertion(
    conn: Any, assertion_id: BoatDesignCategoryAssertionId
) -> BoatDesignCategoryAssertionRecord | None:
    """Exact typed readback of one immutable assertion by its own id,
    regardless of whether it is still the current head."""
    if not isinstance(assertion_id, BoatDesignCategoryAssertionId):
        raise TypeError(
            f"assertion_id must be a BoatDesignCategoryAssertionId, got {type(assertion_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_ASSERTION_RECORD, [assertion_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_boat_design_category_assertion_revisions(
    conn: Any, boat_design_id: str
) -> list[BoatDesignCategoryAssertionRecord]:
    """Exact typed readback of the immutable assertion history for one
    BoatDesign. Ordered by `recorded_at` for display/audit convenience only;
    use `fetch_current_boat_design_category_assertion` to learn which is
    current."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_HISTORY, [boat_design_id])
        rows = cur.fetchall()
    return [_row_to_record(row) for row in rows]
