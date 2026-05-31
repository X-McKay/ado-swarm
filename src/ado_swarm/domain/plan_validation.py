from __future__ import annotations

from ado_swarm.contracts.mission import PlanVersion


class PlanValidationError(ValueError):
    """Raised when a plan cannot be executed safely."""


def validate_plan(plan: PlanVersion) -> None:
    task_ids = {task.task_id for task in plan.tasks}
    if len(task_ids) != len(plan.tasks):
        raise PlanValidationError("Task IDs must be unique")

    by_id = {task.task_id: task for task in plan.tasks}
    for task in plan.tasks:
        missing = set(task.depends_on) - task_ids
        if missing:
            raise PlanValidationError(
                f"Task {task.task_id} depends on unknown tasks: {sorted(missing)}"
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise PlanValidationError(f"Cycle detected at task {task_id}")
        visiting.add(task_id)
        for dep in by_id[task_id].depends_on:
            visit(dep)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_ids:
        visit(task_id)
