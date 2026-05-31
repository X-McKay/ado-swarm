from __future__ import annotations

import json
from time import perf_counter
from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.agents.swarm_cell import Reviewer, run_adjudication_cell
from ado_swarm.config import get_settings
from ado_swarm.contracts.budget import BudgetUsage
from ado_swarm.contracts.casefile import FindingAdjudication, SecurityCasefile
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway

# The reviewer ensemble: each argues one perspective; the judge reconciles them.
_REVIEWER_SPECS = [
    (
        "stale_reviewer",
        "stale-finding-adjudication",
        "Argue whether this finding is STALE (the code/file/line no longer exists or the "
        "referenced code was removed). Weigh repository evidence heavily.",
    ),
    (
        "false_positive_reviewer",
        "false-positive-evidence-review",
        "Argue whether this finding is a FALSE POSITIVE (the flagged pattern is not actually "
        "reachable/exploitable, e.g. sanitized input or test-only code).",
    ),
    (
        "duplicate_reviewer",
        "duplicate-finding-adjudication",
        "Argue whether this finding is a DUPLICATE of a known finding. Use graphiti_search by "
        "fingerprint, CWE, package, or file path to find prior findings.",
    ),
]


def _finding_block(casefile: SecurityCasefile) -> str:
    finding = (
        casefile.normalized_finding.model_dump_json(indent=2)
        if casefile.normalized_finding
        else "{}"
    )
    evidence = (
        casefile.repository_evidence.model_dump_json(indent=2)
        if casefile.repository_evidence
        else "null"
    )
    return f"Finding:\n{finding}\n\nRepository evidence:\n{evidence}"


class SecurityReviewerAgent(CasefileAgent):
    """Model-driven adjudicator.

    Default mode is a single agent (tools in a loop). When the bounded adjudication
    swarm is enabled (settings.security_reviewer_use_swarm or task constraint
    ``use_swarm``), it runs a multi-perspective ensemble + judge inside this one
    activity (Phase 1.5 / ADR-0009). Adopting the swarm is eval-gated: keep it off
    unless evals show it beats the single-agent baseline.
    """

    section_field: ClassVar[str] = "adjudication"
    section_model: ClassVar[type[BaseModel] | None] = FindingAdjudication
    tool_names: ClassVar[list[str]] = ["adjudication_signals", "graphiti_search"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            "Adjudicate this finding (stale / false-positive / already-fixed / duplicate / open). "
            "Call adjudication_signals with the finding and repository evidence for the baseline, "
            "and graphiti_search (by finding fingerprint, CWE, package, or file path) to recall "
            "related prior findings that may indicate a duplicate, then decide with rationale.\n\n"
            f"{_finding_block(casefile)}"
        )

    def _use_swarm(self, invocation: AgentInvocation) -> bool:
        if "use_swarm" in invocation.task.constraints:
            return bool(invocation.task.constraints["use_swarm"])
        return bool(get_settings().security_reviewer_use_swarm)

    async def run(self, invocation: AgentInvocation) -> AgentResult:
        if not self._use_swarm(invocation):
            return await super().run(invocation)

        casefile = casefile_from_invocation(invocation)
        if casefile is None:
            return await super().run(invocation)

        started = perf_counter()
        finding_block = _finding_block(casefile)
        reviewers = [
            Reviewer(
                name=name,
                system_prompt=(f"You are the {name} on a security adjudication panel. {stance}"),
                reasoning_prompt=(
                    f"{stance}\n\nProduce your position as a FindingAdjudication.\n\n{finding_block}"
                ),
                tool_names=["adjudication_signals", "graphiti_search"],
                skill_names=[skill],
            )
            for name, skill, stance in _REVIEWER_SPECS
        ]
        settings = get_settings()
        cell = await run_adjudication_cell(
            model=self._resolve_model(),
            reviewers=reviewers,
            judge_output_model=FindingAdjudication,
            judge_system_prompt=(
                "You are the adjudication judge. Reconcile the reviewers' positions into one "
                "final, well-justified FindingAdjudication. Prefer evidence over assertion."
            ),
            judge_reasoning_prompt=(
                "Reconcile the panel into the final adjudication.\n\n" + finding_block
            ),
            judge_tool_names=["adjudication_signals", "graphiti_search"],
            judge_skill_names=["stale-finding-adjudication"],
            tool_context=self._tool_context(invocation),
            max_model_calls=settings.adjudication_swarm_max_model_calls,
        )
        if not isinstance(cell.section, FindingAdjudication):
            return AgentResult(
                run_id=invocation.run_id,
                task_id=invocation.task.task_id,
                state=TaskState.FAILED,
                summary="Adjudication swarm produced no decision.",
                error_type="ValidationFailed",
                error_message="judge returned no structured output",
            )
        casefile.adjudication = cell.section
        casefile.audit["security_reviewer"] = {
            "section": "adjudication",
            "mode": "swarm",
            "reviewer_positions": cell.reviewer_positions,
            "activated_skills": cell.activated_skills,
            "tools_allowed": cell.tools_allowed,
            "model_calls": cell.model_calls,
        }
        usage = BudgetUsage(
            agent_loops=len(reviewers) + 1,
            model_calls=cell.model_calls,
            input_tokens=cell.input_tokens,
            output_tokens=cell.output_tokens,
            elapsed_seconds=perf_counter() - started,
        )
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary="Security Reviewer adjudicated via bounded swarm.",
            rationale=json.dumps(casefile.audit["security_reviewer"], indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer="security_reviewer")],
            activated_skills=cell.activated_skills,
            requested_tools=cell.tools_allowed,
            budget_usage=usage,
        )


def build_agent(model_gateway: ModelGateway) -> SecurityReviewerAgent:
    return SecurityReviewerAgent(
        agent_id="security_reviewer",
        display_name="Security Reviewer",
        model_gateway=model_gateway,
    )
