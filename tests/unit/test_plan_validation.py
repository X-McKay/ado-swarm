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
