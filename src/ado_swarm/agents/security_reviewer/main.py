from __future__ import annotations

import json
from dataclasses import dataclass

from ado_swarm.agents.base import BaseAgent
from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.contracts.casefile import FindingAdjudication
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway


@dataclass
class SecurityReviewerAgent(BaseAgent):
    async def run(self, invocation: AgentInvocation) -> AgentResult:
        casefile = casefile_from_invocation(invocation)
        if casefile is None or casefile.normalized_finding is None:
            return await super().run(invocation)
        finding = casefile.normalized_finding
        evidence = casefile.repository_evidence
        stale = bool(finding.file_path and evidence and evidence.file_exists is False)
        false_positive = finding.confidence < 0.5
        already_fixed = stale
        confidence = 0.85 if stale or false_positive else min(0.9, max(0.55, finding.confidence))
        rationale_parts = []
        if stale:
            rationale_parts.append("repository evidence indicates the referenced file is absent")
        if false_positive:
            rationale_parts.append("normalization confidence is below adjudication threshold")
        if not rationale_parts:
            rationale_parts.append(
                "repository evidence does not prove the finding is stale or false positive"
            )
        casefile.adjudication = FindingAdjudication(
            stale=stale,
            false_positive=false_positive,
            already_fixed=already_fixed,
            duplicate_of=None,
            rationale="; ".join(rationale_parts),
            confidence=confidence,
        )
        if stale:
            casefile.final_disposition = "stale"
        elif false_positive:
            casefile.final_disposition = "false_positive"
        else:
            casefile.final_disposition = "open"
        casefile.audit["security_reviewer"] = casefile.adjudication.model_dump(mode="json")
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"Adjudicated finding {finding.finding_id} as {casefile.final_disposition}.",
            rationale=json.dumps(casefile.audit["security_reviewer"], indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer="security_reviewer")],
            activated_skills=self.skills,
            requested_tools=invocation.task.allowed_tools,
        )


def build_agent(model_gateway: ModelGateway) -> SecurityReviewerAgent:
    return SecurityReviewerAgent(
        agent_id="security_reviewer",
        display_name="Security Reviewer",
        skills=[
            "stale-finding-adjudication",
            "duplicate-finding-adjudication",
            "false-positive-evidence-review",
        ],
        model_gateway=model_gateway,
    )
