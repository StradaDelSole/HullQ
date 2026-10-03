# SLICE-0079 production API image — docs/governance/PRODUCTION_READINESS_GATE.md §1.
#
# Multi-stage build: the builder stage resolves the locked production
# dependency set with `uv` (no dev-group tooling -- ruff/mypy/pytest never
# ship in the runtime image); the runtime stage copies only the built
# virtual environment and application source, runs as a non-root user, and
# never needs a build toolchain at container-start time. The resulting
# image is immutable and content-addressed by its GHCR digest/tag
# (`.github/workflows/deploy.yml` tags it with the exact git commit SHA --
# `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §24: "Do not use `latest` as
# production truth").
#
# The application host is stateless with respect to canonical application
# data: this image writes nothing to a local volume, keeps no local
# database/media state, and reads all configuration from the environment
# (`docker-compose.prod.yml` / the VPS `.env` file) at container start.

FROM python:3.14-slim-trixie AS builder

RUN pip install --no-cache-dir "uv==0.12.5"

WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY README.md ./README.md

# `--no-dev`: production dependency group only. `--no-editable`: install the
# built wheel content into the venv rather than an editable source link, so
# the runtime stage's copied venv does not depend on this build stage's
# source tree layout.
RUN uv sync --locked --no-dev --no-editable

FROM python:3.14-slim-trixie AS runtime

RUN groupadd --system hullq && useradd --system --gid hullq --create-home hullq

WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY src ./src

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER hullq

EXPOSE 8000

# Liveness only (never touches the database -- see src/hullq/api/app.py's
# `/healthz` docstring for why): a container orchestrator should restart
# this process if it cannot answer HTTP at all, but a database outage must
# not look like "restart the app container" (that would not fix a database
# outage and would cause a restart loop).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]

# Invoked as `python -m uvicorn` rather than the `uvicorn` console-script
# directly: that script's shebang is written at venv-creation time relative
# to the builder stage's `/build` WORKDIR, which does not exist in this
# runtime stage (the venv directory itself was copied and still works --
# only the hardcoded shebang path in wrapper scripts does not survive the
# copy). `python -m` resolves the interpreter via `$PATH` instead.
CMD ["python", "-m", "uvicorn", "hullq.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
