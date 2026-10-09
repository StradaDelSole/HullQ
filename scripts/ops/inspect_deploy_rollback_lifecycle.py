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
   across both cases, not merely the reference string used;
10. (independent-review Finding M) a release whose VPS-local release
    directory (including `image-refs.env`) is completely lost -- simulating
    total loss/rebuild of the application host -- is reconstructed from the
    DURABLE off-host registry record, not from a fresh local rebuild: even
    when a rebuild attempt for that same commit would produce different
    content (upstream base images are mutable), the reconstructed host
    redeploys the ORIGINAL content, byte for byte;
11. (independent-review Finding N) a registry lookup failure that is NOT a
    confirmed absence (here, a real connection failure from stopping the
    registry container) makes the resolver fail closed -- raising rather
    than falling through to a rebuild -- and the established digest is
    unchanged once the registry recovers.

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

Independent-review amendment (Finding M): `image-refs.env` (Finding L)
exists only on the application VPS, which the accepted architecture
requires to be replaceable/rebuildable from scratch -- so it cannot be the
SOLE source of truth for a release's image identity. `_resolve_or_build_and_push`
mirrors `.github/workflows/deploy.yml`'s own durable-reuse guard: before
building, it checks whether the target tag already resolves to a digest in
the registry (the durable, off-host record -- GHCR in production, this
throwaway registry here) and reuses that digest unconditionally rather than
building, so a rebuild of an already-established commit (even one that
would produce different bytes) can never silently redefine it. Step 10
proves the actual failure case Finding M named: deleting a release's
VPS-local directory entirely and reconstructing it on what is, in every way
this proof can observe, a "fresh host."

Independent-review amendment (Finding N): the Finding M version of this
guard treated ANY non-zero `imagetools inspect` exit as "not published,"
which is unsafe -- a transient registry/network outage, an auth failure,
or a rate limit all exit non-zero too, and are NOT proof of absence.
`_resolve_existing_digest` now distinguishes exactly three outcomes: a
successful resolve (reuse, after validating the digest's `sha256:<64 hex>`
shape); buildx's own confirmed `"<ref>: not found"` message (verified
empirically against this real throwaway registry, not assumed -- this is
the ONLY case allowed to proceed to a first publish); and everything else,
which raises instead of returning "not found." `_resolve_or_build_and_push`
also now re-resolves a tag it just pushed and confirms the digest matches
what the push itself reported, before trusting it (the recommended
defense-in-depth safeguard). Step 11 proves the actual failure case
Finding N named: a real registry outage (the throwaway registry container
is actually stopped, not simulated) must make the resolver raise rather
than silently rebuild, and the established identity must survive the
outage unchanged once the registry recovers.

Independent-review amendment (Findings O and P): two HIGH findings from
reviewing Finding N itself. Finding O: `.github/workflows/deploy.yml`
built GHCR references from the raw (mixed-case) `github.repository_owner`
in some places while other logic already hardcoded the lowercase form
Docker/OCI references actually require -- an inconsistency that could
make the very FIRST real lookup fail with an invalid-reference error
rather than a confirmed absence, which Finding N's own correct fail-closed
behavior would then block on forever. Fixed by computing one canonical
lowercase namespace once (a dedicated `resolve_namespace` job) and reusing
it everywhere a GHCR reference is built. This proof script's own
`IMAGE_NAME` has no owner segment at all (a local throwaway registry, not
GHCR), so it was never exposed to this bug; Finding O's fix and its
regression test (`tests/unit/test_deploy_rollback_lifecycle_classifier.py`)
live with the real workflow instead. Finding P: `_is_confirmed_not_found`
(above) replaces what was a suffix-matching regex -- which could have
misclassified a nested manifest/content-resolution failure ending in the
same four words as a confirmed absence of the top-level queried ref -- with
an exact-message match tied to that exact `ref`. The same test file
proves this distinction directly (no Docker required) alongside the
lowercase-namespace mechanism; this script's own steps 1-11 were re-run
against the real Docker Engine after the classifier change, confirming the
stricter classifier still accepts every genuine confirmed-absence case
this proof actually produces (see the amendment's retained execution
evidence for the observed result).

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
import time
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
SHA_HOSTLOSS = "release-hostloss"


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
    return _registry_host_port()


def _registry_host_port() -> str:
    port_result = _run(["docker", "port", REGISTRY_CONTAINER, "5000/tcp"])
    lines = [line.strip() for line in port_result.stdout.splitlines() if line.strip()]
    host_port = lines[-1].rsplit(":", 1)[-1]
    return f"localhost:{host_port}"


