from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import ExecutionResult, RemediationPlan
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
        steps=["Apply the smallest safe code change."],
        requires_human_approval=False,
    )
    casefile.remediation_plan = plan
    finding_dict = finding.model_dump(mode="json")
    plan_dict = plan.model_dump(mode="json")
    expected = ExecutionResult(
        applied=True,
        sandbox_session_id="sandbox-eval",
        changed_files=[finding.file_path or "PLANNED_CHANGE.md"],
        diff_summary="recorded localized_code_fix in sandbox",
        rationale="change materialized in an isolated sandbox for review",
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[
                    ToolCall(
                        name="apply_remediation_change",
                        input={"finding": finding_dict, "remediation_plan": plan_dict},
                    )
                ]
            ),
            ScriptStep(text="applied the change in a sandbox"),
        ],
        structured_outputs={ExecutionResult: expected},
    )
    # The write tool requires approval; the eval supplies an approved context.
    invocation = eval_invocation(
        "software_engineer",
        objective="Apply the remediation in a sandbox.",
        constraints={"casefile": casefile.model_dump(mode="json"), "approved": True},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        casefile_out = result.artifact_refs[0].metadata["casefile"]
        execution = casefile_out.get("execution")
        audit = casefile_out.get("audit", {}).get("software_engineer", {})
        return (
            bool(execution)
            and execution.get("applied") is True
            and "apply_remediation_change" in audit.get("tools_allowed", [])
        )

    return await run_agent_eval(
        "software_engineer",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
