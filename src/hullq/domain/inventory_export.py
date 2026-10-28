"""Broker inventory portability export — SLICE-0088 (2026-10-16 seven-format amendment).

Pure, persistence-neutral domain core for the Owner-accepted broker export
capability: one immutable, bounded, Organization-scoped canonical
``ExportRow`` per selected private draft or promoted listing, a per-row
per-format preflight (`build_row_preflight`), and seven genuine writer
adapters: CSV, TSV, XLSX, XLS, ODS, structured JSON and NautiX 1.4
``adverts.xml``.

**XLSB export is explicitly out of scope** (`ExportFormat` has no XLSB
member): `docs/SLICE_0088_XLSB_WRITER_FEASIBILITY_BLOCKER_2026-10-16.md`
found no sufficiently vetted/approved XLSB writer for HullQ's pinned
CPython 3.14 baseline. Durably tracked in GitHub issue #362. XLSB
**import** (`hullq.domain.import_spreadsheet`) is unaffected.

This module contains no database/FastAPI access and performs no network
I/O. Assembling the canonical, authorization-checked rows from PostgreSQL
is `hullq.application.inventory_export`'s job; this module only ever sees
already-authorized, already-selected rows.

NautiX representability gap and its resolution (review amendment,
2026-10-16): HullQ's broker draft/offer schema (`hullq.domain
.listing_draft_payload`) does not itself capture a new/used `sale_class`
distinction, nor a destination-platform account token / office id, and
`loa_length`/`boat_name` are two of several fields that may be explicit
UNKNOWN or simply absent. Per the slice's own "Absence-vs-error / fail-
closed behavior" invariant, a row missing any NautiX-mandatory field is
`NOT_EXPORTABLE` with an explicit reason -- **never** a fabricated
default, and never a placeholder identity value (a prior revision of this
module hardcoded `office_id="default"`; that was exactly the kind of
fabrication this invariant forbids and has been removed).

Three fields -- `sale_class`, `nautix_account_token`, `nautix_office_id`
-- are therefore never read from stored HullQ listing/offer/claim data at
all. They are populated only from an explicit, per-download, broker-
confirmed **NautiX export profile** (`hullq.application.inventory_export
.NautixExportProfile`): the broker's own destination-platform account
token and office id (data only the broker can know -- HullQ has no
opinion on any other platform's account namespace), and, per selected
listing, the broker's own new/used sale classification. This is the
broker's own confirmed assertion for this one download, scoped to this
export and never persisted as HullQ listing/offer/claim truth -- the
identical discipline already accepted for `listing_offer.broker_summary`/
`vat_tax_status_claim` ("a stored value here is always a broker claim,
never a HullQ legal verification"). Omitting the profile leaves every row
honestly `NOT_EXPORTABLE` for NautiX; the other six formats are
unaffected.

`boat_type` remains the sole unconditional default: every HullQ listing
is, by definition of HullQ's current sailboat-only catalog scope, a
sailing boat, so the generic catalog-wide `sail-yacht` category is a true
structural fact about HullQ itself, not a per-row marketing assertion
about any particular boat.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

from lxml import etree

from hullq.domain.import_nautix import NAUTIX_V14_NAMESPACE

__all__ = [
    "ALLOWED_NAUTIX_SALE_CLASSES",
    "EXPORT_COLUMNS",
    "MAX_EXPORT_MEDIA_PER_ROW",
    "MAX_EXPORT_OUTPUT_BYTES",
    "MAX_EXPORT_ROWS",
    "MAX_XLS_ROWS",
    "ExportFieldState",
    "ExportFormat",
    "ExportRow",
    "ExportSourceKind",
    "ExportWriteError",
    "FormatPreflight",
    "RowPreflight",
    "build_nautix_document",
    "build_row_preflight",
    "escape_formula_injection",
    "write_csv",
    "write_json",
    "write_ods",
    "write_tsv",
    "write_xls",
    "write_xlsx",
]


class ExportFormat(StrEnum):
    """The exact finite Owner-accepted export-format registry.

    Deliberately seven members. XLSB is not, and must never become, a
    member of this enum within SLICE-0088 (2026-10-16 amendment) -- adding
    it back requires a separate Owner-accepted writer-feasibility decision,
    tracked in GitHub issue #362.
    """

    CSV = "CSV"
    TSV = "TSV"
    XLSX = "XLSX"
    XLS = "XLS"
    ODS = "ODS"
    JSON = "JSON"
    NAUTIX = "NAUTIX"


#: Bounded selection size for one export (mechanical invariants: "Output
#: size/listing count ... limits are deterministic"). Generous for a real
#: 30-300 listing broker while bounding worst-case serializer CPU/memory.
MAX_EXPORT_ROWS = 500

#: xlwt (legacy BIFF8 .xls) hard-fails above 65536 rows; kept well clear of
#: that ceiling rather than relying on xlwt's own error for a bound this
#: module already enforces for every format.
MAX_XLS_ROWS = 60_000

#: Bounded approved photo count per row carried into a NautiX advert --
#: mirrors `hullq.domain.import_nautix`'s identical bound on the read side.
MAX_EXPORT_MEDIA_PER_ROW = 20

#: Bounded single-cell text length (mirrors `hullq.domain.import_intake
#: .MAX_IMPORT_CELL_CHARS`) -- guards against one pathological field
#: inflating a row without bound. An application-layer value exceeding this
#: is an upstream invariant violation (every accepted draft/offer string
#: field is already bounded well below this), so writers raise rather than
#: silently truncate.
MAX_EXPORT_CELL_CHARS = 4_000

#: Bounded total serialized output size (mechanical invariants: "Output
#: size/listing count ... limits are deterministic"). `MAX_EXPORT_ROWS *
#: (len(EXPORT_COLUMNS) * MAX_EXPORT_CELL_CHARS)` bounds worst-case
#: table-format text well under this; enforced explicitly after writing
#: (never during, which would require re-architecting each writer) so an
#: unexpectedly oversized result fails closed as a writer error rather
#: than being returned as a successful partial/complete file.
MAX_EXPORT_OUTPUT_BYTES = 25_000_000

#: The pinned XSD's `SaleClass` enumeration, excluding `not-applicable`
#: ("not usable for boats" per the schema's own comment). Never inferred
#: from HullQ listing/offer/claim data (module docstring) -- only ever
#: set from an explicit broker-confirmed `NautixExportProfile` value.
ALLOWED_NAUTIX_SALE_CLASSES: frozenset[str] = frozenset(
    {
        "used",
        "used-excharter",
        "demo-inwater",
        "demo-exhibition",
        "new",
        "new-instock",
        "new-inorder",
        "new-onorder",
    }
)
_ALLOWED_SALE_CLASSES = ALLOWED_NAUTIX_SALE_CLASSES
#: SLICE-0093 (review amendment Finding B): `hullq.domain.vessel_category
#: .VesselCategoryResolution`'s own five-value vocabulary, mirrored here
#: rather than imported so this pure export-domain module keeps no
#: dependency on the category-resolution module. `ExportRow.vessel_category`
#: carries the *resolved* category state (design + concrete + cross-
#: Organization, combined by `hullq.domain.vessel_category
#: .resolve_vessel_category`) -- never only the publisher's own raw claim --
#: so `CONFLICT` is a legitimate stored value here, distinct from the three
#: positive `VesselCategory` claim values and from `UNKNOWN`.
_VESSEL_CATEGORY_VALUES = frozenset({"SAIL", "POWER", "MOTORSAILER", "UNKNOWN", "CONFLICT"})
#: The explicit resolved states that must fail a NautiX row closed -- the
#: identical POWER/MOTORSAILER/CONFLICT set `hullq.domain.vessel_category
#: .VesselCategoryResolutionResult.is_explicitly_non_sail_or_conflicted`
#: already defines for the Sail technical Search pre-filter, reused here for
#: the identical "explicitly not confirmed SAIL" meaning. `None`/`"SAIL"`/
#: `"UNKNOWN"` all pass through unblocked -- preserving every pre-0093 row's
#: existing default-SAIL NautiX assumption exactly (a row whose category was
#: never resolved, or resolves to legacy UNKNOWN, is not thereby proven
#: non-SAIL).
_NAUTIX_EXCLUDED_VESSEL_CATEGORIES = frozenset({"POWER", "MOTORSAILER", "CONFLICT"})


class ExportWriteError(Exception):
    """A serializer/IO failure. Callers must treat this as a hard failure --
    never a partial successful file, never a durable side effect."""


class ExportSourceKind(StrEnum):
    """Which authoritative HullQ record one `ExportRow` was snapshotted
    from -- never conflated (a private draft can never silently become a
    promoted-listing row or vice versa)."""

    PRIVATE_DRAFT = "PRIVATE_DRAFT"
    PROMOTED_LISTING = "PROMOTED_LISTING"


@dataclass(frozen=True)
class ExportRow:
    """One immutable canonical export row.

    Every field below is either exactly what the owning Organization itself
    authored (draft payload / current offer / current own-Organization
    PhysicalBoat claim) or a fact HullQ itself already computed about that
    exact row from one consistent snapshot (`status`, `is_current_public`,
    approved rights-cleared media). Nothing here is inferred from another
    Organization's claim or from canonical qualified BoatDesign-only Search
    facts (core guardrail: "Qualified design data does NOT become seller
    assertion").

    `*_unknown` flags distinguish an explicit broker UNKNOWN assertion from
    plain omission (`core guardrail: "Missing/unknown is not evidence that a
    characteristic is absent"`) -- when `True` the corresponding value field
    is always `None`.

    `media_urls`/`media_md5s` are parallel, position-ordered tuples of equal
    length; `media_md5s[i]` is the asset's own content hash when it happens
    to already be in exactly the NautiX `Md5Value` shape (32 lowercase/
    uppercase hex characters), else `None` -- never a recomputed/invented
    checksum.
    """

    export_id: str
    organization_id: str
    source_kind: ExportSourceKind
    status: str
    is_current_public: bool
    created_at: datetime
    updated_at: datetime
    broker_listing_reference: str | None = None
    marketed_brand_claim: str | None = None
    model_designation_claim: str | None = None
    build_year: int | None = None
    build_year_unknown: bool = False
    boat_name: str | None = None
    boat_name_unknown: bool = False
    loa_meters: Decimal | None = None
    loa_unknown: bool = False
    asking_price_mode: str | None = None
    asking_price_amount: Decimal | None = None
    currency: str | None = None
    location_country: str | None = None
    location_region: str | None = None
    location_region_unknown: bool = False
    broker_description: str | None = None
    media_urls: tuple[str, ...] = ()
    media_md5s: tuple[str | None, ...] = ()
    #: Parallel to `media_urls`/`media_md5s`: the asset's own stored
    #: `mime_type` (`hullq.persistence.media_gallery.MediaAssetRecord
    #: .mime_type`), never guessed from the URL/filename extension.
    media_mime_types: tuple[str | None, ...] = ()
    #: Broker-confirmed NautiX export-profile attestations (module docstring)
    #: -- never read from stored HullQ listing/offer/claim data, never
    #: persisted beyond this one export call. All three are `None` unless
    #: the caller explicitly supplied a `NautixExportProfile` for this row.
    sale_class: str | None = None
    nautix_account_token: str | None = None
    nautix_office_id: str | None = None
    #: SLICE-0093 (review amendment Finding B): the **resolved** current
    #: vessel category for this row's PhysicalBoat --
    #: `hullq.domain.vessel_category.VesselCategoryResolution`'s own value
    #: (`"SAIL"`/`"POWER"`/`"MOTORSAILER"`/`"UNKNOWN"`/`"CONFLICT"`),
    #: combining the design plane, this Organization's own claim and every
    #: other current claiming Organization -- never only the publisher's own
    #: raw claim (the original cut of this field, which a design-linked
    #: positively-POWER BoatDesign or a publisher-vs-other-Organization
    #: category disagreement could silently bypass). `None` only when the
    #: resolution was genuinely never computed for this row. `boat_type`
    #: below remains the sole unconditional NautiX default only when this
    #: resolves to `SAIL`/`UNKNOWN`/omitted; an explicit `POWER`/
    #: `MOTORSAILER`/`CONFLICT` resolution fails the NautiX preflight closed
    #: instead (module docstring NautiX representability gap, extended for
    #: Power).
    vessel_category: str | None = None

    def __post_init__(self) -> None:
        if len(self.media_urls) != len(self.media_md5s) or len(self.media_urls) != len(
            self.media_mime_types
        ):
            raise ValueError(
                "ExportRow.media_urls, media_md5s and media_mime_types must be the same length"
            )
        if len(self.media_urls) > MAX_EXPORT_MEDIA_PER_ROW:
            raise ValueError(f"ExportRow.media_urls exceeds {MAX_EXPORT_MEDIA_PER_ROW} entries")
        if self.sale_class is not None and self.sale_class not in _ALLOWED_SALE_CLASSES:
            raise ValueError(f"ExportRow.sale_class must be one of {sorted(_ALLOWED_SALE_CLASSES)}")
        if self.vessel_category is not None and self.vessel_category not in _VESSEL_CATEGORY_VALUES:
            raise ValueError(
                f"ExportRow.vessel_category must be one of {sorted(_VESSEL_CATEGORY_VALUES)}"
            )
        for label, value in (
            ("broker_listing_reference", self.broker_listing_reference),
            ("marketed_brand_claim", self.marketed_brand_claim),
            ("model_designation_claim", self.model_designation_claim),
            ("boat_name", self.boat_name),
            ("location_region", self.location_region),
            ("broker_description", self.broker_description),
        ):
            if value is not None and len(value) > MAX_EXPORT_CELL_CHARS:
                raise ValueError(f"ExportRow.{label} exceeds {MAX_EXPORT_CELL_CHARS} characters")
        for label, value in (
            ("nautix_account_token", self.nautix_account_token),
            ("nautix_office_id", self.nautix_office_id),
        ):
            if value is not None and not (0 < len(value) <= 200):
                raise ValueError(f"ExportRow.{label} must be 1-200 characters when provided")


#: Canonical, stably ordered column/field set every table-like format
#: (CSV/TSV/XLSX/XLS/ODS/JSON) shares -- one shared header/field schema
#: (Required Behavior: "one shared header/field schema for table outputs").
#: The eleven dotted-key columns reuse `hullq.domain.import_intake
#: .MAPPABLE_TARGET_KEYS` spelling exactly, so a broker reimporting this
#: file through the accepted SLICE-0083 mapping UI maps them to themselves;
#: the remaining five (export_id/status/is_current_public/loa/media_urls)
#: are export-only metadata/facts with no SLICE-0083 mapping target and are
#: expected to be mapped to `__ignore__` on reimport.
EXPORT_COLUMNS: tuple[str, ...] = (
    "export_id",
    "status",
    "is_current_public",
    "broker_listing_reference",
    "physical_boat.marketed_brand_claim",
    "physical_boat.model_designation_claim",
    "physical_boat.build_year",
    "physical_boat.boat_name",
    "physical_boat.loa_length",
    "listing_offer.asking_price_mode",
    "listing_offer.asking_price_amount",
    "listing_offer.currency",
    "listing_offer.location_country",
    "listing_offer.location_region",
    "listing_offer.broker_description",
    "media_urls",
)


def _row_to_wire_fields(row: ExportRow) -> dict[str, Any]:
    """The one shared projection from `ExportRow` to `EXPORT_COLUMNS` ->
    raw (not yet stringified) value. An explicit UNKNOWN assertion is
    rendered as the literal text `"UNKNOWN"` -- mechanically distinct from
    omission, which is rendered as a blank/absent cell."""
    return {
        "export_id": row.export_id,
        "status": row.status,
        "is_current_public": row.is_current_public,
        "broker_listing_reference": row.broker_listing_reference,
        "physical_boat.marketed_brand_claim": row.marketed_brand_claim,
        "physical_boat.model_designation_claim": row.model_designation_claim,
        "physical_boat.build_year": "UNKNOWN" if row.build_year_unknown else row.build_year,
        "physical_boat.boat_name": "UNKNOWN" if row.boat_name_unknown else row.boat_name,
        "physical_boat.loa_length": "UNKNOWN" if row.loa_unknown else row.loa_meters,
        "listing_offer.asking_price_mode": row.asking_price_mode,
        "listing_offer.asking_price_amount": row.asking_price_amount,
        "listing_offer.currency": row.currency,
        "listing_offer.location_country": row.location_country,
        "listing_offer.location_region": (
            "UNKNOWN" if row.location_region_unknown else row.location_region
        ),
        "listing_offer.broker_description": row.broker_description,
        "media_urls": "; ".join(row.media_urls) if row.media_urls else None,
    }


def _cell_text(value: Any) -> str:
    """Stringify one wire value for a table-format cell. `Decimal` is
    rendered as a plain fixed-point string (mirrors `hullq.domain
    .listing_draft_payload`'s identical discipline) -- never through a
    binary-floating-point conversion."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


# ---------------------------------------------------------------------------
# Formula-injection / spreadsheet-interpretation defense
# ---------------------------------------------------------------------------

_FORMULA_TRIGGER_CHARS = frozenset({"=", "+", "-", "@"})
#: ASCII control characters other than the ones csv/xlsx readers already
#: treat as structural (tab/CR/LF are handled by quoting, not stripped
#: here) -- these are never emitted raw into a spreadsheet cell.
_STRIP_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def escape_formula_injection(value: str) -> tuple[str, bool]:
    """Decide-and-test explicit safe escape policy for one string cell
    (Required Behavior: "Decide and test an explicit safe escape/reject
    policy with per-row warnings and importer roundtrip impact").

    Returns `(safe_value, was_modified)`. Stray ASCII control characters are
    stripped unconditionally. If the remaining text still begins with a
    character a spreadsheet application could interpret as a formula/DDE
    trigger (`=`, `+`, `-`, `@`) or a leading tab, a single literal
    apostrophe is prepended so the cell is unambiguously textual to any
    reader -- never evaluated as a formula and never silently reinterpreted
    as a different numeric/date type.

    This is intentionally lossy for exactly these adversarial inputs: a
    value re-imported through the accepted SLICE-0083 parser will carry the
    extra leading apostrophe. That tradeoff is disclosed to the broker via a
    per-row preflight warning before download, never applied silently.
    """
    stripped = _STRIP_CONTROL_CHAR_RE.sub("", value)
    if stripped and (stripped[0] in _FORMULA_TRIGGER_CHARS or stripped[0] == "\t"):
        return "'" + stripped, True
    return stripped, stripped != value


def _escape_table_cell(value: Any) -> tuple[str, bool]:
    text = _cell_text(value)
    if not text:
        return text, False
    return escape_formula_injection(text)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


class ExportFieldState(StrEnum):
    PRESENT = "PRESENT"
    UNKNOWN = "UNKNOWN"
    OMITTED = "OMITTED"


@dataclass(frozen=True)
class FormatPreflight:
    """One format's exportability verdict for one row. `reasons` is
    populated iff `exportable` is `False` -- an unexportable row is never
    silently represented as complete. `warnings` may be populated on an
    otherwise-exportable row (for example, a formula-injection escape that
    was actually applied)."""

    format: ExportFormat
    exportable: bool
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.exportable and self.reasons:
            raise ValueError("An exportable FormatPreflight must not carry reasons")
        if not self.exportable and not self.reasons:
            raise ValueError("A non-exportable FormatPreflight must carry at least one reason")


@dataclass(frozen=True)
class RowPreflight:
    """The complete per-row, per-format preflight report shown to the
    broker before download."""

    row: ExportRow
    field_states: dict[str, ExportFieldState]
    formats: dict[ExportFormat, FormatPreflight]


def _field_states(row: ExportRow) -> dict[str, ExportFieldState]:
    def state(value: Any, unknown: bool) -> ExportFieldState:
        if unknown:
            return ExportFieldState.UNKNOWN
        return ExportFieldState.PRESENT if value is not None else ExportFieldState.OMITTED

    return {
        "broker_listing_reference": state(row.broker_listing_reference, False),
        "physical_boat.marketed_brand_claim": state(row.marketed_brand_claim, False),
        "physical_boat.model_designation_claim": state(row.model_designation_claim, False),
        "physical_boat.build_year": state(row.build_year, row.build_year_unknown),
        "physical_boat.boat_name": state(row.boat_name, row.boat_name_unknown),
        "physical_boat.loa_length": state(row.loa_meters, row.loa_unknown),
        "listing_offer.asking_price_mode": state(row.asking_price_mode, False),
        "listing_offer.currency": state(row.currency, False),
        "listing_offer.location_country": state(row.location_country, False),
        "listing_offer.location_region": state(row.location_region, row.location_region_unknown),
        "listing_offer.broker_description": state(row.broker_description, False),
        "media_urls": state(row.media_urls or None, False),
    }


def _table_format_preflight(fmt: ExportFormat, row: ExportRow) -> FormatPreflight:
    """Every table-like format (and NautiX, handled separately) is always
    exportable -- there is no hard-mandatory field for a plain tabular/JSON
    row. Warnings surface which fields will actually be formula-injection
    escaped so the broker can see the (disclosed, lossy) transformation
    before downloading."""
    wire = _row_to_wire_fields(row)
    warnings: list[str] = []
    if fmt is not ExportFormat.JSON:
        for col in EXPORT_COLUMNS:
            value = wire[col]
            if isinstance(value, str) and value:
                _, modified = escape_formula_injection(value)
                if modified:
                    warnings.append(f"{col}: formula-injection escaped on download")
    return FormatPreflight(format=fmt, exportable=True, warnings=tuple(warnings))


#: HullQ's current sailboat-only catalog scope (core guardrail: "Monohulls,
#: catamarans and trimarans are first-class") makes this generic NautiX
#: category a true structural fact about every HullQ listing, not a
#: per-row marketing-style assertion -- see module docstring.
_NAUTIX_CATALOG_BOAT_TYPE = "sail-yacht"

_MD5_RE = re.compile(r"^[0-9a-fA-F]{32}$")

#: The pinned XSD's `MimeTypeImage` enumeration -- a media asset whose own
#: stored `mime_type` is not exactly one of these is never fabricated into
#: one; it is simply not a usable NautiX photo.
_NAUTIX_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/gif", "image/png", "image/webp"})


def _valid_nautix_photos(row: ExportRow) -> list[tuple[str, str, str]]:
    """Every (url, md5, mime_type) triple that is genuinely usable as one
    NautiX `<image>` element -- a valid 32-hex-char MD5 checksum *and* a
    mime type the pinned XSD actually enumerates, both read from the
    asset's own stored facts, never invented."""
    photos = [
        (url, md5, mime)
        for url, md5, mime in zip(row.media_urls, row.media_md5s, row.media_mime_types, strict=True)
        if md5 and _MD5_RE.fullmatch(md5) and mime in _NAUTIX_IMAGE_MIME_TYPES
    ]
    return photos[:MAX_EXPORT_MEDIA_PER_ROW]


def _resolve_nautix_status(row: ExportRow) -> str | None:
    """Mechanical invariant: "An exported NautiX `active` status is never
    manufactured from a private draft or merely ACTIVE-but-not-current-
    public HullQ listing." Only a genuinely current-public ACTIVE listing
    maps to `active`; only WITHDRAWN maps to `inactive`
    (`inactive` here is a source-status label only -- never implies HullQ
    performed or will perform any remote withdrawal/mutation). Every other
    state (private draft, non-public ACTIVE, HullQ-internal DRAFT lifecycle)
    has no valid NautiX status and is `None`."""
    if row.source_kind is ExportSourceKind.PRIVATE_DRAFT:
        return None
    if row.status == "ACTIVE" and row.is_current_public:
        return "active"
    if row.status == "WITHDRAWN":
        return "inactive"
    return None


def _nautix_preflight(row: ExportRow) -> FormatPreflight:
    reasons: list[str] = []
    if row.source_kind is ExportSourceKind.PRIVATE_DRAFT:
        reasons.append(
            "source: a private draft can never be exported as a NautiX active/inactive advert"
        )
        return FormatPreflight(format=ExportFormat.NAUTIX, exportable=False, reasons=tuple(reasons))

    if _resolve_nautix_status(row) is None:
        reasons.append(
            "status: only a current-public ACTIVE listing or a WITHDRAWN listing may export to "
            "NautiX; a non-public or HullQ-internal-DRAFT lifecycle state is never falsely "
            "exported as current-public"
        )
    title = row.boat_name or row.model_designation_claim or row.marketed_brand_claim
    if not title:
        reasons.append("title: no boat_name/model_designation_claim/marketed_brand_claim present")
    if not row.model_designation_claim:
        reasons.append("boat_data.model: HullQ has no model_designation_claim for this listing")
    if row.loa_meters is None or row.loa_unknown:
        reasons.append(
            "boat_data.dimensions.loa: HullQ has no asserted LOA value for this listing "
            "(never fabricated)"
        )
    elif not (Decimal("0.01") <= row.loa_meters <= Decimal("460.00")):
        reasons.append("boat_data.dimensions.loa: value is outside the NautiX accepted range")
    if row.sale_class is None:
        reasons.append(
            "sale_data.sale_class: no broker-confirmed NautixExportProfile sale classification "
            "was provided for this listing (never fabricated)"
        )
    if not row.nautix_account_token:
        reasons.append(
            "account.token: no broker-confirmed destination account token was provided "
            "(never fabricated from the HullQ Organization id)"
        )
    if not row.nautix_office_id:
        reasons.append(
            "advert_data.office_id: no broker-confirmed destination office id was provided "
            "(never a placeholder value)"
        )
    if row.asking_price_mode is None:
        reasons.append("sale_data.price: no asking_price_mode present")
    elif row.asking_price_mode == "AMOUNT" and (
        row.asking_price_amount is None or row.currency is None
    ):
        reasons.append("sale_data.price: AMOUNT mode requires both an amount and a currency")
    if not row.location_country:
        reasons.append("sale_data.location: no location_country present")
    if not _valid_nautix_photos(row):
        reasons.append(
            "media.images: no approved rights-cleared photo with a genuine NautiX-shaped MD5 "
            "checksum is available (never an invented checksum)"
        )
    # SLICE-0093 Required Behavior §7 (review amendment Finding B): the
    # existing Sail-only `boat_type` default (`_NAUTIX_CATALOG_BOAT_TYPE`,
    # below) must never be allowed to coerce a listing whose **resolved**
    # category (design + concrete + cross-Organization) is explicitly
    # POWER/MOTORSAILER/CONFLICT into the catalog-wide "sail-yacht" type --
    # a design-linked BoatDesign positively categorized POWER with no
    # publisher claim at all, or a publisher-SAIL-vs-design-POWER/other-
    # Organization disagreement, must fail closed exactly like an explicit
    # publisher POWER claim. `None`/`"SAIL"`/`"UNKNOWN"` all preserve the
    # existing default-SAIL NautiX assumption unchanged.
    if row.vessel_category in _NAUTIX_EXCLUDED_VESSEL_CATEGORIES:
        reasons.append(
            "boat_types.boat_type: HullQ's sail-yacht NautiX catalog type cannot represent a "
            f"listing whose resolved current vessel category is {row.vessel_category} "
            "(never coerced to sail-yacht)"
        )

    warnings: list[str] = []
    if row.broker_description and (
        len(row.broker_description) > 60 or "\n" in row.broker_description
    ):
        warnings.append("advert_data.subtitle: truncated/flattened to NautiX's 60-character limit")

    return FormatPreflight(
        format=ExportFormat.NAUTIX,
        exportable=not reasons,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def build_row_preflight(row: ExportRow) -> RowPreflight:
    """The complete per-row, per-format preflight: field completeness plus,
    for every one of the seven accepted formats, whether this exact row is
    exportable and why not when it is not."""
    formats: dict[ExportFormat, FormatPreflight] = {
        fmt: _table_format_preflight(fmt, row)
        for fmt in ExportFormat
        if fmt is not ExportFormat.NAUTIX
    }
    formats[ExportFormat.NAUTIX] = _nautix_preflight(row)
    return RowPreflight(row=row, field_states=_field_states(row), formats=formats)


# ---------------------------------------------------------------------------
# CSV / TSV
# ---------------------------------------------------------------------------


def _write_delimited(rows: list[ExportRow], *, delimiter: str) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, delimiter=delimiter, quotechar='"', lineterminator="\r\n")
    writer.writerow(EXPORT_COLUMNS)
    for row in rows:
        wire = _row_to_wire_fields(row)
        cells = []
        for col in EXPORT_COLUMNS:
            text, _ = _escape_table_cell(wire[col])
            cells.append(text)
        writer.writerow(cells)
    return buf.getvalue().encode("utf-8")


def write_csv(rows: list[ExportRow]) -> bytes:
    return _write_delimited(rows, delimiter=",")


def write_tsv(rows: list[ExportRow]) -> bytes:
    return _write_delimited(rows, delimiter="\t")


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def write_json(rows: list[ExportRow]) -> bytes:
    """One `{"listings": [...]}` document -- the exact 0083-documented
    JSON profile (`hullq.domain.import_parsers.parse_json_table`). String
    values are never formula-injection-escaped here: a JSON value is never
    evaluated as a spreadsheet formula by a JSON reader, and escaping would
    only corrupt reimport fidelity for this format."""
    listings: list[dict[str, Any]] = []
    for row in rows:
        wire = _row_to_wire_fields(row)
        obj: dict[str, Any] = {}
        for col in EXPORT_COLUMNS:
            value = wire[col]
            if value is None:
                continue
            obj[col] = format(value, "f") if isinstance(value, Decimal) else value
        listings.append(obj)
    payload = {"listings": listings}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ": ")).encode("utf-8")


