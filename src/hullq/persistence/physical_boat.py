"""Durable PhysicalBoat identity persistence — SLICE-0046.

Given an explicit caller-supplied `PhysicalBoatId`, durably create and read
the smallest accepted PhysicalBoat identity envelope defined by the accepted
SLICE-0040 `hullq.domain.market_identity.PhysicalBoat` value object:

    PhysicalBoatId
    optional BoatDesignRef
    created_at (server-generated)

A PhysicalBoat is global real-yacht identity, never an Organization-owned
listing resource: no publishing/creator/broker/seller identity is attached
here. An optional `BoatDesignRef` is enforced against the existing
`canonical_boat_designs(id)` authority via a real foreign key; it is never
mutated once a PhysicalBoatId is created (there is no UPDATE path), and
sharing one BoatDesignRef across many PhysicalBoatIds is always valid (no
uniqueness constraint on the design reference). No MarketEpisode/listing
attachment and no SLICE-0044 `PHYSICAL_BOAT` marketplace fact field is
persisted or projected by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import BoatDesignRef, PhysicalBoat, PhysicalBoatId

__all__ = [
    "PhysicalBoatCreationResult",
    "PhysicalBoatCreationStatus",
    "PhysicalBoatRecord",
    "PhysicalBoatTransactionOwnershipError",
    "create_physical_boat",
    "fetch_physical_boat",
]


class PhysicalBoatTransactionOwnershipError(RuntimeError):
    """create_physical_boat cannot safely own a top-level transaction on *conn*.

    Mirrors `hullq.persistence.native_listing.NativeListingTransactionOwnershipError`:
    a CREATED result must always mean the PhysicalBoat row is already durably
    committed independent of later caller action. That guarantee only holds
    when *conn* is IDLE (no transaction already open), since psycopg's
    ``conn.transaction()`` otherwise silently degrades to a nested SAVEPOINT.
    Call ``conn.commit()``/``conn.rollback()`` first, or pass a freshly
    opened connection.
    """


class PhysicalBoatCreationStatus(StrEnum):
    """Mechanically distinct creation outcomes. Never a bare boolean."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    DESIGN_NOT_FOUND = "design_not_found"


@dataclass(frozen=True)
class PhysicalBoatCreationResult:
    """Deterministic result of one create_physical_boat call."""

    status: PhysicalBoatCreationStatus


@dataclass(frozen=True)
class PhysicalBoatRecord:
    """Exact typed readback of one persisted PhysicalBoat.

    Carries only the PhysicalBoat identity link and its server-generated
    creation timestamp — never a joined/projected BoatDesign baseline fact.
    """

    physical_boat: PhysicalBoat
    created_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_INSERT_PHYSICAL_BOAT = """
INSERT INTO physical_boats (physical_boat_id, boat_design_ref)
VALUES (%s, %s)
ON CONFLICT (physical_boat_id) DO NOTHING
"""

_SELECT_BOAT_DESIGN_REF = "SELECT boat_design_ref FROM physical_boats WHERE physical_boat_id = %s"

_SELECT_PHYSICAL_BOAT = (
    "SELECT physical_boat_id, boat_design_ref, created_at "
    "FROM physical_boats WHERE physical_boat_id = %s"
)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def create_physical_boat(conn: Any, *, physical_boat: PhysicalBoat) -> PhysicalBoatCreationResult:
    """Durably create *physical_boat* iff its PhysicalBoatId is unoccupied.

    Race-safe: uses ``INSERT ... ON CONFLICT (physical_boat_id) DO NOTHING``,
    never a check-then-insert window. When the PhysicalBoatId is already
    occupied, the result is classified from an explicit follow-up read of
    the exact durable stored nullable ``boat_design_ref`` — never from the
    requested value alone and never from a hash — so a same-ID/same-envelope
    retry is ALREADY_EXISTS and a same-ID/different-envelope retry is
    CONFLICT, including when the newly requested BoatDesignRef is itself
    unknown to ``canonical_boat_designs``: PostgreSQL's ON CONFLICT arbiter
    check for an already-occupied PhysicalBoatId is resolved before the
    foreign-key constraint on the (unused) proposed row would ever be
    checked, so that case can never surface as a foreign-key violation.

    A *new* PhysicalBoatId with a BoatDesignRef unknown to
    ``canonical_boat_designs`` does reach the real foreign-key constraint and
    fails closed as DESIGN_NOT_FOUND, creating no PhysicalBoat row and no
    placeholder canonical BoatDesign row.

    Raises PhysicalBoatTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(physical_boat, PhysicalBoat):
        raise TypeError(f"physical_boat must be a PhysicalBoat, got {type(physical_boat).__name__}")

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise PhysicalBoatTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); create_physical_boat() requires an "
            "IDLE connection so it can safely own and commit its own top-level "
            "transaction. Call conn.commit()/conn.rollback() first, or pass a freshly "
            "opened connection."
        )

    requested_design_ref = (
        physical_boat.boat_design_ref.value if physical_boat.boat_design_ref is not None else None
    )

    from psycopg.errors import ForeignKeyViolation  # deferred: no module-level psycopg dependency

    try:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(_INSERT_PHYSICAL_BOAT, (physical_boat.id.value, requested_design_ref))
            if cur.rowcount > 0:
                return PhysicalBoatCreationResult(status=PhysicalBoatCreationStatus.CREATED)

            # PhysicalBoatId already occupied: classify purely from the
            # durable stored row, never from the requested value alone.
            cur.execute(_SELECT_BOAT_DESIGN_REF, [physical_boat.id.value])
            row = cur.fetchone()
            stored_design_ref = row[0]
    except ForeignKeyViolation:
        return PhysicalBoatCreationResult(status=PhysicalBoatCreationStatus.DESIGN_NOT_FOUND)

    if stored_design_ref == requested_design_ref:
        return PhysicalBoatCreationResult(status=PhysicalBoatCreationStatus.ALREADY_EXISTS)
    return PhysicalBoatCreationResult(status=PhysicalBoatCreationStatus.CONFLICT)


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_physical_boat(conn: Any, physical_boat_id: PhysicalBoatId) -> PhysicalBoatRecord | None:
    """Exact typed readback by PhysicalBoatId, or None if not found.

    Returns only the BoatDesignRef link itself — never joins/projects
    BoatDesign baseline/configuration data into PhysicalBoat truth.
    """
    if not isinstance(physical_boat_id, PhysicalBoatId):
        raise TypeError(
            f"physical_boat_id must be a PhysicalBoatId, got {type(physical_boat_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_PHYSICAL_BOAT, [physical_boat_id.value])
        row = cur.fetchone()
    if row is None:
        return None

    id_value, boat_design_ref_value, created_at = row
    return PhysicalBoatRecord(
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(id_value),
            boat_design_ref=(
                BoatDesignRef(boat_design_ref_value) if boat_design_ref_value is not None else None
            ),
        ),
        created_at=created_at,
    )
