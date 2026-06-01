"""Provider write tools — approval-gated mutations on issues/PRs.

These are WRITE tools: they mutate provider state (comments, draft PRs). Every
agent that declares one MUST list it in `write_tool_names` so `ToolPolicyHook`
requires an approved `ToolContext` before it can run (ADR-0005 / ADR-0009).
They flow through the same `SourceProvider` port as the read tools.
"""

from __future__ import annotations

from strands import tool

from ado_swarm.contracts.source_provider import SourceRepositoryRef
from ado_swarm.tools.source_providers.providers import get_source_provider


async def create_draft_pr_impl(
    repository: dict, title: str, source_branch: str, target_branch: str, body: str
) -> dict:
    repo = SourceRepositoryRef.model_validate(repository)
    provider = get_source_provider()
    pr = await provider.create_draft_pr(repo, title, source_branch, target_branch, body)
    return pr.model_dump(mode="json")


async def add_issue_comment_impl(external_id: str, body: str) -> dict:
    provider = get_source_provider()
    result = await provider.add_issue_comment(external_id, body)
    return result.model_dump(mode="json")


async def add_pr_comment_impl(repository: dict, pr_external_id: str, body: str) -> dict:
    repo = SourceRepositoryRef.model_validate(repository)
    provider = get_source_provider()
    result = await provider.add_pr_comment(repo, pr_external_id, body)
    return result.model_dump(mode="json")


@tool
async def provider_create_draft_pr(
    repository: dict, title: str, source_branch: str, target_branch: str, body: str
) -> dict:
    """Open a DRAFT pull request (WRITE, approval-gated).

    Draft only — never a ready/auto-merge PR. Requires an approved ToolContext.

    Args:
        repository: A SourceRepositoryRef JSON object.
        title: PR title.
        source_branch: The branch containing the change.
        target_branch: The branch to merge into.
        body: PR description (summary, evidence, validation results).

    Returns:
        A SourcePullRequest JSON object (is_draft=True).
    """
    return await create_draft_pr_impl(repository, title, source_branch, target_branch, body)


@tool
async def provider_add_issue_comment(external_id: str, body: str) -> dict:
    """Add a comment to a provider issue/work item (WRITE, approval-gated).

    Args:
        external_id: The provider-native id of the issue/work item.
        body: The comment text.

    Returns:
        A ProviderMutationResult JSON object.
    """
    return await add_issue_comment_impl(external_id, body)


@tool
async def provider_add_pr_comment(repository: dict, pr_external_id: str, body: str) -> dict:
    """Add a comment to a pull request (WRITE, approval-gated).

    Args:
        repository: A SourceRepositoryRef JSON object.
        pr_external_id: The PR's provider-native id.
        body: The comment text.

    Returns:
        A ProviderMutationResult JSON object.
    """
    return await add_pr_comment_impl(repository, pr_external_id, body)
