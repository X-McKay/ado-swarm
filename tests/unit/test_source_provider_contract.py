import pytest

from ado_swarm.tools.source_providers.stub import StubSourceProvider


@pytest.mark.asyncio
async def test_stub_provider_implements_full_contract() -> None:
    provider = StubSourceProvider()
    issue_page = await provider.search_issues("security")
    issue = await provider.get_issue("SEC-123")
    repo = await provider.get_repository("stub", "repo")
    branches = await provider.list_branches(repo)
    source_file = await provider.get_file(repo, "README.md", "main")
    pr = await provider.create_draft_pr(repo, "title", "fix", "main", "body")
    issue_comment = await provider.add_issue_comment(issue.external_id, "comment")
    pr_comment = await provider.add_pr_comment(repo, pr.external_id, "comment")

    assert issue_page.items
    assert branches[0].name == "main"
    assert source_file.content
    assert pr.is_draft
    assert issue_comment.ok
    assert pr_comment.ok
