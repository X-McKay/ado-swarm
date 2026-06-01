from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import typer

from ado_swarm.agents.registry import list_agent_metadata
from ado_swarm.config import get_settings
from ado_swarm.knowledge.graphiti_store import KnowledgeStore
from ado_swarm.storage.artifacts import PostgresArtifactStore
from ado_swarm.temporal.client import build_temporal_client
from ado_swarm.tools.source_providers.factory import build_source_provider

app = typer.Typer(no_args_is_help=True)
runs_app = typer.Typer(no_args_is_help=True)
app.add_typer(runs_app, name="runs")


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
        typer.echo(f"{metadata.id}	{metadata.version}	{metadata.name}")


@app.command("eval-agents")
def eval_agents(model_profile: str = "fake", output: str | None = None, trials: int = 1) -> None:
    async def _run() -> list[dict]:
        results = []
        for metadata in list_agent_metadata():
            module_name, func_name = metadata.eval_entrypoint.split(":", 1)
            module = __import__(module_name, fromlist=[func_name])
            trial_results = []
            for _ in range(trials):
                trial_results.append(await getattr(module, func_name)(model_profile=model_profile))
            passed = all(item.get("passed") for item in trial_results)
            result = trial_results[-1] | {"trials": trials, "pass_k": passed}
            results.append(result)
        return results

    payload = asyncio.run(_run())
    text = json.dumps(payload, indent=2)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    typer.echo(text)


@app.command("eval-swarm")
def eval_swarm(model_profile: str = "fake") -> None:
    """Compare single-agent vs bounded-swarm adjudication; print a recommendation.

    The decision to default the adjudication swarm on (ADR-0009) is data-driven:
    run this against a real model (e.g. --model-profile ollama) and only enable the
    swarm if it beats the single-agent agreement rate.
    """
    from ado_swarm.evals.swarm_comparison import compare_modes

    typer.echo(json.dumps(asyncio.run(compare_modes(model_profile)), indent=2))


@app.command("start-mission")
def start_mission(goal: str) -> None:
    async def _run() -> dict:
        settings = get_settings()
        run_id = str(uuid4())
        client = await build_temporal_client(settings)
        handle = await client.start_workflow(
            "SupervisorWorkflow",
            args=[run_id, goal],
            id=f"mission:{run_id}",
            task_queue=settings.temporal_task_queue,
        )
        return {"run_id": run_id, "workflow_id": handle.id, "status": "started"}

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@runs_app.command("describe")
def describe_run(workflow_id: str) -> None:
    async def _run() -> dict:
        client = await build_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        snapshot = await handle.query("get_snapshot")
        return snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else snapshot

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@runs_app.command("artifacts")
def run_artifacts(run_id: str) -> None:
    async def _run() -> list[dict]:
        artifacts = await PostgresArtifactStore().list_for_run(run_id)
        return [artifact.model_dump(mode="json") for artifact in artifacts]

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@runs_app.command("pause")
def pause_run(workflow_id: str, reason: str = "manual pause") -> None:
    async def _run() -> dict:
        client = await build_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("pause", reason)
        return {"workflow_id": workflow_id, "status": "pause_signal_sent"}

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@runs_app.command("resume")
def resume_run(workflow_id: str) -> None:
    async def _run() -> dict:
        client = await build_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal("resume")
        return {"workflow_id": workflow_id, "status": "resume_signal_sent"}

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


agents_app = typer.Typer(no_args_is_help=True)
app.add_typer(agents_app, name="agents")
skills_app = typer.Typer(no_args_is_help=True)
app.add_typer(skills_app, name="skills")
scaffold_app = typer.Typer(no_args_is_help=True)
app.add_typer(scaffold_app, name="scaffold")


@agents_app.command("run")
def agents_run(
    agent_id: str,
    casefile: str | None = None,
    source_issue: str | None = None,
    model_profile: str = "fake",
    approved: bool = False,
) -> None:
    """Run one agent in isolation against a fixture and print its AgentResult.

    No Temporal/Postgres needed. Use --model-profile ollama to exercise a real model.
    """
    from ado_swarm.agents.eval_support import build_eval_model_gateway, eval_invocation
    from ado_swarm.agents.registry import build_agent

    constraints: dict = {}
    if casefile:
        constraints["casefile"] = json.loads(Path(casefile).read_text())
    if source_issue:
        constraints["source_issue"] = json.loads(Path(source_issue).read_text())
    if approved:
        constraints["approved"] = True

    async def _run() -> dict:
        agent = build_agent(agent_id, model_gateway=build_eval_model_gateway(model_profile))
        invocation = eval_invocation(
            agent_id, objective=f"Run {agent_id} in isolation.", constraints=constraints
        )
        result = await agent.run(invocation)
        return result.model_dump(mode="json")

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@skills_app.command("list")
def skills_list() -> None:
    from ado_swarm.skills.loader import list_skills

    for name in list_skills():
        typer.echo(name)


@skills_app.command("show")
def skills_show(name: str) -> None:
    from ado_swarm.skills.loader import SKILLS_DIR

    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        typer.echo(f"Unknown skill: {name}", err=True)
        raise typer.Exit(code=1)
    typer.echo(path.read_text())


@skills_app.command("lint")
def skills_lint() -> None:
    """Validate every SKILL.md loads (strict) and every pack references known skills."""
    from strands import Skill

    from ado_swarm.skills.loader import SKILLS_DIR, list_skills, validate_packs

    invalid_skills: dict[str, str] = {}
    for name in list_skills():
        try:
            Skill.from_file(SKILLS_DIR / name / "SKILL.md", strict=True)
        except Exception as exc:  # surface any validation issue
            invalid_skills[name] = f"{type(exc).__name__}: {exc}"
    payload = {
        "invalid_skills": invalid_skills,
        "invalid_packs": validate_packs(),
        "ok": not invalid_skills and not validate_packs(),
    }
    typer.echo(json.dumps(payload, indent=2))
    if not payload["ok"]:
        raise typer.Exit(code=1)


@scaffold_app.command("agent")
def scaffold_agent_cmd(
    agent_id: str, section_field: str = "TODO_section", tool: str = "TODO_tool"
) -> None:
    from ado_swarm.cli.scaffold import scaffold_agent

    created = scaffold_agent(agent_id, section_field=section_field, tool=tool)
    for path in created:
        typer.echo(f"created {path}")


@scaffold_app.command("tool")
def scaffold_tool_cmd(name: str, area: str) -> None:
    from ado_swarm.cli.scaffold import scaffold_tool

    typer.echo(f"created/updated {scaffold_tool(name, area)} (remember to register it in CATALOG)")


@scaffold_app.command("skill")
def scaffold_skill_cmd(name: str, description: str = "TODO: when to use this skill") -> None:
    from ado_swarm.cli.scaffold import scaffold_skill

    typer.echo(f"created {scaffold_skill(name, description)}")


if __name__ == "__main__":
    app()
