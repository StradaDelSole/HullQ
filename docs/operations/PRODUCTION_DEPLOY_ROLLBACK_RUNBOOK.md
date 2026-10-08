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
5. **GitHub repository setting (independent-review Finding G, defense in depth alongside `.github/workflows/deploy.yml`'s own `github.ref == 'refs/heads/main'` check):** in the repository's `production` GitHub Environment settings, set **Deployment branches and tags** to **Selected branches and tags** and add only `main`. This makes GitHub itself refuse to run the `deploy` job for any ref other than `main`, even if the workflow-level check were ever weakened or bypassed. Configure this once, before the `deploy` job is ever exercised for real.

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

**Execution status (independent-review Finding D, resolved 2026-10-08):**
Docker Desktop was started and the real Docker Engine (29.7.2) became
reachable in this session. `uv run python
scripts/ops/inspect_deploy_rollback_lifecycle.py` was then actually
executed against it and the real local PostgreSQL 18 test database, and
observed to complete clean:

```text
$ uv run python scripts/ops/inspect_deploy_rollback_lifecycle.py
[proof] 1) first deploy (release-a): expect no previous-release recorded
[proof] 2) upgrade to release-b: expect previous-release=release-a
[proof] 3) manual rollback via the stable rollback.sh entrypoint
[proof] 4) deploy deliberately-unhealthy release-c: expect auto-revert to release-a, exit 1
[proof] 5) corrupt the rollback target: expect a detected failure, no false success
[proof] cleaning up containers/images/temp directory
{
  "results": {
    "1_first_deploy_no_previous": true,
    "2_upgrade_a_to_b": true,
    "6_tag_config_coupling": true,
    "3_manual_rollback_returns_to_a": true,
    "4_failed_deploy_auto_reverts": true,
    "5_failed_rollback_detected": true,
    "7_real_nested_release_layout": true
  },
  "clear": true
}
```

exit code 0. All 7 named invariants (§5 above) observed true on this exact
run; the finally-block cleanup left no stray containers/images behind
(confirmed via `docker ps -a`/`docker images` immediately after).

This first real execution also surfaced and fixed five genuine defects in
the proof harness that static review alone had missed — exactly why
Finding D treated static inspection as insufficient:

1. `_bash()` invoked a bare `bash` on `$PATH`; on this Windows sandbox that
   resolved to `C:\Windows\System32\bash.exe`, which forwards into the
   machine's *default* WSL distribution — here the Docker-Desktop-managed
   `docker-desktop` appliance VM, which has no general-purpose shell
   (`execvpe(/bin/bash) failed`). Fixed by resolving Git for Windows' own
   `bash.exe` explicitly when present, falling back to normal `$PATH`
   lookup elsewhere (Linux CI runners, a real VPS).
2. Capturing subprocess output with `text=True` and no explicit encoding
   hit a `UnicodeDecodeError` against a byte in Docker's build output that
   is not valid in Windows' default `cp1252` locale codec. Fixed by
   decoding as UTF-8 with `errors="replace"`.
3. The stand-in `.env` pointed the APPLICATION CONTAINER's
   `HULLQ_DATABASE_URL` at `localhost`, which inside any container means
   the container's own loopback, never the host — so `/readyz` could
   never succeed and every deploy timed out after 60s. Fixed by using
   `host.docker.internal` (plus an explicit
   `host.docker.internal:host-gateway` `extra_hosts` mapping, so this also
   resolves on native Linux Docker, not just Docker Desktop).
4. `docker build` without `--load` completed with exit 0 but left the
   image only inside the active buildx builder's own cache (observed when
   Docker Desktop's ambient builder was using the `docker-container`
   driver rather than the classic driver) — invisible to `docker
   images`/`docker tag`/`docker run`, so the very next step failed with
   "No such image". Fixed by passing `--load` unconditionally.
5. Step 4's deliberately-tight health-check budget (3 retries × 1s = 3s,
   chosen only to make detecting release-c's unhealthiness fast) is
   inherited by the auto-revert redeploy of release-a that a failed
   deploy triggers — and a real container recreate + uvicorn startup +
   `/readyz` DB check does not always fit in 3s under load, which one
   repeat run surfaced as a spurious exit 3 ("auto-revert ALSO failed")
   instead of the expected exit 1. This was nondeterminism in the test's
   own timing margin, not in `deploy.sh`'s logic. Fixed by widening the
   budget to 20 retries × 1s = 20s — still far short of production's 60s
   default, but enough real margin for the revert's redeploy to
   consistently succeed. Confirmed deterministic by rerunning clean twice
   more after this fix.

None of these five affected the actual deploy/rollback mechanism being
proven (`scripts/ops/deploy.sh`/`rollback.sh` themselves needed no further
change beyond the health-port fix already recorded above) — all five were
in the proof harness's own subprocess/Docker/timing code. **Residual**:
the first real GHCR push and the first real VPS deploy via
`.github/workflows/deploy.yml` remain unobserved — this proof exercises the
mechanism against a real Docker Engine and a disposable release layout,
not the actual production VPS/GHCR path.

## 6. Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `deploy.sh` reports health-check failure, auto-reverts, exits 1 or 3 | new image fails to start, or `/readyz` fails (DB unreachable); exit 3 means the auto-revert itself also failed | inspect `docker compose logs api` in the failed release's directory; fix the underlying issue before retrying the same release; exit 3 requires immediate manual intervention |
| `rollback.sh` exits 2 | `state/previous-release` is missing, or names a release directory whose `deploy.sh` is gone | manually `docker compose up -d` a known-good release directory under `releases/`, or restore the missing release directory from CI/git history |
| Caddy returns 525/526 | Cloudflare Full (strict) mode cert mismatch/expiry | reissue the Cloudflare Origin CA certificate, replace `shared/certs/cf-origin*.pem`, `docker compose restart caddy` |
