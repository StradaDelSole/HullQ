"""Unit tests for `hullq.domain.inventory_export` — SLICE-0088.

Pure domain-level tests: genuine format-byte signatures for all seven
Owner-accepted writers, formula-injection escaping, preflight field-state
reporting, and the NautiX 1.4 pinned-XSD-validation + SLICE-0083 reimport
roundtrip against a hypothetically complete synthetic row (the domain
writer's own correctness proof -- independent of whether any *real*
current HullQ listing can supply every NautiX-mandatory field; that
honest representability gap is proven separately, at the application/API
layer, in `tests/persistence/test_inventory_export_api.py`).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hullq.domain import inventory_export as ie
from hullq.domain.import_intake import RowPreviewClassification
from hullq.domain.import_nautix import map_nautix_adverts_to_rows, parse_and_validate_nautix

_NOW = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
_REAL_MD5 = hashlib.md5(b"fixture-photo-bytes", usedforsecurity=False).hexdigest()


def _complete_row(**overrides: object) -> ie.ExportRow:
    defaults: dict[str, object] = {
        "export_id": "org1:listing1",
        "organization_id": "org1",
        "source_kind": ie.ExportSourceKind.PROMOTED_LISTING,
        "status": "ACTIVE",
        "is_current_public": True,
        "created_at": _NOW,
        "updated_at": _NOW,
        "broker_listing_reference": "REF-001",
        "marketed_brand_claim": "Beneteau",
        "model_designation_claim": "Oceanis 40",
        "build_year": 2015,
        "boat_name": "Sea Breeze",
        "loa_meters": Decimal("12.19"),
        "asking_price_mode": "AMOUNT",
        "asking_price_amount": Decimal("95000"),
        "currency": "EUR",
        "location_country": "FR",
        "location_region": "Brittany",
        "broker_description": "A lovely cruising yacht",
        "media_urls": ("https://example.hullq.test/media/abc.jpg",),
        "media_md5s": (_REAL_MD5,),
        "media_mime_types": ("image/jpeg",),
        "sale_class": "used",
        "nautix_account_token": "BROKER-ACCT-123",
        "nautix_office_id": "OFFICE-1",
    }
    defaults.update(overrides)
    return ie.ExportRow(**defaults)  # type: ignore[arg-type]


def _draft_row(**overrides: object) -> ie.ExportRow:
    defaults: dict[str, object] = {
        "export_id": "org1:draft1",
        "organization_id": "org1",
        "source_kind": ie.ExportSourceKind.PRIVATE_DRAFT,
        "status": "PRIVATE_DRAFT",
        "is_current_public": False,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    defaults.update(overrides)
    return ie.ExportRow(**defaults)  # type: ignore[arg-type]


class TestExportFormatRegistry:
    def test_xlsb_is_not_an_accepted_format(self) -> None:
        assert "XLSB" not in {f.value for f in ie.ExportFormat}

    def test_exactly_seven_formats(self) -> None:
        assert len(ie.ExportFormat) == 7


class TestFormulaInjectionEscaping:
    @pytest.mark.parametrize("payload", ["=2+2", "+2+2", "-2+2", "@SUM(A1)", "\tcmd"])
    def test_dangerous_leading_character_is_escaped(self, payload: str) -> None:
        safe, modified = ie.escape_formula_injection(payload)
        assert modified is True
        assert safe.startswith("'")
        assert payload in safe

    def test_benign_text_is_untouched(self) -> None:
        safe, modified = ie.escape_formula_injection("Beneteau Oceanis")
        assert modified is False
        assert safe == "Beneteau Oceanis"

    def test_control_characters_are_stripped(self) -> None:
        safe, modified = ie.escape_formula_injection("Sea\x00Breeze")
        assert modified is True
        assert "\x00" not in safe


class TestTableWriters:
    @pytest.mark.parametrize(
        ("writer", "magic"),
        [
            (ie.write_csv, b"export_id,status"),
            (ie.write_tsv, b"export_id\tstatus"),
            (ie.write_xlsx, b"PK"),
            (ie.write_xls, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
            (ie.write_ods, b"PK"),
        ],
    )
    def test_genuine_binary_signature(self, writer: object, magic: bytes) -> None:
        content = writer([_complete_row()])  # type: ignore[operator]
        assert content[: len(magic)] == magic

    def test_json_writer_produces_documented_profile(self) -> None:
        content = ie.write_json([_complete_row()])
        import json

        payload = json.loads(content)
        assert set(payload) == {"listings"}
        assert payload["listings"][0]["physical_boat.marketed_brand_claim"] == "Beneteau"

    def test_formula_injection_payload_is_escaped_in_csv(self) -> None:
        row = _draft_row(marketed_brand_claim="=2+2")
        content = ie.write_csv([row])
        assert b",=2+2" not in content
        assert b"'=2+2" in content

    def test_formula_injection_payload_is_not_escaped_in_json(self) -> None:
        # JSON values are never evaluated as spreadsheet formulas -- escaping
        # would only corrupt reimport fidelity for this format.
        row = _draft_row(marketed_brand_claim="=2+2")
        content = ie.write_json([row])
        assert b'"=2+2"' in content

    def test_xls_rejects_oversized_selection(self) -> None:
        rows = [_complete_row(export_id=f"org1:listing{i}") for i in range(2)]
        with pytest.raises(ie.ExportWriteError):
            ie.write_xls(rows * (ie.MAX_XLS_ROWS // 2 + 1))


class TestExportRowValidation:
    def test_invalid_sale_class_is_rejected_at_construction(self) -> None:
        with pytest.raises(ValueError, match="sale_class"):
            _complete_row(sale_class="not-a-real-sale-class")

    def test_every_allowed_sale_class_constructs(self) -> None:
        for value in ie.ALLOWED_NAUTIX_SALE_CLASSES:
            _complete_row(sale_class=value)  # must not raise

    def test_not_applicable_is_excluded(self) -> None:
        assert "not-applicable" not in ie.ALLOWED_NAUTIX_SALE_CLASSES


class TestPreflight:
    def test_complete_promoted_row_is_exportable_in_all_table_formats(self) -> None:
        preflight = ie.build_row_preflight(_complete_row())
        for fmt in ie.ExportFormat:
            if fmt is ie.ExportFormat.NAUTIX:
                continue
            assert preflight.formats[fmt].exportable is True

    def test_complete_row_with_sale_class_is_nautix_exportable(self) -> None:
        preflight = ie.build_row_preflight(_complete_row())
        assert preflight.formats[ie.ExportFormat.NAUTIX].exportable is True

    def test_private_draft_is_never_nautix_exportable(self) -> None:
        preflight = ie.build_row_preflight(_draft_row())
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("private draft" in r for r in nautix.reasons)

    def test_missing_sale_class_is_not_exportable_never_fabricated(self) -> None:
        preflight = ie.build_row_preflight(_complete_row(sale_class=None))
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("sale_class" in r for r in nautix.reasons)

    def test_missing_account_token_is_not_exportable_never_fabricated_from_org_id(self) -> None:
        preflight = ie.build_row_preflight(_complete_row(nautix_account_token=None))
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("account.token" in r for r in nautix.reasons)

    def test_missing_office_id_is_not_exportable_never_a_placeholder(self) -> None:
        preflight = ie.build_row_preflight(_complete_row(nautix_office_id=None))
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("office_id" in r for r in nautix.reasons)

    def test_active_but_not_current_public_is_never_nautix_active(self) -> None:
        preflight = ie.build_row_preflight(_complete_row(is_current_public=False))
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("status" in r for r in nautix.reasons)

    def test_unknown_build_year_is_distinct_from_omitted(self) -> None:
        unknown_pf = ie.build_row_preflight(_complete_row(build_year=None, build_year_unknown=True))
        omitted_pf = ie.build_row_preflight(
            _complete_row(build_year=None, build_year_unknown=False)
        )
        assert unknown_pf.field_states["physical_boat.build_year"] == ie.ExportFieldState.UNKNOWN
        assert omitted_pf.field_states["physical_boat.build_year"] == ie.ExportFieldState.OMITTED

    def test_photo_without_valid_md5_is_not_usable_for_nautix(self) -> None:
        row = _complete_row(media_md5s=("not-a-valid-md5",))
        preflight = ie.build_row_preflight(row)
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("media.images" in r for r in nautix.reasons)

    def test_photo_without_allowed_mime_type_is_not_usable_for_nautix(self) -> None:
        row = _complete_row(media_mime_types=("application/pdf",))
        preflight = ie.build_row_preflight(row)
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("media.images" in r for r in nautix.reasons)

    # SLICE-0093 Required Behavior §7: the Sail-only NautiX "sail-yacht"
    # catalog type must never coerce an explicitly non-SAIL listing.

    def test_explicit_power_vessel_category_is_never_nautix_exportable(self) -> None:
        row = _complete_row(vessel_category="POWER")
        preflight = ie.build_row_preflight(row)
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("boat_type" in r for r in nautix.reasons)

    def test_explicit_motorsailer_vessel_category_is_never_nautix_exportable(self) -> None:
        row = _complete_row(vessel_category="MOTORSAILER")
        preflight = ie.build_row_preflight(row)
        nautix = preflight.formats[ie.ExportFormat.NAUTIX]
        assert nautix.exportable is False
        assert any("boat_type" in r for r in nautix.reasons)

    def test_explicit_sail_vessel_category_is_still_nautix_exportable(self) -> None:
        preflight = ie.build_row_preflight(_complete_row(vessel_category="SAIL"))
        assert preflight.formats[ie.ExportFormat.NAUTIX].exportable is True

    def test_omitted_vessel_category_preserves_existing_default_sail_assumption(self) -> None:
        """A `None` vessel_category (every pre-0093 row/caller) must keep
        exporting exactly as before -- the seven accepted Sail output
        formats remain unaffected."""
        preflight = ie.build_row_preflight(_complete_row(vessel_category=None))
        assert preflight.formats[ie.ExportFormat.NAUTIX].exportable is True

    def test_power_category_does_not_affect_the_other_six_formats(self) -> None:
        preflight = ie.build_row_preflight(_complete_row(vessel_category="POWER"))
        for fmt in ie.ExportFormat:
            if fmt is ie.ExportFormat.NAUTIX:
                continue
            assert preflight.formats[fmt].exportable is True

    def test_invalid_vessel_category_is_rejected_at_construction(self) -> None:
        with pytest.raises(ValueError, match="vessel_category"):
            _complete_row(vessel_category="NOT_A_REAL_CATEGORY")


class TestNautixWriterRoundtrip:
    def test_complete_row_passes_pinned_xsd_and_0083_reimport(self) -> None:
        row = _complete_row()
        document = ie.build_nautix_document([row], generated_at=_NOW)
        root = parse_and_validate_nautix(document)
        mapped = map_nautix_adverts_to_rows(
            root, attested_account_tokens=frozenset({"BROKER-ACCT-123"})
        )
        assert len(mapped) == 1
        assert mapped[0].classification is RowPreviewClassification.VALID, mapped[0].reasons

    def test_not_exportable_row_is_silently_omitted_never_fabricated(self) -> None:
        # Missing sale_class -> NOT_EXPORTABLE; the document must contain
        # zero adverts, never a fabricated sale_class value.
        row = _complete_row(sale_class=None)
        document = ie.build_nautix_document([row], generated_at=_NOW)
        root = parse_and_validate_nautix(document)
        mapped = map_nautix_adverts_to_rows(
            root, attested_account_tokens=frozenset({"BROKER-ACCT-123"})
        )
        assert len(mapped) == 0

    def test_withdrawn_listing_maps_to_inactive_status(self) -> None:
        row = _complete_row(status="WITHDRAWN", is_current_public=False)
        document = ie.build_nautix_document([row], generated_at=_NOW)
        assert b'status="inactive"' in document
        root = parse_and_validate_nautix(document)
        mapped = map_nautix_adverts_to_rows(
            root, attested_account_tokens=frozenset({"BROKER-ACCT-123"})
        )
        assert len(mapped) == 1
        assert mapped[0].classification is RowPreviewClassification.CONFLICT_REVIEW

    def test_poa_price_roundtrips(self) -> None:
        row = _complete_row(asking_price_mode="POA", asking_price_amount=None, currency=None)
        document = ie.build_nautix_document([row], generated_at=_NOW)
        root = parse_and_validate_nautix(document)
        mapped = map_nautix_adverts_to_rows(
            root, attested_account_tokens=frozenset({"BROKER-ACCT-123"})
        )
        assert len(mapped) == 1
        assert mapped[0].draft_request_wire is not None
        assert mapped[0].draft_request_wire["listing_offer.asking_price_mode"] == "POA"

    def test_malicious_doctype_payload_in_subtitle_cannot_smuggle_xxe(self) -> None:
        # The broker_description text is placed inside an element's text
        # content via lxml's own text assignment, never raw string
        # concatenation -- lxml escapes it as ordinary XML text, so a
        # literal "<!DOCTYPE" payload can never become a real DTD
        # declaration in the output document.
        row = _complete_row(
            broker_description="<!DOCTYPE foo [ <!ENTITY xxe SYSTEM 'file:///etc/passwd'> ]>"
        )
        document = ie.build_nautix_document([row], generated_at=_NOW)
        assert b"<!DOCTYPE" not in document
        # Still passes the pinned XSD/secure-parser roundtrip unchanged.
        parse_and_validate_nautix(document)
