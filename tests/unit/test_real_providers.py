from __future__ import annotations

import base64

import httpx
import pytest
import respx

from ado_swarm.contracts.source_provider import (
    SourceFile,
    SourceIssue,
    SourceProviderKind,
    SourceRepositoryRef,
)
from ado_swarm.tools.source_providers.azure_devops import AzureDevOpsSourceProvider
from ado_swarm.tools.source_providers.base import ProviderError
from ado_swarm.tools.source_providers.github import GitHubSourceProvider

ADO_ORG = "https://dev.azure.com/contoso"
ADO_PROJECT = "secproj"
ADO_BASE = f"{ADO_ORG}/{ADO_PROJECT}/_apis"
GH_BASE = "https://api.github.com"


def _fast_retries(provider: AzureDevOpsSourceProvider | GitHubSourceProvider) -> None:
    """Make retry sleeps effectively instant so tests stay fast."""
    provider._default_retry_after = 0.0  # type: ignore[attr-defined]
    provider._max_retry_after = 0.0  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Azure DevOps
# --------------------------------------------------------------------------- #


def _ado_workitem(item_id: int) -> dict:
    return {
        "id": item_id,
        "_links": {"html": {"href": f"https://dev.azure.com/contoso/wi/{item_id}"}},
        "fields": {
            "System.Title": f"Issue {item_id}",
            "System.Description": "body",
            "System.State": "Active",
            "System.Tags": "security; dependency",
            "System.CreatedDate": "2026-01-01T00:00:00Z",
            "System.ChangedDate": "2026-01-02T00:00:00Z",
        },
    }


@pytest.mark.asyncio
@respx.mock
async def test_ado_get_issue_parses_contract() -> None:
    respx.get(f"{ADO_BASE}/wit/workitems/42").mock(
        return_value=httpx.Response(200, json=_ado_workitem(42))
    )
    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        issue = await provider.get_issue("42")
    assert isinstance(issue, SourceIssue)
    assert issue.provider is SourceProviderKind.AZURE_DEVOPS
    assert issue.external_id == "42"
    assert issue.title == "Issue 42"
    assert issue.labels == ["security", "dependency"]


@pytest.mark.asyncio
@respx.mock
async def test_ado_get_file_parses_contract() -> None:
    repo = SourceRepositoryRef(
        provider=SourceProviderKind.AZURE_DEVOPS,
        external_id="repo-1",
        owner_or_project=ADO_PROJECT,
        name="repo",
    )
    respx.get(f"{ADO_BASE}/git/repositories/repo-1/items").mock(
        return_value=httpx.Response(
            200, json={"content": "print('hi')\n", "commitId": "abc", "url": "u"}
        )
    )
    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        file = await provider.get_file(repo, "main.py", "main")
    assert isinstance(file, SourceFile)
    assert file.content == "print('hi')\n"
    assert file.sha == "abc"


@pytest.mark.asyncio
@respx.mock
async def test_ado_list_branches_paginates() -> None:
    repo = SourceRepositoryRef(
        provider=SourceProviderKind.AZURE_DEVOPS,
        external_id="repo-1",
        owner_or_project=ADO_PROJECT,
        name="repo",
    )
    route = respx.get(f"{ADO_BASE}/git/repositories/repo-1/refs")
    route.side_effect = [
        httpx.Response(
            200,
            headers={"x-ms-continuationtoken": "tok"},
            json={"value": [{"name": "refs/heads/a", "objectId": "1"}]},
        ),
        httpx.Response(
            200,
            json={"value": [{"name": "refs/heads/b", "objectId": "2"}]},
        ),
    ]
    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        branches = await provider.list_branches(repo, limit=10)
    assert [b.name for b in branches] == ["a", "b"]
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_ado_list_branches_respects_limit() -> None:
    repo = SourceRepositoryRef(
        provider=SourceProviderKind.AZURE_DEVOPS,
        external_id="repo-1",
        owner_or_project=ADO_PROJECT,
        name="repo",
    )
    respx.get(f"{ADO_BASE}/git/repositories/repo-1/refs").mock(
        return_value=httpx.Response(
            200,
            headers={"x-ms-continuationtoken": "tok"},
            json={
                "value": [
                    {"name": "refs/heads/a", "objectId": "1"},
                    {"name": "refs/heads/b", "objectId": "2"},
                ]
            },
        )
    )
    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        branches = await provider.list_branches(repo, limit=1)
    assert [b.name for b in branches] == ["a"]


