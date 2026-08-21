"""Regression guard for the two pre-existing syntax defects fixed during SLICE-0017.

``src/hullq/sources/wikidata.py`` and ``src/hullq/domain/provenance.py`` each
contained an invalid Python-2-style ``except A, B:`` clause (missing the
required parentheses around the exception tuple) that made the module
unimportable. Both were corrected to ``except (A, B):`` and marked
``# fmt: skip`` because the exact pinned ``ruff==0.16.3`` formatter has a
reproducible bug that strips the parentheses back off a bare
``except (A, B):`` clause (no ``as`` binding), reintroducing the syntax
error — see the SLICE-0017 slice document "Pre-existing defects discovered
and fixed" section.

This is deliberately the smallest possible guard: it does not depend on
ruff, does not invoke the formatter, and does not test unrelated tooling. It
proves two independent things that must both remain true:

1. both modules remain syntactically valid Python (``ast.parse``) and
   therefore importable;
2. the specific corrected lines still carry the required parentheses, so a
   future accidental ``ruff format`` (write mode) reintroducing the known
   formatter bug is caught here rather than silently breaking the build.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_GUARDED_FILES = (
    ROOT / "src" / "hullq" / "sources" / "wikidata.py",
    ROOT / "src" / "hullq" / "domain" / "provenance.py",
)

# A bare multi-exception `except` clause without the required parentheses,
# e.g. `except ValueError, InvalidOperation:` — the exact invalid pattern
# this guard exists to catch, matched without requiring the parenthesized
# form (which is what must NOT match here).
_BROKEN_EXCEPT_RE = re.compile(r"except\s+\w+(\.\w+)*\s*,\s*\w+(\.\w+)*\s*:")


def test_guarded_modules_remain_syntactically_valid_python() -> None:
    for path in _GUARDED_FILES:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))  # raises SyntaxError if broken


def test_guarded_modules_contain_no_unparenthesized_multi_except() -> None:
    for path in _GUARDED_FILES:
        source = path.read_text(encoding="utf-8")
        match = _BROKEN_EXCEPT_RE.search(source)
        if match is not None:
            raise AssertionError(
                f"{path} contains an unparenthesized multi-exception except clause "
                f"({match.group(0)!r}); this is invalid Python 3 syntax and was the "
                "exact class of pre-existing defect fixed for SLICE-0017."
            )


def test_guarded_modules_are_actually_importable() -> None:
    import hullq.domain.provenance
    import hullq.sources.wikidata  # noqa: F401
