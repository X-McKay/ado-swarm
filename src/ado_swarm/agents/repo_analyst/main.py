from __future__ import annotations

import json
from dataclasses import dataclass

from ado_swarm.agents.base import BaseAgent
from ado_swarm.agents.casefile_utils import casefile_artifact, casefile_from_invocation
from ado_swarm.config import get_settings
from ado_swarm.contracts.casefile import RepositoryEvidence
from ado_swarm.contracts.events import TaskState
from ado_swarm.contracts.mission import AgentInvocation, AgentResult
from ado_swarm.model_gateway.gateway import ModelGateway
from ado_swarm.tools.source_providers.factory import build_source_provider


@dataclass
class RepoAnalystAgent(BaseAgent):
    async def run(self, invocation: AgentInvocation) -> AgentResult:
        casefile = casefile_from_invocation(invocation)
        if casefile is None or casefile.normalized_finding is None:
            return await super().run(invocation)
        finding = casefile.normalized_finding
        repository = (
            casefile.repository_evidence.repository if casefile.repository_evidence else None
        )
        repository = repository or casefile.source_issue.repository
        evidence_items: list[str] = []
        file_exists: bool | None = None
        ref: str | None = None
        if repository is not None:
            evidence_items.append("repository resolved from source issue context")
            ref = repository.default_branch
        if repository is not None and finding.file_path:
            provider = build_source_provider(get_settings())
            try:
                source_file = await provider.get_file(repository, finding.file_path, ref or "main")
                file_exists = True
                evidence_items.append(
                    f"file {finding.file_path} exists at {source_file.ref} "
                    f"with sha {source_file.sha}"
                )
                ref = source_file.ref
            except Exception as exc:
                file_exists = False
                evidence_items.append(
                    f"file {finding.file_path} could not be read: {type(exc).__name__}: {exc}"
                )
        elif finding.file_path:
            file_exists = None
            evidence_items.append("finding has file path but no repository context was available")
        else:
            evidence_items.append("finding did not include a file path for repository verification")
        casefile.repository_evidence = RepositoryEvidence(
            repository=repository,
            ref=ref,
            file_exists=file_exists,
            evidence=evidence_items,
        )
        casefile.audit["repo_analyst"] = {
            "checked_file_path": finding.file_path,
            "repository_resolved": repository is not None,
            "file_exists": file_exists,
            "evidence_count": len(evidence_items),
        }
        return AgentResult(
            run_id=invocation.run_id,
            task_id=invocation.task.task_id,
            state=TaskState.COMPLETED,
            summary=f"Collected repository evidence for {finding.finding_id}.",
            rationale=json.dumps(casefile.audit["repo_analyst"], indent=2, sort_keys=True),
            artifact_refs=[casefile_artifact(casefile, producer="repo_analyst")],
            activated_skills=self.skills,
            requested_tools=invocation.task.allowed_tools,
        )


def build_agent(model_gateway: ModelGateway) -> RepoAnalystAgent:
    return RepoAnalystAgent(
        agent_id="repo_analyst",
        display_name="Repository Analyst",
        skills=["repository-resolution", "code-location-verification", "git-history-investigation"],
        model_gateway=model_gateway,
    )
