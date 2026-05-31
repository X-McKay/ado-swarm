from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import RepositoryEvidence
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.model_gateway.strands_models import FakeModel, ScriptStep, ToolCall

FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/source_issues/codeql_sast.json"


async def run_eval(model_profile: str = "fake") -> dict:
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    casefile = build_casefile("eval-run", issue)
    casefile.repository_evidence = None
    issue_dict = issue.model_dump(mode="json")
    repo_dict = issue.repository.model_dump(mode="json") if issue.repository else {}
    file_path = (
        casefile.normalized_finding.file_path if casefile.normalized_finding else None
    ) or "README.md"
    expected = RepositoryEvidence(
        repository=issue.repository,
        ref=issue.repository.default_branch if issue.repository else None,
        file_exists=True,
        evidence=["repository resolved and file verified"],
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[ToolCall(name="resolve_repository", input={"source_issue": issue_dict})]
            ),
            ScriptStep(
                tool_calls=[
                    ToolCall(
                        name="verify_file_location",
                        input={"repository": repo_dict, "path": file_path, "ref": "main"},
                    )
                ]
            ),
            ScriptStep(text="gathered repository evidence"),
        ],
        structured_outputs={RepositoryEvidence: expected},
    )
    invocation = eval_invocation(
        "repo_analyst",
        objective="Gather read-only repository evidence.",
        constraints={"casefile": casefile.model_dump(mode="json")},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        evidence = casefile_out.get("repository_evidence")
        audit = casefile_out.get("audit", {}).get("repo_analyst", {})
        return bool(evidence) and "resolve_repository" in audit.get("tools_allowed", [])

    return await run_agent_eval(
        "repo_analyst",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
