from __future__ import annotations

import httpx

from ado_swarm.contracts.source_provider import SourceIssue, SourceProviderKind, SourceRepositoryRef
from ado_swarm.tools.source_providers.stub import StubSourceProvider


class AzureDevOpsSourceProvider(StubSourceProvider):
    provider_name = SourceProviderKind.AZURE_DEVOPS.value

    def __init__(self, org_url: str, project: str, pat: str) -> None:
        super().__init__()
        self.org_url = org_url.rstrip("/")
        self.project = project
        self.client = httpx.AsyncClient(auth=("", pat), timeout=30)

    async def get_issue(self, external_id: str) -> SourceIssue:
        # The concrete REST mapping is intentionally isolated here; tests use the stub provider.
        url = f"{self.org_url}/{self.project}/_apis/wit/workitems/{external_id}?api-version=7.1"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        fields = data.get("fields", {})
        return SourceIssue(
            provider=SourceProviderKind.AZURE_DEVOPS,
            external_id=str(data["id"]),
            url=data.get("_links", {}).get("html", {}).get("href", url),
            title=fields.get("System.Title", ""),
            body=fields.get("System.Description"),
            state=fields.get("System.State", "unknown"),
            labels=[tag.strip() for tag in fields.get("System.Tags", "").split(";") if tag.strip()],
            provider_payload=data,
        )

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef:
        return SourceRepositoryRef(
            provider=SourceProviderKind.AZURE_DEVOPS,
            external_id=f"{owner_or_project}/{name}",
            owner_or_project=owner_or_project,
            name=name,
            default_branch="main",
        )
