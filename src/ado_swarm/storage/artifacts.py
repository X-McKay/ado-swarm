from __future__ import annotations

import json

import asyncpg

from ado_swarm.config import get_settings
from ado_swarm.contracts.artifacts import RunArtifact


class PostgresArtifactStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_settings().database_url

    async def append(self, artifact: RunArtifact) -> RunArtifact:
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
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
        finally:
            await conn.close()
        return artifact

    async def list_for_run(self, run_id: str) -> list[RunArtifact]:
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                "SELECT * FROM run_artifacts WHERE run_id=$1 ORDER BY created_at", run_id
            )
        finally:
            await conn.close()
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
