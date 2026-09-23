"""Professional listing draft — pure decision core — SLICE-0061/0065.

Implements `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md` §2/§4/§5
and `specs/PROFESSIONAL_PUBLICATION_INPUT_ALIGNMENT_CONTRACT.v0.1.md` §4: the
`ProfessionalListingDraftId` identity kind, the professional-only
`broker_listing_reference` metadata field, and the professional-only offer
input `listing_offer.broker_description`, layered on top of the
channel-neutral nine common draft-input keys shared with owner-direct
(`hullq.domain.listing_draft_payload`, contract §4.1). `broker_description`
is deliberately never added to `ACCEPTED_DRAFT_PAYLOAD_KEYS`: it is
professional-only, exactly like `broker_listing_reference`, and MUST NOT
become an accepted `OwnerDirectListingDraft` key (SLICE-0065 contract §3).
This module is pure and persistence-neutral -- no database, no FastAPI, no
Account/Organization/session lookup.

`ProfessionalListingDraftId` is deliberately unrelated to
`OwnerDirectListingDraftId`/`NativeListingId`/`PhysicalBoatId`/
`MarketEpisodeId` (contract §2) -- reusing any of those identity kinds for a
professional draft would blur the hard non-promotion boundary this slice
exists to protect. Equal raw text across identity kinds must not make them
interchangeable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hullq.domain.listing_draft_payload import (
    ACCEPTED_DRAFT_PAYLOAD_KEYS,
    EMPTY_LISTING_DRAFT_PAYLOAD,
    AskingPriceMode,
    InvalidListingDraftPayloadError,
    ListingDraftPayload,
    parse_listing_draft_payload,
    require_trimmed_nonempty_string,
)

__all__ = [
    "ACCEPTED_DRAFT_PAYLOAD_KEYS",
    "BROKER_DESCRIPTION_KEY",
    "BROKER_LISTING_REFERENCE_KEY",
    "EMPTY_LISTING_DRAFT_PAYLOAD",
    "AskingPriceMode",
    "InvalidListingDraftPayloadError",
    "ListingDraftPayload",
    "ProfessionalListingDraftId",
    "ProfessionalListingDraftRequest",
    "parse_listing_draft_payload",
    "parse_professional_listing_draft_request",
]


@dataclass(frozen=True)
class ProfessionalListingDraftId:
    """Server-generated opaque professional draft identity.

    Deliberately a distinct runtime type from `OwnerDirectListingDraftId`/
    `NativeListingId`/`PhysicalBoatId`/`MarketEpisodeId` (contract §2):
    equal raw text across those kinds must never be accepted as
    interchangeable, and this identity must never be accepted by an API/
    persistence function expecting another identity kind.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ProfessionalListingDraftId.value must be non-empty")


#: The one professional-only metadata key (contract §5), deliberately kept
#: outside `ACCEPTED_DRAFT_PAYLOAD_KEYS`: it is not one of the nine
#: channel-neutral common draft-input keys and carries no marketplace/
#: NativeListing identity meaning.
BROKER_LISTING_REFERENCE_KEY = "broker_listing_reference"

#: SLICE-0065: the one professional-only bounded pre-market offer input,
#: deliberately kept outside `ACCEPTED_DRAFT_PAYLOAD_KEYS` (Publication
#: Input Alignment contract §3/§4): it is not one of the nine channel-neutral
#: common draft-input keys, is distinct from `BROKER_LISTING_REFERENCE_KEY`,
#: and MUST NOT be accepted by `OwnerDirectListingDraft`.
BROKER_DESCRIPTION_KEY = "listing_offer.broker_description"


@dataclass(frozen=True)
class ProfessionalListingDraftRequest:
    """One parsed professional draft request: the shared common payload
    plus the professional-only `broker_listing_reference` (contract §5) and
    `listing_offer.broker_description` (Publication Input Alignment contract
    §4).
    """

    common: ListingDraftPayload
    broker_listing_reference: str | None = None
    broker_description: str | None = None


def parse_professional_listing_draft_request(raw: Any) -> ProfessionalListingDraftRequest:
    """Validate *raw* against the bounded professional draft request shape.

    *raw* is the nine common draft-input keys (contract §4) plus the
    optional professional-only `broker_listing_reference` (contract §5) and
    `listing_offer.broker_description` (Publication Input Alignment contract
    §4) in one flat JSON object. Both professional-only fields, when
    present, must be a trimmed non-empty string -- the identical rule
    already used by every other "trimmed non-empty string" common field,
    reused via `require_trimmed_nonempty_string` rather than a second
    inconsistent copy. Unknown keys (including a malformed
    `broker_listing_reference`/`listing_offer.broker_description` key
    spelling) fail closed via the shared common-key parser.
    """
    if not isinstance(raw, dict):
        raise InvalidListingDraftPayloadError(
            f"draft request must be a JSON object, got {type(raw).__name__}"
        )

    body = dict(raw)
    broker_listing_reference: str | None = None
    if BROKER_LISTING_REFERENCE_KEY in body:
        raw_reference = body.pop(BROKER_LISTING_REFERENCE_KEY)
        broker_listing_reference = require_trimmed_nonempty_string(
            raw_reference, BROKER_LISTING_REFERENCE_KEY
        )

    broker_description: str | None = None
    if BROKER_DESCRIPTION_KEY in body:
        raw_description = body.pop(BROKER_DESCRIPTION_KEY)
        broker_description = require_trimmed_nonempty_string(
            raw_description, BROKER_DESCRIPTION_KEY
        )

    common = parse_listing_draft_payload(body)
    return ProfessionalListingDraftRequest(
        common=common,
        broker_listing_reference=broker_listing_reference,
        broker_description=broker_description,
    )
