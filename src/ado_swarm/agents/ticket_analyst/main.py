from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import NormalizedFinding, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class TicketAnalystAgent(CasefileAgent):
    """Model-driven: reasons over a messy provider issue, calls the deterministic
    `normalize_finding` tool for the baseline, and emits a canonical finding."""

    section_field: ClassVar[str] = "normalized_finding"
    section_model: ClassVar[type[BaseModel] | None] = NormalizedFinding
    tool_names: ClassVar[list[str]] = ["normalize_finding"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            "Normalize this provider security issue into a canonical finding. Call the "
            "normalize_finding tool with the source issue to get the deterministic baseline, "
            "then reconcile anything ambiguous or missing.\n\n"
            f"Source issue:\n{casefile.source_issue.model_dump_json(indent=2)}"
        )


def build_agent(model_gateway: ModelGateway) -> TicketAnalystAgent:
    return TicketAnalystAgent(
        agent_id="ticket_analyst",
        display_name="Ticket Analyst",
        model_gateway=model_gateway,
    )
