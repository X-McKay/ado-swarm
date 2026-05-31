from __future__ import annotations

import json
from dataclasses import dataclass

from ado_swarm.agents.base import BaseAgent
from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway


@dataclass
class TestEngineerAgent(BaseAgent):
    async def run(self, invocation: AgentInvocation) -> AgentResult:
        casefile = casefile_from_invocation(invocation)
        if casefile is None or casefile.normalized_finding is None:
            return await super().run(invocation)
        finding = casefile.normalized_finding
        plan = casefile.remediation_plan
        verification = {
            "finding_id": finding.finding_id,
            "strategy": plan.strategy if plan else None,
            "recommended_checks": [],
            "draft_pr_ready": False,
        }
        if finding.file_path:
            verification["recommended_checks"].append(
                f"targeted test or scanner coverage for {finding.file_path}"
            )
        if finding.package_name:
            verification["recommended_checks"].append(
                f"dependency resolution check for {finding.package_name}"
            )
        verification["recommended_checks"].append("full project quality gate before PR creation")
        verification["draft_pr_ready"] = bool(plan and not plan.requires_human_approval)
        if verification["draft_pr_ready"]:
            casefile.final_disposition = "ready_for_review"
        casefile.audit["test_engineer"] = verification
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"Prepared validation checklist for {finding.finding_id}.",
            rationale=json.dumps(verification, indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer="test_engineer")],
            activated_skills=self.skills,
            requested_tools=invocation.task.allowed_tools,
            requires_approval=not verification["draft_pr_ready"],
        )


def build_agent(model_gateway: ModelGateway) -> TestEngineerAgent:
    return TestEngineerAgent(
        agent_id="test_engineer",
        display_name="Test Engineer",
        skills=[
            "test-and-build-validation",
            "security-fix-verification",
            "pull-request-preparation",
        ],
        model_gateway=model_gateway,
    )
