from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from ado_swarm.agents.eval_support import build_eval_model_gateway
from ado_swarm.agents.security_reviewer.main import build_agent
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.casefile import (
    RepositoryEvidence,
)
from ado_swarm.contracts.mission import AgentInvocation, TaskSpec
from ado_swarm.contracts.source_provider import SourceIssue


def _fixture_casefile() -> dict:
    issue = SourceIssue.model_validate(
        json.loads(Path("tests/fixtures/source_issues/codeql_sast.json").read_text())
    )
    casefile = build_casefile("eval-run", issue)
    casefile.repository_evidence = RepositoryEvidence.model_validate(
        {
            "repository": casefile.source_issue.repository.model_dump(mode="json")
            if casefile.source_issue.repository
            else None,
            "ref": "main",
            "file_exists": True,
            "evidence": ["fixture repository evidence"],
        }
    )
    casefile.adjudication = None
    casefile.risk = None
    casefile.remediation_plan = None
    return casefile.model_dump(mode="json")


async def run_eval(model_profile: str = "fake") -> dict:
    agent = build_agent(build_eval_model_gateway(model_profile))
    task = TaskSpec(
        run_id="eval-run",
        title="Evaluate Security Reviewer",
        objective="Run deterministic casefile evaluation for Security Reviewer.",
        capability="security_reviewer",
        agent_id="security_reviewer",
        constraints={"casefile": _fixture_casefile()},
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
    casefile = result.artifact_refs[0].metadata["casefile"] if result.artifact_refs else {}
    passed = result.state == "completed" and casefile.get("adjudication") is not None
    return {
        "agent_id": "security_reviewer",
        "passed": passed,
        "result": result.model_dump(mode="json"),
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
