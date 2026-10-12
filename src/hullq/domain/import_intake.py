"""Multi-format broker inventory import intake — SLICE-0083.

Implements D26 (`docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`)
and `docs/slices/SLICE-0083-multiformat-broker-inventory-intake.md`: the
channel-neutral staged-row/batch identity model, explicit column-mapping
application onto the existing `hullq.domain.professional_listing_draft`
request shape, and the four durable outcome categories `CREATE_NEW_DRAFT`,
`ALREADY_IMPORTED`, `CONFLICT_REVIEW`, `INVALID`.

Pure and persistence-neutral: no database, no FastAPI, no parsing library
import. Format-specific byte parsing lives in `hullq.domain.import_parsers`
(CSV/TSV/JSON), `hullq.domain.import_spreadsheet` (XLSX/XLS/XLSB/ODS) and
`hullq.domain.import_nautix` (NautiX 1.4 XML) -- every one of those funnels
into the single `ParsedTable` shape this module maps/classifies (CSV/TSV/
Excel/JSON) or, for NautiX, directly into the single `StagedRowPreview`
shape via `hullq.domain.import_nautix.map_nautix_adverts_to_rows`. There is
exactly one staging/classification vocabulary, never a second one per
format (slice "ONE-CAPABILITY CHECK").

`StagedRowPreview.classification` is a three-way *content/mapping*
classification only (`VALID`/`INVALID`/`CONFLICT_REVIEW`, the latter used
only for a NautiX `status=inactive` source row -- "inactive is a source
status, not HullQ authorization to auto-withdraw", mechanical invariants).
Whether a `VALID` row is actually new or a replay of an already-imported or
since-changed source record requires the durable `(Organization,
ImportSource, SourceRecordKey)` mapping table and is therefore resolved one
layer up, in `hullq.application.import_intake`, never here.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.domain.listing_draft_payload import (
    ACCEPTED_DRAFT_PAYLOAD_KEYS,
    InvalidListingDraftPayloadError,
)
from hullq.domain.professional_listing_draft import (
    BROKER_DESCRIPTION_KEY,
    BROKER_LISTING_REFERENCE_KEY,
    parse_professional_listing_draft_request,
)

__all__ = [
    "IGNORE_TARGET",
    "MAPPABLE_TARGET_KEYS",
    "MAX_IMPORT_CELL_CHARS",
    "MAX_IMPORT_COLUMNS",
    "MAX_IMPORT_FILE_BYTES",
    "MAX_IMPORT_ROWS",
    "MAX_SOURCE_RECORD_KEY_CHARS",
    "SOURCE_RECORD_KEY_TARGET",
    "ImportBatchId",
    "ImportFormat",
    "ImportParseError",
    "ImportParseErrorKind",
    "ImportRowId",
    "ImportRowOutcome",
    "ImportSource",
    "InvalidColumnMappingError",
    "ParsedTable",
    "RowPreviewClassification",
    "SourceRecordKey",
    "StagedRowPreview",
    "apply_mapping_to_rows",
    "compute_file_sha256",
    "compute_row_digest",
    "normalize_source_record_key",
    "snapshot_source_record_key",
    "validate_mapping",
]


class ImportFormat(StrEnum):
    """The exact finite supported-format registry (slice support matrix).

    There is no "generic XML"/"generic CRM" member: an unrecognized upload
    is `UNSUPPORTED_FORMAT`, never silently coerced into one of these.
    """

    CSV = "CSV"
    TSV = "TSV"
    XLSX = "XLSX"
    XLS = "XLS"
    XLSB = "XLSB"
    ODS = "ODS"
    JSON = "JSON"
    NAUTIX_XML = "NAUTIX_XML"


#: Bounded bytes accepted for one uploaded import file -- generous for a
#: 30-300 listing broker export while bounding worst-case parser CPU/memory
#: (mechanical invariants: "bounded per-file size").
MAX_IMPORT_FILE_BYTES = 20_000_000

#: Bounded staged rows per batch (mechanical invariants: "row count ...
#: bounds are explicitly enforced").
MAX_IMPORT_ROWS = 2_000

#: Bounded columns per row -- guards against a pathological wide-table DoS.
MAX_IMPORT_COLUMNS = 200

#: Bounded raw cell text length -- guards against one pathological cell
#: inflating staged JSONB without bound.
MAX_IMPORT_CELL_CHARS = 4_000

#: Bounded `SourceRecordKey` length -- generous for a real broker reference
#: or NautiX `account_token:advert_id` composite while remaining bounded.
MAX_SOURCE_RECORD_KEY_CHARS = 200


class ImportParseErrorKind(StrEnum):
    """Mechanically distinct whole-file parse failures (never collapsed to
    a silent empty/zero-row result -- "absence-vs-error" mechanical
    invariant)."""

    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    MALFORMED = "MALFORMED"
    EMPTY = "EMPTY"
    OVERSIZE = "OVERSIZE"
    TOO_MANY_ROWS = "TOO_MANY_ROWS"
    TOO_MANY_COLUMNS = "TOO_MANY_COLUMNS"
    DUPLICATE_HEADER = "DUPLICATE_HEADER"
    ENCRYPTED = "ENCRYPTED"
    WORKSHEET_REQUIRED = "WORKSHEET_REQUIRED"
    WORKSHEET_NOT_FOUND = "WORKSHEET_NOT_FOUND"


class ImportParseError(Exception):
    """One whole-file/whole-worksheet parse failure. Callers must fail the
    whole batch closed with *kind*/*message*, never fabricate zero staged
    rows."""

    def __init__(self, kind: ImportParseErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


@dataclass(frozen=True)
class ImportBatchId:
    """Server-generated opaque import batch identity (D26). Deliberately a
    distinct runtime type from every marketplace/draft identity kind --
    never accepted interchangeably."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ImportBatchId.value must be non-empty")


@dataclass(frozen=True)
class ImportRowId:
    """Server-generated opaque import row identity (D26)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ImportRowId.value must be non-empty")


#: An Organization-chosen bounded logical namespace for one recurring
#: source (D26 §2: "Broker Org chooses a bounded ImportSource logical
#: namespace"). Deliberately plain, human-chosen text -- never a broker
#: reference or yacht identity (mechanical invariants).
_IMPORT_SOURCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{0,62}$")


@dataclass(frozen=True)
class ImportSource:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _IMPORT_SOURCE_PATTERN.fullmatch(self.value):
            raise ValueError(
                "ImportSource must be 1-63 characters of letters/digits/space/._- , "
                f"starting with a letter or digit, got {self.value!r}"
            )


@dataclass(frozen=True)
class SourceRecordKey:
    """The normalized `(Organization, ImportSource, SourceRecordKey)`
    identity-mapping key (D26). NEVER a `broker_listing_reference`,
    `PhysicalBoatId`, `MarketEpisodeId`, `BoatDesignRef`, HIN or yacht
    identity (mechanical invariants) -- it is an opaque import-dedup key
    only.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("SourceRecordKey.value must be a non-empty string")
        if len(self.value) > MAX_SOURCE_RECORD_KEY_CHARS:
            raise ValueError(
                f"SourceRecordKey.value must be at most {MAX_SOURCE_RECORD_KEY_CHARS} characters"
            )


def normalize_source_record_key(raw: str) -> SourceRecordKey:
    """The one normalization rule for a broker-supplied stable row id:
    stripped of leading/trailing whitespace, otherwise byte-for-byte --
    never case-folded or otherwise reinterpreted (a source system's own ID
    casing is its own identity, not HullQ's to normalize further)."""
    return SourceRecordKey(raw.strip())


def snapshot_source_record_key(file_sha256: str, row_ordinal: int) -> SourceRecordKey:
    """The explicit one-time snapshot mode key (mechanical invariants /
    Required Behavior #4): a server-authored namespace plus the exact
    immutable uploaded-file SHA-256 and row ordinal. A later changed upload
    for the same Organization/ImportSource necessarily produces different
    snapshot keys for every row, so it can never silently collide with -- or
    silently continue -- a prior snapshot batch's rows; the application
    layer separately classifies a *repeated* ImportSource with a *different*
    file digest as requiring `CONFLICT_REVIEW` continuity handling rather
    than inventing row-level continuity here.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", file_sha256):
        raise ValueError("file_sha256 must be a lowercase 64-character hex SHA-256 digest")
    if row_ordinal < 0:
        raise ValueError("row_ordinal must be non-negative")
    return SourceRecordKey(f"SNAPSHOT:{file_sha256}:{row_ordinal}")


def compute_file_sha256(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_row_digest(draft_request_wire: dict[str, Any]) -> str:
    """The exact-mapping idempotency digest (mechanical invariants:
    "Idempotency is per source record and exact mapping, not merely global
    SHA of a CSV filename"): a canonical-JSON hash of the coerced,
    draft-ready wire dict -- never the raw source bytes, so cosmetic raw-text
    noise outside the mapped fields never registers as a changed record."""
    canonical = json.dumps(draft_request_wire, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Parsed table -- the one shared shape CSV/TSV/Excel/JSON parsers produce.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedTable:
    """One bounded parsed table: a header row plus data rows, all raw
    strings -- format-specific typed/locale decisions already resolved, but
    *no* mapping/validation against draft keys yet. Every row is exactly
    `len(headers)` long (short-row padding/long-row rejection is each
    parser's own responsibility, enforced before this type is constructed).
    """

    headers: tuple[str, ...]
    rows: tuple[tuple[str | None, ...], ...]
    worksheet_name: str | None = None

    def __post_init__(self) -> None:
        if len(self.headers) != len(set(self.headers)):
            raise ImportParseError(
                ImportParseErrorKind.DUPLICATE_HEADER,
                "duplicate column header names are not permitted",
            )
        if len(self.headers) > MAX_IMPORT_COLUMNS:
            raise ImportParseError(
                ImportParseErrorKind.TOO_MANY_COLUMNS,
                f"more than {MAX_IMPORT_COLUMNS} columns",
            )
        if len(self.rows) > MAX_IMPORT_ROWS:
            raise ImportParseError(
                ImportParseErrorKind.TOO_MANY_ROWS, f"more than {MAX_IMPORT_ROWS} rows"
            )
        for row in self.rows:
            if len(row) != len(self.headers):
                raise ImportParseError(
                    ImportParseErrorKind.MALFORMED,
                    "a data row's column count does not match the header row",
                )


# ---------------------------------------------------------------------------
# Column mapping
# ---------------------------------------------------------------------------

#: Pseudo-target: this source column is explicitly reviewed and intentionally
#: not mapped to any draft field (Required Behavior #1/#3: unmapped fields
#: are reported, never silently dropped).
IGNORE_TARGET = "__ignore__"

#: Pseudo-target: this source column supplies the stable per-row
#: `SourceRecordKey` (Required Behavior #4). Mutually exclusive with
#: snapshot mode.
SOURCE_RECORD_KEY_TARGET = "__source_record_key__"

#: The complete set of real (non-pseudo) mapping targets: the nine
#: channel-neutral common draft keys plus the two professional-only fields.
MAPPABLE_TARGET_KEYS: frozenset[str] = ACCEPTED_DRAFT_PAYLOAD_KEYS | {
    BROKER_LISTING_REFERENCE_KEY,
    BROKER_DESCRIPTION_KEY,
}

_ALL_TARGETS: frozenset[str] = MAPPABLE_TARGET_KEYS | {IGNORE_TARGET, SOURCE_RECORD_KEY_TARGET}


class InvalidColumnMappingError(ValueError):
    """*mapping* is not a safe, complete, unambiguous assignment of every
    source column to exactly one target (Required Behavior #1: "Workbook
    worksheet choice and column matching are explicit; no implicit
    guessing")."""


def validate_mapping(
    headers: tuple[str, ...], mapping: dict[str, str], *, snapshot_mode: bool
) -> None:
    """Every *headers* entry must appear in *mapping* exactly once (no
    implicit default), every mapped target must be a known target, every
    real (non-ignore) target may be claimed by at most one column, and
    exactly one column maps to `SOURCE_RECORD_KEY_TARGET` iff *snapshot_mode*
    is `False` (mechanical invariants / Required Behavior #4: a safe
    explicit choice between a genuine stable id column and one-time
    snapshot mode -- never both, never neither).
    """
    header_set = set(headers)
    mapping_keys = set(mapping)
    if mapping_keys != header_set:
        missing = header_set - mapping_keys
        extra = mapping_keys - header_set
        raise InvalidColumnMappingError(
            f"mapping must cover every column exactly once; missing={sorted(missing)} "
            f"extra={sorted(extra)}"
        )

    target_counts: dict[str, int] = {}
    for header, target in mapping.items():
        if target not in _ALL_TARGETS:
            raise InvalidColumnMappingError(
                f"column {header!r} maps to an unknown target {target!r}"
            )
        if target != IGNORE_TARGET:
            target_counts[target] = target_counts.get(target, 0) + 1

    ambiguous = sorted(t for t, count in target_counts.items() if count > 1)
    if ambiguous:
        raise InvalidColumnMappingError(f"target(s) claimed by more than one column: {ambiguous}")

    key_column_count = target_counts.get(SOURCE_RECORD_KEY_TARGET, 0)
    if snapshot_mode and key_column_count > 0:
        raise InvalidColumnMappingError(
            "snapshot mode is selected but a source-record-key column is also mapped"
        )
    if not snapshot_mode and key_column_count != 1:
        raise InvalidColumnMappingError(
            "exactly one column must be mapped as the stable source-record-key column, "
            "or snapshot mode must be explicitly selected"
        )


# ---------------------------------------------------------------------------
# Row classification / staging
# ---------------------------------------------------------------------------


class RowPreviewClassification(StrEnum):
    """The content/mapping-level classification (see module docstring for
    why this is a three-way, not the full D26 four-way, outcome)."""

    VALID = "VALID"
    INVALID = "INVALID"
    CONFLICT_REVIEW = "CONFLICT_REVIEW"


class ImportRowOutcome(StrEnum):
    """D26's exact four durable per-row outcome categories. Resolved only
    at confirm time (`hullq.application.import_intake`), by comparing a
    `RowPreviewClassification.VALID` row's `row_digest` against the
    durable `(Organization, ImportSource, SourceRecordKey)` mapping table:
    a brand-new key -> `CREATE_NEW_DRAFT`; an existing key with a matching
    digest -> `ALREADY_IMPORTED`; an existing key with a different digest
    -> `CONFLICT_REVIEW`. A domain-level `INVALID`/`CONFLICT_REVIEW`
    `RowPreviewClassification` carries straight through unchanged.
    """

    CREATE_NEW_DRAFT = "CREATE_NEW_DRAFT"
    ALREADY_IMPORTED = "ALREADY_IMPORTED"
    CONFLICT_REVIEW = "CONFLICT_REVIEW"
    INVALID = "INVALID"


@dataclass(frozen=True)
class StagedRowPreview:
    row_ordinal: int
    raw_fields: dict[str, str | None]
    unmapped_headers: tuple[str, ...]
    classification: RowPreviewClassification
    reasons: tuple[str, ...]
    source_record_key: SourceRecordKey | None
    draft_request_wire: dict[str, Any] | None
    row_digest: str | None

    def __post_init__(self) -> None:
        has_draft = self.draft_request_wire is not None
        has_digest = self.row_digest is not None
        if has_draft != has_digest:
            raise ValueError("draft_request_wire and row_digest must be present/absent together")
        if self.classification is RowPreviewClassification.VALID and not has_draft:
            raise ValueError("a VALID row must carry a draft_request_wire/row_digest")
        if self.classification is not RowPreviewClassification.VALID and has_draft:
            raise ValueError("only a VALID row may carry a draft_request_wire/row_digest")


_CELL_PRICE_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
_CELL_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_CELL_COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
_CELL_YEAR_PATTERN = re.compile(r"^[0-9]{4}$")


def _coerce_cell_for_target(
    target_key: str, raw_value: str | None
) -> tuple[Any | None, str | None]:
    """Returns `(wire_value, None)` on success, `(None, reason)` on a
    field-level coercion failure, or `(None, None)` for a blank cell -- a
    blank cell always means "no claim for this row's this field", never a
    guessed value (core data guardrail: "Never invent missing boat data").

    No silent locale/decimal reinterpretation (slice support matrix): a
    thousands separator, currency symbol or non-ASCII-digit amount is a
    hard per-field error, never silently stripped/reparsed.
    """
    if raw_value is None:
        return None, None
    text = raw_value.strip()
    if text == "":
        return None, None
    if len(text) > MAX_IMPORT_CELL_CHARS:
        return None, f"{target_key}: cell exceeds {MAX_IMPORT_CELL_CHARS} characters"

    if target_key == "physical_boat.build_year":
        if not _CELL_YEAR_PATTERN.fullmatch(text):
            return None, f"{target_key}: expected a 4-digit year, got {raw_value!r}"
        return int(text), None
    if target_key == "listing_offer.asking_price_mode":
        upper = text.upper()
        if upper not in ("AMOUNT", "POA"):
            return None, f"{target_key}: expected AMOUNT or POA, got {raw_value!r}"
        return upper, None
    if target_key == "listing_offer.asking_price_amount":
        if not _CELL_PRICE_PATTERN.fullmatch(text):
            return (
                None,
                f"{target_key}: expected a plain decimal amount with no currency symbol or "
                f"thousands separator, got {raw_value!r}",
            )
        return text, None
    if target_key == "listing_offer.currency":
        upper = text.upper()
        if not _CELL_CURRENCY_PATTERN.fullmatch(upper):
            return None, f"{target_key}: expected a 3-letter ISO currency code, got {raw_value!r}"
        return upper, None
    if target_key == "listing_offer.location_country":
        upper = text.upper()
        if not _CELL_COUNTRY_PATTERN.fullmatch(upper):
            return None, f"{target_key}: expected a 2-letter ISO country code, got {raw_value!r}"
        return upper, None
    # Remaining plain-string targets: physical_boat.marketed_brand_claim,
    # physical_boat.model_designation_claim, physical_boat.boat_name,
    # listing_offer.location_region, broker_listing_reference,
    # listing_offer.broker_description -- pass the trimmed text through
    # unchanged (no hidden transformation).
    return text, None


def _row_with_invalid(row: StagedRowPreview, extra_reason: str) -> StagedRowPreview:
    return StagedRowPreview(
        row_ordinal=row.row_ordinal,
        raw_fields=row.raw_fields,
        unmapped_headers=row.unmapped_headers,
        classification=RowPreviewClassification.INVALID,
        reasons=(*row.reasons, extra_reason),
        source_record_key=row.source_record_key,
        draft_request_wire=None,
        row_digest=None,
    )


def apply_mapping_to_rows(
    table: ParsedTable,
    mapping: dict[str, str],
    *,
    snapshot_mode: bool,
    file_sha256: str,
) -> tuple[StagedRowPreview, ...]:
    """Apply *mapping* to every row of *table*, producing one
    `StagedRowPreview` per row, in order.

    Raises `InvalidColumnMappingError` for a malformed *mapping* itself
    (checked once, before any row is processed -- Required Behavior #4:
    "all rows get precise classification before confirmation").
    """
    validate_mapping(table.headers, mapping, snapshot_mode=snapshot_mode)
    header_index = {h: i for i, h in enumerate(table.headers)}
    key_column = next((h for h, t in mapping.items() if t == SOURCE_RECORD_KEY_TARGET), None)
    unmapped_headers = tuple(h for h, t in mapping.items() if t == IGNORE_TARGET)

    previews: list[StagedRowPreview] = []
    for ordinal, row in enumerate(table.rows):
        raw_fields: dict[str, str | None] = {h: row[header_index[h]] for h in table.headers}
        reasons: list[str] = []
        wire: dict[str, Any] = {}
        for header, target in mapping.items():
            if target in (IGNORE_TARGET, SOURCE_RECORD_KEY_TARGET):
                continue
            value, error = _coerce_cell_for_target(target, row[header_index[header]])
            if error is not None:
                reasons.append(error)
            elif value is not None:
                wire[target] = value

        source_record_key: SourceRecordKey | None
        if snapshot_mode:
            source_record_key = snapshot_source_record_key(file_sha256, ordinal)
        else:
            assert key_column is not None
            raw_key = row[header_index[key_column]]
            key_text = raw_key.strip() if raw_key is not None else ""
            if not key_text:
                reasons.append("source-record-key column is empty for this row")
                source_record_key = None
            else:
                source_record_key = normalize_source_record_key(key_text)

        draft_request_wire: dict[str, Any] | None = None
        if not reasons:
            try:
                parse_professional_listing_draft_request(wire)
            except InvalidListingDraftPayloadError as exc:
                reasons.append(str(exc))
            else:
                draft_request_wire = wire

        classification = (
            RowPreviewClassification.VALID if not reasons else RowPreviewClassification.INVALID
        )
        previews.append(
            StagedRowPreview(
                row_ordinal=ordinal,
                raw_fields=raw_fields,
                unmapped_headers=unmapped_headers,
                classification=classification,
                reasons=tuple(reasons),
                source_record_key=source_record_key,
                draft_request_wire=draft_request_wire,
                row_digest=compute_row_digest(draft_request_wire)
                if draft_request_wire is not None
                else None,
            )
        )

    if not snapshot_mode:
        key_to_ordinals: dict[str, list[int]] = {}
        for preview in previews:
            if preview.source_record_key is not None:
                key_to_ordinals.setdefault(preview.source_record_key.value, []).append(
                    preview.row_ordinal
                )
        duplicated = {
            ordinal
            for ordinals in key_to_ordinals.values()
            if len(ordinals) > 1
            for ordinal in ordinals
        }
        if duplicated:
            previews = [
                _row_with_invalid(
                    preview, "source-record-key is duplicated by another row in this file"
                )
                if preview.row_ordinal in duplicated
                else preview
                for preview in previews
            ]

    return tuple(previews)
