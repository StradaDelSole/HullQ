"""NautiX 1.4 `adverts.xml` import adapter — SLICE-0083.

Validates an uploaded document against the actual pinned official NautiX
1.4 XSD (`hullq.domain.nautix_schema`, provenance in that package's
`PROVENANCE.md`) using `lxml`, then maps only `advert type="boat"
purpose="sale"` records inside HullQ's currently accepted sailboat supply
domain into the one shared `hullq.domain.import_intake.StagedRowPreview`
shape -- bypassing manual column mapping entirely, since the NautiX field
semantics are fixed by the schema itself (Required Behavior #5).

Security posture (mechanical invariants / Required Behavior #5):

- the XSD is loaded once from the pinned, SHA-256-verified local file --
  never fetched over the network, never approximated by a hand-written
  "schema-like" subset validator;
- the XML parser disables DTD loading, entity resolution and network
  access, and keeps libxml2's own `huge_tree=False` depth/resource
  restrictions enabled -- a literal `<!DOCTYPE` anywhere in the raw bytes
  is rejected outright before the file is even handed to the parser, which
  closes the entire classic-XXE/billion-laughs attack class (both require
  a DTD) independent of any single parser flag's correctness;
- a document must pass real XSD validation (`AdvertIdValue`/
  `AdvertPurpose`/`AdvertType`/`AdvertStatus`/`DateTimeWithZone` etc, all
  defined by the schema) before any field is ever read for mapping -- a
  syntactically well-formed but XSD-invalid document is denied with zero
  draft writes, never partially/silently normalized.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from lxml import etree

from hullq.domain.import_intake import (
    MAX_IMPORT_FILE_BYTES,
    MAX_IMPORT_ROWS,
    ImportParseError,
    ImportParseErrorKind,
    RowPreviewClassification,
    SourceRecordKey,
    StagedRowPreview,
    compute_row_digest,
)
from hullq.domain.listing_draft_payload import InvalidListingDraftPayloadError
from hullq.domain.professional_listing_draft import parse_professional_listing_draft_request

__all__ = ["NAUTIX_V14_NAMESPACE", "map_nautix_adverts_to_rows", "parse_and_validate_nautix"]

#: The exact targetNamespace declared by the pinned XSD.
NAUTIX_V14_NAMESPACE = "https://nautix.nautic-network.org/v1.4/"

_SCHEMA_DIR = Path(__file__).parent / "nautix_schema"
_SCHEMA_PATH = _SCHEMA_DIR / "NautiX_v1.4.xsd"

#: Immutable pin (`PROVENANCE.md` in the same directory): the exact
#: official file retrieved 2026-10-12 from
#: `https://nautix.nautic-network.org/v1.4/NautiX.xsd`. A corrupted or
#: tampered on-disk asset fails closed rather than silently validating
#: against a different schema.
_PINNED_SHA256 = "249fd6693fd032dc71d5138b64a39a3b018ffdf8e3c733101e95f6e4a2ddb91f"

_NAUTIX_TAG = f"{{{NAUTIX_V14_NAMESPACE}}}nautix"


@lru_cache(maxsize=1)
def _load_pinned_schema() -> etree.XMLSchema:
    raw = _SCHEMA_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != _PINNED_SHA256:
        raise RuntimeError(
            "pinned NautiX v1.4 XSD asset digest mismatch: expected "
            f"{_PINNED_SHA256}, got {digest}. Refusing to validate against an "
            "unverified schema."
        )
    schema_doc = etree.fromstring(raw, parser=_secure_parser())
    return etree.XMLSchema(schema_doc)


def _secure_parser() -> etree.XMLParser:
    # resolve_entities=False + no_network=True + load_dtd=False close the
    # XXE surface; huge_tree defaults to False, keeping libxml2's own
    # depth/resource-consumption guards against entity/structural bombs.
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        huge_tree=False,
    )


def parse_and_validate_nautix(raw_bytes: bytes) -> Any:
    """Parse *raw_bytes* securely and validate it against the pinned
    official NautiX 1.4 XSD. Returns the validated `lxml.etree._Element`
    root, or raises `ImportParseError`.
    """
    if len(raw_bytes) == 0:
        raise ImportParseError(ImportParseErrorKind.EMPTY, "file is empty")
    if len(raw_bytes) > MAX_IMPORT_FILE_BYTES:
        raise ImportParseError(
            ImportParseErrorKind.OVERSIZE, "file exceeds the maximum upload size"
        )
    if b"<!doctype" in raw_bytes.lower():
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED, "DOCTYPE declarations are not permitted"
        )

    try:
        root = etree.fromstring(raw_bytes, parser=_secure_parser())
    except etree.XMLSyntaxError as exc:
        raise ImportParseError(ImportParseErrorKind.MALFORMED, f"malformed XML: {exc}") from exc

    if root.tag != _NAUTIX_TAG:
        raise ImportParseError(
            ImportParseErrorKind.UNSUPPORTED_FORMAT,
            f"unrecognized root element/namespace (expected {_NAUTIX_TAG!r}, got {root.tag!r})",
        )
    if root.get("version") != "1.4":
        raise ImportParseError(
            ImportParseErrorKind.UNSUPPORTED_FORMAT,
            f"unsupported NautiX version (expected '1.4', got {root.get('version')!r})",
        )

    schema = _load_pinned_schema()
    if not schema.validate(root):
        errors = "; ".join(str(e) for e in list(schema.error_log)[:5])
        raise ImportParseError(
            ImportParseErrorKind.MALFORMED,
            f"document does not validate against NautiX v1.4 XSD: {errors}",
        )
    return root


#: Every HullQ-accepted sailboat `BoatType` enumeration member (the XSD's
#: full `BoatType` also covers power/inflatable/small/pwc categories, which
#: are outside HullQ's current accepted supply domain -- core data
#: guardrail: "Monohulls, catamarans and trimarans are first-class"
#: refers to HullQ's own sailboat identity model, not an invitation to
#: widen supply to powerboats here).
_ACCEPTED_SAIL_BOAT_TYPES = frozenset(
    {
        "sail-cabin",
        "sail-catamaran",
        "sail-classic",
        "sail-cruising",
        "sail-daysailer",
        "sail-decksaloon",
        "sail-dinghy",
        "sail-flat",
        "sail-gulet",
        "sail-hull",
        "sail-motorsailer",
        "sail-racing",
        "sail-trimaran",
        "sail-yacht",
    }
)


def _ns(tag: str) -> str:
    return f"{{{NAUTIX_V14_NAMESPACE}}}{tag}"


def _text(el: Any | None) -> str | None:
    if el is None or el.text is None:
        return None
    text = el.text.strip()
    return text or None


def _first_sail_boat_type(boat_data: Any | None) -> str | None:
    if boat_data is None:
        return None
    boat_types = boat_data.find(_ns("boat_types"))
    if boat_types is None:
        return None
    for type_el in boat_types.findall(_ns("type")):
        value = _text(type_el)
        if value in _ACCEPTED_SAIL_BOAT_TYPES:
            return value
    return None


def _advert_raw_fields(advert: Any) -> dict[str, str | None]:
    advert_data = advert.find(_ns("advert_data"))
    sale_data = advert.find(_ns("sale_data"))
    boat_data = advert.find(_ns("boat_data"))
    price_el = sale_data.find(_ns("price")) if sale_data is not None else None
    location_el = sale_data.find(_ns("location")) if sale_data is not None else None
    dimensions_el = boat_data.find(_ns("dimensions")) if boat_data is not None else None
    loa_el = dimensions_el.find(_ns("loa")) if dimensions_el is not None else None
    media_el = advert.find(_ns("media"))
    images_el = media_el.find(_ns("images")) if media_el is not None else None
    image_elements = images_el.findall(_ns("image")) if images_el is not None else []
    image_count = len(image_elements)
    # Mechanical invariants: "An imported media URL is retained as an
    # inert reference only ... no HTTP requests/downloads". Captured as
    # plain staged text -- the element's own URL/md5 text, never fetched
    # -- and bounded to the first 20 images so one adversarial advert
    # cannot inflate staged JSONB without bound.
    media_image_urls = "; ".join((_text(img) or "") for img in image_elements[:20] if _text(img))
    media_image_md5s = "; ".join(md5 for img in image_elements[:20] if (md5 := img.get("md5")))

    return {
        "advert_id": advert.get("id"),
        "advert_type": advert.get("type"),
        "advert_purpose": advert.get("purpose"),
        "advert_status": advert.get("status"),
        "advert_modified": advert.get("modified"),
        "boat_type": _first_sail_boat_type(boat_data),
        "manufacturer": _text(boat_data.find(_ns("manufacturer")))
        if boat_data is not None
        else None,
        "builder": _text(boat_data.find(_ns("builder"))) if boat_data is not None else None,
        "model": _text(boat_data.find(_ns("model"))) if boat_data is not None else None,
        "boat_name": _text(boat_data.find(_ns("boat_name"))) if boat_data is not None else None,
        "year_built": _text(boat_data.find(_ns("year_built"))) if boat_data is not None else None,
        "model_year": _text(boat_data.find(_ns("model_year"))) if boat_data is not None else None,
        "loa_meters": loa_el.text.strip() if loa_el is not None and loa_el.text else None,
        "price_type": price_el.get("type") if price_el is not None else None,
        "price_amount": _text(price_el),
        "price_currency": price_el.get("currency") if price_el is not None else None,
        "location_country": location_el.get("country") if location_el is not None else None,
        "image_count": str(image_count),
        "media_image_urls": media_image_urls or None,
        "media_image_md5s": media_image_md5s or None,
        "subtitle": _text(advert_data.find(_ns("subtitle"))) if advert_data is not None else None,
    }


def _map_advert_to_wire(fields: dict[str, str | None]) -> tuple[dict[str, Any], list[str]]:
    """Map the already-extracted raw NautiX fields onto the shared draft
    request wire shape. Blank/absent source fields are omitted (never
    guessed) -- same discipline as the column-mapped formats."""
    wire: dict[str, Any] = {}
    errors: list[str] = []

    brand = fields["manufacturer"] or fields["builder"]
    if brand:
        wire["physical_boat.marketed_brand_claim"] = brand
    if fields["model"]:
        wire["physical_boat.model_designation_claim"] = fields["model"]
    if fields["boat_name"]:
        wire["physical_boat.boat_name"] = fields["boat_name"]

    # Independent review amendment Finding C: `year_built` and `model_year`
    # are two separately defined XSD fields with different real-world
    # semantics (a boat's actual build year vs. its marketed model-year
    # designation, which commonly differ by up to a year for new/demo
    # boats) -- `physical_boat.build_year` is mapped ONLY from
    # `year_built`. A missing `year_built` is an honest absence (core data
    # guardrail: "missing/unknown is not evidence a characteristic is
    # absent"), never silently backfilled from a different-meaning field.
    year_text = fields["year_built"]
    if year_text:
        try:
            wire["physical_boat.build_year"] = int(year_text)
        except ValueError:
            errors.append(f"physical_boat.build_year: expected an integer year, got {year_text!r}")

    # Independent review amendment Finding C: `price/@type` is authoritative
    # for whether an amount is expected at all. Only `type="on-request"`
    # means "no asking amount by definition" -> POA. Every other declared
    # type (fixed/negotiable/auction/share) asserts a real amount exists;
    # a missing amount under one of those types is a genuinely ambiguous/
    # incomplete source record and must never be silently reinterpreted as
    # POA (mechanical invariants: "no guessed ... price ... facts").
    price_type = fields["price_type"]
    price_amount = fields["price_amount"]
    if price_type == "on-request":
        wire["listing_offer.asking_price_mode"] = "POA"
    elif price_amount:
        wire["listing_offer.asking_price_mode"] = "AMOUNT"
        wire["listing_offer.asking_price_amount"] = price_amount
        if fields["price_currency"]:
            wire["listing_offer.currency"] = fields["price_currency"]
    elif price_type is not None:
        errors.append(
            f"sale_data.price: type={price_type!r} declares an asking amount but none was provided"
        )

    if fields["location_country"]:
        wire["listing_offer.location_country"] = fields["location_country"]
    if fields["advert_id"]:
        wire["broker_listing_reference"] = fields["advert_id"]
    if fields["subtitle"]:
        wire["listing_offer.broker_description"] = fields["subtitle"]

    return wire, errors


def map_nautix_adverts_to_rows(
    root: Any, *, attested_account_tokens: frozenset[str]
) -> tuple[StagedRowPreview, ...]:
    """Map every `advert` under every `account` of a validated NautiX
    document into one `StagedRowPreview` per advert, in document order.

    *attested_account_tokens* is the broker-attested set of account tokens
    this Organization currently owns (Required Behavior #2/§37 of the
    slice: "an adverts.xml containing one or multiple accounts only when
    current Organization ownership of each account is explicitly
    attested, otherwise fail closed"). An advert under an unattested
    account token is `INVALID`, never silently skipped or silently
    imported.

    Independent review amendment Finding E: the total advert count across
    every account is bounded by `MAX_IMPORT_ROWS` -- checked *before* any
    row is mapped/materialized, mirroring every column-mapped format's
    identical bound, rather than silently accepting and persisting an
    unbounded number of staged rows from one oversized document.
    """
    total_adverts = sum(
        len(adverts_el.findall(_ns("advert")))
        for account in root.findall(_ns("account"))
        for adverts_el in (account.find(_ns("adverts")),)
        if adverts_el is not None
    )
    if total_adverts > MAX_IMPORT_ROWS:
        raise ImportParseError(
            ImportParseErrorKind.TOO_MANY_ROWS,
            f"more than {MAX_IMPORT_ROWS} adverts across all accounts",
        )

    previews: list[StagedRowPreview] = []
    ordinal = 0
    for account in root.findall(_ns("account")):
        token = account.get("token")
        adverts_el = account.find(_ns("adverts"))
        if adverts_el is None:
            continue
        for advert in adverts_el.findall(_ns("advert")):
            fields = _advert_raw_fields(advert)
            raw_fields: dict[str, str | None] = {"account_token": token, **fields}
            advert_id = fields["advert_id"]

            reasons: list[str] = []
            if not token or token not in attested_account_tokens:
                reasons.append("account token is not in the broker-attested set of owned accounts")
            if fields["advert_type"] != "boat" or fields["advert_purpose"] != "sale":
                reasons.append(
                    "only advert type='boat' purpose='sale' is within this importer's scope "
                    f"(got type={fields['advert_type']!r} purpose={fields['advert_purpose']!r})"
                )
            elif fields["boat_type"] is None:
                reasons.append(
                    "boat is not within HullQ's currently accepted sailboat supply domain"
                )

            source_record_key = (
                SourceRecordKey(f"{token}:{advert_id}") if token and advert_id else None
            )

            if reasons:
                previews.append(
                    StagedRowPreview(
                        row_ordinal=ordinal,
                        raw_fields=raw_fields,
                        unmapped_headers=(),
                        classification=RowPreviewClassification.INVALID,
                        reasons=tuple(reasons),
                        source_record_key=source_record_key,
                        draft_request_wire=None,
                        row_digest=None,
                    )
                )
                ordinal += 1
                continue

            wire, coercion_errors = _map_advert_to_wire(fields)
            if coercion_errors:
                previews.append(
                    StagedRowPreview(
                        row_ordinal=ordinal,
                        raw_fields=raw_fields,
                        unmapped_headers=(),
                        classification=RowPreviewClassification.INVALID,
                        reasons=tuple(coercion_errors),
                        source_record_key=source_record_key,
                        draft_request_wire=None,
                        row_digest=None,
                    )
                )
                ordinal += 1
                continue

            try:
                parse_professional_listing_draft_request(wire)
            except InvalidListingDraftPayloadError as exc:
                previews.append(
                    StagedRowPreview(
                        row_ordinal=ordinal,
                        raw_fields=raw_fields,
                        unmapped_headers=(),
                        classification=RowPreviewClassification.INVALID,
                        reasons=(str(exc),),
                        source_record_key=source_record_key,
                        draft_request_wire=None,
                        row_digest=None,
                    )
                )
                ordinal += 1
                continue

            if fields["advert_status"] == "inactive":
                # Mechanical invariants: "status=inactive is a source
                # status, not HullQ authorization to auto-withdraw a live
                # listing. An inactive existing source mapping is flagged
                # CONFLICT_REVIEW ... and cannot create or mutate a public
                # offer." Treated conservatively here: no automatic draft
                # creation at all for an inactive source row -- it always
                # requires explicit human review.
                previews.append(
                    StagedRowPreview(
                        row_ordinal=ordinal,
                        raw_fields=raw_fields,
                        unmapped_headers=(),
                        classification=RowPreviewClassification.CONFLICT_REVIEW,
                        reasons=("source advert status is 'inactive'",),
                        source_record_key=source_record_key,
                        draft_request_wire=None,
                        row_digest=None,
                    )
                )
                ordinal += 1
                continue

            previews.append(
                StagedRowPreview(
                    row_ordinal=ordinal,
                    raw_fields=raw_fields,
                    unmapped_headers=(),
                    classification=RowPreviewClassification.VALID,
                    reasons=(),
                    source_record_key=source_record_key,
                    draft_request_wire=wire,
                    row_digest=compute_row_digest(wire),
                )
            )
            ordinal += 1

    return tuple(previews)
