"""Model-driven casefile agent base — tools in a loop + skills + structured output.

Per `docs/concepts/agents-tools-skills.md`, every agent is a Strands `Agent`
(model + tools in a loop). A `CasefileAgent` reads a `SecurityCasefile`, runs a
real reasoning loop (the model calls deterministic catalog tools through the
policy gate, with skills progressively disclosed), then emits exactly one typed
casefile section via structured output. The deterministic logic the old agents
inlined now lives in the tool catalog.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from time import perf_counter
from typing import ClassVar

from pydantic import BaseModel
from strands import Agent, AgentSkills
from strands.models import Model

from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.contracts.budget import BudgetUsage
from ado_swarm.contracts.casefile import SecurityCasefile
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway
from ado_swarm.model_gateway.strands_models import build_strands_model
from ado_swarm.skills.runtime import build_skills_plugin
from ado_swarm.tools.catalog import get_tools
from ado_swarm.tools.policy import ApprovalState, ToolContext, ToolPolicy
from ado_swarm.tools.policy_hook import ToolPolicyHook


@dataclass
class CasefileAgent:
    agent_id: str
    display_name: str
    model_gateway: ModelGateway
    # Skills are single-sourced from metadata.yaml by the registry.
    skill_names: list[str] = field(default_factory=list)
    # Injected Strands model override for deterministic tests/evals.
    model: Model | None = None

    # --- behavior declared by each agent subclass ---
    section_field: ClassVar[str] = ""
    section_model: ClassVar[type[BaseModel] | None] = None
    tool_names: ClassVar[list[str]] = []

    # ------------------------------------------------------------------
    def system_prompt(self) -> str:
        return (
            f"You are {self.display_name}, a security-remediation specialist. Use your skills "
            "and the provided tools to analyze the casefile and produce an accurate, auditable "
            "result. Prefer calling tools for precise evidence over guessing."
        )

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            "Analyze this security casefile and gather the evidence you need by calling tools.\n\n"
            f"Casefile:\n{casefile.model_dump_json(indent=2)}"
        )

    def section_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            f"Based on your analysis, produce the {self.section_field} for this casefile "
            "as a structured result."
        )

    # ------------------------------------------------------------------
    def _resolve_model(self) -> Model:
        return self.model or build_strands_model(self.model_gateway.profile)

    def _tool_context(self, invocation: AgentInvocation) -> ToolContext:
        approval = (
            ApprovalState.APPROVED
            if invocation.task.constraints.get("approved")
            else ApprovalState.NOT_REQUIRED
        )
        return ToolContext(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            agent_id=self.agent_id,
            risk_level=invocation.task.risk_level,
            approval_state=approval,
            provider=invocation.source_provider,
        )

    def _build_strands_agent(
        self, invocation: AgentInvocation
    ) -> tuple[Agent, ToolPolicyHook, AgentSkills | None]:
        policy = ToolPolicy(self.tool_names)
        hook = ToolPolicyHook(policy, self._tool_context(invocation))
        plugin = build_skills_plugin(self.skill_names)
        agent = Agent(
            model=self._resolve_model(),
            tools=get_tools(self.tool_names),
            plugins=[plugin] if plugin else [],
            hooks=[hook],
            system_prompt=self.system_prompt(),
            callback_handler=None,  # no console streaming; we capture results structurally
        )
        return agent, hook, plugin

    async def run(self, invocation: AgentInvocation) -> AgentResult:
        started = perf_counter()
        casefile = casefile_from_invocation(invocation)
        if casefile is None or self.section_model is None:
            return AgentResult(
                run_id=invocation.run_id,
                task_id=invocation.task.task_id,
                state=TaskState.FAILED,
                summary=f"{self.display_name} could not resolve a casefile to enrich.",
                error_type="ValidationFailed",
                error_message="no casefile available on invocation",
            )

        agent, hook, plugin = self._build_strands_agent(invocation)
        await agent.invoke_async(self.reasoning_prompt(casefile))
        # TODO(structured-output): migrate to the single-invocation, non-deprecated
        # path `invoke_async(prompt, structured_output_model=...)` once FakeModel
        # supports the forced structured-output tool. That path also keeps tool
        # results in context for the structured emission on real models.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            section = await agent.structured_output_async(
                self.section_model, self.section_prompt(casefile)
            )
        setattr(casefile, self.section_field, section)

        available = [s.name for s in plugin.get_available_skills()] if plugin else []
        activated = plugin.get_activated_skills(agent) if plugin else []
        casefile.audit[self.agent_id] = {
            "section": self.section_field,
            "available_skills": available,
            "activated_skills": activated,
            "tools_allowed": hook.outcome.allowed,
            "tools_denied": hook.outcome.denied,
            "tools_approval_required": hook.outcome.approval_required,
        }

        usage = BudgetUsage(agent_loops=1, model_calls=1, elapsed_seconds=perf_counter() - started)
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"{self.display_name} produced {self.section_field}.",
            rationale=json.dumps(casefile.audit[self.agent_id], indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer=self.agent_id)],
            activated_skills=activated or available,
            requested_tools=hook.outcome.allowed,
            requires_approval=bool(hook.outcome.approval_required),
            budget_usage=usage,
        )
