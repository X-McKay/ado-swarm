"""Shared mission-control service for API and CLI surfaces."""

from __future__ import annotations

from uuid import uuid4

from ado_swarm.config import Settings
from ado_swarm.temporal.client import build_temporal_client
from ado_swarm.temporal.search_attributes import MissionSearchAttributes


class MissionService:
    """Small wrapper around Temporal mission workflow operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    async def _client(self):
        return await build_temporal_client(self.settings)

    async def start(self, goal: str) -> dict:
        settings = self.settings
        client = await build_temporal_client(settings)
        if settings is None:
            from ado_swarm.config import get_settings

            settings = get_settings()
        run_id = str(uuid4())
        handle = await client.start_workflow(
            "SupervisorWorkflow",
            args=[run_id, goal],
            id=f"mission:{run_id}",
            task_queue=settings.temporal_task_queue,
            search_attributes=MissionSearchAttributes(
                run_id=run_id,
                source_provider=settings.source_provider,
                mission_status="created",
            ).as_keywords(),
        )
        return {"run_id": run_id, "workflow_id": handle.id, "goal": goal, "status": "started"}

    async def describe(self, workflow_id: str) -> dict:
        client = await self._client()
        handle = client.get_workflow_handle(workflow_id)
        snapshot = await handle.query("get_snapshot")
        return snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else snapshot

    async def pause(self, workflow_id: str, reason: str = "manual pause") -> dict:
        client = await self._client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("pause", reason)
        return {"workflow_id": workflow_id, "status": "pause_signal_sent"}

    async def resume(self, workflow_id: str) -> dict:
        client = await self._client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("resume")
        return {"workflow_id": workflow_id, "status": "resume_signal_sent"}
