import pytest

from ado_swarm.contracts.mission import PlanVersion, TaskSpec
from ado_swarm.domain.plan_validation import PlanValidationError, validate_plan


def test_validate_plan_accepts_dag() -> None:
    task = TaskSpec(run_id="r1", title="a", objective="b", capability="ticket_analyst")
    validate_plan(PlanVersion(run_id="r1", goal="g", rationale="r", tasks=[task]))


def test_validate_plan_rejects_missing_dependency() -> None:
    task = TaskSpec(
        run_id="r1", title="a", objective="b", capability="ticket_analyst", depends_on=["missing"]
    )
    with pytest.raises(PlanValidationError):
        validate_plan(PlanVersion(run_id="r1", goal="g", rationale="r", tasks=[task]))


@pytest.mark.asyncio
async def test_plan_mission_builds_full_casefile_pipeline() -> None:
    from ado_swarm.activities.planning import PIPELINE, plan_mission

    plan = await plan_mission("r-pipeline", "validate pipeline")
    assert [task.agent_id for task in plan.tasks] == [agent_id for agent_id, _, _ in PIPELINE]
    assert len(plan.tasks) == 6
    assert "source_issue" in plan.tasks[0].constraints
    for index, current in enumerate(plan.tasks[1:], start=1):
        assert current.depends_on == [plan.tasks[index - 1].task_id]
    validate_plan(plan)


def test_downstream_task_can_carry_dependency_casefile_artifact() -> None:
    from ado_swarm.contracts.events import ArtifactRef

    artifact = ArtifactRef(
        name="casefile.json",
        uri="memory://casefiles/case-1",
        metadata={"casefile": {"casefile_id": "case-1"}},
    )
    task = TaskSpec(run_id="r1", title="a", objective="b", capability="repo_analyst")
    enriched = task.model_copy(update={"input_refs": [*task.input_refs, artifact]})
    assert enriched.input_refs[0].metadata["casefile"]["casefile_id"] == "case-1"
