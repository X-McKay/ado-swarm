from __future__ import annotations

from dataclasses import dataclass

from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway


@dataclass
class BaseAgent:
    agent_id: str
    display_name: str
    skills: list[str]
    model_gateway: ModelGateway

    async def run(self, invocation: AgentInvocation) -> AgentResult:
        prompt = (
            f"Agent {self.display_name} executing task {invocation.task.title}: "
            f"{invocation.task.objective}"
        )
        completion = await self.model_gateway.complete(prompt)
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"{self.display_name} completed task with base runtime.",
            rationale=completion,
            activated_skills=self.skills[:1],
            requested_tools=invocation.task.allowed_tools,
        )
