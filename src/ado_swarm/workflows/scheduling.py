"""Pure scheduling helpers for ``SupervisorWorkflow``.

Temporal-specific code should stay in the workflow, but dependency resolution,
artifact propagation, and task update construction are deterministic decisions
that are easier to unit-test as plain functions.
"""

from __future__ import annotations

from ado_swarm.contracts.events import ArtifactRef
from ado_swarm.contracts.mission import TaskSpec


def runnable_tasks(pending: dict[str, TaskSpec], completed: set[str]) -> list[TaskSpec]:
    """Return pending tasks whose dependencies are all complete."""
    return [task for task in pending.values() if all(dep in completed for dep in task.depends_on)]


def collect_dependency_artifacts(
    task: TaskSpec, artifacts_by_task: dict[str, list[ArtifactRef]]
) -> list[ArtifactRef]:
    """Collect artifacts produced by ``task`` dependencies, preserving dependency order."""
    artifacts: list[ArtifactRef] = []
    for dependency_id in task.depends_on:
        artifacts.extend(artifacts_by_task.get(dependency_id, []))
    return artifacts


def task_with_runtime_context(
    task: TaskSpec, *, dependency_artifacts: list[ArtifactRef], approved: bool
) -> TaskSpec:
    """Return a task copy with dependency artifacts and approval context attached."""
    updates: dict = {}
    if dependency_artifacts:
        updates["input_refs"] = [*task.input_refs, *dependency_artifacts]
    if approved:
        updates["constraints"] = {**task.constraints, "approved": True}
    return task.model_copy(update=updates) if updates else task
