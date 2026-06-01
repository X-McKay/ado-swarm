from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import RiskClassification, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class RiskAuditorAgent(CasefileAgent):
    """Model-driven: scores risk and automation eligibility, using the deterministic
    `score_severity` tool as a baseline it can adopt or override with rationale."""

    section_field: ClassVar[str] = "risk"
    section_model: ClassVar[type[BaseModel] | None] = RiskClassification
    tool_names: ClassVar[list[str]] = ["score_severity"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        finding = (
            casefile.normalized_finding.model_dump_json(indent=2)
            if casefile.normalized_finding
            else "{}"
        )
        return (
            "Assess the security risk, impact, and automation eligibility of this finding. "
            "Call score_severity for the deterministic baseline, then decide, accounting for "
            "any adjudication or repository evidence already in the casefile.\n\n"
            f"Finding:\n{finding}"
        )


def build_agent(model_gateway: ModelGateway) -> RiskAuditorAgent:
    return RiskAuditorAgent(
        agent_id="risk_auditor",
        display_name="Risk Auditor",
        model_gateway=model_gateway,
    )