def _stop_registry() -> None:
    _run(["docker", "rm", "-f", "-v", REGISTRY_CONTAINER], check=False)


_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _is_confirmed_not_found(ref: str, stderr_text: str) -> bool:
    """True ONLY for buildx's own exact confirmed-absence message for
    THIS specific `ref` -- `ERROR: <ref>: not found`, the complete
    message, not a substring or suffix match.

    Independent-review Finding P: an earlier version of this check used a
    suffix match (`re.search(r": not found\\s*$", ...)`), which would
    also match a NESTED manifest/content-resolution failure whose own
    message happens to end the same way (e.g. "ERROR: <ref>: failed to
    resolve some-internal-blob: not found") even though the top-level
    queried `ref` actually exists. Exact equality against the full
    expected message, anchored to this exact `ref`, is what makes this
    genuinely "only a confirmed absence of the exact queried tag may
    authorize first publication" rather than "any error that happens to
    end in the same four words." If buildx's wording ever changes, this
    correctly stops classifying anything as absent (a safe availability
    failure -- see `_resolve_existing_digest`) rather than silently
    broadening to match more text.
    """

    return stderr_text.strip() == f"ERROR: {ref}: not found"


def _resolve_existing_digest(ref: str) -> str | None:
    """Query the registry for `ref`'s existing digest, distinguishing a
    CONFIRMED absence (returns None) from every other failure (raises) --
    independent-review Finding N: a generic non-zero exit from `imagetools
    inspect` is NOT proof of absence. It can equally mean a transient
    registry/network outage, an auth failure, or a rate limit -- and
    treating any of those as "not published" (the pre-Finding-N version of
    this logic, and of `.github/workflows/deploy.yml`'s matching step)
    risked exactly the invariant Findings L/M exist to protect: a lookup
    failure for an ALREADY-established commit falling through to a
    rebuild that could silently redefine it. Only `_is_confirmed_not_found`
    (verified empirically against a real registry, not assumed -- see this
    amendment's own verification) is treated as absence; every other
    failure raises instead.
    """

    result = _run(["docker", "buildx", "imagetools", "inspect", ref], check=False)
    if result.returncode == 0:
        match = re.search(r"^Digest:\s*(\S+)", result.stdout, re.MULTILINE)
        digest = match.group(1) if match else ""
        if not _DIGEST_RE.match(digest):
            raise RuntimeError(f"resolved digest for {ref} has an unexpected shape: {digest!r}")
        return digest
    if _is_confirmed_not_found(ref, result.stderr):
        return None
    raise RuntimeError(
        f"could not confirm whether {ref} exists (registry/network/auth failure, "
        f"not a confirmed absence) -- failing closed rather than risking an unsafe "
        f"rebuild:\n{result.stderr}"
    )


