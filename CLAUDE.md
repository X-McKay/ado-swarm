# CLAUDE.md

Guide for Claude Code (and humans) working in `ado-swarm`. Read [`docs/concepts/agents-tools-skills.md`](docs/concepts/agents-tools-skills.md) and [`docs/architecture.md`](docs/architecture.md) before making changes.

## What this is

A Temporal-orchestrated security-remediation agent swarm. **Temporal** owns durable orchestration; **Strands** agents (model + tools in a loop) run inside Temporal activities and reason over a typed `SecurityCasefile`. Provider adapters hide Azure DevOps/GitHub behind canonical contracts.

## The core rule (non-negotiable)

> **Every agent uses a model. If a unit of work is deterministic, it is a *tool* (or a harness verification step) — never an agent.**

- **Agent** = tools in a loop (Strands `Agent`, always model-driven). Lives in `src/ado_swarm/agents/<id>/`.
- **Tool** = a deterministic typed `@tool` in `src/ado_swarm/tools/catalog/`. The agent's hands.
- **Skill** = a `SKILL.md` under `src/ado_swarm/skills/<name>/`. Context/expertise, not code.

If you find deterministic logic inside an agent's `run()`, extract it to a catalog tool. To restrict what an agent can do, change the **tool policy** — not the prompt, not a skill's `allowed-tools` (which is documentation only).

## Commands

```bash
just check          # ruff + ty + unit tests + eval-agents (the gate; run before finishing)
just test           # unit tests only
just test-workflow  # Temporal workflow tests (skip locally if the test-server binary is unavailable)
just eval-agents    # every agent's golden eval on the deterministic `fake` model
just format         # ruff format + autofix

# isolated agent/skill harness
just agent-run <id> --source-issue f.json            # run one agent against a fixture (add --model-profile ollama)
uv run python -m ado_swarm.agents.<id>.eval --model-profile fake   # one agent's golden eval
just skills-list / just skills-show <name> / just skills-lint
just new-agent <id> / just new-tool <name> <area> / just new-skill <name>
MODEL_PROVIDER=ollama just eval-agents                # evals against a real local model
```

`uv` runs everything; `mise` pins tools. CI mirrors `just check` plus `eval-agents` on the `fake` profile; the workflow is kept as a template at `docs/ci/github-actions-ci.yml` because the bot can't push `.github/workflows/` — copy it there to enable CI.

## Layout

```
src/ado_swarm/
  agents/<id>/        main.py (CasefileAgent subclass + build_agent), metadata.yaml, eval.py, fixtures/
  agents/casefile_agent.py   CasefileAgent base (read casefile -> reason -> emit one typed section)
  agents/model_runtime.py    run_model_agent: builds the Strands agent (tools+skills+policy) and runs it
  agents/registry.py         build_agent(); single-sources skills from metadata
  agents/eval_support.py     run_agent_eval / eval_cli (shared eval harness)
  tools/catalog/      typed @tool functions (the deterministic capabilities) + registry
  tools/policy.py / policy_hook.py   ToolPolicy + the BeforeToolCallEvent gate
  skills/<name>/SKILL.md      the skill catalog; skills/runtime.py binds it via AgentSkills
  model_gateway/strands_models.py    build_strands_model + FakeModel (deterministic, offline)
  contracts/          pydantic contracts (casefile.py, mission.py, events.py, ...)
  workflows/ activities/ workers/    Temporal (deterministic workflows; I/O in activities)
  tools/source_providers/   ADO/GitHub/stub adapters behind a Protocol
  storage/ knowledge/ sandbox/ api/ cli/
tests/unit/  tests/workflow/
```

## How to add an AGENT

1. `metadata.yaml`: id, name, version, description, `entrypoint`/`eval_entrypoint`, `skills` (must exist in the catalog — this is the single source of truth), `tools.allowed`, `risk_tier`.
2. `main.py`: a `CasefileAgent` subclass declaring `section_field`, `section_model` (a `SecurityCasefile` field + its pydantic type), `tool_names` (must exist in the catalog), an optional `reasoning_prompt`, and a `build_agent(model_gateway)` factory. ~30 lines.
3. `eval.py`: use `eval_support.run_agent_eval` with a scripted `FakeModel` (script the tool calls, inject the expected `structured_outputs`) and an `assertion`. Add it to `tests/unit/test_next_wave_agents.py`.
4. `just check` must pass; the guardrail test (`tests/unit/test_agent_metadata_validation.py`) enforces model + ≥1 catalog tool + real skills.

A standalone (non-casefile) model agent — like `data_analyst` — calls `model_runtime.run_model_agent` directly with its own output model.

## How to add a TOOL

In `tools/catalog/<area>.py`: a plain `_impl` function (deterministic, typed) and a thin `@tool` wrapper with a clear docstring (the model reads it). Register it in `tools/catalog/__init__.py::CATALOG`. Add a unit test in `tests/unit/test_tool_catalog.py`. **Write tools** must be added to the agent's `write_tool_names` so they are approval-gated.

## How to add a SKILL

Create `skills/<name>/SKILL.md` with frontmatter `name` (must equal the directory, lowercase-hyphen), `description`, optional `allowed-tools`, plus a markdown body of instructions. Reference it from an agent's `metadata.yaml` `skills`. Validate with `just skills-validate`.

## Conventions / gotchas

- **Temporal determinism:** workflow code uses `workflow.now()`/`workflow.uuid4()`; no wall-clock, I/O, or model calls in workflows — those go in activities. Pass pydantic models via the pydantic data converter.
- **Approvals** are Temporal Updates with validators; **write/high-risk tools** require an approved `ToolContext` (`constraints["approved"]` in tests/evals).
- **Structured output:** use the non-deprecated `invoke_async(prompt, structured_output_model=...)`. The forced structured-output tool is named after the section model and must bypass the policy (handled in `run_model_agent`).
- **Hermetic tests:** the `fake` model exercises the *real* Strands loop offline; never call a network model in unit tests.
- **Read-only first:** keep provider/git/repo operations read-only; write paths stay behind policy + approval + verification.

## Where to look

- Vocabulary & rule: `docs/concepts/agents-tools-skills.md`
- Architecture: `docs/architecture.md`; decisions: `docs/decisions/` (ADR-0008 = model-driven agents)
- Roadmap: `docs/implementation-plan-2026-06.md`; review: `docs/codebase-review-2026-05.md`
- Tool/skill gaps to explore next: `docs/tools-skills-review.md`
</content>
