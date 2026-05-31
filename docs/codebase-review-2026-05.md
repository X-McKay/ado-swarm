# ado-swarm Codebase Review & Improvement Plan

**Date:** 2026-05-31
**Scope:** Full codebase — architecture, redundancy, testability, scale, objective-completion, and developer experience (incl. AI tooling).
**Status of repo at review:** `just check` green (23 unit tests pass, ruff clean, `ty` clean, `eval-agents` passes on the `fake` profile). ~4,100 LOC of `src`, ~310 LOC of tests.

> **Update note (2026-05-31, post-rebase onto `main`).** After the initial review, commit `bb2b443 "Execute full casefile pipeline in Temporal"` landed (ADR-0007). It expands the planner from a 2-task plan to the full **six-agent linear DAG** (`ticket_analyst → repo_analyst → security_reviewer → risk_auditor → solutions_architect → test_engineer`) and makes the supervisor **propagate each stage's casefile artifact to its dependent task via `TaskSpec.input_refs`** (`workflows/supervisor.py:62-71`), which `casefile_from_invocation()` now reads (`agents/casefile_utils.py:18-22`). Build is green (25 unit tests).
>
> **Net effect on this report:** the typed casefile handoff is now genuinely wired end-to-end (a real improvement — it resolves the "prompt-only handoff" risk in the *good* direction), so §2's praise of the contracts handoff is reinforced. **The core thesis is unchanged and arguably sharper:** the entire read-only triage path is now executed as deterministic Python with *no model reasoning, no skill injection, and no policy gate* on any of the six stages. Specific line references updated below are marked ⟳. Findings in §2.1–2.4, §3.1, §4, §5, §6, §7 all still hold.

---

## 1. Executive summary

`ado-swarm` is a well-disciplined scaffold. The contracts layer is coherent (`extra="forbid"`, UTC-aware, `StrEnum` vocabularies), the ports-and-adapters seams are real, the Temporal/agent separation is respected, and the developer command surface (`mise` + `uv` + `just` + `prek` + `ruff` + `ty`) is exactly what the implementation plan prescribed. Milestones 0–7 of `docs/implementation-plan.md` are largely scaffolded.

However, the review surfaced **one structural theme that dominates everything else**: the system's headline capabilities — *agents reason with an LLM*, *skills are progressively disclosed into the model*, and *tools are policy-gated and denied by default* — **exist as data and types but are not wired into the execution path.** The "swarm" today is a set of deterministic Python functions that mutate a casefile; the model, the 26 skills, and the tool-policy engine are essentially decorative. Closing that gap is the highest-leverage work for "improving the ability to successfully complete the underlying objective."

The second theme is **redundancy from copy-paste scaffolding**: 9 near-identical `eval.py` files, 26 byte-identical `SKILL.md` bodies, two near-identical provider adapters, and a repeated casefile-`run()` skeleton. Roughly 600–800 lines can be deleted by making these declarative.

The third theme is **missing engineering infrastructure**: there is **no CI**, no in-memory stores for testing, no connection pooling, a non-versioned migration runner, and **no AI-developer tooling** (one stale Claude skill, no hooks, no plugin, no isolated agent/skill test harness).

The rest of this document details findings by theme with `file:line` references, then proposes a prioritized roadmap.

---

## 2. The central gap: the cognitive/governance layer is inert

This is the most important section. Four mechanisms that the README and `implementation-plan.md` describe as core are not connected to runtime behavior.

### 2.1 Agents do not actually reason with a model
- `BaseAgent.run()` is the only path that calls the model (`agents/base.py:29-30`), and only the 3 stub agents (`qa_lead`, `data_analyst`, `software_engineer`) use it. The 6 "richer" agents override `run()` with hand-coded Python and **never call `model_gateway`** (e.g. `agents/repo_analyst/main.py:18-74`). ⟳ Since ADR-0007 the default mission now runs **all six** of these deterministic agents as the Temporal pipeline (`activities/planning.py:9-75`), so the production triage path is *entirely* model-free, not just the eval path.
- The `fake` model returns `f"[fake:{model_id}] {prompt[:500]}"` (`model_gateway/gateway.py:23`) — a prompt echo. Every eval and every `just check` runs on this echo, so **no test exercises real model reasoning**, and the "pass^k" eval semantics (`cli/main.py:48-55`) measure deterministic Python, not model quality.
- `StrandsAgentRuntime` (`runtime/strands_runtime.py`) constructs `Agent(system_prompt=...)` with **no tools and no skills**, wrapped in a bare `except Exception` that silently falls back (`strands_runtime.py:44-48`). Even when `strands` is installed it cannot call tools.

