"""Injectable knowledge-store provider.

Tools and activities resolve the knowledge store through this accessor so the
backend (in-memory stub or a real Graphiti/Neo4j-backed store) can be swapped
via config without touching call sites (mirrors `storage/providers.py`).
"""

from __future__ import annotations

from ado_swarm.config import get_settings
from ado_swarm.knowledge.graphiti_store import (
    GraphitiKnowledgeStore,
    KnowledgeStore,
    KnowledgeStorePort,
)

_knowledge_store: KnowledgeStorePort | None = None


def _build_from_settings() -> KnowledgeStorePort:
    settings = get_settings()
    if settings.knowledge_backend == "graphiti":
        return GraphitiKnowledgeStore(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    return KnowledgeStore()


def get_knowledge_store() -> KnowledgeStorePort:
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = _build_from_settings()
    return _knowledge_store


def set_knowledge_store(store: KnowledgeStorePort | None) -> None:
    global _knowledge_store
    _knowledge_store = store
