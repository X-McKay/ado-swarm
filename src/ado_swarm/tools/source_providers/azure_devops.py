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


class AzureDevOpsSourceProvider:
    provider_name = SourceProviderKind.AZURE_DEVOPS.value

    def __init__(self, org_url: str, project: str, pat: str) -> None:
        self.org_url = org_url.rstrip("/")
        self.project = project
        token = base64.b64encode(f":{pat}".encode()).decode()
        self.client = httpx.AsyncClient(
            base_url=f"{self.org_url}/{self.project}/_apis",
            headers={"Authorization": f"Basic {token}"},
            timeout=30,
        )

    def _parse_dt(self, value: str | None) -> datetime:
        return datetime.fromisoformat((value or "1970-01-01T00:00:00Z").replace("Z", "+00:00"))

    def _repo_ref(self, data: dict[str, Any]) -> SourceRepositoryRef:
        return SourceRepositoryRef(
            provider=SourceProviderKind.AZURE_DEVOPS,
            external_id=data["id"],
            owner_or_project=self.project,
            name=data["name"],
            default_branch=(data.get("defaultBranch") or "refs/heads/main").removeprefix(
                "refs/heads/"
            ),
            clone_url=data.get("remoteUrl"),
            web_url=data.get("webUrl"),
        )

    def _issue(self, data: dict[str, Any]) -> SourceIssue:
        fields = data.get("fields", {})
        return SourceIssue(
            provider=SourceProviderKind.AZURE_DEVOPS,
            external_id=str(data["id"]),
            url=data.get("_links", {}).get("html", {}).get("href", ""),
            title=fields.get("System.Title", ""),
            body=fields.get("System.Description"),
            state=fields.get("System.State", "unknown"),
            labels=[tag.strip() for tag in fields.get("System.Tags", "").split(";") if tag.strip()],
            created_at=self._parse_dt(fields.get("System.CreatedDate")),
            updated_at=self._parse_dt(fields.get("System.ChangedDate")),
            provider_payload=data,
        )

    async def get_issue(self, external_id: str) -> SourceIssue:
        response = await self.client.get(
            f"/wit/workitems/{external_id}", params={"api-version": "7.1"}
        )
        response.raise_for_status()
        return self._issue(response.json())

    async def search_issues(self, query: str, *, limit: int = 50) -> SourceIssuePage:
        escaped_query = query.replace("'", "''")
        wiql_query = (
            "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "  # noqa: S608
            f"AND [System.Title] CONTAINS '{escaped_query}' "
            "ORDER BY [System.ChangedDate] DESC"
        )
        wiql = {"query": wiql_query}
        response = await self.client.post(
            "/wit/wiql", params={"api-version": "7.1", "$top": limit}, json=wiql
        )
        response.raise_for_status()
        ids = [str(item["id"]) for item in response.json().get("workItems", [])[:limit]]
        items = [await self.get_issue(item_id) for item_id in ids]
        return SourceIssuePage(
            provider=SourceProviderKind.AZURE_DEVOPS, items=items, query=query, limit=limit
        )

    async def add_issue_comment(self, external_id: str, body: str) -> ProviderMutationResult:
        response = await self.client.post(
            f"/wit/workItems/{external_id}/comments",
            params={"api-version": "7.1-preview.4"},
            json={"text": body},
        )
        response.raise_for_status()
        data = response.json()
        return ProviderMutationResult(
            provider=SourceProviderKind.AZURE_DEVOPS,
            ok=True,
            external_id=str(data.get("id", external_id)),
            url=data.get("url"),
            message="Azure DevOps work item comment created",
            provider_payload=data,
        )

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef:
        response = await self.client.get(f"/git/repositories/{name}", params={"api-version": "7.1"})
        response.raise_for_status()
        return self._repo_ref(response.json())

    async def list_branches(
        self, repository: SourceRepositoryRef, *, limit: int = 100
    ) -> list[SourceBranch]:
        response = await self.client.get(
            f"/git/repositories/{repository.external_id}/refs",
            params={"api-version": "7.1", "filter": "heads/", "peelTags": "false"},
        )
        response.raise_for_status()
        return [
            SourceBranch(
                repository=repository,
                name=item["name"].removeprefix("refs/heads/"),
                sha=item.get("objectId"),
                provider_payload=item,
            )
            for item in response.json().get("value", [])[:limit]
        ]

    async def get_file(self, repository: SourceRepositoryRef, path: str, ref: str) -> SourceFile:
        response = await self.client.get(
            f"/git/repositories/{repository.external_id}/items",
            params={
                "api-version": "7.1",
                "path": path,
                "versionDescriptor.version": ref,
                "includeContent": "true",
            },
        )
        response.raise_for_status()
        data = response.json()
        return SourceFile(
            repository=repository,
            path=path,
            ref=ref,
            content=data.get("content", ""),
            sha=data.get("commitId"),
            url=data.get("url"),
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
            f"/git/repositories/{repository.external_id}/pullrequests",
            params={"api-version": "7.1"},
            json={
                "sourceRefName": f"refs/heads/{source_branch}",
                "targetRefName": f"refs/heads/{target_branch}",
                "title": title,
                "description": body,
                "isDraft": True,
            },
        )
        response.raise_for_status()
        data = response.json()
        return SourcePullRequest(
            provider=SourceProviderKind.AZURE_DEVOPS,
            external_id=str(data["pullRequestId"]),
            url=data.get("url", ""),
            title=data.get("title", title),
            source_branch=source_branch,
            target_branch=target_branch,
            is_draft=data.get("isDraft", True),
            state=data.get("status", "open"),
            provider_payload=data,
        )

    async def add_pr_comment(
        self, repository: SourceRepositoryRef, pr_external_id: str, body: str
    ) -> ProviderMutationResult:
        response = await self.client.post(
            f"/git/repositories/{repository.external_id}/pullRequests/{pr_external_id}/threads",
            params={"api-version": "7.1"},
            json={
                "comments": [{"parentCommentId": 0, "content": body, "commentType": 1}],
                "status": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        return ProviderMutationResult(
            provider=SourceProviderKind.AZURE_DEVOPS,
            ok=True,
            external_id=str(data.get("id", pr_external_id)),
            url=data.get("url"),
            message="Azure DevOps pull request thread created",
            provider_payload=data,
        )
