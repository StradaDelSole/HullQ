# Production Deploy / Rollback Runbook — SLICE-0079

**Status:** operational runbook, required output of SLICE-0079.
**Scope:** the application VPS running `docker-compose.prod.yml` (FastAPI `api` + Astro `web` + Caddy edge). Database migration is a separate step — see `PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md`.
**Controlling gate:** `docs/governance/PRODUCTION_READINESS_GATE.md` §1.

## 1. Topology

```text
Cloudflare (public edge, Full (strict) TLS)
  |
  v
application VPS ($DEPLOY_PATH, e.g. /opt/hullq)
  +-- releases/<git-commit-sha>/         — one immutable, versioned release
  |     +-- docker-compose.prod.yml      — this release's own copy
  |     +-- Caddyfile                    — this release's own copy
  |     +-- deploy.sh, rollback.sh       — this release's own copy
  +-- shared/                            — stable, non-versioned runtime state
  |     +-- .env                         — never committed, never per-release
  |     +-- certs/cf-origin*.pem
  +-- state/                             — deploy/rollback state machine
  |     +-- current-release              — SHA of the currently-live release
  |     +-- previous-release             — SHA of the one valid rollback target
  +-- rollback.sh                        — stable entrypoint, refreshed from
  |                                         the current release on every
  |                                         successful deploy (§4)
  +-- Caddy, api, web containers (Compose project `hullq-prod`)
  +-- a separate `uv`-managed checkout of this repository for scripts/ops/*
      (backup/restore/migration/health-monitor — these are not baked into
      the api/web images; see PRODUCTION_BACKUP_RESTORE_RUNBOOK.md and
      PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md)
```

