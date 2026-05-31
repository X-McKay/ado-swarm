"""Injectable knowledge-store provider.

Tools and activities resolve the knowledge store through this accessor so the
in-memory stub can be swapped for a real Graphiti/Neo4j-backed store later
without touching call sites (mirrors `storage/providers.py`).
"""

from __future__ import annotations

from ado_swarm.knowledge.graphiti_store import KnowledgeStore

_knowledge_store: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = KnowledgeStore()
    return _knowledge_store


def set_knowledge_store(store: KnowledgeStore | None) -> None:
    global _knowledge_store
    _knowledge_store = store
