from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    task_id: str
    agent_id: str
    position: Literal["after_model", "after_tools", "activity_boundary"] = "activity_boundary"
    cycle_index: int = 0
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    app_data: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
