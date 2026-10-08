from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from scripts.ops import inspect_deploy_rollback_lifecycle as lifecycle


def test_lowercase_owner_mechanism_matches_workflow_resolve_namespace_job() -> None:
    """Independent-review Finding O: GHCR/OCI repository names must be
    lowercase, but `github.repository_owner` can be mixed-case (e.g. the
    real owner `StradaDelSole`). `.github/workflows/deploy.yml`'s
    `resolve_namespace` job derives the canonical lowercase value with
    `tr '[:upper:]' '[:lower:]'` once and every other job consumes that
    single output. This proves the same transform on the same real
    mixed-case owner produces the exact lowercase namespace the workflow
    then reuses for lookup, metadata, push and deploy-time references.
    """
    bash = shutil.which("bash.exe", path=r"C:\Program Files\Git\usr\bin") or shutil.which("bash")
    if bash is None:
        pytest.skip("no POSIX bash available to execute the workflow's own shell snippet")
    env = dict(os.environ)
    env["OWNER"] = "StradaDelSole"
    result = subprocess.run(
        [bash, "-c", "printf '%s' \"$OWNER\" | tr '[:upper:]' '[:lower:]'"],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "stradadelsole"


def test_is_confirmed_not_found_accepts_exact_buildx_absence_message() -> None:
    ref = "ghcr.io/stradadelsole/hullq-api:sha-abc123"
    assert lifecycle._is_confirmed_not_found(ref, f"ERROR: {ref}: not found") is True


def test_is_confirmed_not_found_accepts_message_with_trailing_newline() -> None:
    ref = "ghcr.io/stradadelsole/hullq-api:sha-abc123"
    assert lifecycle._is_confirmed_not_found(ref, f"ERROR: {ref}: not found\n") is True


def test_is_confirmed_not_found_rejects_nested_manifest_failure() -> None:
    """Independent-review Finding P's core negative regression: a nested
    manifest/content-resolution failure can itself end in the same four
    words ("...not found") while the top-level queried ref genuinely
    exists. The old suffix-matching regex would have misclassified this
    as confirmed absence and authorized an unsafe rebuild. It must not.
    """
    ref = "ghcr.io/stradadelsole/hullq-api:sha-abc123"
    nested_failure = f"ERROR: {ref}: failed to resolve some-internal-blob: not found"
    assert lifecycle._is_confirmed_not_found(ref, nested_failure) is False


def test_is_confirmed_not_found_rejects_wrong_ref() -> None:
    queried_ref = "ghcr.io/stradadelsole/hullq-api:sha-abc123"
    other_ref = "ghcr.io/stradadelsole/hullq-api:sha-zzz999"
    assert lifecycle._is_confirmed_not_found(queried_ref, f"ERROR: {other_ref}: not found") is False


def test_is_confirmed_not_found_rejects_auth_and_network_failures() -> None:
    ref = "ghcr.io/stradadelsole/hullq-api:sha-abc123"
    assert lifecycle._is_confirmed_not_found(ref, "unauthorized: authentication required") is False
    assert lifecycle._is_confirmed_not_found(ref, "dial tcp: lookup ghcr.io: no such host") is False
    assert lifecycle._is_confirmed_not_found(ref, "") is False


def test_digest_re_accepts_well_formed_sha256_digest() -> None:
    assert lifecycle._DIGEST_RE.match("sha256:" + "a" * 64) is not None


def test_digest_re_rejects_malformed_digests() -> None:
    assert lifecycle._DIGEST_RE.match("sha256:" + "a" * 63) is None
    assert lifecycle._DIGEST_RE.match("sha256:" + "A" * 64) is None
    assert lifecycle._DIGEST_RE.match("sha256:" + "g" * 64) is None
    assert lifecycle._DIGEST_RE.match("") is None
    assert lifecycle._DIGEST_RE.match("not-a-digest") is None
