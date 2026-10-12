"""Excel XLSX/XLS/XLSB and OpenDocument ODS import parser — SLICE-0083.

The single spreadsheet library candidate named by the slice,
`python-calamine`, backs every one of the four binary spreadsheet formats
through one code path: calamine itself never evaluates a formula or runs a
macro -- it reads the file's own last-cached cell value (slice support
matrix: "formula/macro execution prohibited"). This module adds the
pre-parse defenses calamine does not provide on its own: an explicit
macro-content/zip-bomb guard over the underlying ZIP container (XLSX/XLSB/
ODS are all ZIP packages) before calamine is ever invoked, on top of the
shared `MAX_IMPORT_FILE_BYTES` whole-file bound every format enforces.

Known, documented limitation (slice stop-condition: "document the exact
deficiency ... rather than falsely mark the acceptance matrix complete"):
calamine's `to_python()` returns a formula cell's cached computed value
(or an empty string if the file carries no cached value for it) and does
not expose whether a given cell was a literal or a formula. A formula cell
lacking a trustworthy cached value is therefore indistinguishable from a
genuinely blank cell and is treated the same safe way: omitted (never a
guessed value), surfaced to the broker only as a blank cell in the row
preview they explicitly review before confirming -- never a silently
fabricated field value.
"""

from __future__ import annotations

import datetime
import io
import zipfile
from typing import Any

import python_calamine as pc

from hullq.domain.import_intake import (
    MAX_IMPORT_CELL_CHARS,
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_FILE_BYTES,
    MAX_IMPORT_ROWS,
    ImportFormat,
    ImportParseError,
    ImportParseErrorKind,
    ParsedTable,
)

__all__ = ["list_spreadsheet_worksheets", "parse_spreadsheet_table"]

#: ZIP-container formats (XLSX, XLSB and ODS are all ZIP packages; legacy
#: binary XLS is not). Used only for the pre-parse macro/zip-bomb guard
#: below -- never for the actual cell parse, which calamine handles
#: uniformly for all four formats.
_ZIP_CONTAINER_FORMATS = frozenset({ImportFormat.XLSX, ImportFormat.XLSB, ImportFormat.ODS})

#: Case-insensitive ZIP-entry-name substrings that indicate embedded macro
#: content (OOXML VBA project / OpenDocument Basic macro library) renamed
#: to a non-macro extension.
_MACRO_ENTRY_MARKERS = ("vbaproject", "macros/", "basic/")

#: Defense-in-depth zip-bomb guard: a ZIP container declaring more than
#: this many bytes of *uncompressed* content, or more than this many
#: entries, is rejected before calamine ever decompresses anything --
#: `ZipInfo.file_size`/`namelist()` read only the ZIP central directory,
#: never decompress.
_MAX_ZIP_UNCOMPRESSED_BYTES = 200_000_000
_MAX_ZIP_ENTRIES = 10_000


def _guard_zip_container(raw_bytes: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            infos = archive.infolist()
            if len(infos) > _MAX_ZIP_ENTRIES:
                raise ImportParseError(
                    ImportParseErrorKind.OVERSIZE, "too many entries in the workbook container"
                )
            total_uncompressed = sum(info.file_size for info in infos)
            if total_uncompressed > _MAX_ZIP_UNCOMPRESSED_BYTES:
                raise ImportParseError(
                    ImportParseErrorKind.OVERSIZE,
                    "workbook container declares an implausibly large uncompressed size",
                )
            for info in infos:
                lowered = info.filename.lower()
                if any(marker in lowered for marker in _MACRO_ENTRY_MARKERS):
                    raise ImportParseError(
                        ImportParseErrorKind.UNSUPPORTED_FORMAT,
                        "macro-enabled workbook content is not supported",
                    )
    except zipfile.BadZipFile as exc:
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED, f"not a valid workbook container: {exc}"
        ) from exc


def _open_workbook(raw_bytes: bytes, fmt: ImportFormat) -> Any:
    if len(raw_bytes) > MAX_IMPORT_FILE_BYTES:
        raise ImportParseError(
            ImportParseErrorKind.OVERSIZE, "file exceeds the maximum upload size"
        )
    if len(raw_bytes) == 0:
        raise ImportParseError(ImportParseErrorKind.EMPTY, "file is empty")
    if fmt in _ZIP_CONTAINER_FORMATS:
        _guard_zip_container(raw_bytes)
    try:
        return pc.CalamineWorkbook.from_filelike(io.BytesIO(raw_bytes))
    except pc.PasswordError as exc:
        raise ImportParseError(
            ImportParseErrorKind.ENCRYPTED, "workbook is password-protected"
        ) from exc
    except (pc.CalamineError, pc.ZipError, pc.XmlError) as exc:
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED, f"malformed workbook: {exc}"
        ) from exc


