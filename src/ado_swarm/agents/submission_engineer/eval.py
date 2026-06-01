from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import SubmissionResult
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.model_gateway.strands_models import FakeModel, ScriptStep, ToolCall

FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/source_issues/codeql_sast.json"


async def run_eval(model_profile: str = "fake") -> dict:
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    casefile = build_casefile("eval-run", issue)
    repo_dict = issue.repository.model_dump(mode="json") if issue.repository else {}
    expected = SubmissionResult(
        submitted=True,
        draft_pr_url="https://example.invalid/pull/1",
        disposition_comment="Draft PR opened for review.",
        actions=["created draft PR", "commented on issue"],
        rationale="Validated and approved; draft PR prepared.",
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[
                    ToolCall(
                        name="provider_create_draft_pr",
                        input={
                            "repository": repo_dict,
                            "title": "Fix finding",
                            "source_branch": "fix/finding",
                            "target_branch": "main",
                            "body": "remediation",
                        },
                    )
                ]
            ),
            ScriptStep(
                tool_calls=[
                    ToolCall(
                        name="provider_add_issue_comment",
                        input={"external_id": issue.external_id, "body": "Draft PR opened."},
                    )
                ]
            ),
            ScriptStep(text="prepared submission"),
        ],
        structured_outputs={SubmissionResult: expected},
    )
    # Submission requires approval — the write tools are gated until approved.
    invocation = eval_invocation(
        "submission_engineer",
        objective="Prepare the draft PR and disposition update.",
        constraints={"casefile": casefile.model_dump(mode="json"), "approved": True},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        submission = casefile_out.get("submission")
        audit = casefile_out.get("audit", {}).get("submission_engineer", {})
        # Approved run: the write tools must have been allowed (not blocked).
        return bool(submission) and "provider_create_draft_pr" in audit.get("tools_allowed", [])

    return await run_agent_eval(
        "submission_engineer",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
