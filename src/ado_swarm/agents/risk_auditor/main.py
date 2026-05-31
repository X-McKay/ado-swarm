from __future__ import annotations

import json
from dataclasses import dataclass

from ado_swarm.agents.base import BaseAgent
from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.contracts.casefile import RiskClassification
from ado_swarm.contracts.events import RiskLevel, TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway

SEVERITY_TO_RISK = {
    "critical": RiskLevel.CRITICAL,
    "high": RiskLevel.HIGH,
    "medium": RiskLevel.MEDIUM,
    "moderate": RiskLevel.MEDIUM,
    "low": RiskLevel.LOW,
}


@dataclass
class RiskAuditorAgent(BaseAgent):
    async def run(self, invocation: AgentInvocation) -> AgentResult:
        casefile = casefile_from_invocation(invocation)
        if casefile is None or casefile.normalized_finding is None:
            return await super().run(invocation)
        finding = casefile.normalized_finding
        risk_level = SEVERITY_TO_RISK.get((finding.severity or "").lower(), RiskLevel.MEDIUM)
        if finding.category == "sast" and finding.cwe in {"CWE-89", "CWE-78", "CWE-22"}:
            risk_level = RiskLevel.HIGH if risk_level != RiskLevel.CRITICAL else risk_level
        stale_or_false_positive = bool(
            casefile.adjudication
            and (casefile.adjudication.stale or casefile.adjudication.false_positive)
        )
        automation_eligible = (
            risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}
            and not stale_or_false_positive
            and bool(
                casefile.repository_evidence
                and casefile.repository_evidence.file_exists is not False
            )
        )
        impact = (
            f"{finding.category or 'security'} finding with severity "
            f"{finding.severity or 'unknown'}"
        )
        rationale = (
            "Automation is allowed for bounded low/medium findings with repository evidence."
            if automation_eligible
            else (
                "Human review is required because severity, adjudication, or repository "
                "evidence prevents automation."
            )
        )
        casefile.risk = RiskClassification(
            risk_level=risk_level,
            impact=impact,
            automation_eligible=automation_eligible,
            confidence=0.85 if finding.severity else 0.6,
            rationale=rationale,
        )
        if not automation_eligible and casefile.final_disposition == "open":
            casefile.final_disposition = "needs_human"
        casefile.audit["risk_auditor"] = casefile.risk.model_dump(mode="json")
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"Classified risk for {finding.finding_id} as {risk_level.value}.",
            rationale=json.dumps(casefile.audit["risk_auditor"], indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer="risk_auditor")],
            activated_skills=self.skills,
            requested_tools=invocation.task.allowed_tools,
            requires_approval=not automation_eligible,
        )


def build_agent(model_gateway: ModelGateway) -> RiskAuditorAgent:
    return RiskAuditorAgent(
        agent_id="risk_auditor",
        display_name="Risk Auditor",
        skills=[
            "security-risk-scoring",
            "change-impact-classification",
            "automation-eligibility-assessment",
        ],
        model_gateway=model_gateway,
    )
