from __future__ import annotations

import json
from pathlib import Path

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.agents.ticket_analyst.normalization import normalize_source_issue
from ado_swarm.contracts.analytics import CampaignReport
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentResult
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.model_gateway.strands_models import FakeModel, ScriptStep, ToolCall

FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/source_issues/codeql_sast.json"


async def run_eval(model_profile: str = "fake") -> dict:
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    finding = normalize_source_issue(issue)
    findings = [finding.model_dump(mode="json")]
    expected = CampaignReport(
        total_findings=1,
        by_category={finding.category or "security": 1},
        by_severity={finding.severity: 1} if finding.severity else {},
        recommendations=["Prioritize the most common category for a remediation campaign."],
        rationale="Single-finding sample; expand history for stronger campaign signals.",
    )
    fake = FakeModel(
        script=[
            ScriptStep(
                tool_calls=[ToolCall(name="summarize_findings", input={"findings": findings})]
            ),
            ScriptStep(text="summarized findings"),
        ],
        structured_outputs={CampaignReport: expected},
    )
    invocation = eval_invocation(
        "data_analyst",
        objective="Mine findings for campaign patterns.",
        constraints={"findings": findings},
    )

    def assertion(result: AgentResult) -> bool:
        if result.state != TaskState.COMPLETED or not result.artifact_refs:
            return False
        report = result.artifact_refs[0].metadata.get("campaign_report")
        return bool(report) and "summarize_findings" in result.requested_tools

    return await run_agent_eval(
        "data_analyst",
        invocation=invocation,
        model_profile=model_profile,
        fake_model=fake,
        assertion=assertion,
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
