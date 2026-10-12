"""Pure domain unit tests for SLICE-0083 `hullq.domain.import_intake`.

Covers the shared mapping/classification engine: snapshot-key derivation,
column-mapping validation, per-row coercion, in-file duplicate-key
detection and the VALID/INVALID/CONFLICT_REVIEW three-way classification.
Format-specific parsers are covered in their own
`test_import_parsers_domain.py`/`test_import_spreadsheet_domain.py`/
`test_import_nautix_domain.py`; durable staging/confirm state is covered in
`tests/persistence/test_import_intake_persistence.py`.
"""

from __future__ import annotations

import pytest

from hullq.domain.import_intake import (
    IGNORE_TARGET,
    SOURCE_RECORD_KEY_TARGET,
    ImportSource,
    InvalidColumnMappingError,
    ParsedTable,
    RowPreviewClassification,
    SourceRecordKey,
    apply_mapping_to_rows,
    compute_file_sha256,
    compute_row_digest,
    normalize_source_record_key,
    snapshot_source_record_key,
    validate_mapping,
)


class TestImportSource:
    def test_accepts_simple_name(self) -> None:
        assert ImportSource("NautiX Export 2026").value == "NautiX Export 2026"

    @pytest.mark.parametrize("bad", ["", " leading-space", "has/slash", "x" * 64])
    def test_rejects_invalid_values(self, bad: str) -> None:
        with pytest.raises(ValueError):
            ImportSource(bad)


class TestSourceRecordKey:
    def test_normalize_strips_whitespace_only(self) -> None:
        key = normalize_source_record_key("  REF-001  ")
        assert key.value == "REF-001"

    def test_normalize_preserves_case(self) -> None:
        assert normalize_source_record_key("AbC-1").value == "AbC-1"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            SourceRecordKey("")

    def test_rejects_oversize(self) -> None:
        with pytest.raises(ValueError):
            SourceRecordKey("x" * 201)


class TestSnapshotSourceRecordKey:
    def test_deterministic_for_same_digest_and_ordinal(self) -> None:
        digest = compute_file_sha256(b"hello world")
        a = snapshot_source_record_key(digest, 0)
        b = snapshot_source_record_key(digest, 0)
        assert a == b

    def test_distinct_for_distinct_ordinal(self) -> None:
        digest = compute_file_sha256(b"hello world")
        a = snapshot_source_record_key(digest, 0)
        b = snapshot_source_record_key(digest, 1)
        assert a != b

    def test_distinct_for_distinct_file(self) -> None:
        a = snapshot_source_record_key(compute_file_sha256(b"one"), 0)
        b = snapshot_source_record_key(compute_file_sha256(b"two"), 0)
        assert a != b

    def test_rejects_malformed_digest(self) -> None:
        with pytest.raises(ValueError):
            snapshot_source_record_key("not-a-digest", 0)

    def test_rejects_negative_ordinal(self) -> None:
        with pytest.raises(ValueError):
            snapshot_source_record_key(compute_file_sha256(b"x"), -1)


class TestComputeRowDigest:
    def test_order_independent(self) -> None:
        a = compute_row_digest({"a": "1", "b": "2"})
        b = compute_row_digest({"b": "2", "a": "1"})
        assert a == b

    def test_sensitive_to_value_change(self) -> None:
        a = compute_row_digest({"a": "1"})
        b = compute_row_digest({"a": "2"})
        assert a != b


_HEADERS = ("Boat Name", "Build Year", "Price", "Ref")


def _table(rows: tuple[tuple[str | None, ...], ...]) -> ParsedTable:
    return ParsedTable(headers=_HEADERS, rows=rows)


_FULL_MAPPING = {
    "Boat Name": "physical_boat.boat_name",
    "Build Year": "physical_boat.build_year",
    "Price": "listing_offer.asking_price_amount",
    "Ref": SOURCE_RECORD_KEY_TARGET,
}


class TestValidateMapping:
    def test_accepts_complete_unambiguous_mapping(self) -> None:
        validate_mapping(_HEADERS, _FULL_MAPPING, snapshot_mode=False)

    def test_rejects_missing_column(self) -> None:
        incomplete = dict(_FULL_MAPPING)
        del incomplete["Ref"]
        with pytest.raises(InvalidColumnMappingError):
            validate_mapping(_HEADERS, incomplete, snapshot_mode=False)

    def test_rejects_unknown_column(self) -> None:
        extra = dict(_FULL_MAPPING)
        extra["Nonexistent"] = IGNORE_TARGET
        with pytest.raises(InvalidColumnMappingError):
            validate_mapping(_HEADERS, extra, snapshot_mode=False)

    def test_rejects_unknown_target(self) -> None:
        bad = dict(_FULL_MAPPING)
        bad["Boat Name"] = "not.a.real.target"
        with pytest.raises(InvalidColumnMappingError):
            validate_mapping(_HEADERS, bad, snapshot_mode=False)

    def test_rejects_ambiguous_duplicate_target(self) -> None:
        ambiguous = dict(_FULL_MAPPING)
        ambiguous["Build Year"] = "physical_boat.boat_name"
        with pytest.raises(InvalidColumnMappingError):
            validate_mapping(_HEADERS, ambiguous, snapshot_mode=False)

    def test_rejects_no_key_column_without_snapshot_mode(self) -> None:
        no_key = dict(_FULL_MAPPING)
        no_key["Ref"] = IGNORE_TARGET
        with pytest.raises(InvalidColumnMappingError):
            validate_mapping(_HEADERS, no_key, snapshot_mode=False)

    def test_rejects_key_column_with_snapshot_mode(self) -> None:
        with pytest.raises(InvalidColumnMappingError):
            validate_mapping(_HEADERS, _FULL_MAPPING, snapshot_mode=True)

    def test_accepts_no_key_column_with_snapshot_mode(self) -> None:
        no_key = dict(_FULL_MAPPING)
        no_key["Ref"] = IGNORE_TARGET
        validate_mapping(_HEADERS, no_key, snapshot_mode=True)


