"""Unit tests for hullq.research.jobs — SLICE-0007.

Covers required scenarios 1-3 from SLICE-0007:
1. ResearchTarget contains only manufacturer/model/first-built identity input.
2. ResearchJob status vocabulary matches RESEARCH_JOB_SCHEMA.v0.1.
3. Invalid empty job/model and negative requested count are rejected.
"""

from __future__ import annotations

import pytest

from hullq.research.jobs import (
    HullConfigurationHint,
    ResearchJob,
    ResearchJobStatus,
    ResearchTarget,
    is_review_status,
    is_terminal_status,
)

# ---------------------------------------------------------------------------
# Scenario 1 — ResearchTarget identity fields
# ---------------------------------------------------------------------------


def test_research_target_accepts_all_fields() -> None:
    t = ResearchTarget(manufacturer="Beneteau", model="First 40", first_built=1985)
    assert t.manufacturer == "Beneteau"
    assert t.model == "First 40"
    assert t.first_built == 1985


def test_research_target_accepts_null_manufacturer() -> None:
    t = ResearchTarget(manufacturer=None, model="Contessa 32", first_built=None)
    assert t.manufacturer is None
    assert t.first_built is None


def test_research_target_only_has_expected_fields() -> None:
    """Verify ResearchTarget has exactly manufacturer, model, first_built — no extras."""
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(ResearchTarget)}
    assert field_names == {"manufacturer", "model", "first_built"}


def test_research_target_rejects_empty_model() -> None:
    with pytest.raises(ValueError, match="model must be non-empty"):
        ResearchTarget(manufacturer=None, model="", first_built=None)


# ---------------------------------------------------------------------------
# Scenario 2 — Status vocabulary parity with schema
# ---------------------------------------------------------------------------


def test_research_job_status_vocabulary_matches_schema() -> None:
    expected = {"pending", "researching", "needs_review", "conflict", "complete", "blocked"}
    actual = {s.value for s in ResearchJobStatus}
    assert actual == expected


def test_hull_configuration_hint_vocabulary() -> None:
    expected = {"monohull", "catamaran", "trimaran", "other", "unknown"}
    actual = {h.value for h in HullConfigurationHint}
    assert actual == expected


# ---------------------------------------------------------------------------
# Scenario 3 — Contract invariant validation
# ---------------------------------------------------------------------------


def test_research_job_rejects_empty_job_id() -> None:
    target = ResearchTarget(manufacturer="Beneteau", model="Oceanis 45", first_built=2010)
    with pytest.raises(ValueError, match="job_id must be non-empty"):
        ResearchJob(
            job_id="",
            target=target,
            hull_configuration_hint=None,
            status=ResearchJobStatus.PENDING,
            notes=None,
            requested_count=1,
            created_at=None,
            updated_at=None,
        )


def test_research_job_rejects_negative_requested_count() -> None:
    target = ResearchTarget(manufacturer="Hallberg-Rassy", model="HR 40", first_built=1984)
    with pytest.raises(ValueError, match="requested_count must be non-negative"):
        ResearchJob(
            job_id="JOB-001",
            target=target,
            hull_configuration_hint=HullConfigurationHint.MONOHULL,
            status=ResearchJobStatus.PENDING,
            notes=None,
            requested_count=-1,
            created_at=None,
            updated_at=None,
        )


def test_research_job_accepts_zero_requested_count() -> None:
    target = ResearchTarget(manufacturer=None, model="Etap 28i", first_built=None)
    job = ResearchJob(
        job_id="JOB-002",
        target=target,
        hull_configuration_hint=None,
        status=ResearchJobStatus.PENDING,
        notes=None,
        requested_count=0,
        created_at="2026-08-19",
        updated_at="2026-08-19",
    )
    assert job.requested_count == 0


def test_research_job_valid_construction() -> None:
    target = ResearchTarget(manufacturer="Jeanneau", model="Sun Odyssey 440", first_built=2018)
    job = ResearchJob(
        job_id="JOB-003",
        target=target,
        hull_configuration_hint=HullConfigurationHint.MONOHULL,
        status=ResearchJobStatus.RESEARCHING,
        notes="Test job",
        requested_count=5,
        created_at="2026-08-19",
        updated_at="2026-08-19",
    )
    assert job.job_id == "JOB-003"
    assert job.target.model == "Sun Odyssey 440"
    assert job.status == ResearchJobStatus.RESEARCHING


def test_research_job_is_frozen() -> None:
    target = ResearchTarget(manufacturer="X", model="Y", first_built=None)
    job = ResearchJob(
        job_id="JOB-FROZEN",
        target=target,
        hull_configuration_hint=None,
        status=ResearchJobStatus.PENDING,
        notes=None,
        requested_count=1,
        created_at=None,
        updated_at=None,
    )
    with pytest.raises(AttributeError):
        job.status = ResearchJobStatus.COMPLETE  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Status helper functions
# ---------------------------------------------------------------------------


def test_is_terminal_status_complete() -> None:
    assert is_terminal_status(ResearchJobStatus.COMPLETE) is True


def test_is_terminal_status_blocked() -> None:
    assert is_terminal_status(ResearchJobStatus.BLOCKED) is True


def test_is_terminal_status_needs_review() -> None:
    assert is_terminal_status(ResearchJobStatus.NEEDS_REVIEW) is True


def test_is_terminal_status_conflict() -> None:
    assert is_terminal_status(ResearchJobStatus.CONFLICT) is True


def test_is_terminal_status_non_terminal() -> None:
    for s in (ResearchJobStatus.PENDING, ResearchJobStatus.RESEARCHING):
        assert is_terminal_status(s) is False


def test_is_review_status_needs_review() -> None:
    assert is_review_status(ResearchJobStatus.NEEDS_REVIEW) is True


def test_is_review_status_conflict() -> None:
    assert is_review_status(ResearchJobStatus.CONFLICT) is True


def test_is_review_status_non_review() -> None:
    for s in (
        ResearchJobStatus.PENDING,
        ResearchJobStatus.RESEARCHING,
        ResearchJobStatus.COMPLETE,
        ResearchJobStatus.BLOCKED,
    ):
        assert is_review_status(s) is False
