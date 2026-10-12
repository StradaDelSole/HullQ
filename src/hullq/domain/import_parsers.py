"""CSV / TSV / JSON import parsers — SLICE-0083.

Pure, stdlib-only parsers that turn raw uploaded bytes into the one shared
`hullq.domain.import_intake.ParsedTable` shape. No database, no FastAPI, no
guessed encoding/dialect beyond the explicit rules documented below (slice
support matrix: "No silent wrong decimal/locale parsing ... or hidden
Excel reinterpretation").
"""

from __future__ import annotations

import csv
import io
import json

from hullq.domain.import_intake import (
    MAX_IMPORT_CELL_CHARS,
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_ROWS,
    ImportParseError,
    ImportParseErrorKind,
    ParsedTable,
)

__all__ = ["parse_delimited_table", "parse_json_table"]

#: Required JSON-profile row member set mirrors the delimited/spreadsheet
#: shape: a flat object of string keys. Nested objects/arrays as values are
#: rejected rather than silently stringified (no implicit reinterpretation).
_JSON_ROW_SCALAR_TYPES = (str, int, float, bool, type(None))


def _decode_bytes(raw_bytes: bytes) -> str:
    """UTF-8, optional BOM -- the one documented encoding (slice support
    matrix: "UTF-8 (optional BOM)"). Any other encoding/invalid UTF-8 is a
    `MALFORMED` failure, never a best-effort re-decode."""
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED, f"file is not valid UTF-8: {exc}"
        ) from exc


def _bound_cell(value: str | None) -> str | None:
    if value is not None and len(value) > MAX_IMPORT_CELL_CHARS:
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED,
            f"a cell exceeds {MAX_IMPORT_CELL_CHARS} characters",
        )
    return value


def parse_delimited_table(raw_bytes: bytes, *, delimiter: str) -> ParsedTable:
    """CSV (`delimiter=","`) / TSV (`delimiter="\\t"`) parser.

    Deterministic dialect: the exact *delimiter*, `"` as the sole quote
    character, doubled-quote escaping, and `\\r\\n`/`\\n` line endings via
    `csv.reader`'s own universal-newline handling -- never `csv.Sniffer` or
    any other dialect guess. A formula-leading cell value (`=`, `+`, `-`,
    `@`) is accepted and stored as inert plain text: this parser never
    evaluates a formula and the web layer HTML-escapes all raw strings, so
    the exact leading character is preserved rather than guessed/stripped.
    """
    text = _decode_bytes(raw_bytes)
    if text == "":
        raise ImportParseError(ImportParseErrorKind.EMPTY, "file is empty")

    reader = csv.reader(io.StringIO(text), delimiter=delimiter, quotechar='"')
    try:
        raw_rows = list(reader)
    except csv.Error as exc:
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED, f"malformed delimited text: {exc}"
        ) from exc

    # Trailing fully-blank lines are common in broker exports and carry no
    # data; drop them rather than rejecting the whole file as malformed.
    while raw_rows and all(cell == "" for cell in raw_rows[-1]):
        raw_rows.pop()

    if not raw_rows:
        raise ImportParseError(ImportParseErrorKind.EMPTY, "file has no header row")

    header_row = raw_rows[0]
    if len(header_row) != len(set(header_row)):
        raise ImportParseError(
            ImportParseErrorKind.DUPLICATE_HEADER, "duplicate column header names"
        )
    if len(header_row) > MAX_IMPORT_COLUMNS:
        raise ImportParseError(
            ImportParseErrorKind.TOO_MANY_COLUMNS, f"more than {MAX_IMPORT_COLUMNS} columns"
        )

    data_rows = raw_rows[1:]
    if len(data_rows) > MAX_IMPORT_ROWS:
        raise ImportParseError(
            ImportParseErrorKind.TOO_MANY_ROWS, f"more than {MAX_IMPORT_ROWS} rows"
        )

    width = len(header_row)
    normalized_rows: list[tuple[str | None, ...]] = []
    for row in data_rows:
        if len(row) > width:
            raise ImportParseError(
                ImportParseErrorKind.MALFORMED,
                "a data row has more columns than the header row",
            )
        padded = tuple(row) + (None,) * (width - len(row))
        normalized_rows.append(tuple(_bound_cell(cell) for cell in padded))

    return ParsedTable(headers=tuple(header_row), rows=tuple(normalized_rows))


