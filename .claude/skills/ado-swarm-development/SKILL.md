---
name: ado-swarm-development
description: Develop and modify the ado-swarm base architecture, agents, provider adapters, and tests.
---
# ado-swarm development

When working in this repository, preserve the core boundaries:

1. Temporal workflows stay deterministic and delegate I/O to activities.
2. Azure DevOps and GitHub access goes through `tools/source_providers` ports and adapters.
3. Agents live under `src/ado_swarm/agents/<agent_name>/` with `main.py`, `metadata.yaml`, `eval.py`, and `prompts.md`.
4. New agent behavior must include or update isolated evaluations.
5. Write-capable provider, Git, PR, and ticket operations must remain policy-gated.
6. Run `just check` before finalizing changes.

Prefer small, testable functions and update documentation when changing architecture or developer workflow.
