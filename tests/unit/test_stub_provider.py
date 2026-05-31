import pytest

from ado_swarm.tools.source_providers.stub import StubSourceProvider


@pytest.mark.asyncio
async def test_stub_provider_returns_issue() -> None:
    provider = StubSourceProvider()
    issue = await provider.get_issue("SEC-123")
    assert issue.external_id == "SEC-123"
    assert issue.repository is not None
