from __future__ import annotations

from typing import Protocol

from ado_swarm.contracts.source_provider import (
    SourceFile,
    SourceIssue,
    SourcePullRequest,
    SourceRepositoryRef,
)


class SourceProvider(Protocol):
    provider_name: str

    async def get_issue(self, external_id: str) -> SourceIssue: ...

    async def search_issues(self, query: str, *, limit: int = 50) -> list[SourceIssue]: ...

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef: ...

    async def get_file(
        self, repository: SourceRepositoryRef, path: str, ref: str
    ) -> SourceFile: ...

    async def create_draft_pr(
        self,
        repository: SourceRepositoryRef,
        title: str,
        source_branch: str,
        target_branch: str,
        body: str,
    ) -> SourcePullRequest: ...
