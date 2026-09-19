"""Mechanical Claude Code approval-autonomy guard for HullQ.

Used by project-level PreToolUse and PermissionRequest hooks. The guard has
two deliberately different jobs:

* PreToolUse rejects routine shell composition that Claude Code cannot
  statically permission-match reliably. Claude receives a rewrite reason and
  can retry with standalone calls without involving the operator.
* PermissionRequest auto-allows only the same bounded routine command
  families HullQ already intends to run autonomously. Destructive or
  privileged operations are left to the normal permission flow.

The hook never executes the requested command itself and never prints
environment-variable values.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from typing import Any

_ROUTINE_ALLOW_PATTERNS = (
    re.compile(r"^uv(?:\s|$)"),
    re.compile(r"^pytest(?:\s|$)"),
    re.compile(r"^npm\s+(?:ci|run|test)(?:\s|$)"),
    re.compile(r"^git\s+(?:status|diff|log|show|rev-parse|fetch|add|commit)(?:\s|$)"),
    re.compile(r"^gh\s+(?:run\s+(?:list|view|watch)|pr(?:\s|$))"),
    re.compile(r"^docker\s+(?:ps|logs|compose\s+(?:ps|build|up))(?:\s|$)"),
)

_OPERATOR_RE = re.compile(r"[;&|<>]")
_CONTROL_WORD_RE = re.compile(r"(^|\s)(?:for|while|until|case|if|function)\b")
_ASSIGNMENT_RE = re.compile(r"(^|\s)[A-Za-z_][A-Za-z0-9_]*\s*=")
_SUBSHELL_RE = re.compile(r"(^|\s)\(")
_ROUTINE_WRAPPER_RE = re.compile(
    r"^\s*(?:xargs|watch|setsid|ionice|flock)(?:\s|$)"
    r"|^\s*(?:bash|sh|zsh|fish)\s+-c(?:\s|$)"
    r"|^\s*(?:powershell(?:\.exe)?|pwsh)\s+-(?:Command|File)(?:\s|$)"
    r"|^\s*cmd(?:\.exe)?\s+/c(?:\s|$)",
    re.IGNORECASE,
)
_FIND_EXEC_RE = re.compile(r"^\s*find\b.*(?:-exec|-delete)\b")

_DANGEROUS_ROUTINE_PATTERNS = (
    re.compile(r"^git\s+push\b.*(?:--force|-f(?:\s|$)|origin\s+main(?:\s|$)|:main|--delete)"),
    re.compile(r"^git\s+reset\s+--hard\b"),
    re.compile(r"^git\s+clean\b"),
    re.compile(r"^git\s+rebase\b"),
    re.compile(r"^git\s+(?:switch|checkout)\s+main(?:\s|$)"),
    re.compile(r"^git\s+commit\b.*--amend\b"),
    re.compile(r"^git\s+branch\s+-[dD](?:\s|$)"),
    re.compile(r"^uv\s+run\s+alembic\s+downgrade\b"),
    re.compile(r"^uv\s+run\s+(?:bash|sh|zsh|fish|powershell|pwsh|cmd)(?:\s|$)"),
    re.compile(r"^docker\s+compose\s+down\b.*(?:-v|--volumes)(?:\s|$)"),
)


def _shell_views(command: str) -> tuple[str, str, bool]:
    """Return (outside_quotes, outside_single_quotes, quotes_balanced).

    Shell operators matter only outside quotes. Variable/command expansion
    still matters inside double quotes, but not inside single quotes.
    """

    outside: list[str] = []
    expandable: list[str] = []
    in_single = False
    in_double = False

    for char in command:
        if char == "'" and not in_double:
            in_single = not in_single
            outside.append(" ")
            expandable.append(" ")
            continue

        if char == '"' and not in_single:
            in_double = not in_double
            outside.append(" ")
            expandable.append(" ")
            continue

        outside.append(char if not in_single and not in_double else " ")
        expandable.append(char if not in_single else " ")

    return "".join(outside), "".join(expandable), not (in_single or in_double)


def composition_reason(command: str) -> str | None:
    """Explain shell composition that must be split before execution."""

    outside, expandable, balanced = _shell_views(command)

    if not balanced:
        return "unbalanced shell quoting/escaping"
    if "\n" in outside or "\r" in outside:
        return "multiple shell statements/newlines"
    if _CONTROL_WORD_RE.search(outside):
        return "shell control flow/loop"
    if _ROUTINE_WRAPPER_RE.search(outside):
        return "shell/exec wrapper"
    if _FIND_EXEC_RE.search(outside):
        return "find -exec/-delete"
    if _ASSIGNMENT_RE.search(outside):
        return "shell variable/environment assignment"
    if "$(" in expandable or "`" in expandable:
        return "command substitution"
    if "$" in expandable:
        return "shell/environment-variable expansion"
    if "{" in outside or "}" in outside:
        return "unquoted brace expansion"
    if _SUBSHELL_RE.search(outside):
        return "subshell/group expression"
    if _OPERATOR_RE.search(outside):
        return "pipe/redirection/compound shell operator"
    return None


def _readonly_gh_api_allowed(command: str) -> bool:
    """Allow gh api only for requests that cannot implicitly write.

    `gh api` defaults to GET, but body/field flags can switch it to POST.
    Keep those and every non-GET explicit method in the normal operator
    permission flow while allowing ordinary repository API reads.
    """

    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if len(tokens) < 3 or tokens[:2] != ["gh", "api"]:
        return False

    index = 2
    while index < len(tokens):
        token = tokens[index]

        if token in {"-X", "--method"}:
            if index + 1 >= len(tokens) or tokens[index + 1].upper() != "GET":
                return False
            index += 2
            continue
        if token.startswith("--method="):
            if token.split("=", 1)[1].upper() != "GET":
                return False
        elif token.startswith("-X") and token != "-X":
            if token[2:].upper() != "GET":
                return False

        # These flags can supply a request body or implicitly change the
        # default method to POST. Leave them operator-gated even if the
        # target endpoint itself looks harmless.
        if token in {"-f", "--raw-field", "-F", "--field", "--input"}:
            return False
        if token.startswith(("--raw-field=", "--field=", "--input=")):
            return False
        if (token.startswith("-f") and token != "-f") or (token.startswith("-F") and token != "-F"):
            return False

        index += 1

    return True


def routine_permission_allowed(command: str) -> bool:
    """Return True only for bounded routine commands eligible for auto-allow."""

    stripped = command.strip()
    if not stripped or composition_reason(stripped) is not None:
        return False
    if any(pattern.search(stripped) for pattern in _DANGEROUS_ROUTINE_PATTERNS):
        return False
    if _readonly_gh_api_allowed(stripped):
        return True
    return any(pattern.search(stripped) for pattern in _ROUTINE_ALLOW_PATTERNS)


def _pretool_output(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "HullQ approval-autonomy guard blocked this routine shell command because it "
                f"contains {reason}. Rewrite and retry without asking the operator: use "
                "Read/Grep/Glob for file inspection and one standalone approved process command "
                "per tool call; use 'uv run python ...' for Python and '--prefix web' for npm "
                "when applicable. Do not use shell variables, pipes, redirects, loops, "
                "subshells, command substitution, ';', '&&', or '||' for routine work. "
                "For recurring diagnostics use 'uv run python scripts/workflow/claude_diag.py' "
                "(env-status, tcp-check, latest-temp-dir, run-local-test-db, or run-local-api)."
            ),
        }
    }


def hook_response(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return the hook JSON decision, or None for normal permission flow."""

    tool_name = payload.get("tool_name")
    if tool_name not in {"Bash", "PowerShell"}:
        return None

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None

    command = tool_input.get("command")
    if not isinstance(command, str):
        return None

    event = payload.get("hook_event_name")
    if event == "PreToolUse":
        reason = composition_reason(command)
        return _pretool_output(reason) if reason is not None else None

    if event == "PermissionRequest" and routine_permission_allowed(command):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"},
            }
        }

    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError, UnicodeDecodeError:
        # Malformed hook input must never grant permission.
        return

    if not isinstance(payload, dict):
        return

    response = hook_response(payload)
    if response is not None:
        json.dump(response, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