def list_spreadsheet_worksheets(raw_bytes: bytes, fmt: ImportFormat) -> tuple[str, ...]:
    """The ordered worksheet-name list for explicit broker selection
    (Required Behavior #1: "Workbook worksheet choice ... explicit")."""
    workbook = _open_workbook(raw_bytes, fmt)
    try:
        return tuple(workbook.sheet_names)
    finally:
        workbook.close()


def _cell_to_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return repr(value)
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    raise ImportParseError(
        ImportParseErrorKind.MALFORMED, f"unsupported cell value type {type(value).__name__}"
    )


def _bound_cell_text(value: str | None) -> str | None:
    if value is not None and len(value) > MAX_IMPORT_CELL_CHARS:
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED, f"a cell exceeds {MAX_IMPORT_CELL_CHARS} characters"
        )
    return value


def parse_spreadsheet_table(
    raw_bytes: bytes, fmt: ImportFormat, *, worksheet_name: str | None
) -> ParsedTable:
    """Parse one explicit worksheet of an XLSX/XLS/XLSB/ODS workbook into
    the shared `ParsedTable` shape.

    *worksheet_name* is required (Required Behavior #1): a `None` or
    unknown name is `WORKSHEET_REQUIRED`/`WORKSHEET_NOT_FOUND`, never a
    silent default to "the first sheet".
    """
    workbook = _open_workbook(raw_bytes, fmt)
    try:
        sheet_names = tuple(workbook.sheet_names)
        if worksheet_name is None:
            raise ImportParseError(
                ImportParseErrorKind.WORKSHEET_REQUIRED,
                f"a worksheet must be explicitly selected from: {list(sheet_names)}",
            )
        if worksheet_name not in sheet_names:
            raise ImportParseError(
                ImportParseErrorKind.WORKSHEET_NOT_FOUND,
                f"worksheet {worksheet_name!r} not found; available: {list(sheet_names)}",
            )
        sheet = workbook.get_sheet_by_name(worksheet_name)
        try:
            rows = sheet.to_python(skip_empty_area=True)
        except pc.CalamineError as exc:
            raise ImportParseError(
                ImportParseErrorKind.MALFORMED, f"malformed worksheet content: {exc}"
            ) from exc
    finally:
        workbook.close()

    if not rows:
        raise ImportParseError(ImportParseErrorKind.EMPTY, "worksheet has no header row")

    header_cells = [_bound_cell_text(_cell_to_text(c)) for c in rows[0]]
    non_empty_headers: list[str] = []
    for cell in header_cells:
        if not cell:
            raise ImportParseError(
                ImportParseErrorKind.MALFORMED,
                "header row must have a non-empty name in every column",
            )
        non_empty_headers.append(cell)
    headers = tuple(non_empty_headers)
    if len(headers) != len(set(headers)):
        raise ImportParseError(
            ImportParseErrorKind.DUPLICATE_HEADER, "duplicate column header names"
        )
    if len(headers) > MAX_IMPORT_COLUMNS:
        raise ImportParseError(
            ImportParseErrorKind.TOO_MANY_COLUMNS, f"more than {MAX_IMPORT_COLUMNS} columns"
        )

    data_rows = rows[1:]
    if len(data_rows) > MAX_IMPORT_ROWS:
        raise ImportParseError(
            ImportParseErrorKind.TOO_MANY_ROWS, f"more than {MAX_IMPORT_ROWS} rows"
        )

    width = len(headers)
    normalized_rows: list[tuple[str | None, ...]] = []
    for row in data_rows:
        if len(row) > width:
            raise ImportParseError(
                ImportParseErrorKind.MALFORMED, "a data row has more columns than the header row"
            )
        cells = [_bound_cell_text(_cell_to_text(c)) for c in row]
        padded = tuple(cells) + (None,) * (width - len(cells))
        normalized_rows.append(padded)

    return ParsedTable(headers=headers, rows=tuple(normalized_rows), worksheet_name=worksheet_name)