# ---------------------------------------------------------------------------
# XLSX (xlsxwriter)
# ---------------------------------------------------------------------------


def write_xlsx(rows: list[ExportRow]) -> bytes:
    import xlsxwriter

    buf = io.BytesIO()
    try:
        # independent review amendment (2026-10-16): xlsxwriter silently
        # forces constant_memory=False whenever in_memory=True ("We can't
        # do 'constant_memory' mode while doing 'in_memory' mode" --
        # xlsxwriter's own Workbook.__init__). Passing both was therefore a
        # contradiction that claimed a memory bound the combination never
        # actually enforced. `in_memory=True` is kept (required so this
        # function returns bytes rather than writing a temp file); the
        # real memory bound is `MAX_EXPORT_ROWS * MAX_EXPORT_CELL_CHARS`
        # enforced by `ExportRow.__post_init__`, not a writer flag.
        workbook = xlsxwriter.Workbook(buf, {"in_memory": True})
        worksheet = workbook.add_worksheet("Listings")
        header_format = workbook.add_format({"bold": True})
        for col_idx, col in enumerate(EXPORT_COLUMNS):
            worksheet.write_string(0, col_idx, col, header_format)
        for row_idx, row in enumerate(rows, start=1):
            wire = _row_to_wire_fields(row)
            for col_idx, col in enumerate(EXPORT_COLUMNS):
                value = wire[col]
                if value is None:
                    continue
                if isinstance(value, int) and not isinstance(value, bool):
                    worksheet.write_number(row_idx, col_idx, value)
                else:
                    # Decimal and every other value go through the string
                    # path (never write_number) so a price amount is never
                    # routed through a binary-floating-point cell type, and
                    # always through write_string (never the generic write()
                    # dispatcher) so a cell is never promoted to a formula
                    # object regardless of leading character.
                    text, _ = _escape_table_cell(value)
                    worksheet.write_string(row_idx, col_idx, text)
        workbook.close()
    except Exception as exc:
        raise ExportWriteError(f"XLSX serialization failed: {exc}") from exc
    return buf.getvalue()


