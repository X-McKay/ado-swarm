from __future__ import annotations

from datetime import UTC, datetime

from ado_swarm.contracts.source_provider import (
    SourceFile,
    SourceIssue,
    SourceProviderKind,
    SourcePullRequest,
    SourceRepositoryRef,
)


class StubSourceProvider:
    provider_name = SourceProviderKind.STUB.value

    def __init__(self) -> None:
        self.repository = SourceRepositoryRef(
            provider=SourceProviderKind.STUB,
            external_id="stub/repo",
            owner_or_project="stub",
            name="repo",
            default_branch="main",
            clone_url="https://example.invalid/stub/repo.git",
            web_url="https://example.invalid/stub/repo",
        )
        self.issue = SourceIssue(
            provider=SourceProviderKind.STUB,
            external_id="SEC-1",
            url="https://example.invalid/issues/SEC-1",
            title="Dependency vulnerability in sample package",
            body="Sample provider issue used for local tests.",
            labels=["security", "dependency"],
            repository=self.repository,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def get_issue(self, external_id: str) -> SourceIssue:
        return self.issue.model_copy(update={"external_id": external_id})

    async def search_issues(self, query: str, *, limit: int = 50) -> list[SourceIssue]:
        return [self.issue.model_copy(update={"provider_payload": {"query": query}})][:limit]

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef:
        return self.repository.model_copy(
            update={"owner_or_project": owner_or_project, "name": name}
        )

    async def get_file(self, repository: SourceRepositoryRef, path: str, ref: str) -> SourceFile:
        return SourceFile(
            repository=repository, path=path, ref=ref, content="stub content\n", sha="stub-sha"
        )

    async def create_draft_pr(
        self,
        repository: SourceRepositoryRef,
        title: str,
        source_branch: str,
        target_branch: str,
        body: str,
    ) -> SourcePullRequest:
        return SourcePullRequest(
            provider=SourceProviderKind.STUB,
            external_id="PR-1",
            url="https://example.invalid/pull/1",
            title=title,
            source_branch=source_branch,
            target_branch=target_branch,
            is_draft=True,
            provider_payload={"body": body, "repository": repository.model_dump(mode="json")},
        )