@pytest.mark.asyncio
@respx.mock
async def test_ado_retries_on_429_then_succeeds() -> None:
    route = respx.get(f"{ADO_BASE}/wit/workitems/7")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json=_ado_workitem(7)),
    ]
    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        _fast_retries(provider)
        issue = await provider.get_issue("7")
    assert issue.external_id == "7"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_ado_persistent_500_raises_provider_error() -> None:
    respx.get(f"{ADO_BASE}/wit/workitems/9").mock(return_value=httpx.Response(500))
    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        with pytest.raises(ProviderError) as exc:
            await provider.get_issue("9")
    assert exc.value.status_code == 500
    assert exc.value.provider == SourceProviderKind.AZURE_DEVOPS.value


@pytest.mark.asyncio
@respx.mock
async def test_ado_persistent_429_raises_provider_error() -> None:
    respx.get(f"{ADO_BASE}/wit/workitems/9").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"})
    )
    async with AzureDevOpsSourceProvider(ADO_ORG, ADO_PROJECT, "pat") as provider:
        _fast_retries(provider)
        with pytest.raises(ProviderError) as exc:
            await provider.get_issue("9")
    assert exc.value.status_code == 429


# --------------------------------------------------------------------------- #
# GitHub
# --------------------------------------------------------------------------- #


def _gh_repo() -> dict:
    return {
        "full_name": "octo/repo",
        "name": "repo",
        "owner": {"login": "octo"},
        "default_branch": "main",
        "clone_url": "https://github.com/octo/repo.git",
        "html_url": "https://github.com/octo/repo",
    }


def _gh_issue(number: int) -> dict:
    return {
        "number": number,
        "html_url": f"https://github.com/octo/repo/issues/{number}",
        "title": f"Issue {number}",
        "body": "body",
        "state": "open",
        "labels": [{"name": "bug"}],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }


@pytest.mark.asyncio
@respx.mock
async def test_github_get_issue_parses_contract() -> None:
    respx.get(f"{GH_BASE}/repos/octo/repo").mock(return_value=httpx.Response(200, json=_gh_repo()))
    respx.get(f"{GH_BASE}/repos/octo/repo/issues/5").mock(
        return_value=httpx.Response(200, json=_gh_issue(5))
    )
    async with GitHubSourceProvider("token", "octo") as provider:
        issue = await provider.get_issue("repo#5")
    assert isinstance(issue, SourceIssue)
    assert issue.provider is SourceProviderKind.GITHUB
    assert issue.external_id == "repo#5"
    assert issue.repository is not None
    assert issue.repository.name == "repo"


@pytest.mark.asyncio
@respx.mock
async def test_github_get_file_parses_contract() -> None:
    repo = SourceRepositoryRef(
        provider=SourceProviderKind.GITHUB,
        external_id="octo/repo",
        owner_or_project="octo",
        name="repo",
    )
    encoded = base64.b64encode(b"hello\n").decode()
    respx.get(f"{GH_BASE}/repos/octo/repo/contents/README.md").mock(
        return_value=httpx.Response(
            200,
            json={
                "content": encoded,
                "encoding": "base64",
                "sha": "deadbeef",
                "html_url": "https://github.com/octo/repo/blob/main/README.md",
            },
        )
    )
    async with GitHubSourceProvider("token", "octo") as provider:
        file = await provider.get_file(repo, "README.md", "main")
    assert isinstance(file, SourceFile)
    assert file.content == "hello\n"
    assert file.sha == "deadbeef"


