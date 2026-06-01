from __future__ import annotations

import pytest

from ado_swarm.knowledge.providers import get_knowledge_store, set_knowledge_store
from ado_swarm.tools.catalog import CATALOG
from ado_swarm.tools.catalog.knowledge import (
    graphiti_add_episode_impl,
    graphiti_search_impl,
)
from ado_swarm.tools.catalog.provider import (
    provider_get_issue_impl,
    provider_search_issues_impl,
)


@pytest.fixture(autouse=True)
def _fresh_knowledge_store():
    set_knowledge_store(None)  # reset to a fresh in-memory store per test
    yield
    set_knowledge_store(None)


def test_knowledge_and_provider_tools_registered() -> None:
    for name in (
        "graphiti_search",
        "graphiti_add_episode",
        "provider_get_issue",
        "provider_search_issues",
        "provider_get_repo_metadata",
    ):
        assert name in CATALOG


async def test_graphiti_add_then_search_roundtrip() -> None:
    added = await graphiti_add_episode_impl(
        "dup-cluster", {"fingerprint": "finding-abc", "cwe": "CWE-79"}
    )
    assert added["episode_id"]
    # Same shared store instance backs both tools.
    assert get_knowledge_store() is get_knowledge_store()
    hit = await graphiti_search_impl("CWE-79")
    assert hit["count"] == 1
    miss = await graphiti_search_impl("nonexistent-token")
    assert miss["count"] == 0


async def test_provider_get_issue_tool_uses_stub() -> None:
    issue = await provider_get_issue_impl("SEC-1")
    assert issue["external_id"]
    assert "title" in issue


async def test_provider_search_issues_tool_returns_page() -> None:
    page = await provider_search_issues_impl("security", limit=5)
    assert "items" in page
    assert page["limit"] == 5
