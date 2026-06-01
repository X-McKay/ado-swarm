"""Provider-read tools — read-only access to issues/repos through the source port.

The model decides what provider evidence to pull; these tools do the deterministic,
policy-gated reads via the configured `SourceProvider` (ADO/GitHub/stub).
"""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.source_provider import SourceRepositoryRef
from ado_swarm.tools.source_providers.providers import get_source_provider


async def provider_get_issue_impl(external_id: str) -> dict:
    provider = get_source_provider()
    issue = await provider.get_issue(external_id)
    return issue.model_dump(mode="json")


async def provider_search_issues_impl(query: str, limit: int = 25) -> dict:
    provider = get_source_provider()
    page = await provider.search_issues(query, limit=limit)
    return page.model_dump(mode="json")


async def provider_get_repo_metadata_impl(repository: dict) -> dict:
    repo = SourceRepositoryRef.model_validate(repository)
    provider = get_source_provider()
    metadata = await provider.get_repository(repo.owner_or_project, repo.name)
    return metadata.model_dump(mode="json")


@tool
async def provider_get_issue(external_id: str) -> dict:
    """Fetch a single provider issue/work item by its external id (read-only).

    Args:
        external_id: The provider-native id of the issue/work item.

    Returns:
        A SourceIssue JSON object.
    """
    return await provider_get_issue_impl(external_id)


@tool
async def provider_search_issues(query: str, limit: int = 25) -> dict:
    """Search provider issues/work items (read-only).

    Args:
        query: The provider search query.
        limit: Maximum number of results to return.

    Returns:
        A SourceIssuePage JSON object (provider, items, query, limit).
    """
    return await provider_search_issues_impl(query, limit)


@tool
async def provider_get_repo_metadata(repository: dict) -> dict:
    """Fetch repository metadata for a repository reference (read-only).

    Args:
        repository: A SourceRepositoryRef JSON object.

    Returns:
        A SourceRepository JSON object.
    """
    return await provider_get_repo_metadata_impl(repository)
