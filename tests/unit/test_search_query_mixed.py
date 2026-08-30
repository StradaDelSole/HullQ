"""Unit tests for hullq.search.query_mixed — SLICE-0035.

Covers:
- MixedAndQuery requires at least one criterion and rejects non-leaf entries
- v0.2 serialization round-trips mixed numeric + categorical criteria without
  semantic drift
- v0.1 payloads remain readable with identical meaning (delegated parsing;
  acceptance criterion "Existing serialized query v0.1 remains readable with
  identical semantics")
- v0.2 fails closed on unknown top-level/criterion keys, unsupported/missing
  "kind", unsupported schema_version/type (adversarial checklist Q7: "Can
  query v0.2 accept unknown semantic keys or criterion kinds and silently
  discard them?")
- adversarial checklist Q10: existing numeric v0.1 truth/serialization is
  unaffected by the v0.2 extension
"""

from __future__ import annotations

import pytest

from hullq.search.criteria import CategoricalLeafCriterion, NumericLeafCriterion
from hullq.search.query import AndQuery, query_from_json_dict, query_to_json_dict
from hullq.search.query_mixed import (
    MixedAndQuery,
    mixed_query_from_json_dict,
    mixed_query_to_json_dict,
)
from hullq.search.types import NumericComparisonKind

# ---------------------------------------------------------------------------
# MixedAndQuery construction
# ---------------------------------------------------------------------------


def test_mixed_and_query_requires_at_least_one_criterion() -> None:
    with pytest.raises(ValueError, match="at least one criterion"):
        MixedAndQuery(criteria=())


def test_mixed_and_query_rejects_non_leaf_entries() -> None:
    with pytest.raises(ValueError, match="NumericLeafCriterion or CategoricalLeafCriterion"):
        MixedAndQuery(criteria=("not-a-criterion",))  # type: ignore[arg-type]


def _mixed_query() -> MixedAndQuery:
    return MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="draft_max_m", comparison=NumericComparisonKind.MAXIMUM, threshold_max=1.8
            ),
            CategoricalLeafCriterion(field="rig.masthead_fractional", equals="masthead"),
        )
    )


# ---------------------------------------------------------------------------
# v0.2 round-trip
# ---------------------------------------------------------------------------


def test_mixed_query_v2_round_trip_without_semantic_drift() -> None:
    original = _mixed_query()
    data = mixed_query_to_json_dict(original)
    assert data["schema_version"] == "0.2"
    restored = mixed_query_from_json_dict(data)
    assert restored == original
    assert mixed_query_to_json_dict(restored) == data


def test_mixed_query_v2_serializes_kind_discriminator() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    kinds = {c["kind"] for c in data["criteria"]}
    assert kinds == {"NUMERIC", "CATEGORICAL"}


def test_mixed_query_all_numeric_still_serializes_as_v2() -> None:
    # A MixedAndQuery is never silently downgraded to v0.1, even when every
    # leaf happens to be numeric.
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field="loa_m", comparison=NumericComparisonKind.MINIMUM, threshold_min=10.0
            ),
        )
    )
    data = mixed_query_to_json_dict(query)
    assert data["schema_version"] == "0.2"


# ---------------------------------------------------------------------------
# v0.1 payloads remain readable with identical meaning
# ---------------------------------------------------------------------------


def _v1_numeric_query() -> AndQuery:
    return AndQuery(
        criteria=(
            NumericLeafCriterion(
                field="loa_m",
                comparison=NumericComparisonKind.RANGE,
                threshold_min=8.0,
                threshold_max=11.0,
            ),
        )
    )


def test_mixed_query_reads_v1_payload_with_identical_criteria() -> None:
    v1_query = _v1_numeric_query()
    v1_data = query_to_json_dict(v1_query)
    mixed = mixed_query_from_json_dict(v1_data)
    assert mixed.criteria == v1_query.criteria


def test_mixed_query_reads_v1_payload_via_same_underlying_parser() -> None:
    # Delegation guarantee: a v0.1 payload that query_from_json_dict rejects
    # must also be rejected identically through the mixed-query entry point.
    v1_data = query_to_json_dict(_v1_numeric_query())
    v1_data["criteria"][0]["unit"] = "ft"
    with pytest.raises(ValueError, match="Unknown numeric leaf criterion field"):
        query_from_json_dict(v1_data)
    with pytest.raises(ValueError, match="Unknown numeric leaf criterion field"):
        mixed_query_from_json_dict(v1_data)


# ---------------------------------------------------------------------------
# Fail-closed v0.2 deserialization
# ---------------------------------------------------------------------------


def test_mixed_query_rejects_unsupported_schema_version() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["schema_version"] = "9.9"
    with pytest.raises(ValueError, match="schema_version"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_unsupported_type() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["type"] = "OR"
    with pytest.raises(ValueError, match="type"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_empty_criteria() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"] = []
    with pytest.raises(ValueError, match="non-empty"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_unknown_top_level_key() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["extra_field"] = "unexpected"
    with pytest.raises(ValueError, match="Unknown top-level query field"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_missing_kind() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    del data["criteria"][0]["kind"]
    with pytest.raises(ValueError, match="leaf criterion kind"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_unrecognized_kind() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][0]["kind"] = "BOOLEAN"
    with pytest.raises(ValueError, match="leaf criterion kind"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_unknown_numeric_criterion_key() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][0]["unit"] = "ft"
    with pytest.raises(ValueError, match="Unknown numeric leaf criterion field"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_unknown_categorical_criterion_key() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][1]["synonym_of"] = "fractional"
    with pytest.raises(ValueError, match="Unknown categorical leaf criterion field"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_non_object_criterion_entry() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][0] = "not-a-criterion-object"
    with pytest.raises(ValueError, match="must be a JSON object"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_non_object_top_level_payload() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        mixed_query_from_json_dict(["not", "an", "object"])  # type: ignore[arg-type]


def test_mixed_query_rejects_non_string_categorical_equals() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][1]["equals"] = 42
    with pytest.raises(ValueError, match="equals must be a string"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_numeric_criterion_missing_key() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    del data["criteria"][0]["threshold_min"]
    with pytest.raises(ValueError, match="Malformed numeric leaf criterion"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_numeric_criterion_non_string_field() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][0]["field"] = 123
    with pytest.raises(ValueError, match="field must be a string"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_numeric_criterion_non_finite_threshold_min() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][0]["threshold_min"] = float("nan")
    with pytest.raises(ValueError, match="threshold_min must be a finite"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_numeric_criterion_non_finite_threshold_max() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][0]["threshold_max"] = float("inf")
    with pytest.raises(ValueError, match="threshold_max must be a finite"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_categorical_criterion_missing_key() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    del data["criteria"][1]["equals"]
    with pytest.raises(ValueError, match="Malformed categorical leaf criterion"):
        mixed_query_from_json_dict(data)


def test_mixed_query_rejects_categorical_criterion_non_string_field() -> None:
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"][1]["field"] = 123
    with pytest.raises(ValueError, match="field must be a string"):
        mixed_query_from_json_dict(data)


def test_mixed_query_categorical_kind_silently_discarding_is_not_possible() -> None:
    # Adversarial checklist Q7 direct example: a "kind" that isn't in the
    # accepted set must never fall through to a default numeric/categorical
    # interpretation.
    data = mixed_query_to_json_dict(_mixed_query())
    data["criteria"].append(
        {"kind": "RANGE_FUZZY", "field": "draft_max_m", "equals": "1.5", "strength": "MUST"}
    )
    with pytest.raises(ValueError, match="leaf criterion kind"):
        mixed_query_from_json_dict(data)
