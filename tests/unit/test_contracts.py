from ado_swarm.contracts.source_provider import SourceIssue, SourceProviderKind


def test_source_issue_preserves_provider_identity() -> None:
    issue = SourceIssue(
        provider=SourceProviderKind.STUB,
        external_id="SEC-1",
        url="https://example.invalid",
        title="x",
    )
    assert issue.provider == SourceProviderKind.STUB
    assert issue.external_id == "SEC-1"
