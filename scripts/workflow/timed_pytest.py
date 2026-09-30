"""Run pytest and print its exact wall-clock duration — SLICE-0073 timing observability.

Thin wrapper around `scripts/run_pytest_local.py`'s own sys.path fix-up, so it
can be invoked the same way through
`scripts/workflow/claude_diag.py run-local-test-db-compact`:

    uv run python scripts/workflow/claude_diag.py run-local-test-db-compact \\
        scripts/workflow/timed_pytest.py -n auto --dist loadgroup

Prints a single machine-readable `TIMED_PYTEST_RUN seconds=<float> returncode=<int>`
line after pytest exits, in addition to pytest's normal output, so a retained
CI/local log carries an exact before/after wall-clock figure without needing
to parse pytest's own duration reporting.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pytest  # noqa: E402 -- must follow the sys.path fix-up above


def main(argv: list[str]) -> int:
    start = time.monotonic()
    returncode = pytest.main(argv)
    elapsed = time.monotonic() - start
    print(f"TIMED_PYTEST_RUN seconds={elapsed:.1f} returncode={int(returncode)}")
    return int(returncode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
