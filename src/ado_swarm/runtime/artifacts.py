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