**Consequence:** the project cannot currently "complete the underlying objective" (triage/adjudicate/remediate security findings) for any case that isn't already hand-coded. It is a deterministic pipeline wearing an agent-swarm costume.

### 2.2 Skills are inert labels
- `skills/loader.py` (`list_skills`/`load_pack`/`validate_packs`) is imported **only by `tests/unit/test_skill_catalog.py`** — never by `src/`.
- No code reads `SKILL.md` *bodies* into any prompt. Skills surface only as `AgentResult.activated_skills`, and `BaseAgent` reports just the first one: `activated_skills=self.skills[:1]` (`agents/base.py:49`) — a placeholder bug.
- The implementation plan's §9 (Strands `AgentSkills` plugin, progressive disclosure, `set_available_skills`, activation audit) is unimplemented.

### 2.3 Tool policy is never enforced
- `tools/policy.py` (`ToolPolicy`/`ToolContext`) is exercised **only by its own unit test** (`tests/unit/test_harness_contracts.py`). No agent or activity routes a tool call through it.
- `repo_analyst` calls `provider.get_file(...)` directly (`agents/repo_analyst/main.py:34-36`) with no policy gate, despite README claiming "tool access is policy-gated and denied by default." ⟳ ADR-0007 added a **second** ungated provider read — `plan_mission` now calls `provider.get_issue("SEC-1")` directly in the planning activity (`activities/planning.py:30-33`), also with no policy gate (and a hardcoded issue id).
- All 26 `SKILL.md` files declare the **same** `allowed-tools` line regardless of phase, and the front-matter is explicitly "descriptive, not enforcement."

### 2.4 Approvals are collected but never gate execution
- `SupervisorWorkflow.approve_task`/`reject_task` updates store approver strings (⟳ `workflows/supervisor.py:120-149`) but the scheduling loop (⟳ `supervisor.py:62-90`) **never reads `self.approvals`**. `request_replan` terminally `return`s instead of replanning (⟳ `supervisor.py:49-52`) — "replan" is a misnomer for "stop." (Unchanged by ADR-0007, which added artifact propagation but no approval gating.)

> **Recommendation:** Treat 2.1–2.4 as the product's critical path. Pick **one** vertical slice (e.g. `ticket_analyst` → `risk_auditor`) and make it genuinely model-driven with real skill injection and a real policy gate end-to-end, on a *real local model* (Ollama), with golden evals that fail when the model misbehaves. Everything else is secondary to proving this loop works once.

---

## 3. Architecture & simplification

### 3.1 Three parallel, disconnected representations of "the plan/DAG"
1. ⟳ `activities/planning.py:6-75` — a hand-built linear `PlanVersion` driven by a hardcoded `PIPELINE` constant (was a static 2-task plan; ADR-0007 grew it to a 6-task chain but it is still a static, code-embedded DAG).
2. `runtime/graph_templates.py:23-52` — a `GraphTemplate` with its own `execution_order` topological sort and a `triage-readonly` registry — which already encodes a triage pipeline.
3. `workflows/supervisor.py:53-57` — its own inline topological scheduler.

The supervisor never consumes `graph_templates`; `plan_mission` never references them. The DAG algorithm is implemented twice, and ADR-0007's `PIPELINE` list now hardcodes a *fourth* shape of the same triage ordering that `graph_templates.triage_readonly_graph` already describes. **Collapse to one** plan representation and one scheduler — ideally have the planner emit the graph template the runtime already knows about.

### 3.2 Worker split is illusory
`workers/supervisor_worker.py:18-23` registers *both* workflows and *both* activities on one task queue; `workers/agent_worker.py` just re-calls `supervisor_worker.main` (`agent_worker.py:1-6`). There is no separate agent queue, so the implied isolation doesn't exist. Either give the agent worker its own task queue/registrations or delete it.

### 3.3 Hand-rolled observability with no exporter
`runtime/observability.py` reimplements a span (`span`, `RuntimeSpan`) that only computes a duration string and is manually flattened into telemetry at `agents/base.py:54-60`. `event_payload` (`observability.py:37`) is unused. OpenTelemetry is already a dependency — either wire a real exporter or drop the homegrown layer.

