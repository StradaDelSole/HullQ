from pathlib import Path

from hullq.contracts import ContractRegistry
from scripts.validate_repository import no_active_drafts_check, requirements_check

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
