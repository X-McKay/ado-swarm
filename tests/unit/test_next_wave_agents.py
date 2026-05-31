from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from ado_swarm.agents.eval_support import build_eval_model_gateway
from ado_swarm.agents.repo_analyst.main import build_agent as build_repo_analyst
from ado_swarm.agents.risk_auditor.main import build_agent as build_risk_auditor
from ado_swarm.agents.security_reviewer.main import build_agent as build_security_reviewer
from ado_swarm.agents.solutions_architect.main import build_agent as build_solutions_architect
from ado_swarm.agents.test_engineer.main import build_agent as build_test_engineer
from ado_swarm.agents.ticket_analyst.normalization import build_casefile
from ado_swarm.contracts.mission import AgentInvocation, TaskSpec
from ado_swarm.contracts.source_provider import SourceIssue


def fixture_casefile() -> dict:
    issue = SourceIssue.model_validate(
        json.loads(Path("tests/fixtures/source_issues/codeql_sast.json").read_text())
    )
    return build_casefile("test-run", issue).model_dump(mode="json")


async def run_agent(agent_id: str, builder, casefile: dict) -> dict:
    agent = builder(build_eval_model_gateway("fake"))
    task = TaskSpec(
        run_id="test-run",
        title=f"Run {agent_id}",
        objective="Validate richer next-wave behavior.",
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
async def test_next_wave_casefile_enrichment_pipeline() -> None:
    casefile = fixture_casefile()
    casefile = await run_agent("repo_analyst", build_repo_analyst, casefile)
    assert casefile["repository_evidence"]["file_exists"] is True
    casefile = await run_agent("security_reviewer", build_security_reviewer, casefile)
    assert casefile["adjudication"]["false_positive"] is False
    casefile = await run_agent("risk_auditor", build_risk_auditor, casefile)
    assert casefile["risk"]["risk_level"] in {"medium", "high", "critical", "low"}
    casefile = await run_agent("solutions_architect", build_solutions_architect, casefile)
    assert casefile["remediation_plan"]["steps"]
    casefile = await run_agent("test_engineer", build_test_engineer, casefile)
    assert "test_engineer" in casefile["audit"]
