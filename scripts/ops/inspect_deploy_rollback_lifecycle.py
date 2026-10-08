"""SLICE-0079 real-Docker proof of the release deploy/rollback lifecycle.

Independent-review amendment (2026-10): runs the REAL `scripts/ops/deploy.sh`
and `scripts/ops/rollback.sh` (not reimplemented test doubles) against a
temporary directory shaped exactly like the documented production layout
(`/opt/hullq/{releases/<sha>,shared,state}` --
`docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md` §1/§2), a real local
ephemeral Docker registry (see below), and the real Docker Engine, proving:

1. a first deploy with no previous release records no rollback target, and
   that release's recorded image identity is the exact digest actually
   pushed for it;
2. an upgrade (A -> B) leaves A as the rollback target, and A/B are
   genuinely distinct, independent image identities (not the same content
   retagged);
3. a manual rollback after a successful upgrade restores A's EXACT original
   image identity, not a freshly-resolved reference;
4. a failed deploy (health check never succeeds) automatically reverts to
   the previous release and reports failure (exit 1), never success;
5. a failed rollback (corrupt/missing previous-release target) is detected
   and reported (non-zero exit) without corrupting the current-release
   state;
6. the running container's image reference always exactly matches the
   immutable digest identity recorded for its own release -- image and
   deployment configuration can never drift apart;
7. all of the above works from the real nested release-directory layout,
   not a flattened stand-in;
8. (independent-review Finding L) a later attempt to "republish" an
   already-established release with a DIFFERENT image digest is refused --
   that release's recorded `image-refs.env` is left untouched, so a
   rerun/retry/re-dispatch of the same commit can never silently make that
   commit mean different image content;
9. (independent-review Finding L) a host with no locally-cached copy of a
   release's image (forced via `docker rmi`) and a host that already had it
   cached both resolve that release to the exact same image content, proven
   by comparing the actually-running container's real local image ID
   across both cases, not merely the reference string used.

Independent-review amendment (Finding L): release identity is now bound to
the real OCI manifest digest GHCR would assign in production
(`repository@sha256:<digest>`), never the mutable `sha-<commit>` tag alone.
To prove this for real rather than asserting it, this script starts a
throwaway, unauthenticated local Docker registry (`registry:2`, removed at
the end along with its anonymous volume) and builds TWO genuinely distinct
image contents (release A and release B each get their own `--label`, so
their builds produce genuinely different, independently-verified digests,
not one build retagged under different names) and pushes each for real,
parsing the real digest `docker push` reports. `docker-compose.prod.yml`'s
stand-in here reads `${HULLQ_API_IMAGE}` -- the exact same environment
variable name the real `docker-compose.prod.yml` and `scripts/ops/deploy.sh`
use -- from each release's own `image-refs.env`, written by
`_materialize_release` below exactly once per release directory, mirroring
`.github/workflows/deploy.yml`'s own first-publish-wins guard. `pull_policy:
missing` (matching the real file, not `never`) is used deliberately, so
this proof can genuinely exercise a real pull-by-digest against the local
throwaway registry -- never any real external network access.

The per-release Compose file used here is deliberately a minimal
single-service (api-only) stand-in for the real `docker-compose.prod.yml`
-- same `env_file`/image/port-binding shape, but without Caddy/TLS, which
are irrelevant to the release/state-machine/digest-identity logic under
test. `HULLQ_WEB_IMAGE` is still written into `image-refs.env` (reusing the
api image's own reference) purely so the real `deploy.sh`'s generic
both-must-be-set validation is satisfied; this stand-in's own Compose file
never reads it.

Run:
  uv run python scripts/ops/inspect_deploy_rollback_lifecycle.py

Requires a working local Docker Engine and the local PostgreSQL 18 test
database (the same fixed local-only credentials
`scripts/workflow/claude_diag.py` already uses).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGE_NAME = "hullq-api"
REGISTRY_CONTAINER = "hullq-proof-registry"
PROJECT_NAME = "hullq-prod-lifecycle-test"
HEALTH_PORT = 18200
# `host.docker.internal`, not `localhost`: this URL is read by the
# APPLICATION CONTAINER (via env_file), not by this host script -- from
# inside any container, `localhost` means the container's own loopback,
# never the host running Docker Desktop. `_write_compose` below adds the
# `host.docker.internal:host-gateway` extra_hosts mapping that makes this
# name resolve on Linux too (Docker 20.10+), not just Docker
# Desktop/Windows/Mac, where it already resolves without that mapping.
_LOCAL_TEST_DB_URL = "postgresql://hullq_test:hullq_test@host.docker.internal:5432/hullq_test"
_LOCAL_PREVIEW_SECRET = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="

SHA_A = "release-a"
SHA_B = "release-b"
SHA_C = "release-c-broken"


def _posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _resolve_bash() -> str:
    """Resolve a real POSIX bash, not Windows' WSL bash.exe relay.

    On Windows, a plain `bash` on PATH commonly resolves to
    C:\\Windows\\System32\\bash.exe, which forwards into whatever WSL
    distribution is currently default -- on a machine with Docker Desktop
    installed that is typically the `docker-desktop` distro, a minimal
    appliance VM with no general-purpose shell, not a real POSIX
    environment (`execvpe(/bin/bash) failed` results). Git for Windows'
    own bash.exe is this repository's documented shell for scripts/ops/*.sh
    (CLAUDE.md), so prefer it explicitly when present; elsewhere (Linux CI
    runners, a real VPS) fall back to normal PATH resolution.
    """

    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    found = shutil.which("bash")
    if found is None:
        raise RuntimeError("no usable bash executable found")
    return found


_BASH = _resolve_bash()


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    # explicit utf-8/replace: Docker/curl subprocess output is not
    # guaranteed to be valid in Windows' default locale codec (cp1252),
    # and a decode crash here must never be mistaken for the proof itself
    # failing.
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _bash(script: Path, *, extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    full_env.update(extra_env)
    return subprocess.run(
        [_BASH, _posix(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=full_env,
    )


def _start_registry() -> str:
    """Start a throwaway, unauthenticated local Docker registry.

    Docker Engine treats `localhost`/loopback registries as plain-HTTP
    allowed without any daemon configuration, which is exactly what makes
    this realistic (a real push, a real digest, a real pull-by-digest)
    without any real external network access or insecure-registry setup.
    """

    _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            REGISTRY_CONTAINER,
            "-p",
            "127.0.0.1:0:5000",
            "registry:2",
        ]
    )
    port_result = _run(["docker", "port", REGISTRY_CONTAINER, "5000/tcp"])
    lines = [line.strip() for line in port_result.stdout.splitlines() if line.strip()]
    host_port = lines[-1].rsplit(":", 1)[-1]
    return f"localhost:{host_port}"


def _stop_registry() -> None:
    _run(["docker", "rm", "-f", "-v", REGISTRY_CONTAINER], check=False)


def _build_and_push(registry_base: str, release_label: str) -> str:
    """Build a real, distinct image and push it for real, returning the
    real OCI manifest digest (e.g. "sha256:...") GHCR would equally assign
    in production. Each release gets its own `--label` so A and B are
    genuinely different content with genuinely different digests --
    independent-review Finding L requires proving release independence,
    which one image retagged three ways cannot demonstrate.
    """

    tag = f"{registry_base}/{IMAGE_NAME}:build-{release_label}"
    _run(
        [
            "docker",
            "build",
            "--load",
            "--label",
            f"hullq.proof.release={release_label}",
            "-t",
            tag,
            "-f",
            _posix(REPO_ROOT / "Dockerfile"),
            _posix(REPO_ROOT),
        ]
    )
    push_result = _run(["docker", "push", tag])
    match = re.search(r"digest:\s*(sha256:[0-9a-f]+)", push_result.stdout)
    if match is None:
        raise RuntimeError(f"could not parse digest from docker push output:\n{push_result.stdout}")
    return f"{registry_base}/{IMAGE_NAME}@{match.group(1)}"


def _write_compose(release_dir: Path, *, shared_dir: Path, sleep_forever: bool) -> None:
    command_line = '\n    command: ["sleep", "999"]' if sleep_forever else ""
    content = (
        "name: " + PROJECT_NAME + "\n"
        "services:\n"
        "  api:\n"
        "    image: ${HULLQ_API_IMAGE}\n"
        "    pull_policy: missing\n"
        '    restart: "no"\n'
        f"    env_file: {_posix(shared_dir)}/.env\n"
        "    extra_hosts:\n"
        '      - "host.docker.internal:host-gateway"\n'
        "    ports:\n"
        f'      - "127.0.0.1:{HEALTH_PORT}:8000"{command_line}\n'
    )
    (release_dir / "docker-compose.prod.yml").write_text(content, encoding="utf-8")


def _materialize_release(
    root: Path, shared_dir: Path, sha: str, image_ref: str, *, sleep_forever: bool = False
) -> tuple[Path, bool]:
    """Create release `sha`'s directory with its own `image-refs.env`,
    UNLESS it already exists -- mirroring .github/workflows/deploy.yml's
    own first-publish-wins guard (independent-review Finding L): once a
    release directory has an established `image-refs.env`, a later call
    for the same release (a rerun/retry/re-dispatch of the same commit)
    must never overwrite it, even with a different `image_ref`.

    Returns (release_dir, created) -- `created` is False when the release
    already existed and this call deliberately left it untouched.
    """

    release_dir = root / "releases" / sha
    image_refs_file = release_dir / "image-refs.env"
    if image_refs_file.is_file():
        return release_dir, False
    release_dir.mkdir(parents=True, exist_ok=True)
    _write_compose(release_dir, shared_dir=shared_dir, sleep_forever=sleep_forever)
    image_refs_file.write_text(
        f"HULLQ_API_IMAGE={image_ref}\nHULLQ_WEB_IMAGE={image_ref}\n", encoding="utf-8"
    )
    for name in ("deploy.sh", "rollback.sh"):
        destination = release_dir / name
        shutil.copy2(REPO_ROOT / "scripts" / "ops" / name, destination)
        destination.chmod(0o755)
    return release_dir, True


def _running_image_reference(container_suffix: str = "api-1") -> str:
    result = _run(
        [
            "docker",
            "inspect",
            f"{PROJECT_NAME}-{container_suffix}",
            "--format",
            "{{.Config.Image}}",
        ]
    )
    return result.stdout.strip()


def _running_image_id(container_suffix: str = "api-1") -> str:
    """The actually-running container's real local content-addressed
    image ID -- unlike `_running_image_reference`, this changes if the
    underlying image CONTENT differs, which is what independent-review
    Finding L's fresh-vs-cached-pull proof needs to compare.
    """

    result = _run(
        [
            "docker",
            "inspect",
            f"{PROJECT_NAME}-{container_suffix}",
            "--format",
            "{{.Image}}",
        ]
    )
    return result.stdout.strip()


def main() -> int:
    results: dict[str, bool] = {}
    root = Path(tempfile.mkdtemp(prefix="hullq-release-proof-"))
    shared_dir = root / "shared"
    shared_dir.mkdir()
    (shared_dir / ".env").write_text(
        f"HULLQ_DATABASE_URL={_LOCAL_TEST_DB_URL}\n"
        f"HULLQ_PREVIEW_SIGNING_SECRET={_LOCAL_PREVIEW_SECRET}\n",
        encoding="utf-8",
    )
    # HULLQ_DEPLOY_HEALTH_PORT must match the host-side port the stand-in
    # Compose file above actually publishes (HEALTH_PORT, deliberately not
    # production's 8000, so this proof can never collide with or
    # accidentally observe a real deploy running on the same machine).
    # deploy.sh's health check otherwise defaults to checking port 8000,
    # which would silently check the wrong (or no) service here.
    env_common = {
        "HULLQ_SHARED_DIR": _posix(shared_dir),
        "HULLQ_DEPLOY_HEALTH_PORT": str(HEALTH_PORT),
    }
    current_file = root / "state" / "current-release"
    previous_file = root / "state" / "previous-release"
    registry_base: str | None = None

    try:
        print(f"[proof] temp /opt/hullq-equivalent root: {root}", file=sys.stderr)
        print("[proof] starting throwaway local Docker registry", file=sys.stderr)
        registry_base = _start_registry()

        print(
            "[proof] building two genuinely distinct images and pushing each for a real digest",
            file=sys.stderr,
        )
        image_ref_a = _build_and_push(registry_base, "a")
        image_ref_b = _build_and_push(registry_base, "b")
        if image_ref_a == image_ref_b:
            raise AssertionError(
                "release A and release B must have genuinely distinct image digests"
            )

        release_a, created_a = _materialize_release(root, shared_dir, SHA_A, image_ref_a)
        release_b, created_b = _materialize_release(root, shared_dir, SHA_B, image_ref_b)
        release_c, created_c = _materialize_release(
            root, shared_dir, SHA_C, image_ref_a, sleep_forever=True
        )
        if not (created_a and created_b and created_c):
            raise AssertionError("every release must be freshly materialized on its first call")

        print(
            "[proof] 1) first deploy (release-a): expect no previous-release recorded, "
            "exact pushed digest deployed",
            file=sys.stderr,
        )
        result = _bash(release_a / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"first deploy failed:\n{result.stdout}\n{result.stderr}")
        if current_file.read_text().strip() != SHA_A:
            raise AssertionError("current-release was not release-a after first deploy")
        if previous_file.exists():
            raise AssertionError("previous-release must not exist after the first-ever deploy")
        if _running_image_reference() != image_ref_a:
            raise AssertionError("release-a did not deploy its own recorded immutable digest")
        results["1_first_deploy_no_previous"] = True

        print(
            "[proof] 2) upgrade to release-b: expect previous-release=release-a, "
            "distinct independent digest deployed",
            file=sys.stderr,
        )
        result = _bash(release_b / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"upgrade to release-b failed:\n{result.stdout}\n{result.stderr}")
        if current_file.read_text().strip() != SHA_B or previous_file.read_text().strip() != SHA_A:
            raise AssertionError("state after upgrade to release-b is wrong")
        if _running_image_reference() != image_ref_b:
            raise AssertionError("running container is not using release-b's own immutable digest")
        results["2_upgrade_a_to_b"] = True

        print("[proof] 3) manual rollback via the stable rollback.sh entrypoint", file=sys.stderr)
        rollback_entry = root / "rollback.sh"
        if not rollback_entry.exists():
            raise AssertionError("deploy.sh did not refresh the stable rollback.sh entrypoint")
        result = _bash(rollback_entry, extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"manual rollback failed:\n{result.stdout}\n{result.stderr}")
        if current_file.read_text().strip() != SHA_A or previous_file.read_text().strip() != SHA_B:
            raise AssertionError("state after manual rollback did not swap back to release-a")
        if _running_image_reference() != image_ref_a:
            raise AssertionError(
                "manual rollback did not restore release-a's exact original immutable digest"
            )
        results["3_manual_rollback_returns_to_a"] = True

        print(
            "[proof] 4) deploy deliberately-unhealthy release-c: expect auto-revert to release-a, exit 1",
            file=sys.stderr,
        )
        # release-c itself (no HTTP server at all -- `sleep 999`) will
        # exhaust these retries and fail every time regardless of their
        # size; what must NOT be too tight is the auto-revert redeploy of
        # release-a that deploy.sh triggers on failure (same script,
        # inherits these same env overrides) -- that is a real container
        # recreate + uvicorn startup + /readyz DB check, which a very
        # short budget (previously 3 retries * 1s = 3s) was observed to
        # occasionally miss under load, turning an expected exit 1 into a
        # spurious exit 3 (see independent-review Finding D amendment).
        # 20s is still far shorter than production's 60s default while
        # leaving real startup margin.
        result = _bash(
            release_c / "deploy.sh",
            extra_env={
                **env_common,
                "HULLQ_DEPLOY_HEALTH_RETRIES": "20",
                "HULLQ_DEPLOY_HEALTH_INTERVAL_SECONDS": "1",
            },
        )
        if result.returncode != 1:
            raise AssertionError(
                f"expected exit 1 (failed deploy, successful auto-revert), got {result.returncode}:\n"
                f"{result.stdout}\n{result.stderr}"
            )
        if current_file.read_text().strip() != SHA_A:
            raise AssertionError("auto-revert after a failed deploy did not restore release-a")
        if _running_image_reference() != image_ref_a:
            raise AssertionError("auto-revert did not actually redeploy release-a's own digest")
        results["4_failed_deploy_auto_reverts"] = True

        print(
            "[proof] 5) corrupt the rollback target: expect a detected failure, no false success",
            file=sys.stderr,
        )
        previous_file.write_text("does-not-exist", encoding="utf-8")
        before_current = current_file.read_text().strip()
        result = _bash(rollback_entry, extra_env=env_common)
        if result.returncode == 0:
            raise AssertionError("rollback to a nonexistent release must not report success")
        if current_file.read_text().strip() != before_current:
            raise AssertionError("a failed rollback must not change current-release")
        results["5_failed_rollback_detected"] = True
        results["6_digest_config_coupling"] = True
        results["7_real_nested_release_layout"] = True

        print(
            "[proof] 8) attempt to republish release-a with release-b's digest: "
            "expect its image-refs.env to remain untouched",
            file=sys.stderr,
        )
        _, republish_created = _materialize_release(root, shared_dir, SHA_A, image_ref_b)
        recorded_after_republish_attempt = (release_a / "image-refs.env").read_text(
            encoding="utf-8"
        )
        if republish_created or image_ref_b in recorded_after_republish_attempt:
            raise AssertionError(
                "re-materializing an already-established release must never change its "
                "recorded image identity"
            )
        if image_ref_a not in recorded_after_republish_attempt:
            raise AssertionError("release-a's original recorded image identity went missing")
        results["8_republish_cannot_change_identity"] = True

        print(
            "[proof] 9) fresh pull (no local cache) vs cached pull resolve release-a to the "
            "same immutable content",
            file=sys.stderr,
        )
        # Fully reset state/previous so this step cleanly redeploys A
        # twice from a known baseline, independent of step 5's
        # deliberately-corrupted previous_file.
        previous_file.unlink(missing_ok=True)
        result = _bash(release_a / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"baseline redeploy of release-a failed:\n{result.stdout}")
        content_cached = _running_image_id()

        # Stop the container using this image first -- Docker refuses to
        # remove an image that a running container still references.
        _run(["docker", "compose", "-p", PROJECT_NAME, "down"], check=False)
        _run(["docker", "rmi", image_ref_a])  # force no local cache for the next pull
        result = _bash(release_a / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"fresh-pull redeploy of release-a failed:\n{result.stdout}")
        content_fresh = _running_image_id()

        if content_cached != content_fresh:
            raise AssertionError(
                f"fresh pull produced different content than the cached pull: "
                f"{content_fresh} != {content_cached}"
            )
        results["9_fresh_and_cached_pull_identical_content"] = True
    finally:
        print("[proof] cleaning up containers/images/registry/temp directory", file=sys.stderr)
        _run(["docker", "compose", "-p", PROJECT_NAME, "down", "--remove-orphans"], check=False)
        _stop_registry()
        if registry_base is not None:
            _run(["docker", "rmi", f"{registry_base}/{IMAGE_NAME}:build-a"], check=False)
            _run(["docker", "rmi", f"{registry_base}/{IMAGE_NAME}:build-b"], check=False)
        shutil.rmtree(root, ignore_errors=True)

    all_passed = all(results.values()) and len(results) == 9
    print(json.dumps({"results": results, "clear": all_passed}, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