### 3.4 Dead / inert code (safe deletions)
- `temporal/errors.py` — `policy_denied`/`approval_required`/`validation_failed` have **zero call sites**; the retry policies' `non_retryable_error_types` therefore reference errors nothing ever raises.
- `agent_task.py:31-33` — both `if`/else branches `return result` (no-op branch).
- `runtime/artifacts.py:17` `execution_artifact`, `runtime/observability.py:37` `event_payload` — unused.
- `runtime/swarm_experiment.py`, `runtime/graph_templates.py`, `temporal/search_attributes.py` — "tested but unwired"; only test code references them, giving false coverage signal. `MissionSearchAttributes.as_keywords()` is never passed to any `start_workflow` (`api/app.py:48-53`, `cli/main.py:76`), so operational filtering is unavailable.
- `storage/checkpoints.py:41-68` `latest_for_task` — checkpoint *resume* path is dead (`AgentInvocation.checkpoint_resume` is never populated).
- `prompts.md` (all 9) — 3-line stubs with **zero readers**; the system prompt is hardcoded at `base.py:24-27`.
- `ActivityRetryProfile.GRAPH_WRITE`/`SANDBOX` (`temporal/policies.py:9-15`) silently collapse to `DEFAULT` (`policies.py:42-48`) — latent bug; only `MODEL`/`DEFAULT` are used.

---

## 4. Redundancy reduction (high-value deletions)

| Redundancy | Where | Fix | Approx. LOC saved |
|---|---|---|---|
| 9 near-identical `eval.py` (argparse/`main`/invocation boilerplate) | `agents/*/eval.py` (e.g. identical `main()` at `qa_lead/eval.py:39-54` == `data_analyst/eval.py:39-54`) | One parametrized harness in `eval_support` driven by `metadata.eval_entrypoint` + per-agent `input_builder`/`assertion` | ~400 |
| `_fixture_casefile()` duplicated in 5 evals + the test module | `repo_analyst/eval.py:16-25`, `security_reviewer/eval.py:19-37`, …, `test_next_wave_agents.py:21-25` | Single fixture factory in a shared test/eval helper | ~80 |
| Casefile `run()` skeleton repeated 6× | `repo_analyst/main.py:18-74`, `security_reviewer/main.py:16-59`, `risk_auditor/main.py:24-75`, `solutions_architect/main.py:16-60`, `test_engineer/main.py:15-50` | `CasefileAgent(BaseAgent)` base with one abstract `enrich(casefile) -> section` | ~120 |
| 26 byte-identical `SKILL.md` bodies | `skills/*/SKILL.md` (diff of any two differs only in name/description/pack) | Generate from one YAML registry + shared template, or load descriptions from a data file | ~600 of Markdown |
| Two near-identical provider adapters | `azure_devops.py`, `github.py` (repeated `raise_for_status()`+`.json()` ~8×/file; `_parse_dt` duplicated) | Shared `BaseHttpSourceProvider` with `_request()` helper; override only URL/payload/field-mapping | ~60 |
| `snapshot.model_dump() if hasattr(...)` | `api/app.py:64`, `cli/main.py:93` | One helper | small |
| `confidence: float = Field(0.0, ge=0, le=1)` declared 4× | `casefile.py:25,45,54` | `Confidence = Annotated[float, Field(ge=0, le=1)]` alias | small |

**Metadata/code drift to fix while here:** every agent's `metadata.yaml` lists **one** skill but `main.py` hardcodes **three** (e.g. `repo_analyst/metadata.yaml:11-12` vs `repo_analyst/main.py:81`). Make `build_agent` read skills/packs from metadata via the registry so there is a single source of truth — this also finally gives `loader.py` a runtime purpose. Add a registry-validation test (extend `validate_packs`) covering metadata schema + skill existence + metadata↔code consistency.

---

## 5. Correctness & Temporal determinism

These are latent landmines — the current happy path is safe, but the defaults make future edits dangerous, and there are no workflow tests to catch regressions.

