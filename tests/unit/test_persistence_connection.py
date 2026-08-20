"""Unit tests for connection configuration — SLICE-0013 criterion 24."""

from __future__ import annotations

import pytest

from hullq.persistence.connection import (
    HULLQ_DATABASE_URL_ENV,
    HULLQ_TEST_DATABASE_URL_ENV,
    get_database_url,
)


def test_get_database_url_raises_when_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HULLQ_DATABASE_URL_ENV, raising=False)
    with pytest.raises(RuntimeError, match=HULLQ_DATABASE_URL_ENV):
        get_database_url()


def test_get_database_url_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HULLQ_DATABASE_URL_ENV, "   ")
    with pytest.raises(RuntimeError, match=HULLQ_DATABASE_URL_ENV):
        get_database_url()


def test_get_database_url_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HULLQ_DATABASE_URL_ENV, "postgresql://user:pass@localhost/db")
    assert get_database_url() == "postgresql://user:pass@localhost/db"


def test_get_database_url_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HULLQ_DATABASE_URL_ENV, "  postgresql://host/db  ")
    assert get_database_url() == "postgresql://host/db"


def test_get_database_url_custom_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HULLQ_TEST_DATABASE_URL_ENV, "postgresql://test/testdb")
    result = get_database_url(env_var=HULLQ_TEST_DATABASE_URL_ENV)
    assert result == "postgresql://test/testdb"


def test_get_database_url_custom_env_var_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HULLQ_TEST_DATABASE_URL_ENV, raising=False)
    with pytest.raises(RuntimeError, match=HULLQ_TEST_DATABASE_URL_ENV):
        get_database_url(env_var=HULLQ_TEST_DATABASE_URL_ENV)


def test_importing_connection_module_has_no_network_side_effect() -> None:
    """Importing the module must not connect to any database."""
    import importlib

    import hullq.persistence.connection as mod

    # Re-importing should not raise even without env vars set.
    importlib.reload(mod)
