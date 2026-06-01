"""Model-driven casefile agent base — tools in a loop + skills + structured output.

Per `docs/concepts/agents-tools-skills.md`, every agent is a Strands `Agent`
(model + tools in a loop). A `CasefileAgent` reads a `SecurityCasefile`, runs a
real reasoning loop (the model calls deterministic catalog tools through the
policy gate, with skills progressively disclosed), then emits exactly one typed
casefile section via structured output. The Strands plumbing lives in
`agents/model_runtime.run_model_agent`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import ClassVar

from pydantic import BaseModel
from strands.models import Model

from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.agents.model_runtime import run_model_agent
from ado_swarm.contracts.budget import BudgetUsage
from ado_swarm.contracts.casefile import SecurityCasefile
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway
from ado_swarm.model_gateway.strands_models import build_strands_model
from ado_swarm.tools.policy import ApprovalState, ToolContext


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
    # Subset of tool_names that mutate state and therefore require approval.
    write_tool_names: ClassVar[list[str]] = []

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

        run = await run_model_agent(
            model=self._resolve_model(),
            tool_names=self.tool_names,
            skill_names=self.skill_names,
            system_prompt=self.system_prompt(),
            reasoning_prompt=self.reasoning_prompt(casefile),
            output_model=self.section_model,
            output_prompt=self.section_prompt(casefile),
            tool_context=self._tool_context(invocation),
            write_tool_names=self.write_tool_names,
        )
        if run.section is None:
            return AgentResult(
                run_id=invocation.run_id,
                task_id=invocation.task.task_id,
                state=TaskState.FAILED,
                summary=f"{self.display_name} did not produce a {self.section_field}.",
                error_type="ValidationFailed",
                error_message="model returned no structured output",
            )
        setattr(casefile, self.section_field, run.section)

        casefile.audit[self.agent_id] = {
            "section": self.section_field,
            "available_skills": run.available_skills,
            "activated_skills": run.activated_skills,
            "tools_allowed": run.policy_outcome.allowed,
            "tools_denied": run.policy_outcome.denied,
            "tools_approval_required": run.policy_outcome.approval_required,
        }

        usage = BudgetUsage(
            agent_loops=1,
            model_calls=run.model_calls or 1,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            elapsed_seconds=perf_counter() - started,
        )
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"{self.display_name} produced {self.section_field}.",
            rationale=json.dumps(casefile.audit[self.agent_id], indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer=self.agent_id)],
            activated_skills=run.activated_skills or run.available_skills,
            requested_tools=run.policy_outcome.allowed,
            requires_approval=bool(run.policy_outcome.approval_required),
            budget_usage=usage,
        )