Every release directory is self-contained and immutable: its own
`docker-compose.prod.yml`/`Caddyfile`/`deploy.sh`/`rollback.sh`, all from the
exact same commit. `deploy.sh` derives the image tag it deploys
(`sha-<directory name>`) from its OWN release directory's name — never from
an argument, the working directory, or a separately-mutable checkout — so an
older immutable image can never be paired with newer or drifted
configuration (independent review Finding B). `<tag>` is always
`sha-<full git commit SHA>` — never `latest`
(`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §24). Both images are stateless:
neither writes canonical application data to a local volume. PostgreSQL
(DigitalOcean Managed) and object storage (Cloudflare R2) are both
externalized, so the VPS itself can be rebuilt from scratch using only this
repository, the `.env` file and the two certificate files.

## 2. One-time VPS setup

1. Install Docker Engine + Compose plugin (standard distribution packages).
2. Create the deploy root, e.g. `/opt/hullq`, containing:
   - `shared/.env` (copied from `docs/operations/production.env.example` and filled in — never committed)
   - `shared/certs/cf-origin.pem`, `shared/certs/cf-origin-key.pem` (Cloudflare dashboard → SSL/TLS → Origin Server → Create Certificate; mode must be **Full (strict)**)
   - an empty `releases/` directory — CI populates one subdirectory per deployed commit (§3); never hand-create or hand-edit a release directory
3. `docker login ghcr.io` using a read-only GHCR personal access token (`read:packages` scope only — least privilege).
4. Also set up a separate `uv`-managed checkout for `scripts/ops/*` (§1) — these run directly on the VPS, outside Docker, because they need `pg_dump`/`pg_restore` matching PostgreSQL 18 exactly (`apt-get install postgresql-client-18` from the PGDG apt repository).

`state/` and the stable `$DEPLOY_PATH/rollback.sh` entrypoint do not need to
be created manually — the first successful `deploy.sh` run creates them.

## 3. Normal deploy

Deploy is automated by `.github/workflows/deploy.yml`'s `push_to_ghcr` job (runs on every push to `main`, building and pushing both images tagged `sha-<commit>`). Rolling that build out to the VPS is **manual** via the same workflow's `deploy` job (`workflow_dispatch` with `deploy: true`), gated behind the GitHub `production` Environment (configure required reviewers there before first use).

That `deploy` job does two things over SSH, for the exact commit SHA it is deploying:

1. materializes `$DEPLOY_PATH/releases/<sha>/` on the VPS, containing that commit's own `docker-compose.prod.yml`, `Caddyfile`, `deploy.sh` and `rollback.sh`;
2. runs that release's own `deploy.sh` — **no arguments**; everything it needs (the image tag, the Compose/Caddy configuration) is derived from its own release directory.

`deploy.sh` runs `docker compose up -d` (pinned to its own release's image tag), polls `/healthz` and `/readyz` on `127.0.0.1:8000` for up to 60 seconds, and only on success advances the `state/` release pointers: the release that was current becomes `state/previous-release` (the rollback target) and the new release becomes `state/current-release` (independent review Finding C — state only advances after the deploy it describes has actually succeeded). It also refreshes the stable `$DEPLOY_PATH/rollback.sh` entrypoint from its own copy, so an operator always invokes the same fixed path regardless of which release is currently live.

On health-check failure, `deploy.sh` **automatically** re-runs the previously-current release's own `deploy.sh` (an auto-revert, not a mutation of state) and then exits non-zero — a failed deploy never advances or corrupts `state/current-release`/`state/previous-release`.

## 4. Manual rollback

```bash
/opt/hullq/rollback.sh
```

This stable path always contains whichever release's `rollback.sh` was last refreshed by a successful `deploy.sh` (§3) — the operator never needs to know which release directory is current. It reads `state/previous-release` and re-runs **that exact release's own** `deploy.sh` (image + Compose/Caddy configuration together, never just a tag rewrite) — which, because it succeeds, naturally swaps `current`/`previous` back via the same state machine `deploy.sh` always uses. A second rollback therefore correctly toggles back to the release that was just replaced, rather than requiring unbounded rollback history.

If `state/previous-release` is missing, or names a release directory that no longer has its own `deploy.sh`, `rollback.sh` exits non-zero and leaves `state/current-release` untouched — a failed rollback never silently claims success or corrupts the recorded known-good state.

There is no destructive database migration to reverse here by design — see the migration runbook's expand/migrate/contract discipline, which keeps every deployed image version compatible with both the pre- and post-migration schema for one release window.

## 5. Local proof

`scripts/ops/inspect_deploy_rollback_lifecycle.py` runs the REAL
`scripts/ops/deploy.sh` and `scripts/ops/rollback.sh` (not reimplemented test
doubles) against a temporary directory shaped exactly like the production
layout in §1 (`releases/<sha>/`, `shared/`, `state/`) and the real Docker
Engine. It proves, end to end:

1. a first deploy with no previous release records no rollback target;
2. an upgrade (A → B) leaves A as `state/previous-release` (the rollback target), not B;
3. a manual rollback through the stable `rollback.sh` entrypoint genuinely redeploys A's own image+configuration (verified by inspecting the running container's actual image reference, not just the state file), and correctly swaps `current`/`previous` back;
4. a deliberately-unhealthy deploy auto-reverts to the last good release and reports failure (exit 1), never success, and never advances `state/current-release`;
5. a corrupted rollback target is detected and reported (non-zero exit) without corrupting `state/current-release`;
6. the running container's image reference always matches the tag derived from its own release directory's name — image and deployment configuration can never drift apart (Finding B);
7. all of the above against the real nested release-directory layout, not a flattened stand-in.

Run:

```bash
uv run python scripts/ops/inspect_deploy_rollback_lifecycle.py
```

Requires a working local Docker Engine and the local PostgreSQL 18 test
database.

**Execution status for this amendment**: this sandbox's Docker Desktop
backend is not running in this session (`docker context ls` shows only the
`desktop-linux`/`default` npipe endpoints, and `docker version`/`docker info`
fail with "cannot connect to the Docker API"; the `docker-desktop` WSL
distribution exists but is `Stopped` and is not independently startable
without the Docker Desktop application, which is not present on this
machine). The script was written/reviewed but **could not be executed** in
this session — this is a sandbox limitation, not a claim of a passing or
failing run. **Residual**: the real-Docker execution of this proof, and the
first real GHCR push/VPS deploy via `.github/workflows/deploy.yml`, remain
unobserved and must be run (by a human operator or a session with Docker
available) before this mechanism can be marked verified.

## 6. Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `deploy.sh` reports health-check failure, auto-reverts, exits 1 or 3 | new image fails to start, or `/readyz` fails (DB unreachable); exit 3 means the auto-revert itself also failed | inspect `docker compose logs api` in the failed release's directory; fix the underlying issue before retrying the same release; exit 3 requires immediate manual intervention |
| `rollback.sh` exits 2 | `state/previous-release` is missing, or names a release directory whose `deploy.sh` is gone | manually `docker compose up -d` a known-good release directory under `releases/`, or restore the missing release directory from CI/git history |
| Caddy returns 525/526 | Cloudflare Full (strict) mode cert mismatch/expiry | reissue the Cloudflare Origin CA certificate, replace `shared/certs/cf-origin*.pem`, `docker compose restart caddy` |
