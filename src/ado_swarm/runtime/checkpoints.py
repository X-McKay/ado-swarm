from __future__ import annotations

from typing import Any

from ado_swarm.contracts.checkpoints import AgentCheckpoint
from ado_swarm.contracts.mission import AgentInvocation


def activity_boundary_checkpoint(
    invocation: AgentInvocation, *, cycle_index: int = 0, state: dict[str, Any] | None = None
) -> AgentCheckpoint:
    return AgentCheckpoint(
        run_id=invocation.run_id,
        task_id=invocation.task.task_id,
        agent_id=invocation.task.agent_id or invocation.task.capability,
        position="activity_boundary",
        cycle_index=cycle_index,
        checkpoint=state or {},
        app_data={
            "context_id": invocation.context_id,
            "plan_version": invocation.plan_version,
            "idempotency_key": invocation.idempotency_key,
        },
    )
