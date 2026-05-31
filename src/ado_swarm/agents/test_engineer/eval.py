from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import RemediationPlan, ValidationResult
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
    plan = RemediationPlan(
        strategy="localized_code_fix",
        change_boundary=f"single finding {finding.finding_id}",
        steps=["Apply the smallest safe code change.", "Run targeted tests."],
        requires_human_approval=True,
    )
    casefile.remediation_plan = plan
    finding_dict = finding.model_dump(mode="json")
    plan_dict = plan.model_dump(mode="json")
    expected = ValidationResult(
        recommended_checks=[
            "targeted test or scanner coverage for the affected file",
            "full project quality gate before PR creation",
        ],
        ready_for_review=False,
        rationale="Human approval is required before this finding is ready for review.",
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[
                    ToolCall(
                        name="propose_validation_checks",
                        input={"finding": finding_dict, "remediation_plan": plan_dict},
                    )
                ]
            ),
            ScriptStep(text="prepared validation checklist"),
        ],
        structured_outputs={ValidationResult: expected},
    )
    invocation = eval_invocation(
        "test_engineer",
        objective="Define validation checks and readiness.",
        constraints={"casefile": casefile.model_dump(mode="json")},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        validation = casefile_out.get("validation")
        audit = casefile_out.get("audit", {}).get("test_engineer", {})
        return (
            bool(validation)
            and bool(validation.get("recommended_checks"))
            and "propose_validation_checks" in audit.get("tools_allowed", [])
        )

    return await run_agent_eval(
        "test_engineer",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
