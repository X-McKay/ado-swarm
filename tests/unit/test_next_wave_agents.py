from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from ado_swarm.agents.eval_support import build_eval_model_gateway
from ado_swarm.agents.security_reviewer.main import build_agent as build_security_reviewer
from ado_swarm.agents.solutions_architect.main import build_agent as build_solutions_architect
from ado_swarm.agents.test_engineer.main import build_agent as build_test_engineer
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.mission import AgentInvocation, TaskSpec
from ado_swarm.contracts.source_provider import SourceIssue

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/source_issues/codeql_sast.json"


def fixture_casefile() -> dict:
    issue = SourceIssue.model_validate(json.loads(FIXTURE.read_text()))
    return build_casefile("test-run", issue).model_dump(mode="json")


async def run_agent(agent_id: str, builder, casefile: dict) -> dict:
    agent = builder(build_eval_model_gateway("fake"))
    task = TaskSpec(
        run_id="test-run",
        title=f"Run {agent_id}",
        objective="Validate casefile enrichment behavior.",
        capability=agent_id,
        agent_id=agent_id,
        constraints={"casefile": casefile},
    )
    result = await agent.run(
        AgentInvocation(
            run_id="test-run",
            task=task,
            context_id="test",
            plan_version=1,
            idempotency_key=str(uuid4()),
        )
    )
    assert result.artifact_refs
    return result.artifact_refs[0].metadata["casefile"]


@pytest.mark.asyncio
async def test_deterministic_casefile_enrichment_pipeline() -> None:
    # Covers the agents still on the deterministic path. The model-driven slice
    # (ticket_analyst, repo_analyst, risk_auditor) is covered by their own evals.
    casefile = fixture_casefile()
    casefile = await run_agent("security_reviewer", build_security_reviewer, casefile)
    assert casefile["adjudication"]["false_positive"] is False
    casefile = await run_agent("solutions_architect", build_solutions_architect, casefile)
    assert casefile["remediation_plan"]["steps"]
    casefile = await run_agent("test_engineer", build_test_engineer, casefile)
    assert "test_engineer" in casefile["audit"]
