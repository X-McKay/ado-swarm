# ADR-0009: Bounded swarm cell for adjudication; approval-gated tool execution

**Status:** Accepted
**Date:** 2026-05-31
**Relates to:** ADR-0005 (tool policy & approvals), ADR-0008 (model-driven agents); resolves implementation-plan §8-D1 and delivers Phase 1.5.

## Context

Two related decisions are recorded here.

1. **Where multi-agent collaboration lives.** The implementation plan left §8-D1 open: should cross-agent collaboration be owned by Temporal (one Strands agent per activity) or by Strands' own `Swarm`/`Graph`? We committed to *Temporal owns orchestration*, but adjudication (`security_reviewer`) is the one stage where multi-perspective critique measurably improves a decision — independent reviewers arguing *stale* vs *false-positive* vs *duplicate*, reconciled by a judge.

2. **How approvals gate tool execution.** ADR-0005 defined the policy/approval contracts; the supervisor wires approvals as Temporal Updates with validators. The tool layer needs a matching structural gate so that write/high-risk tools cannot execute without an approved `ToolContext`.

## Decision

### Bounded swarm cell (Phase 1.5)
- A **bounded swarm cell** runs a reviewer ensemble + a judge **inside a single Temporal activity** (`agents/swarm_cell.py::run_adjudication_cell`). The cell returns one typed result (`FindingAdjudication`), so Temporal still sees exactly one `security_reviewer` task — durability, retries, and approval boundaries are unchanged.
- The cell reuses `run_model_agent`, so every reviewer and the judge go through the **same tool-policy gate and skill machinery** as any other agent.
- It is **bounded**: a hard `max_model_calls` budget (default `adjudication_swarm_max_model_calls=8`) is enforced across reviewers + judge; exceeding it raises `BudgetExceededError` and fails the activity fast rather than burning unbounded tokens (an ensemble+judge is ~Nx a single agent).
- It is **opt-in and eval-gated**: `security_reviewer` runs as a single agent by default; the swarm is enabled per-run via the `use_swarm` task constraint or globally via `security_reviewer_use_swarm` (default `False`). We only flip the default once golden evals show the swarm beats the single-agent baseline.
- The reviewer positions and judge decision are recorded in the casefile `audit` for auditability (the swarm transcript is harness state, not Temporal history).

### Approval-gated tool execution
- `ToolPolicyHook` (on Strands `BeforeToolCallEvent`) maps each call to `ALLOW | DENY | REQUIRE_APPROVAL`. Tools an agent declares in `write_tool_names` (e.g. `apply_remediation_change`) require an **approved `ToolContext`** (`approval_state == APPROVED`, set from the `approved` task constraint / the supervisor's `approve_task` Update); otherwise the call is cancelled with an approval-required message and the agent surfaces `requires_approval` on its `AgentResult`.
- The forced structured-output tool (named after the section model) is harness machinery and bypasses the domain policy, so structured emission is never blocked or re-forced into a loop.

## Consequences

- Adjudication can use multi-perspective critique without sacrificing Temporal's durability/visibility, and without unbounded cost.
- The decision to *use* the swarm is data-driven (evals), not architectural faith — and reversible by flipping a setting.
- Write tools are structurally un-runnable without approval, satisfying the read-only-first / approval-gated posture even as the remediation skills/tools land.

## Validation

`tests/unit/test_adjudication_swarm.py` covers: the ensemble-then-judge flow, the budget cap raising `BudgetExceededError`, swarm-mode producing an adjudication, and the single-agent default. Tool approval-gating is covered by `tests/unit/test_tool_policy_hook.py`. All run hermetically on the `fake` model.
</content>
