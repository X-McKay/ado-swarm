# ado-swarm

`ado-swarm` is a Python-first, Docker-first foundation for a Temporal-orchestrated security remediation agent swarm. The base architecture supports Azure DevOps and GitHub through provider-neutral source-provider ports, uses Postgres for operational state, and reserves Neo4j + Graphiti for long-term knowledge memory.

The implementation intentionally starts with read-only triage, canonical contracts, a stub provider, and agent evaluation harnesses. Additional remediation skills should be added after the foundation is stable.

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

Temporal owns durable orchestration. Agents own reasoning and structured outputs. Provider adapters hide Azure DevOps and GitHub differences behind canonical contracts. Tool access is policy-gated and denied by default outside the current phase and trust zone.

## Agent catalog

Each agent lives under `src/ado_swarm/agents/<agent_name>/` and has:

| File | Purpose |
|---|---|
| `main.py` | Agent implementation and `build_agent()` factory. |
| `metadata.yaml` | Description, version, tools, skills, permissions, and eval entrypoint. |
| `eval.py` | Isolated evaluation harness. |
| `prompts.md` | Stable role prompt. |

## Current agents

| Directory | Display name | Purpose |
|---|---|---|
| `qa_lead` | QA Lead | Coordinates casefile quality and phase readiness. |
| `ticket_analyst` | Ticket Analyst | Normalizes provider issues/work items. |
| `repo_analyst` | Repository Analyst | Gathers read-only repository evidence. |
| `security_reviewer` | Security Reviewer | Adjudicates stale, duplicate, fixed, and false-positive findings. |
| `risk_auditor` | Risk Auditor | Scores security risk and automation eligibility. |
| `solutions_architect` | Solutions Architect | Produces bounded remediation plans. |
| `software_engineer` | Software Engineer | Applies later sandboxed changes after approval. |
| `test_engineer` | Test Engineer | Validates diffs and prepares later draft PRs. |
| `data_analyst` | Data Analyst | Mines outcomes and campaign patterns. |
