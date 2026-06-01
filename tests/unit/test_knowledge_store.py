from __future__ import annotations

from typing import Any

import pytest

from ado_swarm.config import Settings
from ado_swarm.knowledge import providers
from ado_swarm.knowledge.graphiti_store import (
    GraphitiKnowledgeStore,
    KnowledgeStore,
    KnowledgeStorePort,
)
from ado_swarm.knowledge.providers import get_knowledge_store, set_knowledge_store


@pytest.fixture(autouse=True)
def _fresh_knowledge_store():
    set_knowledge_store(None)
    yield
    set_knowledge_store(None)


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "",
    }
    base.update(overrides)
    return Settings(**base)


def test_in_memory_store_conforms_to_port() -> None:
    store = KnowledgeStore()
    assert isinstance(store, KnowledgeStorePort)


async def test_in_memory_store_roundtrip() -> None:
    store = KnowledgeStore()
    episode_id = await store.add_episode("dup-cluster", {"cwe": "CWE-79"})
    assert episode_id
    hits = await store.search("CWE-79")
    assert len(hits) == 1
    assert hits[0]["name"] == "dup-cluster"
    misses = await store.search("nonexistent-token")
    assert misses == []
    health = await store.healthcheck()
    assert health["status"] == "degraded"


def test_get_knowledge_store_returns_in_memory_by_default(monkeypatch) -> None:
    monkeypatch.setattr(providers, "get_settings", lambda: _settings())
    store = get_knowledge_store()
    assert isinstance(store, KnowledgeStore)
    # Shared instance across calls.
    assert get_knowledge_store() is store


def test_get_knowledge_store_selects_graphiti(monkeypatch) -> None:
    monkeypatch.setattr(providers, "get_settings", lambda: _settings(knowledge_backend="graphiti"))
    store = get_knowledge_store()
    assert isinstance(store, GraphitiKnowledgeStore)


async def test_graphiti_healthcheck_degrades_without_backend(monkeypatch) -> None:
    # No live Neo4j (and possibly no graphiti-core): healthcheck must report
    # degraded rather than raising.
    monkeypatch.setattr(providers, "get_settings", lambda: _settings(knowledge_backend="graphiti"))
    store = get_knowledge_store()
    assert isinstance(store, GraphitiKnowledgeStore)
    health = await store.healthcheck()
    assert health["status"] == "degraded"
    assert health["backend"] == "graphiti-neo4j-unavailable"
    assert "error" in health


async def test_graphiti_search_and_add_degrade_gracefully() -> None:
    store = GraphitiKnowledgeStore("bolt://localhost:7687", "neo4j", "")
    # Without a live backend these must not raise; they return empty/sentinel.
    assert await store.search("anything") == []
    assert await store.add_episode("name", {"k": "v"}) == ""


def test_set_knowledge_store_injection() -> None:
    sentinel = KnowledgeStore()
    set_knowledge_store(sentinel)
    assert get_knowledge_store() is sentinel
    set_knowledge_store(None)
    # Reset rebuilds a fresh store.
    assert get_knowledge_store() is not sentinel
