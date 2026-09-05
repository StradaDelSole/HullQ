"""Durable MarketEpisode identity persistence — SLICE-0047.

Given an explicit caller-supplied `MarketEpisodeId`, durably create and read
the smallest accepted MarketEpisode identity envelope defined by the
accepted SLICE-0040 `hullq.domain.market_identity.MarketEpisode` value
object:

    MarketEpisodeId
    PhysicalBoatId (required, enforced via real foreign key)
    created_at (server-generated)

A MarketEpisode identifies one sale/market episode for exactly one durable
`PhysicalBoat`; multiple distinct MarketEpisodeIds may reference the same
PhysicalBoatId (a later sale episode is not an identity conflict). No
lifecycle/status, freshness, seller/broker ownership, price, source
observation, continuity confidence or dedup/merge metadata is persisted or
projected by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import MarketEpisode, MarketEpisodeId, PhysicalBoatId

__all__ = [
    "MarketEpisodeCreationResult",
    "MarketEpisodeCreationStatus",
    "MarketEpisodeRecord",
    "MarketEpisodeTransactionOwnershipError",
    "create_market_episode",
    "fetch_market_episode",
]


class MarketEpisodeTransactionOwnershipError(RuntimeError):
    """create_market_episode cannot safely own a top-level transaction on *conn*.

    Mirrors `hullq.persistence.physical_boat.PhysicalBoatTransactionOwnershipError`:
    a CREATED result must always mean the MarketEpisode row is already
    durably committed independent of later caller action. That guarantee
    only holds when *conn* is IDLE (no transaction already open), since
    psycopg's ``conn.transaction()`` otherwise silently degrades to a nested
    SAVEPOINT. Call ``conn.commit()``/``conn.rollback()`` first, or pass a
    freshly opened connection.
    """


class MarketEpisodeCreationStatus(StrEnum):
    """Mechanically distinct creation outcomes. Never a bare boolean."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    PHYSICAL_BOAT_NOT_FOUND = "physical_boat_not_found"


@dataclass(frozen=True)
class MarketEpisodeCreationResult:
    """Deterministic result of one create_market_episode call."""

    status: MarketEpisodeCreationStatus


@dataclass(frozen=True)
class MarketEpisodeRecord:
    """Exact typed readback of one persisted MarketEpisode.

    Carries only the MarketEpisode identity link and its server-generated
    creation timestamp — never a joined/projected PhysicalBoat/BoatDesign/
    listing/lifecycle fact.
    """

    market_episode: MarketEpisode
    created_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_INSERT_MARKET_EPISODE = """
INSERT INTO market_episodes (market_episode_id, physical_boat_id)
VALUES (%s, %s)
ON CONFLICT (market_episode_id) DO NOTHING
"""

_SELECT_PHYSICAL_BOAT_ID = (
    "SELECT physical_boat_id FROM market_episodes WHERE market_episode_id = %s"
)

_SELECT_MARKET_EPISODE = (
    "SELECT market_episode_id, physical_boat_id, created_at "
    "FROM market_episodes WHERE market_episode_id = %s"
)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def create_market_episode(
    conn: Any, *, market_episode: MarketEpisode
) -> MarketEpisodeCreationResult:
    """Durably create *market_episode* iff its MarketEpisodeId is unoccupied.

    Race-safe: uses ``INSERT ... ON CONFLICT (market_episode_id) DO NOTHING``,
    never a check-then-insert window. When the MarketEpisodeId is already
    occupied, the result is classified from an explicit follow-up read of
    the exact durable stored PhysicalBoatId — never from the requested value
    alone — so a same-ID/same-PhysicalBoatId retry is ALREADY_EXISTS and a
    same-ID/different-PhysicalBoatId retry is CONFLICT, including when the
    newly requested PhysicalBoatId does not itself exist: PostgreSQL's ON
    CONFLICT arbiter check for an already-occupied MarketEpisodeId is
    resolved before the foreign-key constraint on the (unused) proposed row
    would ever be checked, so that case can never surface as a foreign-key
    violation.

    A *new* MarketEpisodeId with a PhysicalBoatId unknown to
    ``physical_boats`` does reach the real foreign-key constraint and fails
    closed as PHYSICAL_BOAT_NOT_FOUND, creating no MarketEpisode row.

    Raises MarketEpisodeTransactionOwnershipError, before any write is
    attempted, if *conn* already has an open transaction.
    """
    if not isinstance(market_episode, MarketEpisode):
        raise TypeError(
            f"market_episode must be a MarketEpisode, got {type(market_episode).__name__}"
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise MarketEpisodeTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); create_market_episode() requires an "
            "IDLE connection so it can safely own and commit its own top-level "
            "transaction. Call conn.commit()/conn.rollback() first, or pass a freshly "
            "opened connection."
        )

    requested_physical_boat_id = market_episode.physical_boat_id.value

    from psycopg.errors import ForeignKeyViolation  # deferred: no module-level psycopg dependency

    try:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(
                _INSERT_MARKET_EPISODE,
                (market_episode.id.value, requested_physical_boat_id),
            )
            if cur.rowcount > 0:
                return MarketEpisodeCreationResult(status=MarketEpisodeCreationStatus.CREATED)

            # MarketEpisodeId already occupied: classify purely from the
            # durable stored row, never from the requested value alone.
            cur.execute(_SELECT_PHYSICAL_BOAT_ID, [market_episode.id.value])
            row = cur.fetchone()
            stored_physical_boat_id = row[0]
    except ForeignKeyViolation:
        return MarketEpisodeCreationResult(
            status=MarketEpisodeCreationStatus.PHYSICAL_BOAT_NOT_FOUND
        )

    if stored_physical_boat_id == requested_physical_boat_id:
        return MarketEpisodeCreationResult(status=MarketEpisodeCreationStatus.ALREADY_EXISTS)
    return MarketEpisodeCreationResult(status=MarketEpisodeCreationStatus.CONFLICT)


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_market_episode(
    conn: Any, market_episode_id: MarketEpisodeId
) -> MarketEpisodeRecord | None:
    """Exact typed readback by MarketEpisodeId, or None if not found.

    Returns only the PhysicalBoatId link itself — never joins/projects
    PhysicalBoat/BoatDesign baseline data or listing/lifecycle facts into
    MarketEpisode truth.
    """
    if not isinstance(market_episode_id, MarketEpisodeId):
        raise TypeError(
            f"market_episode_id must be a MarketEpisodeId, got {type(market_episode_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_MARKET_EPISODE, [market_episode_id.value])
        row = cur.fetchone()
    if row is None:
        return None

    id_value, physical_boat_id_value, created_at = row
    return MarketEpisodeRecord(
        market_episode=MarketEpisode(
            id=MarketEpisodeId(id_value),
            physical_boat_id=PhysicalBoatId(physical_boat_id_value),
        ),
        created_at=created_at,
    )
