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
  |     +-- image-refs.env               — this release's own runtime COPY of
  |                                         its immutable image identity
  |                                         (Finding L); the durable SOURCE
  |                                         of that identity is GHCR itself,
  |                                         off-host (Finding M, §1 below) —
  |                                         never this VPS-local file alone
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
`docker-compose.prod.yml`/`Caddyfile`/`deploy.sh`/`rollback.sh`/
`image-refs.env`, all from the exact same commit. `deploy.sh` reads the
images it deploys from its OWN release directory's `image-refs.env` — never
from an argument, the working directory, or a separately-mutable checkout —
so an older immutable image can never be paired with newer or drifted
configuration (independent review Finding B).

**Independent-review Finding L — immutable image identity.** A
`sha-<commit>` TAG by itself is not a mechanically immutable image
identity: the same tag could in principle be republished with different
bytes by a workflow rerun/retry/re-dispatch, and the Dockerfiles' own
upstream base images are themselves mutable tags, so rebuilding the same
commit later is not guaranteed to reproduce the same content. Each release
is therefore bound to the real OCI manifest **digest** GHCR assigned when
that release's images were first pushed —
`repository@sha256:<digest>` — recorded in that release's own
`image-refs.env` (`HULLQ_API_IMAGE=`/`HULLQ_WEB_IMAGE=`, read by
`docker-compose.prod.yml`) by `.github/workflows/deploy.yml`'s `deploy` job,
**exactly once**: if a release directory already has an `image-refs.env`
(e.g. because this exact commit's deploy is retried/re-dispatched), that
file is never overwritten, even if a rebuild of the same commit produced a
different digest this time. A human-readable `sha-<commit>` tag is still
pushed alongside the digest for operator convenience (`docker pull
<repo>:sha-<commit>` for manual inspection), but nothing in the deploy/
rollback path ever resolves it — only the recorded digest is ever deployed.
`<tag>` is always `sha-<full git commit SHA>` — never `latest`
(`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §24).

**Independent-review Finding M — the durable off-host release manifest.**
`image-refs.env` (Finding L) exists only on the application VPS. That alone
conflicts with this host being replaceable: if the VPS is lost and rebuilt,
a replacement VPS has no release directory for a previously-deployed
commit, and re-dispatching the deploy workflow for that same commit could
in principle rebuild it into *different* image bytes (the Dockerfiles'
upstream base images are themselves mutable tags) under the same
`sha-<commit>` tag — silently redefining what that commit means.

**GHCR itself is the durable, off-host release manifest** — no new
artifact type, service or platform was introduced. Before building either
image, `.github/workflows/deploy.yml`'s `push_api_to_ghcr`/
`push_web_to_ghcr` jobs check whether `ghcr.io/stradadelsole/hullq-<api|web>
:sha-<commit>` already resolves to a digest (`docker buildx imagetools
inspect`). If it does — this commit was ever successfully published
before, by this run or any earlier one, regardless of what happened to the
VPS in between — that existing digest is reused unconditionally and
nothing is rebuilt. Only when the tag has never been published does the
job build and push for the first time, which is what establishes the
durable record. `deploy`'s VPS-local `image-refs.env` write (Finding L) is
therefore always populated from this durable, already-resolved digest, not
from whatever a fresh build on this run happened to produce.

This is what actually justifies "the VPS can be rebuilt from scratch":
Both images are stateless: neither writes canonical application data to a
local volume. PostgreSQL (DigitalOcean Managed) and object storage
(Cloudflare R2) are both externalized. And now, a replacement VPS
re-materializing any previously-established commit's release directory
reconstructs the exact original image identity from GHCR's durable record
— never a fresh, potentially-divergent rebuild — using only this
repository, the `.env` file, the two certificate files, and GHCR's own
retained image history.

## 2. One-time VPS setup

1. Install Docker Engine + Compose plugin (standard distribution packages).
2. Create the deploy root, e.g. `/opt/hullq`, containing:
   - `shared/.env` (copied from `docs/operations/production.env.example` and filled in — never committed)
   - `shared/certs/cf-origin.pem`, `shared/certs/cf-origin-key.pem` (Cloudflare dashboard → SSL/TLS → Origin Server → Create Certificate; mode must be **Full (strict)**)
   - an empty `releases/` directory — CI populates one subdirectory per deployed commit (§3); never hand-create or hand-edit a release directory
3. `docker login ghcr.io` using a read-only GHCR personal access token (`read:packages` scope only — least privilege).
4. Also set up a separate `uv`-managed checkout for `scripts/ops/*` (§1) — these run directly on the VPS, outside Docker, because they need `pg_dump`/`pg_restore` matching PostgreSQL 18 exactly (`apt-get install postgresql-client-18` from the PGDG apt repository).
5. **GitHub repository setting (independent-review Finding G, defense in depth alongside `.github/workflows/deploy.yml`'s own `github.ref == 'refs/heads/main'` check):** in the repository's `production` GitHub Environment settings, set **Deployment branches and tags** to **Selected branches and tags** and add only `main`. This makes GitHub itself refuse to run the `deploy` job for any ref other than `main`, even if the workflow-level check were ever weakened or bypassed. Configure this once, before the `deploy` job is ever exercised for real.
6. **Pin the production SSH host key (independent-review Finding I — do not skip this):** `deploy.yml` trusts the production host's identity from the `DEPLOY_SSH_KNOWN_HOSTS` secret alone, never from a runtime `ssh-keyscan` against the same network path it is about to use (TOFU is not authentication). Obtain the host's real key out-of-band from the connection you are about to automate — e.g. the VPS provider's console/control-panel display of the host's SSH fingerprint, or by running `ssh-keyscan -H <host>` yourself over a connection you independently trust (e.g. the provider's web-based console, not the same path GitHub Actions will use) — then:
   - run `ssh-keyscan -H <host>` from that trusted vantage point and verify the returned fingerprint (`ssh-keygen -lf <(ssh-keyscan -H <host>)`) matches what the provider's console displays;
   - store the exact resulting line(s) (`<host> ssh-ed25519 AAAA...` etc.) as the `production` GitHub Environment's `DEPLOY_SSH_KNOWN_HOSTS` secret, newline-joined if there is more than one key type;
   - **rotation**: whenever the VPS is rebuilt or its host key is otherwise regenerated, repeat this procedure and update the secret before the next deploy — a stale `DEPLOY_SSH_KNOWN_HOSTS` value will correctly cause `deploy.yml` to fail closed (`StrictHostKeyChecking=yes`) rather than silently trusting a new, unverified key.

`state/` and the stable `$DEPLOY_PATH/rollback.sh` entrypoint do not need to
be created manually — the first successful `deploy.sh` run creates them.

## 3. Normal deploy

Deploy is automated by `.github/workflows/deploy.yml`'s `push_api_to_ghcr`/`push_web_to_ghcr` jobs (run on every push to `main`) — but only after that same workflow's `verify_ci_passed` job (independent-review Finding H) has confirmed, by directly querying GitHub's Checks API for that exact commit SHA, that the "CI" workflow's quality/db-integration/dependency-audit/historical-replay checks and the "Manufacturer artifact reproducibility" workflow's checks have all actually completed with `success` for it. A `main` commit whose required checks are failing (or still running) can never reach GHCR through this workflow.

Each push job first checks GHCR for an existing `sha-<commit>` tag for its own image (independent-review Finding M — GHCR is the durable off-host release manifest): if one already resolves to a digest, that digest is reused and nothing is rebuilt; otherwise the job builds and pushes for the first time, tagging the result `sha-<commit>` for human-readable convenience, and that push establishes the durable record. Either way, the job exposes the resolved `digest` (the real OCI manifest digest GHCR holds for that tag) as its output. Rolling a pushed build out to the VPS is **manual** via the same workflow's `deploy` job (`workflow_dispatch` with `deploy: true`), gated behind the GitHub `production` Environment (configure required reviewers there before first use).

That `deploy` job does, over SSH, for the exact commit SHA it is deploying:

1. checks whether `$DEPLOY_PATH/releases/<sha>/image-refs.env` already exists on the VPS. If it does (a rerun/retry/re-dispatch of this exact commit on a VPS that still has it), that release is left completely untouched — its originally-recorded image digests are never replaced (independent-review Finding L);
2. otherwise, materializes `$DEPLOY_PATH/releases/<sha>/` on the VPS — whether for the first time ever, or because a replacement VPS has no release directory for this commit after the original was lost — containing that commit's own `docker-compose.prod.yml`, `Caddyfile`, `deploy.sh`, `rollback.sh` **and** a freshly-written `image-refs.env` binding `HULLQ_API_IMAGE`/`HULLQ_WEB_IMAGE` to the `repository@sha256:<digest>` identities `push_api_to_ghcr`/`push_web_to_ghcr` resolved for THIS commit — the durable GHCR-recorded digests (reused from a prior publish if one exists), never necessarily a fresh build's output (independent-review Finding M);
3. runs that release's own `deploy.sh` — **no arguments**; everything it needs (the immutable image digests, the Compose/Caddy configuration) is derived from its own release directory.

**VPS loss/rebuild recovery:** because step 2 above always sources its digests from GHCR's durable record rather than purely from this run's own build, a replacement VPS re-dispatched for a previously-deployed commit reconstructs that exact same release — not a potentially-divergent rebuild — with no extra operator action beyond the normal deploy sequence.

`deploy.sh` reads `image-refs.env` (refusing to run if it is missing or incomplete — no mutable-tag fallback), runs `docker compose up -d` (pinned to those exact digests), polls `/healthz` and `/readyz` on `127.0.0.1:8000` for up to 60 seconds, and only on success advances the `state/` release pointers: the release that was current becomes `state/previous-release` (the rollback target) and the new release becomes `state/current-release` (independent review Finding C — state only advances after the deploy it describes has actually succeeded). It also refreshes the stable `$DEPLOY_PATH/rollback.sh` entrypoint from its own copy, so an operator always invokes the same fixed path regardless of which release is currently live.

On health-check failure, `deploy.sh` **automatically** re-runs the previously-current release's own `deploy.sh` (an auto-revert, not a mutation of state) and then exits non-zero — a failed deploy never advances or corrupts `state/current-release`/`state/previous-release`.

## 4. Manual rollback

```bash
/opt/hullq/rollback.sh
```

This stable path always contains whichever release's `rollback.sh` was last refreshed by a successful `deploy.sh` (§3) — the operator never needs to know which release directory is current. It reads `state/previous-release` and re-runs **that exact release's own** `deploy.sh`, which reads that release's own `image-refs.env` — the exact immutable digests recorded at that release's first publish, never re-resolved or re-derived (independent-review Finding L) — together with its own Compose/Caddy configuration. Because that succeeds, it naturally swaps `current`/`previous` back via the same state machine `deploy.sh` always uses. A second rollback therefore correctly toggles back to the release that was just replaced, rather than requiring unbounded rollback history.

If `state/previous-release` is missing, or names a release directory that no longer has its own `deploy.sh`, `rollback.sh` exits non-zero and leaves `state/current-release` untouched — a failed rollback never silently claims success or corrupts the recorded known-good state.

There is no destructive database migration to reverse here by design — see the migration runbook's expand/migrate/contract discipline, which keeps every deployed image version compatible with both the pre- and post-migration schema for one release window.

## 5. Local proof

`scripts/ops/inspect_deploy_rollback_lifecycle.py` runs the REAL
`scripts/ops/deploy.sh` and `scripts/ops/rollback.sh` (not reimplemented test
doubles) against a temporary directory shaped exactly like the production
layout in §1 (`releases/<sha>/`, `shared/`, `state/`) and the real Docker
Engine. It proves, end to end:

1. a first deploy with no previous release records no rollback target, and that release's recorded image identity is the exact digest actually pushed for it;
2. an upgrade (A → B) leaves A as `state/previous-release` (the rollback target), not B — and A/B are genuinely distinct, independently-pushed image digests (independent-review Finding L), not one build retagged;
3. a manual rollback through the stable `rollback.sh` entrypoint genuinely redeploys A's own EXACT ORIGINAL image digest+configuration (verified by inspecting the running container's actual image reference, not just the state file), and correctly swaps `current`/`previous` back;
4. a deliberately-unhealthy deploy auto-reverts to the last good release and reports failure (exit 1), never success, and never advances `state/current-release`;
5. a corrupted rollback target is detected and reported (non-zero exit) without corrupting `state/current-release`;
6. the running container's image reference always matches the immutable digest identity recorded for its own release — image and deployment configuration can never drift apart (Finding B/L);
7. all of the above against the real nested release-directory layout, not a flattened stand-in;
8. (independent-review Finding L) a later attempt to "republish" an already-established release with a DIFFERENT image digest is refused — that release's `image-refs.env` is left untouched, so a rerun/retry/re-dispatch of the same commit can never silently make that commit mean different image content;
9. (independent-review Finding L) a host with no locally-cached copy of a release's image (forced via `docker rmi`) and a host that already had it cached both resolve that release to the exact same image content;
10. (independent-review Finding M) a release whose VPS-local release directory (`image-refs.env` included) is deleted entirely — simulating total loss/rebuild of the application host — is reconstructed from the DURABLE off-host registry record, not from a fresh rebuild that (because upstream base images are mutable) could produce different content; the reconstructed host redeploys the ORIGINAL content exactly.

Run:

```bash
uv run python scripts/ops/inspect_deploy_rollback_lifecycle.py
```

Requires a working local Docker Engine and the local PostgreSQL 18 test
database.

**Execution status (independent-review Findings D, L and M, resolved
2026-10-08):** Docker Desktop was started and the real Docker Engine
(29.7.2) became reachable in this session. `uv run python
scripts/ops/inspect_deploy_rollback_lifecycle.py` was then actually
executed against it and the real local PostgreSQL 18 test database, and
observed to complete clean — this transcript is the current, expanded
10-invariant proof (Finding M added invariant 10's host-loss/
reconstruction assertion on top of Finding L's 9, which themselves expanded
Finding D's original 7):

```text
$ uv run python scripts/ops/inspect_deploy_rollback_lifecycle.py
[proof] starting throwaway local Docker registry
[proof] building two genuinely distinct images and pushing each for a real digest
[proof] 1) first deploy (release-a): expect no previous-release recorded, exact pushed digest deployed
[proof] 2) upgrade to release-b: expect previous-release=release-a, distinct independent digest deployed
[proof] 3) manual rollback via the stable rollback.sh entrypoint
[proof] 4) deploy deliberately-unhealthy release-c: expect auto-revert to release-a, exit 1
[proof] 5) corrupt the rollback target: expect a detected failure, no false success
[proof] 8) attempt to republish release-a with release-b's digest: expect its image-refs.env to remain untouched
[proof] 9) fresh pull (no local cache) vs cached pull resolve release-a to the same immutable content
[proof] 10) a lost/rebuilt application host reconstructs a release from the durable off-host registry record, never from a fresh local rebuild
[proof] cleaning up containers/images/registry/temp directory
{
  "results": {
    "1_first_deploy_no_previous": true,
    "2_upgrade_a_to_b": true,
    "3_manual_rollback_returns_to_a": true,
    "4_failed_deploy_auto_reverts": true,
    "5_failed_rollback_detected": true,
    "6_digest_config_coupling": true,
    "7_real_nested_release_layout": true,
    "8_republish_cannot_change_identity": true,
    "9_fresh_and_cached_pull_identical_content": true,
    "10_host_loss_reconstructs_from_durable_identity": true
  },
  "clear": true
}
```

exit code 0. All 10 named invariants (§5 above) observed true on this exact
run, confirmed deterministic across two consecutive clean runs; the
finally-block cleanup left no stray containers/images/registry behind each
time (confirmed via `docker ps -a`/`docker images` immediately after).

**Independent-review Finding M (resolved 2026-10-08):** added invariant 10,
which builds a fresh commit's image for real, deletes its VPS-local
release directory entirely (simulating total host loss), and proves that
re-materializing it resolves the ORIGINAL durable digest from the registry
rather than building new content — even when a simulated rebuild attempt
for the same commit tag would have produced genuinely different content.
`_resolve_or_build_and_push` (replacing the prior `_build_and_push`)
mirrors `.github/workflows/deploy.yml`'s own check-before-build guard
exactly: query the registry for an existing resolvable digest first,
build only if none exists. No defect was found while building this
expansion; it passed clean on the first real run and was re-run clean once
more to confirm determinism.

**Independent-review Finding L (resolved 2026-10-08):** the proof above now
starts a throwaway local Docker registry and builds two genuinely distinct
images (separate `--label`s, separate real pushed digests — not one build
retagged three ways as the original Finding D version did), proving
release independence and digest-bound identity for real rather than by
construction. One real defect surfaced and was fixed in this expansion:
step 9's fresh-pull check called `docker rmi` on an image a still-running
container referenced (left over from the immediately-preceding redeploy),
which Docker correctly refuses ("image is being used by running
container"). Fixed by stopping that container (`docker compose down`)
before removing the image, which is also simply the correct operational
order. Re-run clean twice after the fix.

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
