"""Lead acquisition/discovery provenance vocabulary — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§8B: two distinct bounded evidence dimensions --

    acquisition_channel -- how the visit/session entered HullQ (first-touch,
        to the extent bounded evidence for it exists at submission time);
    discovery_surface   -- which HullQ surface/path led to the contacted
        NativeListing.

Attribution is evidence, never inference-by-guess (contract §8B): absence is
always `UNKNOWN`, never a guessed default. v0.1 evidences acquisition only
from explicitly-supplied bounded UTM query parameters via a small
deterministic `utm_medium` -> channel table (the sender's own declared
channel label, not a guess). `discovery_surface` has no first-party capture
wired in this slice (no internal-navigation tracking exists yet) and is
therefore always `UNKNOWN` here -- the vocabulary/schema/persistence/display
foundation is still built so a later HullQ surface can populate it without
schema replacement (contract §8B: "later HullQ surfaces extensible without
replacing the model").

Pure value objects/normalizers only -- no persistence/network access.
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum

__all__ = [
    "MAX_UTM_VALUE_LENGTH",
    "AcquisitionChannel",
    "DiscoverySurface",
    "classify_acquisition_channel",
    "normalize_utm_value",
]


class AcquisitionChannel(StrEnum):
    """Bounded acquisition-channel vocabulary (contract §8B minimum set)."""

    DIRECT = "DIRECT"
    ORGANIC_SEARCH = "ORGANIC_SEARCH"
    PAID_SEARCH = "PAID_SEARCH"
    PAID_CAMPAIGN = "PAID_CAMPAIGN"
    REFERRAL = "REFERRAL"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class DiscoverySurface(StrEnum):
    """Bounded discovery-surface vocabulary (contract §8B minimum set)."""

    DIRECT_LISTING = "DIRECT_LISTING"
    TECHNICAL_SEARCH = "TECHNICAL_SEARCH"
    INTERNAL_BROWSE = "INTERNAL_BROWSE"
    SHORTLIST = "SHORTLIST"
    COMPARE = "COMPARE"
    UNKNOWN = "UNKNOWN"


#: Bounded per contract §8B: generous enough for a genuine UTM value while
#: rejecting unbounded input. Mirrors common UTM-parameter length practice.
MAX_UTM_VALUE_LENGTH = 200

#: Deterministic `utm_medium` (lower-cased) -> channel mapping. This is the
#: sender's own declared channel label per the well-established UTM
#: convention, not an inference from ambiguous signals -- an unmapped or
#: absent medium with a present `utm_source`/`utm_campaign` resolves to
#: `OTHER`, never a guessed specific channel.
_UTM_MEDIUM_CHANNEL_MAP: dict[str, AcquisitionChannel] = {
    "cpc": AcquisitionChannel.PAID_SEARCH,
    "ppc": AcquisitionChannel.PAID_SEARCH,
    "paid": AcquisitionChannel.PAID_SEARCH,
    "paidsearch": AcquisitionChannel.PAID_SEARCH,
    "organic": AcquisitionChannel.ORGANIC_SEARCH,
    "social": AcquisitionChannel.SOCIAL,
    "referral": AcquisitionChannel.REFERRAL,
    "email": AcquisitionChannel.PAID_CAMPAIGN,
    "campaign": AcquisitionChannel.PAID_CAMPAIGN,
}


def normalize_utm_value(raw: object) -> str | None:
    """Trim and bound one optional UTM query-parameter value.

    `None`/missing/blank input normalizes to `None` (contract §8B:
    "Absence is UNKNOWN") -- this is not an error case. Raises `ValueError`
    for a non-`str`, control-character-bearing or over-long value: a
    materially malformed value is rejected, not silently dropped, so a
    caller cannot mistake a rejected value for genuine absence.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise TypeError(f"UTM value must be a str or None, got {type(raw).__name__}")
    trimmed = raw.strip()
    if not trimmed:
        return None
    if len(trimmed) > MAX_UTM_VALUE_LENGTH:
        raise ValueError(f"UTM value must be at most {MAX_UTM_VALUE_LENGTH} characters")
    for char in trimmed:
        if unicodedata.category(char) == "Cc":
            raise ValueError("UTM value must not contain control characters")
    return trimmed


def classify_acquisition_channel(
    *, utm_source: str | None, utm_medium: str | None, utm_campaign: str | None
) -> AcquisitionChannel:
    """Deterministically classify acquisition channel from bounded, already-
    normalized UTM evidence.

    No evidence at all -> `UNKNOWN` (never `DIRECT`: v0.1 captures no
    referrer/no-referrer evidence, so "no UTM parameters" is not itself
    proof of a direct, referrer-less visit). A recognized `utm_medium` maps
    via the fixed table above; any other combination that still supplies at
    least one UTM field resolves to `OTHER`.
    """
    if utm_source is None and utm_medium is None and utm_campaign is None:
        return AcquisitionChannel.UNKNOWN
    if utm_medium is not None:
        mapped = _UTM_MEDIUM_CHANNEL_MAP.get(utm_medium.strip().lower())
        if mapped is not None:
            return mapped
    return AcquisitionChannel.OTHER
