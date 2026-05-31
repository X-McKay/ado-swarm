from __future__ import annotations

from typing import Protocol

from ado_swarm.contracts.source_provider import (
    ProviderMutationResult,
    SourceBranch,
    SourceFile,
    SourceIssue,
    SourceIssuePage,
    SourcePullRequest,
    SourceRepositoryRef,
)


class SourceProvider(Protocol):
    provider_name: str

    async def get_issue(self, external_id: str) -> SourceIssue: ...

    async def search_issues(self, query: str, *, limit: int = 50) -> SourceIssuePage: ...

    async def add_issue_comment(self, external_id: str, body: str) -> ProviderMutationResult: ...

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef: ...

    async def list_branches(
        self, repository: SourceRepositoryRef, *, limit: int = 100
    ) -> list[SourceBranch]: ...

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

    async def add_pr_comment(
        self, repository: SourceRepositoryRef, pr_external_id: str, body: str
    ) -> ProviderMutationResult: ...
