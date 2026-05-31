from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import httpx

from ado_swarm.contracts.source_provider import (
    ProviderMutationResult,
    SourceBranch,
    SourceFile,
    SourceIssue,
    SourceIssuePage,
    SourceProviderKind,
    SourcePullRequest,
    SourceRepositoryRef,
)


class GitHubSourceProvider:
    provider_name = SourceProviderKind.GITHUB.value

    def __init__(self, token: str, owner: str) -> None:
        self.owner = owner
        self.client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=30,
        )

    def _repo_ref(self, repo: dict[str, Any]) -> SourceRepositoryRef:
        return SourceRepositoryRef(
            provider=SourceProviderKind.GITHUB,
            external_id=repo["full_name"],
            owner_or_project=repo["owner"]["login"],
            name=repo["name"],
            default_branch=repo.get("default_branch"),
            clone_url=repo.get("clone_url"),
            web_url=repo.get("html_url"),
        )

    def _issue(
        self, data: dict[str, Any], repository: SourceRepositoryRef | None = None
    ) -> SourceIssue:
        repo_ref = repository
        if repo_ref is None and "repository" in data:
            repo_ref = self._repo_ref(data["repository"])
        return SourceIssue(
            provider=SourceProviderKind.GITHUB,
            external_id=str(
                data["number"] if repo_ref is None else f"{repo_ref.name}#{data['number']}"
            ),
            url=data["html_url"],
            title=data["title"],
            body=data.get("body"),
            state=data.get("state", "unknown"),
            labels=[label["name"] for label in data.get("labels", [])],
            repository=repo_ref,
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            provider_payload=data,
        )

    async def get_issue(self, external_id: str) -> SourceIssue:
        repo, number = external_id.split("#", 1)
        repo_ref = await self.get_repository(self.owner, repo)
        response = await self.client.get(f"/repos/{self.owner}/{repo}/issues/{number}")
        response.raise_for_status()
        return self._issue(response.json(), repo_ref)

    async def search_issues(self, query: str, *, limit: int = 50) -> SourceIssuePage:
        q = f"{query} org:{self.owner}" if "org:" not in query and "repo:" not in query else query
        response = await self.client.get(
            "/search/issues", params={"q": q, "per_page": min(limit, 100)}
        )
        response.raise_for_status()
        items = [self._issue(item) for item in response.json().get("items", [])[:limit]]
        return SourceIssuePage(
            provider=SourceProviderKind.GITHUB, items=items, query=query, limit=limit
        )

    async def add_issue_comment(self, external_id: str, body: str) -> ProviderMutationResult:
        repo, number = external_id.split("#", 1)
        response = await self.client.post(
            f"/repos/{self.owner}/{repo}/issues/{number}/comments", json={"body": body}
        )
        response.raise_for_status()
        data = response.json()
        return ProviderMutationResult(
            provider=SourceProviderKind.GITHUB,
            ok=True,
            external_id=str(data["id"]),
            url=data["html_url"],
            message="GitHub issue comment created",
            provider_payload=data,
        )

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef:
        response = await self.client.get(f"/repos/{owner_or_project}/{name}")
        response.raise_for_status()
        return self._repo_ref(response.json())

    async def list_branches(
        self, repository: SourceRepositoryRef, *, limit: int = 100
    ) -> list[SourceBranch]:
        response = await self.client.get(
            f"/repos/{repository.owner_or_project}/{repository.name}/branches",
            params={"per_page": min(limit, 100)},
        )
        response.raise_for_status()
        return [
            SourceBranch(
                repository=repository,
                name=item["name"],
                sha=item.get("commit", {}).get("sha"),
                protected=item.get("protected", False),
                provider_payload=item,
            )
            for item in response.json()[:limit]
        ]

    async def get_file(self, repository: SourceRepositoryRef, path: str, ref: str) -> SourceFile:
        response = await self.client.get(
            f"/repos/{repository.owner_or_project}/{repository.name}/contents/{path}",
            params={"ref": ref},
        )
        response.raise_for_status()
        data = response.json()
        content = (
            base64.b64decode(data.get("content", "")).decode()
            if data.get("encoding") == "base64"
            else ""
        )
        return SourceFile(
            repository=repository,
            path=path,
            ref=ref,
            content=content,
            sha=data.get("sha"),
            url=data.get("html_url"),
        )

    async def create_draft_pr(
        self,
        repository: SourceRepositoryRef,
        title: str,
        source_branch: str,
        target_branch: str,
        body: str,
    ) -> SourcePullRequest:
        response = await self.client.post(
            f"/repos/{repository.owner_or_project}/{repository.name}/pulls",
            json={
                "title": title,
                "head": source_branch,
                "base": target_branch,
                "body": body,
                "draft": True,
            },
        )
        response.raise_for_status()
        data = response.json()
        return SourcePullRequest(
            provider=SourceProviderKind.GITHUB,
            external_id=str(data["number"]),
            url=data["html_url"],
            title=data["title"],
            source_branch=source_branch,
            target_branch=target_branch,
            is_draft=data.get("draft", True),
            state=data.get("state", "open"),
            provider_payload=data,
        )

    async def add_pr_comment(
        self, repository: SourceRepositoryRef, pr_external_id: str, body: str
    ) -> ProviderMutationResult:
        response = await self.client.post(
            f"/repos/{repository.owner_or_project}/{repository.name}/issues/{pr_external_id}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        data = response.json()
        return ProviderMutationResult(
            provider=SourceProviderKind.GITHUB,
            ok=True,
            external_id=str(data["id"]),
            url=data["html_url"],
            message="GitHub pull request comment created",
            provider_payload=data,
        )
