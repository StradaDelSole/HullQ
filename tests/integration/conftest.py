"""Conftest for opt-in live network integration tests — SLICE-0008."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live network integration tests against real Wikidata endpoints",
    )
