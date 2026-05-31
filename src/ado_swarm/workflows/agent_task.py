from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from ado_swarm.contracts.events import TaskState
    from ado_swarm.contracts.mission import AgentInvocation, AgentResult, TaskSpec


@workflow.defn(name="AgentTaskWorkflow")
class AgentTaskWorkflow:
    @workflow.run
    async def run(self, run_id: str, task: TaskSpec, plan_version: int) -> AgentResult:
        invocation = AgentInvocation(
            run_id=run_id,
            task=task,
            context_id=run_id,
            plan_version=plan_version,
            idempotency_key=f"{run_id}:{task.task_id}",
        )
        raw_result = await workflow.execute_activity(
            "run_agent",
            args=[invocation],
            start_to_close_timeout=timedelta(seconds=task.timeout_seconds),
        )
        result = AgentResult.model_validate(raw_result)
        if result.state != TaskState.COMPLETED:
            return result
        return result
