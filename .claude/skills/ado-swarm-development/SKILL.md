---
name: ado-swarm-development
description: Develop and modify the ado-swarm base architecture, agents, provider adapters, and tests.
---
# ado-swarm development

## Canonical vocabulary — read first (`docs/concepts/agents-tools-skills.md`)

We use Simon Willison's definitions:
- **Agent** = *tools in a loop* — an LLM called with tool definitions, executing tools and feeding results back in a bounded loop. **An agent always uses a model.**
- **Tool** = an executable function the harness gives the agent (its *hands*); deterministic, typed, unit-tested.
- **Skill** = packaged expertise (a `SKILL.md`) loaded into context to shape *how* an agent approaches a problem; it is context, not code.

**THE CORE RULE:** every agent uses a model. If a unit of work is deterministic, it is a **tool** (or a harness verification step) — **never** an agent. Do not create "deterministic agents." If you find deterministic logic inside an agent's `run()`, extract it into a `@tool` in the tool catalog. To restrict what an agent can do, change the tool policy — not the prompt or a skill's `allowed-tools` (which is documentation only).

## Core boundaries

When working in this repository, preserve the core boundaries:

1. Temporal workflows stay deterministic and delegate I/O to activities.
2. Azure DevOps and GitHub access goes through `tools/source_providers` ports and adapters.
3. Agents live under `src/ado_swarm/agents/<agent_name>/` with `main.py`, `metadata.yaml`, `eval.py`, and `prompts.md`.
4. New agent behavior must include or update isolated evaluations.
5. Write-capable provider, Git, PR, and ticket operations must remain policy-gated.
6. Run `just check` before finalizing changes.

Prefer small, testable functions and update documentation when changing architecture or developer workflow.


## Harness runtime conventions

When changing agent execution, preserve the separation between Temporal and the agent runtime. Temporal owns durable workflow state, retries, Signals, Updates, approvals, and mission lifecycle. Agent modules may use the Strands-compatible runtime adapter through `BaseAgent`, but must continue returning `AgentResult` contracts.

Use `build_temporal_client()` instead of calling `Client.connect()` directly so Pydantic data conversion and future tracing configuration remain centralized. Use `ToolPolicy` and `ToolContext` before adding any write-capable tool path. High-risk tasks, write tools, and destructive operations must require an approved `ApprovalState`.

New workflow-visible state should be represented as contracts first, then tested in isolation. For agent durability, prefer `AgentCheckpoint` and the checkpoint store rather than ad hoc files. For run-level auditability, use `RunArtifact` records for plans, context packs, execution logs, verification records, and decision records.

Evaluation changes should support repeated trials and pass^k semantics. Add golden, edge, adversarial, and regression cases where possible, and keep the deterministic `fake` model path passing before testing local or remote models.


## Richer agent pipeline

For read-only security workflow changes, use `SecurityCasefile` as the handoff object. Agents should read a casefile from task constraints or artifact metadata with `casefile_from_invocation()` and emit updated state with `casefile_artifact()`. Each specialist owns a specific casefile field: repository evidence, adjudication, risk, remediation plan, or validation audit. Do not introduce prompt-only handoffs when a typed field can represent the state.


The default Temporal mission planner executes the full casefile pipeline in this order: `ticket_analyst`, `repo_analyst`, `security_reviewer`, `risk_auditor`, `solutions_architect`, and `test_engineer`. When modifying planner or workflow behavior, preserve dependency artifact propagation: downstream tasks should receive upstream casefile artifacts through `TaskSpec.input_refs`, and workflows should avoid storing mutable casefile state outside typed artifacts.
