from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BROKER_GATE = ROOT / "docs" / "governance" / "BROKER_WORKSPACE_LAUNCH_GATE.md"
MANDATORY_REGISTER = (
    ROOT / "docs" / "governance" / "BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md"
)
PRODUCTION_GATE = ROOT / "docs" / "governance" / "PRODUCTION_READINESS_GATE.md"
PRODUCT_DIRECTION = ROOT / "docs" / "BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md"
SOURCE_ADDENDUM = ROOT / "docs" / "BROKER_WORKSPACE_ADDENDUM_2026-09-12.md"
BROKER_REQUIREMENTS = ROOT / "specs" / "BROKER_WORKSPACE_REQUIREMENTS.v0.1.md"


def _single_marker(text: str, pattern: str, label: str) -> str:
    matches = re.findall(pattern, text)
    assert len(matches) == 1, f"{label} must appear exactly once"
    return matches[0]


def _requirement_statuses(text: str) -> dict[int, str]:
    statuses: dict[int, str] = {}
    for number in range(22, 31):
        statuses[number] = _single_marker(
            text,
            rf"<!--\s*REQ_BROKER_{number:03d}_STATUS:\s*(PENDING|DUE|IMPLEMENTED)\s*-->",
            f"REQ_BROKER_{number:03d}_STATUS",
        )
    return statuses


def _sale_outcome_status(text: str) -> str:
    return _single_marker(
        text,
        r"<!--\s*BROKER_SALE_OUTCOME_WORKFLOW_STATUS:\s*(PENDING|IMPLEMENTED)\s*-->",
        "BROKER_SALE_OUTCOME_WORKFLOW_STATUS",
    )


def test_broker_workspace_governance_artifacts_exist() -> None:
    assert PRODUCT_DIRECTION.is_file()
    assert SOURCE_ADDENDUM.is_file()
    assert BROKER_REQUIREMENTS.is_file()
    assert BROKER_GATE.is_file()
    assert MANDATORY_REGISTER.is_file()


def test_broker_workspace_launch_gate_blocks_early_activation() -> None:
    broker_text = BROKER_GATE.read_text(encoding="utf-8")
    production_text = PRODUCTION_GATE.read_text(encoding="utf-8")

    gate = _single_marker(
        broker_text,
        r"<!--\s*BROKER_WORKSPACE_LAUNCH_GATE_STATUS:\s*(NOT_READY|IN_PROGRESS|PASS)\s*-->",
        "BROKER_WORKSPACE_LAUNCH_GATE_STATUS",
    )
    self_service = _single_marker(
        broker_text,
        r"<!--\s*BROKER_SELF_SERVICE_PILOT_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->",
        "BROKER_SELF_SERVICE_PILOT_STATUS",
    )
    paid_plan = _single_marker(
        broker_text,
        r"<!--\s*PAID_BROKER_PLAN_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->",
        "PAID_BROKER_PLAN_STATUS",
    )
    public_launch = _single_marker(
        production_text,
        r"<!--\s*PUBLIC_PRODUCTION_LAUNCH_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->",
        "PUBLIC_PRODUCTION_LAUNCH_STATUS",
    )

    activation_active = (
        self_service == "ACTIVE" or paid_plan == "ACTIVE" or public_launch == "ACTIVE"
    )
    assert not activation_active or gate == "PASS", (
        "Broker self-service pilot, paid broker plan or public production launch cannot be "
        "ACTIVE until BROKER_WORKSPACE_LAUNCH_GATE_STATUS is PASS"
    )


def test_broker_workspace_requirements_cover_committed_domains() -> None:
    text = BROKER_REQUIREMENTS.read_text(encoding="utf-8")
    requirement_ids = set(re.findall(r"^### (REQ-BROKER-\d{3})\b", text, re.MULTILINE))

    expected = {f"REQ-BROKER-{number:03d}" for number in range(1, 31)}
    assert requirement_ids == expected

    acceptances = re.findall(r"^\*\*Acceptance:\*\*", text, re.MULTILINE)
    assert len(acceptances) == len(expected)


def test_launch_gate_requires_branding_and_connectivity_recovery() -> None:
    broker_text = BROKER_GATE.read_text(encoding="utf-8")
    register_text = MANDATORY_REGISTER.read_text(encoding="utf-8")
    gate = _single_marker(
        broker_text,
        r"<!--\s*BROKER_WORKSPACE_LAUNCH_GATE_STATUS:\s*(NOT_READY|IN_PROGRESS|PASS)\s*-->",
        "BROKER_WORKSPACE_LAUNCH_GATE_STATUS",
    )
    statuses = _requirement_statuses(register_text)

    if gate == "PASS":
        assert statuses[23] == "IMPLEMENTED"
        assert statuses[24] == "IMPLEMENTED"


