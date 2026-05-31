# Architecture

`ado-swarm` separates **durable orchestration** (Temporal) from **agent reasoning** (Strands). This document is the concise reference; the full design and roadmap live in [`implementation-plan-2026-06.md`](implementation-plan-2026-06.md), and the agent/tool/skill vocabulary in [`concepts/agents-tools-skills.md`](concepts/agents-tools-skills.md).

## Layers

```
 Operator / API / CLI ──► Temporal SupervisorWorkflow (plan DAG, retries, approvals, snapshot)
                              └─► AgentTaskWorkflow (per task) ─► run_agent ACTIVITY
                                                                    └─► Strands Agent (model + tools + skills)
        Postgres (runs/plans/events/artifacts)   Neo4j+Graphiti (knowledge)   OTel (traces)
```

| Concern | Owner | Mechanism |
|---|---|---|
| Plan/DAG, scheduling, retries, approvals, snapshot | **Temporal workflow** | `workflows/supervisor.py`, `workflows/agent_task.py` (deterministic; `workflow.now()`, no I/O) |
| Model reasoning, tool calls, skill activation | **Strands `Agent`** in an activity | `agents/casefile_agent.py` → `agents/model_runtime.py` (`run_model_agent`) |
| Tool authorization | **Strands `BeforeToolCallEvent` hook** | `tools/policy_hook.py` → `ALLOW \| DENY \| REQUIRE_APPROVAL` |
| Deterministic capabilities | **Tool catalog** | `tools/catalog/` (typed `@tool` functions) |
| Expertise / procedures | **Skills** | `skills/<name>/SKILL.md` via the Strands `AgentSkills` plugin |
| Provider differences (ADO/GitHub) | **Source-provider ports** | `tools/source_providers/` |
| Operational state | **Postgres** | `storage/` (artifacts, checkpoints, events, migrations) |
| Long-term knowledge | **Neo4j + Graphiti** | `knowledge/graphiti_store.py` (`KnowledgeStore` port) |

## Core rule

Every agent is a Strands agent (model + tools in a loop). Deterministic work is a **tool**, never an agent. Skills are context. Tool policy — not prompts or a skill's `allowed-tools` — enforces access. See [`concepts/agents-tools-skills.md`](concepts/agents-tools-skills.md).

## Model providers

Agents talk to Strands model providers (`model_gateway/strands_models.py::build_strands_model`):
`fake` (deterministic, offline CI) · `ollama` · `openai`/`openai_compatible` · `litellm` · `bedrock`. The provider is selected by `MODEL_PROVIDER`; `fake` is the default in CI and `just check`.

## Casefile handoff

Agents collaborate through a typed `SecurityCasefile` (`contracts/casefile.py`). Each specialist reads the casefile and emits exactly one section (`normalized_finding`, `repository_evidence`, `adjudication`, `risk`, `remediation_plan`, `validation`, `execution`, `readiness`). The supervisor propagates each stage's casefile artifact to its dependents via `TaskSpec.input_refs`.

## Decision records

See [`decisions/`](decisions/): Temporal control plane (0001), provider-neutral adapters (0002), model gateway (0003), Strands/Temporal harness runtime (0004), tool policy & approvals (0005), casefile pipeline (0006), Temporal casefile execution (0007), and model-driven agents on Strands (0008).
</content>
