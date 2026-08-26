"""Unit tests for deterministic fingerprinting — SLICE-0013 criterion 2."""

from __future__ import annotations

import json

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    JsonPointer,
    ProducerKind,
    ProducerMetadata,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.persistence.fingerprint import (
    _applicability_dict,
    _canonical_json,
    _crosscheck_dict,
    _finding_dict,
    _locator_dict,
    _normalized_dict,
    _producer_dict,
    _raw_dict,
    _sha256,
    _target_dict,
    fingerprint_bundle,
    fingerprint_dict,
    fingerprint_observation,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    NormalizedCandidate,
    ObservationApplicability,
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_applicability(
    *,
    first_year: int | None = None,
    unknown_or_unbounded: bool = True,
    design_option_hints: list[str] | None = None,
    individual_hull_or_listing_ref: str | None = None,
) -> ObservationApplicability:
    return ObservationApplicability(
        first_year=first_year,
        last_year=None,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=tuple(design_option_hints) if design_option_hints else None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=individual_hull_or_listing_ref,
        unknown_or_unbounded=unknown_or_unbounded,
    )


def _make_obs(
    obs_id: str = "OBS-001",
    raw_value: object = "10.5",
    applicability: ObservationApplicability | None = None,
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=obs_id,
        research_target=ResearchTarget(manufacturer="Acme", model="Test 35", first_built=1980),
        source_id="SRC-001",
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.LITERAL, value=raw_value, unit="m", excerpt=None
        ),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=applicability or _make_applicability(),
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="test-tool",
            version="0.1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=SubjectKind.BOAT_DESIGN,
        intended_field_pointer=JsonPointer("/loa_m"),
        notes=None,
    )


def _make_bundle(obs: list[ResearchObservation] | None = None) -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(
        bundle_id="BUNDLE-001",
        bundle_version="1.0",
        research_target=ResearchTarget(manufacturer="Acme", model="Test 35", first_built=1980),
        research_job_id=None,
        activity_id=None,
        observations=tuple(obs or [_make_obs()]),
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# Canonical JSON tests
# ---------------------------------------------------------------------------


def test_canonical_json_sorts_keys() -> None:
    result = _canonical_json({"z": 1, "a": 2})
    assert list(json.loads(result).keys()) == ["a", "z"]


def test_canonical_json_no_whitespace() -> None:
    result = _canonical_json({"a": 1})
    assert " " not in result


def test_canonical_json_none_value() -> None:
    result = _canonical_json({"k": None})
    assert result == '{"k":null}'


def test_canonical_json_nested_sorted() -> None:
    result = _canonical_json({"z": {"b": 2, "a": 1}})
    parsed = json.loads(result)
    assert list(parsed["z"].keys()) == ["a", "b"]


def test_sha256_deterministic() -> None:
    h1 = _sha256("hello")
    h2 = _sha256("hello")
    assert h1 == h2
    assert len(h1) == 64


def test_fingerprint_dict_deterministic() -> None:
    d = {"b": [1, 2], "a": "x"}
    assert fingerprint_dict(d) == fingerprint_dict(d)


def test_fingerprint_dict_key_order_independent() -> None:
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2, "a": 1}
    assert fingerprint_dict(d1) == fingerprint_dict(d2)


def test_fingerprint_dict_changes_with_content() -> None:
    assert fingerprint_dict({"a": 1}) != fingerprint_dict({"a": 2})


# ---------------------------------------------------------------------------
# Helper dict tests
# ---------------------------------------------------------------------------


def test_target_dict_round_trip() -> None:
    t = ResearchTarget(manufacturer="Acme", model="Test 35", first_built=1980)
    d = _target_dict(t)
    assert d["manufacturer"] == "Acme"
    assert d["model"] == "Test 35"
    assert d["first_built"] == 1980


def test_target_dict_null_manufacturer() -> None:
    t = ResearchTarget(manufacturer=None, model="X", first_built=None)
    d = _target_dict(t)
    assert d["manufacturer"] is None
    assert d["first_built"] is None


def test_locator_dict_all_none() -> None:
    loc = SourceLocator(
        page=None, section=None, anchor=None, table=None, figure=None, record_key=None
    )
    d = _locator_dict(loc)
    assert all(v is None for v in d.values())


def test_raw_dict_preserves_kind() -> None:
    raw = RawObservation(kind=RawObservationKind.LITERAL, value="10.5", unit="m", excerpt=None)
    d = _raw_dict(raw)
    assert d["kind"] == "literal"
    assert d["value"] == "10.5"
    assert d["unit"] == "m"


def test_normalized_dict_none() -> None:
    assert _normalized_dict(None) is None


def test_normalized_dict_present() -> None:
    nc = NormalizedCandidate(value=10.5, unit="m", method_id="std", method_version="1.0")
    d = _normalized_dict(nc)
    assert d is not None
    assert d["value"] == 10.5
    assert d["method_id"] == "std"


def test_normalized_dict_decimal_value_wrapped_and_fingerprintable() -> None:
    """SLICE-0026: fingerprint_evidence/fingerprint_observation must not raise
    on a Decimal-valued NormalizedCandidate (every measurement value
    hullq.sources.wikidata produces) — json.dumps has no native Decimal
    support, so _normalized_dict must encode it via the shared
    hullq.persistence.schema.encode_decimal_for_jsonb marker (never a bare
    ``str(value)``, which would collide with a legitimately string-typed
    value of the same text)."""
    from decimal import Decimal

    from hullq.persistence.schema import DECIMAL_JSONB_MARKER_KEY

    nc = NormalizedCandidate(
        value=Decimal("4500"), unit="kg", method_id="std", method_version="1.0"
    )
    d = _normalized_dict(nc)
    assert d is not None
    assert d["value"] == {DECIMAL_JSONB_MARKER_KEY: "4500"}

    # Must not raise — exercises the exact json.dumps call fingerprint_dict makes.
    digest = fingerprint_dict(d)
    assert isinstance(digest, str) and len(digest) == 64
    # Deterministic: identical input always yields the identical digest.
    assert fingerprint_dict(d) == digest


