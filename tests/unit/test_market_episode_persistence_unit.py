"""Unit tests for MarketEpisode persistence contract composition — SLICE-0047.

Tests input-type enforcement and the transaction-ownership guard using a
connection double that raises if `cursor()`/`transaction()` is ever called.
These tests do NOT prove PostgreSQL SQL correctness — that is covered by
tests/persistence/test_market_episode_persistence.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from hullq.domain.market_identity import MarketEpisode, MarketEpisodeId, PhysicalBoatId
from hullq.persistence.market_episode import (
    MarketEpisodeTransactionOwnershipError,
    create_market_episode,
    fetch_market_episode,
)


class _ConnectionMustNotBeTouched:
    """Fails the test if any database-facing method is invoked on it."""

    def cursor(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("connection.cursor() must not be called")

    def transaction(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("connection.transaction() must not be called")


class _FakeConnectionInfo:
    def __init__(self, transaction_status: Any) -> None:
        self.transaction_status = transaction_status


class _NonIdleConnection(_ConnectionMustNotBeTouched):
    """Reports a non-IDLE transaction_status; still fails if cursor()/
    transaction() is ever reached, proving the ownership check runs first."""

    def __init__(self, transaction_status: Any) -> None:
        self.info = _FakeConnectionInfo(transaction_status)


# ---------------------------------------------------------------------------
# Creation accepts only the accepted SLICE-0040 identity types
# ---------------------------------------------------------------------------


def test_create_rejects_a_non_market_episode_value() -> None:
    """A competing plain-string/dict identity must not be interchangeable
    with the accepted MarketEpisode domain object."""
    with pytest.raises(TypeError, match="MarketEpisode"):
        create_market_episode(
            _ConnectionMustNotBeTouched(),
            market_episode="ME-1",  # type: ignore[arg-type]
        )


def test_physical_boat_id_link_accepts_only_the_accepted_physical_boat_id_type() -> None:
    """The required PhysicalBoatId link is enforced by the SLICE-0040
    MarketEpisode domain object itself, not reinvented here."""
    with pytest.raises(TypeError):
        MarketEpisode(id=MarketEpisodeId("ME-1"), physical_boat_id="PB-1")  # type: ignore[arg-type]


def test_readback_rejects_a_plain_string_market_episode_identity() -> None:
    with pytest.raises(TypeError, match="MarketEpisodeId"):
        fetch_market_episode(_ConnectionMustNotBeTouched(), "ME-1")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Transaction ownership: creation must refuse to write unless it can safely
# own and commit its own top-level transaction.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("non_idle_status", ["ACTIVE", "INTRANS", "INERROR"])
def test_create_rejects_a_non_idle_connection_before_any_write(non_idle_status: str) -> None:
    """If *conn* already has an open transaction, psycopg's conn.transaction()
    degrades to a nested SAVEPOINT rather than an independently committed
    top-level transaction, so a CREATED result could be returned for a row
    that is not actually durable. create_market_episode must fail closed
    before touching cursor()/transaction() at all — proven here by the fact
    that _NonIdleConnection raises AssertionError if either is reached."""
    from psycopg.pq import TransactionStatus

    conn = _NonIdleConnection(TransactionStatus[non_idle_status])

    with pytest.raises(MarketEpisodeTransactionOwnershipError):
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId("ME-1"), physical_boat_id=PhysicalBoatId("PB-1")
            ),
        )


def test_create_accepts_an_idle_connection_marker() -> None:
    """Sanity check that IDLE is the only status the ownership guard accepts
    -- reaching the real cursor()/transaction() calls (which
    _ConnectionMustNotBeTouched forbids) proves the guard let it through."""
    from psycopg.pq import TransactionStatus

    conn = _NonIdleConnection(TransactionStatus.IDLE)

    with pytest.raises(AssertionError, match="transaction"):
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId("ME-1"), physical_boat_id=PhysicalBoatId("PB-1")
            ),
        )


# ---------------------------------------------------------------------------
# Result-type invariants
# ---------------------------------------------------------------------------


def test_market_episode_domain_object_rejects_a_plain_string_physical_boat_id() -> None:
    """Equal raw text across PhysicalBoatId/MarketEpisodeId must not be
    interchangeable -- this is proven at the domain layer and relied on here
    so persistence never has to re-derive it."""
    with pytest.raises(TypeError):
        MarketEpisode(
            id=MarketEpisodeId("ME-1"),
            physical_boat_id=MarketEpisodeId("ME-1"),  # type: ignore[arg-type]
        )


def test_physical_boat_id_value_round_trips_through_domain_object() -> None:
    episode = MarketEpisode(id=MarketEpisodeId("ME-1"), physical_boat_id=PhysicalBoatId("PB-1"))
    assert episode.physical_boat_id == PhysicalBoatId("PB-1")