class TestApplyMappingToRows:
    def test_maps_valid_row(self) -> None:
        table = _table((("Aria", "1998", "125000", "REF-1"),))
        digest = compute_file_sha256(b"irrelevant")
        rows = apply_mapping_to_rows(table, _FULL_MAPPING, snapshot_mode=False, file_sha256=digest)
        assert len(rows) == 1
        row = rows[0]
        assert row.classification is RowPreviewClassification.VALID
        assert row.reasons == ()
        assert row.source_record_key is not None
        assert row.source_record_key.value == "REF-1"
        assert row.draft_request_wire == {
            "physical_boat.boat_name": "Aria",
            "physical_boat.build_year": 1998,
            "listing_offer.asking_price_amount": "125000",
        }
        assert row.row_digest is not None

    def test_blank_cell_is_omitted_not_guessed(self) -> None:
        table = _table((("Aria", "", "", "REF-1"),))
        digest = compute_file_sha256(b"irrelevant")
        rows = apply_mapping_to_rows(table, _FULL_MAPPING, snapshot_mode=False, file_sha256=digest)
        assert rows[0].classification is RowPreviewClassification.VALID
        assert "physical_boat.build_year" not in (rows[0].draft_request_wire or {})
        assert "listing_offer.asking_price_amount" not in (rows[0].draft_request_wire or {})

    def test_malformed_year_is_invalid(self) -> None:
        table = _table((("Aria", "not-a-year", "125000", "REF-1"),))
        digest = compute_file_sha256(b"irrelevant")
        rows = apply_mapping_to_rows(table, _FULL_MAPPING, snapshot_mode=False, file_sha256=digest)
        assert rows[0].classification is RowPreviewClassification.INVALID
        assert rows[0].draft_request_wire is None
        assert any("build_year" in reason for reason in rows[0].reasons)

    def test_price_with_currency_symbol_is_invalid_not_stripped(self) -> None:
        table = _table((("Aria", "1998", "$125,000", "REF-1"),))
        digest = compute_file_sha256(b"irrelevant")
        rows = apply_mapping_to_rows(table, _FULL_MAPPING, snapshot_mode=False, file_sha256=digest)
        assert rows[0].classification is RowPreviewClassification.INVALID

    def test_missing_source_key_is_invalid(self) -> None:
        table = _table((("Aria", "1998", "125000", ""),))
        digest = compute_file_sha256(b"irrelevant")
        rows = apply_mapping_to_rows(table, _FULL_MAPPING, snapshot_mode=False, file_sha256=digest)
        assert rows[0].classification is RowPreviewClassification.INVALID
        assert rows[0].source_record_key is None

    def test_duplicate_source_key_in_file_marks_both_invalid(self) -> None:
        table = _table(
            (
                ("Aria", "1998", "125000", "REF-1"),
                ("Beta", "2001", "89000", "REF-1"),
            )
        )
        digest = compute_file_sha256(b"irrelevant")
        rows = apply_mapping_to_rows(table, _FULL_MAPPING, snapshot_mode=False, file_sha256=digest)
        assert rows[0].classification is RowPreviewClassification.INVALID
        assert rows[1].classification is RowPreviewClassification.INVALID
        assert rows[0].draft_request_wire is None
        assert rows[1].draft_request_wire is None

    def test_snapshot_mode_derives_server_authored_key(self) -> None:
        no_key_mapping = dict(_FULL_MAPPING)
        no_key_mapping["Ref"] = IGNORE_TARGET
        table = _table((("Aria", "1998", "125000", "whatever"),))
        digest = compute_file_sha256(b"my-file-bytes")
        rows = apply_mapping_to_rows(table, no_key_mapping, snapshot_mode=True, file_sha256=digest)
        assert rows[0].classification is RowPreviewClassification.VALID
        assert rows[0].source_record_key == snapshot_source_record_key(digest, 0)

    def test_two_rows_same_digest_amount_different_rows_do_not_collide(self) -> None:
        table = _table(
            (
                ("Aria", "1998", "125000", "REF-1"),
                ("Beta", "2001", "89000", "REF-2"),
            )
        )
        digest = compute_file_sha256(b"irrelevant")
        rows = apply_mapping_to_rows(table, _FULL_MAPPING, snapshot_mode=False, file_sha256=digest)
        assert rows[0].classification is RowPreviewClassification.VALID
        assert rows[1].classification is RowPreviewClassification.VALID
        assert rows[0].source_record_key != rows[1].source_record_key

    def test_invalid_mapping_itself_raises_before_any_row_processed(self) -> None:
        bad_mapping = dict(_FULL_MAPPING)
        bad_mapping["Boat Name"] = "physical_boat.build_year"  # duplicate target
        table = _table((("Aria", "1998", "125000", "REF-1"),))
        with pytest.raises(InvalidColumnMappingError):
            apply_mapping_to_rows(
                table, bad_mapping, snapshot_mode=False, file_sha256=compute_file_sha256(b"x")
            )
