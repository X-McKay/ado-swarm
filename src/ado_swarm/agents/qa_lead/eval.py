from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import ReadinessVerdict
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.model_gateway.strands_models import FakeModel, ScriptStep, ToolCall

FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/source_issues/codeql_sast.json"


async def run_eval(model_profile: str = "fake") -> dict:
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    casefile = build_casefile("eval-run", issue)
    casefile_dict = casefile.model_dump(mode="json")
    expected = ReadinessVerdict(
        ready=False,
        next_phase="triage",
        blocking_reasons=["missing adjudication", "missing risk classification"],
        rationale="Adjudication and risk sections are not yet populated.",
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[ToolCall(name="assess_readiness", input={"casefile": casefile_dict})]
            ),
            ScriptStep(text="assessed readiness"),
        ],
        structured_outputs={ReadinessVerdict: expected},
    )
    invocation = eval_invocation(
        "qa_lead",
        objective="Assess casefile phase readiness.",
        constraints={"casefile": casefile_dict},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        readiness = casefile_out.get("readiness")
        audit = casefile_out.get("audit", {}).get("qa_lead", {})
        return bool(readiness) and "assess_readiness" in audit.get("tools_allowed", [])

    return await run_agent_eval(
        "qa_lead",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
