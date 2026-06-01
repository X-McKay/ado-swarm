# ado-swarm Implementation Plan v2 — "From Swarm Costume to Durable Harness"

**Date:** 2026-05-31
**Author:** engineering review
**Inputs:** `docs/codebase-review-2026-05.md` (the current-state review), plus current-API research on the **Strands Agents SDK `1.41.0`**, the **Temporal Python SDK `temporalio 1.27.2`**, and the *harness-engineering* body of practice (`ai-boost/awesome-harness-engineering`); the **Willison agent/tool/skill vocabulary** (§2.0, `docs/concepts/agents-tools-skills.md`); and a reviewed **Workflow + Swarm architecture suggestion** (folded in as the §8-D1 resolution and Phase 1.5).
**Status:** Draft for review & discussion. Recommendations are made throughout; genuine forks are collected in **§8 Open decisions**.

---

## Implementation progress (branch `feature/claude-cleanup`)

- **Phase 0 — done.** CI template (`docs/ci/github-actions-ci.yml`), SessionStart hook, justfile recipes, determinism fixes (`workflow.now()`), DI seams + in-memory stores, dead-code removal, `tests/workflow/` time-skipping suite.
- **Phase 1 — done.** Strands model factory + deterministic `FakeModel`; `run_model_agent` runtime; `ToolPolicyHook` (`BeforeToolCallEvent`); tool catalog (15 tools); `AgentSkills`-bound skills single-sourced from metadata; **all 9 agents** model-driven via `CasefileAgent`/`run_model_agent`; non-deprecated `invoke_async(structured_output_model=...)`; shared golden-eval harness; vocabulary guardrail test.
- **Phase 1.5 — done.** Bounded adjudication swarm in `security_reviewer` (`agents/swarm_cell.py`): reviewer ensemble + judge inside one activity, hard model-call budget, opt-in (`use_swarm` / `security_reviewer_use_swarm`, default off) and eval-gated. ADR-0009.
- **Phase 2 — done.** Approvals as Temporal Updates+validators wired into the supervisor; typed non-retryable errors; `TaskSpec.max_attempts` honored; write tools approval-gated via `ToolContext` (ADR-0009).
- **Phase 3 (DX) — done.** `ado-swarm agents run` / `skills list|show|lint` / `scaffold agent|tool|skill`; `just` recipes; `CLAUDE.md`; `ado-swarm-add-agent` Claude skill; docs + ADR-0008 sweep.
- **Phase 4 — in progress.** Done: asyncpg connection pooling + versioned migration runner; source-provider hardening (async-ctx lifecycle, `_request` helper, 429/Retry-After retries, pagination, `ProviderError`); real token/budget capture into `AgentResult.budget_usage`; honest `/health`; knowledge tools (`graphiti_search`/`graphiti_add_episode`) + provider-read tools (`provider_get_issue`/`provider_search_issues`/`provider_get_repo_metadata`), recall wired into `security_reviewer`; collapsed the duplicate plan/DAG into one graph template (review §3.1); all 26 `SKILL.md` bodies rewritten with real guidance. Remaining: real Graphiti/Neo4j `KnowledgeStore` backend; OTel GenAI tracing; provider-contract semantics pinning (`external_id`, mutation-result ids).
- **Verification governor — done.** Sandboxed, allowlisted `run_validation_command` (`tools/catalog/verification.py` + `sandbox/provider.py::run_command`) wired into `test_engineer`: tests/lint/build are *run* (not just proposed), non-zero exit is a hard failure (the harness "governor").
- **Repository-investigation tools — done.** `repo_grep` (confirm a flagged pattern is present) and `repo_parse_manifest` (confirm the vulnerable package/version) wired into `repo_analyst`.
- **Provider write tools — done.** `provider_create_draft_pr` (draft only), `provider_add_issue_comment`, `provider_add_pr_comment` (`tools/catalog/provider_write.py`) — WRITE tools that require an approved `ToolContext` via the policy gate; declare them in an agent's `write_tool_names`. The draft-PR path is now available behind approval (no agent enables them by default yet).
- **Real KnowledgeStore backend — done.** `GraphitiKnowledgeStore` (Neo4j-backed via `graphiti-core`, lazy-imported, graceful degrade) selectable by `knowledge_backend=memory|graphiti`; `KnowledgeStorePort` Protocol; in-memory stays the default.
- **Submission agent — done.** `submission_engineer` consumes the approval-gated write tools (`provider_create_draft_pr`, `provider_add_issue_comment` in `write_tool_names`) to prepare a DRAFT PR + ticket disposition (`SubmissionResult` section), activating the `pull-request-preparation` / `ticket-disposition-update` skills. **Now the terminal node of the default Temporal pipeline**, behind a per-task approval gate: the planner marks the node `requires_approval`, and the supervisor parks the run (WAITING_FOR_APPROVAL) until `approve_task` is received, then dispatches it with an approved `ToolContext` so its write tools pass the gate (rejection cancels the run).
- **Git-history tool — done.** `SourceCommit` contract + `list_commits` on the provider port (stub/ADO/GitHub implementations) + `git_log_path` tool wired into `repo_analyst` for staleness/recent-fix evidence.
- **Not started.** OTel GenAI tracing; provider-contract semantics pinning (`external_id`, mutation-result ids); promoting the swarm default after an eval comparison.

Gate status: `ruff` + `ruff format` + `ty` clean; 157 unit/workflow tests pass (4 skipped); `eval-agents` 10/10 on `fake`; tool catalog = 22 tools; 10 agents (submission_engineer is the terminal, approval-gated pipeline stage).

