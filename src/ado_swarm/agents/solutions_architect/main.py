from __future__ import annotations

from ado_swarm.agents.base import BaseAgent
from ado_swarm.model_gateway.gateway import ModelGateway


def build_agent(model_gateway: ModelGateway) -> BaseAgent:
    return BaseAgent(
        agent_id="solutions_architect",
        display_name="Solutions Architect",
        skills=["fix-plan-generation"],
        model_gateway=model_gateway,
    )
