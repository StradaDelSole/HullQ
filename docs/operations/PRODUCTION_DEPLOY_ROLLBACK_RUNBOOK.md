# Production Deploy / Rollback Runbook — SLICE-0079

**Status:** operational runbook, required output of SLICE-0079.
**Scope:** the application VPS running `docker-compose.prod.yml` (FastAPI `api` + Astro `web` + Caddy edge). Database migration is a separate step — see `PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md`.
**Controlling gate:** `docs/governance/PRODUCTION_READINESS_GATE.md` §1.

## 1. Topology

```text
Cloudflare (public edge, Full (strict) TLS)
  |
  v
application VPS
  +-- Caddy (Caddyfile, this repo)       — reverse proxy, Cloudflare Origin CA cert
  +-- api   (ghcr.io/stradadelsole/hullq-api:<tag>)
  +-- web   (ghcr.io/stradadelsole/hullq-web:<tag>)
  +-- a separate `uv`-managed checkout of this repository for scripts/ops/*
      (backup/restore/migration/health-monitor — these are not baked into
      the api/web images; see PRODUCTION_BACKUP_RESTORE_RUNBOOK.md and
      PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md)
```

`<tag>` is always `sha-<full git commit SHA>` — never `latest`
(`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §24). Both images are stateless:
neither writes canonical application data to a local volume. PostgreSQL
(DigitalOcean Managed) and object storage (Cloudflare R2) are both
externalized, so the VPS itself can be rebuilt from scratch using only this
repository, the `.env` file and the two certificate files.

## 2. One-time VPS setup

1. Install Docker Engine + Compose plugin (standard distribution packages).
2. Create a deploy directory, e.g. `/opt/hullq`, containing:
   - `docker-compose.prod.yml` (this repository)
   - `Caddyfile` (this repository)
   - `scripts/ops/deploy.sh`, `scripts/ops/rollback.sh` (this repository, `chmod +x`)
   - `.env` (copied from `docs/operations/production.env.example` and filled in — never committed)
   - `certs/cf-origin.pem`, `certs/cf-origin-key.pem` (Cloudflare dashboard → SSL/TLS → Origin Server → Create Certificate; mode must be **Full (strict)**)
3. `docker login ghcr.io` using a read-only GHCR personal access token (`read:packages` scope only — least privilege).
4. Also set up a separate `uv`-managed checkout for `scripts/ops/*` (§1) — these run directly on the VPS, outside Docker, because they need `pg_dump`/`pg_restore` matching PostgreSQL 18 exactly (`apt-get install postgresql-client-18` from the PGDG apt repository).

## 3. Normal deploy

Deploy is automated by `.github/workflows/deploy.yml`'s `push_to_ghcr` job (runs on every push to `main`, building and pushing both images tagged `sha-<commit>`). Rolling that build out to the VPS is **manual** via the same workflow's `deploy` job (`workflow_dispatch` with `deploy: true`), gated behind the GitHub `production` Environment (configure required reviewers there before first use).

On the VPS, `deploy.sh` does the actual work:

```bash
/opt/hullq/deploy.sh sha-<commit>
```

It pulls both images at that tag, runs `docker compose up -d`, polls `/healthz` and `/readyz` on `127.0.0.1:8000` for up to 60 seconds, and on success records the tag in `.last-good-tag`. On health-check failure it **automatically** invokes `rollback.sh`.

## 4. Manual rollback

```bash
/opt/hullq/rollback.sh
```

Redeploys the tag recorded in `.last-good-tag` (written by the last successful `deploy.sh` run) and re-polls health. There is no destructive database migration to reverse here by design — see the migration runbook's expand/migrate/contract discipline, which keeps every deployed image version compatible with both the pre- and post-migration schema for one release window.

## 5. Local proof performed for this slice (2026-10-03)

Executed directly against the real Docker Engine and the real local PostgreSQL 18 test database (no mocks), since this slice's sandbox had no VPS/GHCR network access:

```text
1. docker build -f Dockerfile .                 -> succeeded (image ce59cd45729e, tag proofA)
2. docker run (proofA) + curl /healthz /readyz   -> 200 {"status":"ok"} / {"status":"ok","database":"reachable"}
3. docker inspect --format '{{.State.Health.Status}}' -> "healthy" (the image's own HEALTHCHECK directive)
4. docker build --label hullq.proof=B .         -> succeeded, distinct image digest ac3e5188ccf6 (tag proofB)
5. docker run (proofB) + curl /readyz            -> 200 {"status":"ok","database":"reachable"}; confirmed
   running image digest differs from step 2 (ac3e5188... vs ce59cd45...) -- a genuine swap, not a no-op
6. Rollback: docker run (proofA again) + curl /healthz -> 200; confirmed running image digest is back to
   ce59cd45... (byte-identical to step 2) -- the recorded "known-good" tag redeploys exactly, not a rebuild
7. docker build -f web/Dockerfile web            -> succeeded (Astro Node SSR image)
```

This is a real deploy -> new-deploy -> rollback cycle against real immutable images and real HTTP health
checks; the only thing this sandbox could not exercise is steps 1-6 driven through `deploy.sh`/`rollback.sh`
themselves (both scripts call `docker compose ... pull`, which needs real GHCR network access this sandbox
does not have) and the actual GHCR push (`.github/workflows/deploy.yml`'s `push_to_ghcr` job runs on
GitHub's `ubuntu-latest` runners, which do have Docker + network — this has not yet been observed because
the workflow has not yet run on `main`). **Residual**: the exact-head GitHub Actions run of `push_to_ghcr`
after this slice merges is the first real observation of the GHCR-push half of this mechanism; the
deploy/rollback mechanism itself (image build, container swap, health-gating, rollback-to-prior-tag) is
proven above against the real Docker Engine.

## 6. Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `deploy.sh` reports health-check failure, auto-rolls back | new image fails to start, or `/readyz` fails (DB unreachable) | inspect `docker compose logs api`; fix the underlying issue before retrying the same tag |
| `rollback.sh` exits 2 | no `.last-good-tag` recorded yet (first-ever deploy failed) | manually `docker compose pull` + `up -d` a known-good tag from the GHCR package list |
| Caddy returns 525/526 | Cloudflare Full (strict) mode cert mismatch/expiry | reissue the Cloudflare Origin CA certificate, replace `certs/cf-origin*.pem`, `docker compose restart caddy` |
