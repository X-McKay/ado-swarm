"""Scaffolders for the model-driven agent/tool/skill pattern.

Used by the `ado-swarm scaffold ...` CLI and `just new-*` recipes so a new
agent/tool/skill starts from the correct shape (see `CLAUDE.md` and
`docs/concepts/agents-tools-skills.md`) rather than copy-paste.
"""

from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
AGENTS_DIR = SRC / "agents"
CATALOG_DIR = SRC / "tools" / "catalog"
SKILLS_DIR = SRC / "skills"


def _title(identifier: str) -> str:
    return " ".join(part.capitalize() for part in identifier.replace("-", "_").split("_"))


def scaffold_skill(name: str, description: str = "TODO: when to use this skill") -> Path:
    """Create skills/<name>/SKILL.md. `name` must be lowercase-hyphen."""
    skill_dir = SKILLS_DIR / name
    path = skill_dir / "SKILL.md"
    if path.exists():
        raise FileExistsError(path)
    skill_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
name: {name}
description: {description}
allowed-tools: ""
---
# {_title(name)}

## Objective
TODO: what good output looks like for this procedure.

## Procedure
1. TODO

## Output expectations
TODO
"""
    )
    return path


def scaffold_tool(name: str, area: str) -> Path:
    """Create (or append to) tools/catalog/<area>.py with a deterministic @tool."""
    path = CATALOG_DIR / f"{area}.py"
    snippet = f'''

def {name}_impl(payload: dict) -> dict:
    # TODO: deterministic, typed logic.
    return {{"result": payload}}


@tool
def {name}(payload: dict) -> dict:
    """TODO: one-line purpose the model reads.

    Args:
        payload: TODO describe the JSON input.

    Returns:
        A JSON object with TODO.
    """
    return {name}_impl(payload)
'''
    if path.exists():
        existing = path.read_text()
        if "from strands import tool" not in existing:
            existing = "from strands import tool\n" + existing
        path.write_text(existing.rstrip() + "\n" + snippet)
    else:
        path.write_text(
            "from __future__ import annotations\n\nfrom strands import tool\n" + snippet
        )
    return path


def scaffold_agent(
    agent_id: str, section_field: str = "TODO_section", tool: str = "TODO_tool"
) -> list[Path]:
    """Create agents/<agent_id>/ with metadata.yaml, main.py, eval.py, __init__.py."""
    agent_dir = AGENTS_DIR / agent_id
    if agent_dir.exists():
        raise FileExistsError(agent_dir)
    agent_dir.mkdir(parents=True)
    display = _title(agent_id)
    cls = display.replace(" ", "") + "Agent"

    (agent_dir / "__init__.py").write_text("")
    metadata = agent_dir / "metadata.yaml"
    metadata.write_text(
        f"""id: {agent_id}
name: {display}
version: 0.1.0
description: TODO describe what {display} does.
entrypoint: ado_swarm.agents.{agent_id}.main:build_agent
eval_entrypoint: ado_swarm.agents.{agent_id}.eval:run_eval
skills: []          # MUST exist in src/ado_swarm/skills/ (single source of truth)
tools:
  allowed:
    - {tool}
risk_tier: low
"""
    )
    main = agent_dir / "main.py"
    main.write_text(
        f'''from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from ado_swarm.agents.casefile_agent import CasefileAgent
from ado_swarm.contracts.casefile import SecurityCasefile  # TODO import your section model
from ado_swarm.model_gateway.gateway import ModelGateway


class {cls}(CasefileAgent):
    section_field: ClassVar[str] = "{section_field}"
    section_model: ClassVar[type[BaseModel] | None] = None  # TODO: the section's pydantic type
    tool_names: ClassVar[list[str]] = ["{tool}"]

    def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
        return "TODO instruct the model; call {tool}.\\n\\n" + casefile.model_dump_json(indent=2)


def build_agent(model_gateway: ModelGateway) -> {cls}:
    return {cls}(agent_id="{agent_id}", display_name="{display}", model_gateway=model_gateway)
'''
    )
    eval_py = agent_dir / "eval.py"
    eval_py.write_text(
        f'''from __future__ import annotations

from ado_swarm.agents.eval_support import eval_cli, eval_invocation, run_agent_eval
from ado_swarm.contracts.mission import AgentResult

# TODO: build a scripted FakeModel (script the ToolCalls, inject structured_outputs)
# and an assertion. See ticket_analyst/eval.py for the canonical example.


async def run_eval(model_profile: str = "fake") -> dict:
    invocation = eval_invocation(
        "{agent_id}", objective="Evaluate {display}.", constraints={{}}
    )

    def assertion(result: AgentResult) -> bool:
        return result.state == "completed"

    return await run_agent_eval(
        "{agent_id}", invocation=invocation, model_profile=model_profile, assertion=assertion
    )


def main() -> None:
    eval_cli(run_eval)


if __name__ == "__main__":
    main()
'''
    )
    return [metadata, main, eval_py]
