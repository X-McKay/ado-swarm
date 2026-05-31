from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphNodeSpec:
    node_id: str
    agent_id: str
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
    return GraphTemplate(
        template_id="triage-readonly",
        description="Normalize a source issue and perform initial read-only triage.",
        nodes=(
            GraphNodeSpec("ticket", "ticket_analyst"),
            GraphNodeSpec("repo", "repo_analyst", depends_on=("ticket",)),
            GraphNodeSpec("security", "security_reviewer", depends_on=("repo",)),
            GraphNodeSpec("risk", "risk_auditor", depends_on=("security",)),
        ),
        max_steps=8,
        max_concurrency=1,
    )


def graph_registry() -> dict[str, Callable[[], GraphTemplate]]:
    return {"triage-readonly": triage_readonly_graph}
