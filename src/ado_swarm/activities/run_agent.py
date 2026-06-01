from __future__ import annotations

from temporalio import activity

from ado_swarm.agents.registry import build_agent
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.storage.providers import get_checkpoint_store


@activity.defn(name="run_agent")
async def run_agent(invocation: AgentInvocation) -> AgentResult:
    agent = build_agent(invocation.task.agent_id or invocation.task.capability)
    result = await agent.run(invocation)
    try:
        store = get_checkpoint_store()
        for checkpoint in result.checkpoints:
            await store.append(checkpoint)
    except Exception as exc:
        # Checkpoint persistence must not mask a completed agent result.
        result.telemetry["checkpoint_persistence_error"] = f"{type(exc).__name__}: {exc}"
    return result
