from __future__ import annotations

from ado_swarm.agents.base import BaseAgent
from ado_swarm.model_gateway.gateway import ModelGateway


def build_agent(model_gateway: ModelGateway) -> BaseAgent:
    return BaseAgent(
        agent_id="risk_auditor",
        display_name="Risk Auditor",
        skills=["security-risk-scoring"],
        model_gateway=model_gateway,
    )
