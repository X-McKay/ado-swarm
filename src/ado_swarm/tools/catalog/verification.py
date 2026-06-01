"""Verification tool — run an allowlisted check command in a sandbox (the governor).

This is the "hard environmental signal" from the harness literature: the model
does not get to self-certify a fix. `test_engineer` (and later the validation
flow) calls this to actually run tests/linters/build in an isolated sandbox and
get a pass/fail it must respect. The command's executable must be allowlisted by
the sandbox; the agent cannot run arbitrary shell.
"""

from __future__ import annotations

from strands import tool

from ado_swarm.sandbox.provider import LocalSandboxProvider, SandboxCommandError


def run_validation_command_impl(command: list[str], *, timeout_seconds: int = 120) -> dict:
    provider = LocalSandboxProvider()
    session = provider.create("verification")
    try:
        result = provider.run_command(session, command, timeout_seconds=timeout_seconds)
    except SandboxCommandError as exc:
        return {
            "ok": False,
            "rejected": True,
            "reason": str(exc),
            "command": command,
        }
    return {
        "ok": result.ok,
        "rejected": False,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
        "command": result.command,
    }


@tool
def run_validation_command(command: list[str], timeout_seconds: int = 120) -> dict:
    """Run an allowlisted validation command (tests/lint/build) in a sandbox and report pass/fail.

    The first element of `command` must be an allowlisted executable (e.g. pytest,
    ruff, npm, go, cargo). Runs with no shell, a timeout, and truncated output.
    Treat a non-zero exit as a hard failure: do not declare a fix verified unless
    this returns ok=true.

    Args:
        command: The argv list, e.g. ["pytest", "-q", "tests/unit"].
        timeout_seconds: Wall-clock timeout for the command.

    Returns:
        A JSON object: ok, rejected, exit_code, timed_out, stdout_tail, stderr_tail, command.
    """
    return run_validation_command_impl(command, timeout_seconds=timeout_seconds)
