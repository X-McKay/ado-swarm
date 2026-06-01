from __future__ import annotations

from datetime import UTC, datetime

from ado_swarm.contracts.source_provider import (
    MutationResultKind,
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

    async def search_issues(self, query: str, *, limit: int = 50) -> SourceIssuePage:
        issue = self.issue.model_copy(update={"provider_payload": {"query": query}})
        return SourceIssuePage(
            provider=SourceProviderKind.STUB, items=[issue][:limit], query=query, limit=limit
        )

    async def add_issue_comment(self, external_id: str, body: str) -> ProviderMutationResult:
        return ProviderMutationResult(
            provider=SourceProviderKind.STUB,
            ok=True,
            result_kind=MutationResultKind.ISSUE_COMMENT,
            external_id="stub-comment-1",
            url=f"https://example.invalid/issues/{external_id}#comment-1",
            message="stub issue comment recorded",
            provider_payload={"body": body, "issue_external_id": external_id},
        )

    async def get_repository(self, owner_or_project: str, name: str) -> SourceRepositoryRef:
        return self.repository.model_copy(
            update={"owner_or_project": owner_or_project, "name": name}
        )

    async def list_branches(
        self, repository: SourceRepositoryRef, *, limit: int = 100
    ) -> list[SourceBranch]:
        return [
            SourceBranch(
                repository=repository, name=repository.default_branch or "main", sha="stub-sha"
            )
        ]

    async def get_file(self, repository: SourceRepositoryRef, path: str, ref: str) -> SourceFile:
        return SourceFile(
            repository=repository, path=path, ref=ref, content="stub content\n", sha="stub-sha"
        )

    async def list_commits(
        self, repository: SourceRepositoryRef, path: str, *, ref: str = "main", limit: int = 20
    ) -> list[SourceCommit]:
        return [
            SourceCommit(
                repository=repository,
                sha="stub-sha-1",
                message=f"stub commit touching {path}",
                author="stub-author",
                committed_at=datetime(2024, 1, 1, tzinfo=UTC),
                url="https://example.invalid/commit/stub-sha-1",
            )
        ][:limit]

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

    async def add_pr_comment(
        self, repository: SourceRepositoryRef, pr_external_id: str, body: str
    ) -> ProviderMutationResult:
        return ProviderMutationResult(
            provider=SourceProviderKind.STUB,
            ok=True,
            result_kind=MutationResultKind.PR_COMMENT,
            external_id="stub-pr-comment-1",
            url=f"{repository.web_url}/pull/{pr_external_id}#comment-1",
            message="stub pull request comment recorded",
            provider_payload={"body": body, "pr_external_id": pr_external_id},
        )
