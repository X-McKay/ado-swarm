"""Knowledge tools — graph-memory recall for adjudication and analytics.

These wrap the `KnowledgeStore` (in-memory today, Graphiti/Neo4j later) so agents
like `security_reviewer` can recall related/duplicate findings and record outcomes
through the policy gate. Resolved via `knowledge.providers` so the backend is
swappable without touching call sites.
"""

from __future__ import annotations

from strands import tool

from ado_swarm.knowledge.providers import get_knowledge_store


async def graphiti_search_impl(query: str) -> dict:
    store = get_knowledge_store()
    episodes = await store.search(query)
    return {"query": query, "count": len(episodes), "episodes": episodes}


async def graphiti_add_episode_impl(name: str, content: dict) -> dict:
    store = get_knowledge_store()
    episode_id = await store.add_episode(name, content)
    return {"episode_id": episode_id, "name": name}


@tool
async def graphiti_search(query: str) -> dict:
    """Search graph memory for related prior findings/outcomes (read-only).

    Args:
        query: Free-text query, e.g. a finding fingerprint, CWE, package, or file path.

    Returns:
        A JSON object: query, count, and the matching episodes (each with id/name/content).
    """
    return await graphiti_search_impl(query)


@tool
async def graphiti_add_episode(name: str, content: dict) -> dict:
    """Record an episode (e.g. an adjudication outcome) into graph memory.

    Args:
        name: A short label for the episode.
        content: A JSON object capturing the outcome/evidence to remember.

    Returns:
        A JSON object: the new episode_id and name.
    """
    return await graphiti_add_episode_impl(name, content)
