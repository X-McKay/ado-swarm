from __future__ import annotations

import pytest

from ado_swarm.tools.catalog.provider import provider_get_issue_impl, provider_search_issues_impl
from ado_swarm.tools.source_providers.providers import close_source_provider, set_source_provider
from ado_swarm.tools.source_providers.stub import StubSourceProvider


@pytest.fixture(autouse=True)
async def _stub_provider_runtime():
    await close_source_provider()
    set_source_provider(StubSourceProvider())
    yield
    await close_source_provider()


async def test_provider_tool_runtime_roundtrip_uses_injected_source_provider() -> None:
    issue = await provider_get_issue_impl("SEC-INTEGRATION")
    page = await provider_search_issues_impl("security", limit=1)

    assert issue["external_id"] == "SEC-INTEGRATION"
    assert page["items"]
    assert page["limit"] == 1
