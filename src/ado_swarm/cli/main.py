from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from ado_swarm.agents.registry import list_agent_metadata
from ado_swarm.config import get_settings
from ado_swarm.knowledge.graphiti_store import KnowledgeStore
from ado_swarm.tools.source_providers.factory import build_source_provider

app = typer.Typer(no_args_is_help=True)


@app.command()
def smoke() -> None:
    async def _run() -> dict:
        settings = get_settings()
        provider = build_source_provider(settings)
        issue = await provider.get_issue("SEC-1")
        knowledge = KnowledgeStore()
        episode_id = await knowledge.add_episode("smoke", issue.model_dump(mode="json"))
        return {
            "status": "ok",
            "provider": provider.provider_name,
            "issue": issue.external_id,
            "episode_id": episode_id,
        }

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@app.command("list-agents")
def list_agents() -> None:
    for metadata in list_agent_metadata():
        typer.echo(f"{metadata.id}\t{metadata.version}\t{metadata.name}")


@app.command("eval-agents")
def eval_agents(model_profile: str = "fake", output: str | None = None) -> None:
    async def _run() -> list[dict]:
        results = []
        for metadata in list_agent_metadata():
            module_name, func_name = metadata.eval_entrypoint.split(":", 1)
            module = __import__(module_name, fromlist=[func_name])
            result = await getattr(module, func_name)(model_profile=model_profile)
            results.append(result)
        return results

    payload = asyncio.run(_run())
    text = json.dumps(payload, indent=2)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    typer.echo(text)


if __name__ == "__main__":
    app()
