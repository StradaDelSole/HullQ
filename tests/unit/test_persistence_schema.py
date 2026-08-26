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
    applicability_from_jsonb,
    applicability_to_jsonb,
    context_to_jsonb,
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
    assert d["value"] == 10.5
    assert d["method_id"] == "std"


def test_normalized_to_jsonb_decimal_value_stringified() -> None:
    """SLICE-0026: every measurement value hullq.sources.wikidata produces via
    hullq.domain.measurements.normalize_measurement is a Decimal.
    NormalizedCandidate.value is untyped (``object``), but json.dumps (used
    by psycopg's Jsonb wrapper for JSONB storage) has no native Decimal
    support — normalized_to_jsonb must stringify it losslessly rather than
    raise ``TypeError: Object of type Decimal is not JSON serializable``.
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
    assert d["value"] == "12.80"
    assert isinstance(d["value"], str)

    import json

    # Must not raise — this is exactly the shape passed to psycopg's Jsonb().
    json.dumps(d)


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
