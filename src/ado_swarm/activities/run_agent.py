from __future__ import annotations

from ado_swarm.agents.registry import build_agent
from ado_swarm.contracts.mission import AgentInvocation, AgentResult


async def run_agent(invocation: AgentInvocation) -> AgentResult:
    agent = build_agent(invocation.task.agent_id or invocation.task.capability)
    return await agent.run(invocation)
