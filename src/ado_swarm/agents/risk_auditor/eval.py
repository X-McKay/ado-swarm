from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import RiskClassification
from ado_swarm.contracts.events import RiskLevel, TaskState
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
    expected = RiskClassification(
        risk_level=RiskLevel.HIGH,
        impact="sast finding with high severity",
        automation_eligible=False,
        confidence=0.8,
        rationale="High-severity SAST finding requires human review.",
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[ToolCall(name="score_severity", input={"finding": finding_dict})]
            ),
            ScriptStep(text="scored the finding"),
        ],
        structured_outputs={RiskClassification: expected},
    )
    invocation = eval_invocation(
        "risk_auditor",
        objective="Score risk and automation eligibility.",
        constraints={"casefile": casefile.model_dump(mode="json")},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        risk = casefile_out.get("risk")
        audit = casefile_out.get("audit", {}).get("risk_auditor", {})
        return (
            bool(risk)
            and risk.get("risk_level") in {"low", "medium", "high", "critical"}
            and "score_severity" in audit.get("tools_allowed", [])
        )

    return await run_agent_eval(
        "risk_auditor",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
