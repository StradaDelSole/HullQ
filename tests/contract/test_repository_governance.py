from pathlib import Path

from scripts.validate_repository import active_schemas, no_active_drafts_check, requirements_check

ROOT = Path(__file__).resolve().parents[2]


def test_active_json_schemas_are_valid() -> None:
    assert active_schemas()


def test_every_requirement_has_one_acceptance_criterion() -> None:
    requirements, acceptances = requirements_check()
    assert requirements == acceptances
    assert requirements > 0


def test_active_specs_contain_no_draft_files() -> None:
    no_active_drafts_check()


def test_core_docs_exist() -> None:
    required = [
        "PROJECT_CONTEXT.md",
        "CLAUDE.md",
        "docs/EXECUTION_PLAN.md",
        "docs/PROJECT_STATE.md",
        "docs/governance/OPEN_QUESTIONS.md",
        "specs/REQUIREMENTS.md",
        "specs/TEST_STRATEGY.md",
    ]
    assert all((ROOT / path).is_file() for path in required)
