from __future__ import annotations

import json

import asyncpg

from ado_swarm.config import get_settings
from ado_swarm.contracts.checkpoints import AgentCheckpoint


class PostgresCheckpointStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_settings().database_url

    async def append(self, checkpoint: AgentCheckpoint) -> AgentCheckpoint:
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
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
        finally:
            await conn.close()
        return checkpoint

    async def latest_for_task(self, run_id: str, task_id: str) -> AgentCheckpoint | None:
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                SELECT * FROM agent_checkpoints
                WHERE run_id=$1 AND task_id=$2
                ORDER BY created_at DESC LIMIT 1
                """,
                run_id,
                task_id,
            )
        finally:
            await conn.close()
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
