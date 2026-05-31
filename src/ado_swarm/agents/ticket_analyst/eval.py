from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from ado_swarm.agents.eval_support import build_eval_model_gateway
from ado_swarm.agents.ticket_analyst.main import build_agent
from ado_swarm.contracts.mission import AgentInvocation, TaskSpec
from ado_swarm.contracts.source_provider import SourceIssue
from ado_swarm.tools.source_providers.stub import StubSourceProvider

FIXTURE_PATH = Path("src/ado_swarm/agents/ticket_analyst/fixtures/codeql_sast_issue.json")


def load_fixture_issue() -> SourceIssue:
    return SourceIssue.model_validate_json(FIXTURE_PATH.read_text())


async def _evaluate_issue(model_profile: str, issue: SourceIssue) -> dict:
    agent = build_agent(build_eval_model_gateway(model_profile))
    task = TaskSpec(
        run_id="eval-run",
        title="Evaluate Ticket Analyst",
        objective="Normalize a provider issue into a canonical security finding.",
        capability="ticket_analyst",
        agent_id="ticket_analyst",
        constraints={"source_issue": issue.model_dump(mode="json")},
    )
    result = await agent.run(
        AgentInvocation(
            run_id="eval-run",
            task=task,
            context_id="eval",
            plan_version=1,
            idempotency_key=str(uuid4()),
        )
    )
    casefile = result.artifact_refs[0].metadata["casefile"] if result.artifact_refs else None
    finding = casefile["normalized_finding"] if casefile else None
    expected_category = "dependency" if "dependency" in issue.title.lower() else None
    passed = result.state == "completed" and finding is not None and finding["confidence"] >= 0.55
    if expected_category:
        passed = passed and finding["category"] == expected_category
    return {
        "issue": issue.external_id,
        "passed": passed,
        "finding": finding,
        "result": result.model_dump(mode="json"),
    }


async def run_eval(model_profile: str = "fake") -> dict:
    provider = StubSourceProvider()
    issues = [await provider.get_issue("SEC-1"), load_fixture_issue()]
    cases = [await _evaluate_issue(model_profile, issue) for issue in issues]
    return {
        "agent_id": "ticket_analyst",
        "passed": all(case["passed"] for case in cases),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-profile", default="fake")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = asyncio.run(run_eval(args.model_profile))
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
