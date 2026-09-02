"""Alembic environment — SLICE-0042.

``target_metadata`` is intentionally ``None``: HullQ does not adopt a
SQLAlchemy ORM domain model (see the SLICE-0042 "no ORM architecture
expansion" boundary). SQLAlchemy is present only as the migration-tooling
dependency Alembic itself requires.

No database URL is ever committed. ``alembic.ini`` leaves ``sqlalchemy.url``
blank; the real URL is resolved here from HullQ's existing environment-driven
connection configuration (``hullq.persistence.connection``), preferring
``HULLQ_TEST_DATABASE_URL`` when set, exactly like the rest of the
persistence integration-test suite.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _resolve_database_url() -> str:
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured

    from hullq.persistence.connection import (
        HULLQ_TEST_DATABASE_URL_ENV,
        get_database_url,
    )

    test_url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if test_url:
        return test_url
    return get_database_url()


def _as_sqlalchemy_url(raw_url: str) -> str:
    """Force the psycopg3 SQLAlchemy dialect.

    HullQ's own ``connection.py`` returns plain ``postgresql://`` URLs
    because it talks to psycopg directly and never goes through SQLAlchemy.
    SQLAlchemy's default ``postgresql://`` dialect expects psycopg2, which
    this project does not depend on, so the driver must be pinned explicitly
    for Alembic's engine.
    """
    for prefix in ("postgresql://", "postgres://"):
        if raw_url.startswith(prefix):
            return "postgresql+psycopg://" + raw_url[len(prefix) :]
    return raw_url


def run_migrations_offline() -> None:
    url = _as_sqlalchemy_url(_resolve_database_url())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _as_sqlalchemy_url(_resolve_database_url())
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