- **Wall-clock in workflow-reachable code.** `RunSnapshot.updated_at` defaults to `datetime.now(UTC)` (`contracts/mission.py:106`) and `RunSnapshot` is constructed *inside* the workflow (`supervisor.py:27`). `model_validate(plan)` in the workflow (`supervisor.py:34`) re-runs default factories for any missing field, so a plan missing `created_at`/IDs would invoke `datetime.now`/`uuid4()` during replay → non-determinism. Use `workflow.now()` and freeze timestamps/IDs in the activity.
- **Approvals don't gate scheduling** (see §2.4) — ⟳ `supervisor.py:62-90` never checks `self.approvals`.
- **"Replan" terminates the run** instead of replanning (⟳ `supervisor.py:49-52`).
- **No concurrency.** Runnable sibling tasks execute strictly sequentially in a `for await` loop (⟳ `supervisor.py:62-90`); `GraphTemplate.max_concurrency` exists but is unused. (ADR-0007's pipeline is purely linear, so this is latent today, but the scheduler is what will serialize any future fan-out.) Independent branches should `asyncio.gather`.
- **Retry safety net is decorative** — `non_retryable_error_types` lists types nothing raises (§3.4); agents never raise (they always return `COMPLETED` at `base.py:43`), so there is effectively **no failure path** from a real agent error.
- **Broad `except` masks bugs.** `api/app.py:54-55` turns any `start_workflow` error (bad args, serialization) into "Temporal unavailable" 503. `strands_runtime.py` swallows all exceptions into a silent fallback.
- **`agent_task.py` ignores `TaskSpec.max_attempts`** (`mission.py:38`), hardcoding the `MODEL` retry profile (`agent_task.py:28`).

---

## 6. Testability

- **No DI seams in the activity/agent path.** `activities/run_agent.py:15` constructs `PostgresCheckpointStore()` internally (needs live Postgres or monkeypatch). `agents/base.py:29` instantiates `StrandsAgentRuntime` inside `run()`. `registry.build_agent` hardwires `build_model_gateway(get_settings())` with no override.
- **Global cached settings.** `get_settings()` is `@lru_cache`'d (`config.py:33`) and reached deep inside activities, the registry, and the gateway — per-test configuration requires cache clearing.
- **Asymmetric in-memory stores.** `storage/events.py` has `InMemoryEventStore`, but artifacts and checkpoints have **no** in-memory variant, so anything writing them needs a live DB.
- **CWD-dependent fixtures.** Evals/tests read `Path("tests/fixtures/...")` / `Path("src/ado_swarm/...")` (`repo_analyst/eval.py:18`, `ticket_analyst/eval.py:15`) — only resolve from repo root. Use `Path(__file__).parent`.
- **Whole subsystems untested.** No test imports cover: Temporal workflows, activities, workers, storage (artifacts/checkpoints/migrations), the API, the CLI, the real ADO/GitHub adapters (only `stub` is tested), or the model gateway's provider branches. The implementation plan's `tests/workflow/` and `tests/integration/` directories don't exist.
- **Eval assertions duplicate test assertions** (`security_reviewer/eval.py:60` vs `test_next_wave_agents.py`), so behavior is verified in two places that can drift.

---

## 7. Scalability & resource handling

- **Connection-per-call, no pooling.** Every storage method does `asyncpg.connect()`/close in `finally` (`storage/artifacts.py:16,41`; `storage/checkpoints.py:16,43`). `run_agent.py:16-17` calls `append` in a loop → one connect/disconnect per checkpoint. Adopt `asyncpg.create_pool` and inject the pool.
- **Unclosed httpx clients, rebuilt per request.** `AzureDevOpsSourceProvider`/`GitHubSourceProvider` create `httpx.AsyncClient` in `__init__` and never `aclose()` (`azure_devops.py:28`, `github.py:26`); the factory builds a fresh provider on every `/health` and CLI call (`api/app.py:28`, `cli/main.py:26`) → connection-pool leak. ⟳ ADR-0007 added another hot path: `plan_mission` builds a fresh provider on **every mission** (`activities/planning.py:30-31`) and discards it after one `get_issue`. Make providers async context managers and/or cache them.
- **Naive migration runner.** `storage/migrations.py:12-24` globs `*.sql`, sorts, and `execute()`s each whole file every run, relying on `IF NOT EXISTS` for idempotency. No version table, no per-migration transaction, no down-migrations; `ALTER TABLE ADD COLUMN` will fail on re-run. Uses a relative `Path("migrations")` (CWD-dependent). Adopt Alembic/yoyo or at minimum a `schema_migrations` table + per-file transaction.
- **No pagination.** Both real providers slice `[:limit]` of a single page (`github.py:120`, `azure_devops.py:127`) → silent truncation at scale. No 429/`Retry-After` handling; raw `httpx.HTTPStatusError` leaks to agent code.
- **No token capture.** The gateway creates a fresh client per call and never reads usage, so `BudgetUsage.input_tokens/output_tokens` (`budget.py`) can never be populated — token-budget enforcement is dead. The `budget_events` table (`migrations/0002:28-37`) has **no writer**.
- **Misleading health.** `KnowledgeStore.healthcheck()` always returns `"ok"` (`knowledge/graphiti_store.py:11`) even though it's an in-memory stub, so `/health` reports healthy with no real knowledge backend.

---

## 8. Data modeling (contracts)

The contracts are the strongest part of the codebase. Refinements:
- **`event_type: str` is stringly-typed** (`events.py:65`) while everything else is a `StrEnum` — close the vocabulary.
- **Two "needs approval" booleans** that are hand-synced and can disagree: `RemediationPlan.requires_human_approval` (`casefile.py:64`) vs `AgentResult.requires_approval` (`mission.py:83`). Single-source it.
- **`SecurityCasefile.final_disposition`** is an inline 7-value `Literal` (`casefile.py:79-87`) overlapping `FindingAdjudication` booleans (`casefile.py:40-43`); a casefile's disposition can contradict its adjudication with no validator. Make it a `StrEnum`, ideally derived.
- **`RunArtifact` vs `ArtifactRef`** overlap heavily (`artifacts.py:22` vs `events.py:37`) with no documented relationship and an unexplained `uri` optionality divergence.
- **`AgentInvocation.source_provider`/`model_profile` are free-form `str`** (`mission.py:63-64`) despite `SourceProviderKind` existing.
- **`severity: str | None`** (`casefile.py:22`) should be a normalized enum.
- `contracts/__init__.py` doesn't export `SourceBranch`/`SourceIssuePage`/`SourceFile`, weakening it as the public API.
- **Provider abstraction leak:** `SourceIssue.external_id` is non-uniform — GitHub uses bare number *or* `"{repo}#{number}"` (`github.py:50-53,66`), ADO uses raw id (`azure_devops.py:54`), so a caller can't round-trip an id generically. `ProviderMutationResult.external_id` means "created comment id" for ADO/GitHub but "issue id" for the stub (`stub.py:55`). `add_pr_comment` posts an issue comment on GitHub (`github.py:180`) but creates a PR thread on ADO (`azure_devops.py:188-193`). Pin these semantics in the contract. Also: the `SourceProvider` `Protocol` is never enforced (no implementation declares it; `factory.py:9` has no return annotation) — adding `-> SourceProvider` gives a free conformance check.

---

## 9. Developer experience & AI tooling

This is where the project is thinnest relative to its ambitions. Today there is exactly **one** AI-dev artifact (`.claude/skills/ado-swarm-development/SKILL.md`), **no CI**, **no hooks**, **no plugin**, and **no isolated agent/skill test harness**.

### 9.1 CI is missing entirely
`implementation-plan.md` §18 specifies `.github/workflows/ci.yml`, but it doesn't exist. **Add it first** — it's the cheapest high-value change and mirrors `just check`:
```yaml
name: ci
on: { pull_request: {}, push: { branches: [main] } }
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jdx/mise-action@v2
      - run: uv sync --all-extras --dev
      - run: uv run ruff format --check src tests
      - run: uv run ruff check src tests
      - run: uv run ty check
      - run: uv run pytest tests/unit
      - run: uv run ado-swarm eval-agents --model-profile fake
```
Add a separate (manual or `workflow_dispatch`) job for future `tests/integration` behind Docker services.

### 9.2 A SessionStart hook for Claude Code on the web
The repo is used via Claude Code on the web (this very session). A `.claude/settings.json` SessionStart hook that runs `uv sync --all-extras --dev` ensures every web session can immediately run tests/lint without a manual sync (we hit exactly this — deps were unsynced at session start). The `session-start-hook` skill can scaffold this.

### 9.3 `justfile` gaps
Strong base, but add the recipes that match the workflows developers actually need:
- `format-check` (CI parity: `ruff format --check`).
- `test-cov` (`pytest --cov`, the dep is already declared).
- `eval-agent-model agent profile` to run a single agent's eval against a **real** model (Ollama), not just `fake` — today `eval-agent` hardcodes `--model-profile fake`.
- `new-agent name` — scaffold a new agent directory from a template (see 9.5).
- `skills-validate` — run `validate_packs()` + metadata/code consistency check.
- `up-ollama` — `docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d`.
- `agent-repl agent` — drop into an interactive loop to send ad-hoc invocations to one agent (see 9.4).

### 9.4 An isolated agent & skill test harness (the user's explicit ask)
Today, testing one agent means hand-writing a `TaskSpec`/`AgentInvocation` (the duplicated eval boilerplate). Provide a first-class harness:
- `eval_support.run_agent_eval(agent_id, input_builder, assertion, *, model_profile)` — one function that builds the invocation, runs the agent, and returns a structured result. All 9 `eval.py` files shrink to a fixture + an assertion.
- A `ado-swarm agent run <agent_id> --casefile fixture.json --model-profile ollama` CLI command that runs a single agent against a casefile fixture and prints the `AgentResult` — enabling "test an agent in isolation against a real model" without Temporal/Postgres.
- A `ado-swarm skill show <skill>` / `ado-swarm skill lint` command once skills carry real bodies, so a skill's instructions can be inspected and validated independently.
- Golden-casefile fixtures under each agent's `fixtures/` (the plan's intended layout) resolved via `Path(__file__).parent`.

