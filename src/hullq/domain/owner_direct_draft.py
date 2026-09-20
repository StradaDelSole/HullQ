"""Owner-direct listing draft — pure decision core — SLICE-0054.

Implements `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md` §5/§6/§7:
the `OwnerDirectListingDraftId` identity kind, plus the finite v0.1 draft
payload re-exported from the SLICE-0061 channel-neutral
`hullq.domain.listing_draft_payload` primitive (contract §4.1 / professional
contract §4.1: owner-direct and professional Organization drafts share one
implementation of the nine common draft-input keys, never two inconsistent
copies). This module is pure and persistence-neutral -- no database, no
FastAPI, no Account/session lookup.

The nine accepted keys are *draft input keys only* (contract §6): a value
accepted here is never treated as resolved/canonical marketplace truth.
`OwnerDirectListingDraftId` is deliberately unrelated to `NativeListingId`/
`PhysicalBoatId`/`MarketEpisodeId` (contract §1) -- reusing any marketplace
identity kind for a draft would blur the hard non-promotion boundary this
slice exists to protect.

Every name below is re-exported with its original SLICE-0054 spelling so
this module's public API/behavior is unchanged for every existing caller and
test.
"""

from __future__ import annotations

from dataclasses import dataclass

from hullq.domain.listing_draft_payload import (
    ACCEPTED_DRAFT_PAYLOAD_KEYS,
    EMPTY_LISTING_DRAFT_PAYLOAD,
    AskingPriceMode,
    InvalidListingDraftPayloadError,
    ListingDraftPayload,
    parse_listing_draft_payload,
)

#: Re-exported with their original SLICE-0054 spelling so this module's
#: public API/behavior is unchanged for every existing caller and test.
EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD = EMPTY_LISTING_DRAFT_PAYLOAD
InvalidOwnerDirectDraftPayloadError = InvalidListingDraftPayloadError
OwnerDirectDraftPayload = ListingDraftPayload
parse_owner_direct_draft_payload = parse_listing_draft_payload

__all__ = [
    "ACCEPTED_DRAFT_PAYLOAD_KEYS",
    "EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD",
    "AskingPriceMode",
    "InvalidOwnerDirectDraftPayloadError",
    "OwnerDirectDraftPayload",
    "OwnerDirectListingDraftId",
    "parse_owner_direct_draft_payload",
]


@dataclass(frozen=True)
class OwnerDirectListingDraftId:
    """Server-generated opaque draft identity.

    Deliberately a distinct runtime type from `NativeListingId`/
    `PhysicalBoatId`/`MarketEpisodeId` (contract §1) and from
    `ProfessionalListingDraftId` (SLICE-0061): equal raw text across those
    kinds must never be accepted as interchangeable.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("OwnerDirectListingDraftId.value must be non-empty")
