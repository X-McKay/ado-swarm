from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class KnowledgeStorePort(Protocol):
    """The stable knowledge-store port.

    Both the in-memory reference store and the Graphiti/Neo4j-backed store
    conform to this shape, so call sites (tools/activities) never depend on a
    concrete backend.
    """

    async def healthcheck(self) -> dict[str, str]: ...

    async def add_episode(self, name: str, content: dict[str, Any]) -> str: ...

    async def search(self, query: str) -> list[dict[str, Any]]: ...


@dataclass
class KnowledgeStore:
    """In-memory reference implementation of :class:`KnowledgeStorePort`.

    Named ``KnowledgeStore`` (not ``InMemoryKnowledgeStore``) so existing
    call sites in ``api/app.py`` and ``cli/main.py`` keep working unchanged.
    """

    episodes: list[dict[str, Any]] = field(default_factory=list)

    async def healthcheck(self) -> dict[str, str]:
        # Be honest: the in-memory backend is not a durable knowledge graph, so a
        # readiness probe should see it as degraded rather than fully "ok".
        return {"status": "degraded", "backend": "in-memory-graphiti-compatible"}

    async def add_episode(self, name: str, content: dict[str, Any]) -> str:
        episode_id = f"episode-{len(self.episodes) + 1}"
        self.episodes.append({"id": episode_id, "name": name, "content": content})
        return episode_id

    async def search(self, query: str) -> list[dict[str, Any]]:
        return [episode for episode in self.episodes if query.lower() in str(episode).lower()]


class GraphitiKnowledgeStore:
    """Graphiti/Neo4j-backed knowledge store.

    Imports of ``graphiti_core``/``neo4j`` are deferred into the methods so that
    importing this module never hard-fails when the optional ``graphiti`` extra
    is not installed. Each method degrades gracefully: connection/import errors
    surface as a ``degraded`` healthcheck or as empty/best-effort results rather
    than propagating exceptions to callers.
    """

    def __init__(self, uri: str, user: str, password: str, *, group_id: str = "ado-swarm") -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._group_id = group_id

    def _build_client(self) -> Any:
        # Lazy import keeps the optional dependency truly optional.
        from graphiti_core import Graphiti

        return Graphiti(self._uri, self._user, self._password)

    async def healthcheck(self) -> dict[str, str]:
        try:
            client = self._build_client()
        except Exception as exc:  # ImportError or construction failure
            return {
                "status": "degraded",
                "backend": "graphiti-neo4j-unavailable",
                "error": str(exc),
            }
        try:
            # build_indices_and_constraints requires a live connection; if it
            # succeeds we know Neo4j is reachable.
            await client.build_indices_and_constraints()
            return {"status": "ok", "backend": "graphiti-neo4j"}
        except Exception as exc:
            return {
                "status": "degraded",
                "backend": "graphiti-neo4j-unavailable",
                "error": str(exc),
            }
        finally:
            await _safe_close(client)

    async def add_episode(self, name: str, content: dict[str, Any]) -> str:
        try:
            from graphiti_core.nodes import EpisodeType

            client = self._build_client()
        except Exception:
            # Optional dependency missing or client construction failed.
            return ""
        try:
            result = await client.add_episode(
                name=name,
                episode_body=json.dumps(content),
                source_description="ado-swarm",
                reference_time=datetime.now(UTC),
                source=EpisodeType.json,
                group_id=self._group_id,
            )
            episode = getattr(result, "episode", None)
            uuid = getattr(episode, "uuid", None)
            return str(uuid) if uuid is not None else ""
        except Exception:
            return ""
        finally:
            await _safe_close(client)

    async def search(self, query: str) -> list[dict[str, Any]]:
        try:
            client = self._build_client()
        except Exception:
            return []
        try:
            edges = await client.search(query, group_ids=[self._group_id])
        except Exception:
            return []
        finally:
            await _safe_close(client)
        results: list[dict[str, Any]] = []
        for edge in edges or []:
            results.append(
                {
                    "id": str(getattr(edge, "uuid", "")),
                    "name": getattr(edge, "name", None),
                    "content": {"fact": getattr(edge, "fact", None)},
                }
            )
        return results


async def _safe_close(client: Any) -> None:
    close = getattr(client, "close", None)
    if close is None:
        return
    try:
        result = close()
        if hasattr(result, "__await__"):
            await result
    except Exception:  # noqa: S110 - best-effort cleanup; close errors are non-fatal
        pass
