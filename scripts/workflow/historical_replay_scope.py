"""Decide whether the SLICE-0073 historical-research-replay CI job needs to
actually replay anything for the current change, or can report a fast clean
pass.

The historical Wikidata bootstrap/replay steps (SLICE-0017/0018/0021/0022/
0026/0027/0028/0030/0031/0032) reproduce already-closed, frozen research
evidence against PostgreSQL. An ordinary product PR that never touches the
bootstrap/identity-import code path or the retained research artifacts
cannot change that reproduction's outcome, so re-running it on every such PR
buys no incremental verification -- only wall-clock.

This module implements the every-PR / change-triggered boundary required by
specs/TEST_CI_THROUGHPUT_OPTIMIZATION.v0.1.md section 5.6: the job itself
always runs (so it never becomes a permanently-pending required check per
docs/engineering/CI_BASELINE.md), but only pays the real replay cost when a
path in RELEVANT_PATH_PREFIXES changed, or on schedule/workflow_dispatch/push
to main, or whenever the changed-file set cannot be determined (fail toward
running the replay, never toward silently skipping it).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Anything under these prefixes can plausibly change the historical replay's
# deterministic outcome: the retained manifests/evidence themselves, the
# bootstrap/import code that consumes them, the shared migration/SQL schema,
# the replay tests, and the locked dependency set.
RELEVANT_PATH_PREFIXES: tuple[str, ...] = (
    "research/bootstrap/",
    "scripts/bootstrap/",
    "src/hullq/bootstrap/",
    "src/hullq/persistence/identity_importer.py",
    "src/hullq/persistence/identity_readback.py",
    "src/hullq/persistence/identity_types.py",
    "src/hullq/persistence/importer.py",
    "src/hullq/persistence/migrations.py",
    "src/hullq/persistence/sql/",
    "tests/persistence/test_wikidata_",
    "tests/persistence/conftest.py",
    "tests/persistence/_field_resolution_support.py",
    "uv.lock",
    "pyproject.toml",
)

# Events where the job must always pay the full replay cost regardless of
# the changed-file set: scheduled drift detection, manual dispatch, and
# post-merge push to main (the last accepted-state gate before main moves).
ALWAYS_RELEVANT_EVENTS: frozenset[str] = frozenset({"schedule", "workflow_dispatch", "push"})

_MISSING_SHA_MARKERS = frozenset({"", "0000000000000000000000000000000000000000"})


def _changed_files(repo: Path, base: str, head: str) -> list[str] | None:
    """Return changed paths between *base* and *head*, or None if undeterminable."""
    if base in _MISSING_SHA_MARKERS or head in _MISSING_SHA_MARKERS:
        return None
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_relevant_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in RELEVANT_PATH_PREFIXES)


def decide_in(*, repo: Path, event: str, base: str, head: str) -> tuple[bool, str]:
    """Return (relevant, reason) for the given CI event/SHA pair, diffing *repo*."""
    if event in ALWAYS_RELEVANT_EVENTS:
        return True, f"event {event!r} always pays the full historical-replay cost"

    changed = _changed_files(repo, base, head)
    if changed is None:
        return True, "changed-file set undeterminable; failing toward running the replay"

    hits = [path for path in changed if is_relevant_path(path)]
    if hits:
        return True, f"relevant path(s) changed: {', '.join(hits[:5])}"
    return False, "no relevant path changed"


def decide(*, event: str, base: str, head: str) -> tuple[bool, str]:
    """Return (relevant, reason) for the given CI event/SHA pair in this repo checkout."""
    return decide_in(repo=ROOT, event=event, base=base, head=head)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--base", default="")
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)

    relevant, reason = decide(event=args.event, base=args.base, head=args.head)
    print(f"relevant={'true' if relevant else 'false'}")
    print(f"reason={reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
