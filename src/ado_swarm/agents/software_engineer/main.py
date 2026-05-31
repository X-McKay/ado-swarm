from __future__ import annotations

from ado_swarm.agents.base import BaseAgent
from ado_swarm.model_gateway.gateway import ModelGateway


def build_agent(model_gateway: ModelGateway) -> BaseAgent:
    return BaseAgent(
        agent_id="software_engineer",
        display_name="Software Engineer",
        skills=["dependency-remediation-execution"],
        model_gateway=model_gateway,
    )
