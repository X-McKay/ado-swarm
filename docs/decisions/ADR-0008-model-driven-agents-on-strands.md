# ADR-0008: Model-driven agents on Strands; deterministic logic as tools

**Status:** Accepted
**Date:** 2026-05-31
**Supersedes in part:** ADR-0004 (the Strands/Temporal harness runtime), ADR-0006 (the casefile pipeline)

## Context

The earlier implementation contained two anti-patterns (see `docs/codebase-review-2026-05.md` §2): canned-text "stub agents" that never reasoned, and "richer agents" that were deterministic Python mutating a casefile with the model doing nothing. Skills were inert labels (never loaded into a prompt), and the `ToolPolicy` was never wired into execution. The headline capabilities — agents reason with a model, skills are progressively disclosed, tools are policy-gated — existed as data and types but not in the execution path.

We also adopted Simon Willison's definitions as the project's canonical vocabulary (`docs/concepts/agents-tools-skills.md`): an **agent** is *tools in a loop* and always uses a model; a **tool** is a deterministic executable capability; a **skill** is packaged expertise loaded into context. The governing rule: **every agent uses a model; anything deterministic is a tool, never an agent.**

## Decision

1. **Every agent is a model-driven Strands `Agent`** run inside a Temporal activity. The shared runtime (`agents/model_runtime.run_model_agent`) builds the agent with its tools, the `AgentSkills` plugin, and the policy hook, then runs one non-deprecated `invoke_async(prompt, structured_output_model=...)` so the model reasons (calling tools) and emits a typed result in one loop.
2. **Deterministic logic lives in the tool catalog** (`tools/catalog/`) as typed `@tool` functions, each unit-tested in isolation. Agents declare which tools they may call; the deterministic code the old agents inlined is now tools the model invokes.
3. **Tool authorization is structural**, enforced at the Strands `BeforeToolCallEvent` hook (`tools/policy_hook.py`), mapping each call to `ALLOW | DENY | REQUIRE_APPROVAL`. A skill's `allowed-tools` is documentation only. Write tools are declared in `write_tool_names` and require an approved `ToolContext`.
4. **Skills are load-bearing**: the on-disk `SKILL.md` catalog is bound to each agent via the `AgentSkills` plugin (progressive disclosure). Which skills an agent gets is single-sourced from `metadata.yaml` by the registry.
5. **Typed structured output**: each casefile agent emits exactly one `SecurityCasefile` section via structured output; the standalone `data_analyst` emits a `CampaignReport` artifact.
6. **Determinism stays in the workflow**: model calls and I/O happen only in activities; the hand-rolled per-provider completion path (`ModelGateway.complete`) and the old `BaseAgent`/`StrandsAgentRuntime` were deleted in favor of Strands model providers.

## Consequences

- The swarm now genuinely reasons: tools are called through the policy gate, skills are disclosed into context, and outputs are typed and schema-checked. Golden evals run the real Strands loop deterministically via a `FakeModel` (offline CI) and against real models (Ollama) for quality gates.
- Adding an agent is declarative: one `metadata.yaml` + one ~30-line `CasefileAgent` subclass + one eval + a catalog tool. A CI guardrail test enforces that every agent is model-driven with valid catalog tools and real skills.
- The structured-output tool is named after the section model and bypasses the domain policy as harness machinery (otherwise it would be denied and re-forced into a loop).
- Strands' structured-output methods (`structured_output_async`) are deprecated; we use the single-invocation `invoke_async(structured_output_model=...)` path, which also keeps tool results in context for the structured emission on real models.

## Validation

All 9 agents are model-driven and pass golden evals on the `fake` profile; a vocabulary-guardrail test (`tests/unit/test_agent_metadata_validation.py`) fails any model-less agent or unknown tool/skill. Tool-policy denial and approval-gating are covered by `tests/unit/test_tool_policy_hook.py`, and the Temporal workflow lifecycle by `tests/workflow/`.
</content>
