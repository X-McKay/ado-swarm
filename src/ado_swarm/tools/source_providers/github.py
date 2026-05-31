from __future__ import annotations

import httpx

from ado_swarm.contracts.source_provider import SourceIssue, SourceProviderKind, SourceRepositoryRef
from ado_swarm.tools.source_providers.stub import StubSourceProvider


class GitHubSourceProvider(StubSourceProvider):
    provider_name = SourceProviderKind.GITHUB.value

    def __init__(self, token: str, owner: str) -> None:
        super().__init__()
        self.owner = owner
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=30,
        )

    async def get_issue(self, external_id: str) -> SourceIssue:
        repo, number = external_id.split("#", 1)
        url = f"https://api.github.com/repos/{self.owner}/{repo}/issues/{number}"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        return SourceIssue(
            provider=SourceProviderKind.GITHUB,
            external_id=f"{repo}#{data['number']}",
            url=data["html_url"],
            title=data["title"],
            body=data.get("body"),
            state=data.get("state", "unknown"),
            labels=[label["name"] for label in data.get("labels", [])],
            repository=SourceRepositoryRef(
                provider=SourceProviderKind.GITHUB,
                external_id=f"{self.owner}/{repo}",
                owner_or_project=self.owner,
                name=repo,
            ),
            provider_payload=data,
        )
