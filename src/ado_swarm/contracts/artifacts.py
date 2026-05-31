from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ArtifactKind(StrEnum):
    PLAN = "plan"
    CONTEXT_PACK = "context_pack"
    EXECUTION_LOG = "execution_log"
    VERIFICATION = "verification"
    DECISION_RECORD = "decision_record"
    MODEL_TRANSCRIPT = "model_transcript"
    TOOL_TRANSCRIPT = "tool_transcript"
    CHECKPOINT = "checkpoint"


class RunArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    task_id: str | None = None
    kind: ArtifactKind
    name: str
    uri: str | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
