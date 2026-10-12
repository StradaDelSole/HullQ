"""Pure unit tests for SLICE-0082's `hullq.domain.boat_design_association` --
no PostgreSQL/FastAPI dependency.

Covers the bounded selector query parse, the exactly-one-key association
request parse, and the fixed `DesignConfirmationMethod` vocabulary.
"""

from __future__ import annotations

import pytest

from hullq.domain.boat_design_association import (
    DESIGN_SELECTOR_MAX_RESULTS,
    MAX_DESIGN_SELECTOR_QUERY_LENGTH,
    DesignConfirmationMethod,
    InvalidDesignAssociationRequestError,
    InvalidDesignSelectorQueryError,
    parse_design_association_request,
    parse_design_selector_query,
)
from hullq.domain.market_identity import BoatDesignRef


class TestParseDesignSelectorQuery:
    def test_none_means_no_filter(self) -> None:
        assert parse_design_selector_query(None) == ""

    def test_missing_like_none(self) -> None:
        assert parse_design_selector_query("") == ""

    def test_strips_whitespace(self) -> None:
        assert parse_design_selector_query("  Oceanis 46  ") == "Oceanis 46"

    def test_non_string_rejected(self) -> None:
        with pytest.raises(InvalidDesignSelectorQueryError):
            parse_design_selector_query(123)

    def test_over_max_length_rejected(self) -> None:
        with pytest.raises(InvalidDesignSelectorQueryError):
            parse_design_selector_query("x" * (MAX_DESIGN_SELECTOR_QUERY_LENGTH + 1))

    def test_exactly_max_length_accepted(self) -> None:
        term = "x" * MAX_DESIGN_SELECTOR_QUERY_LENGTH
        assert parse_design_selector_query(term) == term


class TestParseDesignAssociationRequest:
    def test_valid_request_parses(self) -> None:
        parsed = parse_design_association_request({"boat_design_ref": "BD-001"})
        assert parsed == BoatDesignRef("BD-001")

    def test_missing_key_is_invalid(self) -> None:
        with pytest.raises(InvalidDesignAssociationRequestError):
            parse_design_association_request({})

    def test_unknown_key_is_invalid(self) -> None:
        with pytest.raises(InvalidDesignAssociationRequestError):
            parse_design_association_request({"boat_design_ref": "BD-001", "extra": "x"})

    def test_non_dict_body_is_invalid(self) -> None:
        with pytest.raises(InvalidDesignAssociationRequestError):
            parse_design_association_request("BD-001")

    def test_null_value_is_invalid(self) -> None:
        with pytest.raises(InvalidDesignAssociationRequestError):
            parse_design_association_request({"boat_design_ref": None})

    def test_empty_string_value_is_invalid(self) -> None:
        with pytest.raises(InvalidDesignAssociationRequestError):
            parse_design_association_request({"boat_design_ref": ""})

    def test_non_string_value_is_invalid(self) -> None:
        with pytest.raises(InvalidDesignAssociationRequestError):
            parse_design_association_request({"boat_design_ref": 123})

    def test_native_listing_id_shaped_value_is_not_rejected_by_kind(self) -> None:
        """A non-empty string is accepted regardless of which identity kind
        it happens to resemble -- construction-time kind separation is
        `BoatDesignRef`'s own job (SLICE-0040 contract), not this parser's;
        this parser only enforces the wire shape."""
        parsed = parse_design_association_request({"boat_design_ref": "NL-NOT-A-DESIGN"})
        assert parsed == BoatDesignRef("NL-NOT-A-DESIGN")


def test_design_selector_max_results_is_twenty() -> None:
    assert DESIGN_SELECTOR_MAX_RESULTS == 20


def test_confirmation_method_has_exactly_one_value() -> None:
    assert list(DesignConfirmationMethod) == [DesignConfirmationMethod.MANUAL_SELECTOR_CONFIRMATION]
