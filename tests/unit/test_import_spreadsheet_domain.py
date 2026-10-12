"""Pure domain unit tests for SLICE-0083 `hullq.domain.import_spreadsheet`
(XLSX/ODS via python-calamine).

XLS/XLSB fixtures are not exercised here: this session generated/verified
real representative fixtures only for XLSX (via `xlsxwriter`, dev-only) and
hand-authored ODS (plain zip + OpenDocument XML, no dependency). XLS/XLSB
share the identical `parse_spreadsheet_table` code path (calamine handles
all four formats uniformly) but have no representative fixture executed in
this session -- a documented gap, not a silent assumption of coverage
(slice stop-condition: "document the exact deficiency ... rather than
falsely mark the acceptance matrix complete").
"""

from __future__ import annotations

import io
import zipfile

import pytest
import xlsxwriter

from hullq.domain.import_intake import ImportFormat, ImportParseError, ImportParseErrorKind
from hullq.domain.import_spreadsheet import list_spreadsheet_worksheets, parse_spreadsheet_table


def _xlsx_bytes(sheet_name: str, rows: list[list[object]]) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet(sheet_name)
    for r, row in enumerate(rows):
        ws.write_row(r, 0, row)
    wb.close()
    return buf.getvalue()


class TestXlsx:
    def test_list_worksheets(self) -> None:
        raw = _xlsx_bytes("Inventory", [["a", "b"], ["1", "2"]])
        assert list_spreadsheet_worksheets(raw, ImportFormat.XLSX) == ("Inventory",)

    def test_parse_requires_explicit_worksheet(self) -> None:
        raw = _xlsx_bytes("Inventory", [["a"], ["1"]])
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(raw, ImportFormat.XLSX, worksheet_name=None)
        assert exc_info.value.kind is ImportParseErrorKind.WORKSHEET_REQUIRED

    def test_parse_rejects_unknown_worksheet(self) -> None:
        raw = _xlsx_bytes("Inventory", [["a"], ["1"]])
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(raw, ImportFormat.XLSX, worksheet_name="Nope")
        assert exc_info.value.kind is ImportParseErrorKind.WORKSHEET_NOT_FOUND

    def test_parses_typed_cells_to_text_without_float_noise(self) -> None:
        raw = _xlsx_bytes(
            "Inventory",
            [["Boat", "Year", "Price"], ["Aria", 1998, 19999.99], ["Beta", 2001, 25000]],
        )
        table = parse_spreadsheet_table(raw, ImportFormat.XLSX, worksheet_name="Inventory")
        assert table.headers == ("Boat", "Year", "Price")
        assert table.rows == (
            ("Aria", "1998", "19999.99"),
            ("Beta", "2001", "25000"),
        )

    def test_duplicate_header_rejected(self) -> None:
        raw = _xlsx_bytes("S", [["a", "a"], ["1", "2"]])
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(raw, ImportFormat.XLSX, worksheet_name="S")
        assert exc_info.value.kind is ImportParseErrorKind.DUPLICATE_HEADER

    def test_empty_file_rejected(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(b"", ImportFormat.XLSX, worksheet_name="S")
        assert exc_info.value.kind is ImportParseErrorKind.EMPTY

    def test_malformed_bytes_rejected(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(b"not a real xlsx file", ImportFormat.XLSX, worksheet_name="S")
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_macro_marker_entry_is_rejected_as_unsupported(self) -> None:
        """A `.xlsx`-shaped ZIP carrying a `vbaProject.bin` entry (macro
        content renamed to a non-macro extension) is rejected before
        calamine ever opens it."""
        raw = _xlsx_bytes("S", [["a"], ["1"]])
        archive_buf = io.BytesIO()
        with (
            zipfile.ZipFile(io.BytesIO(raw)) as original,
            zipfile.ZipFile(archive_buf, "w") as tampered,
        ):
            for name in original.namelist():
                tampered.writestr(name, original.read(name))
            tampered.writestr("xl/vbaProject.bin", b"fake macro content")
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(archive_buf.getvalue(), ImportFormat.XLSX, worksheet_name="S")
        assert exc_info.value.kind is ImportParseErrorKind.UNSUPPORTED_FORMAT

    def test_zip_bomb_declared_size_is_rejected(self) -> None:
        """A ZIP container whose central directory declares an implausible
        uncompressed size is rejected before calamine decompresses
        anything."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            info = zipfile.ZipInfo("huge.bin")
            # Lie about the uncompressed size in the local/central directory
            # metadata without actually writing that much data.
            archive.writestr(info, b"\x00" * 1000)
        raw = bytearray(buf.getvalue())
        # Patch every local/central-directory "uncompressed size" 4-byte
        # field (any occurrence of the real size, 1000, as little-endian
        # uint32) to an implausibly large value.
        real_size = (1000).to_bytes(4, "little")
        bomb_size = (500_000_000).to_bytes(4, "little")
        patched = bytes(raw).replace(real_size, bomb_size)
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(patched, ImportFormat.XLSX, worksheet_name="S")
        assert exc_info.value.kind in (
            ImportParseErrorKind.OVERSIZE,
            ImportParseErrorKind.MALFORMED,
        )