def test_normalized_dict_decimal_and_equal_text_string_produce_different_fingerprints() -> None:
    """Decimal("4500") and the string "4500" are distinct
    NormalizedCandidate.value shapes and MUST NOT produce the same content
    fingerprint — otherwise two semantically different evidence items would
    be treated as identical by the SLICE-0013 importer's fingerprint-based
    identity/conflict checks."""
    from decimal import Decimal

    nc_decimal = NormalizedCandidate(
        value=Decimal("4500"), unit="kg", method_id=None, method_version=None
    )
    nc_string = NormalizedCandidate(value="4500", unit="kg", method_id=None, method_version=None)

    d_decimal = _normalized_dict(nc_decimal)
    d_string = _normalized_dict(nc_string)
    assert d_decimal != d_string
    assert fingerprint_dict(d_decimal) != fingerprint_dict(d_string)


def test_applicability_dict_design_option_hints() -> None:
    app = _make_applicability(design_option_hints=["shoal_keel", "fin_keel"])
    d = _applicability_dict(app)
    assert d["design_option_hints"] == ["shoal_keel", "fin_keel"]


def test_applicability_dict_null_hints() -> None:
    app = _make_applicability()
    d = _applicability_dict(app)
    assert d["design_option_hints"] is None


def test_producer_dict_preserves_kind() -> None:
    p = ProducerMetadata(
        kind=ProducerKind.HUMAN,
        identifier="alice",
        version=None,
        model=None,
        prompt_or_rule_version=None,
    )
    d = _producer_dict(p)
    assert d["kind"] == "human"
    assert d["identifier"] == "alice"


def test_finding_dict_sorted_obs_ids() -> None:
    f = UnresolvedFinding(
        finding_id="F-1",
        topic="test",
        description="desc",
        related_observation_ids=frozenset(["OBS-B", "OBS-A"]),
        severity=UnresolvedFindingSeverity.REVIEW,
    )
    d = _finding_dict(f)
    assert d["related_observation_ids"] == ["OBS-A", "OBS-B"]


def test_crosscheck_dict_preserves_outcome() -> None:
    cc = ReferenceCrosscheck(
        crosscheck_id="CC-1",
        reference_source_id="sailboatdata-reference",
        topic_or_field="/loa_m",
        outcome=ReferenceCheckOutcome.CONFLICT,
        notes=None,
    )
    d = _crosscheck_dict(cc)
    assert d["outcome"] == "conflict"
    assert "evidence_id" not in d


# ---------------------------------------------------------------------------
# Observation fingerprint tests
# ---------------------------------------------------------------------------


def test_fingerprint_observation_deterministic() -> None:
    obs = _make_obs()
    assert fingerprint_observation(obs) == fingerprint_observation(obs)


def test_fingerprint_observation_changes_with_raw_value() -> None:
    obs1 = _make_obs(raw_value="10.5")
    obs2 = _make_obs(raw_value="11.0")
    assert fingerprint_observation(obs1) != fingerprint_observation(obs2)


def test_fingerprint_observation_changes_with_applicability() -> None:
    app1 = _make_applicability(unknown_or_unbounded=True)
    app2 = _make_applicability(unknown_or_unbounded=False)
    obs1 = _make_obs(applicability=app1)
    obs2 = _make_obs(applicability=app2)
    assert fingerprint_observation(obs1) != fingerprint_observation(obs2)


def test_fingerprint_observation_changes_with_id() -> None:
    obs1 = _make_obs(obs_id="OBS-001")
    obs2 = _make_obs(obs_id="OBS-002")
    assert fingerprint_observation(obs1) != fingerprint_observation(obs2)


def test_fingerprint_observation_is_hex_str() -> None:
    h = fingerprint_observation(_make_obs())
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# Bundle fingerprint tests
# ---------------------------------------------------------------------------


def test_fingerprint_bundle_deterministic() -> None:
    bundle = _make_bundle()
    assert fingerprint_bundle(bundle) == fingerprint_bundle(bundle)


def test_fingerprint_bundle_changes_with_observation() -> None:
    b1 = _make_bundle(obs=[_make_obs(raw_value="10.5")])
    b2 = _make_bundle(obs=[_make_obs(raw_value="11.0")])
    assert fingerprint_bundle(b1) != fingerprint_bundle(b2)


def test_fingerprint_bundle_changes_with_bundle_id() -> None:
    b1 = ResearchEvidenceBundle(
        bundle_id="B-001",
        bundle_version="1.0",
        research_target=ResearchTarget(manufacturer=None, model="X", first_built=None),
        research_job_id=None,
        activity_id=None,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )
    b2 = ResearchEvidenceBundle(
        bundle_id="B-002",
        bundle_version="1.0",
        research_target=ResearchTarget(manufacturer=None, model="X", first_built=None),
        research_job_id=None,
        activity_id=None,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )
    assert fingerprint_bundle(b1) != fingerprint_bundle(b2)


def test_fingerprint_bundle_same_version_same_hash() -> None:
    b = _make_bundle()
    h1 = fingerprint_bundle(b)
    h2 = fingerprint_bundle(b)
    assert h1 == h2
