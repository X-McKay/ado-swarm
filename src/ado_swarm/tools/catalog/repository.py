"""Repository tools — read-only repo/file evidence for the `repo_analyst` agent.

These are the agent's *hands*: the model decides what to inspect, these tools do
the deterministic, policy-gated provider reads.
"""

from __future__ import annotations

from strands import tool

from ado_swarm.config import get_settings
from ado_swarm.contracts.source_provider import SourceIssue, SourceRepositoryRef
from ado_swarm.tools.source_providers.factory import build_source_provider


def resolve_repository_impl(source_issue: dict) -> dict:
    issue = SourceIssue.model_validate(source_issue)
    repo = issue.repository
    if repo is None:
        return {"resolved": False, "repository": None, "ref": None, "evidence": []}
    return {
        "resolved": True,
        "repository": repo.model_dump(mode="json"),
        "ref": repo.default_branch,
        "evidence": ["repository resolved from source issue context"],
    }


async def verify_file_location_impl(repository: dict, path: str, ref: str = "main") -> dict:
    repo = SourceRepositoryRef.model_validate(repository)
    provider = build_source_provider(get_settings())
    try:
        source_file = await provider.get_file(repo, path, ref)
    except Exception as exc:  # provider read failure is evidence, not a crash
        return {
            "file_exists": False,
            "ref": ref,
            "sha": None,
            "evidence": [f"file {path} could not be read: {type(exc).__name__}: {exc}"],
        }
    return {
        "file_exists": True,
        "ref": source_file.ref,
        "sha": source_file.sha,
        "evidence": [f"file {path} exists at {source_file.ref} with sha {source_file.sha}"],
    }


@tool
def resolve_repository(source_issue: dict) -> dict:
    """Resolve the repository context for a finding from its source issue (read-only).

    Args:
        source_issue: A SourceIssue JSON object.

    Returns:
        A JSON object: resolved (bool), repository (SourceRepositoryRef or null),
        ref (default branch or null), and evidence strings.
    """
    return resolve_repository_impl(source_issue)


@tool
async def verify_file_location(repository: dict, path: str, ref: str = "main") -> dict:
    """Check whether a file path exists in a repository at a ref (read-only).

    Args:
        repository: A SourceRepositoryRef JSON object.
        path: The file path to verify.
        ref: The git ref/branch to check (defaults to "main").

    Returns:
        A JSON object: file_exists (bool), ref, sha, and evidence strings.
    """
    return await verify_file_location_impl(repository, path, ref)
