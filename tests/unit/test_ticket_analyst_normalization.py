import json
from pathlib import Path

import pytest

from ado_swarm.agents.ticket_analyst.main import build_agent
from ado_swarm.agents.ticket_analyst.normalization import build_casefile, normalize_source_issue
from ado_swarm.contracts.mission import AgentInvocation, TaskSpec
from ado_swarm.contracts.source_provider import SourceIssue, SourceProviderKind
from ado_swarm.model_gateway.gateway import ModelGateway, ModelProfile
from ado_swarm.tools.source_providers.stub import StubSourceProvider


@pytest.mark.asyncio
async def test_normalize_stub_dependency_issue() -> None:
    issue = await StubSourceProvider().get_issue("SEC-1")
    finding = normalize_source_issue(issue)
    assert finding.category == "dependency"
    assert finding.severity is None
    assert finding.confidence >= 0.65
    assert finding.finding_id.startswith("finding-")


def test_normalize_codeql_sast_fixture() -> None:
    fixture = Path("src/ado_swarm/agents/ticket_analyst/fixtures/codeql_sast_issue.json")
    issue = SourceIssue.model_validate_json(fixture.read_text())
    finding = normalize_source_issue(issue)
    assert finding.scanner == "CodeQL"
    assert finding.category == "sast"
    assert finding.severity == "high"
    assert finding.cwe == "CWE-89"
    assert finding.file_path == "src/api/users.py"
    assert finding.line == 128


@pytest.mark.asyncio
async def test_ticket_analyst_returns_casefile_artifact() -> None:
    issue = await StubSourceProvider().get_issue("SEC-1")
    agent = build_agent(ModelGateway(ModelProfile(provider="fake")))
    task = TaskSpec(
        run_id="run-1",
        title="Normalize ticket",
        objective="Normalize source issue.",
        capability="ticket_analyst",
        agent_id="ticket_analyst",
        constraints={"source_issue": issue.model_dump(mode="json")},
    )
    result = await agent.run(
        AgentInvocation(
            run_id="run-1",
            task=task,
            context_id="ctx",
            plan_version=1,
            idempotency_key="key",
        )
    )
    assert result.artifact_refs
    casefile = result.artifact_refs[0].metadata["casefile"]
    assert casefile["normalized_finding"]["category"] == "dependency"
    assert "security-ticket-normalization" in result.activated_skills
    rationale = json.loads(result.rationale or "{}")
    assert rationale["casefile_id"].startswith("casefile-")


def test_build_casefile_preserves_audit_missing_fields() -> None:
    issue = SourceIssue(
        provider=SourceProviderKind.STUB,
        external_id="minimal",
        url="https://example.invalid",
        title="Security issue",
    )
    casefile = build_casefile("run-1", issue)
    audit = casefile.audit["ticket_analyst"]
    assert "severity" in audit["missing_fields"]
    assert casefile.normalized_finding is not None