### 9.5 Agent scaffolding & a `claude` agent-author skill
After the `CasefileAgent` refactor (§4), a new agent should be: one `metadata.yaml` + one `enrich()` function. Provide:
- A `just new-agent <name>` generator (or a cookiecutter-style template dir) that emits the directory, `metadata.yaml`, a minimal `main.py`, and a fixtures stub — so no copy-paste.
- A repository **Claude skill** (`.claude/skills/ado-swarm-add-agent/`) that teaches the coding agent the (post-refactor) one-file pattern, the contracts to honor, and the eval requirement. Update the existing `ado-swarm-development` skill, which currently still describes the *old* per-`run()` pattern.

### 9.6 Plugin & hooks opportunities
- A small **Claude Code plugin** bundling the repo skills + a `/eval-agent` slash command + a pre-push hook that runs `skills-validate` would make the agent/skill workflow turnkey for contributors.
- A `PostToolUse`/pre-commit hook to regenerate `SKILL.md` files from the YAML registry (§4) so the catalog can't drift.

### 9.7 Docs are good but describe the aspiration
`README.md` and the ADRs claim policy-gating and agent reasoning that aren't wired (§2). Either implement them or add a prominent "Current limitations / what is stubbed" section so contributors aren't misled. `docs/architecture.md` is a single sentence — expand it or fold it into the (excellent) implementation plan.

