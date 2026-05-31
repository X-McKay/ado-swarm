from __future__ import annotations

from ado_swarm.contracts.mission import PlanVersion, TaskSpec


async def plan_mission(run_id: str, goal: str) -> PlanVersion:
    tasks = [
        TaskSpec(
            run_id=run_id,
            title="Normalize source issue",
            objective=goal,
            capability="ticket_analyst",
            agent_id="ticket_analyst",
        ),
        TaskSpec(
            run_id=run_id,
            title="Assess risk",
            objective="Score risk and automation eligibility.",
            capability="risk_auditor",
            agent_id="risk_auditor",
        ),
    ]
    tasks[1].depends_on.append(tasks[0].task_id)
    return PlanVersion(
        run_id=run_id, goal=goal, rationale="Static base architecture plan.", tasks=tasks
    )