# ---------------------------------------------------------------------------
# XLS (xlwt, legacy BIFF8)
# ---------------------------------------------------------------------------


def write_xls(rows: list[ExportRow]) -> bytes:
    if len(rows) > MAX_XLS_ROWS:
        raise ExportWriteError(
            f"XLS (legacy BIFF8) cannot represent more than {MAX_XLS_ROWS} rows; got {len(rows)}"
        )
    import xlwt

    try:
        workbook = xlwt.Workbook(encoding="utf-8")
        sheet = workbook.add_sheet("Listings")
        bold = xlwt.easyxf("font: bold on")
        for col_idx, col in enumerate(EXPORT_COLUMNS):
            sheet.write(0, col_idx, col, bold)
        for row_idx, row in enumerate(rows, start=1):
            wire = _row_to_wire_fields(row)
            for col_idx, col in enumerate(EXPORT_COLUMNS):
                value = wire[col]
                if value is None:
                    continue
                if isinstance(value, int) and not isinstance(value, bool):
                    sheet.write(row_idx, col_idx, value)
                else:
                    text, _ = _escape_table_cell(value)
                    # xlwt's write() treats a plain str as a Label (text)
                    # record, never a Formula record, regardless of content.
                    sheet.write(row_idx, col_idx, text)
        buf = io.BytesIO()
        workbook.save(buf)
    except ExportWriteError:
        raise
    except Exception as exc:
        raise ExportWriteError(f"XLS serialization failed: {exc}") from exc
    return buf.getvalue()


