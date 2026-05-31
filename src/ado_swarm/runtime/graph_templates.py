from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphNodeSpec:
    node_id: str
    agent_id: str
    title: str = ""
    objective: str = ""
    depends_on: tuple[str, ...] = ()
    timeout_seconds: int = 300


@dataclass(frozen=True)
class GraphTemplate:
    template_id: str
    description: str
    nodes: tuple[GraphNodeSpec, ...]
    max_steps: int = 20
    max_concurrency: int = 1

    def execution_order(self) -> list[GraphNodeSpec]:
        completed: set[str] = set()
        pending = list(self.nodes)
        ordered: list[GraphNodeSpec] = []
        while pending:
            runnable = [
                node for node in pending if all(dep in completed for dep in node.depends_on)
            ]
            if not runnable:
                raise ValueError(f"Graph template {self.template_id} has unresolved dependencies")
            for node in runnable:
                ordered.append(node)
                completed.add(node.node_id)
                pending.remove(node)
        return ordered


def triage_readonly_graph() -> GraphTemplate:
    """The single source of truth for the read-only triage pipeline DAG.

    The planner (`activities/planning.py`) builds the mission plan from this
    template, so the chain is defined exactly once (review §3.1 collapsed the
    duplicate definitions that previously lived in both the planner and here).
    """
    return GraphTemplate(
        template_id="triage-readonly",
        description="Normalize a source issue and perform read-only triage and planning.",
        nodes=(
            GraphNodeSpec(
                "ticket_analyst",
                "ticket_analyst",
                title="Normalize source issue",
                objective="Normalize the provider issue into a canonical security casefile.",
            ),
            GraphNodeSpec(
                "repo_analyst",
                "repo_analyst",
                title="Collect repository evidence",
                objective=(
                    "Resolve repository context and verify the referenced file path when available."
                ),
                depends_on=("ticket_analyst",),
            ),
            GraphNodeSpec(
                "security_reviewer",
                "security_reviewer",
                title="Adjudicate finding",
                objective=(
                    "Decide whether the finding is stale, false positive, already fixed, "
                    "duplicate, or open."
                ),
                depends_on=("repo_analyst",),
            ),
            GraphNodeSpec(
                "risk_auditor",
                "risk_auditor",
                title="Assess risk and automation eligibility",
                objective="Classify risk, impact, and whether automation can proceed safely.",
                depends_on=("security_reviewer",),
            ),
            GraphNodeSpec(
                "solutions_architect",
                "solutions_architect",
                title="Design bounded remediation plan",
                objective="Create a minimal safe remediation strategy and approval boundary.",
                depends_on=("risk_auditor",),
            ),
            GraphNodeSpec(
                "test_engineer",
                "test_engineer",
                title="Prepare validation checklist",
                objective=(
                    "Define validation checks and determine whether the casefile is "
                    "ready for review."
                ),
                depends_on=("solutions_architect",),
            ),
        ),
        max_steps=12,
        max_concurrency=1,
    )


def graph_registry() -> dict[str, Callable[[], GraphTemplate]]:
    return {"triage-readonly": triage_readonly_graph}