def test_scaled_onboarding_requires_bulk_import_and_real_broker_validation() -> None:
    text = MANDATORY_REGISTER.read_text(encoding="utf-8")
    statuses = _requirement_statuses(text)
    scaled = _single_marker(
        text,
        r"<!--\s*SCALED_BROKER_ONBOARDING_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->",
        "SCALED_BROKER_ONBOARDING_STATUS",
    )
    post_pilot = _single_marker(
        text,
        r"<!--\s*POST_PILOT_REAL_BROKER_VALIDATION_STATUS:\s*(NOT_STARTED|IN_PROGRESS|PASS)\s*-->",
        "POST_PILOT_REAL_BROKER_VALIDATION_STATUS",
    )

    if scaled == "ACTIVE":
        assert statuses[27] == "IMPLEMENTED"
        assert post_pilot == "PASS"


def test_paid_or_public_activation_requires_post_pilot_commitments() -> None:
    broker_text = BROKER_GATE.read_text(encoding="utf-8")
    production_text = PRODUCTION_GATE.read_text(encoding="utf-8")
    register_text = MANDATORY_REGISTER.read_text(encoding="utf-8")
    statuses = _requirement_statuses(register_text)

    paid_plan = _single_marker(
        broker_text,
        r"<!--\s*PAID_BROKER_PLAN_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->",
        "PAID_BROKER_PLAN_STATUS",
    )
    public_launch = _single_marker(
        production_text,
        r"<!--\s*PUBLIC_PRODUCTION_LAUNCH_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->",
        "PUBLIC_PRODUCTION_LAUNCH_STATUS",
    )
    post_pilot = _single_marker(
        register_text,
        r"<!--\s*POST_PILOT_REAL_BROKER_VALIDATION_STATUS:\s*(NOT_STARTED|IN_PROGRESS|PASS)\s*-->",
        "POST_PILOT_REAL_BROKER_VALIDATION_STATUS",
    )

    if paid_plan == "ACTIVE" or public_launch == "ACTIVE":
        assert post_pilot == "PASS"
        assert _sale_outcome_status(register_text) == "IMPLEMENTED"
        assert statuses[22] == "IMPLEMENTED"
        assert statuses[26] == "IMPLEMENTED"
        assert statuses[28] == "IMPLEMENTED"


def test_search_volume_trigger_makes_insight_capabilities_due() -> None:
    text = MANDATORY_REGISTER.read_text(encoding="utf-8")
    statuses = _requirement_statuses(text)
    volume = _single_marker(
        text,
        r"<!--\s*SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS:\s*(NOT_REACHED|REACHED)\s*-->",
        "SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS",
    )

    if volume == "REACHED":
        assert statuses[25] in {"DUE", "IMPLEMENTED"}
        assert statuses[29] in {"DUE", "IMPLEMENTED"}


def test_broker_product_cannot_be_declared_complete_with_open_commitments() -> None:
    register_text = MANDATORY_REGISTER.read_text(encoding="utf-8")
    broker_text = BROKER_GATE.read_text(encoding="utf-8")
    statuses = _requirement_statuses(register_text)
    product_completion = _single_marker(
        register_text,
        r"<!--\s*BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS:\s*(OPEN|COMPLETE)\s*-->",
        "BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS",
    )
    commitments = _single_marker(
        register_text,
        r"<!--\s*BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS:\s*(OPEN|COMPLETE)\s*-->",
        "BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS",
    )
    gate = _single_marker(
        broker_text,
        r"<!--\s*BROKER_WORKSPACE_LAUNCH_GATE_STATUS:\s*(NOT_READY|IN_PROGRESS|PASS)\s*-->",
        "BROKER_WORKSPACE_LAUNCH_GATE_STATUS",
    )

    if product_completion == "COMPLETE" or commitments == "COMPLETE":
        assert set(statuses.values()) == {"IMPLEMENTED"}
        assert _sale_outcome_status(register_text) == "IMPLEMENTED"
        assert gate == "PASS"


def test_broker_register_requires_post_slice_reassessment_visibility() -> None:
    text = MANDATORY_REGISTER.read_text(encoding="utf-8")
    assert "Every normal post-slice capability reassessment" in text
    assert "A `DUE` broker commitment may be deferred" in text
    assert "It may not be omitted from consideration" in text
    assert "BROKER_SALE_OUTCOME_WORKFLOW_STATUS" in text


def test_broker_workspace_direction_keeps_core_operating_principles() -> None:
    text = PRODUCT_DIRECTION.read_text(encoding="utf-8")
    assert "A broker should never have to enter information twice" in text
    assert "Lead is a first-class HullQ product object" in text
    assert "Lead attribution is launch-critical" in text
    assert "Broker analytics must answer business questions" in text
    assert "Search explainability is a broker differentiator" in text
    assert "Inventory portability and no lock-in" in text
    assert "Validation order and real-broker evidence" in text
    assert "Deferred does not mean optional" in text
