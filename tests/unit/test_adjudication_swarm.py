from __future__ import annotations

import json
from pathlib import Path

import pytest

from ado_swarm.agents.eval_support import eval_invocation
from ado_swarm.agents.registry import build_agent
from ado_swarm.agents.swarm_cell import (
    BudgetExceededError,
    Reviewer,
    run_adjudication_cell,
)
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import FindingAdjudication
from ado_swarm.contracts.events import TaskState
from ado_swarm.model_gateway.gateway import ModelGateway, ModelProfile
from ado_swarm.model_gateway.strands_models import FakeModel
from ado_swarm.tools.policy import ToolContext
from ado_swarm.contracts.source_provider import SourceIssue

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "source_issues" / "codeql_sast.json"


def _judge_decision() -> FindingAdjudication:
    return FindingAdjudication(
        stale=False,
        false_positive=False,
        already_fixed=False,
        rationale="Panel reconciled: finding is open and exploitable.",
        confidence=0.82,
    )


def _reviewers() -> list[Reviewer]:
    return [
        Reviewer(name="stale_reviewer", system_prompt="s", reasoning_prompt="r"),
        Reviewer(name="false_positive_reviewer", system_prompt="s", reasoning_prompt="r"),
        Reviewer(name="duplicate_reviewer", system_prompt="s", reasoning_prompt="r"),
    ]


async def test_adjudication_cell_runs_ensemble_then_judge() -> None:
    fake = FakeModel(
        default_text="position",
        structured_outputs={FindingAdjudication: _judge_decision()},
    )
    result = await run_adjudication_cell(
        model=fake,
        reviewers=_reviewers(),
        judge_output_model=FindingAdjudication,
        judge_system_prompt="judge",
        judge_reasoning_prompt="reconcile",
        judge_tool_names=[],
        judge_skill_names=[],
        tool_context=ToolContext(run_id="r1"),
        max_model_calls=8,
    )
    assert isinstance(result.section, FindingAdjudication)
    # 3 reviewers + 1 judge each emit a position
    assert set(result.reviewer_positions) == {
        "stale_reviewer",
        "false_positive_reviewer",
        "duplicate_reviewer",
    }
    assert result.transcript[-1].get("judge") is True
    assert result.model_calls >= 4


async def test_adjudication_cell_enforces_budget() -> None:
    fake = FakeModel(structured_outputs={FindingAdjudication: _judge_decision()})
    with pytest.raises(BudgetExceededError):
        await run_adjudication_cell(
            model=fake,
            reviewers=_reviewers(),  # 3 reviewers
            judge_output_model=FindingAdjudication,
            judge_system_prompt="judge",
            judge_reasoning_prompt="reconcile",
            judge_tool_names=[],
            judge_skill_names=[],
            tool_context=ToolContext(run_id="r1"),
            max_model_calls=2,  # cannot fit 3 reviewers + judge
        )


async def test_security_reviewer_swarm_mode_produces_adjudication() -> None:
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    casefile = build_casefile("eval-run", issue)
    fake = FakeModel(
        default_text="position",
        structured_outputs={FindingAdjudication: _judge_decision()},
    )
    agent = build_agent(
        "security_reviewer", model_gateway=ModelGateway(ModelProfile(provider="fake"))
    )
    agent.model = fake
    invocation = eval_invocation(
        "security_reviewer",
        objective="Adjudicate via swarm.",
        constraints={"casefile": casefile.model_dump(mode="json"), "use_swarm": True},
    )
    result = await agent.run(invocation)
    assert result.state == TaskState.COMPLETED
    casefile_out = result.artifact_refs[0].metadata["casefile"]
    assert casefile_out["adjudication"] is not None
    assert casefile_out["audit"]["security_reviewer"]["mode"] == "swarm"


async def test_security_reviewer_defaults_to_single_agent() -> None:
    # Without use_swarm, the audit should not be in swarm mode.
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    casefile = build_casefile("eval-run", issue)
    fake = FakeModel(structured_outputs={FindingAdjudication: _judge_decision()})
    agent = build_agent(
        "security_reviewer", model_gateway=ModelGateway(ModelProfile(provider="fake"))
    )
    agent.model = fake
    invocation = eval_invocation(
        "security_reviewer",
        objective="Adjudicate.",
        constraints={"casefile": casefile.model_dump(mode="json")},
    )
    result = await agent.run(invocation)
    assert result.state == TaskState.COMPLETED
    audit = result.artifact_refs[0].metadata["casefile"]["audit"]["security_reviewer"]
    assert audit.get("mode") != "swarm"
