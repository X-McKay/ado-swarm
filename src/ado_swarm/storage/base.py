"""Storage ports and in-memory implementations.

These Protocols give the activity/agent layer a seam so tests can run without a
live Postgres. The Postgres implementations live in `storage.artifacts` and
`storage.checkpoints`; the in-memory variants here are the default test doubles.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ado_swarm.contracts.artifacts import RunArtifact
from ado_swarm.contracts.checkpoints import AgentCheckpoint


@runtime_checkable
class ArtifactStore(Protocol):
    async def append(self, artifact: RunArtifact) -> RunArtifact: ...

    async def list_for_run(self, run_id: str) -> list[RunArtifact]: ...


@runtime_checkable
class CheckpointStore(Protocol):
    async def append(self, checkpoint: AgentCheckpoint) -> AgentCheckpoint: ...

    async def latest_for_task(self, run_id: str, task_id: str) -> AgentCheckpoint | None: ...


class InMemoryArtifactStore:
    """Process-local artifact store for tests and isolated agent/eval runs."""

    def __init__(self) -> None:
        self._artifacts: list[RunArtifact] = []

    async def append(self, artifact: RunArtifact) -> RunArtifact:
        self._artifacts.append(artifact)
        return artifact

    async def list_for_run(self, run_id: str) -> list[RunArtifact]:
        return [a for a in self._artifacts if a.run_id == run_id]


class InMemoryCheckpointStore:
    """Process-local checkpoint store for tests and isolated agent/eval runs."""

    def __init__(self) -> None:
        self._checkpoints: list[AgentCheckpoint] = []

    async def append(self, checkpoint: AgentCheckpoint) -> AgentCheckpoint:
        self._checkpoints.append(checkpoint)
        return checkpoint

    async def latest_for_task(self, run_id: str, task_id: str) -> AgentCheckpoint | None:
        matches = [c for c in self._checkpoints if c.run_id == run_id and c.task_id == task_id]
        if not matches:
            return None
        return max(matches, key=lambda c: c.created_at)
