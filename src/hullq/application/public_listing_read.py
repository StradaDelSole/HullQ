"""First production-public NativeListing read model — SLICE-0049 §8 / SLICE-0050 §10.

Resolves an exact `NativeListingId` into the bounded public projection only
when the durable chain is complete AND lifecycle == ACTIVE. Reuses the same
accepted SLICE-0048 chain-resolution predicate
(`hullq.application.preview_read.resolve_previewable_listing`) so the public
read model derives from the identical truth-bearing current `LISTING_OFFER`
semantics -- lossless asking-price representation, omission vs explicit
UNKNOWN/NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED, conservative known-history
wording, VAT/tax claim qualification -- without inventing a second read path.

SLICE-0050 extends this same projection with the publishing Organization's
own current bounded PhysicalBoat claim snapshot (`THIS BOAT`) -- the seven
originally accepted SLICE-0050 fields plus the optional SLICE-0065
`boat_name` field -- resolved via
`hullq.persistence.physical_boat_claims.fetch_current_physical_boat_claim`
against the exact `(physical_boat_id, publishing_organization_id)` pair --
never a different Organization's claim for the same PhysicalBoat, and never
a BoatDesign baseline value standing in for an omitted/UNKNOWN claim
(SLICE-0050 §9/§12). A PhysicalBoat with no recorded claim from this
listing's publishing Organization still renders publicly: claim absence is
never a listing-lifecycle failure.

`PUBLIC != INDEXABLE` and `ACTIVE != FRESHNESS CONFIRMED`
(`specs/NATIVE_LISTING_PUBLIC_SURFACE_SEO_CONTRACT.v0.1.md`): this module
resolves public *readability* only. Indexation/crawl directives are a
presentation-boundary concern applied by the FastAPI route and Astro page,
not by this read model.

SLICE-0052 narrows current-market readability further (contract §7.1):
`ACTIVE` alone no longer proves eligibility. This module additionally
resolves freshness (`hullq.application.native_listing_freshness`) at the
explicit *as_of* boundary supplied by the caller and collapses
`ACTIVE + STALE`/`ACTIVE + UNKNOWN` to the identical `None` result used for
DRAFT/WITHDRAWN/missing/incomplete -- never a distinguishable "stale current
offer" projection. Lifecycle/history are never touched by this read.

DRAFT, WITHDRAWN, missing and incomplete listings all collapse to the
identical `None` result -- this module (and therefore the public FastAPI
route built on it) is never a NativeListingId existence oracle, exactly like
the SLICE-0048 preview surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from hullq.application.native_listing_freshness import (
    is_current_market_eligible,
    resolve_current_freshness,
)
from hullq.application.preview_read import resolve_previewable_listing
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.native_listing_offer import (
    BrokerSummaryClaim,
    KnownHistoryNarrativeClaim,
    LocationRegionClaim,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
)
from hullq.domain.physical_boat_claims import (
    BoatNameClaim,
    BuildYearClaim,
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    LoaLengthClaim,
    PhysicalBoatClaimSnapshot,
    RudderConfiguration,
    RudderConfigurationClaim,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.broker_identity import fetch_marketplace_organization
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.physical_boat_claims import fetch_current_physical_boat_claim

__all__ = ["PublicListingReadModel", "get_public_listing_read_model"]


@dataclass(frozen=True)
class PublicListingReadModel:
    """The bounded public projection of one ACTIVE NativeListing's current offer.

    Carries no creator/actor Account identity, no publication-transition
    history, no internal hashes/transaction metadata, and no BoatDesign
    baseline-as-yacht-fact -- only the accepted nine-field `LISTING_OFFER`
    public projection plus the minimal VAT/tax attribution metadata already
    accepted for the SLICE-0048 preview projection, plus (SLICE-0050) the
    publishing Organization's own current bounded PhysicalBoat claim
    snapshot -- the seven originally accepted SLICE-0050 fields plus the
    optional SLICE-0065 `boat_name` field -- when one exists. Unlike the
    preview projection, this
    carries no `preview_expires_at`: public visibility here is determined
    solely by the accepted ACTIVE predicate, never by a finite bearer
    capability.
    """

    offer: NativeListingOfferSnapshot
    publishing_organization_id: MarketplaceOrganizationId
    publishing_organization_display_name: str
    offer_recorded_at: datetime
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None
    physical_boat_claims: PhysicalBoatClaimSnapshot | None = None

    def to_public_dict(self) -> dict[str, Any]:
        """Render the exact accepted public projection as a JSON-safe dict.

        Mirrors `hullq.application.preview_read.PreviewReadModel.to_public_dict`
        field-for-field (minus `preview_expires_at`, plus
        `physical_boat_claims`, `freshness_status` and `last_confirmed_at`):
        `asking_price_amount` is a decimal string, never a binary float, and
        each optional claim field distinguishes omission (`None`) from an
        explicit UNKNOWN/NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED/
        VALUE_ASSERTION assertion. `publishing_organization_display_name`
        (SLICE-0063) is always present -- the current actor-directory
        `public_display_name` when the publishing Organization resolves, or
        the exact `publishing_organization_id` as the accepted legacy
        compatibility fallback when it does not (contract §6/§7); it is
        presentation metadata only, never a second identity.
        `physical_boat_claims` is `None` when the
        publishing Organization has not yet recorded any SLICE-0050 claim
        for this PhysicalBoat (SLICE-0050 §10: claim absence never fails the
        listing's own public readability), and otherwise carries only the
        seven originally accepted bounded fields plus the optional
        SLICE-0065 `boat_name` field -- no revision id, recording Account or
        BoatDesign baseline value. `freshness_status` is always one of
        `CONFIRMED`/`DUE_FOR_CONFIRMATION` here (contract §7.1: STALE/UNKNOWN
        never reach this dict -- `get_public_listing_read_model` resolves to
        `None` first).
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
            "publishing_organization_display_name": self.publishing_organization_display_name,
            "offer_recorded_at": self.offer_recorded_at.isoformat(),
            "hullq_vat_verification_status": "NONE",
            "physical_boat_claims": _physical_boat_claims_dict(self.physical_boat_claims),
            "freshness_status": self.freshness_status.value,
            "last_confirmed_at": (
                self.last_confirmed_at.isoformat() if self.last_confirmed_at is not None else None
            ),
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


def _optional_boat_claim_dict(
    claim: BuildYearClaim
    | LoaLengthClaim
    | DraftClaim
    | KeelConfigurationClaim
    | RudderConfigurationClaim
    | BoatNameClaim
    | None,
) -> dict[str, Any] | None:
    if claim is None:
        return None
    value = claim.value
    if isinstance(value, Decimal):
        rendered: Any = str(value)
    elif isinstance(value, (KeelConfiguration, RudderConfiguration)):
        rendered = value.value
    else:
        rendered = value
    return {"assertion_kind": claim.assertion_kind.value, "value": rendered}


def _physical_boat_claims_dict(claims: PhysicalBoatClaimSnapshot | None) -> dict[str, Any] | None:
    """Render the bounded seven-field PhysicalBoat claim projection plus the
    SLICE-0065 optional `boat_name` field, or `None`.

    `None` at this top level means the publishing Organization has not
    recorded any SLICE-0050 claim for this PhysicalBoat at all -- distinct
    from `loa_length`/`draft`/`keel_configuration`/`rudder_configuration`/
    `boat_name` each individually being `None` (that field was never
    supplied by the broker) versus an explicit `{"assertion_kind":
    "UNKNOWN", ...}` (or, for `boat_name` only, `"ABSENT"`) object
    (the broker was asked and does not know).
    """
    if claims is None:
        return None
    return {
        "marketed_brand_claim": claims.marketed_brand_claim,
        "model_designation_claim": claims.model_designation_claim,
        "build_year": _optional_boat_claim_dict(claims.build_year),
        "loa_length": _optional_boat_claim_dict(claims.loa_length),
        "draft": _optional_boat_claim_dict(claims.draft),
        "keel_configuration": _optional_boat_claim_dict(claims.keel_configuration),
        "rudder_configuration": _optional_boat_claim_dict(claims.rudder_configuration),
        "boat_name": _optional_boat_claim_dict(claims.boat_name),
    }


def get_public_listing_read_model(
    conn: Any, native_listing_id: NativeListingId, *, as_of: datetime
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

    SLICE-0052 contract §7.1: current-market eligibility additionally
    requires freshness CONFIRMED or DUE_FOR_CONFIRMATION at the explicit
    *as_of* boundary. `ACTIVE + STALE` and `ACTIVE + UNKNOWN` collapse to
    this identical `None` result -- never a distinguishable stale-offer
    projection -- without mutating lifecycle/history.
    """
    if fetch_lifecycle_state(conn, native_listing_id) is not NativeListingLifecycleState.ACTIVE:
        return None

    resolved = resolve_previewable_listing(conn, native_listing_id)
    if resolved is None:
        return None

    freshness = resolve_current_freshness(conn, native_listing_id, as_of=as_of)
    if not is_current_market_eligible(freshness.status):
        return None

    # SLICE-0050 §10/§12: the *publishing* Organization's own current claim
    # head only -- never a different Organization's claim for the same
    # PhysicalBoat, and never a BoatDesign baseline value. A claim
    # absence here is not a listing-lifecycle failure: `claim_record` stays
    # `None` and the listing remains publicly readable exactly as it was
    # before SLICE-0050 existed.
    claim_record = fetch_current_physical_boat_claim(
        conn, resolved.physical_boat_id, resolved.publishing_organization_id
    )

    # SLICE-0063 contract §6/§7: the publishing Organization's own current
    # bounded display name, or the exact Organization ID as the accepted
    # legacy compatibility fallback when the actor-directory row does not
    # (yet, or ever) exist. Never a listing-readability failure either way.
    publishing_organization = fetch_marketplace_organization(
        conn, resolved.publishing_organization_id
    )
    display_name = (
        publishing_organization.resolved_public_display_name
        if publishing_organization is not None
        else resolved.publishing_organization_id.value
    )

    return PublicListingReadModel(
        offer=resolved.offer,
        publishing_organization_id=resolved.publishing_organization_id,
        publishing_organization_display_name=display_name,
        offer_recorded_at=resolved.offer_recorded_at,
        freshness_status=freshness.status,
        last_confirmed_at=freshness.last_confirmed_at,
        physical_boat_claims=claim_record.claims if claim_record is not None else None,
    )
