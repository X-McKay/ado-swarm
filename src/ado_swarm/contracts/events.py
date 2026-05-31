from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class RunStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskState(StrEnum):
    PENDING = "pending"
    ROUTING = "routing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    media_type: str = "application/octet-stream"
    uri: str
    size_bytes: int | None = None
    sha256: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    store: Literal["postgres", "object", "vector", "graph", "trace"]
    uri: str | None = None
    labels: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    task_id: str | None = None
    event_type: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    state: TaskState | None = None
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    memory_refs: list[MemoryRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
