from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import SecurityCasefile, ValidationResult
from ado_swarm.model_gateway.gateway import ModelGateway


class TestEngineerAgent(CasefileAgent):
    """Model-driven: defines the validation/build checks and review-readiness for a
    remediation, calling the deterministic `propose_validation_checks` tool."""

    section_field: ClassVar[str] = "validation"
    section_model: ClassVar[type[BaseModel] | None] = ValidationResult
    tool_names: ClassVar[list[str]] = ["propose_validation_checks"]

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
            "Define the validation and build checks needed before this finding is ready for "
            "review, and decide readiness. Call propose_validation_checks with the finding and "
            "remediation plan for the baseline.\n\n"
            f"Finding:\n{finding}\n\nRemediation plan:\n{plan}"
        )


def build_agent(model_gateway: ModelGateway) -> TestEngineerAgent:
    return TestEngineerAgent(
        agent_id="test_engineer",
        display_name="Test Engineer",
        model_gateway=model_gateway,
    )