@pytest.mark.asyncio
@respx.mock
async def test_github_search_issues_paginates() -> None:
    route = respx.get(f"{GH_BASE}/search/issues")
    next_link = f'<{GH_BASE}/search/issues?page=2>; rel="next"'
    route.side_effect = [
        httpx.Response(200, headers={"Link": next_link}, json={"items": [_gh_issue(1)]}),
        httpx.Response(200, json={"items": [_gh_issue(2)]}),
    ]
    async with GitHubSourceProvider("token", "octo") as provider:
        page = await provider.search_issues("vuln", limit=10)
    assert [i.provider_payload["number"] for i in page.items] == [1, 2]
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_github_list_branches_paginates() -> None:
    repo = SourceRepositoryRef(
        provider=SourceProviderKind.GITHUB,
        external_id="octo/repo",
        owner_or_project="octo",
        name="repo",
    )
    route = respx.get(f"{GH_BASE}/repos/octo/repo/branches")
    next_link = f'<{GH_BASE}/repos/octo/repo/branches?page=2>; rel="next"'
    route.side_effect = [
        httpx.Response(
            200,
            headers={"Link": next_link},
            json=[{"name": "main", "commit": {"sha": "a"}}],
        ),
        httpx.Response(200, json=[{"name": "dev", "commit": {"sha": "b"}}]),
    ]
    async with GitHubSourceProvider("token", "octo") as provider:
        branches = await provider.list_branches(repo, limit=10)
    assert [b.name for b in branches] == ["main", "dev"]
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_github_search_respects_limit() -> None:
    respx.get(f"{GH_BASE}/search/issues").mock(
        return_value=httpx.Response(
            200,
            headers={"Link": f'<{GH_BASE}/search/issues?page=2>; rel="next"'},
            json={"items": [_gh_issue(1), _gh_issue(2)]},
        )
    )
    async with GitHubSourceProvider("token", "octo") as provider:
        page = await provider.search_issues("vuln", limit=1)
    assert len(page.items) == 1


@pytest.mark.asyncio
@respx.mock
async def test_github_retries_on_429_then_succeeds() -> None:
    respx.get(f"{GH_BASE}/repos/octo/repo").mock(return_value=httpx.Response(200, json=_gh_repo()))
    route = respx.get(f"{GH_BASE}/repos/octo/repo/issues/5")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json=_gh_issue(5)),
    ]
    async with GitHubSourceProvider("token", "octo") as provider:
        _fast_retries(provider)
        issue = await provider.get_issue("repo#5")
    assert issue.external_id == "repo#5"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_github_persistent_404_raises_provider_error() -> None:
    respx.get(f"{GH_BASE}/repos/octo/repo").mock(return_value=httpx.Response(404))
    async with GitHubSourceProvider("token", "octo") as provider:
        with pytest.raises(ProviderError) as exc:
            await provider.get_repository("octo", "repo")
    assert exc.value.status_code == 404
    assert exc.value.provider == SourceProviderKind.GITHUB.value


@pytest.mark.asyncio
@respx.mock
async def test_transport_error_raises_provider_error() -> None:
    respx.get(f"{GH_BASE}/repos/octo/repo").mock(side_effect=httpx.ConnectError("boom"))
    async with GitHubSourceProvider("token", "octo") as provider:
        with pytest.raises(ProviderError):
            await provider.get_repository("octo", "repo")


@pytest.mark.asyncio
@respx.mock
async def test_provider_usable_without_context_manager() -> None:
    respx.get(f"{GH_BASE}/repos/octo/repo").mock(return_value=httpx.Response(200, json=_gh_repo()))
    provider = GitHubSourceProvider("token", "octo")
    try:
        repo = await provider.get_repository("octo", "repo")
        assert repo.name == "repo"
    finally:
        await provider.aclose()