# ---------------------------------------------------------------------------
# ODS (odfpy)
# ---------------------------------------------------------------------------


def write_ods(rows: list[ExportRow]) -> bytes:
    try:
        from odf.opendocument import OpenDocumentSpreadsheet
        from odf.table import Table, TableCell, TableRow
        from odf.text import P

        doc = OpenDocumentSpreadsheet()
        table = Table(name="Listings")
        header_row = TableRow()
        for col in EXPORT_COLUMNS:
            cell = TableCell(valuetype="string")
            cell.addElement(P(text=col))
            header_row.addElement(cell)
        table.addElement(header_row)
        for row in rows:
            wire = _row_to_wire_fields(row)
            data_row = TableRow()
            for col in EXPORT_COLUMNS:
                value = wire[col]
                if value is None:
                    data_row.addElement(TableCell())
                    continue
                if isinstance(value, int) and not isinstance(value, bool):
                    cell = TableCell(valuetype="float", value=value)
                    cell.addElement(P(text=str(value)))
                else:
                    # Every non-integer value (including Decimal, so price
                    # amounts never pass through a binary-floating-point
                    # cell type) is written as a plain string-typed cell
                    # with no `formula` attribute, so it is never evaluated
                    # as a formula by any ODS-reading application regardless
                    # of leading character.
                    text, _ = _escape_table_cell(value)
                    cell = TableCell(valuetype="string")
                    cell.addElement(P(text=text))
                data_row.addElement(cell)
            table.addElement(data_row)
        doc.spreadsheet.addElement(table)
        buf = io.BytesIO()
        doc.save(buf)
    except Exception as exc:
        raise ExportWriteError(f"ODS serialization failed: {exc}") from exc
    return buf.getvalue()


