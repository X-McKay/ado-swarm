from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

from ado_swarm.agents.registry import list_agent_metadata
from ado_swarm.config import get_settings
from ado_swarm.knowledge.graphiti_store import KnowledgeStore
from ado_swarm.tools.source_providers.factory import build_source_provider

app = FastAPI(title="ado-swarm", version="0.1.0")


class MissionRequest(BaseModel):
    goal: str


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
    # API wiring is present; Temporal start is kept in CLI/worker paths
    # for local simplicity in the base runtime.
    return {"run_id": str(uuid4()), "goal": request.goal, "status": "created"}
