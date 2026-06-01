from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import RepositoryEvidence, SecurityCasefile
from ado_swarm.model_gateway.gateway import ModelGateway


class RepoAnalystAgent(CasefileAgent):
    """Model-driven: decides what repository evidence to gather and calls read-only
    repo tools (resolve_repository, verify_file_location) through the policy gate."""

    section_field: ClassVar[str] = "repository_evidence"
    section_model: ClassVar[type[BaseModel] | None] = RepositoryEvidence
    tool_names: ClassVar[list[str]] = [
        "resolve_repository",
        "verify_file_location",
        "repo_grep",
        "repo_parse_manifest",
    ]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            "Gather read-only repository evidence for this finding. Use resolve_repository to "
            "find the repository from the source issue and verify_file_location to confirm the "
            "referenced file exists at the resolved ref. When the finding cites a code pattern, "
            "use repo_grep to confirm the pattern is actually present at the location; for a "
            "dependency finding, use repo_parse_manifest to confirm the affected package/version. "
            "Base your evidence on what the tools return, not assumptions.\n\n"
            f"Casefile:\n{casefile.model_dump_json(indent=2)}"
        )


def build_agent(model_gateway: ModelGateway) -> RepoAnalystAgent:
    return RepoAnalystAgent(
        agent_id="repo_analyst",
        display_name="Repository Analyst",
        model_gateway=model_gateway,
    )
