"""Reproducibility proof for the SLICE-0019 manufacturer research package.

Offline and deterministic: no web/network calls. Executes the full retained
generator chain in-process (build_registry -> finalize_source_yield ->
analyze_overlap -> build_report) against the committed inputs and asserts the
regenerated structured outputs/report are byte-identical to what is committed
in the repository. This is the proof required by the SLICE-0019 independent
review that the generator chain documented in REPORT.md actually reproduces
the retained artifacts, rather than merely having run once by hand.

Also pins the accepted SLICE-0017/0018 AUTO_ADMIT union at exactly 1,770 QIDs
and the bounded exact-only overlap semantics (57 probes, no fuzzy matching),
matching the invariant already enforced inside analyze_overlap.py itself.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

MANUFACTURERS = Path(__file__).resolve().parents[2] / "research" / "manufacturers"


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def manufacturers_path_prefix():
    """These scripts import sibling modules (e.g. ``archive_surface``) by bare
    name, which only resolves when the directory containing them is on
    sys.path (normally guaranteed by running them as ``python script.py``)."""
    inserted = str(MANUFACTURERS) not in sys.path
    if inserted:
        sys.path.insert(0, str(MANUFACTURERS))
    yield
    if inserted:
        sys.path.remove(str(MANUFACTURERS))


ARTIFACTS = [
    MANUFACTURERS / "registry.json",
    MANUFACTURERS / "source_yield_study.json",
    MANUFACTURERS / "overlap_result.json",
    MANUFACTURERS / "REPORT.md",
]


def test_generator_chain_reproduces_committed_artifacts(manufacturers_path_prefix):
    before = {path: path.read_bytes() for path in ARTIFACTS}

    build_registry = _load_module("slice0019_build_registry", MANUFACTURERS / "build_registry.py")
    build_registry.main()

    finalize_source_yield = _load_module(
        "slice0019_finalize_source_yield", MANUFACTURERS / "finalize_source_yield.py"
    )
    finalize_source_yield.main()

    analyze_overlap = _load_module(
        "slice0019_analyze_overlap", MANUFACTURERS / "analyze_overlap.py"
    )
    analyze_overlap.main()

    build_report = _load_module("slice0019_build_report", MANUFACTURERS / "build_report.py")
    build_report.main()

    after = {path: path.read_bytes() for path in ARTIFACTS}

    def normalize_newlines(data: bytes) -> bytes:
        # Python's default text-mode write translates outgoing "\n" to the
        # platform line separator (CRLF on Windows), while a checked-out git
        # blob's line endings depend on the runner's checkout/gitattributes
        # configuration. Normalizing both sides isolates genuine content
        # drift from this incidental, OS-specific text-mode representation.
        return data.replace(b"\r\n", b"\n")

    for path in ARTIFACTS:
        assert normalize_newlines(after[path]) == normalize_newlines(before[path]), (
            f"{path.name} regenerated from the committed generator chain does not match the "
            "committed artifact (content, ignoring line-ending style)"
        )


def test_overlap_union_and_probe_semantics_pinned(manufacturers_path_prefix):
    import json

    result = json.loads((MANUFACTURERS / "overlap_result.json").read_text(encoding="utf-8"))

    assert result["accepted_universe"]["auto_admit_qid_count"] == 1770
    assert result["accepted_universe"]["expected_canonical_boatmodel_count"] == 1770
    assert result["probe_summary"]["probe_model_identity_count"] == 57
    assert "No fuzzy matching" in result["method"]
