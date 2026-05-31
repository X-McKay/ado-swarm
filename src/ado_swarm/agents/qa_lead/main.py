from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import ReadinessVerdict, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class QaLeadAgent(CasefileAgent):
    """Model-driven: decides whether a casefile is ready to advance to the next
    phase, calling the deterministic `assess_readiness` tool as a baseline."""

    section_field: ClassVar[str] = "readiness"
    section_model: ClassVar[type[BaseModel] | None] = ReadinessVerdict
    tool_names: ClassVar[list[str]] = ["assess_readiness"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            "Decide whether this casefile is ready to advance to the next phase, and which "
            "phase. Call assess_readiness with the casefile for the baseline, then decide.\n\n"
            f"Casefile:\n{casefile.model_dump_json(indent=2)}"
        )


def build_agent(model_gateway: ModelGateway) -> QaLeadAgent:
    return QaLeadAgent(
        agent_id="qa_lead",
        display_name="QA Lead",
        model_gateway=model_gateway,
    )
