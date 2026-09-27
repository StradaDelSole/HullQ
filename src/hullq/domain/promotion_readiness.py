"""PromotionReadiness — pure decision core — SLICE-0067.

Implements `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md` §3: the
one canonical, deterministic evaluator of whether a professional draft's
current content satisfies every accepted D07 required response plus the
price-state consistency rule, used identically by browser/preflight display
and the authoritative mutation-time re-evaluation (contract §3.3 -- there is
exactly one evaluator, never two independently-maintained copies).

This module is pure and persistence-neutral -- no database, no FastAPI, no
Account/Organization/session lookup, and no opinion about draft promotion
*state* (EDITABLE/PROMOTED) or authorization/eligibility, which remain
separate concerns (contract §3).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hullq.domain.listing_draft_payload import AskingPriceMode, ListingDraftPayload

__all__ = [
    "PromotionReadiness",
    "PromotionReadinessReason",
    "evaluate_promotion_readiness",
]


class PromotionReadinessReason(StrEnum):
    """The bounded, deterministic machine reason vocabulary (contract §3.3).

    Members are declared in exactly the canonical order the evaluator must
    emit them in -- see `evaluate_promotion_readiness`.
    """

    MISSING_MARKETED_BRAND = "MISSING_MARKETED_BRAND"
    MISSING_MODEL_DESIGNATION = "MISSING_MODEL_DESIGNATION"
    MISSING_BUILD_YEAR_RESPONSE = "MISSING_BUILD_YEAR_RESPONSE"
    MISSING_ASKING_PRICE_MODE = "MISSING_ASKING_PRICE_MODE"
    MISSING_LOCATION_COUNTRY = "MISSING_LOCATION_COUNTRY"
    MISSING_BROKER_DESCRIPTION = "MISSING_BROKER_DESCRIPTION"
    MISSING_ASKING_PRICE_AMOUNT = "MISSING_ASKING_PRICE_AMOUNT"
    MISSING_CURRENCY = "MISSING_CURRENCY"
    CURRENCY_NOT_ALLOWED_FOR_POA = "CURRENCY_NOT_ALLOWED_FOR_POA"


@dataclass(frozen=True)
class PromotionReadiness:
    """One deterministic evaluation result. Zero reasons means READY."""

    reasons: tuple[PromotionReadinessReason, ...]

    @property
    def is_ready(self) -> bool:
        return len(self.reasons) == 0


def evaluate_promotion_readiness(
    payload: ListingDraftPayload, broker_description: str | None
) -> PromotionReadiness:
    """Evaluate *payload* + the professional-only *broker_description* input.

    Reasons are always appended in exactly the contract §3.3 canonical
    order, regardless of which conditions actually trigger. Conditional
    price reasons are only ever considered when `asking_price_mode` is
    itself present (contract §3.3: "mode omitted -> MISSING_ASKING_PRICE_MODE;
    do not additionally invent AMOUNT/POA conditional reasons").
    """
    if not isinstance(payload, ListingDraftPayload):
        raise TypeError(f"payload must be a ListingDraftPayload, got {type(payload).__name__}")
    if broker_description is not None and not isinstance(broker_description, str):
        raise TypeError(
            f"broker_description must be a str or None, got {type(broker_description).__name__}"
        )

    reasons: list[PromotionReadinessReason] = []

    if payload.marketed_brand_claim is None:
        reasons.append(PromotionReadinessReason.MISSING_MARKETED_BRAND)
    if payload.model_designation_claim is None:
        reasons.append(PromotionReadinessReason.MISSING_MODEL_DESIGNATION)
    if payload.build_year is None:
        reasons.append(PromotionReadinessReason.MISSING_BUILD_YEAR_RESPONSE)
    if payload.asking_price_mode is None:
        reasons.append(PromotionReadinessReason.MISSING_ASKING_PRICE_MODE)
    if payload.location_country is None:
        reasons.append(PromotionReadinessReason.MISSING_LOCATION_COUNTRY)
    if broker_description is None:
        reasons.append(PromotionReadinessReason.MISSING_BROKER_DESCRIPTION)

    if payload.asking_price_mode is AskingPriceMode.AMOUNT:
        if payload.asking_price_amount is None:
            reasons.append(PromotionReadinessReason.MISSING_ASKING_PRICE_AMOUNT)
        if payload.currency is None:
            reasons.append(PromotionReadinessReason.MISSING_CURRENCY)
    elif payload.asking_price_mode is AskingPriceMode.POA:
        if payload.currency is not None:
            reasons.append(PromotionReadinessReason.CURRENCY_NOT_ALLOWED_FOR_POA)

    return PromotionReadiness(reasons=tuple(reasons))
