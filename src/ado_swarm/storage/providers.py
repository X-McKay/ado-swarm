"""Injectable storage providers.

Activities resolve their stores through these accessors instead of constructing
a concrete store inline, so tests (and isolated agent runs) can swap in the
in-memory implementations from `storage.base` without a live database.
"""

from __future__ import annotations

from ado_swarm.storage.base import ArtifactStore, CheckpointStore

_checkpoint_store: CheckpointStore | None = None
_artifact_store: ArtifactStore | None = None


def get_checkpoint_store() -> CheckpointStore:
    global _checkpoint_store
    if _checkpoint_store is None:
        from ado_swarm.storage.checkpoints import PostgresCheckpointStore

        _checkpoint_store = PostgresCheckpointStore()
    return _checkpoint_store


def set_checkpoint_store(store: CheckpointStore | None) -> None:
    global _checkpoint_store
    _checkpoint_store = store


def get_artifact_store() -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        from ado_swarm.storage.artifacts import PostgresArtifactStore

        _artifact_store = PostgresArtifactStore()
    return _artifact_store


def set_artifact_store(store: ArtifactStore | None) -> None:
    global _artifact_store
    _artifact_store = store
