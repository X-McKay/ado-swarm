from __future__ import annotations

from ado_swarm.contracts.artifacts import ArtifactKind, RunArtifact
from ado_swarm.contracts.mission import PlanVersion


def plan_artifact(plan: PlanVersion) -> RunArtifact:
    return RunArtifact(
        run_id=plan.run_id,
        kind=ArtifactKind.PLAN,
        name=f"plan-v{plan.version}",
        content=plan.model_dump(mode="json"),
        metadata={"created_by": plan.created_by},
    )


def execution_artifact(run_id: str, task_id: str | None, name: str, content: dict) -> RunArtifact:
    return RunArtifact(
        run_id=run_id,
        task_id=task_id,
        kind=ArtifactKind.EXECUTION_LOG,
        name=name,
        content=content,
    )
