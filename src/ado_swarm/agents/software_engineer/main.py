from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import ExecutionResult, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class SoftwareEngineerAgent(CasefileAgent):
    """Model-driven: applies the planned remediation in an isolated sandbox via the
    write-capable `apply_remediation_change` tool, which is approval-gated."""

    section_field: ClassVar[str] = "execution"
    section_model: ClassVar[type[BaseModel] | None] = ExecutionResult
    tool_names: ClassVar[list[str]] = ["apply_remediation_change"]
    write_tool_names: ClassVar[list[str]] = ["apply_remediation_change"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        finding = (
            casefile.normalized_finding.model_dump_json(indent=2)
            if casefile.normalized_finding
            else "{}"
        )
        plan = (
            casefile.remediation_plan.model_dump_json(indent=2)
            if casefile.remediation_plan
            else "null"
        )
        return (
            "Apply the planned remediation in an isolated sandbox by calling "
            "apply_remediation_change with the finding and remediation plan. If the change tool "
            "is denied (approval required), report applied=false and that approval is needed.\n\n"
            f"Finding:\n{finding}\n\nRemediation plan:\n{plan}"
        )


def build_agent(model_gateway: ModelGateway) -> SoftwareEngineerAgent:
    return SoftwareEngineerAgent(
        agent_id="software_engineer",
        display_name="Software Engineer",
        model_gateway=model_gateway,
    )
