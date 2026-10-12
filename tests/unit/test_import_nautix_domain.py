"""Pure domain unit tests for SLICE-0083 `hullq.domain.import_nautix`.

Validates against the actual pinned official NautiX 1.4 XSD
(`hullq.domain.nautix_schema`, provenance in that package's
`PROVENANCE.md`) -- no hand-written subset validator. Covers XSD-valid
sale/boat mapping, inactive-status conflict-review, unsupported advert
type, unattested account token, and the XXE/DOCTYPE/wrong-namespace/
malformed/XSD-invalid adversarial fail-closed paths.
"""

from __future__ import annotations

import pytest

from hullq.domain.import_intake import (
    ImportParseError,
    ImportParseErrorKind,
    RowPreviewClassification,
)
from hullq.domain.import_nautix import map_nautix_adverts_to_rows, parse_and_validate_nautix

_NS = "https://nautix.nautic-network.org/v1.4/"


def _wrap(account_body: str) -> bytes:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<nautix xmlns="{_NS}" version="1.4" date="2026-10-01T10:00:00+02:00">
{account_body}
</nautix>
""".encode()


_VALID_ACTIVE_SAIL_ADVERT = """
  <account token="ACME-1" status="active">
    <account_name>Acme Yacht Brokers</account_name>
    <adverts count="1">
      <advert id="ADV-0001" purpose="sale" type="boat" status="active" modified="2026-09-15T08:00:00+02:00">
        <advert_data>
          <office_id>OFFICE-1</office_id>
          <subtitle>Well-maintained cruising yacht</subtitle>
        </advert_data>
        <sale_data>
          <sale_class>used</sale_class>
          <price type="fixed" currency="EUR">125000.00</price>
          <location country="ES"/>
        </sale_data>
        <boat_data>
          <boat_types><type primary="true">sail-yacht</type></boat_types>
          <manufacturer>Beneteau</manufacturer>
          <model>Oceanis 46.1</model>
          <boat_name>Aria</boat_name>
          <year_built>2019</year_built>
        </boat_data>
      </advert>
    </adverts>
  </account>
"""


class TestParseAndValidateNautix:
    def test_valid_document_passes(self) -> None:
        root = parse_and_validate_nautix(_wrap(_VALID_ACTIVE_SAIL_ADVERT))
        assert root.tag == f"{{{_NS}}}nautix"

    def test_rejects_doctype(self) -> None:
        raw = (
            b'<?xml version="1.0"?>\n'
            b'<!DOCTYPE nautix [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n' + _wrap("&xxe;")
        )
        with pytest.raises(ImportParseError) as exc_info:
            parse_and_validate_nautix(raw)
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_rejects_wrong_namespace(self) -> None:
        raw = (
            b'<?xml version="1.0"?>\n'
            b'<nautix xmlns="https://example.com/not-nautix/" version="1.4" '
            b'date="2026-10-01T10:00:00+02:00"/>\n'
        )
        with pytest.raises(ImportParseError) as exc_info:
            parse_and_validate_nautix(raw)
        assert exc_info.value.kind is ImportParseErrorKind.UNSUPPORTED_FORMAT

    def test_rejects_wrong_version(self) -> None:
        raw = (
            f'<?xml version="1.0"?>\n<nautix xmlns="{_NS}" version="1.3" '
            f'date="2026-10-01T10:00:00+02:00"/>\n'
        ).encode()
        with pytest.raises(ImportParseError) as exc_info:
            parse_and_validate_nautix(raw)
        assert exc_info.value.kind is ImportParseErrorKind.UNSUPPORTED_FORMAT

    def test_rejects_malformed_xml(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_and_validate_nautix(b"<nautix><unclosed>")
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_rejects_xsd_invalid_document(self) -> None:
        """Syntactically well-formed, correct namespace/version, but
        missing a schema-required element (`sale_data.location`) -- must be
        denied by real XSD validation, not a hand-written subset check."""
        missing_location = """
  <account token="T" status="active">
    <account_name>X</account_name>
    <adverts>
      <advert id="A1" purpose="sale" type="boat" status="active" modified="2026-09-15T08:00:00+02:00">
        <sale_data>
          <sale_class>used</sale_class>
          <price type="on-request"></price>
        </sale_data>
      </advert>
    </adverts>
  </account>
