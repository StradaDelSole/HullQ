"""Run pytest with the fixed local-test PostgreSQL environment already set.

Intended to be invoked only through
`scripts/workflow/claude_diag.py run-local-test-db` (see that module's
docstring): the helper injects `HULLQ_TEST_DATABASE_URL` into this process's
environment before it starts, so this script never reads, constructs or
prints that value itself -- it only forwards its own argv straight to
`pytest.main()`.
"""

from __future__ import annotations

import sys

import pytest

if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:]))