def _resolve_or_build_and_push(registry_base: str, tag: str, release_label: str) -> str:
    """Mirror .github/workflows/deploy.yml's own Finding M/N guard for
    real: check whether `tag` already resolves to a digest in the
    registry -- the durable, off-host record of what that tag means,
    which (in production, GHCR; here, this throwaway registry) survives
    even total loss of the application VPS -- and reuse it
    unconditionally rather than building. Only when the registry
    explicitly confirms the tag has never been published does this build
    fresh content (labelled `release_label`, so distinct calls with
    distinct labels produce genuinely distinct digests) and push it,
    returning the real OCI manifest digest (e.g. "sha256:...") GHCR would
    equally assign in production. Any OTHER lookup failure propagates as
    an exception -- it must never fall through to a build (Finding N).

    A later call with the SAME `tag` but a DIFFERENT `release_label` must
    still return the ORIGINAL digest -- that is exactly what proves a
    rebuild (even one that would produce different bytes, e.g. because
    upstream base images moved) can never silently redefine an
    already-established identity.
    """

    ref = f"{registry_base}/{IMAGE_NAME}:{tag}"
    existing_digest = _resolve_existing_digest(ref)
    if existing_digest is not None:
        return f"{registry_base}/{IMAGE_NAME}@{existing_digest}"

    _run(
        [
            "docker",
            "build",
            "--load",
            "--label",
            f"hullq.proof.release={release_label}",
            "-t",
            ref,
            "-f",
            _posix(REPO_ROOT / "Dockerfile"),
            _posix(REPO_ROOT),
        ]
    )
    push_result = _run(["docker", "push", ref])
    match = re.search(r"digest:\s*(sha256:[0-9a-f]+)", push_result.stdout)
    if match is None:
        raise RuntimeError(f"could not parse digest from docker push output:\n{push_result.stdout}")
    pushed_digest = match.group(1)
    if not _DIGEST_RE.match(pushed_digest):
        raise RuntimeError(f"pushed digest for {ref} has an unexpected shape: {pushed_digest!r}")

    # Independent-review Finding N recommended safeguard: re-resolve the
    # tag we just pushed from the registry itself and confirm it matches
    # what the push reported, rather than trusting that single report
    # alone.
    verify_digest = _resolve_existing_digest(ref)
    if verify_digest != pushed_digest:
        raise RuntimeError(
            f"post-push verification mismatch for {ref}: push reported {pushed_digest}, "
            f"registry now resolves {verify_digest}"
        )
    return f"{registry_base}/{IMAGE_NAME}@{pushed_digest}"


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
    recovered_registry_base: str | None = None
    fail_closed_tag: str | None = None

    try:
        print(f"[proof] temp /opt/hullq-equivalent root: {root}", file=sys.stderr)
        print("[proof] starting throwaway local Docker registry", file=sys.stderr)
        registry_base = _start_registry()

        print(
            "[proof] building two genuinely distinct images and pushing each for a real digest",
            file=sys.stderr,
        )
        image_ref_a = _resolve_or_build_and_push(registry_base, "build-a", "a")
        image_ref_b = _resolve_or_build_and_push(registry_base, "build-b", "b")
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

        print(
            "[proof] 10) a lost/rebuilt application host reconstructs a release from the "
            "durable off-host registry record, never from a fresh local rebuild",
            file=sys.stderr,
        )
        # independent-review Finding M: $RELEASE_DIR/image-refs.env (Finding
        # L) exists only on the application VPS, which the accepted
        # architecture requires to be replaceable. This step proves that a
        # TOTAL loss of that VPS-local release directory does not cost
        # commit X its established identity, because the durable record
        # lives in the registry (GHCR in production; this throwaway
        # registry here), never only on the host.
        hostloss_tag = "sha-hostloss-commit"
        digest_established = _resolve_or_build_and_push(registry_base, hostloss_tag, "hostloss-v1")
        release_hostloss, _ = _materialize_release(
            root, shared_dir, SHA_HOSTLOSS, digest_established
        )
        result = _bash(release_hostloss / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"initial deploy of release-hostloss failed:\n{result.stdout}")
        content_before_loss = _running_image_id()

        # Simulate total loss of the application VPS's local release
        # state for this commit: its release directory (including
        # image-refs.env) is gone, exactly as it would be after a VPS
        # rebuild from scratch.
        _run(["docker", "compose", "-p", PROJECT_NAME, "down"], check=False)
        shutil.rmtree(release_hostloss)
        if release_hostloss.exists():
            raise AssertionError(
                "simulated host loss did not actually remove the release directory"
            )

        # Simulate a later rebuild of the SAME commit that -- because
        # upstream base images are mutable -- would produce DIFFERENT
        # content if it were ever actually built. The durable registry
        # record for `hostloss_tag` must cause this to resolve to the
        # ORIGINAL digest instead of building this "v2" content at all.
        digest_after_rebuild_attempt = _resolve_or_build_and_push(
            registry_base, hostloss_tag, "hostloss-v2-WOULD-BE-DIFFERENT"
        )
        if digest_after_rebuild_attempt != digest_established:
            raise AssertionError(
                "a rebuild attempt for an already-established commit must resolve to the "
                "original durable digest, not a new one"
            )

        # Reconstruct a fresh host: the release directory does not exist
        # locally (just deleted above), so this is a genuine first-time
        # materialization on this "host" -- but it must use the RESOLVED
        # durable digest, not re-trigger a build.
        reconstructed_release, reconstructed_created = _materialize_release(
            root, shared_dir, SHA_HOSTLOSS, digest_after_rebuild_attempt
        )
        if not reconstructed_created:
            raise AssertionError("reconstruction after simulated host loss did not actually occur")
        reconstructed_refs = (reconstructed_release / "image-refs.env").read_text(encoding="utf-8")
        if digest_established not in reconstructed_refs:
            raise AssertionError(
                "reconstructed release-hostloss does not record the original durable digest"
            )

        # Prove redeployment (the rollback/redeploy path) on the
        # reconstructed host actually runs the ORIGINAL content, not
        # anything a "v2" rebuild could have produced.
        result = _bash(reconstructed_release / "deploy.sh", extra_env=env_common)
        if result.returncode != 0:
            raise AssertionError(f"redeploy after host loss failed:\n{result.stdout}")
        content_after_reconstruction = _running_image_id()
        if content_after_reconstruction != content_before_loss:
            raise AssertionError(
                f"reconstructed host did not redeploy the original content: "
                f"{content_after_reconstruction} != {content_before_loss}"
            )
        results["10_host_loss_reconstructs_from_durable_identity"] = True

        print(
            "[proof] 11) a registry lookup failure (not a confirmed absence) fails closed: "
            "no build/push side effect, established identity unchanged",
            file=sys.stderr,
        )
        # independent-review Finding N: a non-zero `imagetools inspect` exit
        # is NOT proof of absence -- it can equally mean a transient
        # registry/network outage. Establish a tag, then stop the registry
        # container entirely (a real connection failure, not a simulated
        # one) and prove `_resolve_or_build_and_push` RAISES rather than
        # falling through to a rebuild that would silently redefine this
        # tag. Then bring the registry back and prove the established
        # digest survived the outage unchanged.
        fail_closed_tag = "sha-failclosed-test"
        digest_before_outage = _resolve_or_build_and_push(
            registry_base, fail_closed_tag, "failclosed-v1"
        )

        _run(["docker", "stop", REGISTRY_CONTAINER])
        raised = False
        try:
            _resolve_or_build_and_push(
                registry_base, fail_closed_tag, "failclosed-v2-WOULD-BE-DIFFERENT"
            )
        except RuntimeError:
            raised = True
        if not raised:
            raise AssertionError(
                "a registry outage must make the resolver raise, not silently fall "
                "through to a rebuild"
            )

        # `docker start` on a dynamically-published (`-p 0:5000`) container
        # reassigns the host port rather than reusing the old one -- so the
        # registry must be re-discovered, not assumed to still be at
        # `registry_base`. A short bounded retry absorbs the container's
        # brief startup window.
        _run(["docker", "start", REGISTRY_CONTAINER])
        digest_after_recovery = None
        last_error: Exception | None = None
        for _attempt in range(10):
            time.sleep(1)
            try:
                recovered_registry_base = _registry_host_port()
                digest_after_recovery = _resolve_or_build_and_push(
                    recovered_registry_base, fail_closed_tag, "failclosed-v3-irrelevant"
                )
                break
            except RuntimeError as exc:
                last_error = exc
        else:
            raise AssertionError(f"registry did not recover after restart: {last_error}")

        # Compare only the `@sha256:...` digest suffix, not the full
        # reference string: this throwaway registry's dynamically-assigned
        # host port is reassigned by `docker start` (a test-harness
        # artifact of this sandbox -- a real registry like GHCR has a
        # fixed hostname), so `registry_base` legitimately differs
        # before/after the outage even though the underlying image
        # content/digest must not.
        digest_suffix_before = digest_before_outage.rsplit("@", 1)[-1]
        digest_suffix_after = (
            digest_after_recovery.rsplit("@", 1)[-1] if digest_after_recovery else None
        )
        if digest_suffix_after != digest_suffix_before:
            raise AssertionError(
                "established digest must survive a transient registry outage unchanged: "
                f"{digest_after_recovery} != {digest_before_outage}"
            )
        results["11_registry_failure_fails_closed_no_side_effect"] = True
    finally:
        print("[proof] cleaning up containers/images/registry/temp directory", file=sys.stderr)
        _run(["docker", "compose", "-p", PROJECT_NAME, "down", "--remove-orphans"], check=False)
        _stop_registry()
        if registry_base is not None:
            _run(["docker", "rmi", f"{registry_base}/{IMAGE_NAME}:build-a"], check=False)
            _run(["docker", "rmi", f"{registry_base}/{IMAGE_NAME}:build-b"], check=False)
            _run(
                ["docker", "rmi", f"{registry_base}/{IMAGE_NAME}:sha-hostloss-commit"], check=False
            )
        if recovered_registry_base is not None and fail_closed_tag is not None:
            _run(
                ["docker", "rmi", f"{recovered_registry_base}/{IMAGE_NAME}:{fail_closed_tag}"],
                check=False,
            )
        shutil.rmtree(root, ignore_errors=True)

    all_passed = all(results.values()) and len(results) == 11
    print(json.dumps({"results": results, "clear": all_passed}, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
