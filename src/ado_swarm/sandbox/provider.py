from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


@dataclass
class SandboxSession:
    session_id: str
    root: Path
    metadata: dict[str, str] = field(default_factory=dict)


class LocalSandboxProvider:
    """Local filesystem sandbox provider for dry-run remediation and tests."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(".artifacts/sandboxes")

    def create(self, purpose: str) -> SandboxSession:
        session_id = str(uuid4())
        root = self.base_dir / session_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "README.md").write_text(f"# Sandbox {session_id}\n\nPurpose: {purpose}\n")
        return SandboxSession(session_id=session_id, root=root, metadata={"purpose": purpose})

    def cleanup(self, session: SandboxSession) -> None:
        # Intentionally preserve local sandboxes for audit/debug by default.
        (session.root / ".closed").write_text("closed\n")
