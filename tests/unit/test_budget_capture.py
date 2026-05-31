"""Token / budget capture from the real Strands event loop.

These tests prove that real token usage flows from the Strands ``AgentResult``
metrics through ``run_model_agent`` and onto ``AgentResult.budget_usage`` for the
model-driven agents. They are hermetic: the offline ``FakeModel`` drives the real
Strands loop and emits a ``metadata`` event carrying non-zero usage, exactly as a
real provider would.
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from ado_swarm.agents.data_analyst.main import DataAnalystAgent
from ado_swarm.agents.eval_support import eval_invocation
from ado_swarm.agents.model_runtime import run_model_agent
from ado_swarm.contracts.budget import BudgetUsage
from ado_swarm.contracts.events import TaskState
from ado_swarm.model_gateway.gateway import ModelGateway, ModelProfile
from ado_swarm.model_gateway.strands_models import FakeModel
from ado_swarm.tools.policy import ToolContext


class _Note(BaseModel):
    """Trivial structured-output section model for the harness."""

    note: str = ""


def test_run_model_agent_captures_usage() -> None:
    """run_model_agent surfaces real input/output tokens from AgentResult.metrics."""
    model = FakeModel(default_text="a moderately long answer that costs some tokens")

    run = asyncio.run(
        run_model_agent(
            model=model,
            tool_names=[],
            skill_names=[],
            system_prompt="you are a test agent",
            reasoning_prompt="think about something with enough text to cost input tokens",
            output_model=_Note,
            output_prompt="produce the note",
            tool_context=ToolContext(run_id="run-1", task_id="task-1", agent_id="tester"),
        )
    )

    assert run.input_tokens > 0
    assert run.output_tokens > 0
    # FakeModel runs at least the reasoning turn plus the forced structured-output
    # turn, so the event loop reports a positive cycle/model-call count.
    assert run.model_calls > 0


def test_data_analyst_budget_usage_has_tokens() -> None:
    """DataAnalystAgent.run populates BudgetUsage with the captured token counts."""
    invocation = eval_invocation(
        "data_analyst",
        objective="Mine findings for campaign patterns.",
        constraints={"findings": []},
    )
    agent = DataAnalystAgent(
        agent_id="data_analyst",
        display_name="Data Analyst",
        model_gateway=ModelGateway(ModelProfile(provider="fake")),
        model=FakeModel(default_text="a longer deterministic answer for token capture"),
    )

    result = asyncio.run(agent.run(invocation))

    assert result.state is TaskState.COMPLETED
    assert isinstance(result.budget_usage, BudgetUsage)
    assert result.budget_usage.input_tokens > 0
    assert result.budget_usage.output_tokens > 0
    assert result.budget_usage.model_calls >= 1
