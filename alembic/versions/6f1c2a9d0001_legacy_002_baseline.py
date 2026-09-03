"""legacy_002_baseline

Revision ID: 6f1c2a9d0001
Revises:
Create Date: 2026-09-02

SLICE-0042 transition marker. Represents the accepted legacy schema state
after the historical lightweight SQL migration runner
(``hullq.persistence.migrations``) has applied both
``001_initial_schema`` (SLICE-0013) and ``002_canonical_identity_schema``
(SLICE-0016).

This revision intentionally applies NO DDL. Replaying the already-applied
historical schema through Alembic would duplicate the single accepted
schema definition across two migration mechanisms, which the SLICE-0042
locked semantic boundary forbids ("must not replay/destructively rewrite
that accepted schema"). It exists only so every future schema migration has
a well-defined Alembic parent to depend on.

Databases reach this revision only via
``hullq.persistence.alembic_baseline.prepare_alembic_baseline``, which
either bootstraps 001/002 through the legacy runner (genuinely empty
database) or verifies their prior application (existing accepted legacy
database) before stamping — never by running ``alembic upgrade`` from an
empty database.
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "6f1c2a9d0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """No-op — see module docstring."""


def downgrade() -> None:
    """No-op — see module docstring."""
