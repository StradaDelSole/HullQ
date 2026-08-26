"""Unit tests for schema serialization helpers — SLICE-0013."""

from __future__ import annotations

from hullq.domain.provenance import (
    ProducerKind,
    ProducerMetadata,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
)
from hullq.persistence.schema import (
    ENCODED_VALUE_PAYLOAD_KEY,
    ENCODED_VALUE_TYPE_DECIMAL,
    ENCODED_VALUE_TYPE_KEY,
    ENCODED_VALUE_TYPE_RAW,
    EncodedValueError,
    applicability_from_jsonb,
    applicability_to_jsonb,
    context_to_jsonb,
    decode_normalized_value,
    encode_normalized_value,
    locator_to_jsonb,
    normalized_to_jsonb,
    producer_to_jsonb,
    raw_to_jsonb,
    target_to_jsonb,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import NormalizedCandidate, ObservationApplicability


def _make_app(**kwargs: object) -> ObservationApplicability:
    defaults: dict[str, object] = {
        "first_year": None,
        "last_year": None,
        "hull_number_from": None,
        "hull_number_to": None,
        "market_or_region": None,
        "named_variant_hint": None,
        "design_option_hints": None,
        "operating_state_hint": None,
        "individual_hull_or_listing_ref": None,
        "unknown_or_unbounded": True,
    }
    defaults.update(kwargs)
    return ObservationApplicability(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# target_to_jsonb
# ---------------------------------------------------------------------------


def test_target_to_jsonb_all_fields() -> None:
    t = ResearchTarget(manufacturer="Acme", model="Test 35", first_built=1980)
    d = target_to_jsonb(t)
    assert d == {"manufacturer": "Acme", "model": "Test 35", "first_built": 1980}


def test_target_to_jsonb_nulls() -> None:
    t = ResearchTarget(manufacturer=None, model="X", first_built=None)
    d = target_to_jsonb(t)
    assert d["manufacturer"] is None
    assert d["first_built"] is None


# ---------------------------------------------------------------------------
# locator_to_jsonb
# ---------------------------------------------------------------------------


def test_locator_to_jsonb_all_none() -> None:
    loc = SourceLocator(
        page=None, section=None, anchor=None, table=None, figure=None, record_key=None
    )
    d = locator_to_jsonb(loc)
    assert all(v is None for v in d.values())


def test_locator_to_jsonb_page_int() -> None:
    loc = SourceLocator(page=5, section="A", anchor=None, table=None, figure=None, record_key=None)
    d = locator_to_jsonb(loc)
    assert d["page"] == 5
    assert d["section"] == "A"


# ---------------------------------------------------------------------------
# raw_to_jsonb
# ---------------------------------------------------------------------------


def test_raw_to_jsonb_literal() -> None:
    raw = RawObservation(kind=RawObservationKind.LITERAL, value="10.5", unit="m", excerpt=None)
    d = raw_to_jsonb(raw)
    assert d["kind"] == "literal"
    assert d["value"] == "10.5"
    assert d["unit"] == "m"
    assert d["excerpt"] is None


# ---------------------------------------------------------------------------
# normalized_to_jsonb
# ---------------------------------------------------------------------------


def test_normalized_to_jsonb_none() -> None:
    assert normalized_to_jsonb(None) is None


def test_normalized_to_jsonb_present() -> None:
    nc = NormalizedCandidate(value=10.5, unit="m", method_id="std", method_version="1.0")
    d = normalized_to_jsonb(nc)
    assert d is not None
    assert d["value"] == {
        ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_RAW,
        ENCODED_VALUE_PAYLOAD_KEY: 10.5,
    }
    assert d["method_id"] == "std"


def test_normalized_to_jsonb_decimal_value_wrapped_in_type_envelope() -> None:
    """SLICE-0026: every measurement value hullq.sources.wikidata produces via
    hullq.domain.measurements.normalize_measurement is a Decimal.
    NormalizedCandidate.value is untyped (``object``) with a genuinely
    unconstrained accepted domain (FIELD_EVIDENCE_SCHEMA.v0.2), so no bare
    marker shape can be proven collision-safe against a legitimate value
    that happens to look like it. normalized_to_jsonb must therefore wrap
    EVERY value (not only Decimal) in the total {type, value} envelope
    rather than raising ``TypeError: Object of type Decimal is not JSON
    serializable`` and rather than risking an ambiguous partial encoding.
    """
    from decimal import Decimal

    nc = NormalizedCandidate(
        value=Decimal("12.80"),
        unit="m",
        method_id="hullq-measurements-1.0",
        method_version="SLICE-0004-v1",
    )
    d = normalized_to_jsonb(nc)
    assert d is not None
    assert d["value"] == {
        ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_DECIMAL,
        ENCODED_VALUE_PAYLOAD_KEY: "12.80",
    }

    import json

    # Must not raise — this is exactly the shape passed to psycopg's Jsonb().
    json.dumps(d)


def test_normalized_to_jsonb_numeric_looking_string_passes_through_as_raw() -> None:
    """A legitimately string-typed NormalizedCandidate.value that happens to
    look numeric (e.g. "12.80") must NOT be treated as, or collapse with, a
    Decimal — no numeric-looking-text heuristic is applied on the encode
    side either; it is embedded verbatim under the "raw" envelope type."""
    nc = NormalizedCandidate(value="12.80", unit="m", method_id="std", method_version="1.0")
    d = normalized_to_jsonb(nc)
    assert d is not None
    assert d["value"] == {
        ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_RAW,
        ENCODED_VALUE_PAYLOAD_KEY: "12.80",
    }


def test_normalized_to_jsonb_value_that_looks_like_the_decimal_envelope_passes_through_as_raw() -> (
    None
):
    """A legitimate structured NormalizedCandidate.value that itself happens
    to look exactly like the encoder's own Decimal-envelope shape (e.g.
    ``{"__decimal__": "12.80"}`` under a hypothetical earlier marker scheme,
    or literally any dict) must round-trip completely unchanged, nested
    ONE level under the "raw" envelope — never misread as an actual
    Decimal."""
    lookalike = {"__decimal__": "12.80"}
    nc = NormalizedCandidate(value=lookalike, unit="m", method_id=None, method_version=None)
    d = normalized_to_jsonb(nc)
    assert d is not None
    assert d["value"] == {
        ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_RAW,
        ENCODED_VALUE_PAYLOAD_KEY: lookalike,
    }
    assert d["value"] != {
        ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_DECIMAL,
        ENCODED_VALUE_PAYLOAD_KEY: "12.80",
    }


def test_encode_normalized_value_distinguishes_decimal_from_equal_text_string() -> None:
    from decimal import Decimal

    encoded_decimal = encode_normalized_value(Decimal("12.80"))
    encoded_string = encode_normalized_value("12.80")
    assert encoded_decimal != encoded_string
    assert encoded_decimal == {
        ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_DECIMAL,
        ENCODED_VALUE_PAYLOAD_KEY: "12.80",
    }
    assert encoded_string == {
        ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_RAW,
        ENCODED_VALUE_PAYLOAD_KEY: "12.80",
    }


def test_decode_normalized_value_round_trips_decimal_exactly() -> None:
    from decimal import Decimal

    encoded = encode_normalized_value(Decimal("12.80"))
    assert decode_normalized_value(encoded) == Decimal("12.80")
    assert isinstance(decode_normalized_value(encoded), Decimal)


def test_decode_normalized_value_round_trips_plain_string_exactly() -> None:
    encoded = encode_normalized_value("12.80")
    decoded = decode_normalized_value(encoded)
    assert decoded == "12.80"
    assert isinstance(decoded, str)


def test_decode_normalized_value_round_trips_decimal_lookalike_dict_exactly() -> None:
    """The exact scenario the reviewer flagged: a legitimate structured value
    equal to {"__decimal__": "12.80"} must decode back to that same dict,
    never to Decimal("12.80")."""
    lookalike = {"__decimal__": "12.80"}
    encoded = encode_normalized_value(lookalike)
    decoded = decode_normalized_value(encoded)
    assert decoded == lookalike
    assert isinstance(decoded, dict)


def test_decimal_string_and_lookalike_dict_are_pairwise_distinguishable() -> None:
    """All three of the reviewer's required cases, pairwise: distinguishable
    persistence (encoded) representations AND correct decode identity for
    each."""
    from decimal import Decimal

    lookalike = {"__decimal__": "12.80"}
    values: list[object] = [Decimal("12.80"), "12.80", lookalike]
    encoded = [encode_normalized_value(v) for v in values]

    # Pairwise distinguishable encoded (persistence) representations.
    for i in range(len(encoded)):
        for j in range(len(encoded)):
            if i != j:
                assert encoded[i] != encoded[j]

    decoded = [decode_normalized_value(e) for e in encoded]
    assert decoded[0] == Decimal("12.80") and isinstance(decoded[0], Decimal)
    assert decoded[1] == "12.80" and isinstance(decoded[1], str)
    assert decoded[2] == lookalike and isinstance(decoded[2], dict)


def test_decode_normalized_value_rejects_unwrapped_value() -> None:
    # A bare, never-enveloped value (e.g. legacy/foreign data) must fail
    # closed rather than being silently guessed at.
    import pytest

    with pytest.raises(EncodedValueError):
        decode_normalized_value("12.80")
    with pytest.raises(EncodedValueError):
        decode_normalized_value(10.5)
    with pytest.raises(EncodedValueError):
        decode_normalized_value({"__decimal__": "12.80"})


def test_decode_normalized_value_rejects_unknown_type_tag() -> None:
    import pytest

    with pytest.raises(EncodedValueError):
        decode_normalized_value(
            {ENCODED_VALUE_TYPE_KEY: "float", ENCODED_VALUE_PAYLOAD_KEY: "12.80"}
        )


def test_decode_normalized_value_rejects_decimal_envelope_with_non_string_payload() -> None:
    import pytest

    with pytest.raises(EncodedValueError):
        decode_normalized_value(
            {ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_DECIMAL, ENCODED_VALUE_PAYLOAD_KEY: 12.80}
        )


def test_decimal_and_equal_text_string_round_trip_through_jsonb_shape_distinctly() -> None:
    """End-to-end regression: NormalizedCandidate(value=Decimal("12.80")) and
    NormalizedCandidate(value="12.80") must remain distinguishable after a
    full normalized_to_jsonb -> decode_normalized_value round trip."""
    from decimal import Decimal

    nc_decimal = NormalizedCandidate(
        value=Decimal("12.80"), unit="m", method_id=None, method_version=None
    )
    nc_string = NormalizedCandidate(value="12.80", unit="m", method_id=None, method_version=None)

    encoded_decimal = normalized_to_jsonb(nc_decimal)
    encoded_string = normalized_to_jsonb(nc_string)
    assert encoded_decimal != encoded_string

    assert encoded_decimal is not None
    assert encoded_string is not None
    decoded_decimal = decode_normalized_value(encoded_decimal["value"])
    decoded_string = decode_normalized_value(encoded_string["value"])
    assert decoded_decimal == Decimal("12.80")
    assert isinstance(decoded_decimal, Decimal)
    assert decoded_string == "12.80"
    assert isinstance(decoded_string, str)


def test_normalized_to_jsonb_existing_non_decimal_values_remain_valid() -> None:
    """Existing non-Decimal NormalizedCandidate.value behavior (float, int,
    bool, None, list) remains valid: each round-trips through
    normalized_to_jsonb -> decode_normalized_value to the exact original
    value, unaffected by the Decimal-specific envelope branch."""
    for value in (10.5, 42, True, None, [1, 2, 3], {"nested": "dict"}):
        nc = NormalizedCandidate(value=value, unit="m", method_id=None, method_version=None)
        encoded = normalized_to_jsonb(nc)
        assert encoded is not None
        assert decode_normalized_value(encoded["value"]) == value


# ---------------------------------------------------------------------------
# producer_to_jsonb
# ---------------------------------------------------------------------------


def test_producer_to_jsonb_human() -> None:
    p = ProducerMetadata(
        kind=ProducerKind.HUMAN,
        identifier="alice",
        version=None,
        model=None,
        prompt_or_rule_version=None,
    )
    d = producer_to_jsonb(p)
    assert d["kind"] == "human"
    assert d["identifier"] == "alice"
    assert d["version"] is None


# ---------------------------------------------------------------------------
# context_to_jsonb
# ---------------------------------------------------------------------------


def test_context_to_jsonb() -> None:
    ctx = ResearchContext(research_job_id="JOB-1", activity_id="WAVE-1")
    d = context_to_jsonb(ctx)
    assert d == {"research_job_id": "JOB-1", "activity_id": "WAVE-1"}


# ---------------------------------------------------------------------------
# applicability_to_jsonb / applicability_from_jsonb round-trip
# ---------------------------------------------------------------------------


def test_applicability_roundtrip_unknown_unbounded() -> None:
    app = _make_app(unknown_or_unbounded=True)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.unknown_or_unbounded is True
    assert restored.design_option_hints is None
    assert restored.first_year is None


def test_applicability_roundtrip_year_range() -> None:
    app = _make_app(first_year=1985, last_year=1999, unknown_or_unbounded=False)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.first_year == 1985
    assert restored.last_year == 1999


def test_applicability_roundtrip_design_option_hints() -> None:
    app = _make_app(design_option_hints=("shoal_keel", "fin_keel"), unknown_or_unbounded=False)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.design_option_hints == ("shoal_keel", "fin_keel")


def test_applicability_roundtrip_individual_hull() -> None:
    app = _make_app(individual_hull_or_listing_ref="HULL-123", unknown_or_unbounded=False)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.individual_hull_or_listing_ref == "HULL-123"


def test_applicability_roundtrip_market_region() -> None:
    app = _make_app(market_or_region="US", unknown_or_unbounded=False)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.market_or_region == "US"


def test_applicability_roundtrip_operating_state() -> None:
    app = _make_app(operating_state_hint="boards_deployed", unknown_or_unbounded=False)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.operating_state_hint == "boards_deployed"


def test_applicability_null_means_unknown_not_global() -> None:
    app = _make_app(first_year=None, unknown_or_unbounded=True)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    # null first_year must remain None, not converted to 0 or any default
    assert restored.first_year is None


def test_applicability_roundtrip_named_variant_hint() -> None:
    app = _make_app(named_variant_hint="tall_rig", unknown_or_unbounded=False)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.named_variant_hint == "tall_rig"


def test_applicability_roundtrip_hull_number_bounds() -> None:
    app = _make_app(hull_number_from="0001", hull_number_to="0500", unknown_or_unbounded=False)
    d = applicability_to_jsonb(app)
    restored = applicability_from_jsonb(d)
    assert restored.hull_number_from == "0001"
    assert restored.hull_number_to == "0500"
