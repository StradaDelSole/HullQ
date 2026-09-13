from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BROKER_GATE = ROOT / "docs" / "governance" / "BROKER_WORKSPACE_LAUNCH_GATE.md"
PRODUCTION_GATE = ROOT / "docs" / "governance" / "PRODUCTION_READINESS_GATE.md"
PRODUCT_DIRECTION = ROOT / "docs" / "BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md"
BROKER_REQUIREMENTS = ROOT / "specs" / "BROKER_WORKSPACE_REQUIREMENTS.v0.1.md"


def _single_marker(text: str, pattern: str, label: str) -> str:
    matches = re.findall(pattern, text)
    assert len(matches) == 1, f"{label} must appear exactly once"
    return matches[0]


def test_broker_workspace_governance_artifacts_exist() -> None:
    assert PRODUCT_DIRECTION.is_file()
    assert BROKER_REQUIREMENTS.is_file()
    assert BROKER_GATE.is_file()


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


def test_broker_workspace_requirements_cover_launch_critical_domains() -> None:
    text = BROKER_REQUIREMENTS.read_text(encoding="utf-8")
    requirement_ids = set(re.findall(r"^### (REQ-BROKER-\d{3})\b", text, re.MULTILINE))

    expected = {f"REQ-BROKER-{number:03d}" for number in range(1, 22)}
    assert requirement_ids == expected

    acceptances = re.findall(r"^\*\*Acceptance:\*\*", text, re.MULTILINE)
    assert len(acceptances) == len(expected)


def test_broker_workspace_direction_keeps_core_operating_principle() -> None:
    text = PRODUCT_DIRECTION.read_text(encoding="utf-8")
    assert "A broker should never have to enter information twice" in text
    assert "Lead is a first-class HullQ product object" in text
    assert "Lead attribution is launch-critical" in text
    assert "Broker analytics must answer business questions" in text
    assert "Hard launch position" in text
