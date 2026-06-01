from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import RemediationPlan, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class SolutionsArchitectAgent(CasefileAgent):
    """Model-driven: produces a bounded remediation plan, calling the deterministic
    `propose_remediation_strategy` tool as a baseline."""

    section_field: ClassVar[str] = "remediation_plan"
    section_model: ClassVar[type[BaseModel] | None] = RemediationPlan
    tool_names: ClassVar[list[str]] = ["propose_remediation_strategy"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        finding = (
            casefile.normalized_finding.model_dump_json(indent=2)
            if casefile.normalized_finding
            else "{}"
        )
        risk = casefile.risk.risk_level.value if casefile.risk else "unknown"
        return (
            "Produce a minimal, safe remediation plan for this finding. Call "
            "propose_remediation_strategy for the baseline strategy and steps, then set "
            f"requires_human_approval appropriately (risk level: {risk}).\n\n"
            f"Finding:\n{finding}"
        )


def build_agent(model_gateway: ModelGateway) -> SolutionsArchitectAgent:
    return SolutionsArchitectAgent(
        agent_id="solutions_architect",
        display_name="Solutions Architect",
        model_gateway=model_gateway,
    )