# ---------------------------------------------------------------------------
# NautiX 1.4 adverts.xml
# ---------------------------------------------------------------------------

_ADVERT_ID_SAFE_RE = re.compile(r"[^-a-zA-Z0-9_]")


def _ns(tag: str) -> str:
    return f"{{{NAUTIX_V14_NAMESPACE}}}{tag}"


def _format_nautix_datetime(value: datetime) -> str:
    """The exact `DateTimeWithZone` pinned-XSD shape
    (`YYYY-MM-DDTHH:MM:SS+HH:MM`)."""
    as_utc = value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return as_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _sanitize_advert_id(export_id: str) -> str:
    """The pinned XSD's `AdvertIdValue` is `[-a-zA-Z0-9_]{1,36}`. A stable
    broker export identity (Required Behavior: "stable broker export
    identity is scoped to owning listing") derived deterministically from
    *export_id* -- never a fresh/random value, so a retried export of the
    identical selection always yields the identical advert id."""
    candidate = _ADVERT_ID_SAFE_RE.sub("", export_id)
    if candidate and len(candidate) <= 36:
        return candidate
    digest = hashlib.sha256(export_id.encode("utf-8")).hexdigest()[:32]
    return f"hq{digest}"[:36]


def _quantize_loa(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_nautix_advert(adverts_el: Any, row: ExportRow) -> None:
    status = _resolve_nautix_status(row)
    assert status is not None  # caller only reaches here for an exportable row

    advert_el = etree.SubElement(adverts_el, _ns("advert"))
    advert_el.set("id", _sanitize_advert_id(row.export_id))
    advert_el.set("type", "boat")
    advert_el.set("purpose", "sale")
    advert_el.set("status", status)
    advert_el.set("modified", _format_nautix_datetime(row.updated_at))

    advert_data_el = etree.SubElement(advert_el, _ns("advert_data"))
    assert row.nautix_office_id is not None
    etree.SubElement(advert_data_el, _ns("office_id")).text = row.nautix_office_id
    if row.broker_description:
        subtitle = row.broker_description.replace("\n", " ").replace("\r", " ")[:60]
        etree.SubElement(advert_data_el, _ns("subtitle")).text = subtitle

    sale_data_el = etree.SubElement(advert_el, _ns("sale_data"))
    assert row.sale_class is not None
    etree.SubElement(sale_data_el, _ns("sale_class")).text = row.sale_class
    price_el = etree.SubElement(sale_data_el, _ns("price"))
    if row.asking_price_mode == "POA":
        price_el.set("type", "on-request")
        price_el.text = ""
    else:
        assert row.asking_price_amount is not None
        assert row.currency is not None
        price_el.set("type", "fixed")
        price_el.set("currency", row.currency)
        price_el.text = format(row.asking_price_amount, "f")
    location_el = etree.SubElement(sale_data_el, _ns("location"))
    assert row.location_country is not None
    location_el.set("country", row.location_country)
    location_el.text = row.location_region or row.location_country

    boat_data_el = etree.SubElement(advert_el, _ns("boat_data"))
    boat_types_el = etree.SubElement(boat_data_el, _ns("boat_types"))
    etree.SubElement(boat_types_el, _ns("type")).text = _NAUTIX_CATALOG_BOAT_TYPE
    if row.marketed_brand_claim:
        etree.SubElement(boat_data_el, _ns("manufacturer")).text = row.marketed_brand_claim
    assert row.model_designation_claim is not None
    etree.SubElement(boat_data_el, _ns("model")).text = row.model_designation_claim
    if row.boat_name:
        etree.SubElement(boat_data_el, _ns("boat_name")).text = row.boat_name
    if row.build_year is not None and not row.build_year_unknown:
        etree.SubElement(boat_data_el, _ns("year_built")).text = str(row.build_year)
    dimensions_el = etree.SubElement(boat_data_el, _ns("dimensions"))
    loa_el = etree.SubElement(dimensions_el, _ns("loa"))
    loa_el.set("unit", "m")
    assert row.loa_meters is not None
    loa_el.text = format(_quantize_loa(row.loa_meters), "f")

    media_el = etree.SubElement(advert_el, _ns("media"))
    images_el = etree.SubElement(media_el, _ns("images"))
    for url, md5, mime in _valid_nautix_photos(row):
        image_el = etree.SubElement(images_el, _ns("image"))
        image_el.set("type", mime)
        image_el.set("md5", md5.lower())
        image_el.text = url


def build_nautix_document(rows: list[ExportRow], *, generated_at: datetime) -> bytes:
    """Build one NautiX 1.4 `adverts.xml` document from *rows*.

    Only rows whose `_nautix_preflight` is exportable are ever written as an
    `<advert>` element -- a `NOT_EXPORTABLE` row is silently omitted from
    the document body entirely (never emitted with a fabricated/placeholder
    value for its missing mandatory field). Callers (the application layer)
    are responsible for surfacing the omission to the broker via
    `build_row_preflight` before download; this function's only job is to
    never put an incomplete/fabricated advert into the output bytes.

    The document's `<account token="...">` is the exportable rows' own
    broker-confirmed `nautix_account_token` (module docstring) -- there is
    deliberately no *organization_id* parameter here any more: an earlier
    revision derived the token from the HullQ Organization id when no
    profile was supplied, which is exactly the fabricated-identity pattern
    this invariant forbids. When zero rows are exportable the account
    element still needs some `NotEmptyString` token to stay schema-valid;
    `"no-export"` is used in that case precisely because it wraps zero
    adverts and asserts nothing about any real account.

    The caller must validate the returned bytes against the pinned XSD
    (`hullq.domain.import_nautix.parse_and_validate_nautix` reuses the exact
    same pinned schema) before treating this as a finished download --
    this function alone is not the proof.
    """
    exportable_rows = [row for row in rows if _nautix_preflight(row).exportable]

    root = etree.Element(_ns("nautix"), nsmap={None: NAUTIX_V14_NAMESPACE})
    root.set("version", "1.4")
    root.set("date", _format_nautix_datetime(generated_at))

    account_el = etree.SubElement(root, _ns("account"))
    token = exportable_rows[0].nautix_account_token if exportable_rows else "no-export"
    assert token
    account_el.set("token", token)
    account_el.set("status", "active")
    etree.SubElement(account_el, _ns("account_name")).text = token
    adverts_el = etree.SubElement(account_el, _ns("adverts"))

    for row in exportable_rows:
        _build_nautix_advert(adverts_el, row)

    serialized: bytes = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    return serialized
