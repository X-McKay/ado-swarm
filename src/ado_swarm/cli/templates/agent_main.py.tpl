from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import ${section_model}, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class ${class_name}(CasefileAgent):
    section_field: ClassVar[str] = "${section_field}"
    section_model: ClassVar[type[BaseModel] | None] = ${section_model}
    tool_names: ClassVar[list[str]] = ["${tool}"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            "Analyze the casefile, call ${tool} for deterministic evidence, and produce "
            "the ${section_field} section.\n\n"
            f"Casefile:\n{casefile.model_dump_json(indent=2)}"
        )


def build_agent(model_gateway: ModelGateway) -> ${class_name}:
    return ${class_name}(agent_id="${agent_id}", display_name="${display}", model_gateway=model_gateway)
