from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeStore:
    episodes: list[dict[str, Any]] = field(default_factory=list)

    async def healthcheck(self) -> dict[str, str]:
        return {"status": "ok", "backend": "in-memory-graphiti-compatible"}

    async def add_episode(self, name: str, content: dict[str, Any]) -> str:
        episode_id = f"episode-{len(self.episodes) + 1}"
        self.episodes.append({"id": episode_id, "name": name, "content": content})
        return episode_id

    async def search(self, query: str) -> list[dict[str, Any]]:
        return [episode for episode in self.episodes if query.lower() in str(episode).lower()]
