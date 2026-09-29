"""Lead acquisition/discovery provenance persistence — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§8B: one immutable creation-time evidence row per Lead. Like
`hullq.persistence.lead_notification.insert_pending_notification_intent`,
`insert_lead_acquisition_provenance` is a bare-cursor function meant to be
called from inside `hullq.persistence.buyer_lead.create_buyer_lead`'s own
CREATED-branch transaction, so provenance capture never becomes a second,
separately-committed write against the same Lead creation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hullq.domain.buyer_lead import LeadId
from hullq.domain.lead_provenance import AcquisitionChannel, DiscoverySurface

__all__ = ["LeadProvenanceRecord", "fetch_lead_acquisition_provenance", "insert_lead_acquisition_provenance"]


@dataclass(frozen=True)
class LeadProvenanceRecord:
    lead_id: LeadId
    acquisition_channel: AcquisitionChannel
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_term: str | None
    utm_content: str | None
    discovery_surface: DiscoverySurface


_INSERT_PROVENANCE = """
INSERT INTO lead_acquisition_provenance (
    lead_id, acquisition_channel, utm_source, utm_medium, utm_campaign, utm_term, utm_content,
    discovery_surface
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (lead_id) DO NOTHING
"""

_SELECT_PROVENANCE = """
SELECT lead_id, acquisition_channel, utm_source, utm_medium, utm_campaign, utm_term, utm_content,
       discovery_surface
FROM lead_acquisition_provenance WHERE lead_id = %s
"""


def insert_lead_acquisition_provenance(
    cur: Any,
    *,
    lead_id: LeadId,
    acquisition_channel: AcquisitionChannel,
    utm_source: str | None,
    utm_medium: str | None,
    utm_campaign: str | None,
    utm_term: str | None,
    utm_content: str | None,
    discovery_surface: DiscoverySurface,
) -> None:
    """Insert one immutable provenance row using the caller's own open
    cursor/transaction. Never mutated after creation."""
    cur.execute(
        _INSERT_PROVENANCE,
        (
            lead_id.value,
            acquisition_channel.value,
            utm_source,
            utm_medium,
            utm_campaign,
            utm_term,
            utm_content,
            discovery_surface.value,
        ),
    )


def fetch_lead_acquisition_provenance(conn: Any, lead_id: LeadId) -> LeadProvenanceRecord | None:
    if not isinstance(lead_id, LeadId):
        raise TypeError(f"lead_id must be a LeadId, got {type(lead_id).__name__}")
    with conn.cursor() as cur:
        cur.execute(_SELECT_PROVENANCE, [lead_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return LeadProvenanceRecord(
        lead_id=LeadId(row[0]),
        acquisition_channel=AcquisitionChannel(row[1]),
        utm_source=row[2],
        utm_medium=row[3],
        utm_campaign=row[4],
        utm_term=row[5],
        utm_content=row[6],
        discovery_surface=DiscoverySurface(row[7]),
    )