def _json_row_to_cells(
    row: dict[str, object], headers: list[str], header_index: dict[str, int]
) -> list[str | None]:
    cells: list[str | None] = [None] * len(headers)
    for key, value in row.items():
        if key not in header_index:
            continue  # filled in by the caller's header-union pass
        if value is None:
            cells[header_index[key]] = None
        elif isinstance(value, str):
            cells[header_index[key]] = value
        elif isinstance(value, bool):
            cells[header_index[key]] = "true" if value else "false"
        elif isinstance(value, int | float):
            cells[header_index[key]] = str(value)
        else:
            raise ImportParseError(
                ImportParseErrorKind.MALFORMED,
                f"row field {key!r} must be a scalar (string/number/boolean/null), "
                f"got {type(value).__name__}",
            )
    return cells


def _object_pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ImportParseError(
                ImportParseErrorKind.DUPLICATE_HEADER, f"duplicate JSON object key {key!r}"
            )
        seen.add(key)
    return dict(pairs)


def parse_json_table(raw_bytes: bytes) -> ParsedTable:
    """Strict structured-JSON parser (slice support matrix: "UTF-8 JSON
    array or documented `{listings:[...]}` profile; strict top-level/row
    keys").

    Accepts a top-level JSON array of row objects, or a top-level object
    with exactly one member `"listings"` whose value is such an array.
    Every row must be a flat object of string keys to scalar values -- a
    duplicate key within one row object, a non-scalar value, or any other
    top-level shape is `MALFORMED`. The column set is the ordered union of
    every row's keys (a row omitting a key simply leaves that cell blank --
    never an error, since sparse records are an accepted JSON import
    shape).
    """
    text = _decode_bytes(raw_bytes)
    if text.strip() == "":
        raise ImportParseError(ImportParseErrorKind.EMPTY, "file is empty")

    try:
        parsed = json.loads(text, object_pairs_hook=_object_pairs_hook)
    except ImportParseError:
        raise
    except json.JSONDecodeError as exc:
        raise ImportParseError(ImportParseErrorKind.MALFORMED, f"invalid JSON: {exc}") from exc

    if isinstance(parsed, dict):
        if set(parsed) != {"listings"}:
            raise ImportParseError(
                ImportParseErrorKind.MALFORMED,
                'a top-level JSON object must have exactly one member: "listings"',
            )
        rows_raw = parsed["listings"]
    else:
        rows_raw = parsed

    if not isinstance(rows_raw, list):
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED, "expected a top-level JSON array of row objects"
        )
    if len(rows_raw) == 0:
        raise ImportParseError(ImportParseErrorKind.EMPTY, "no rows present")
    if len(rows_raw) > MAX_IMPORT_ROWS:
        raise ImportParseError(
            ImportParseErrorKind.TOO_MANY_ROWS, f"more than {MAX_IMPORT_ROWS} rows"
        )

    for row in rows_raw:
        if not isinstance(row, dict):
            raise ImportParseError(
                ImportParseErrorKind.MALFORMED, "every row must be a flat JSON object"
            )

    headers: list[str] = []
    header_index: dict[str, int] = {}
    for row in rows_raw:
        for key in row:
            if not isinstance(key, str):
                raise ImportParseError(ImportParseErrorKind.MALFORMED, "row keys must be strings")
            if key not in header_index:
                header_index[key] = len(headers)
                headers.append(key)
    if len(headers) > MAX_IMPORT_COLUMNS:
        raise ImportParseError(
            ImportParseErrorKind.TOO_MANY_COLUMNS, f"more than {MAX_IMPORT_COLUMNS} columns"
        )

    normalized_rows: list[tuple[str | None, ...]] = []
    for row in rows_raw:
        cells = _json_row_to_cells(row, headers, header_index)
        normalized_rows.append(tuple(_bound_cell(cell) for cell in cells))

    return ParsedTable(headers=tuple(headers), rows=tuple(normalized_rows))
