from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import httpx

from ado_swarm.contracts.source_provider import (
    ProviderMutationResult,
    SourceBranch,
    SourceCommit,
    SourceFile,
    SourceIssue,
    SourceIssuePage,
    SourceProviderKind,
    SourcePullRequest,
    SourceRepositoryRef,
)
from ado_swarm.tools.source_providers.base import HttpProviderMixin


class GitHubSourceProvider(HttpProviderMixin):
    provider_name = SourceProviderKind.GITHUB.value

    _page_size = 100

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

    @staticmethod
    def _has_next_page(response: httpx.Response) -> bool:
        return 'rel="next"' in response.headers.get("Link", "")

    async def get_issue(self, external_id: str) -> SourceIssue:
        repo, number = external_id.split("#", 1)
        repo_ref = await self.get_repository(self.owner, repo)
        data = await self._request("GET", f"/repos/{self.owner}/{repo}/issues/{number}")
        return self._issue(data, repo_ref)

    async def search_issues(self, query: str, *, limit: int = 50) -> SourceIssuePage:
        q = f"{query} org:{self.owner}" if "org:" not in query and "repo:" not in query else query
        items: list[SourceIssue] = []
        page = 1
        while len(items) < limit:
            per_page = min(self._page_size, limit - len(items))
            response = await self._raw_request(
                "GET",
                "/search/issues",
                params={"q": q, "per_page": per_page, "page": page},
            )
            data = self._json_or_raise(response, "GET", "/search/issues")
            results = data.get("items", [])
            for item in results:
                items.append(self._issue(item))
                if len(items) >= limit:
                    break
            if not results or not self._has_next_page(response):
                break
            page += 1
        return SourceIssuePage(
            provider=SourceProviderKind.GITHUB, items=items[:limit], query=query, limit=limit
        )

    async def add_issue_comment(self, external_id: str, body: str) -> ProviderMutationResult:
        repo, number = external_id.split("#", 1)
        data = await self._request(
            "POST", f"/repos/{self.owner}/{repo}/issues/{number}/comments", json={"body": body}
        )
        return ProviderMutationResult(
            provider=SourceProviderKind.GITHUB,
            ok=True,
            external_id=str(data["id"]),
            url=data["html_url"],
            message="GitHub issue comment created",
            provider_payload=data,
        )

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef:
        data = await self._request("GET", f"/repos/{owner_or_project}/{name}")
        return self._repo_ref(data)

    async def list_branches(
        self, repository: SourceRepositoryRef, *, limit: int = 100
    ) -> list[SourceBranch]:
        url = f"/repos/{repository.owner_or_project}/{repository.name}/branches"
        branches: list[SourceBranch] = []
        page = 1
        while len(branches) < limit:
            per_page = min(self._page_size, limit - len(branches))
            response = await self._raw_request(
                "GET", url, params={"per_page": per_page, "page": page}
            )
            data = self._json_or_raise(response, "GET", url)
            for item in data:
                branches.append(
                    SourceBranch(
                        repository=repository,
                        name=item["name"],
                        sha=item.get("commit", {}).get("sha"),
                        protected=item.get("protected", False),
                        provider_payload=item,
                    )
                )
                if len(branches) >= limit:
                    break
            if not data or not self._has_next_page(response):
                break
            page += 1
        return branches[:limit]

    async def get_file(self, repository: SourceRepositoryRef, path: str, ref: str) -> SourceFile:
        data = await self._request(
            "GET",
            f"/repos/{repository.owner_or_project}/{repository.name}/contents/{path}",
            params={"ref": ref},
        )
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

    async def list_commits(
        self, repository: SourceRepositoryRef, path: str, *, ref: str = "main", limit: int = 20
    ) -> list[SourceCommit]:
        data = await self._request(
            "GET",
            f"/repos/{repository.owner_or_project}/{repository.name}/commits",
            params={"path": path, "sha": ref, "per_page": limit},
        )
        commits: list[SourceCommit] = []
        for entry in (data or [])[:limit]:
            commit = entry.get("commit", {})
            author = commit.get("author", {})
            committed_at = None
            if author.get("date"):
                committed_at = datetime.fromisoformat(author["date"].replace("Z", "+00:00"))
            commits.append(
                SourceCommit(
                    repository=repository,
                    sha=entry.get("sha", ""),
                    message=commit.get("message", ""),
                    author=author.get("name"),
                    committed_at=committed_at,
                    url=entry.get("html_url"),
                )
            )
        return commits

    async def create_draft_pr(
        self,
        repository: SourceRepositoryRef,
        title: str,
        source_branch: str,
        target_branch: str,
        body: str,
    ) -> SourcePullRequest:
        data = await self._request(
            "POST",
            f"/repos/{repository.owner_or_project}/{repository.name}/pulls",
            json={
                "title": title,
                "head": source_branch,
                "base": target_branch,
                "body": body,
                "draft": True,
            },
        )
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
        data = await self._request(
            "POST",
            f"/repos/{repository.owner_or_project}/{repository.name}/issues/{pr_external_id}/comments",
            json={"body": body},
        )
        return ProviderMutationResult(
            provider=SourceProviderKind.GITHUB,
            ok=True,
            external_id=str(data["id"]),
            url=data["html_url"],
            message="GitHub pull request comment created",
            provider_payload=data,
        )
