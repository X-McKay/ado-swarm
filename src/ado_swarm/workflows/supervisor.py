from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from ado_swarm.contracts.events import RunStatus, TaskState
    from ado_swarm.contracts.mission import AgentInvocation, RunSnapshot


@workflow.defn(name="SupervisorWorkflow")
class SupervisorWorkflow:
    def __init__(self) -> None:
        self.snapshot: RunSnapshot | None = None

    @workflow.run
    async def run(self, run_id: str, goal: str) -> RunSnapshot:
        self.snapshot = RunSnapshot(run_id=run_id, status=RunStatus.PLANNING, goal=goal)
        plan = await workflow.execute_activity(
            "plan_mission", args=[run_id, goal], start_to_close_timeout=timedelta(seconds=30)
        )
        self.snapshot.current_plan_version = plan.version
        self.snapshot.status = RunStatus.RUNNING
        for task in plan.tasks:
            self.snapshot.task_states[task.task_id] = TaskState.RUNNING
            invocation = AgentInvocation(
                run_id=run_id,
                task=task,
                context_id=run_id,
                plan_version=plan.version,
                idempotency_key=f"{run_id}:{task.task_id}",
            )
            result = await workflow.execute_activity(
                "run_agent", args=[invocation], start_to_close_timeout=timedelta(seconds=60)
            )
            self.snapshot.task_states[task.task_id] = result.state
        self.snapshot.status = RunStatus.COMPLETED
        return self.snapshot

    @workflow.query
    def get_snapshot(self) -> RunSnapshot | None:
        return self.snapshot
