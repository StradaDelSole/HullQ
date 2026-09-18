"""Buyer Requirement Sensitivity application service — SLICE-0057.

Implements `specs/BUYER_REQUIREMENT_SENSITIVITY_CONTRACT.v0.1.md`: given one
valid current Direct Search requirement, the buyer explicitly chooses exactly
one currently active hard criterion (`draft_max` or `keel_configuration`) and
supplies one replacement value. This module evaluates the current and
alternative requirements through the exact same accepted Search truth
(`hullq.application.search_read.evaluate_requirement_search_outcome`, the one
dispatch point shared with the ordinary `GET /api/search/{locale}` route) and
reports the factual, stable-`NativeListingId` set-difference delta (contract
§8) -- never total-count arithmetic, never a second Search evaluator.

This module is pure application logic, independent of any HTTP framework
(mirrors `hullq.application.search_read`'s own boundary) so it stays testable
without a `TestClient`. It performs no persistence of its own (contract §5:
"read-only computation ... persists nothing").

## Coherent evaluation boundary (contract §7)

The current and alternative evaluations run back to back against the same
*conn*, wrapped in one `REPEATABLE READ` PostgreSQL transaction
(`_evaluate_coherent_pair` below) -- under the default `READ COMMITTED`
isolation each half's several underlying statements would each see the
latest committed state independently, so a write landing between the two
halves could produce a delta that never existed in any single consistent
database state. `REPEATABLE READ` fixes one MVCC snapshot at the first
statement of the transaction and holds it for every following statement in
that same transaction, satisfying contract §7 without any new global
snapshot framework. Per
`hullq.persistence.native_listing.NativeListingTransactionOwnershipError`'s
documented `conn.transaction()` caveat, *conn* must be IDLE (no prior
statement executed) when this module receives it -- callers must pass a
freshly opened connection, exactly like every other route in
`hullq.api.app`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.inventory_search import DraftMaxSearchOutcome
from hullq.application.native_inventory_query import NativeInventorySearchOutcome
from hullq.application.search_read import (
    build_canonical_search_path,
    evaluate_requirement_search_outcome,
)
from hullq.search.draft_max_request import DraftMaxSyntaxError, parse_draft_max_decimal
from hullq.search.keel_design_bridge import SEARCH_KEEL_CONFIGURATION_VALUES

__all__ = [
    "SensitivityErrorKind",
    "SensitivityOutcome",
    "SensitivityOutcomeKind",
    "SensitivityResult",
    "evaluate_requirement_sensitivity",
]

_DRAFT_MAX_KEY = "draft_max"
_KEEL_CONFIGURATION_KEY = "keel_configuration"
_ALLOWED_CURRENT_KEYS = frozenset({_DRAFT_MAX_KEY, _KEEL_CONFIGURATION_KEY})
_ALLOWED_CHANGED_CRITERIA = frozenset({_DRAFT_MAX_KEY, _KEEL_CONFIGURATION_KEY})


class SensitivityErrorKind(StrEnum):
    """Every accepted 400-class failure (contract §11), fail-closed and
    mutually exclusive -- checked in this fixed order so the first genuine
    problem is always the one reported."""

    UNKNOWN_CURRENT_KEY = "UNKNOWN_CURRENT_KEY"
    NO_ACTIVE_CRITERIA = "NO_ACTIVE_CRITERIA"
    UNSUPPORTED_CHANGED_CRITERION = "UNSUPPORTED_CHANGED_CRITERION"
    CHANGED_CRITERION_NOT_ACTIVE = "CHANGED_CRITERION_NOT_ACTIVE"
    INVALID_DRAFT_MAX = "INVALID_DRAFT_MAX"
    INVALID_KEEL_CONFIGURATION = "INVALID_KEEL_CONFIGURATION"


class SensitivityOutcomeKind(StrEnum):
    OK = "OK"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    """The complete factual comparison (contract §10). Every semantic value
    the contract requires is represented explicitly and typed -- no advice,
    recommendation, score or inferred intent."""

    locale: str
    current_draft_max: Decimal | None
    current_keel_configuration: str | None
    alternative_draft_max: Decimal | None
    alternative_keel_configuration: str | None
    changed_criterion: str
    current_confirmed_match_count: int
    alternative_confirmed_match_count: int
    newly_confirmed_match_count: int
    no_longer_confirmed_match_count: int
    current_insufficient_data_count: int
    alternative_insufficient_data_count: int
    alternative_search_path: str


@dataclass(frozen=True, slots=True)
class SensitivityOutcome:
    """One evaluated sensitivity request. Exactly one payload matches `kind`."""

    kind: SensitivityOutcomeKind
    error: SensitivityErrorKind | None = None
    result: SensitivityResult | None = None

    def __post_init__(self) -> None:
        if self.kind is SensitivityOutcomeKind.OK:
            if self.result is None:
                raise ValueError("An OK outcome must carry result")
            if self.error is not None:
                raise ValueError("An OK outcome must not carry error")
        else:
            if self.error is None:
                raise ValueError("An INVALID outcome must carry error")
            if self.result is not None:
                raise ValueError("An INVALID outcome must not carry result")


def _confirmed_ids(
    outcome: DraftMaxSearchOutcome | NativeInventorySearchOutcome,
) -> frozenset[str]:
    return frozenset(match.native_listing_id.value for match in outcome.confirmed_matches)


def _evaluate_coherent_pair(
    conn: Any,
    *,
    current_draft_max: Decimal | None,
    current_keel_configuration: str | None,
    alternative_draft_max: Decimal | None,
    alternative_keel_configuration: str | None,
    as_of: datetime,
) -> tuple[
    DraftMaxSearchOutcome | NativeInventorySearchOutcome,
    DraftMaxSearchOutcome | NativeInventorySearchOutcome,
]:
    """Evaluate the current and alternative requirements inside one
    `REPEATABLE READ` transaction (contract §7 -- see this module's
    docstring). `SET TRANSACTION ISOLATION LEVEL` must be the first
    statement of the PostgreSQL transaction, so it runs immediately after
    `conn.transaction()` opens the (required-IDLE) connection's transaction
    block, before either evaluation issues its own statements.
    """
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        current_outcome = evaluate_requirement_search_outcome(
            conn,
            draft_max=current_draft_max,
            keel_configuration=current_keel_configuration,
            as_of=as_of,
        )
        alternative_outcome = evaluate_requirement_search_outcome(
            conn,
            draft_max=alternative_draft_max,
            keel_configuration=alternative_keel_configuration,
            as_of=as_of,
        )
    return current_outcome, alternative_outcome


def evaluate_requirement_sensitivity(
    conn: Any,
    *,
    locale: str,
    current: Mapping[str, str],
    changed_criterion: str,
    changed_value: str,
    as_of: datetime,
) -> SensitivityOutcome:
    """Evaluate one buyer-authored one-change sensitivity request.

    *current* carries the current Search's already-active raw criterion
    values (`draft_max` and/or `keel_configuration`, contract §5: "no unknown
    keys"). *changed_criterion*/*changed_value* are the buyer-selected
    criterion name and its raw replacement value. *conn* must be a freshly
    opened, IDLE connection (this module's docstring).

    Every value -- current and proposed alike -- is parsed/validated through
    the exact same accepted primitives `GET /api/search/{locale}` uses
    (`hullq.search.draft_max_request.parse_draft_max_decimal`,
    `hullq.search.keel_design_bridge.SEARCH_KEEL_CONFIGURATION_VALUES`):
    tampered/malformed current state fails closed exactly like a tampered
    proposed value, never silently accepted because it "came from the
    buyer's own prior Search."
    """
    if not isinstance(locale, str) or not locale:
        raise ValueError(f"locale must be a non-empty string; got {locale!r}")

    unknown_keys = set(current) - _ALLOWED_CURRENT_KEYS
    if unknown_keys:
        return SensitivityOutcome(
            kind=SensitivityOutcomeKind.INVALID, error=SensitivityErrorKind.UNKNOWN_CURRENT_KEY
        )
    if not current:
        return SensitivityOutcome(
            kind=SensitivityOutcomeKind.INVALID, error=SensitivityErrorKind.NO_ACTIVE_CRITERIA
        )
    if changed_criterion not in _ALLOWED_CHANGED_CRITERIA:
        return SensitivityOutcome(
            kind=SensitivityOutcomeKind.INVALID,
            error=SensitivityErrorKind.UNSUPPORTED_CHANGED_CRITERION,
        )
    if changed_criterion not in current:
        return SensitivityOutcome(
            kind=SensitivityOutcomeKind.INVALID,
            error=SensitivityErrorKind.CHANGED_CRITERION_NOT_ACTIVE,
        )

    current_draft_max: Decimal | None = None
    if _DRAFT_MAX_KEY in current:
        try:
            current_draft_max = parse_draft_max_decimal(current[_DRAFT_MAX_KEY])
        except DraftMaxSyntaxError:
            return SensitivityOutcome(
                kind=SensitivityOutcomeKind.INVALID, error=SensitivityErrorKind.INVALID_DRAFT_MAX
            )

    current_keel_configuration: str | None = None
    if _KEEL_CONFIGURATION_KEY in current:
        raw_keel = current[_KEEL_CONFIGURATION_KEY]
        if raw_keel not in SEARCH_KEEL_CONFIGURATION_VALUES:
            return SensitivityOutcome(
                kind=SensitivityOutcomeKind.INVALID,
                error=SensitivityErrorKind.INVALID_KEEL_CONFIGURATION,
            )
        current_keel_configuration = raw_keel

    alternative_draft_max: Decimal | None
    alternative_keel_configuration: str | None
    if changed_criterion == _DRAFT_MAX_KEY:
        try:
            alternative_draft_max = parse_draft_max_decimal(changed_value)
        except DraftMaxSyntaxError:
            return SensitivityOutcome(
                kind=SensitivityOutcomeKind.INVALID, error=SensitivityErrorKind.INVALID_DRAFT_MAX
            )
        alternative_keel_configuration = current_keel_configuration
    else:
        if changed_value not in SEARCH_KEEL_CONFIGURATION_VALUES:
            return SensitivityOutcome(
                kind=SensitivityOutcomeKind.INVALID,
                error=SensitivityErrorKind.INVALID_KEEL_CONFIGURATION,
            )
        alternative_draft_max = current_draft_max
        alternative_keel_configuration = changed_value

    current_outcome, alternative_outcome = _evaluate_coherent_pair(
        conn,
        current_draft_max=current_draft_max,
        current_keel_configuration=current_keel_configuration,
        alternative_draft_max=alternative_draft_max,
        alternative_keel_configuration=alternative_keel_configuration,
        as_of=as_of,
    )

    current_ids = _confirmed_ids(current_outcome)
    alternative_ids = _confirmed_ids(alternative_outcome)

    result = SensitivityResult(
        locale=locale,
        current_draft_max=current_draft_max,
        current_keel_configuration=current_keel_configuration,
        alternative_draft_max=alternative_draft_max,
        alternative_keel_configuration=alternative_keel_configuration,
        changed_criterion=changed_criterion,
        current_confirmed_match_count=len(current_ids),
        alternative_confirmed_match_count=len(alternative_ids),
        newly_confirmed_match_count=len(alternative_ids - current_ids),
        no_longer_confirmed_match_count=len(current_ids - alternative_ids),
        current_insufficient_data_count=current_outcome.insufficient_data_count,
        alternative_insufficient_data_count=alternative_outcome.insufficient_data_count,
        alternative_search_path=build_canonical_search_path(
            locale,
            draft_max=alternative_draft_max,
            keel_configuration=alternative_keel_configuration,
        ),
    )
    return SensitivityOutcome(kind=SensitivityOutcomeKind.OK, result=result)
