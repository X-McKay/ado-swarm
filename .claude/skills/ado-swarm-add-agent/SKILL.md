---
name: ado-swarm-add-agent
description: Add or modify an ado-swarm agent, tool, or skill following the model-driven (tools-in-a-loop) pattern. Use when creating a new specialist agent, a new catalog tool, or a new SKILL.md.
---
# Adding an agent, tool, or skill to ado-swarm

Follow the canonical rule (`docs/concepts/agents-tools-skills.md`): **every agent uses a model; deterministic work is a tool, never an agent.** Run `just check` before finishing.

## Add a TOOL (do this first if the agent needs new deterministic capability)

In `src/ado_swarm/tools/catalog/<area>.py`:
```python
from strands import tool

def my_capability_impl(finding: dict) -> dict:        # deterministic, typed, unit-tested
    ...
    return {"result": ...}

@tool
def my_capability(finding: dict) -> dict:
    """One-line purpose the model reads. Args: finding: a NormalizedFinding JSON object.
    Returns: a JSON object with ..."""
    return my_capability_impl(finding)
```
Register it in `tools/catalog/__init__.py::CATALOG`, and add a test to `tests/unit/test_tool_catalog.py` (call the `_impl`). **Write tools** (mutate state) must later be listed in the agent's `write_tool_names` so they are approval-gated.

## Add an AGENT (casefile specialist)

1. Pick the `SecurityCasefile` section it emits (add a new field + pydantic model to `contracts/casefile.py` if needed).
2. `src/ado_swarm/agents/<id>/metadata.yaml`:
   ```yaml
   id: my_agent
   name: My Agent
   version: 0.1.0
   description: ...
   entrypoint: ado_swarm.agents.my_agent.main:build_agent
   eval_entrypoint: ado_swarm.agents.my_agent.eval:run_eval
   skills: [some-existing-skill]      # MUST exist in src/ado_swarm/skills/ — single source of truth
   tools: { allowed: [my_capability] }
   risk_tier: low
   ```
3. `src/ado_swarm/agents/<id>/main.py`:
   ```python
   from typing import ClassVar
   from pydantic import BaseModel
   from ado_swarm.agents.casefile_agent import CasefileAgent
   from ado_swarm.contracts.casefile import MySection, SecurityCasefile
   from ado_swarm.model_gateway.gateway import ModelGateway

   class MyAgent(CasefileAgent):
       section_field: ClassVar[str] = "my_section"
       section_model: ClassVar[type[BaseModel] | None] = MySection
       tool_names: ClassVar[list[str]] = ["my_capability"]
       # write_tool_names: ClassVar[list[str]] = ["my_write_tool"]   # if it writes
       def reasoning_prompt(self, casefile: SecurityCasefile) -> str:
           return "Do X. Call my_capability for the baseline.\n\n" + casefile.model_dump_json(indent=2)

   def build_agent(model_gateway: ModelGateway) -> MyAgent:
       return MyAgent(agent_id="my_agent", display_name="My Agent", model_gateway=model_gateway)
   ```
   Do **not** hardcode skills here (the registry applies them from metadata) and do **not** put deterministic logic in the agent — call a tool.
4. `src/ado_swarm/agents/<id>/eval.py`: use `eval_support.run_agent_eval` with a scripted `FakeModel` (script the `ToolCall`s, inject `structured_outputs={MySection: expected}`) and an `assertion`. Add the agent to `tests/unit/test_next_wave_agents.py`.

A standalone (non-casefile) agent — see `agents/data_analyst/main.py` — calls `agents/model_runtime.run_model_agent` directly with its own input/output model and emits an artifact.

## Add a SKILL

`src/ado_swarm/skills/<name>/SKILL.md` with frontmatter `name` (= directory, lowercase-hyphen), `description`, optional `allowed-tools` (documentation only), plus a markdown procedure body. Reference it from an agent's `metadata.yaml` `skills`. Validate with `just skills-validate`. Remember: a skill is context/expertise, not code, and takes no action — enforcement is the tool policy.

## Verify

`just check` (lint + type + unit + eval-agents). The guardrail test `tests/unit/test_agent_metadata_validation.py` will fail a model-less agent, an unknown tool, or a non-existent skill.
</content>
