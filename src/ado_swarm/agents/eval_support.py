from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any
from uuid import uuid4

from strands.models import Model

from ado_swarm.agents.registry import build_agent
from ado_swarm.config import get_settings
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult, TaskSpec
from ado_swarm.model_gateway.gateway import ModelGateway, ModelProfile


def build_eval_model_gateway(model_profile: str = "fake") -> ModelGateway:
    """Build eval gateway from the requested provider and environment settings.

    Agent eval entrypoints accept a short provider name for CLI ergonomics. For
    non-fake providers, the concrete model id and base URL must come from the
    normal runtime settings so local OpenAI-compatible, Ollama, LiteLLM, and
    Bedrock profiles work during E2E validation.
    """
    settings = get_settings()
    if model_profile == "fake":
        return ModelGateway(ModelProfile(provider="fake"))
    return ModelGateway(
        ModelProfile(
            provider=model_profile,
            model_id=settings.model_id,
            base_url=settings.model_base_url,
        )
    )


def eval_invocation(agent_id: str, *, objective: str, constraints: dict) -> AgentInvocation:
    """Build a deterministic AgentInvocation for an isolated agent evaluation."""
    task = TaskSpec(
        run_id="eval-run",
        title=f"Evaluate {agent_id}",
        objective=objective,
        capability=agent_id,
        agent_id=agent_id,
        constraints=constraints,
    )
    return AgentInvocation(
        run_id="eval-run",
        task=task,
        context_id="eval",
        plan_version=1,
        idempotency_key=str(uuid4()),
    )


async def run_agent_eval(
    agent_id: str,
    *,
    invocation: AgentInvocation,
    model_profile: str = "fake",
    fake_model: Model | None = None,
    assertion: Callable[[AgentResult], bool] | None = None,
) -> dict:
    """Run one agent in isolation and report a structured eval result.

    The agent is composed through the registry (so skills come from metadata). On
    the deterministic ``fake`` profile a scripted ``FakeModel`` is injected so the
    real Strands agent loop runs offline; on a real profile the configured model
    is used. This single harness replaces the per-agent eval boilerplate.
    """
    agent = build_agent(agent_id, model_gateway=build_eval_model_gateway(model_profile))
    if model_profile == "fake" and fake_model is not None:
        agent.model = fake_model
    result = await agent.run(invocation)
    passed = assertion(result) if assertion else result.state == TaskState.COMPLETED
    return {"agent_id": agent_id, "passed": bool(passed), "result": result.model_dump(mode="json")}


def eval_cli(run_eval: Callable[[str], Coroutine[Any, Any, dict]]) -> None:
    """Standard CLI wrapper shared by every agent's ``eval.py`` ``main()``."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-profile", default="fake")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = asyncio.run(run_eval(args.model_profile))
    text = json.dumps(payload, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    else:
        print(text)
