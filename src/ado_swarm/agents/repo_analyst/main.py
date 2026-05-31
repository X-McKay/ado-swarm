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
    tool_names: ClassVar[list[str]] = ["resolve_repository", "verify_file_location"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return (
            "Gather read-only repository evidence for this finding. Use resolve_repository to "
            "find the repository from the source issue, then verify_file_location to confirm the "
            "referenced file path exists at the resolved ref.\n\n"
            f"Casefile:\n{casefile.model_dump_json(indent=2)}"
        )


def build_agent(model_gateway: ModelGateway) -> RepoAnalystAgent:
    return RepoAnalystAgent(
        agent_id="repo_analyst",
        display_name="Repository Analyst",
        model_gateway=model_gateway,
    )
