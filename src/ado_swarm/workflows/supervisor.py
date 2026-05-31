from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from ado_swarm.contracts.events import RunStatus, TaskState
    from ado_swarm.contracts.mission import AgentResult, PlanVersion, RunSnapshot
    from ado_swarm.domain.plan_validation import validate_plan
    from ado_swarm.workflows.agent_task import AgentTaskWorkflow


@workflow.defn(name="SupervisorWorkflow")
class SupervisorWorkflow:
    def __init__(self) -> None:
        self.snapshot: RunSnapshot | None = None

    @workflow.run
    async def run(self, run_id: str, goal: str) -> RunSnapshot:
        self.snapshot = RunSnapshot(run_id=run_id, status=RunStatus.PLANNING, goal=goal)
        raw_plan = await workflow.execute_activity(
            "plan_mission", args=[run_id, goal], start_to_close_timeout=timedelta(seconds=30)
        )
        plan = PlanVersion.model_validate(raw_plan)
        validate_plan(plan)
        self.snapshot.current_plan_version = plan.version
        self.snapshot.status = RunStatus.RUNNING
        completed: set[str] = set()
        pending = {task.task_id: task for task in plan.tasks}
        while pending:
            runnable = [
                task
                for task in pending.values()
                if all(dep in completed for dep in task.depends_on)
            ]
            if not runnable:
                self.snapshot.status = RunStatus.FAILED
                self.snapshot.blocked_reason = "Plan has unresolved dependencies after validation."
                return self.snapshot
            for task in runnable:
                self.snapshot.task_states[task.task_id] = TaskState.RUNNING
                raw_result = await workflow.execute_child_workflow(
                    AgentTaskWorkflow.run,
                    args=[run_id, task, plan.version],
                    id=f"agent-task:{run_id}:{task.task_id}",
                )
                result = AgentResult.model_validate(raw_result)
                self.snapshot.task_states[task.task_id] = result.state
                if result.state != TaskState.COMPLETED:
                    self.snapshot.status = RunStatus.FAILED
                    self.snapshot.blocked_reason = result.error_message or result.summary
                    return self.snapshot
                completed.add(task.task_id)
                pending.pop(task.task_id)
        self.snapshot.status = RunStatus.COMPLETED
        return self.snapshot

    @workflow.query
    def get_snapshot(self) -> RunSnapshot | None:
        return self.snapshot
