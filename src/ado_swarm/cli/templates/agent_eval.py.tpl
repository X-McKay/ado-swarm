from __future__ import annotations

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult


async def run_eval(model_profile: str = "fake") -> dict:
    invocation = eval_invocation(
        "${agent_id}", objective="Evaluate ${display}.", constraints={}
    )

    def assertion(result: AgentResult) -> bool:
        return result.state == TaskState.COMPLETED

    return await run_agent_eval(
        "${agent_id}", invocation=invocation, model_profile=model_profile, assertion=assertion
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
