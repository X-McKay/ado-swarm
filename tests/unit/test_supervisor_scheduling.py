from __future__ import annotations

from ado_swarm.contracts.events import ArtifactRef
from ado_swarm.contracts.mission import TaskSpec
from ado_swarm.workflows.scheduling import (
    collect_dependency_artifacts,
    runnable_tasks,
    task_with_runtime_context,
)


def _task(task_id: str, *, depends_on: list[str] | None = None) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        run_id="run-1",
        title=task_id,
        objective="test",
        capability="capability",
        depends_on=depends_on or [],
    )


def _artifact(name: str) -> ArtifactRef:
    return ArtifactRef(name=name, media_type="application/json", uri=f"memory://{name}")


def test_runnable_tasks_selects_only_dependency_satisfied_tasks() -> None:
    first = _task("first")
    second = _task("second", depends_on=["first"])
    third = _task("third", depends_on=["missing"])

    runnable = runnable_tasks({t.task_id: t for t in [first, second, third]}, {"first"})

    assert [task.task_id for task in runnable] == ["first", "second"]


def test_collect_dependency_artifacts_preserves_dependency_order() -> None:
    task = _task("third", depends_on=["first", "second"])
    artifacts_by_task = {
        "second": [_artifact("second-a")],
        "first": [_artifact("first-a"), _artifact("first-b")],
    }

    artifacts = collect_dependency_artifacts(task, artifacts_by_task)

    assert [artifact.name for artifact in artifacts] == ["first-a", "first-b", "second-a"]


def test_task_with_runtime_context_attaches_artifacts_and_approval() -> None:
    original = _task("approved", depends_on=["first"])
    artifact = _artifact("casefile.json")

    updated = task_with_runtime_context(original, dependency_artifacts=[artifact], approved=True)

    assert updated is not original
    assert updated.input_refs == [artifact]
    assert updated.constraints["approved"] is True
    assert original.input_refs == []
    assert "approved" not in original.constraints


def test_task_with_runtime_context_returns_original_when_no_updates_needed() -> None:
    original = _task("plain")

    updated = task_with_runtime_context(original, dependency_artifacts=[], approved=False)

    assert updated is original
