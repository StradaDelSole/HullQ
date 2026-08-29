"""Persistence-neutral searchable projection input — SLICE-0033.

`SearchableDesignProjection` is the boundary type between the search kernel
and any future PostgreSQL/FastAPI layer: it carries only already-qualified
field values keyed by name, so search evaluation never has to read raw
BoatDesign/FieldResolution/DerivedMetrics artifacts directly (slice in-scope
item 9). Producing a projection from those artifacts is a future ingestion
concern outside this slice.

Does not implement: persistence, ResolvedConfiguration/option expansion, or
any BoatDesign/FieldResolution mutation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from hullq.search.types import ValueQualification
from hullq.search.values import QualifiedNumericValue

__all__ = ["SearchableDesignProjection"]

_MISSING = QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING)


@dataclass(frozen=True, slots=True)
class SearchableDesignProjection:
    """One design's qualified numeric field values, keyed by projection field name.

    `is_fixture` MUST be `True` for any projection built from test/demo data
    (slice Required Behavior §E) so a demo run can never be mistaken for a
    claim that the underlying record is a canonical searchable BoatDesign.
    """

    design_id: str
    values: Mapping[str, QualifiedNumericValue] = field(default_factory=dict)
    is_fixture: bool = False

    def __post_init__(self) -> None:
        if not self.design_id:
            raise ValueError("SearchableDesignProjection.design_id must be non-empty")
        object.__setattr__(self, "values", dict(self.values))

    def get(self, field_name: str) -> QualifiedNumericValue:
        """Return the qualified value for *field_name*, or MISSING if absent.

        A field absent from the projection is treated identically to a field
        present with an unqualified/missing status — never as a confirmed
        non-match — preserving the fail-closed guarantee even for an
        incomplete projection.
        """
        return self.values.get(field_name, _MISSING)
