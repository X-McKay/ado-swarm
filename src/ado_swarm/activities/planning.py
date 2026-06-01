from __future__ import annotations

from temporalio import activity

from ado_swarm.config import get_settings
from ado_swarm.contracts.mission import PlanVersion, TaskSpec
from ado_swarm.runtime.graph_templates import GraphTemplate, triage_readonly_graph
from ado_swarm.tools.source_providers.factory import build_source_provider

# Backwards-compatible view of the pipeline (agent_id, title, objective), derived
# from the single-source-of-truth graph template so the two can never drift.
PIPELINE = [
    (node.agent_id, node.title, node.objective)
    for node in triage_readonly_graph().execution_order()
]


def build_plan_from_template(
    run_id: str, goal: str, template: GraphTemplate, *, source_issue: dict | None = None
) -> PlanVersion:
    """Build a mission plan from a graph template (single source of truth for the DAG).

    Node keys map 1:1 to task ids so dependencies translate directly. The first
    (entry) task carries the source issue so the pipeline has a deterministic
    start, and a node's ``requires_approval`` becomes a task constraint the
    supervisor parks on before dispatching the task.
    """
    key_to_task_id: dict[str, str] = {}
    tasks: list[TaskSpec] = []
    for node in template.execution_order():
        constraints: dict = {}
        if not node.depends_on and source_issue is not None:
            constraints["source_issue"] = source_issue
        if node.requires_approval:
            constraints["requires_approval"] = True
        task = TaskSpec(
            run_id=run_id,
            title=node.title,
            objective=goal if not node.depends_on else node.objective,
            capability=node.agent_id,
            agent_id=node.agent_id,
            constraints=constraints,
            depends_on=[key_to_task_id[dep] for dep in node.depends_on],
            timeout_seconds=node.timeout_seconds,
        )
        key_to_task_id[node.node_id] = task.task_id
        tasks.append(task)
    return PlanVersion(
        run_id=run_id,
        goal=goal,
        rationale=f"Plan built from graph template '{template.template_id}'.",
        tasks=tasks,
    )


@activity.defn(name="plan_mission")
async def plan_mission(run_id: str, goal: str) -> PlanVersion:
    settings = get_settings()
    provider = build_source_provider(settings)
    # The first production increment uses the configured source provider's default
    # issue as a deterministic starting point. API/CLI request-level issue selection
    # can be added later without changing the pipeline handoff contract.
    source_issue = await provider.get_issue("SEC-1")
    return build_plan_from_template(
        run_id, goal, triage_readonly_graph(), source_issue=source_issue.model_dump(mode="json")
    )
