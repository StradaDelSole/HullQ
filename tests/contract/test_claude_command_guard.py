from scripts.workflow.claude_command_guard import (
    composition_reason,
    hook_response,
    routine_permission_allowed,
)


def _payload(event: str, command: str, tool_name: str = "Bash") -> dict[str, object]:
    return {
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": {"command": command},
    }


def test_guard_blocks_shell_loop_before_permission_prompt() -> None:
    command = (
        'for f in en de fr pt es; do echo "== $f =="; '
        'grep -n "canonicalPath" web/src/pages/$f/search.astro; done'
    )
    response = hook_response(_payload("PreToolUse", command))
    assert response is not None
    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_guard_blocks_pipeline_redirect_and_compound_operator() -> None:
    command = "cd web && npm ci 2>&1 | tail -20"
    reason = composition_reason(command)
    assert reason is not None


def test_guard_blocks_variable_expansion_and_substitution() -> None:
    assert composition_reason('echo "$HULLQ_TEST_DATABASE_URL"') is not None
    assert composition_reason('python_ver=$(uv run python -c "print(1)")') is not None


def test_guard_blocks_all_shell_expansion_forms_and_exec_wrappers() -> None:
    assert composition_reason('echo "$1"') is not None
    assert composition_reason('echo "${items[@]}"') is not None
    assert composition_reason("env NODE_ENV=test npm test") is not None
    assert composition_reason("echo {a,b}") is not None
    assert composition_reason("xargs grep canonicalPath") is not None
    assert composition_reason("bash -c 'npm test'") is not None
    assert composition_reason("find . -name '*.py' -exec cat {} \\;") is not None


def test_guard_allows_shell_metacharacters_inside_python_code_quotes() -> None:
    command = 'uv run python -c "import ast; print(1); print(2 | 1)"'
    assert composition_reason(command) is None


def test_guard_allows_standalone_approved_diagnostics() -> None:
    assert routine_permission_allowed('uv run python -c "import sys; print(sys.path[:5])"')
    assert routine_permission_allowed("npm ci --prefix web")
    assert routine_permission_allowed(
        "git diff --no-index web/src/pages/de/search.astro web/src/pages/fr/search.astro"
    )


def test_guard_does_not_auto_allow_destructive_or_privileged_commands() -> None:
    assert not routine_permission_allowed("uv run alembic downgrade -1")
    assert not routine_permission_allowed("git reset --hard HEAD~1")
    assert not routine_permission_allowed("git commit --amend --no-edit")
    assert not routine_permission_allowed("git switch main")
    assert not routine_permission_allowed("docker compose down -v")
    assert not routine_permission_allowed("uv run bash -c 'rm -rf build'")


def test_permission_request_auto_allows_only_bounded_routine_command() -> None:
    response = hook_response(_payload("PermissionRequest", "npm test --prefix web"))
    assert response == {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        }
    }

    assert hook_response(_payload("PermissionRequest", "rm -rf build")) is None


def test_non_shell_tool_is_not_intercepted() -> None:
    assert hook_response(_payload("PreToolUse", "anything", tool_name="Read")) is None