---

## 1. How to read this

The review (`codebase-review-2026-05.md`) established the diagnosis: the contracts/scaffold are sound, but the three headline capabilities — *agents reason with a model*, *skills are progressively disclosed*, *tools are policy-gated* — and approvals **are not wired into the execution path** (review §2). The whole read-only triage pipeline is deterministic Python (review §2.1, sharpened by ADR-0007).

This plan turns that diagnosis into a buildable sequence, grounded in the **actual** current SDK APIs (verified by package introspection, not stale blog posts — see §7). It is organized as five phases (§5) with explicit acceptance gates (§9), three cross-cutting tracks (§6: policy, evals, observability), and a decisions list (§8).

The unifying frame from harness engineering: **Agent = Model + Harness.** Temporal is the *durable harness substrate* (loop, state, retries, human-in-the-loop, observability); Strands is the *cognitive layer* (model + tools + skills + structured output). We are currently shipping the harness with the cognitive layer stubbed out. This plan connects them.

---

## 2. Vocabulary & non-negotiables

### 2.0 Canonical vocabulary (Simon Willison) — the core rule
This project adopts Simon Willison's definitions as its **canonical vocabulary**, enforced in code review, scaffolding, linting, and docs (§6.4):

- **Agent** — *"tools in a loop to achieve a goal."* Software that calls an LLM with a prompt **and a set of tool definitions**, executes whichever tools the model requests, and feeds the results back into the model in a **bounded loop** until a stopping condition is met. **An agent without a model is not an agent.**
- **Tool** — an executable function/capability the harness provides to the agent: the agent's *hands*. Deterministic, typed, testable in isolation.
- **Skill** — *packaged expertise* (domain knowledge, instructions, behavioral patterns) loaded into the agent's context to shape *how* it approaches a problem (Anthropic "Agent Skills" / `SKILL.md` format). A skill is not code and takes no action; it is context.

> **THE CORE RULE (load-bearing):** **Every agent uses a model.** If a unit of work is deterministic, it is a **tool** (or a harness verification step), **never** an agent. We do not ship "deterministic agents." This resolves the old review distinction between "stub agents" and "richer agents": both were anti-patterns — the former did nothing real, the latter were deterministic Python masquerading as agents. Going forward, an `Agent` = model + tools (+ skills) in a loop; the deterministic logic those agents used moves into the **tool catalog** (§5 Phase 1).

This rule is the lens for the whole plan: Phase 1 turns the deterministic casefile-enrichment code into tools and makes every specialist a genuine tools-in-a-loop agent; the DX work (§6.4, Phase 3) makes the vocabulary impossible to drift from.

