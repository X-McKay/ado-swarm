"""Bounded swarm cell — multi-perspective ensemble + judge inside one activity.

This is the Phase 1.5 mechanism (ADR-0009 / plan §8-D1): several reviewer agents
each argue one perspective, then a judge reconciles them into a single typed
result. It stays inside one Temporal activity (the cell returns one typed object;
Temporal still sees one task), and is *bounded* by a hard budget cap so the
ensemble cannot run away — an ensemble+judge is ~Nx the cost of a single agent.

The cell reuses `run_model_agent`, so reviewers and the judge go through the same
tool-policy gate and skill machinery as every other agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel
from strands.models import Model

from ado_swarm.agents.model_runtime import ModelAgentRun, run_model_agent
from ado_swarm.tools.policy import ToolContext


@dataclass(frozen=True)
class Reviewer:
    """One perspective in the ensemble."""

    name: str
    system_prompt: str
    reasoning_prompt: str
    tool_names: list[str] = field(default_factory=list)
    skill_names: list[str] = field(default_factory=list)


@dataclass
class SwarmCellResult:
    section: BaseModel | None
    reviewer_positions: dict[str, dict]
    transcript: list[dict]
    input_tokens: int
    output_tokens: int
    model_calls: int
    budget_exceeded: bool
    activated_skills: list[str]
    tools_allowed: list[str]


class BudgetExceededError(RuntimeError):
    """Raised when the swarm cell hits its hard model-call budget."""


async def run_adjudication_cell(
    *,
    model: Model,
    reviewers: list[Reviewer],
    judge_output_model: type[BaseModel],
    judge_system_prompt: str,
    judge_reasoning_prompt: str,
    judge_tool_names: list[str],
    judge_skill_names: list[str],
    tool_context: ToolContext,
    max_model_calls: int = 8,
) -> SwarmCellResult:
    """Run the reviewer ensemble then the judge, bounded by ``max_model_calls``.

    Each reviewer produces its own ``judge_output_model``-shaped position; the
    judge sees all positions (folded into its prompt) and emits the final typed
    section. The budget counts every model call across reviewers + judge; if a
    step would exceed it, the cell stops and raises ``BudgetExceededError`` so the
    activity fails fast rather than burning unbounded tokens.
    """
    transcript: list[dict] = []
    positions: dict[str, dict] = {}
    input_tokens = output_tokens = model_calls = 0
    activated: list[str] = []
    tools_allowed: list[str] = []

    runs: list[tuple[str, ModelAgentRun]] = []
    for reviewer in reviewers:
        if model_calls >= max_model_calls:
            raise BudgetExceededError(
                f"swarm cell exceeded {max_model_calls} model calls before judge"
            )
        run = await run_model_agent(
            model=model,
            tool_names=reviewer.tool_names,
            skill_names=reviewer.skill_names,
            system_prompt=reviewer.system_prompt,
            reasoning_prompt=reviewer.reasoning_prompt,
            output_model=judge_output_model,
            output_prompt=f"State your position as {reviewer.name}.",
            tool_context=tool_context,
        )
        runs.append((reviewer.name, run))
        model_calls += max(run.model_calls, 1)
        input_tokens += run.input_tokens
        output_tokens += run.output_tokens
        activated.extend(run.activated_skills)
        tools_allowed.extend(run.policy_outcome.allowed)
        position = run.section.model_dump(mode="json") if run.section else {}
        positions[reviewer.name] = position
        transcript.append({"reviewer": reviewer.name, "position": position})

    if model_calls >= max_model_calls:
        raise BudgetExceededError(
            f"swarm cell exhausted {max_model_calls} model calls before the judge could run"
        )

    positions_block = "\n".join(f"- {name}: {position}" for name, position in positions.items())
    judge_run = await run_model_agent(
        model=model,
        tool_names=judge_tool_names,
        skill_names=judge_skill_names,
        system_prompt=judge_system_prompt,
        reasoning_prompt=(
            f"{judge_reasoning_prompt}\n\nReviewer positions to reconcile:\n{positions_block}"
        ),
        output_model=judge_output_model,
        output_prompt="Reconcile the reviewer positions into the final decision.",
        tool_context=tool_context,
    )
    model_calls += max(judge_run.model_calls, 1)
    input_tokens += judge_run.input_tokens
    output_tokens += judge_run.output_tokens
    activated.extend(judge_run.activated_skills)
    tools_allowed.extend(judge_run.policy_outcome.allowed)
    transcript.append(
        {
            "judge": True,
            "decision": judge_run.section.model_dump(mode="json") if judge_run.section else {},
        }
    )

    return SwarmCellResult(
        section=judge_run.section,
        reviewer_positions=positions,
        transcript=transcript,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model_calls=model_calls,
        budget_exceeded=False,
        activated_skills=sorted(set(activated)),
        tools_allowed=sorted(set(tools_allowed)),
    )
