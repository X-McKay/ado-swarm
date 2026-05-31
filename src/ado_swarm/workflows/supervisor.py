from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from ado_swarm.contracts.events import RunStatus, TaskState
    from ado_swarm.contracts.mission import PlanVersion, RunSnapshot
    from ado_swarm.domain.plan_validation import validate_plan
    from ado_swarm.runtime.artifacts import plan_artifact
    from ado_swarm.temporal.policies import ActivityRetryProfile, retry_policy
    from ado_swarm.workflows.agent_task import AgentTaskWorkflow


@workflow.defn(name="SupervisorWorkflow")
class SupervisorWorkflow:
    def __init__(self) -> None:
        self.snapshot: RunSnapshot | None = None
        self.paused = False
        self.cancel_requested = False
        self.replan_requested = False
        self.approvals: dict[str, str] = {}

    @workflow.run
    async def run(self, run_id: str, goal: str) -> RunSnapshot:
        self.snapshot = RunSnapshot(run_id=run_id, status=RunStatus.PLANNING, goal=goal)
        plan = await workflow.execute_activity(
            "plan_mission",
            args=[run_id, goal],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy(ActivityRetryProfile.DEFAULT),
        )
        plan = PlanVersion.model_validate(plan)
        validate_plan(plan)
        self.snapshot.current_plan_version = plan.version
        self.snapshot.run_artifacts.append(plan_artifact(plan))
        self.snapshot.status = RunStatus.RUNNING
        completed: set[str] = set()
        pending = {task.task_id: task for task in plan.tasks}
        while pending:
            await workflow.wait_condition(lambda: not self.paused or self.cancel_requested)
            if self.cancel_requested:
                self.snapshot.status = RunStatus.CANCELLED
                self.snapshot.blocked_reason = "cancel requested"
                return self.snapshot
            if self.replan_requested:
                self.snapshot.status = RunStatus.WAITING_FOR_APPROVAL
                self.snapshot.blocked_reason = "replan requested"
                return self.snapshot
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
                result = await workflow.execute_child_workflow(
                    AgentTaskWorkflow.run,
                    args=[run_id, task, plan.version],
                    id=f"agent-task:{run_id}:{task.task_id}",
                )
                self.snapshot.task_states[task.task_id] = result.state
                self.snapshot.artifact_refs.extend(result.artifact_refs)
                if result.requires_approval:
                    self.snapshot.status = RunStatus.WAITING_FOR_APPROVAL
                    self.snapshot.blocked_reason = result.summary
                    return self.snapshot
                if result.state != TaskState.COMPLETED:
                    self.snapshot.status = RunStatus.FAILED
                    self.snapshot.blocked_reason = result.error_message or result.summary
                    return self.snapshot
                completed.add(task.task_id)
                pending.pop(task.task_id)
        self.snapshot.status = RunStatus.COMPLETED
        self.snapshot.approvals = dict(self.approvals)
        return self.snapshot

    @workflow.query
    def get_snapshot(self) -> RunSnapshot | None:
        return self.snapshot

    @workflow.signal
    def pause(self, reason: str = "manual pause") -> None:
        self.paused = True
        if self.snapshot:
            self.snapshot.status = RunStatus.WAITING_FOR_APPROVAL
            self.snapshot.blocked_reason = reason

    @workflow.signal
    def resume(self) -> None:
        self.paused = False
        if self.snapshot and self.snapshot.status == RunStatus.WAITING_FOR_APPROVAL:
            self.snapshot.status = RunStatus.RUNNING
            self.snapshot.blocked_reason = None

    @workflow.signal
    def cancel(self, reason: str = "manual cancel") -> None:
        self.cancel_requested = True
        if self.snapshot:
            self.snapshot.blocked_reason = reason

    @workflow.update
    def approve_task(self, task_id: str, approver: str) -> str:
        self.approvals[task_id] = approver
        if self.snapshot:
            self.snapshot.approvals = dict(self.approvals)
        return "approved"

    @approve_task.validator
    def validate_approve_task(self, task_id: str, approver: str) -> None:
        if not task_id:
            raise ValueError("task_id is required")
        if not approver:
            raise ValueError("approver is required")

    @workflow.update
    def reject_task(self, task_id: str, reason: str) -> str:
        self.approvals[task_id] = f"rejected:{reason}"
        if self.snapshot:
            self.snapshot.approvals = dict(self.approvals)
            self.snapshot.status = RunStatus.CANCELLED
            self.snapshot.blocked_reason = reason
        self.cancel_requested = True
        return "rejected"

    @reject_task.validator
    def validate_reject_task(self, task_id: str, reason: str) -> None:
        if not task_id:
            raise ValueError("task_id is required")
        if not reason:
            raise ValueError("reason is required")

    @workflow.update
    def request_replan(self, reason: str) -> str:
        self.replan_requested = True
        if self.snapshot:
            self.snapshot.status = RunStatus.WAITING_FOR_APPROVAL
            self.snapshot.blocked_reason = reason
        return "replan_requested"

    @request_replan.validator
    def validate_request_replan(self, reason: str) -> None:
        if not reason:
            raise ValueError("reason is required")