"""
        with pytest.raises(ImportParseError) as exc_info:
            parse_and_validate_nautix(_wrap(missing_location))
        assert exc_info.value.kind is ImportParseErrorKind.MALFORMED

    def test_rejects_empty_file(self) -> None:
        with pytest.raises(ImportParseError) as exc_info:
            parse_and_validate_nautix(b"")
        assert exc_info.value.kind is ImportParseErrorKind.EMPTY


class TestMapNautixAdvertsToRows:
    def test_valid_sail_sale_advert_maps_to_valid_row(self) -> None:
        root = parse_and_validate_nautix(_wrap(_VALID_ACTIVE_SAIL_ADVERT))
        rows = map_nautix_adverts_to_rows(root, attested_account_tokens=frozenset({"ACME-1"}))
        assert len(rows) == 1
        row = rows[0]
        assert row.classification is RowPreviewClassification.VALID
        assert row.source_record_key is not None
        assert row.source_record_key.value == "ACME-1:ADV-0001"
        assert row.draft_request_wire == {
            "physical_boat.marketed_brand_claim": "Beneteau",
            "physical_boat.model_designation_claim": "Oceanis 46.1",
            "physical_boat.boat_name": "Aria",
            "physical_boat.build_year": 2019,
            "listing_offer.asking_price_mode": "AMOUNT",
            "listing_offer.asking_price_amount": "125000.00",
            "listing_offer.currency": "EUR",
            "listing_offer.location_country": "ES",
            "broker_listing_reference": "ADV-0001",
            "listing_offer.broker_description": "Well-maintained cruising yacht",
        }

    def test_unattested_account_token_is_invalid(self) -> None:
        root = parse_and_validate_nautix(_wrap(_VALID_ACTIVE_SAIL_ADVERT))
        rows = map_nautix_adverts_to_rows(root, attested_account_tokens=frozenset())
        assert rows[0].classification is RowPreviewClassification.INVALID
        assert any("attested" in r for r in rows[0].reasons)

    def test_inactive_status_is_conflict_review_not_valid(self) -> None:
        inactive = _VALID_ACTIVE_SAIL_ADVERT.replace(
            'status="active" modified="2026-09-15T08:00:00+02:00">',
            'status="inactive" modified="2026-09-15T08:00:00+02:00">',
            1,
        )
        root = parse_and_validate_nautix(_wrap(inactive))
        rows = map_nautix_adverts_to_rows(root, attested_account_tokens=frozenset({"ACME-1"}))
        assert rows[0].classification is RowPreviewClassification.CONFLICT_REVIEW
        assert rows[0].draft_request_wire is None

    def test_non_boat_advert_type_is_invalid(self) -> None:
        engine_advert = """
  <account token="ACME-1" status="active">
    <account_name>Acme Yacht Brokers</account_name>
    <adverts>
      <advert id="ADV-ENGINE" purpose="sale" type="engine" status="active" modified="2026-09-15T08:00:00+02:00">
        <sale_data>
          <sale_class>used</sale_class>
          <price type="on-request"></price>
          <location country="ES"/>
        </sale_data>
      </advert>
    </adverts>
  </account>
"""
        root = parse_and_validate_nautix(_wrap(engine_advert))
        rows = map_nautix_adverts_to_rows(root, attested_account_tokens=frozenset({"ACME-1"}))
        assert rows[0].classification is RowPreviewClassification.INVALID

    def test_non_sailboat_boat_type_is_invalid(self) -> None:
        power_advert = """
  <account token="ACME-1" status="active">
    <account_name>Acme Yacht Brokers</account_name>
    <adverts>
      <advert id="ADV-POWER" purpose="sale" type="boat" status="active" modified="2026-09-15T08:00:00+02:00">
        <sale_data>
          <sale_class>used</sale_class>
          <price type="on-request"></price>
          <location country="ES"/>
        </sale_data>
        <boat_data>
          <boat_types><type primary="true">power-yacht</type></boat_types>
          <model>Some Powerboat</model>
        </boat_data>
      </advert>
    </adverts>
  </account>
"""
        root = parse_and_validate_nautix(_wrap(power_advert))
        rows = map_nautix_adverts_to_rows(root, attested_account_tokens=frozenset({"ACME-1"}))
        assert rows[0].classification is RowPreviewClassification.INVALID

    def test_poa_price_maps_without_amount(self) -> None:
        poa_advert = _VALID_ACTIVE_SAIL_ADVERT.replace(
            '<price type="fixed" currency="EUR">125000.00</price>',
            '<price type="on-request"></price>',
        )
        root = parse_and_validate_nautix(_wrap(poa_advert))
        rows = map_nautix_adverts_to_rows(root, attested_account_tokens=frozenset({"ACME-1"}))
        assert rows[0].classification is RowPreviewClassification.VALID
        assert rows[0].draft_request_wire is not None
        assert rows[0].draft_request_wire["listing_offer.asking_price_mode"] == "POA"
        assert "listing_offer.asking_price_amount" not in rows[0].draft_request_wire
