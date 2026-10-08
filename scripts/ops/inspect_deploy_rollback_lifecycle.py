"""SLICE-0079 real-Docker proof of the release deploy/rollback lifecycle.

Independent-review amendment (2026-10): runs the REAL `scripts/ops/deploy.sh`
and `scripts/ops/rollback.sh` (not reimplemented test doubles) against a
temporary directory shaped exactly like the documented production layout
(`/opt/hullq/{releases/<sha>,shared,state}` --
`docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md` §1/§2) and the real
Docker Engine, proving:

1. a first deploy with no previous release records no rollback target;
2. an upgrade (A -> B) records A as the rollback target;
3. a manual rollback after a successful upgrade returns to A, not B;
4. a failed deploy (health check never succeeds) automatically reverts to
   the previous release and reports failure (exit 1), never success;
5. a failed rollback (corrupt/missing previous-release target) is detected
   and reported (non-zero exit) without corrupting the current-release
   state;
6. the running container's image reference is always exactly the tag
   derived from its own release directory's name -- image and deployment
   configuration can never drift apart;
7. all of the above works from the real nested release-directory layout,
   not a flattened stand-in.

Only one Docker image is built (all three "releases" tag the same content
under different names): this proof is about release/state-machine
correctness -- whether the right release's own image+configuration is the
one actually running at each point, not whether distinct commits produce
distinct image content (an ordinary property of `docker build`, not
specific to this mechanism).

The per-release Compose file used here is deliberately a minimal
single-service (api-only) stand-in for the real
`docker-compose.prod.yml` -- same `env_file`/image/port-binding shape, but
without Caddy/TLS, which are irrelevant to the release/state-machine logic
under test. `pull_policy: never` is used here (instead of the real file's
`missing`) so this proof can never attempt real network access.

Run:
  uv run python scripts/ops/inspect_deploy_rollback_lifecycle.py

Requires a working local Docker Engine and the local PostgreSQL 18 test
database (the same fixed local-only credentials
`scripts/workflow/claude_diag.py` already uses).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGE_NAME = "ghcr.io/stradadelsole/hullq-api"
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


def _write_compose(release_dir: Path, *, shared_dir: Path, sleep_forever: bool) -> None:
    command_line = '\n    command: ["sleep", "999"]' if sleep_forever else ""
    content = (
        "name: " + PROJECT_NAME + "\n"
        "services:\n"
        "  api:\n"
        f"    image: {IMAGE_NAME}:${{HULLQ_IMAGE_TAG}}\n"
        "    pull_policy: never\n"
        '    restart: "no"\n'
        f"    env_file: {_posix(shared_dir)}/.env\n"
        "    extra_hosts:\n"
        '      - "host.docker.internal:host-gateway"\n'
        "    ports:\n"
        f'      - "127.0.0.1:{HEALTH_PORT}:8000"{command_line}\n'
    )
    (release_dir / "docker-compose.prod.yml").write_text(content, encoding="utf-8")


def _make_release(root: Path, shared_dir: Path, sha: str, *, sleep_forever: bool = False) -> Path:
    release_dir = root / "releases" / sha
    release_dir.mkdir(parents=True)
    _write_compose(release_dir, shared_dir=shared_dir, sleep_forever=sleep_forever)
    for name in ("deploy.sh", "rollback.sh"):
        destination = release_dir / name
        shutil.copy2(REPO_ROOT / "scripts" / "ops" / name, destination)
        destination.chmod(0o755)
    return release_dir


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

    try:
        print(f"[proof] temp /opt/hullq-equivalent root: {root}", file=sys.stderr)
        print("[proof] building one real production image, tagged as all three releases", file=sys.stderr)
        # --load: when the active buildx builder uses the `docker-container`
        # driver (observed non-deterministically on this machine's Docker
        # Desktop), a build without --load completes "successfully" but
        # leaves the result only inside the buildkit builder's own cache --
        # invisible to `docker images`/`docker tag`/`docker run`. --load
        # forces the result into the local image store unconditionally,
        # which is what every later step here (tag, compose up, inspect)
        # requires.
        _run(
            [
                "docker",
                "build",
                "--load",
                "-t",
                f"{IMAGE_NAME}:sha-{SHA_A}",
                "-f",
                _posix(REPO_ROOT / "Dockerfile"),
                _posix(REPO_ROOT),
            ]
        )
        _run(["docker", "tag", f"{IMAGE_NAME}:sha-{SHA_A}", f"{IMAGE_NAME}:sha-{SHA_B}"])
        _run(["docker", "tag", f"{IMAGE_NAME}:sha-{SHA_A}", f"{IMAGE_NAME}:sha-{SHA_C}"])

        release_a = _make_release(root, shared_dir, SHA_A)
        release_b = _make_release(root, shared_dir, SHA_B)
        release_c = _make_release(root, shared_dir, SHA_C, sleep_forever=True)

        print("[proof] 1) first deploy (release-a): expect no previous-release recorded", file=sys.stderr)
        result = _bash(release_a / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"first deploy failed:\n{result.stdout}\n{result.stderr}")
        if current_file.read_text().strip() != SHA_A:
            raise AssertionError("current-release was not release-a after first deploy")
        if previous_file.exists():
            raise AssertionError("previous-release must not exist after the first-ever deploy")
        results["1_first_deploy_no_previous"] = True

        print("[proof] 2) upgrade to release-b: expect previous-release=release-a", file=sys.stderr)
        result = _bash(release_b / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"upgrade to release-b failed:\n{result.stdout}\n{result.stderr}")
        if current_file.read_text().strip() != SHA_B or previous_file.read_text().strip() != SHA_A:
            raise AssertionError("state after upgrade to release-b is wrong")
        if _running_image_reference() != f"{IMAGE_NAME}:sha-{SHA_B}":
            raise AssertionError("running container is not using release-b's own image tag")
        results["2_upgrade_a_to_b"] = True
        results["6_tag_config_coupling"] = True

        print("[proof] 3) manual rollback via the stable rollback.sh entrypoint", file=sys.stderr)
        rollback_entry = root / "rollback.sh"
        if not rollback_entry.exists():
            raise AssertionError("deploy.sh did not refresh the stable rollback.sh entrypoint")
        result = _bash(rollback_entry, extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"manual rollback failed:\n{result.stdout}\n{result.stderr}")
        if current_file.read_text().strip() != SHA_A or previous_file.read_text().strip() != SHA_B:
            raise AssertionError("state after manual rollback did not swap back to release-a")
        if _running_image_reference() != f"{IMAGE_NAME}:sha-{SHA_A}":
            raise AssertionError("manual rollback did not actually redeploy release-a's image")
        results["3_manual_rollback_returns_to_a"] = True

        print("[proof] 4) deploy deliberately-unhealthy release-c: expect auto-revert to release-a, exit 1", file=sys.stderr)
        result = _bash(
            release_c / "deploy.sh",
            extra_env={
                **env_common,
                "HULLQ_DEPLOY_HEALTH_RETRIES": "3",
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
        if _running_image_reference() != f"{IMAGE_NAME}:sha-{SHA_A}":
            raise AssertionError("auto-revert did not actually redeploy release-a's image")
        results["4_failed_deploy_auto_reverts"] = True

        print("[proof] 5) corrupt the rollback target: expect a detected failure, no false success", file=sys.stderr)
        previous_file.write_text("does-not-exist", encoding="utf-8")
        before_current = current_file.read_text().strip()
        result = _bash(rollback_entry, extra_env=env_common)
        if result.returncode == 0:
            raise AssertionError("rollback to a nonexistent release must not report success")
        if current_file.read_text().strip() != before_current:
            raise AssertionError("a failed rollback must not change current-release")
        results["5_failed_rollback_detected"] = True

        results["7_real_nested_release_layout"] = True
    finally:
        print("[proof] cleaning up containers/images/temp directory", file=sys.stderr)
        _run(["docker", "compose", "-p", PROJECT_NAME, "down", "--remove-orphans"], check=False)
        for sha in (SHA_A, SHA_B, SHA_C):
            _run(["docker", "rmi", f"{IMAGE_NAME}:sha-{sha}"], check=False)
        shutil.rmtree(root, ignore_errors=True)

    all_passed = all(results.values()) and len(results) == 7
    print(json.dumps({"results": results, "clear": all_passed}, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