---

## 10. Prioritized roadmap

**P0 — prove the core loop & stop the bleeding (1–2 wks)**
1. Add CI (`9.1`) and a SessionStart sync hook (`9.2`). Cheap, immediate.
2. Make **one** vertical slice genuinely model-driven on a real local model: real skill-body injection + a real `ToolPolicy` gate + golden evals that fail on bad model output (§2). This is the project's existential validation.
3. Fix the Temporal determinism landmines and wire approvals into scheduling (§5) — and add the first `tests/workflow/` tests using Temporal's test environment.

**P1 — collapse redundancy & add seams (1–2 wks)**
4. `CasefileAgent` base + single parametrized eval harness + metadata-driven skills (single source of truth) (§4, §9.4). ~600 LOC deleted.
5. Generate `SKILL.md` from a YAML registry; delete dead `prompts.md`/`errors.py`/`agent_worker.py`/unwired modules (§3.4, §4).
6. DI for stores/runtime/settings + in-memory artifact/checkpoint stores (§6).

**P2 — productionization (2–4 wks)**
7. Connection pooling, async-context-managed providers, real migration tool, pagination + rate-limit handling, token capture for budgets (§7).
8. Pin provider-abstraction semantics (`external_id`, mutation-result ids, `add_pr_comment`) and enforce the `Protocol` (§8).
9. Real KnowledgeStore (Graphiti/Neo4j) behind the existing port; honest `/health`.

**P3 — DX polish**
10. `just new-agent`, agent-author Claude skill, `ado-swarm agent run`/`skill show`, optional plugin (§9.5, §9.6).

---

## 11. Appendix — quick wins (low risk, do anytime)
- Delete: `temporal/errors.py`, `workers/agent_worker.py` (or make it real), `runtime/artifacts.py:execution_artifact`, `runtime/observability.py:event_payload`, all `prompts.md` stubs.
- Fix `activated_skills=self.skills[:1]` → report all (`base.py:49`).
- Remove the no-op `if` at `agent_task.py:31-33`.
- Complete or trim `ActivityRetryProfile` (`policies.py`).
- `Confidence` annotated-type alias (`casefile.py`).
- Resolve fixtures via `Path(__file__).parent`.
- Add `-> SourceProvider` return annotation to `factory.py` for a free conformance check.
- Move provider credential validation into a `Settings` validator so it fails at config load.
