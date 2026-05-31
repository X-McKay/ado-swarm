from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    version: str
    description: str
    entrypoint: str
    eval_entrypoint: str
    capabilities: list[str] = Field(default_factory=list)
    skill_packs: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    tools: dict[str, list[str] | dict] = Field(default_factory=dict)
    risk_tier: str = "low"
