from __future__ import annotations

from dataclasses import dataclass

from ado_swarm.contracts.mission import AgentInvocation
from ado_swarm.model_gateway.gateway import ModelGateway


@dataclass
class StrandsRuntimeResult:
    text: str
    telemetry: dict


class StrandsAgentRuntime:
    """Optional Strands-backed runtime adapter with graceful fallback.

    The repository keeps the existing AgentResult contracts stable while enabling
    gradual adoption of Strands features. If `strands` is unavailable or an agent
    has not yet opted into native Strands tools, this adapter falls back to the
    configured ModelGateway.
    """

    def __init__(self, model_gateway: ModelGateway) -> None:
        self.model_gateway = model_gateway

    async def run_text(
        self, invocation: AgentInvocation, system_prompt: str
    ) -> StrandsRuntimeResult:
        prompt = (
            f"{system_prompt}\n\n"
            f"Task: {invocation.task.title}\n"
            f"Objective: {invocation.task.objective}\n"
            f"Constraints: {invocation.task.constraints}\n"
        )
        try:
            from strands import Agent
        except Exception:
            text = await self.model_gateway.complete(prompt)
            return StrandsRuntimeResult(text=text, telemetry={"runtime": "model_gateway_fallback"})

        try:
            agent = Agent(system_prompt=system_prompt)
            result = agent(prompt)
            return StrandsRuntimeResult(text=str(result), telemetry={"runtime": "strands"})
        except Exception:
            text = await self.model_gateway.complete(prompt)
            return StrandsRuntimeResult(text=text, telemetry={"runtime": "strands_fallback"})
