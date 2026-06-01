from __future__ import annotations

from ado_swarm.contracts.source_provider import MutationResultKind
from ado_swarm.tools.source_providers.stub import StubSourceProvider

STUB_REPO_FIELDS = {
    "provider": "stub",
    "external_id": "repo-1",
    "owner_or_project": "acme",
    "name": "service",
    "default_branch": "main",
    "web_url": "https://example.invalid/acme/service",
}


async def test_issue_comment_result_kind_and_id() -> None:
    provider = StubSourceProvider()
    result = await provider.add_issue_comment("SEC-1", "hello")
    # external_id identifies the created COMMENT, not the parent issue.
    assert result.result_kind == MutationResultKind.ISSUE_COMMENT
    assert result.external_id == "stub-comment-1"
    assert result.provider_payload["issue_external_id"] == "SEC-1"


async def test_pr_comment_result_kind_and_id() -> None:
    from ado_swarm.contracts.source_provider import SourceRepositoryRef

    provider = StubSourceProvider()
    repo = SourceRepositoryRef.model_validate(STUB_REPO_FIELDS)
    result = await provider.add_pr_comment(repo, "PR-1", "validated")
    assert result.result_kind == MutationResultKind.PR_COMMENT
    assert result.external_id == "stub-pr-comment-1"
    assert result.provider_payload["pr_external_id"] == "PR-1"


async def test_issue_external_id_round_trips() -> None:
    # The id returned by get_issue is accepted back verbatim by get_issue.
    provider = StubSourceProvider()
    issue = await provider.get_issue("SEC-42")
    again = await provider.get_issue(issue.external_id)
    assert again.external_id == issue.external_id