### 2.1 Non-negotiables
1. **Every agent is a model running tools in a loop; deterministic work is a tool.** (§2.0). Each agent must declare a model, ≥1 tool, and its skills; a model-less "agent" fails lint.
2. **Temporal owns orchestration; Strands owns single-agent reasoning.** Each specialist agent is a Strands `Agent` executed *inside a Temporal activity*. Temporal's `SupervisorWorkflow` remains the DAG/topology and the human-in-the-loop authority. We do **not** adopt Strands' own `Swarm`/`Graph` multi-agent orchestration for cross-agent flow (it would duplicate and fight Temporal's durability). Strands `Swarm`/`Graph` stay available for a *tightly-coupled sub-team inside one activity* if ever needed (§8-D1).
3. **Policy is structural, not prose.** Tool access is enforced at the Strands `BeforeToolCallEvent` hook (a real interception point), mapped to a PEP/PDP decision `ALLOW | DENY | REQUIRE_APPROVAL`. The `allowed-tools` field in `SKILL.md` is *documentation only* — Strands explicitly does not enforce it (§7.3). This directly fixes review §2.3.
4. **Verification is a governor, not advice.** Agent output is accepted only when it passes deterministic checks (schema validity, casefile invariants, and — for remediation — tests/linters in a sandbox). The model never self-certifies. This is the harness "hard environmental signal." (Verification checks are harness steps/tools, not agents — per §2.0.)
5. **Determinism stays in the workflow; all I/O and model calls stay in activities.** No wall-clock/uuid/model calls in workflow code (fixes review §5).
6. **Everything is eval-gated.** Golden casefiles + `pass^k`, deterministic assertions before any LLM-judge, the `fake` model keeps CI hermetic, a real local model (Ollama) runs in a nightly quality gate.

### 2.2 Stage execution modes — pick the right one per pipeline stage
A pipeline **stage** is not the same thing as an **agent**. Each stage runs in exactly one of three modes; the choice is made per stage and can change as a stage matures:

| Mode | What it is | Uses a model? | When |
|---|---|---|---|
| **Tool / harness step** | A bare deterministic tool call (or verification check) inside the activity — **no agent** | No | The work is fully deterministic (e.g. compute a risk threshold, run schema/test checks). Per §2.0 this is *not* a "deterministic agent" — it's a tool, and we never call it an agent. |
| **Single agent** | One Strands `Agent` — tools in a loop | Yes | The stage needs a model to decide/plan/judge over messy inputs (e.g. `repo_analyst` choosing what evidence to gather). |
| **Bounded swarm cell** | Multiple agents + a judge inside one activity, returning one typed result | Yes (several) | Multi-perspective critique measurably raises quality (e.g. `security_reviewer` adjudication — Phase 1.5). Only adopt where evals prove it beats single-agent. |

This reframes the common "deterministic / model-assisted / swarm" mode taxonomy so it stays consistent with the §2.0 rule: a "deterministic stage" is a **tool step with no agent**, never a deterministic agent. Default to the simplest mode that meets the quality bar; escalate to a swarm cell only when an eval justifies the added cost (a swarm cell is ~4× the model calls of a single agent).

---

## 3. Target architecture

```
 Operator / API / CLI
        │  start_mission(goal) · approve/reject (Update) · query snapshot
        ▼
┌─────────────────────────── Temporal (durable harness) ───────────────────────────┐
│  SupervisorWorkflow            — owns plan DAG, scheduling, approvals, snapshot     │
│    └─ AgentTaskWorkflow (child) — per task: route → run → verify → checkpoint       │
│         └─ run_agent ACTIVITY  ─────────────────────────────┐                       │
│         └─ verify ACTIVITY (sandbox tests/linters)          │                       │
└────────────────────────────────────────────────────────────┼───────────────────────┘
                                                              ▼
                              ┌──────────────── Strands Agent (cognitive layer) ──────┐
                              │  Agent(model, tools, plugins=[AgentSkills], hooks=[    │
                              │        ToolPolicyHook, BudgetHook, TelemetryHook])     │
                              │   • model  ← ModelProfile → BedrockModel/OpenAIModel/  │
                              │             OllamaModel/LiteLLMModel/FakeModel         │
                              │   • skills ← AgentSkills(src/ado_swarm/skills, strict) │
                              │   • tools  ← casefile_read, provider_get_file, …       │
                              │   • output ← agent.structured_output(SectionModel)     │
                              │   • state  ← take_snapshot()/load_snapshot() across    │
                              │             activity boundaries                        │
                              └───────────────────────────────────────────────────────┘
        Postgres (runs/plans/events/artifacts/budgets)   Neo4j+Graphiti (knowledge)
        OTel (GenAI semconv spans: workflow→activity→agent→model/tool)
```

**Responsibility split (unchanged from ADR-0001, now made real):**

| Concern | Owner | Mechanism |
|---|---|---|
| Plan/DAG, scheduling, retries, snapshot | Temporal workflow | `SupervisorWorkflow` (one plan representation — collapse the three from review §3.1) |
| Human approval gates | Temporal **Update + validator** | `approve_task`/`reject_task` (not signals — §7.6) |
| Model reasoning, tool calls, skill activation | Strands `Agent` in an activity | `run_agent` activity |
| Multi-perspective adjudication (where evals justify it) | **Bounded swarm cell** inside one activity | Strands `Swarm`/`Graph` → one typed result (Phase 1.5, §8-D1) |
| Tool authorization | Strands `BeforeToolCallEvent` hook | `ToolPolicyHook` → PEP/PDP |
| Typed casefile sections | Strands structured output | `agent.structured_output(Section, prompt)` |
| Cross-activity agent memory | Strands snapshots | `take_snapshot`/`load_snapshot` |
| Knowledge/recall | Graphiti behind `KnowledgeStore` | real Neo4j adapter |
| Verification | sandbox activity | tests/linters as governor |

---

## 4. Dependency & version decisions

| Package | Current pin | New pin | Why |
|---|---|---|---|
| `strands-agents` | `>=1.0` | `>=1.41,<1.42` **`[openai,ollama,litellm,otel]`** | Event names, `AgentSkills` Python API, snapshots, structured output all stabilized at 1.41 (§7). Bedrock is built-in (no extra). |
| `strands-agents-tools` | — | `>=0.7,<0.8` (optional) | Prebuilt tools if we want `shell`/`file_read` later; not required for read-only phase. |
| `temporalio` | `>=1.7` | `>=1.27,<1.28` **`[opentelemetry]`** | Updates-with-validator stage API, typed search attributes, time-skipping test env (§7). |
| Python | `>=3.11` | keep `>=3.11` | Strands needs `>=3.10`; fine. |
| `respx` (dev) | present | keep | provider adapter tests. |

**Model gateway decision:** retire the hand-rolled per-provider `ModelGateway.complete()` (review found it can't do tool-calling or token capture). Replace with a **`build_strands_model(profile: ModelProfile) -> strands.models.Model`** factory plus a deterministic **`FakeModel(Model)`** for `fake`. Agents talk to Strands, not to a bespoke completion shim. (See §7.2 for the exact constructor shapes — `base_url` lives in `client_args` for OpenAI-compatible, `host` for Ollama.)

---

## 5. Phases

Each phase leaves the repo green (`just check`) and shippable. Effort is rough (1 engineer).

### Phase 0 — Guardrails & test infrastructure (≈3–4 days)
*Goal: stop the bleeding and make the rest testable. No behavior change.*

- **CI** (`.github/workflows/ci.yml`) mirroring `just check` + `eval-agents --model-profile fake`; a separate `workflow_dispatch` job for Docker integration tests (review §9.1).
- **SessionStart hook** (`.claude/settings.json`) running `uv sync --all-extras --dev` so web sessions are immediately runnable (review §9.2).
- **Determinism fixes (review §5):** replace in-workflow `datetime.now`/`uuid4` defaults with values frozen in the planning activity; use `workflow.now()`/`workflow.uuid4()` where a workflow must generate them. Add a `tests/workflow/` suite using `WorkflowEnvironment.start_time_skipping()` (§7.3) that runs the supervisor end-to-end with mocked activities — this is the regression net for everything after.
- **DI seams (review §6):** inject `CheckpointStore`/`ArtifactStore`/`Settings`/runtime into activities and `build_agent` instead of constructing inside; add in-memory artifact & checkpoint stores so agent/activity tests need no Postgres.
- **Quick wins (review §11):** delete `temporal/errors.py` (or start raising them — see Phase 2), the no-op `if` in `agent_task.py`, `prompts.md` stubs (replaced in Phase 1), `event_payload`/`execution_artifact`; fix `activated_skills=self.skills[:1]`; resolve fixtures via `Path(__file__).parent`; add `-> SourceProvider` to the factory.

**Acceptance:** CI green on PRs; `tests/workflow/` proves a mission runs, pauses on approval, cancels, and replays deterministically; agent unit tests run with zero external services.

### Phase 1 — The real agent runtime (the existential slice) (≈1.5–2 wks)
*Goal: one vertical slice genuinely reasons with a model, activates skills, and is tool-gated. This is the project's make-or-break (review §2, §10-P0).*

Pick the slice **`ticket_analyst → repo_analyst → risk_auditor`** (covers normalize → evidence-with-a-tool → classify).

0. **Extract the tool catalog & audit the agents (the §2.0 rule made concrete).** Today's deterministic "enrichment" code is exactly the deterministic work that must become **tools**, not agents:
   - `ticket_analyst/normalization.py` (279 LOC deterministic normalizer) → a `normalize_finding(issue) -> NormalizedFinding` **tool**. The *agent* handles the messy/ambiguous issues the deterministic normalizer can't and decides when to call it. **This is the canonical example of the rule** — keep the well-tested deterministic logic, demote it from "the agent" to "a tool the agent calls."
   - `repo_analyst` file-existence/repo-resolution logic → `repository_resolve`, `verify_file_location`, `get_git_history` tools.
   - `risk_auditor`/`security_reviewer` heuristics → `score_severity`, `fingerprint_finding`, `lookup_duplicate(knowledge)` tools.
   Land these in a **tool registry** (`tools/catalog/`) of `@tool`-decorated functions with typed I/O, each unit-testable in isolation (deterministic tools are the *easy* test surface). Then **audit all 9 agents**: each must have a genuine model-reasoning job and declare model + ≥1 tool + skills; any that are pure deterministic aggregation are demoted to tools or harness steps (candidates flagged in §8-D2). The two anti-patterns from the review — canned-text "stub agents" (`qa_lead`/`data_analyst`/`software_engineer`) and deterministic "richer agents" — are both eliminated here.
1. **Strands model factory + FakeModel** (§4, §7.2). `ModelProfile` → `strands.models.Model`. `FakeModel` returns deterministic, templated structured output so CI stays hermetic and offline (and keeps the now model-driven agents testable without a server).
2. **`StrandsAgentRuntime` rewrite.** Build a real `Agent(model=…, tools=…, plugins=[AgentSkills(...)], hooks=[ToolPolicyHook, BudgetHook, TelemetryHook])`. Remove the silent bare-`except` fallback (review §2.1, §5) — failures must surface as typed errors.
3. **Skills become real.** Point `AgentSkills` at `src/ado_swarm/skills/` (its `SKILL.md` format already matches Strands' expected frontmatter — `name`, `description`, `allowed-tools`; §7.4). Drive *which* skills are available per agent from `metadata.yaml` (single source of truth — fixes review §2.2 metadata/code drift), and switch packs per phase via `set_available_skills`. Record `get_activated_skills()` into `AgentResult.activated_skills` and the audit trail. **This alone makes the 26 skills load-bearing instead of decorative.**
4. **Tool policy via hook.** Convert `tools/policy.py` into a Strands `HookProvider` on `BeforeToolCallEvent` that consults `ToolContext` (agent id, phase, risk, approval state, repo allowlist) and returns `ALLOW | DENY | REQUIRE_APPROVAL`; `DENY`/`REQUIRE_APPROVAL` set `event.cancel_tool` (§7.3). Wrap the existing provider calls (`provider.get_file`, `provider.get_issue`) as `@tool` functions so they flow through the gate — fixes the ungated reads in review §2.3 and ADR-0007.
5. **Structured output for casefile sections.** Each specialist runs its skill-driven, tool-using reasoning loop (calling the catalog tools from step 0), then emits its typed section via `agent.structured_output(RepositoryEvidence | FindingAdjudication | RiskClassification, prompt)` (§7.5). The deterministic catalog tools are the agent's *hands and verifier* — the model decides, the tools compute precisely and the section is schema-checked as a governor (§6.2). (Gotcha: `structured_output` bypasses tool hooks — do tool-using work in the `agent(...)` loop *first*, then extract the typed section; §7.5.)
6. **Golden evals that can fail.** 8–12 golden casefiles per slice agent with expected dispositions; deterministic assertions; `pass^k` (k≥3) on the **real** model (Ollama) in a nightly job, `fake` in CI. Wire the existing `pass_k` plumbing (`cli/main.py`).

**Acceptance:** with `MODEL_PROVIDER=ollama`, every slice agent makes ≥1 real model call **and** ≥1 tool call (no model-less agents; the former `normalization.py` now runs as the `normalize_finding` tool); a denied tool is provably blocked by the hook (a test asserts `cancel_tool` fired); skills show up in `activated_skills`; golden evals pass `pass^3` on the local model and are deterministic on `fake`. Catalog tools have isolated unit tests.

### Phase 1.5 — Bounded adjudication swarm in `security_reviewer` (resolves §8-D1) (≈1 wk)
*Goal: introduce one **bounded swarm cell** where multi-perspective critique genuinely raises decision quality — only after the single-agent loop (M1) is proven reliable. This is the §8-D1 resolution: yes to intra-stage multi-agent, starting here and nowhere else yet.*

`security_reviewer` is the right (and only initial) candidate: adjudication benefits from independent perspectives. Inside the single `security_reviewer` activity, run a Strands `Swarm`/`GraphBuilder` cell:
- A stale-finding reviewer, a false-positive reviewer, and a duplicate/already-fixed reviewer each argue their case (each a model agent with the relevant skill + read tools).
- An **adjudication judge** reconciles them into one **strict-schema** `FindingAdjudication` (typed, not free-form debate).

The cell stays a **bounded swarm cell** — it is harness machinery inside one activity, governed by:
- **Budget cap** (`BudgetHook`): hard ceiling on model/tool calls per finding (an ensemble+judge is ~4× a single agent — this is the dominant cost line, so the cap is mandatory).
- **Timeout** (cell-level + Temporal `node_timeout`/`execution_timeout` on the Strands `Swarm`).
- **Tool policy**: every sub-agent's tools flow through the same `ToolPolicyHook`.
- **Strict judge output schema**: the judge emits a contract-backed `FindingAdjudication` via `structured_output`; reviewers hand off typed positions, not prose (mitigates the "multi-agent fails without explicit coordination" risk from the harness research).
- **Transcript as artifact**: the swarm transcript/summary is stored as a `RunArtifact` for audit; the Temporal workflow still sees exactly one `security_reviewer` task returning one typed result — workflow history stays understandable and deterministic.

**Design note — retry/idempotency (call this out now so we don't trip later):** a swarm cell inside an activity is non-idempotent and *expensive to retry* — a transient failure near the judge re-runs all reviewers. Mitigate by (a) checkpointing reviewer results within the cell (resume the judge without re-debating), (b) a generous `start_to_close_timeout` with a conservative retry policy on this activity, and (c) caching per-finding adjudication keyed by finding fingerprint so a Temporal retry short-circuits completed reviewers.

**Implementation choice (kept simple initially):** run the reviewers *inside one activity* via Strands `Swarm` (shared context, simple handoffs) rather than one Temporal activity per reviewer. We trade per-reviewer durability/visibility for simplicity; revisit only if a reviewer needs independent retry/approval (the child-workflow-per-reviewer alternative is noted in §8-D1).

**Acceptance:** on an ambiguous golden finding, the swarm cell produces a `FindingAdjudication` that beats the single-agent baseline on the adjudication golden set (measured by `pass^k` agreement with expected disposition); a budget breach halts the cell with a typed error; the transcript is persisted as an artifact; Temporal still sees one task and replays deterministically. If the swarm does **not** beat the single-agent baseline on evals, we keep `security_reviewer` single-agent (the eval is the decision gate).

### Phase 2 — Temporal correctness & real approvals (≈1 wk)
*Goal: make the governance layer real (review §2.4, §5).*

- **Approvals as Updates.** Convert `approve_task`/`reject_task` to drive scheduling: a `REQUIRE_APPROVAL` tool decision (or `AgentResult.requires_approval`) parks the task; the workflow `wait_condition`s on an approval recorded by a `@workflow.update` **with a validator** (reject bad approvals before they hit history; §7.6). On approval, re-dispatch the task with an approval token in `ToolContext` that flips the gate to `ALLOW`. Fixes "approvals collected but never gate" (review §2.4).
- **Real "replan"** instead of terminal return: `request_replan` loops back to the planner activity rather than ending the run (review §5).
- **Typed failures.** Agents/activities raise `ApplicationError(type="PolicyDenied"|"ApprovalRequired"|"ValidationFailed", non_retryable=True)`; wire these into `non_retryable_error_types` so the retry net is real, not decorative (review §3.4, §5). Honor `TaskSpec.max_attempts` in the child workflow retry policy (review §5).
- **Concurrency.** Let independent runnable siblings run via `asyncio.gather` (latent today with the linear pipeline, but the scheduler is the bottleneck for any future fan-out; review §5).
- **Collapse the three plan/DAG representations** (review §3.1) into one: have the planner emit the graph the runtime already understands (reuse `graph_templates`), delete the duplicate scheduler/`PIPELINE` constant.

**Acceptance:** a `tests/workflow/` test drives a remediation task to `WAITING_FOR_APPROVAL`, sends an `approve_task` Update, and observes the gated tool now executing; a rejected approval is refused by the validator; a policy-denied tool fails the task as a non-retryable `ApplicationError`.

### Phase 3 — Collapse redundancy & developer experience (≈1 wk)
*Goal: delete ~600–800 LOC and make new agents/skills a one-file affair (review §4, §9).*

- **`CasefileAgent(BaseAgent)`** base owning the `casefile_from_invocation → guard → run-agent-loop → audit → casefile_artifact` skeleton. Per §2.0 the per-agent surface is **declarative, not deterministic code**: each specialist declares its `tools`, `skills`/pack, the structured-output `section_model`, and a prompt template; the base runs the Strands agent loop and writes the typed section. (Contrast the review's original "abstract `enrich(casefile)->section`" idea, which assumed deterministic producers — that would violate the core rule; the deterministic parts now live in the tool catalog from Phase 1.)
- **One parametrized eval harness** in `eval_support` driven by `metadata.eval_entrypoint` + a per-agent `input_builder`/`assertion`; the 9 `eval.py` files shrink to a fixture + an assertion (review §4, ~400 LOC). Single shared `_fixture_casefile()`.
- **Skill catalog from data.** Generate `SKILL.md` from one YAML registry + template (review §4, ~600 MD LOC), with a pre-commit/`PostToolUse` hook to keep them in sync. Per-skill `allowed-tools` becomes real per-phase data (today all 26 are identical).
- **Isolated agent/skill harness (explicit ask, review §9.4):**
  - `ado-swarm agent run <id> --casefile fixture.json --model-profile ollama` — run one agent against a fixture, print the `AgentResult`, no Temporal/Postgres.
  - `ado-swarm skill show <name>` / `skill lint` — inspect/validate a skill body in isolation.
  - `just new-agent <name>` scaffolder; `just eval-agent-model`, `just skills-validate`, `just up-ollama`, `just agent-repl` (review §9.3).
- **Agent-author Claude skill** (`.claude/skills/ado-swarm-add-agent/`) teaching the post-refactor one-file pattern; update the stale `ado-swarm-development` skill. Optional Claude Code **plugin** bundling skills + `/eval-agent` slash command (review §9.5–9.6).

**Acceptance:** adding an agent = one `metadata.yaml` + one `enrich()` + one fixture; `skills-validate` catches drift; `just new-agent` produces a runnable, eval-passing stub; net LOC down ≥500.

### Phase 4 — Productionization & memory (≈2–3 wks)
*Goal: make it scale and remember (review §7, §8).*

- **Resource handling (review §7):** `asyncpg.create_pool` injected into stores; providers as async context managers, cached/closed; real migration tool (Alembic/yoyo or a `schema_migrations` table + per-file transactions); pagination + 429/`Retry-After` in ADO/GitHub adapters; CWD-independent migration path.
- **Budgets are real:** capture token usage from Strands (`EventLoopMetrics`/model usage) in a `BudgetHook`, write `budget_events` (the table exists with no writer), enforce `BudgetUsage` limits — fixes review §7 dead budget path.
- **Observability (cross-cutting §6):** replace homegrown spans with Strands `StrandsTelemetry` OTLP + Temporal `TracingInterceptor`, emitting OTel **GenAI semantic-convention** spans; propagate trace context workflow→activity→agent→model/tool. Honest `/health` (review §7 misleading health).
- **Real KnowledgeStore:** Graphiti/Neo4j behind the existing port (`add_casefile_episode`, `search_related_findings`, `record_outcome_episode`); use it for duplicate/stale adjudication recall — turning the `security_reviewer` from heuristics into evidence-backed memory lookups.
- **Provider-contract hardening (review §8):** pin `external_id`/`ProviderMutationResult`/`add_pr_comment` semantics; enforce the `SourceProvider` `Protocol`; normalize `severity`/disposition enums; single-source the two approval booleans.

**Acceptance:** load test shows pooled connections and no client leaks; `budget_events` populated and a budget breach halts a run; a trace spans operator→workflow→agent→model in the OTel backend; a duplicate finding is adjudicated via a Graphiti recall hit.

---

## 6. Cross-cutting tracks

### 6.1 Policy model (PEP/PDP) — the harness "structural enforcement"
A single decision function, consulted at the Strands tool boundary and mirrored in the workflow:
```
decide(tool, ToolContext) -> ALLOW | DENY | REQUIRE_APPROVAL
  inputs: agent_id, phase, risk_tier, trust_zone, repo_allowlist,
          provider_kind, approval_state, write?/destructive?
```
- `ALLOW` → tool runs.
- `DENY` → `event.cancel_tool="…"`; agent gets a structured refusal it can reason about.
- `REQUIRE_APPROVAL` → cancel + mark `AgentResult.requires_approval`; Temporal parks the task on an `approve_task` Update. Approval re-dispatches with a token → gate returns `ALLOW`.

This implements the harness "5-layer permission / PEP-PDP / ALLOW-DENY-REQUIRE_APPROVAL" pattern structurally, and uses a **two-tier review** posture (deterministic gate first; humans only for genuinely risky/low-confidence actions) to avoid approval fatigue.

### 6.2 Evaluation harness — "eval-driven development"
- **Golden sets per agent** under `agents/<id>/fixtures/` (20–50 total across stale/duplicate/dependency/risky-SAST/false-positive/ambiguous, per the original plan §15).
- **Layered checks:** deterministic/structural assertions (schema valid, casefile invariants, expected disposition) run first and gate CI on `fake`; an optional **LLM-as-judge** (promptfoo-style) only adjudicates the residual on the nightly real-model run.
- **`pass^k`:** each case run k times; require all/most passes to measure reliability under stochasticity (the existing `pass_k` field is the hook). Track per-skill activation and tool-call requests in the eval result.
- **CI wiring:** `fake` in PR CI (hermetic); Ollama `pass^3` nightly; regression gate on golden disposition changes.

### 6.3 Observability — OTel GenAI semconv end-to-end
Strands `StrandsTelemetry().setup_otlp_exporter()` + Temporal `temporalio.contrib.opentelemetry.TracingInterceptor`, GenAI semantic-convention attributes, trace-context propagation across every swarm hop. Treat traces as queryable data for debugging multi-turn failures and building evaluators (Langfuse/Phoenix/Braintrust optional backends).

### 6.4 Vocabulary as a guardrail (Agent / Tool / Skill) — steering future development
The §2.0 definitions must be *enforced and taught*, not just stated, so the codebase can't drift back into "deterministic agents":
- **Canonical doc** (`docs/concepts/agents-tools-skills.md`): the Willison definitions, the core rule, the anti-patterns we removed, and a decision flowchart ("Is it deterministic? → tool. Does it need a model to decide? → agent. Is it context/instructions? → skill."), with a worked example (`normalize_finding` tool vs `ticket_analyst` agent). Linked from `README.md` and `CONTRIBUTING`.
- **Registry validation / lint** (extends `validate_packs`): every `metadata.yaml` agent must declare a model profile, ≥1 tool, and skills; CI **fails** on a model-less agent or an agent whose `run()` makes no model call. A tool must be a typed `@tool` with a unit test; a skill must be a valid `SKILL.md`.
- **Scaffolders teach the pattern:** `just new-agent` emits a model-driven tools-in-a-loop agent (never a deterministic stub); `just new-tool` emits a typed `@tool` + test; `just new-skill` emits a `SKILL.md` from the registry. The `ado-swarm-add-agent` Claude skill and the updated `ado-swarm-development` skill state the three definitions and the core rule up front.
- **Review checklist** item: "New agent? Justify the model-reasoning job. Deterministic? Make it a tool." This is the cheapest, highest-leverage steering mechanism.

---

## 7. Concrete API appendix (verified against installed packages)

### 7.1 Versions
`strands-agents==1.41.0` (Py≥3.10), `strands-agents-tools==0.7.0`, `temporalio==1.27.2` (Py≥3.9, Pydantic v2 converter).

### 7.2 Strands model factory
```python
from strands.models import BedrockModel
from strands.models.openai import OpenAIModel
from strands.models.ollama import OllamaModel
from strands.models.litellm import LiteLLMModel

def build_strands_model(p: ModelProfile):
    if p.provider == "fake":     return FakeModel(p)                 # deterministic, offline
    if p.provider == "bedrock":  return BedrockModel(model_id=p.model_id, region_name=p.region)
    if p.provider == "ollama":   return OllamaModel(host=p.base_url, model_id=p.model_id)  # host!
    if p.provider in ("openai", "openai_compatible"):
        return OpenAIModel(                                          # base_url INSIDE client_args!
            client_args={"api_key": p.api_key or "not-needed", "base_url": p.base_url},
            model_id=p.model_id, params={"temperature": p.temperature, "max_tokens": p.max_tokens})
    if p.provider == "litellm":  return LiteLLMModel(model_id=p.model_id, client_args=p.client_args)
    raise ValueError(p.provider)
```

### 7.3 Tool-policy hook (the enforcement point)
```python
from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent

class ToolPolicyHook(HookProvider):
    def __init__(self, ctx: ToolContext, policy: ToolPolicy): self.ctx, self.policy = ctx, policy
    def register_hooks(self, r: HookRegistry) -> None:
        r.add_callback(BeforeToolCallEvent, self._gate)
    def _gate(self, e: BeforeToolCallEvent) -> None:
        decision = self.policy.decide(e.tool_use["name"], self.ctx)
        if decision is Decision.DENY:
            e.cancel_tool = f"Tool '{e.tool_use['name']}' denied by policy."
        elif decision is Decision.REQUIRE_APPROVAL:
            e.cancel_tool = "approval-required"; self.ctx.mark_approval_required(e.tool_use)
agent = Agent(model=m, tools=[...], hooks=[ToolPolicyHook(ctx, policy)])
```

### 7.4 Skills plugin (progressive disclosure, real)
```python
from strands import Agent, AgentSkills
plugin = AgentSkills(skills="src/ado_swarm/skills", strict=True)  # dir of SKILL.md skill dirs
agent = Agent(model=m, plugins=[plugin])
plugin.set_available_skills(load_pack("triage-readonly"))   # phase-scoped availability
# after run:
activated = plugin.get_activated_skills(agent)              # -> list[str] for the audit trail
```
`SKILL.md` frontmatter already matches: `name` (must equal dir, lowercase-hyphen), `description`, optional `allowed-tools` (documentation only — gate via 7.3).

### 7.5 Structured output (typed casefile sections)
```python
section = await agent.structured_output_async(RiskClassification, "Classify risk for this finding")
```
Caveat: `structured_output` does **not** fire `BeforeToolCallEvent`/`MessageAddedEvent`. Pattern: run tool-using reasoning with `await agent.invoke_async(prompt)` first (gated), then a `structured_output_async` call to emit the typed section.

### 7.6 Temporal approvals (Update + validator) & determinism
```python
@workflow.update
def approve_task(self, task_id: str, approver: str) -> str:
    self.approvals[task_id] = approver; return "approved"
@approve_task.validator
def _v(self, task_id: str, approver: str) -> None:
    if task_id not in self.awaiting_approval: raise ValueError("task not awaiting approval")
# scheduling loop now: await workflow.wait_condition(lambda: task_id in self.approvals or ...)
# client: await handle.execute_update(SupervisorWorkflow.approve_task, args=[tid, "alice"])
```
Determinism: `workflow.now()`, `workflow.uuid4()`, `workflow.random()`; freeze timestamps/ids in activities; pass Pydantic models via `pydantic_data_converter`.

### 7.7 Snapshots across activity boundaries
```python
snap = agent.take_snapshot(preset="session")     # JSON-able dataclass -> store in workflow/Postgres
# next activity:
agent2 = Agent(model=m, tools=[...]); agent2.load_snapshot(snap)
```

### 7.8 Time-skipping workflow tests
```python
async with await WorkflowEnvironment.start_time_skipping() as env:
    @activity.defn(name="run_agent")           # mock by matching name
    async def fake_run_agent(...): return AgentResult(...)
    async with Worker(env.client, task_queue=tq, workflows=[SupervisorWorkflow, AgentTaskWorkflow],
                      activities=[fake_run_agent, fake_plan_mission]):
        handle = await env.client.start_workflow(SupervisorWorkflow.run, args=[rid, goal], id=..., task_queue=tq)
        await handle.execute_update(SupervisorWorkflow.approve_task, args=[tid, "alice"])
        snap = await handle.query(SupervisorWorkflow.get_snapshot)
```

---

## 8. Open decisions (for discussion)

- **D1 — Multi-agent ownership.** *Decided:* **Temporal owns cross-agent orchestration; Strands agents run one-per-activity** — *and* we adopt **bounded swarm cells inside a single activity** where evals prove they raise quality, starting with `security_reviewer` adjudication (**Phase 1.5**, §5). We do **not** hand the whole pipeline to a Strands `Swarm` (that would cede durability/visibility/approval granularity to Strands). The cell stays inside one activity, governed by budget/timeout/tool-policy/strict-judge-schema, returns one typed result, and persists its transcript as an artifact — Temporal sees one task. *Open sub-question:* if a sub-reviewer ever needs independent retry/approval, promote that cell from an in-activity Strands `Swarm` to one Temporal activity/child-workflow per reviewer (heavier, more durable). Default: in-activity swarm.
- **D2 — Agent vs tool demotion (the §2.0 rule applied per unit).** *Decided:* **all agents use a model** (no deterministic agents). The remaining open question is which of today's 9 "agents" are genuine tools-in-a-loop agents vs. should be **demoted to tools or harness steps**. *Recommended:* keep as model-driven agents — `ticket_analyst` (normalize messy/ambiguous issues), `repo_analyst` (decide what evidence to gather, call repo tools), `security_reviewer` (adjudicate stale/dup/false-positive), `risk_auditor` (score risk/eligibility), `solutions_architect` (plan), `test_engineer` (validation strategy). *Demote/justify:* `qa_lead` (intake coordination — may be a workflow/harness step, not an agent), `data_analyst` (analytics — agent only if it genuinely reasons over patterns; otherwise a reporting tool/query), `software_engineer` (out of scope this plan — §8-D7). Confirm the keep/demote list per agent.
- **D3 — Local model target.** Ollama model for the nightly quality gate (e.g. a small Llama/Qwen). Tradeoff: bigger = better evals, slower CI. *Recommended:* a small instruct model for `pass^k`, Bedrock for staging.
- **D4 — Memory backend.** Graphiti+Neo4j (already scaffolded) vs. add mem0/Zep for cross-session recall. *Recommended:* finish Graphiti first (it's in the plan/ADR), revisit mem0 only if recall quality is insufficient.
- **D5 — Migrations tool.** Alembic (heavier, autogenerate) vs. yoyo/`schema_migrations`-table (lighter). *Recommended:* lightweight version table + per-file transactions unless we need autogenerate.
- **D6 — Structured output vs tool-emitted JSON.** `structured_output` is clean but bypasses tool hooks (§7.5). For write-capable agents that must stay gated end-to-end, prefer a gated `emit_section` tool. Discuss per risk tier.
- **D7 — Scope of write capability in this plan.** Recommendation: this plan keeps everything read-only/draft; the `software_engineer`/sandbox-write path is explicitly *out of scope* until the policy+approval+verification loop is proven on read-only.

---

## 9. Sequencing & milestones (acceptance gates)

| Milestone | Phase | Gate |
|---|---|---|
| **M0 Infra** | 0 | CI green; `tests/workflow/` proves mission lifecycle (run/pause/approve/cancel/replay) with mocked activities; agent tests need no services. |
| **M1 Cognitive slice** | 1 | `ticket_analyst→repo_analyst→risk_auditor` reason via Ollama; a denied tool is provably blocked; skills appear in `activated_skills`; golden evals `pass^3` on local model, deterministic on `fake`. |
| **M1.5 Swarm cell** | 1.5 | `security_reviewer` adjudication swarm beats the single-agent baseline on the adjudication golden set; budget breach halts the cell; transcript persisted as artifact; Temporal still sees one task and replays deterministically. *If it doesn't beat the baseline, stay single-agent.* |
| **M2 Governance** | 2 | Approval Update gates a real tool; rejection refused by validator; policy-denied tool → non-retryable `ApplicationError`; one plan/scheduler representation. |
| **M3 DX/dedup** | 3 | New agent = 1 metadata + 1 `enrich()` + 1 fixture; `ado-swarm agent run` works against a real model; `skills-validate` catches drift; ≥500 LOC removed. |
| **M4 Production** | 4 | Pooled DB + leak-free providers; `budget_events` enforced; OTel trace operator→model; Graphiti recall used in adjudication. |

**Recommended first wave:** M0 → M1. M1 is the existential validation from review §10-P0 — if the cognitive loop can't reliably produce correct dispositions on a local model with `pass^k`, that finding should reshape everything after it. Everything from M2 on assumes M1 succeeded.

---

## 10. Mapping back to the review

| Review finding | Addressed in |
|---|---|
| §2.1 agents don't reason | Phase 1 (Strands runtime, structured output) |
| §2.2 skills inert | Phase 1 (`AgentSkills`, metadata single-source) |
| §2.3 policy not enforced | Phase 1 (`ToolPolicyHook`) + §6.1 |
| §2.4 approvals don't gate | Phase 2 (Update+validator) |
| §3.1 three plan/DAG reps | Phase 2 (collapse to one) |
| §3.4 dead code | Phase 0 quick wins |
| §4 redundancy (~700 LOC) | Phase 3 (`CasefileAgent`, eval harness, skill gen) |
| §5 determinism/retry/replan | Phase 0 + Phase 2 |
| §6 testability | Phase 0 (DI, in-memory stores, workflow tests) |
| §7 scale/resources/budgets | Phase 4 |
| §8 contracts hardening | Phase 4 |
| §9 DX & AI tooling | Phase 0 (CI/hook) + Phase 3 (harness, scaffolder, skill/plugin) |
</content>
