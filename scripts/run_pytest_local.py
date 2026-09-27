"""Thin pytest entry point for `scripts/workflow/claude_diag.py run-local-test-db`.

That helper injects `HULLQ_TEST_DATABASE_URL` (and only that) into a child
process running one `scripts/*.py` file; it does not know how to invoke
`pytest` as a module directly. This script exists solely to be that
`scripts/*.py` file, forwarding every argument straight to `pytest.main`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `python -m pytest` adds the current working directory to `sys.path`
# automatically; plain `python scripts/run_pytest_local.py` does not (it adds
# only this script's own directory). Repository test modules that do
# `from scripts.xxx import ...` need the repo root itself on `sys.path`.
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pytest  # noqa: E402 -- must follow the sys.path fix-up above

if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:]))
