from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from ado_swarm.agents.risk_auditor.main import build_agent
from ado_swarm.contracts.mission import AgentInvocation, TaskSpec
from ado_swarm.model_gateway.gateway import ModelGateway, ModelProfile


async def run_eval(model_profile: str = "fake") -> dict:
    agent = build_agent(ModelGateway(ModelProfile(provider=model_profile)))
    task = TaskSpec(
        run_id="eval-run",
        title="Evaluate Risk Auditor",
        objective="Run deterministic isolated evaluation for Risk Auditor.",
        capability="risk_auditor",
        agent_id="risk_auditor",
    )
    result = await agent.run(
        AgentInvocation(
            run_id="eval-run",
            task=task,
            context_id="eval",
            plan_version=1,
            idempotency_key=str(uuid4()),
        )
    )
    return {
        "agent_id": "risk_auditor",
        "passed": result.state == "completed",
        "result": result.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-profile", default="fake")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = asyncio.run(run_eval(args.model_profile))
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
