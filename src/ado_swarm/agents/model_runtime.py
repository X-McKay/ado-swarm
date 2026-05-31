"""Shared model-agent runtime: build a Strands agent (tools + skills + policy gate)
and run one non-deprecated structured-output invocation.

Both `CasefileAgent` and standalone model agents (e.g. data_analyst) use this so
the Strands plumbing lives in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from strands import Agent
from strands.models import Model

from ado_swarm.skills.runtime import build_skills_plugin
from ado_swarm.tools.catalog import get_tools
from ado_swarm.tools.policy import ToolContext, ToolPolicy
from ado_swarm.tools.policy_hook import PolicyOutcome, ToolPolicyHook


@dataclass
class ModelAgentRun:
    section: BaseModel | None
    available_skills: list[str]
    activated_skills: list[str]
    policy_outcome: PolicyOutcome


async def run_model_agent(
    *,
    model: Model,
    tool_names: list[str],
    skill_names: list[str],
    system_prompt: str,
    reasoning_prompt: str,
    output_model: type[BaseModel],
    output_prompt: str,
    tool_context: ToolContext,
    write_tool_names: list[str] | None = None,
) -> ModelAgentRun:
    policy = ToolPolicy(tool_names, write_tools=write_tool_names or [])
    # The forced structured-output tool is named after the output model; it is
    # harness machinery and must bypass the domain tool policy.
    hook = ToolPolicyHook(policy, tool_context, harness_tools={output_model.__name__})
    plugin = build_skills_plugin(skill_names)
    agent = Agent(
        model=model,
        tools=get_tools(tool_names),
        plugins=[plugin] if plugin else [],
        hooks=[hook],
        system_prompt=system_prompt,
        callback_handler=None,
    )
    result = await agent.invoke_async(
        reasoning_prompt,
        structured_output_model=output_model,
        structured_output_prompt=output_prompt,
    )
    return ModelAgentRun(
        section=result.structured_output,
        available_skills=[s.name for s in plugin.get_available_skills()] if plugin else [],
        activated_skills=plugin.get_activated_skills(agent) if plugin else [],
        policy_outcome=hook.outcome,
    )
