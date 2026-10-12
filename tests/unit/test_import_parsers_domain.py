"""Pure domain unit tests for SLICE-0083 `hullq.domain.import_parsers`
(CSV/TSV/JSON)."""

from __future__ import annotations

import pytest

from hullq.domain.import_intake import ImportParseError, ImportParseErrorKind
from hullq.domain.import_parsers import parse_delimited_table, parse_json_table


class TestParseDelimitedTableCsv:
    def test_parses_simple_csv(self) -> None:
        table = parse_delimited_table(b"a,b\r\n1,2\r\n3,4\r\n", delimiter=",")
        assert table.headers == ("a", "b")
        assert table.rows == (("1", "2"), ("3", "4"))

    def test_strips_utf8_bom(self) -> None:
        table = parse_delimited_table("﻿a,b\r\n1,2\r\n".encode(), delimiter=",")
        assert table.headers == ("a", "b")

    def test_handles_quoted_commas(self) -> None:
        table = parse_delimited_table(b'name,note\r\n"Aria","hello, world"\r\n', delimiter=",")
        assert table.rows == (("Aria", "hello, world"),)

    def test_preserves_formula_leading_text_inert(self) -> None:
        table = parse_delimited_table(b'a\r\n"=1+1"\r\n', delimiter=",")
        assert table.rows == (("=1+1",),)

    def test_short_row_padded_with_none(self) -> None:
        table = parse_delimited_table(b"a,b,c\r\n1\r\n", delimiter=",")
        assert table.rows == (("1", None, None),)

    def test_long_row_is_malformed(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_delimited_table(b"a,b\r\n1,2,3\r\n", delimiter=",")
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_duplicate_header_is_rejected(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_delimited_table(b"a,a\r\n1,2\r\n", delimiter=",")
        assert exc_info.value.kind is ImportParseErrorKind.DUPLICATE_HEADER

    def test_empty_file_is_rejected(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_delimited_table(b"", delimiter=",")
        assert exc_info.value.kind is ImportParseErrorKind.EMPTY

    def test_header_only_parses_to_zero_rows_not_an_error(self) -> None:
        """Confirmed zero rows is a valid success, never conflated with a
        parse error (absence-vs-error mechanical invariant)."""
        table = parse_delimited_table(b"a,b\r\n", delimiter=",")
        assert table.headers == ("a", "b")
        assert table.rows == ()

    def test_invalid_utf8_is_malformed(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_delimited_table(b"a,b\r\n\xff\xfe,2\r\n", delimiter=",")
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED


class TestParseDelimitedTableTsv:
    def test_parses_tab_separated(self) -> None:
        table = parse_delimited_table(b"a\tb\r\n1\t2\r\n", delimiter="\t")
        assert table.headers == ("a", "b")
        assert table.rows == (("1", "2"),)

    def test_semicolon_dialect_via_explicit_delimiter(self) -> None:
        table = parse_delimited_table(b"a;b\r\n1;2\r\n", delimiter=";")
        assert table.headers == ("a", "b")


class TestParseJsonTable:
    def test_parses_top_level_array(self) -> None:
        table = parse_json_table(b'[{"a": 1, "b": "x"}, {"a": 2}]')
        assert table.headers == ("a", "b")
        assert table.rows == (("1", "x"), ("2", None))

    def test_parses_listings_profile(self) -> None:
        table = parse_json_table(b'{"listings": [{"a": "x"}]}')
        assert table.headers == ("a",)
        assert table.rows == (("x",),)

    def test_rejects_unknown_top_level_object_shape(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_json_table(b'{"records": []}')
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_rejects_non_array_non_object(self) -> None:
        with pytest.raises(ImportParseError):
            parse_json_table(b'"just a string"')

    def test_rejects_non_scalar_row_value(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_json_table(b'[{"a": {"nested": true}}]')
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_rejects_duplicate_key_in_one_row(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_json_table(b'[{"a": 1, "a": 2}]')
        assert exc_info.value.kind is ImportParseErrorKind.DUPLICATE_HEADER

    def test_boolean_and_null_render_as_text(self) -> None:
        table = parse_json_table(b'[{"a": true, "b": false, "c": null}]')
        assert table.rows == (("true", "false", None),)

    def test_rejects_empty_array(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_json_table(b"[]")
        assert exc_info.value.kind is ImportParseErrorKind.EMPTY

    def test_rejects_invalid_json(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_json_table(b"{not valid json")
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_rejects_invalid_utf8(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_json_table(b"\xff\xfe")
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED
