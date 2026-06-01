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

1. Temporal workflows stay deterministic (`workflow.now()`, no I/O/model calls) and delegate I/O to activities.
2. Azure DevOps and GitHub access goes through `tools/source_providers` ports and adapters.
3. Agents live under `src/ado_swarm/agents/<agent_name>/` with `main.py` (a `CasefileAgent` subclass + `build_agent`), `metadata.yaml`, and `eval.py`.
4. New agent behavior must include or update isolated golden evaluations.
5. Write-capable provider, Git, PR, and ticket operations must be in `write_tool_names` and policy-gated behind approval.
6. Run `just check` before finalizing changes.

Prefer small, testable functions and update documentation (`CLAUDE.md`, `docs/`) when changing architecture or developer workflow.


## Agent runtime conventions

Every agent is a model-driven Strands `Agent` (tools in a loop) run inside a Temporal activity. The Strands plumbing lives in `agents/model_runtime.run_model_agent` (tools + `AgentSkills` + `ToolPolicyHook`, one non-deprecated `invoke_async(structured_output_model=...)`). Agents declare `tool_names`, `section_model`/`section_field`, and prompts; **skills come from `metadata.yaml`** (single source, applied by the registry). Do not hardcode skills in `main.py`, and do not put deterministic logic in `run()` — extract it to a `@tool` in `tools/catalog/`.

Preserve the Temporal/Strands split: Temporal owns durable state, retries, Signals, Updates, approvals, and mission lifecycle; the agent returns an `AgentResult` contract. Use `build_temporal_client()` rather than `Client.connect()` directly. Tool access is enforced at the `BeforeToolCallEvent` hook (`tools/policy_hook.py`) — `ALLOW | DENY | REQUIRE_APPROVAL`. Model invocation comes from Strands providers (`model_gateway/strands_models.py::build_strands_model`); there is no hand-rolled completion path.

New workflow-visible state should be contracts first, tested in isolation. Use `RunArtifact` records for run-level auditability. Evaluations use the shared harness (`eval_support.run_agent_eval`) with a scripted `FakeModel`; support pass^k, keep the deterministic `fake` path green before testing local/remote models.


## Casefile pipeline

`SecurityCasefile` is the typed handoff object. Agents read it with `casefile_from_invocation()` and emit one section via structured output; `CasefileAgent.run` writes the section and the `casefile_artifact`. Each specialist owns exactly one section (`normalized_finding`, `repository_evidence`, `adjudication`, `risk`, `remediation_plan`, `validation`, `execution`, `readiness`). A standalone analytics agent (`data_analyst`) emits a `CampaignReport` artifact instead. Never introduce prompt-only handoffs when a typed field can represent the state. The supervisor propagates each stage's casefile artifact to dependents via `TaskSpec.input_refs`.

To add an agent/tool/skill, follow the step-by-step in `CLAUDE.md`.


The default Temporal mission planner builds the pipeline from one graph template (`runtime/graph_templates.py::triage_readonly_graph`, the single source of truth — do not reintroduce a parallel `PIPELINE` list): `ticket_analyst → repo_analyst → security_reviewer → risk_auditor → solutions_architect → test_engineer → submission_engineer`. When modifying planner or workflow behavior, preserve dependency artifact propagation: downstream tasks receive upstream casefile artifacts through `TaskSpec.input_refs`, and workflows must not store mutable casefile state outside typed artifacts.

## Newer subsystems (keep these conventions)

- **Approval gate:** a node with `requires_approval=True` (e.g. `submission_engineer`) makes the supervisor park `WAITING_FOR_APPROVAL`; on `approve_task` the task is dispatched with `constraints["approved"]=True` so its `write_tool_names` pass the policy gate. Keep write tools approval-gated; never enable them unconditionally.
- **Bounded swarm cell** (`agents/swarm_cell.py`, ADR-0009): multi-perspective ensemble + judge inside one activity, hard `max_model_calls` budget, opt-in (`use_swarm` / `security_reviewer_use_swarm`) and eval-gated via `ado-swarm eval-swarm`. Don't default it on without an eval win.
- **OTel tracing** (`runtime/telemetry.py`, ADR-0010): config-gated (`tracing_enabled`); use `setup_telemetry()` + `trace_attributes()` + `temporal_interceptors()`. Never hand-roll spans (the old `runtime/observability.py` was removed).
- **Knowledge store** (`knowledge/providers.py`): resolve via `get_knowledge_store()`; backend is `memory` or `graphiti` per `knowledge_backend`. **Verification governor:** `run_validation_command` runs allowlisted commands in the sandbox — a non-zero exit is a hard failure, not advisory.
