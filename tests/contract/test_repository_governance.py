from pathlib import Path

from hullq.contracts import ContractRegistry
from scripts.validate_repository import (
    no_active_drafts_check,
    requirements_check,
    trigger_gate_state_check,
)

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"


def test_active_json_schemas_are_valid() -> None:
    registry = ContractRegistry.from_directory(SPECS)
    assert registry.schema_names


def test_every_requirement_has_one_acceptance_criterion() -> None:
    requirements, acceptances = requirements_check()
    assert requirements == acceptances
    assert requirements > 0


def test_active_specs_contain_no_draft_files() -> None:
    no_active_drafts_check()


def test_post_0051_trigger_gate_state_is_valid() -> None:
    architecture, criteria_count, workflow, production = trigger_gate_state_check()
    assert architecture == "PASS"
    assert criteria_count >= 1
    assert workflow in {"NOT_DUE", "PASS"}
    assert production in {"NOT_TRIGGERED", "IN_PROGRESS", "PASS"}


def test_current_architecture_artifacts_are_reconciled() -> None:
    system = (ROOT / "architecture/SYSTEM_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "DigitalOcean Managed PostgreSQL 18" in system
    assert "Auth0 Public Cloud" in system
    assert "GHCR" in system
    assert "docs/governance/POST_0051_TRIGGER_GATES.md" in system
    assert "docs/governance/PRODUCTION_READINESS_GATE.md" in system

    ux = (ROOT / "docs/PRODUCT_UX_PRINCIPLES.md").read_text(encoding="utf-8")
    assert "**Status:** ACCEPTED PRODUCT UX BASELINE" in ux
    assert "PROPOSED PRODUCT UX BASELINE" not in ux

    search_seo = (ROOT / "architecture/SEARCH_AND_SEO_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Astro is the accepted main public-web framework" in search_seo
    assert "Before public frontend implementation, OQ-018 MUST define" not in search_seo
    assert "Framework choice remains OQ-008" not in search_seo
    assert "bounded public `noindex`" in search_seo

    adr = (ROOT / "architecture/decisions/ADR-0010-vps-first-application-stack.md").read_text(
        encoding="utf-8"
    )
    stack = (ROOT / "docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md").read_text(
        encoding="utf-8"
    )
    assert "PARTIALLY SUPERSEDED BY 2026-09-02 REBASELINE" in adr
    assert "PARTIALLY SUPERSEDED BY 2026-09-02 REBASELINE" in stack


def test_core_docs_exist() -> None:
    required = [
        "PROJECT_CONTEXT.md",
        "CLAUDE.md",
        "docs/EXECUTION_PLAN.md",
        "docs/PROJECT_STATE.md",
        "docs/governance/OPEN_QUESTIONS.md",
        "docs/governance/POST_0051_TRIGGER_GATES.md",
        "docs/governance/PRODUCTION_READINESS_GATE.md",
        "specs/REQUIREMENTS.md",
        "specs/TEST_STRATEGY.md",
    ]
    assert all((ROOT / path).is_file() for path in required)
