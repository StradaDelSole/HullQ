"""Unit tests for hullq.domain.promotion_readiness — SLICE-0067.

Covers `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md` §3: the exact
D07 required-response rule, the price-state consistency rule (POA + currency
is NOT_READY, never silently normalized) and the deterministic canonical
reason-code ordering -- independent of any persistence/authorization/network
concern.
"""

from __future__ import annotations

from decimal import Decimal

from hullq.domain.listing_draft_payload import (
    AskingPriceMode,
    BuildYearAssertionKind,
    BuildYearResponse,
    ListingDraftPayload,
)
from hullq.domain.promotion_readiness import PromotionReadinessReason, evaluate_promotion_readiness

_READY_BUILD_YEAR = BuildYearResponse(BuildYearAssertionKind.VALUE_ASSERTION, 2020)
_UNKNOWN_BUILD_YEAR = BuildYearResponse(BuildYearAssertionKind.UNKNOWN)


def _ready_amount_payload() -> ListingDraftPayload:
    return ListingDraftPayload(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=_READY_BUILD_YEAR,
        asking_price_mode=AskingPriceMode.AMOUNT,
        asking_price_amount=Decimal("125000"),
        currency="EUR",
        location_country="FR",
    )


def _ready_poa_payload() -> ListingDraftPayload:
    return ListingDraftPayload(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=_UNKNOWN_BUILD_YEAR,
        asking_price_mode=AskingPriceMode.POA,
        location_country="FR",
    )


class TestReadyCases:
    def test_ready_amount_mode_has_zero_reasons(self) -> None:
        readiness = evaluate_promotion_readiness(_ready_amount_payload(), "A lovely cruiser.")
        assert readiness.is_ready is True
        assert readiness.reasons == ()

    def test_ready_poa_mode_with_unknown_build_year_has_zero_reasons(self) -> None:
        readiness = evaluate_promotion_readiness(_ready_poa_payload(), "A lovely cruiser.")
        assert readiness.is_ready is True
        assert readiness.reasons == ()

    def test_empty_draft_is_not_ready(self) -> None:
        readiness = evaluate_promotion_readiness(ListingDraftPayload(), None)
        assert readiness.is_ready is False


class TestRequiredResponses:
    def test_missing_marketed_brand(self) -> None:
        payload = _ready_amount_payload()
        payload = ListingDraftPayload(**{**payload.__dict__, "marketed_brand_claim": None})
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        assert readiness.reasons == (PromotionReadinessReason.MISSING_MARKETED_BRAND,)

    def test_missing_model_designation(self) -> None:
        payload = _ready_amount_payload()
        payload = ListingDraftPayload(**{**payload.__dict__, "model_designation_claim": None})
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        assert readiness.reasons == (PromotionReadinessReason.MISSING_MODEL_DESIGNATION,)

    def test_missing_build_year_response(self) -> None:
        payload = _ready_amount_payload()
        payload = ListingDraftPayload(**{**payload.__dict__, "build_year": None})
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        assert readiness.reasons == (PromotionReadinessReason.MISSING_BUILD_YEAR_RESPONSE,)

    def test_missing_location_country(self) -> None:
        payload = _ready_amount_payload()
        payload = ListingDraftPayload(**{**payload.__dict__, "location_country": None})
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        assert readiness.reasons == (PromotionReadinessReason.MISSING_LOCATION_COUNTRY,)

    def test_missing_broker_description(self) -> None:
        readiness = evaluate_promotion_readiness(_ready_amount_payload(), None)
        assert readiness.reasons == (PromotionReadinessReason.MISSING_BROKER_DESCRIPTION,)

    def test_boat_name_and_location_region_are_never_required(self) -> None:
        """Contract §3.1: boat name, region, broker listing reference,
        BoatDesignRef, Search-fit fields and media are never required."""
        readiness = evaluate_promotion_readiness(_ready_amount_payload(), "A lovely cruiser.")
        assert readiness.is_ready is True


class TestPriceStateConsistency:
    def test_missing_asking_price_mode_alone(self) -> None:
        payload = _ready_amount_payload()
        payload = ListingDraftPayload(
            **{
                **payload.__dict__,
                "asking_price_mode": None,
                "asking_price_amount": None,
                "currency": None,
            }
        )
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        # Contract §3.3: mode omitted -> MISSING_ASKING_PRICE_MODE only; do
        # not additionally invent AMOUNT/POA conditional reasons.
        assert readiness.reasons == (PromotionReadinessReason.MISSING_ASKING_PRICE_MODE,)

    def test_amount_mode_missing_amount_and_currency(self) -> None:
        payload = _ready_amount_payload()
        payload = ListingDraftPayload(
            **{**payload.__dict__, "asking_price_amount": None, "currency": None}
        )
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        assert readiness.reasons == (
            PromotionReadinessReason.MISSING_ASKING_PRICE_AMOUNT,
            PromotionReadinessReason.MISSING_CURRENCY,
        )

    def test_amount_mode_missing_currency_only(self) -> None:
        payload = _ready_amount_payload()
        payload = ListingDraftPayload(**{**payload.__dict__, "currency": None})
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        assert readiness.reasons == (PromotionReadinessReason.MISSING_CURRENCY,)

    def test_poa_mode_with_currency_is_not_ready(self) -> None:
        """Contract §3.2: POA + currency is NOT_READY -- never silently
        dropped/normalized."""
        payload = ListingDraftPayload(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=_UNKNOWN_BUILD_YEAR,
            asking_price_mode=AskingPriceMode.POA,
            currency="EUR",
            location_country="FR",
        )
        readiness = evaluate_promotion_readiness(payload, "A lovely cruiser.")
        assert readiness.reasons == (PromotionReadinessReason.CURRENCY_NOT_ALLOWED_FOR_POA,)
        assert readiness.is_ready is False


class TestCanonicalReasonOrder:
    def test_every_reason_present_appears_in_exact_canonical_order(self) -> None:
        empty = ListingDraftPayload()
        readiness = evaluate_promotion_readiness(empty, None)
        assert readiness.reasons == (
            PromotionReadinessReason.MISSING_MARKETED_BRAND,
            PromotionReadinessReason.MISSING_MODEL_DESIGNATION,
            PromotionReadinessReason.MISSING_BUILD_YEAR_RESPONSE,
            PromotionReadinessReason.MISSING_ASKING_PRICE_MODE,
            PromotionReadinessReason.MISSING_LOCATION_COUNTRY,
            PromotionReadinessReason.MISSING_BROKER_DESCRIPTION,
        )

    def test_amount_mode_conditional_reasons_sort_after_the_six_base_reasons(self) -> None:
        payload = ListingDraftPayload(asking_price_mode=AskingPriceMode.AMOUNT)
        readiness = evaluate_promotion_readiness(payload, None)
        assert readiness.reasons == (
            PromotionReadinessReason.MISSING_MARKETED_BRAND,
            PromotionReadinessReason.MISSING_MODEL_DESIGNATION,
            PromotionReadinessReason.MISSING_BUILD_YEAR_RESPONSE,
            PromotionReadinessReason.MISSING_LOCATION_COUNTRY,
            PromotionReadinessReason.MISSING_BROKER_DESCRIPTION,
            PromotionReadinessReason.MISSING_ASKING_PRICE_AMOUNT,
            PromotionReadinessReason.MISSING_CURRENCY,
        )
