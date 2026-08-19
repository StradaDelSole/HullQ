"""ResearchJob runtime representation — SLICE-0007.

Implements the accepted RESEARCH_JOB_SCHEMA.v0.1 contract as a persistence-
agnostic runtime: ResearchTarget, ResearchJobStatus, and ResearchJob with
caller-owned input snapshots and basic contract invariant validation.

Does not implement: workflow engine, automatic status transitions, canonical
BoatDesign writes, or network acquisition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "HullConfigurationHint",
    "ResearchJob",
    "ResearchJobStatus",
    "ResearchTarget",
    "is_review_status",
    "is_terminal_status",
]


class HullConfigurationHint(StrEnum):
    MONOHULL = "monohull"
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    OTHER = "other"
    UNKNOWN = "unknown"


class ResearchJobStatus(StrEnum):
    PENDING = "pending"
    RESEARCHING = "researching"
    NEEDS_REVIEW = "needs_review"
    CONFLICT = "conflict"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ResearchTarget:
    """Minimal research input — exactly manufacturer, model, first_built.

    manufacturer is a raw source/reference label; it does not by itself assert
    a canonical Brand or Organization role (REQ-RESEARCH-001, REQ-ID-012).
    """

    manufacturer: str | None
    model: str
    first_built: int | None

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("ResearchTarget.model must be non-empty")


@dataclass(frozen=True)
class ResearchJob:
    """Operational metadata for a minimal research target.

    Preserves caller-owned input snapshots. Does not leak workflow state into
    canonical identity. Does not fabricate undocumented workflow edges.
    """

    job_id: str
    target: ResearchTarget
    hull_configuration_hint: HullConfigurationHint | None
    status: ResearchJobStatus
    notes: str | None
    requested_count: int
    created_at: str | None
    updated_at: str | None

    def __post_init__(self) -> None:
        if not self.job_id:
            raise ValueError("ResearchJob.job_id must be non-empty")
        if self.requested_count < 0:
            raise ValueError("ResearchJob.requested_count must be non-negative")


def is_terminal_status(status: ResearchJobStatus) -> bool:
    """Return True for statuses that represent a completed/final workflow outcome.

    Per RESEARCH_WORKFLOW.md: complete, needs_review, conflict, blocked are all terminal.
    pending and researching are active (non-terminal).
    """
    return status in {
        ResearchJobStatus.COMPLETE,
        ResearchJobStatus.NEEDS_REVIEW,
        ResearchJobStatus.CONFLICT,
        ResearchJobStatus.BLOCKED,
    }


def is_review_status(status: ResearchJobStatus) -> bool:
    """Return True for statuses that require human or systematic review."""
    return status in {ResearchJobStatus.NEEDS_REVIEW, ResearchJobStatus.CONFLICT}
