from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from ado_swarm.contracts.budget import BudgetUsage
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway
from ado_swarm.runtime.checkpoints import activity_boundary_checkpoint
from ado_swarm.runtime.observability import span
from ado_swarm.runtime.strands_runtime import StrandsAgentRuntime


@dataclass
class BaseAgent:
    agent_id: str
    display_name: str
    skills: list[str]
    model_gateway: ModelGateway

    async def run(self, invocation: AgentInvocation) -> AgentResult:
        started = perf_counter()
        system_prompt = (
            f"You are {self.display_name}. Use the provided task objective and skills to produce "
            "a concise, auditable result."
        )
        with span("agent.run", agent_id=self.agent_id, task_id=invocation.task.task_id) as current:
            runtime = StrandsAgentRuntime(self.model_gateway)
            runtime_result = await runtime.run_text(invocation, system_prompt)
        checkpoint = activity_boundary_checkpoint(
            invocation,
            state={
                "summary": f"{self.display_name} completed task with base runtime.",
                "runtime": runtime_result.telemetry,
            },
        )
        usage = BudgetUsage(
            agent_loops=1,
            model_calls=1,
            elapsed_seconds=perf_counter() - started,
        )
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"{self.display_name} completed task with base runtime.",
            rationale=runtime_result.text,
            activated_skills=self.skills[:1],
            requested_tools=invocation.task.allowed_tools,
            checkpoints=[checkpoint],
            budget_usage=usage,
            telemetry={
                **runtime_result.telemetry,
                "span": {
                    "span_id": current.span_id,
                    "duration_ms": current.duration_ms,
                    "error": current.error,
                },
            },
        )
