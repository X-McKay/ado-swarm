from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import SecurityCasefile, SubmissionResult
from ado_swarm.model_gateway.gateway import ModelGateway


class SubmissionEngineerAgent(CasefileAgent):
    """Model-driven: after a remediation is validated and approved, prepares a DRAFT
    pull request and updates the ticket disposition.

    The PR/comment tools are WRITE and approval-gated: `provider_create_draft_pr`
    and `provider_add_issue_comment` are in `write_tool_names`, so `ToolPolicyHook`
    blocks them unless the task carries an approved `ToolContext`
    (`constraints["approved"]`). Without approval the agent can still reason and
    emit a `SubmissionResult` recording that submission is pending approval.
    """

    section_field: ClassVar[str] = "submission"
    section_model: ClassVar[type[BaseModel] | None] = SubmissionResult
    tool_names: ClassVar[list[str]] = [
        "assess_readiness",
        "provider_create_draft_pr",
        "provider_add_issue_comment",
    ]
    write_tool_names: ClassVar[list[str]] = [
        "provider_create_draft_pr",
        "provider_add_issue_comment",
    ]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        validation = (
            casefile.validation.model_dump_json(indent=2) if casefile.validation else "null"
        )
        execution = (
            casefile.execution.model_dump_json(indent=2) if casefile.execution else "null"
        )
        return (
            "Prepare the submission for this validated remediation. Only open a DRAFT pull "
            "request (provider_create_draft_pr) and post a disposition comment "
            "(provider_add_issue_comment) when the change is validated and approved; those tools "
            "are approval-gated, so if they are blocked, record that submission is pending "
            "approval rather than fabricating a result. Summarize the actions taken.\n\n"
            f"Source issue: {casefile.source_issue.external_id}\n"
            f"Validation:\n{validation}\n\nExecution:\n{execution}"
        )


def build_agent(model_gateway: ModelGateway) -> SubmissionEngineerAgent:
    return SubmissionEngineerAgent(
        agent_id="submission_engineer",
        display_name="Submission Engineer",
        model_gateway=model_gateway,
    )
