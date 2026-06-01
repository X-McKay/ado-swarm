# ado-swarm

`ado-swarm` is a Python-first, Docker-first foundation for a Temporal-orchestrated security remediation agent swarm. The base architecture supports Azure DevOps and GitHub through provider-neutral source-provider ports, uses Postgres for operational state, and reserves Neo4j + Graphiti for long-term knowledge memory.

Each specialist agent is a model-driven [Strands](https://strandsagents.com/) agent — *tools in a loop* — executed inside a Temporal activity: the model reasons, calls deterministic catalog tools through a structural policy gate, activates skills, and emits one typed casefile section. The implementation focuses on read-only triage and planning, with write/remediation paths gated behind approval.

## Quick start

```bash
mise install
just setup
just check
just eval-agents
```

To run local infrastructure:

```bash
cp .env.example .env
just up
just smoke
```

## Architecture summary

Temporal owns durable orchestration (plan/DAG, retries, approvals, snapshots). Strands owns single-agent reasoning, run inside Temporal activities. Provider adapters hide Azure DevOps and GitHub differences behind canonical contracts. Tool access is enforced structurally at the Strands `BeforeToolCallEvent` hook (`ALLOW | DENY | REQUIRE_APPROVAL`) — denied by default outside the agent's declared tools, and write tools require approval. See [`docs/architecture.md`](docs/architecture.md) and [`docs/decisions/`](docs/decisions/).

## Core concepts: agents, tools, and skills

This project follows Simon Willison's definitions: an **agent** is *tools in a loop* (an LLM that calls tools and feeds results back until done — it always uses a model), a **tool** is a deterministic executable capability the harness gives the agent, and a **skill** is packaged expertise loaded into context. **The core rule: every agent uses a model; anything deterministic is a tool, never an agent.** See [`docs/concepts/agents-tools-skills.md`](docs/concepts/agents-tools-skills.md).

## Agent catalog

Each agent lives under `src/ado_swarm/agents/<agent_name>/` and has:

| File | Purpose |
|---|---|
| `main.py` | The `CasefileAgent` subclass (declares its `tool_names`, `section_model`, prompts) plus a `build_agent()` factory. ~30 lines. |
| `metadata.yaml` | Identity, version, `skills` (the single source of truth), tools, risk tier, and eval entrypoint. |
| `eval.py` | Golden evaluation using the shared harness (`run_agent_eval`) with a scripted `FakeModel`. |
| `fixtures/` | Optional golden inputs. |

Agents are model-driven: `main.py` declares which catalog **tools** the agent may call and which typed casefile **section** it emits; **skills** come from `metadata.yaml`. The deterministic logic lives in the tool catalog (`src/ado_swarm/tools/catalog/`), never inside the agent. See [`docs/concepts/agents-tools-skills.md`](docs/concepts/agents-tools-skills.md).

## Current agents

| Directory | Display name | Emits (casefile section) | Purpose |
|---|---|---|---|
| `ticket_analyst` | Ticket Analyst | `normalized_finding` | Normalizes provider issues/work items into canonical findings. |
| `repo_analyst` | Repository Analyst | `repository_evidence` | Gathers read-only repository/file evidence. |
| `security_reviewer` | Security Reviewer | `adjudication` | Adjudicates stale, duplicate, fixed, and false-positive findings. |
| `risk_auditor` | Risk Auditor | `risk` | Scores security risk and automation eligibility. |
| `solutions_architect` | Solutions Architect | `remediation_plan` | Produces bounded remediation plans. |
| `test_engineer` | Test Engineer | `validation` | Defines validation/build checks and review readiness. |
| `software_engineer` | Software Engineer | `execution` | Applies changes in an isolated sandbox (write, approval-gated). |
| `submission_engineer` | Submission Engineer | `submission` | Prepares the draft PR + ticket disposition (write, approval-gated). |
| `qa_lead` | QA Lead | `readiness` | Decides phase readiness for the casefile. |
| `data_analyst` | Data Analyst | `CampaignReport` (artifact) | Mines findings for campaign patterns. |

## Developer workflow

| Command | What it does |
|---|---|
| `just check` | Lint (ruff), type-check (ty), unit tests, and `eval-agents` on the deterministic `fake` profile. |
| `just test` / `just test-workflow` | Unit tests / Temporal workflow tests. |
| `just eval-agents` | Run every agent's golden eval (hermetic, `fake` model). |
| `uv run python -m ado_swarm.agents.<id>.eval --model-profile fake` | Run one agent's eval in isolation. |
| `MODEL_PROVIDER=ollama just eval-agents` | Run evals against a real local model. |

See [`CLAUDE.md`](CLAUDE.md) for the full contributor guide (how to add an agent, tool, or skill) and [`docs/tools-skills-review.md`](docs/tools-skills-review.md) for the tool/skill gap analysis.
