"""Pure domain unit tests for SLICE-0083 `hullq.domain.import_spreadsheet`
(XLSX/XLS/XLSB/ODS via python-calamine).

Independent review amendment Finding D: XLSB and ODS are now exercised
against genuine third-party-authored files pinned from `python-calamine`'s
own upstream test corpus (provenance/licensing/hashes in
`tests/fixtures/spreadsheets/PROVENANCE.md`) rather than only structurally
reasoned about; XLS is exercised via `xlwt` (a true BIFF8 binary writer,
dev-only dependency) with content this repository fully controls. This
file also directly verifies the formula-cell fail-closed policy documented
in `hullq.domain.import_spreadsheet`'s module docstring against
hand-authored OOXML XML.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest
import xlsxwriter
import xlwt

from hullq.domain.import_intake import ImportFormat, ImportParseError, ImportParseErrorKind
from hullq.domain.import_spreadsheet import list_spreadsheet_worksheets, parse_spreadsheet_table

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "spreadsheets"


def _xlsx_bytes(sheet_name: str, rows: list[list[object]]) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet(sheet_name)
    for r, row in enumerate(rows):
        ws.write_row(r, 0, row)
    wb.close()
    return buf.getvalue()


def _xls_bytes(sheet_name: str, rows: list[list[object]]) -> bytes:
    buf = io.BytesIO()
    wb = xlwt.Workbook()
    ws = wb.add_sheet(sheet_name)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            ws.write(r, c, value)
    wb.save(buf)
    return buf.getvalue()


def _load_pinned_fixture(name: str, expected_sha256: str) -> bytes:
    raw = (_FIXTURES_DIR / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == expected_sha256, (
        f"{name} digest mismatch: expected {expected_sha256}, got {actual}"
    )
    return raw


# A minimal, hand-authored OOXML package -- used only to exercise the exact
# formula-cell fail-closed behavior documented in
# hullq.domain.import_spreadsheet's module docstring, which cannot be
# produced via xlsxwriter's own formula API (it cannot write an explicit
# error-typed cached value or omit a `<v>` cached value entirely).
_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""
_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""
_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""
_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="S" sheetId="1" r:id="rId1"/></sheets>
</workbook>
"""


def _formula_xlsx_bytes(row2_cell_xml: str) -> bytes:
    sheet1 = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
<row r="1"><c r="A1" t="str"><v>a</v></c></row>
<row r="2">{row2_cell_xml}</row>
</sheetData>
</worksheet>
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("xl/workbook.xml", _WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        z.writestr("xl/worksheets/sheet1.xml", sheet1)
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


class TestXls:
    """Genuine BIFF8 binary writes via `xlwt` (dev-only), content this
    repository fully controls."""

    def test_parses_typed_cells(self) -> None:
        raw = _xls_bytes("Inventory", [["Boat", "Year", "Price"], ["Aria", 1998, 125000]])
        table = parse_spreadsheet_table(raw, ImportFormat.XLS, worksheet_name="Inventory")
        assert table.headers == ("Boat", "Year", "Price")
        assert table.rows == (("Aria", "1998", "125000"),)

    def test_list_worksheets(self) -> None:
        raw = _xls_bytes("Inventory", [["a"], ["1"]])
        assert list_spreadsheet_worksheets(raw, ImportFormat.XLS) == ("Inventory",)

    def test_malformed_bytes_rejected(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_spreadsheet_table(b"not a real xls file", ImportFormat.XLS, worksheet_name="S")
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED


class TestGenuineThirdPartyXlsbAndOds:
    """Real third-party-authored files pinned from `python-calamine`'s own
    upstream test corpus -- see `tests/fixtures/spreadsheets/PROVENANCE.md`
    for source/license/digest. Proves genuine binary XLSB and ODS bytes
    this repository did not author parse correctly, not only files our own
    `xlsxwriter`/`xlwt` test helpers wrote."""

    def test_genuine_xlsb_parses(self) -> None:
        raw = _load_pinned_fixture(
            "calamine_date.xlsb",
            "68d36adf4d4de3890209e786eeb89a98778d25158628f83e96587e652fbb4eca",
        )
        assert list_spreadsheet_worksheets(raw, ImportFormat.XLSB) == ("Sheet1",)
        table = parse_spreadsheet_table(raw, ImportFormat.XLSB, worksheet_name="Sheet1")
        assert table.headers == ("2021-01-01", "15")
        assert len(table.rows) == 2
        assert table.rows[0][1] == "16"

    def test_genuine_ods_parses(self) -> None:
        raw = _load_pinned_fixture(
            "calamine_date.ods",
            "d65f3198bc73f2fad356e1b097215fc2f9a833fb802638217e5adc27fbba0466",
        )
        assert list_spreadsheet_worksheets(raw, ImportFormat.ODS) == ("Sheet1",)
        table = parse_spreadsheet_table(raw, ImportFormat.ODS, worksheet_name="Sheet1")
        assert table.headers == ("2021-01-01", "15")
        assert len(table.rows) == 3


class TestFormulaCellFailClosedPolicy:
    """Verified directly against hand-authored OOXML XML (not inferred):
    a formula with a genuine cached value is trusted; a formula with no
    cached value or an explicit error-typed cached value is safely blank
    -- never a fabricated literal (independent review amendment Finding
    D)."""

    def test_formula_with_genuine_cached_value_is_trusted(self) -> None:
        raw = _formula_xlsx_bytes('<c r="A2"><f>1+1</f><v>2</v></c>')
        table = parse_spreadsheet_table(raw, ImportFormat.XLSX, worksheet_name="S")
        assert table.rows == (("2",),)

    def test_formula_with_no_cached_value_is_blank_not_fabricated(self) -> None:
        raw = _formula_xlsx_bytes('<c r="A2"><f>1/0</f></c>')
        table = parse_spreadsheet_table(raw, ImportFormat.XLSX, worksheet_name="S")
        # skip_empty_area trims the now-entirely-blank trailing row.
        assert table.rows == ()

    def test_formula_with_error_typed_cached_value_is_blank_not_fabricated(self) -> None:
        raw = _formula_xlsx_bytes('<c r="A2" t="e"><f>1/0</f><v>#DIV/0!</v></c>')
        table = parse_spreadsheet_table(raw, ImportFormat.XLSX, worksheet_name="S")
        # calamine normalizes the explicit error-typed cached value to an
        # empty string (not dropped as a wholly-empty row, unlike the
        # no-`<v>`-at-all case above) -- still never the literal
        # "#DIV/0!" text or any other fabricated value, and still exactly
        # the same "blank cell" `_coerce_cell_for_target` always treats as
        # "no claim for this field" during mapping.
        assert table.rows == (("",),)
