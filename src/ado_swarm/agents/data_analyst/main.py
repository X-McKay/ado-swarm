from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import ClassVar

from strands.models import Model

from ado_swarm.agents.model_runtime import run_model_agent
from ado_swarm.contracts.analytics import CampaignReport
from ado_swarm.contracts.budget import BudgetUsage
from ado_swarm.contracts.events import ArtifactRef, TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway
from ado_swarm.model_gateway.strands_models import build_strands_model
from ado_swarm.tools.policy import ToolContext


@dataclass
class DataAnalystAgent:
    """Model-driven analytics agent. Unlike the casefile agents it does not enrich a
    casefile; it mines a set of findings for campaign patterns and emits a typed
    CampaignReport artifact."""

    agent_id: str
    display_name: str
    model_gateway: ModelGateway
    skill_names: list[str] = field(default_factory=list)
    model: Model | None = None

    tool_names: ClassVar[list[str]] = ["summarize_findings"]

    async def run(self, invocation: AgentInvocation) -> AgentResult:
        started = perf_counter()
        findings = invocation.task.constraints.get("findings", [])
        model = self.model or build_strands_model(self.model_gateway.profile)
        run = await run_model_agent(
            model=model,
            tool_names=self.tool_names,
            skill_names=self.skill_names,
            system_prompt=(
                f"You are {self.display_name}. Mine the provided findings for campaign patterns "
                "and produce an accurate, auditable analytics report."
            ),
            reasoning_prompt=(
                "Summarize these findings into a campaign report. Call summarize_findings for "
                "the deterministic counts, then add recommendations.\n\n"
                f"Findings:\n{json.dumps(findings, indent=2)}"
            ),
            output_model=CampaignReport,
            output_prompt="Produce the campaign report.",
            tool_context=ToolContext(
                run_id=invocation.run_id,
                task_id=invocation.task.task_id,
                agent_id=self.agent_id,
            ),
        )
        report = run.section if isinstance(run.section, CampaignReport) else CampaignReport()
        usage = BudgetUsage(agent_loops=1, model_calls=1, elapsed_seconds=perf_counter() - started)
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"{self.display_name} produced a campaign report over {report.total_findings} "
            "findings.",
            rationale=json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True),
            artifact_refs=[
                ArtifactRef(
                    name="campaign_report.json",
                    media_type="application/json",
                    uri=f"memory://reports/{invocation.run_id}",
                    metadata={"campaign_report": report.model_dump(mode="json")},
                )
            ],
            activated_skills=run.activated_skills or run.available_skills,
            requested_tools=run.policy_outcome.allowed,
            budget_usage=usage,
        )


def build_agent(model_gateway: ModelGateway) -> DataAnalystAgent:
    return DataAnalystAgent(
        agent_id="data_analyst",
        display_name="Data Analyst",
        model_gateway=model_gateway,
    )
