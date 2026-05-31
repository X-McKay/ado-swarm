from __future__ import annotations

import json
from dataclasses import dataclass

from ado_swarm.agents.base import BaseAgent
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.events import ArtifactRef, TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.model_gateway.gateway import ModelGateway


@dataclass
class TicketAnalystAgent(BaseAgent):
    async def run(self, invocation: AgentInvocation) -> AgentResult:
        raw_issue = invocation.task.constraints.get("source_issue")
        if raw_issue is None:
            return await super().run(invocation)
        issue = SourceIssue.model_validate(raw_issue)
        casefile = build_casefile(invocation.run_id, issue)
        casefile_payload = casefile.model_dump(mode="json")
        finding_id = (
            casefile.normalized_finding.finding_id if casefile.normalized_finding else "unknown"
        )
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"Normalized provider issue into canonical finding {finding_id}.",
            rationale=json.dumps(
                {
                    "casefile_id": casefile.casefile_id,
                    "finding": casefile.normalized_finding.model_dump(mode="json")
                    if casefile.normalized_finding
                    else None,
                    "audit": casefile.audit.get("ticket_analyst", {}),
                },
                indent=2,
                sort_keys=True,
            ),
            artifact_refs=[
                ArtifactRef(
                    name=f"{casefile.casefile_id}.json",
                    media_type="application/json",
                    uri=f"memory://casefiles/{casefile.casefile_id}",
                    metadata={"casefile": casefile_payload},
                )
            ],
            activated_skills=self.skills,
            requested_tools=invocation.task.allowed_tools,
        )


def build_agent(model_gateway: ModelGateway) -> TicketAnalystAgent:
    return TicketAnalystAgent(
        agent_id="ticket_analyst",
        display_name="Ticket Analyst",
        skills=[
            "security-ticket-normalization",
            "finding-type-classification",
            "scanner-finding-fingerprinting",
        ],
        model_gateway=model_gateway,
    )
