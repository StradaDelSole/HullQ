"""Shared strict recognized-archive-surface definition for SLICE-0019.

An internal HullQ research packet (retained under ``other_archive_sources``
purely for provenance, e.g. the RESEARCH-007..009 batch files) MUST NEVER by
itself count as an external official/recognized heritage/archive surface. The
only things that count are:

- a populated ``official_heritage_archive``; or
- a retained source whose ``source_type`` is one of the recognized categories
  below.

``build_registry.py`` (validation) and ``build_report.py`` (reporting) must
both call this single helper so the enforced floor and the reported count can
never diverge.
"""

from __future__ import annotations

from typing import Any

RECOGNIZED_ARCHIVE_SOURCE_TYPES = frozenset(
    {
        "official_heritage_archive",
        "designer_archive",
        "class_or_owners_association",
        "museum_or_archive",
    }
)


def has_recognized_archive_surface(record: dict[str, Any]) -> bool:
    """True only if the record has a defensible external heritage/archive surface.

    ``other_archive_sources`` is deliberately excluded: for SLICE-0019 it holds
    provenance pointers such as the internal RESEARCH-007..009 research-batch
    files, which are not themselves recognized external archive surfaces.
    """
    if record.get("official_heritage_archive"):
        return True
    return any(
        source.get("source_type") in RECOGNIZED_ARCHIVE_SOURCE_TYPES
        for source in record.get("sources", [])
    )


def recognized_archive_surface_count(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if has_recognized_archive_surface(record))
