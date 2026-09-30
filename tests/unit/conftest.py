"""Conftest for tests/unit — SLICE-0073 safe-parallel-execution note.

Almost every test here is a pure/offline unit test with no shared mutable
state, so it is safe to schedule on any pytest-xdist worker concurrently
with any other test.

A small number of "reproduces real committed retained package" regression
tests are a deliberate exception: they exercise a runner script's
`run_assemble()` (or equivalent) entry point against the actual
git-committed retained-package directory on disk (not `tmp_path`), to prove
the assembled bytes are stable -- see e.g.
`test_wikimedia_sl0024_independent_verification_runner.py`'s module
docstring. Any other test that *reads* files from that same real directory
(in the same file or a different one) races with that in-place rewrite if
pytest-xdist schedules them onto different workers at the same time --
observed directly as a flaky digest-mismatch failure on the real GitHub
Actions run for this slice (recomputed digest equal to the SHA-256 of an
empty file, i.e. the reader caught the writer's file mid-rewrite).

`_XDIST_SHARED_REAL_PACKAGE_DIR_MODULES` names exactly the modules that touch
one of these real, shared, on-disk retained-package directories (SLICE-0019
manufacturers/, SLICE-0020 archive_clearance/, SLICE-0024
sl0024-independent-verification/, SLICE-0025
sl0025-breadth-enrichment-entry/). Every test in all of them is pinned to one
single shared `xdist_group` so none of them can ever run concurrently with
any other -- a single group rather than one per directory, since a single
observed flake on a two-group local run left the narrower per-directory
split unable to fully rule out an xdist/group-boundary scheduling edge case;
one shared group removes that residual risk entirely at a negligible
parallelism cost (a few hundred tests out of many thousands). Every other
unit test remains fully parallel.
"""

from __future__ import annotations

import pytest

_XDIST_SHARED_REAL_PACKAGE_DIR_GROUP = "hullq-unit-shared-real-package-dirs"
_XDIST_SHARED_REAL_PACKAGE_DIR_MODULES = frozenset(
    {
        "test_slice_0019_manufacturer_registry_reproducibility.py",
        "test_wikidata_sl0029_boatdesign_applicability_pilot.py",
        "test_slice_0020_archive_clearance.py",
        "test_wikimedia_sl0024_independent_verification_runner.py",
        "test_sl0025_breadth_enrichment_entry_decision.py",
        "test_sl0025_breadth_enrichment_entry_decision_runner.py",
    }
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if "/tests/unit/" not in str(item.fspath).replace("\\", "/"):
            continue
        if item.fspath.basename in _XDIST_SHARED_REAL_PACKAGE_DIR_MODULES:
            item.add_marker(pytest.mark.xdist_group(name=_XDIST_SHARED_REAL_PACKAGE_DIR_GROUP))
