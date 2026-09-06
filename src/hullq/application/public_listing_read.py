"""First production-public NativeListing read model — SLICE-0049 §8.

Resolves an exact `NativeListingId` into the bounded public projection only
when the durable chain is complete AND lifecycle == ACTIVE. Reuses the same
accepted SLICE-0048 chain-resolution predicate
(`hullq.application.preview_read.resolve_previewable_listing`) so the public
read model derives from the identical truth-bearing current `LISTING_OFFER`
semantics -- lossless asking-price representation, omission vs explicit
UNKNOWN/NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED, conservative known-history
wording, VAT/tax claim qualification -- without inventing a second read path.

`PUBLIC != INDEXABLE` and `ACTIVE != FRESHNESS CONFIRMED`
(`specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`): this module
resolves public *readability* only. Indexation/crawl directives are a
presentation-boundary concern applied by the FastAPI route and Astro page,
not by this read model.

DRAFT, WITHDRAWN, missing and incomplete listings all collapse to the
identical `None` result -- this module (and therefore the public FastAPI
route built on it) is never a NativeListingId existence oracle, exactly like
the SLICE-0048 preview surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.application.preview_read import resolve_previewable_listing
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import (
    BrokerSummaryClaim,
    KnownHistoryNarrativeClaim,
    LocationRegionClaim,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state

__all__ = ["PublicListingReadModel", "get_public_listing_read_model"]


@dataclass(frozen=True)
class PublicListingReadModel:
    """The bounded public projection of one ACTIVE NativeListing's current offer.

    Carries no creator/actor Account identity, no publication-transition
    history, no internal hashes/transaction metadata, no inferred
    PhysicalBoat fact and no BoatDesign baseline-as-yacht-fact -- only the
    accepted nine-field `LISTING_OFFER` public projection plus the minimal
    VAT/tax attribution metadata already accepted for the SLICE-0048 preview
    projection. Unlike the preview projection, this carries no
    `preview_expires_at`: public visibility here is determined solely by the
    accepted ACTIVE predicate, never by a finite bearer capability.
    """

    offer: NativeListingOfferSnapshot
    publishing_organization_id: MarketplaceOrganizationId
    offer_recorded_at: datetime

    def to_public_dict(self) -> dict[str, Any]:
        """Render the exact accepted public projection as a JSON-safe dict.

        Mirrors `hullq.application.preview_read.PreviewReadModel.to_public_dict`
        field-for-field (minus `preview_expires_at`): `asking_price_amount`
        is a decimal string, never a binary float, and each optional claim
        field distinguishes omission (`None`) from an explicit
        UNKNOWN/NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED/VALUE_ASSERTION
        assertion.
        """
        offer = self.offer
        return {
            "asking_price_mode": offer.asking_price_mode.value,
            "asking_price_amount": (
                str(offer.asking_price_amount) if offer.asking_price_amount is not None else None
            ),
            "currency": offer.currency,
            "location_country": offer.location_country,
            "location_region": _claim_dict(offer.location_region),
            "broker_summary": _claim_dict(offer.broker_summary),
            "broker_description": offer.broker_description,
            "known_history_narrative": _claim_dict(offer.known_history_narrative),
            "vat_tax_status_claim": _vat_claim_dict(offer.vat_tax_status_claim),
            "publishing_organization_id": self.publishing_organization_id.value,
            "offer_recorded_at": self.offer_recorded_at.isoformat(),
            "hullq_vat_verification_status": "NONE",
        }


def _claim_dict(
    claim: LocationRegionClaim | BrokerSummaryClaim | KnownHistoryNarrativeClaim | None,
) -> dict[str, Any] | None:
    if claim is None:
        return None
    return {"assertion_kind": claim.assertion_kind.value, "value": claim.value}


def _vat_claim_dict(claim: VatTaxStatusClaim | None) -> dict[str, Any] | None:
    if claim is None:
        return None
    return {
        "assertion_kind": claim.assertion_kind.value,
        "value": claim.value.value if claim.value is not None else None,
    }


def get_public_listing_read_model(
    conn: Any, native_listing_id: NativeListingId
) -> PublicListingReadModel | None:
    """Resolve *native_listing_id* to its public read model, or `None`.

    Gates strictly on lifecycle == ACTIVE before resolving the durable
    chain: a missing listing, a DRAFT listing and a WITHDRAWN listing all
    resolve `fetch_lifecycle_state` to something other than ACTIVE (`None`
    for missing) and short-circuit here identically, without needing to
    reach the chain-resolution query at all. An ACTIVE listing whose chain
    has since become incomplete (should not normally happen, since
    publication requires completeness) still fails closed to `None` via
    `resolve_previewable_listing`, never raises.
    """
    if fetch_lifecycle_state(conn, native_listing_id) is not NativeListingLifecycleState.ACTIVE:
        return None

    resolved = resolve_previewable_listing(conn, native_listing_id)
    if resolved is None:
        return None

    return PublicListingReadModel(
        offer=resolved.offer,
        publishing_organization_id=resolved.publishing_organization_id,
        offer_recorded_at=resolved.offer_recorded_at,
    )
