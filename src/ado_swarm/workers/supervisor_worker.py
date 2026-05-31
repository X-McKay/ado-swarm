from __future__ import annotations

import asyncio

from temporalio.worker import Worker

from ado_swarm.activities.planning import plan_mission
from ado_swarm.activities.run_agent import run_agent
from ado_swarm.config import get_settings
from ado_swarm.temporal.client import build_temporal_client
from ado_swarm.workflows.agent_task import AgentTaskWorkflow
from ado_swarm.workflows.supervisor import SupervisorWorkflow


async def main() -> None:
    settings = get_settings()
    client = await build_temporal_client(settings)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[SupervisorWorkflow, AgentTaskWorkflow],
        activities=[plan_mission, run_agent],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
