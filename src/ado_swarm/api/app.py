from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ado_swarm.agents.registry import list_agent_metadata
from ado_swarm.config import get_settings
from ado_swarm.knowledge.graphiti_store import KnowledgeStore
from ado_swarm.runtime.mission_service import MissionService
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
    knowledge_health = await knowledge.healthcheck()
    return {
        # Reflect the weakest dependency so readiness probes aren't misled.
        "status": "ok" if knowledge_health.get("status") == "ok" else "degraded",
        "source_provider": provider.provider_name,
        "knowledge": knowledge_health,
    }


@app.get("/agents")
async def agents() -> list[dict]:
    return [metadata.model_dump(mode="json") for metadata in list_agent_metadata()]


@app.post("/missions")
async def start_mission(request: MissionRequest) -> dict:
    settings = get_settings()
    try:
        return await MissionService(settings).start(request.goal)
    except Exception as exc:  # pragma: no cover - exercised in deployed Temporal environment
        raise HTTPException(status_code=503, detail=f"Temporal unavailable: {exc}") from exc


@app.get("/missions/{workflow_id}")
async def get_mission(workflow_id: str) -> dict:
    return await MissionService().describe(workflow_id)


@app.post("/missions/{workflow_id}/pause")
async def pause_mission(workflow_id: str, request: WorkflowControlRequest) -> dict:
    return await MissionService().pause(workflow_id, request.reason)


@app.post("/missions/{workflow_id}/resume")
async def resume_mission(workflow_id: str) -> dict:
    return await MissionService().resume(workflow_id)
