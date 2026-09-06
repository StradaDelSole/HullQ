"""NativeListing publication lifecycle vocabulary — SLICE-0049.

Defines the exactly-three-state NativeListing publication lifecycle
(``DRAFT``, ``ACTIVE``, ``WITHDRAWN``) and the identity kind for one
immutable, append-only publication-transition record, required by the
accepted SLICE-0049 readiness contract.

Hard invariants preserved by this module and its consumers:

    NativeListing durable creation != publication
    DRAFT != public
    ACTIVE = public
    WITHDRAWN != public
    WITHDRAWN != SOLD
    STALE != WITHDRAWN
    STALE != SOLD
    freshness != lifecycle

Only ``DRAFT -> ACTIVE`` and ``ACTIVE -> WITHDRAWN`` are authorized
transitions; ``WITHDRAWN -> ACTIVE`` (republish) and any other lifecycle
state (``SOLD``, ``ARCHIVED``, freshness/staleness) are out of scope and
intentionally not represented here.

This module contains only pure, frozen value objects/vocabulary — no
persistence, ORM or network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "NativeListingLifecycleState",
    "PublicationTransitionId",
]


class NativeListingLifecycleState(StrEnum):
    """The exactly three lifecycle states introduced by SLICE-0049."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"


@dataclass(frozen=True)
class PublicationTransitionId:
    """Identifies one immutable, append-only publication-transition record.

    Not interchangeable with ``NativeListingId`` or any other accepted
    marketplace identity kind, even when the underlying raw text collides.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("PublicationTransitionId.value must be non-empty")
