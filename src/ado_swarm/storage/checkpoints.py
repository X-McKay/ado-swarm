from __future__ import annotations

import json

import asyncpg

from ado_swarm.contracts.checkpoints import AgentCheckpoint
from ado_swarm.storage.pool import get_pool, resolve_database_url


class PostgresCheckpointStore:
    def __init__(
        self, database_url: str | None = None, *, pool: asyncpg.Pool | None = None
    ) -> None:
        self.database_url = resolve_database_url(database_url)
        self._pool = pool

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await get_pool(self.database_url)
        return self._pool

    async def append(self, checkpoint: AgentCheckpoint) -> AgentCheckpoint:
        pool = await self._get_pool()
        await pool.execute(
            """
            INSERT INTO agent_checkpoints (
                checkpoint_id, run_id, task_id, agent_id, position, cycle_index,
                checkpoint, app_data, schema_version, created_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9,$10)
            ON CONFLICT (checkpoint_id) DO NOTHING
            """,
            checkpoint.checkpoint_id,
            checkpoint.run_id,
            checkpoint.task_id,
            checkpoint.agent_id,
            checkpoint.position,
            checkpoint.cycle_index,
            json.dumps(checkpoint.checkpoint),
            json.dumps(checkpoint.app_data),
            checkpoint.schema_version,
            checkpoint.created_at,
        )
        return checkpoint

    async def latest_for_task(self, run_id: str, task_id: str) -> AgentCheckpoint | None:
        pool = await self._get_pool()
        row = await pool.fetchrow(
            """
            SELECT * FROM agent_checkpoints
            WHERE run_id=$1 AND task_id=$2
            ORDER BY created_at DESC LIMIT 1
            """,
            run_id,
            task_id,
        )
        if not row:
            return None
        return AgentCheckpoint(
            checkpoint_id=row["checkpoint_id"],
            run_id=row["run_id"],
            task_id=row["task_id"],
            agent_id=row["agent_id"],
            position=row["position"],
            cycle_index=row["cycle_index"],
            checkpoint=dict(row["checkpoint"]),
            app_data=dict(row["app_data"]),
            schema_version=row["schema_version"],
            created_at=row["created_at"],
        )
