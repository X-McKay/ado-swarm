from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

# Only these executables may run in the sandbox. The agent never supplies a raw
# command string; a verification tool selects a command whose first token must be
# in this allowlist, and it always runs with shell=False, a timeout, and output caps.
ALLOWED_EXECUTABLES = frozenset(
    {"pytest", "python", "ruff", "npm", "node", "go", "cargo", "mvn", "gradle", "dotnet"}
)
MAX_OUTPUT_CHARS = 8000


class SandboxCommandError(RuntimeError):
    """Raised when a command is rejected before execution (e.g. not allowlisted)."""


@dataclass
class CommandResult:
    ok: bool
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    command: list[str]


@dataclass
class SandboxSession:
    session_id: str
    root: Path
    metadata: dict[str, str] = field(default_factory=dict)


class LocalSandboxProvider:
    """Local filesystem sandbox provider for dry-run remediation and verification."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(".artifacts/sandboxes")

    def create(self, purpose: str) -> SandboxSession:
        session_id = str(uuid4())
        root = self.base_dir / session_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text(f"# Sandbox {session_id}\n\nPurpose: {purpose}\n")
        return SandboxSession(session_id=session_id, root=root, metadata={"purpose": purpose})

    def run_command(
        self, session: SandboxSession, command: list[str], *, timeout_seconds: int = 120
    ) -> CommandResult:
        """Run an allowlisted command inside the sandbox root.

        The first token must be in ALLOWED_EXECUTABLES; the command runs with
        ``shell=False`` (no shell interpolation), a wall-clock timeout, and the
        sandbox root as cwd. Output is truncated to MAX_OUTPUT_CHARS. This is the
        "governor": a hard pass/fail environmental signal, not a write.
        """
        if not command:
            raise SandboxCommandError("empty command")
        executable = command[0]
        if executable not in ALLOWED_EXECUTABLES:
            raise SandboxCommandError(
                f"executable '{executable}' is not allowlisted for the sandbox"
            )
        try:
            completed = subprocess.run(  # noqa: S603 - shell=False, allowlisted argv, timeout + cwd
                command,
                cwd=session.root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                ok=False,
                exit_code=None,
                stdout=(exc.stdout or "")[:MAX_OUTPUT_CHARS] if isinstance(exc.stdout, str) else "",
                stderr=f"timed out after {timeout_seconds}s",
                timed_out=True,
                command=command,
            )
        except FileNotFoundError as exc:
            raise SandboxCommandError(f"executable not found: {executable}") from exc
        return CommandResult(
            ok=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout[:MAX_OUTPUT_CHARS],
            stderr=completed.stderr[:MAX_OUTPUT_CHARS],
            timed_out=False,
            command=command,
        )

    def cleanup(self, session: SandboxSession) -> None:
        # Intentionally preserve local sandboxes for audit/debug by default.
        (session.root / ".closed").write_text("closed\n")
