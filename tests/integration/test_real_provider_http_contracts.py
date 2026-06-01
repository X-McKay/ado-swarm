from __future__ import annotations

import base64

import httpx
import pytest
import respx

from ado_swarm.contracts.source_provider import SourceProviderKind, SourceRepositoryRef
from ado_swarm.tools.source_providers.azure_devops import AzureDevOpsSourceProvider
from ado_swarm.tools.source_providers.github import GitHubSourceProvider

ADO_ORG = "https://dev.azure.com/contoso"
ADO_PROJECT = "security"
ADO_BASE = f"{ADO_ORG}/{ADO_PROJECT}/_apis"
GH_BASE = "https://api.github.com"


@pytest.mark.asyncio
@respx.mock
async def test_github_provider_file_commit_and_comment_contracts() -> None:
    repo = SourceRepositoryRef(
        provider=SourceProviderKind.GITHUB,
        external_id="octo/repo",
        owner_or_project="octo",
        name="repo",
        default_branch="main",
    )
    encoded = base64.b64encode(b"requests==2.31.0\n").decode()
    respx.get(f"{GH_BASE}/repos/octo/repo/contents/requirements.txt").mock(
        return_value=httpx.Response(
            200,
            json={"content": encoded, "encoding": "base64", "sha": "sha-file", "html_url": "u"},
        )
    )
    respx.get(f"{GH_BASE}/repos/octo/repo/commits").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "sha": "sha-commit",
                    "html_url": "https://github.com/octo/repo/commit/sha-commit",
                    "commit": {"message": "fix", "author": {"name": "Dev"}},
                }
            ],
        )
    )
    respx.post(f"{GH_BASE}/repos/octo/repo/issues/7/comments").mock(
        return_value=httpx.Response(
            201,
            json={"id": 123, "html_url": "https://github.com/octo/repo/issues/7#issuecomment-123"},
        )
    )

    async with GitHubSourceProvider("token", "octo") as provider:
        source_file = await provider.get_file(repo, "requirements.txt", "main")
        commits = await provider.list_commits(repo, "requirements.txt", ref="main", limit=5)
        mutation = await provider.add_issue_comment("octo/repo#7", "comment")

    assert source_file.content == "requests==2.31.0\n"
    assert commits[0].sha == "sha-commit"
    assert mutation.external_id == "123"


@pytest.mark.asyncio
@respx.mock
async def test_azure_devops_provider_file_commit_and_comment_contracts() -> None:
    repo = SourceRepositoryRef(
        provider=SourceProviderKind.AZURE_DEVOPS,
        external_id="repo-id",
        owner_or_project=ADO_PROJECT,
        name="repo",
        default_branch="main",
    )
    respx.get(f"{ADO_BASE}/git/repositories/repo-id/items").mock(
        return_value=httpx.Response(
            200, json={"content": "flask>=3\n", "commitId": "sha-file", "url": "u"}
        )
    )
    respx.get(f"{ADO_BASE}/git/repositories/repo-id/commits").mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    {
                        "commitId": "sha-commit",
                        "comment": "fix",
                        "author": {"name": "Dev", "date": "2024-01-01T00:00:00Z"},
                        "remoteUrl": "https://dev.azure.com/contoso/repo/commit/sha-commit",
                    }
                ]
            },
        )
    )
    respx.post(f"{ADO_BASE}/wit/workItems/42/comments").mock(
        return_value=httpx.Response(
            201, json={"id": 456, "url": "https://dev.azure.com/comment/456"}
        )
    )

    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        source_file = await provider.get_file(repo, "requirements.txt", "main")
        commits = await provider.list_commits(repo, "requirements.txt", ref="main", limit=5)
        mutation = await provider.add_issue_comment("42", "comment")

    assert source_file.content == "flask>=3\n"
    assert commits[0].sha == "sha-commit"
    assert mutation.external_id == "456"
