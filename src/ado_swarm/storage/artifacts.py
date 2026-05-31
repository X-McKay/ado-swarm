from __future__ import annotations

import json

import asyncpg

from ado_swarm.contracts.artifacts import RunArtifact
from ado_swarm.storage.pool import get_pool, resolve_database_url


class PostgresArtifactStore:
    def __init__(
        self, database_url: str | None = None, *, pool: asyncpg.Pool | None = None
    ) -> None:
        self.database_url = resolve_database_url(database_url)
        self._pool = pool

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await get_pool(self.database_url)
        return self._pool

    async def append(self, artifact: RunArtifact) -> RunArtifact:
        pool = await self._get_pool()
        await pool.execute(
            """
            INSERT INTO run_artifacts (
                artifact_id, run_id, task_id, kind, name, uri,
                content, metadata, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9)
            ON CONFLICT (artifact_id) DO NOTHING
            """,
            artifact.artifact_id,
            artifact.run_id,
            artifact.task_id,
            artifact.kind.value,
            artifact.name,
            artifact.uri,
            json.dumps(artifact.content),
            json.dumps(artifact.metadata),
            artifact.created_at,
        )
        return artifact

    async def list_for_run(self, run_id: str) -> list[RunArtifact]:
        pool = await self._get_pool()
        rows = await pool.fetch(
            "SELECT * FROM run_artifacts WHERE run_id=$1 ORDER BY created_at", run_id
        )
        return [
            RunArtifact(
                artifact_id=row["artifact_id"],
                run_id=row["run_id"],
                task_id=row["task_id"],
                kind=row["kind"],
                name=row["name"],
                uri=row["uri"],
                content=dict(row["content"]),
                metadata=dict(row["metadata"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
