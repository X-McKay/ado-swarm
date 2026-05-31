from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import FindingAdjudication
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.model_gateway.strands_models import FakeModel, ScriptStep, ToolCall

FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/source_issues/codeql_sast.json"


async def run_eval(model_profile: str = "fake") -> dict:
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    casefile = build_casefile("eval-run", issue)
    finding = casefile.normalized_finding
    if finding is None:
        raise ValueError("fixture casefile is missing a normalized finding")
    finding_dict = finding.model_dump(mode="json")
    evidence_dict = (
        casefile.repository_evidence.model_dump(mode="json")
        if casefile.repository_evidence
        else None
    )
    expected = FindingAdjudication(
        stale=False,
        false_positive=False,
        already_fixed=False,
        rationale="Repository evidence does not prove the finding is stale or false positive.",
        confidence=0.8,
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[
                    ToolCall(
                        name="adjudication_signals",
                        input={"finding": finding_dict, "repository_evidence": evidence_dict},
                    )
                ]
            ),
            ScriptStep(text="adjudicated the finding"),
        ],
        structured_outputs={FindingAdjudication: expected},
    )
    invocation = eval_invocation(
        "security_reviewer",
        objective="Adjudicate the finding.",
        constraints={"casefile": casefile.model_dump(mode="json")},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        adjudication = casefile_out.get("adjudication")
        audit = casefile_out.get("audit", {}).get("security_reviewer", {})
        return bool(adjudication) and "adjudication_signals" in audit.get("tools_allowed", [])

    return await run_agent_eval(
        "security_reviewer",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
