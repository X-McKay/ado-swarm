from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ado_swarm.contracts.events import (
    ArtifactRef,
    MemoryRef,
    RiskLevel,
    RunStatus,
    TaskEvent,
    TaskState,
)


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    title: str
    objective: str
    capability: str
    agent_id: str | None = None
    input_refs: list[ArtifactRef | MemoryRef] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    allowed_tools: list[str] = Field(default_factory=list)
    max_attempts: int = 3
    timeout_seconds: int = 1800


class PlanVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    version: int = 1
    goal: str
    rationale: str
    tasks: list[TaskSpec]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "planner"
    supersedes_version: int | None = None


class AgentInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    task: TaskSpec
    context_id: str
    plan_version: int
    idempotency_key: str
    source_provider: str = "stub"
    model_profile: str = "fake"
    blackboard_refs: list[MemoryRef] = Field(default_factory=list)
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    user_feedback: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    task_id: str
    state: TaskState
    summary: str
    rationale: str | None = None
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    memory_refs: list[MemoryRef] = Field(default_factory=list)
    suggested_followups: list[TaskSpec] = Field(default_factory=list)
    requires_replan: bool = False
    requires_approval: bool = False
    activated_skills: list[str] = Field(default_factory=list)
    requested_tools: list[str] = Field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None


class RunSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus
    goal: str
    current_plan_version: int | None = None
    task_states: dict[str, TaskState] = Field(default_factory=dict)
    latest_events: list[TaskEvent] = Field(default_factory=list)
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    blocked_reason: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
