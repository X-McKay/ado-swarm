# Agents, Tools, and Skills — the canonical vocabulary

This document defines the three core concepts in `ado-swarm` and the **one rule** that governs how we decide whether a new piece of work is an agent, a tool, or a skill. It is the reference for code review, scaffolding, and design discussions. If you read one doc before contributing, read this one.

We adopt **Simon Willison's definitions** verbatim as our canonical vocabulary.

---

## The three definitions

### Agent
> *"Tools in a loop to achieve a goal."*

An agent is software that calls an LLM with a prompt **and a set of tool definitions**, executes whichever tools the model requests, feeds the results back into the model, and repeats in a **bounded loop** until a stopping condition is met.

- An agent **always uses a model**. The model does the *deciding*.
- An agent **always has tools**. Without tools it cannot act.
- In this codebase an agent is a Strands `Agent` run inside a Temporal activity (see `docs/architecture.md` and the implementation plan).

### Tool
> An executable function or capability the harness provides to the agent — the agent's *hands*.

A tool takes typed input, does one bounded thing (a computation, an API call, a file read), and returns typed output. Tools are **deterministic and testable in isolation**. The model chooses *when* to call a tool; the tool decides *nothing* about the goal.

- In this codebase a tool is a `@tool`-decorated function in the tool catalog (`src/ado_swarm/tools/catalog/`).
- Tool **authorization** is enforced structurally at the Strands `BeforeToolCallEvent` hook (`ToolPolicyHook`), never by prose in a prompt or skill.

### Skill
> *Packaged expertise* — domain knowledge, instructions, or behavioral patterns loaded into the agent's context to shape *how* it approaches a problem.

A skill is **context, not code**. It takes no action. It is the Anthropic "Agent Skills" / `SKILL.md` format: YAML frontmatter (`name`, `description`, optional `allowed-tools`) plus a markdown body of instructions, loaded on demand via progressive disclosure.

- In this codebase a skill is a `SKILL.md` under `src/ado_swarm/skills/<name>/`, surfaced to agents through the Strands `AgentSkills` plugin.
- `allowed-tools` in a skill is **documentation only** — it is not enforced. Enforcement lives in the tool-policy hook.

---

## THE CORE RULE

> **Every agent uses a model. If a unit of work is deterministic, it is a *tool* (or a harness verification step) — never an agent. We do not ship "deterministic agents."**

This is the most important rule in the project. It exists because the codebase's early history contained two anti-patterns (see `docs/codebase-review-2026-05.md` §2):

1. **Canned-text "stub agents"** — "agents" that returned a fixed string and never reasoned.
2. **Deterministic "richer agents"** — "agents" that were hand-written Python mutating a casefile, with the model doing nothing.

Both are eliminated. An agent that doesn't call a model is not an agent — it's a tool wearing a costume.

### Decision flowchart

```
Is this unit of work deterministic (same input → same output, no judgment)?
│
├─ YES → Is it a check that gates acceptance (tests, schema, lint)?
│        ├─ YES → it's a HARNESS VERIFICATION STEP (a governor), not an agent.
│        └─ NO  → it's a TOOL. Add it to the tool catalog as a typed @tool with a unit test.
│
└─ NO → Does it require a model to decide/plan/judge across messy inputs?
        ├─ YES → it's an AGENT. Give it a model, the tools it needs, and the skills that
        │        shape its approach. It must make ≥1 model call and ≥1 tool call.
        └─ "It's instructions/knowledge, not an actor" → it's a SKILL. Write a SKILL.md.
```

### Worked example (the canonical one)

`ticket_analyst` normalizes a provider security issue into a canonical finding.

- The **deterministic** extraction (parse known scanner formats, map fields) is precise and testable → it is the **`normalize_finding` tool**.
- The **judgment** (this issue is messy/ambiguous; which scanner is this really; is evidence missing; should I call the normalizer or ask for more context) requires a model → that is the **`ticket_analyst` agent**, which calls `normalize_finding` as one of its tools in a loop.
- The **instructions** for *how* to triage a security ticket (what good normalization looks like, edge cases) are loaded as the **`security-ticket-normalization` skill**.

Same problem, three roles: the deterministic core is a tool, the reasoning is the agent, the expertise is a skill.

---

## How this maps to the stack

| Concept | Willison | In `ado-swarm` | Enforcement |
|---|---|---|---|
| Agent | tools in a loop + model | Strands `Agent` inside a Temporal activity | Lint: must declare a model + ≥1 tool + skills; CI fails a model-less agent |
| Tool | the agent's hands | `@tool` fn in `tools/catalog/` | Typed I/O + isolated unit test; authorized at `BeforeToolCallEvent` |
| Skill | packaged expertise | `SKILL.md` via `AgentSkills` plugin | Valid frontmatter; `allowed-tools` is **docs only** |

## Rules of thumb for contributors

- **New agent?** Justify the model-reasoning job in the PR. If you can't, it's a tool.
- **Deterministic logic creeping into an agent's `run()`?** Extract it to a tool.
- **Want to change *how* an agent behaves without changing code?** Write or edit a skill.
- **Need to restrict what an agent can do?** Change the tool policy — not the prompt, not the skill's `allowed-tools`.
- **Verification/governor checks** (schema, tests, linters) are harness steps or tools, never agents.

See `docs/implementation-plan-2026-06.md` (§2.0, §6.4) for how this is built and enforced, and `docs/codebase-review-2026-05.md` for the history that motivated the rule.
</content>
