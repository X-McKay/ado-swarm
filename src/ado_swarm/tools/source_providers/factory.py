from __future__ import annotations

from ado_swarm.config import Settings
from ado_swarm.tools.source_providers.azure_devops import AzureDevOpsSourceProvider
from ado_swarm.tools.source_providers.base import SourceProvider
from ado_swarm.tools.source_providers.github import GitHubSourceProvider
from ado_swarm.tools.source_providers.stub import StubSourceProvider


def build_source_provider(settings: Settings) -> SourceProvider:
    if settings.source_provider == "azure_devops":
        if not (settings.ado_org_url and settings.ado_project and settings.ado_pat):
            raise ValueError("ADO_ORG_URL, ADO_PROJECT, and ADO_PAT are required for azure_devops")
        return AzureDevOpsSourceProvider(
            settings.ado_org_url, settings.ado_project, settings.ado_pat
        )
    if settings.source_provider == "github":
        if not (settings.github_token and settings.github_owner):
            raise ValueError("GITHUB_TOKEN and GITHUB_OWNER are required for github")
        return GitHubSourceProvider(settings.github_token, settings.github_owner)
    return StubSourceProvider()
