from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import RemediationPlan
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
    expected = RemediationPlan(
        strategy="localized_code_fix",
        change_boundary=f"single finding {finding.finding_id}",
        steps=[
            "Inspect the affected file around the reported location.",
            "Apply the smallest code change that removes the unsafe data flow.",
            "Run targeted security and unit tests before preparing review output.",
        ],
        requires_human_approval=True,
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[
                    ToolCall(name="propose_remediation_strategy", input={"finding": finding_dict})
                ]
            ),
            ScriptStep(text="prepared the remediation plan"),
        ],
        structured_outputs={RemediationPlan: expected},
    )
    invocation = eval_invocation(
        "solutions_architect",
        objective="Produce a bounded remediation plan.",
        constraints={"casefile": casefile.model_dump(mode="json")},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        plan = casefile_out.get("remediation_plan")
        audit = casefile_out.get("audit", {}).get("solutions_architect", {})
        return (
            bool(plan)
            and bool(plan.get("steps"))
            and "propose_remediation_strategy" in audit.get("tools_allowed", [])
        )

    return await run_agent_eval(
        "solutions_architect",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
