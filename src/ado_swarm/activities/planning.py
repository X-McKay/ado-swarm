from __future__ import annotations

from temporalio import activity

from ado_swarm.config import get_settings
from ado_swarm.contracts.mission import PlanVersion, TaskSpec
from ado_swarm.tools.source_providers.factory import build_source_provider

PIPELINE = [
    (
        "ticket_analyst",
        "Normalize source issue",
        "Normalize the provider issue into a canonical security casefile.",
    ),
    (
        "repo_analyst",
        "Collect repository evidence",
        "Resolve repository context and verify the referenced file path when available.",
    ),
    (
        "security_reviewer",
        "Adjudicate finding",
        "Decide whether the finding is stale, false positive, already fixed, duplicate, or open.",
    ),
    (
        "risk_auditor",
        "Assess risk and automation eligibility",
        "Classify risk, impact, and whether automation can proceed safely.",
    ),
    (
        "solutions_architect",
        "Design bounded remediation plan",
        "Create a minimal safe remediation strategy and approval boundary.",
    ),
    (
        "test_engineer",
        "Prepare validation checklist",
        "Define validation checks and determine whether the casefile is ready for review.",
    ),
]


@activity.defn(name="plan_mission")
async def plan_mission(run_id: str, goal: str) -> PlanVersion:
    settings = get_settings()
    provider = build_source_provider(settings)
    # The first production increment uses the configured source provider's default
    # issue as a deterministic starting point. API/CLI request-level issue selection
    # can be added later without changing the pipeline handoff contract.
    source_issue = await provider.get_issue("SEC-1")

    tasks: list[TaskSpec] = []
    previous_task_id: str | None = None
    for agent_id, title, objective in PIPELINE:
        constraints = {}
        if agent_id == "ticket_analyst":
            constraints["source_issue"] = source_issue.model_dump(mode="json")
        task = TaskSpec(
            run_id=run_id,
            title=title,
            objective=goal if agent_id == "ticket_analyst" else objective,
            capability=agent_id,
            agent_id=agent_id,
            constraints=constraints,
            depends_on=[previous_task_id] if previous_task_id else [],
        )
        tasks.append(task)
        previous_task_id = task.task_id

    return PlanVersion(
        run_id=run_id,
        goal=goal,
        rationale="Six-agent deterministic casefile pipeline plan.",
        tasks=tasks,
    )
