from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import FindingAdjudication, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class SecurityReviewerAgent(CasefileAgent):
    """Model-driven: adjudicates whether a finding is stale, false-positive, duplicate,
    or open, calling the deterministic `adjudication_signals` tool as a baseline."""

    section_field: ClassVar[str] = "adjudication"
    section_model: ClassVar[type[BaseModel] | None] = FindingAdjudication
    tool_names: ClassVar[list[str]] = ["adjudication_signals"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        finding = (
            casefile.normalized_finding.model_dump_json(indent=2)
            if casefile.normalized_finding
            else "{}"
        )
        evidence = (
            casefile.repository_evidence.model_dump_json(indent=2)
            if casefile.repository_evidence
            else "null"
        )
        return (
            "Adjudicate this finding (stale / false-positive / already-fixed / duplicate / open). "
            "Call adjudication_signals with the finding and repository evidence for the baseline, "
            "then decide.\n\n"
            f"Finding:\n{finding}\n\nRepository evidence:\n{evidence}"
        )


def build_agent(model_gateway: ModelGateway) -> SecurityReviewerAgent:
    return SecurityReviewerAgent(
        agent_id="security_reviewer",
        display_name="Security Reviewer",
        model_gateway=model_gateway,
    )
