"""Unit tests for hullq.search.projection — SLICE-0033.

Covers:
- design_id required
- get() returns the stored qualified value
- get() fails closed to MISSING for a field absent from the projection
- values mapping is defensively copied (snapshot safety)
"""

from __future__ import annotations

import pytest

from hullq.search.projection import SearchableDesignProjection
from hullq.search.types import ValueQualification
from hullq.search.values import QualifiedNumericValue


def test_design_id_required() -> None:
    with pytest.raises(ValueError, match="design_id"):
        SearchableDesignProjection(design_id="")


def test_get_returns_stored_value() -> None:
    qv = QualifiedNumericValue(value=11.2, qualification=ValueQualification.CONFIRMED)
    projection = SearchableDesignProjection(design_id="d1", values={"loa_m": qv})
    assert projection.get("loa_m") is qv


def test_get_fails_closed_to_missing_for_absent_field() -> None:
    projection = SearchableDesignProjection(design_id="d1", values={})
    result = projection.get("draft_max_m")
    assert result.qualification is ValueQualification.MISSING
    assert result.value is None


def test_values_mapping_is_copied_defensively() -> None:
    source: dict[str, QualifiedNumericValue] = {
        "loa_m": QualifiedNumericValue(value=11.0, qualification=ValueQualification.CONFIRMED)
    }
    projection = SearchableDesignProjection(design_id="d1", values=source)
    source["beam_m"] = QualifiedNumericValue(value=4.0, qualification=ValueQualification.CONFIRMED)
    assert projection.get("beam_m").qualification is ValueQualification.MISSING


def test_is_fixture_defaults_false() -> None:
    projection = SearchableDesignProjection(design_id="d1")
    assert projection.is_fixture is False
