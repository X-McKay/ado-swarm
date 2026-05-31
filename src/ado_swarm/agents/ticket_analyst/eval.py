from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import normalize_source_issue
from ado_swarm.contracts.casefile import NormalizedFinding
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.model_gateway.strands_models import FakeModel, ScriptStep, ToolCall

FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/source_issues/codeql_sast.json"


async def run_eval(model_profile: str = "fake") -> dict:
    issue_dict = json.loads(FIXTURE.read_text())
    issue = SourceIssue.model_validate(issue_dict)
    expected = normalize_source_issue(issue)
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[ToolCall(name="normalize_finding", input={"issue": issue_dict})]
            ),
            ScriptStep(text="normalized the finding"),
        ],
        structured_outputs={NormalizedFinding: expected},
    )
    invocation = eval_invocation(
        "ticket_analyst",
        objective="Normalize the provider issue into a canonical finding.",
        constraints={"source_issue": issue_dict},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile = result.artifact_refs[0].metadata["casefile"]
        finding = casefile.get("normalized_finding")
        audit = casefile.get("audit", {}).get("ticket_analyst", {})
        return (
            bool(finding)
            and finding.get("severity") == expected.severity
            and "normalize_finding" in audit.get("tools_allowed", [])
        )

    return await run_agent_eval(
        "ticket_analyst",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
