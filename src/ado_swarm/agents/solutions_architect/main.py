from __future__ import annotations

import json
from dataclasses import dataclass

from ado_swarm.agents.base import BaseAgent
from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.contracts.casefile import RemediationPlan
from ado_swarm.contracts.events import RiskLevel, TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway


@dataclass
class SolutionsArchitectAgent(BaseAgent):
    async def run(self, invocation: AgentInvocation) -> AgentResult:
        casefile = casefile_from_invocation(invocation)
        if casefile is None or casefile.normalized_finding is None:
            return await super().run(invocation)
        finding = casefile.normalized_finding
        risk = casefile.risk.risk_level if casefile.risk else RiskLevel.MEDIUM
        if finding.category == "dependency":
            strategy = "dependency_version_update"
            steps = [
                "Locate dependency declaration for "
                f"{finding.package_name or 'the affected package'}.",
                "Select the smallest non-vulnerable version that satisfies project constraints.",
                "Run dependency resolution and targeted tests in an isolated sandbox.",
            ]
        elif finding.category == "sast":
            strategy = "localized_code_fix"
            steps = [
                f"Inspect {finding.file_path or 'the affected file'} around the reported location.",
                "Apply the smallest code change that removes the unsafe data flow.",
                "Run targeted security and unit tests before preparing review output.",
            ]
        else:
            strategy = "manual_investigation"
            steps = [
                "Collect additional evidence for the finding type.",
                "Define a bounded remediation before enabling write actions.",
            ]
        casefile.remediation_plan = RemediationPlan(
            strategy=strategy,
            change_boundary=f"single finding {finding.finding_id}",
            steps=steps,
            requires_human_approval=risk in {RiskLevel.HIGH, RiskLevel.CRITICAL},
        )
        casefile.audit["solutions_architect"] = casefile.remediation_plan.model_dump(mode="json")
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"Prepared {strategy} remediation plan for {finding.finding_id}.",
            rationale=json.dumps(casefile.audit["solutions_architect"], indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer="solutions_architect")],
            activated_skills=self.skills,
            requested_tools=invocation.task.allowed_tools,
            requires_approval=casefile.remediation_plan.requires_human_approval,
        )


def build_agent(model_gateway: ModelGateway) -> SolutionsArchitectAgent:
    return SolutionsArchitectAgent(
        agent_id="solutions_architect",
        display_name="Solutions Architect",
        skills=[
            "fix-plan-generation",
            "remediation-strategy-selection",
            "safe-change-boundary-definition",
        ],
        model_gateway=model_gateway,
    )
