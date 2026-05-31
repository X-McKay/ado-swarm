from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ado_swarm.agents.registry import list_agent_metadata
from ado_swarm.config import get_settings
from ado_swarm.knowledge.graphiti_store import KnowledgeStore
from ado_swarm.temporal.client import build_temporal_client
from ado_swarm.tools.source_providers.factory import build_source_provider

app = FastAPI(title="ado-swarm", version="0.1.0")


class MissionRequest(BaseModel):
    goal: str


class WorkflowControlRequest(BaseModel):
    reason: str = "manual request"


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    provider = build_source_provider(settings)
    knowledge = KnowledgeStore()
    return {
        "status": "ok",
        "source_provider": provider.provider_name,
        "knowledge": await knowledge.healthcheck(),
    }


@app.get("/agents")
async def agents() -> list[dict]:
    return [metadata.model_dump(mode="json") for metadata in list_agent_metadata()]


@app.post("/missions")
async def start_mission(request: MissionRequest) -> dict:
    settings = get_settings()
    run_id = str(uuid4())
    try:
        client = await build_temporal_client(settings)
        handle = await client.start_workflow(
            "SupervisorWorkflow",
            args=[run_id, request.goal],
            id=f"mission:{run_id}",
            task_queue=settings.temporal_task_queue,
        )
    except Exception as exc:  # pragma: no cover - exercised in deployed Temporal environment
        raise HTTPException(status_code=503, detail=f"Temporal unavailable: {exc}") from exc
    return {"run_id": run_id, "workflow_id": handle.id, "goal": request.goal, "status": "started"}


@app.get("/missions/{workflow_id}")
async def get_mission(workflow_id: str) -> dict:
    client = await build_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    snapshot = await handle.query("get_snapshot")
    return snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else snapshot


@app.post("/missions/{workflow_id}/pause")
async def pause_mission(workflow_id: str, request: WorkflowControlRequest) -> dict:
    client = await build_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("pause", request.reason)
    return {"workflow_id": workflow_id, "status": "pause_signal_sent"}


@app.post("/missions/{workflow_id}/resume")
async def resume_mission(workflow_id: str) -> dict:
    client = await build_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("resume")
    return {"workflow_id": workflow_id, "status": "resume_signal_sent"}
